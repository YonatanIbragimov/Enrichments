#!/usr/bin/env python3.11
"""
Enrichment Verification Script
Validates enriched lead data across all batches:
  1. LinkedIn URLs — visits each to confirm profile exists and name matches
  2. Website URLs — confirms real company site (not junk/redirect/unrelated)
  3. Cross-checks Sunbiz owner names vs LinkedIn profile names
  4. Flags mismatches, dead links, junk entries

Usage: python3.11 verify_enrichment.py [batch_01_enriched.csv batch_02_enriched.csv ...]
       python3.11 verify_enrichment.py --all
"""

import asyncio
import csv
import sys
import os
import re
import random
from pathlib import Path
from urllib.parse import quote_plus, urlparse

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

sys.path.insert(0, '/Users/trinity/.browser-use-env/lib/python3.11/site-packages')
from playwright.async_api import async_playwright

ENRICHED_DIR = Path(__file__).parent / "enriched"
VERIFIED_DIR = Path(__file__).parent / "verified"
VERIFIED_DIR.mkdir(exist_ok=True)

JUNK_DOMAINS = [
    "duckduckgo.com", "google.com", "bing.com", "yahoo.com",
    "miamidade.gov", "polktimes.com", "floridapublicnotices.com",
    "myfloridalicense.com", "sunbiz.org", "florida.gov", "state.fl.us",
    "issuu.com", "opencorporates.com", "buzzfile.com", "dnb.com",
    "zoominfo.com", "apollo.io", "indeed.com", "glassdoor.com",
    "yellowpages.com", "manta.com", "mapquest.com", "crunchbase.com",
    "bloomberg.com", "airbtics.com", "lodgify.com", "wexfordins.com",
    "vacasa.com",
]


def is_junk_url(url):
    """Check if URL is a known junk/redirect/unrelated domain."""
    if not url:
        return False
    url_lower = url.lower()
    # DDG redirect URLs
    if "duckduckgo.com/y.js" in url_lower:
        return True
    if len(url) > 500:  # Absurdly long URLs are ad redirects
        return True
    for domain in JUNK_DOMAINS:
        if domain in url_lower:
            return True
    return False


def names_match(name1, name2):
    """Fuzzy check if two names refer to the same person."""
    if not name1 or not name2:
        return False
    # Normalize
    n1 = re.sub(r'[^a-z\s]', '', name1.lower()).split()
    n2 = re.sub(r'[^a-z\s]', '', name2.lower()).split()
    if not n1 or not n2:
        return False
    # Check if first and last names overlap
    shared = set(n1) & set(n2)
    # At least first or last name matches
    if len(shared) >= 1:
        # Check if the shared word is a first or last name (not middle initial etc)
        if n1[0] in shared or n1[-1] in shared or n2[0] in shared or n2[-1] in shared:
            return True
    return False


def name_from_linkedin_slug(url):
    """Extract a name from a LinkedIn URL slug like /in/alessandra-dale-23295bb6."""
    if not url:
        return ""
    match = re.search(r'linkedin\.com/in/([^/?&#]+)', url)
    if not match:
        return ""
    slug = match.group(1)
    # Remove trailing hash/id (e.g., -23295bb6, -a2360812)
    slug = re.sub(r'-[a-f0-9]{6,}$', '', slug)
    # Convert dashes to spaces, title case
    parts = slug.split('-')
    # Filter out numbers and single chars
    parts = [p for p in parts if len(p) > 1 and not p.isdigit()]
    if parts:
        return ' '.join(p.title() for p in parts)
    return ""


