#!/usr/bin/env python3.11
"""
Lead Enrichment Script — Batch Processor v2
Strategy:
  1. Sunbiz (FL Secretary of State) → get officer/owner name
  2. Google → find company website
  3. Google → find owner's LinkedIn profile
  4. Google → find owner's email

Usage: python3.11 enrich_batch.py <batch_file.csv>
"""

import asyncio
import csv
import sys
import os
import re
import time
import random
from pathlib import Path
from urllib.parse import quote_plus

# Force unbuffered output so we can monitor progress
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

sys.path.insert(0, '/Users/trinity/.browser-use-env/lib/python3.11/site-packages')
from playwright.async_api import async_playwright

RESULTS_DIR = Path(__file__).parent / "enriched"
RESULTS_DIR.mkdir(exist_ok=True)

DELAY_MIN = 2
DELAY_MAX = 4


def rand_delay():
    return random.uniform(DELAY_MIN, DELAY_MAX)


async def safe_goto(page, url, retries=2):
    """Navigate with retry on timeout."""
    for attempt in range(retries):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return True
        except Exception as e:
            if attempt < retries - 1:
                await page.wait_for_timeout(3000)
            else:
                print(f"    ⚠ Navigation failed: {e}")
                return False
    return False


# ─── SUNBIZ ───────────────────────────────────────────

async def sunbiz_lookup(page, company_name):
    """Search Florida Sunbiz for the company and extract officer names."""
    # Clean company name for search (remove LLC, INC, etc. for broader match)
    search_name = re.sub(r'\b(LLC|INC|CORP|LTD|LP|CO|L\.?L\.?C\.?|INC\.?)\b\.?', '', company_name, flags=re.IGNORECASE).strip()
    search_name = re.sub(r'[,.]', '', search_name).strip()

    result = {"officers": [], "registered_agent": ""}

    if not await safe_goto(page, "https://search.sunbiz.org/Inquiry/CorporationSearch/ByName"):
        return result

    await page.wait_for_timeout(1500)

    try:
        # Fill search and submit
        await page.fill('input[name="SearchTerm"]', search_name)
        await page.click('input[type="submit"]')
        await page.wait_for_timeout(2500)

        # Find matching result link
        links = await page.query_selector_all("table a")
        best_link = None
        for link in links[:10]:
            text = (await link.inner_text()).strip().upper()
            # Exact or close match
            if company_name.upper().replace(',', '').replace('.', '') in text.replace(',', '').replace('.', ''):
                best_link = link
                break
            # Try matching without LLC/INC
            if search_name.upper() in text:
                best_link = link
                break

        if not best_link and links:
            # Use first result as fallback
            first_text = (await links[0].inner_text()).strip().upper()
            # Only use if reasonably similar
            name_words = set(search_name.upper().split())
            first_words = set(first_text.split())
            overlap = len(name_words & first_words) / max(len(name_words), 1)
            if overlap >= 0.5:
                best_link = links[0]

        if not best_link:
            print(f"    ⚠ Sunbiz: no match found")
            return result

        await best_link.click()
        await page.wait_for_timeout(2500)

        # Parse the detail page
        content = await page.inner_text("body")
        lines = [l.strip() for l in content.split("\n") if l.strip()]

        # Extract officer info
        in_officer_section = False
        current_title = ""
        for i, line in enumerate(lines):
            if "Authorized Person" in line or "Officer/Director" in line:
                in_officer_section = True
                continue
            if in_officer_section and line.startswith("Title"):
                # Next line or same line has the title
                title_match = re.search(r'Title\s+(.+)', line)
                if title_match:
                    current_title = title_match.group(1).strip()
                else:
                    current_title = line.replace("Title", "").strip()
                continue
            if in_officer_section and current_title:
                # This line should be the name (LAST, FIRST format)
                if re.match(r'^[A-Z][A-Z]+,?\s+[A-Z]', line) and "FL " not in line and "Annual" not in line:
                    name_raw = line.strip()
                    # Convert "DALE, ALESSANDRA" to "Alessandra Dale"
                    parts = [p.strip() for p in name_raw.split(",")]
                    if len(parts) == 2:
                        name = f"{parts[1].title()} {parts[0].title()}"
                    else:
                        name = name_raw.title()
                    result["officers"].append({"name": name, "title": current_title})
                    current_title = ""
                continue
            if in_officer_section and ("Annual Report" in line or "Document Images" in line):
                break

        # Extract registered agent
        for i, line in enumerate(lines):
            if "Registered Agent" in line and "Name" in line:
                # Next line should be the agent name
                if i + 1 < len(lines):
                    agent_line = lines[i + 1].strip()
                    if re.match(r'^[A-Z]', agent_line) and "Address" not in agent_line:
                        parts = [p.strip() for p in agent_line.split(",")]
                        if len(parts) == 2 and len(parts[0]) < 30:
                            result["registered_agent"] = f"{parts[1].title()} {parts[0].title()}"
                        else:
                            result["registered_agent"] = agent_line.title()
                break

    except Exception as e:
        print(f"    ⚠ Sunbiz error: {e}")

    return result