async def verify_linkedin(page, url, expected_name):
    """Visit LinkedIn URL, check if profile exists and name matches."""
    result = {"status": "", "profile_name": "", "name_match": False}

    if not url:
        result["status"] = "empty"
        return result

    # First: extract name from URL slug (works even without login)
    slug_name = name_from_linkedin_slug(url)

    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=12000)
        await page.wait_for_timeout(2000)

        status_code = resp.status if resp else 0
        page_url = page.url
        title = await page.title()

        if status_code == 404 or "Page not found" in title or "not found" in title.lower():
            result["status"] = "dead_link"
            return result

        # Try to get name from page title first (works on authwall)
        profile_name = ""
        if title and " | LinkedIn" in title:
            profile_name = title.split(" | LinkedIn")[0].split(" - ")[0].strip()

        # If title gave us junk like "Sign Up" or empty, use slug
        if not profile_name or profile_name.lower() in ["sign up", "linkedin", "log in", "sign in"]:
            profile_name = slug_name

        # If still no name from title, try h1
        if not profile_name or profile_name.lower() in ["sign up", "linkedin", "log in", "sign in"]:
            name_el = await page.query_selector("h1")
            if name_el:
                h1_text = (await name_el.inner_text()).strip()
                if h1_text.lower() not in ["sign up", "linkedin", "log in", "sign in", ""]:
                    profile_name = h1_text

        # Final fallback to slug
        if not profile_name or profile_name.lower() in ["sign up", "linkedin", "log in", "sign in"]:
            profile_name = slug_name

        result["profile_name"] = profile_name
        result["name_match"] = names_match(expected_name, profile_name)

        if "authwall" in page_url or "login" in page_url:
            result["status"] = "authwall_exists"
        else:
            result["status"] = "valid"

    except Exception as e:
        # Even on error, try slug-based name match
        if slug_name:
            result["profile_name"] = slug_name
            result["name_match"] = names_match(expected_name, slug_name)
            result["status"] = f"error_but_slug_matched"
        else:
            result["status"] = f"error: {str(e)[:60]}"

    return result


async def verify_website(page, url, company_name):
    """Visit website URL, check if it's a real company site."""
    result = {"status": "", "actual_domain": "", "relevant": False}

    if not url:
        result["status"] = "empty"
        return result

    # Pre-check: is this a known junk URL?
    if is_junk_url(url):
        result["status"] = "junk_url"
        result["actual_domain"] = urlparse(url).netloc if "://" in url else "junk"
        return result

    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=12000)
        await page.wait_for_timeout(2000)

        final_url = page.url
        domain = urlparse(final_url).netloc
        result["actual_domain"] = domain

        status_code = resp.status if resp else 0
        if status_code >= 400:
            result["status"] = f"http_{status_code}"
            return result

        # Check if the page content mentions the company or vacation/rental keywords
        title = (await page.title()).lower()
        body_text = ""
        try:
            body_text = (await page.inner_text("body"))[:3000].lower()
        except:
            pass

        company_words = set(re.sub(r'[^a-z\s]', '', company_name.lower()).split())
        company_words -= {"llc", "inc", "corp", "ltd", "lp", "co", "the", "of", "and"}

        # Check relevance
        text = title + " " + body_text
        word_hits = sum(1 for w in company_words if w in text)
        rental_keywords = ["rental", "vacation", "property", "management", "airbnb", "vrbo", "beach", "resort", "home"]
        keyword_hits = sum(1 for k in rental_keywords if k in text)

        if word_hits >= 2 or (word_hits >= 1 and keyword_hits >= 1):
            result["status"] = "valid"
            result["relevant"] = True
        elif keyword_hits >= 2:
            result["status"] = "likely_relevant"
            result["relevant"] = True
        else:
            result["status"] = "unrelated"

    except Exception as e:
        result["status"] = f"error: {str(e)[:60]}"

    return result