# ─── SEARCH ENGINES ───────────────────────────────────

async def google_search(page, query):
    """Search Google and return results."""
    url = f"https://www.google.com/search?q={quote_plus(query)}&num=10"
    if not await safe_goto(page, url):
        return []

    await page.wait_for_timeout(2500)

    # Check for CAPTCHA — fall back to DuckDuckGo
    content = await page.content()
    if "unusual traffic" in content.lower() or "captcha" in content.lower():
        print("    ⚠ Google CAPTCHA — falling back to DuckDuckGo")
        return await ddg_search(page, query)

    results = []
    try:
        h3s = await page.query_selector_all("h3")
        for h3 in h3s[:10]:
            try:
                title = await h3.inner_text()
                href = await h3.evaluate("el => el.closest('a')?.href || ''")
                snippet = await h3.evaluate("""el => {
                    const container = el.closest('[data-hveid]') || el.closest('.tF2Cxc') || el.parentElement?.parentElement?.parentElement;
                    if (!container) return '';
                    const spans = container.querySelectorAll('span, .VwiC3b, [data-sncf]');
                    let text = '';
                    for (const s of spans) {
                        const t = s.innerText || '';
                        if (t.length > 40 && !t.includes(el.innerText)) {
                            text = t;
                            break;
                        }
                    }
                    return text;
                }""")
                results.append({"url": href, "title": title, "snippet": snippet})
            except Exception:
                continue
    except Exception as e:
        print(f"    ⚠ Google parse error: {e}")

    return results


async def ddg_search(page, query):
    """Search DuckDuckGo — no CAPTCHAs."""
    url = f"https://duckduckgo.com/?q={quote_plus(query)}"
    if not await safe_goto(page, url):
        return []

    await page.wait_for_timeout(2500)

    results = []
    try:
        # DuckDuckGo result links
        articles = await page.query_selector_all("article")
        for article in articles[:10]:
            try:
                link_el = await article.query_selector("a[data-testid='result-title-a']")
                snippet_el = await article.query_selector("span[data-testid='bodyText']")
                if not link_el:
                    link_el = await article.query_selector("a")
                href = await link_el.get_attribute("href") if link_el else ""
                title = await link_el.inner_text() if link_el else ""
                snippet = await snippet_el.inner_text() if snippet_el else ""
                results.append({"url": href or "", "title": title, "snippet": snippet})
            except Exception:
                continue

        # Fallback: get all result links if articles didn't work
        if not results:
            links = await page.query_selector_all("a[href]")
            for link in links:
                try:
                    href = await link.get_attribute("href") or ""
                    title = await link.inner_text() or ""
                    if href.startswith("http") and "duckduckgo" not in href and len(title) > 5:
                        results.append({"url": href, "title": title, "snippet": ""})
                except Exception:
                    continue
    except Exception as e:
        print(f"    ⚠ DDG parse error: {e}")

    return results


# ─── EXTRACTORS ───────────────────────────────────────

def extract_linkedin_url(results):
    for r in results:
        url = r.get("url", "")
        if "linkedin.com/in/" in url:
            match = re.search(r'(https?://(?:www\.)?linkedin\.com/in/[^/?&#]+)', url)
            if match:
                return match.group(1)
    return ""


def extract_linkedin_name(results):
    """Extract a person's name from a LinkedIn result title like 'John Smith - Owner - Company'."""
    for r in results:
        if "linkedin.com/in/" not in r.get("url", ""):
            continue
        title = r.get("title", "")
        # LinkedIn titles: "First Last - Title - Company | LinkedIn"
        match = re.match(r'^([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)', title)
        if match:
            return match.group(1)
    return ""