async def verify_batch(batch_file, page_li, page_web):
    """Verify all enriched leads in a batch."""
    batch_path = Path(batch_file)
    batch_name = batch_path.stem.replace("_enriched", "")

    leads = []
    with open(batch_path, "r") as f:
        for row in csv.DictReader(f):
            leads.append(row)

    print(f"\n═══════════════════════════════════════════")
    print(f"  Verifying {batch_name}: {len(leads)} leads")
    print(f"═══════════════════════════════════════════")

    verified = []
    stats = {"li_valid": 0, "li_dead": 0, "li_name_match": 0, "li_name_mismatch": 0,
             "web_valid": 0, "web_junk": 0, "web_dead": 0, "web_unrelated": 0,
             "total_with_li": 0, "total_with_web": 0}

    for i, lead in enumerate(leads):
        company = lead.get("Licensee Name", "")
        owner = lead.get("Owner Name", "")
        li_url = lead.get("Owner LinkedIn", "")
        website = lead.get("Website", "")

        print(f"\n  [{i+1}/{len(leads)}] {company}")

        # Verify LinkedIn
        li_result = {"LI Status": "", "LI Profile Name": "", "LI Name Match": ""}
        if li_url:
            stats["total_with_li"] += 1
            print(f"    LinkedIn: {li_url[:60]}...")
            lr = await verify_linkedin(page_li, li_url, owner)
            li_result["LI Status"] = lr["status"]
            li_result["LI Profile Name"] = lr["profile_name"]
            li_result["LI Name Match"] = "yes" if lr["name_match"] else "no"

            if "valid" in lr["status"] or "authwall" in lr["status"]:
                stats["li_valid"] += 1
                if lr["name_match"]:
                    stats["li_name_match"] += 1
                    print(f"    ✓ LinkedIn valid, name matches: {lr['profile_name']}")
                else:
                    stats["li_name_mismatch"] += 1
                    print(f"    ⚠ LinkedIn valid but name mismatch: expected '{owner}', got '{lr['profile_name']}'")
            else:
                stats["li_dead"] += 1
                print(f"    ✗ LinkedIn {lr['status']}")

            await asyncio.sleep(random.uniform(1.5, 3))

        # Verify Website
        web_result = {"Web Status": "", "Web Domain": "", "Web Relevant": ""}
        if website:
            stats["total_with_web"] += 1
            print(f"    Website: {website[:60]}...")
            wr = await verify_website(page_web, website, company)
            web_result["Web Status"] = wr["status"]
            web_result["Web Domain"] = wr["actual_domain"]
            web_result["Web Relevant"] = "yes" if wr["relevant"] else "no"

            if wr["status"] == "valid":
                stats["web_valid"] += 1
                print(f"    ✓ Website valid: {wr['actual_domain']}")
            elif wr["status"] == "likely_relevant":
                stats["web_valid"] += 1
                print(f"    ✓ Website likely relevant: {wr['actual_domain']}")
            elif wr["status"] == "junk_url":
                stats["web_junk"] += 1
                print(f"    ✗ Junk URL (ad redirect or unrelated domain)")
            elif wr["status"] == "unrelated":
                stats["web_unrelated"] += 1
                print(f"    ⚠ Website unrelated to company: {wr['actual_domain']}")
            else:
                stats["web_dead"] += 1
                print(f"    ✗ Website {wr['status']}")

            await asyncio.sleep(random.uniform(1, 2))

        # Merge into lead
        row = dict(lead)
        row.update(li_result)
        row.update(web_result)
        verified.append(row)

        # Save progress
        output_path = VERIFIED_DIR / f"{batch_name}_verified.csv"
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(verified[0].keys()))
            writer.writeheader()
            writer.writerows(verified)

    # Summary
    print(f"\n  ─── {batch_name} Verification Summary ───")
    if stats["total_with_li"] > 0:
        print(f"  LinkedIn: {stats['li_valid']}/{stats['total_with_li']} valid, "
              f"{stats['li_name_match']} name match, {stats['li_name_mismatch']} name mismatch, "
              f"{stats['li_dead']} dead")
    if stats["total_with_web"] > 0:
        print(f"  Website:  {stats['web_valid']}/{stats['total_with_web']} valid, "
              f"{stats['web_junk']} junk, {stats['web_unrelated']} unrelated, "
              f"{stats['web_dead']} dead/error")
    print(f"  Output: {output_path}")

    return stats


async def main(files):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page_li = await ctx.new_page()
        page_web = await ctx.new_page()

        totals = {"li_valid": 0, "li_dead": 0, "li_name_match": 0, "li_name_mismatch": 0,
                  "web_valid": 0, "web_junk": 0, "web_dead": 0, "web_unrelated": 0,
                  "total_with_li": 0, "total_with_web": 0}

        for f in files:
            stats = await verify_batch(f, page_li, page_web)
            for k in totals:
                totals[k] += stats[k]

        await browser.close()

    # Grand totals
    print(f"\n═══════════════════════════════════════════")
    print(f"  VERIFICATION COMPLETE — ALL BATCHES")
    print(f"═══════════════════════════════════════════")
    print(f"  LinkedIn: {totals['li_valid']}/{totals['total_with_li']} valid "
          f"({totals['li_name_match']} name match, {totals['li_name_mismatch']} mismatch, {totals['li_dead']} dead)")
    print(f"  Website:  {totals['web_valid']}/{totals['total_with_web']} valid "
          f"({totals['web_junk']} junk, {totals['web_unrelated']} unrelated, {totals['web_dead']} dead)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3.11 verify_enrichment.py --all")
        print("       python3.11 verify_enrichment.py <enriched_file.csv> ...")
        sys.exit(1)

    if sys.argv[1] == "--all":
        files = sorted(ENRICHED_DIR.glob("batch_*_enriched.csv"))
    else:
        files = [Path(f) for f in sys.argv[1:]]

    print(f"Verifying {len(files)} batch file(s)...")
    asyncio.run(main(files))