SKIP_DOMAINS = [
    "linkedin.com", "facebook.com", "yelp.com", "bbb.org", "google.com",
    "instagram.com", "twitter.com", "x.com", "youtube.com", "zillow.com",
    "airbnb.com", "vrbo.com", "tripadvisor.com", "booking.com", "indeed.com",
    "glassdoor.com", "yellowpages.com", "manta.com", "mapquest.com",
    "crunchbase.com", "bloomberg.com", "zoominfo.com", "apollo.io",
    "dnb.com", "sunbiz.org", "florida.gov", "state.fl.us", "myfloridalicense.com",
    "floridapublicnotices.com", "opencorporates.com", "buzzfile.com",
]


def extract_website(results):
    for r in results:
        url = r.get("url", "")
        if not url:
            continue
        if any(d in url.lower() for d in SKIP_DOMAINS):
            continue
        return url
    return ""


def find_email_in_text(text):
    emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', text)
    junk = ["example.com", "email.com", "sentry.", "noreply", "wixpress", "sentry.io"]
    for email in emails:
        if not any(j in email.lower() for j in junk):
            return email
    return ""


# ─── MAIN ENRICHMENT ─────────────────────────────────

async def enrich_lead(page_sunbiz, page_google, lead):
    """Enrich a single lead."""
    company = lead["Licensee Name"]
    counties = lead.get("Counties", "")

    print(f"\n  🔍 {company}")

    result = {"Owner Name": "", "Owner Email": "", "Owner LinkedIn": "", "Website": "", "Notes": ""}

    # ── Step 1: Sunbiz lookup ──
    print("    Step 1: Sunbiz officer lookup...")
    sb = await sunbiz_lookup(page_sunbiz, company)

    owner_name = ""
    if sb["officers"]:
        # Prefer owner/CEO/president titles
        priority = ["CEO", "PRES", "OWNER", "MGR", "MANAGER", "MANAGING", "PRINCIPAL", "MEMBER"]
        for prio in priority:
            for off in sb["officers"]:
                if prio in off["title"].upper():
                    owner_name = off["name"]
                    print(f"    ✓ Sunbiz officer: {owner_name} ({off['title']})")
                    break
            if owner_name:
                break
        if not owner_name:
            owner_name = sb["officers"][0]["name"]
            print(f"    ✓ Sunbiz officer: {owner_name} ({sb['officers'][0]['title']})")
    elif sb["registered_agent"]:
        owner_name = sb["registered_agent"]
        print(f"    ✓ Sunbiz registered agent: {owner_name}")
    else:
        print("    ✗ Sunbiz: no officers found")

    result["Owner Name"] = owner_name
    await asyncio.sleep(rand_delay())

    # ── Step 2: Google for website ──
    print("    Step 2: Google for website...")
    q2 = f'"{company}" Florida vacation rental property management'
    r2 = await google_search(page_google, q2)
    website = extract_website(r2)
    if website:
        result["Website"] = website
        print(f"    ✓ Website: {website}")
    else:
        print("    ✗ No website found")
    await asyncio.sleep(rand_delay())

    # ── Step 3: DuckDuckGo for LinkedIn (avoids Google CAPTCHAs) ──
    if owner_name:
        print(f"    Step 3: DDG LinkedIn search for {owner_name}...")
        q3 = f'site:linkedin.com/in/ "{owner_name}" Florida'
        r3 = await ddg_search(page_google, q3)
        li = extract_linkedin_url(r3)
        if li:
            result["Owner LinkedIn"] = li
            print(f"    ✓ LinkedIn: {li}")
        else:
            q3b = f'linkedin.com/in {owner_name} {company} Florida'
            r3b = await ddg_search(page_google, q3b)
            li = extract_linkedin_url(r3b)
            if li:
                result["Owner LinkedIn"] = li
                print(f"    ✓ LinkedIn (broad): {li}")
            else:
                print("    ✗ No LinkedIn found")
        await asyncio.sleep(rand_delay())
    else:
        print(f"    Step 3: DDG LinkedIn search for company owner...")
        q3 = f'linkedin.com/in {company} owner founder Florida'
        r3 = await ddg_search(page_google, q3)
        li = extract_linkedin_url(r3)
        if li:
            result["Owner LinkedIn"] = li
            name = extract_linkedin_name(r3)
            if name:
                result["Owner Name"] = name
                print(f"    ✓ LinkedIn + name: {name} → {li}")
            else:
                print(f"    ✓ LinkedIn: {li}")
        else:
            print("    ✗ No LinkedIn found")
        await asyncio.sleep(rand_delay())

    # ── Step 4: DuckDuckGo for email ──
    search_name = result["Owner Name"] or company
    print(f"    Step 4: DDG email search for {search_name}...")
    q4 = f'"{search_name}" "{company}" email'
    r4 = await ddg_search(page_google, q4)
    for r in r4:
        text = r.get("snippet", "") + " " + r.get("title", "")
        email = find_email_in_text(text)
        if email:
            result["Owner Email"] = email
            print(f"    ✓ Email: {email}")
            break
    if not result["Owner Email"]:
        if result["Website"] and result["Owner Name"]:
            q4b = f'"{result["Owner Name"]}" email @'
            r4b = await ddg_search(page_google, q4b)
            for r in r4b:
                text = r.get("snippet", "") + " " + r.get("title", "")
                email = find_email_in_text(text)
                if email:
                    result["Owner Email"] = email
                    print(f"    ✓ Email (broad): {email}")
                    break
        if not result["Owner Email"]:
            print("    ✗ No email found")
    await asyncio.sleep(rand_delay())

    # ── Summary ──
    found = [f for f in ["Owner Name", "Owner LinkedIn", "Owner Email", "Website"] if result[f]]
    missing = [f for f in ["Owner Name", "Owner LinkedIn", "Owner Email", "Website"] if not result[f]]
    result["Notes"] = "Complete" if not missing else f"Missing: {', '.join(missing)}"

    icon = "✓" if len(found) >= 3 else "◐" if found else "✗"
    print(f"    {icon} Result: {len(found)}/4 fields — {result['Notes']}")

    return result


async def process_batch(batch_file):
    """Process an entire batch CSV with resume support."""
    batch_path = Path(batch_file)
    batch_name = batch_path.stem
    output_path = RESULTS_DIR / f"{batch_name}_enriched.csv"

    leads = []
    with open(batch_path, "r") as f:
        for row in csv.DictReader(f):
            leads.append(row)

    # Resume: load already-enriched leads
    enriched = []
    already_done = set()
    if output_path.exists():
        with open(output_path, "r") as f:
            for row in csv.DictReader(f):
                enriched.append(row)
                already_done.add(row["Licensee Name"])
        print(f"  Resuming: {len(already_done)} leads already done, {len(leads) - len(already_done)} remaining")

    print(f"═══════════════════════════════════════════")
    print(f"  Enriching {batch_name}: {len(leads)} leads ({len(already_done)} done)")
    print(f"═══════════════════════════════════════════")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )

        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page_sunbiz = await ctx.new_page()
        page_google = await ctx.new_page()

        for i, lead in enumerate(leads):
            if lead["Licensee Name"] in already_done:
                continue

            print(f"\n[{i+1}/{len(leads)}] ─────────────────────────────")
            try:
                result = await asyncio.wait_for(
                    enrich_lead(page_sunbiz, page_google, lead),
                    timeout=120,  # 2 min max per lead
                )
                lead["Owner Name"] = result["Owner Name"]
                lead["Owner Email"] = result["Owner Email"]
                lead["Owner LinkedIn"] = result["Owner LinkedIn"]
                lead["Website"] = result["Website"]
                lead["Notes"] = result["Notes"]
            except asyncio.TimeoutError:
                print(f"    ✗ Timed out after 120s — skipping")
                lead["Notes"] = "Error: timeout"
            except Exception as e:
                print(f"    ✗ Error: {e}")
                lead["Notes"] = f"Error: {e}"
            enriched.append(lead)

            # Save after every lead
            with open(output_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(enriched[0].keys()))
                writer.writeheader()
                writer.writerows(enriched)

        await browser.close()

    # Summary
    print(f"\n═══════════════════════════════════════════")
    print(f"  BATCH COMPLETE: {batch_name}")
    print(f"═══════════════════════════════════════════")
    complete = sum(1 for l in enriched if l.get("Notes") == "Complete")
    has_name = sum(1 for l in enriched if l.get("Owner Name"))
    has_li = sum(1 for l in enriched if l.get("Owner LinkedIn"))
    has_email = sum(1 for l in enriched if l.get("Owner Email"))
    has_web = sum(1 for l in enriched if l.get("Website"))
    print(f"  Complete (4/4): {complete}/{len(enriched)}")
    print(f"  Owner Name:     {has_name}/{len(enriched)}")
    print(f"  LinkedIn:       {has_li}/{len(enriched)}")
    print(f"  Email:          {has_email}/{len(enriched)}")
    print(f"  Website:        {has_web}/{len(enriched)}")
    print(f"  Output: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3.11 enrich_batch.py <batch_file.csv>")
        sys.exit(1)
    asyncio.run(process_batch(sys.argv[1]))
