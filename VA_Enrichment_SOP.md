# Lead Enrichment SOP — Florida STR Property Managers

**Purpose:** Take a raw list of Florida short-term rental licensees and turn each row into a qualified lead with: **Owner Name, Company Website, LinkedIn Profile, Owner Email.**

**Time per lead:** ~3–5 minutes
**Batch size:** 50 leads (one CSV file)
**Deliverable:** One completed CSV per batch, plus a short notes column for anything unusual.

---

## Tools You Will Use

| Tool | URL | What it's for |
|------|-----|---------------|
| Google Sheets (or Excel) | — | Opens the batch CSV, fills in findings |
| Sunbiz | https://search.sunbiz.org/Inquiry/CorporationSearch/ByName | Finds the legal owner/officer of a Florida company |
| Google Search | https://www.google.com | Finds the company website |
| DuckDuckGo Search | https://duckduckgo.com | Finds LinkedIn + email (Google blocks these searches) |
| Apollo.io | https://app.apollo.io | **Last-resort fallback** for rows still missing LinkedIn or Email |
| Web browser | Chrome or Safari | Everything runs in the browser |

No software to install. No scripts to run. Everything is manual browser work.

> **Apollo access:** You need a logged-in Apollo account with search credits. Apollo is only used at the **end of the batch** for rows that couldn't be filled through the free searches — this keeps credit usage low.

---

## Before You Start Each Batch

1. Open the batch file: `batches/batch_XX.csv` in Google Sheets.
2. Confirm the columns exist. If missing, add them:
   - `Owner Name`
   - `Owner LinkedIn`
   - `Website`
   - `Owner Email`
   - `Notes`
3. Always work top-to-bottom (highest-scored leads first).
4. Save after every 5 leads.

---

## The Workflow

**Pass 1 — free sources (Steps 1–4):** Run every lead through Sunbiz → Google → DuckDuckGo LinkedIn → DuckDuckGo Email.

**Pass 2 — Apollo fallback (Step 5):** Once Pass 1 is done, go back through the batch and use Apollo **only** on rows still missing LinkedIn and/or Email.

If a step returns nothing, leave the cell blank and move on — **do not guess.**

---

### Step 1 — Owner Name (Sunbiz) — expected hit rate: ~99%

1. Go to https://search.sunbiz.org/Inquiry/CorporationSearch/ByName
2. Copy the **Licensee Name** from the row. **Strip the suffix** (remove "LLC", "INC", "CORP", "LTD", "LP") before pasting.
3. Paste the cleaned name into the search box → click **Search Now**.
4. In the results, click the entity whose name matches most closely (ignore "INACTIVE" or dissolved entries if an active one exists).
5. On the detail page, scroll to **"Officer/Director Detail"** or **"Authorized Person(s) Detail"**.
6. Pick the first officer using this priority order:
   - **CEO → President → Owner → MGR → Manager → Principal → Member**
   - If none listed, use the **Registered Agent** name.
7. Paste the officer's full name into the **Owner Name** cell.

> **Tip:** If Sunbiz returns multiple companies with the same name, pick the one whose **Principal Address** is in Florida and whose **Filing Date** is the oldest active one.

---

### Step 2 — Company Website (Google) — expected hit rate: ~39% after cleanup

1. Go to https://www.google.com
2. Search: `"[Company Name]" Florida vacation rental property management`
   - Keep the quotes around the company name.
3. Look at the top 5 results. **Skip** any of these domains:
   - linkedin.com, facebook.com, instagram.com, yelp.com
   - airbnb.com, vrbo.com, booking.com, expedia.com
   - any `.gov` site (myfloridalicense, sunbiz, etc.)
   - news sites, Yellow Pages, aggregator directories
4. The first remaining result should be the company's own website. Paste the URL into the **Website** cell.
5. **Quick verification** — click the URL. Confirm:
   - The site loads (not a 404 or "site down").
   - The company name appears somewhere on the homepage.
   - The site looks like a rental / property management business.
6. If none of that is true, blank the cell and add a note.

> **If Google shows a CAPTCHA:** Switch to https://duckduckgo.com and run the same search there.

---

### Step 3 — LinkedIn Profile (DuckDuckGo) — expected hit rate: ~48% after cleanup

We use **DuckDuckGo** for this, not Google. Google blocks `site:linkedin.com` searches quickly.

1. Go to https://duckduckgo.com
2. Search: `site:linkedin.com/in/ "[Owner Name]" Florida`
   - Use the Owner Name you found in Step 1.
3. If no result, broaden: `linkedin.com/in [Owner Name] [Company Name] Florida`
4. Look for the first `linkedin.com/in/…` URL in the results.
5. **Verify before pasting:**
   - Click the link. If LinkedIn shows a login wall, look at the URL slug instead — e.g. `/in/jane-smith-a12b3c` → "Jane Smith".
   - Does the slug name match the Owner Name? First OR last name match is enough.
   - If it matches → paste the URL into the **Owner LinkedIn** cell.
   - If it doesn't match → leave blank, add note: `LinkedIn wrong person`.

> **Common pitfall:** Common names (e.g. "Carl Johnson") return the wrong person. When in doubt, leave the cell blank. A missing LinkedIn is better than a wrong one.

---

### Step 4 — Owner Email (DuckDuckGo) — expected hit rate: ~4%

Most of the time this returns nothing. That's expected — don't spend more than 2 minutes on it.

1. Stay on https://duckduckgo.com
2. Search: `"[Owner Name]" "[Company Name]" email`
3. Scan result **snippets** (the grey preview text under each result) for anything that looks like an email: `name@domain.com`.
4. **Skip** these junk domains: example.com, noreply@…, sentry.io, wixpress.com, unknown@…
5. If found, paste into the **Owner Email** cell.
6. If not found, leave blank. Move on.

---

### Step 5 — Apollo (Final Fallback) — only for rows still missing LinkedIn or Email

Do this step **after** you've finished Pass 1 on the whole batch. Filter the CSV to rows where **Owner LinkedIn** OR **Owner Email** is still blank. Only those rows go through Apollo.

1. Go to https://app.apollo.io and confirm you're logged in.
2. Open the **People** search (top nav).
3. Search by company:
   - In the **Company** filter, paste the company name. If you have the website from Step 2, use the **domain** (more reliable than name alone).
   - Add **Location: Florida, United States**.
4. In the results, find the row whose name matches the **Owner Name** from Sunbiz. First OR last name match is enough.
5. Click the person's row to open their profile panel.
6. Fill in whatever is **still missing** on the CSV row:
   - If Owner LinkedIn is blank → click the LinkedIn icon on the Apollo profile, copy the URL, paste into the cell.
   - If Owner Email is blank → click **Access Email** (or **Save** → **Access Email**) to reveal and copy the email.
   - **Do not overwrite** fields you already filled in Pass 1. Apollo is only filling gaps.
7. Add `Apollo` to the **Notes** cell so we know where the fill came from.

**What counts as a valid Apollo match:**
- Name matches the Sunbiz owner (first OR last).
- Company on Apollo matches the Licensee Name OR the website domain from Step 2.
- Location is Florida (or the person's prior role was in Florida).
- If two people match, prefer the one with a senior title (Owner, CEO, President, Principal, Manager).

**When to skip the Apollo lookup entirely for a row:**
- No person on Apollo matches the Sunbiz owner name.
- The only matches are clearly the wrong company or industry.
- The row has no Owner Name from Sunbiz (nothing to match against).

> **Do not burn credits on bad matches.** If you're not confident it's the right person, leave the cell blank and move on. A blank is better than a wrong email.

---

## Quality Checks (Do These Before Submitting the Batch)

Open the batch CSV and scan every row:

| Check | What to do |
|-------|-----------|
| Owner Name is present | Should be ~99% filled. If under 95%, go back and re-search the blanks. |
| Website URLs load | Click a random 5. If any are dead or unrelated, blank them. |
| LinkedIn URLs match Owner Name | Click a random 5. Check slug name matches. Blank mismatches. |
| No duplicate owners | Sort by Owner Name. If the same person appears for different companies, add a note on both rows. |
| No personal social accounts as "website" | facebook.com, instagram.com → blank the cell. |
| Apollo fills are tagged | Every row that got data from Apollo should say `Apollo` in Notes. |

---

## What to Deliver

For each completed batch, hand back:

1. **`batch_XX_complete.csv`** — the filled-in batch file.
2. **Notes column** — anything weird: "Sunbiz had two matching entities", "LinkedIn hit belongs to a different person", "website redirects to a broker aggregator", "Apollo", etc.
3. **Flag list** — a short list of row numbers where you couldn't find anything and think the lead should be skipped.
4. **Apollo credit usage** — how many Apollo lookups you ran and how many returned a useful match.

---

## Speed Tips

- During Pass 1, keep **4 browser tabs open**: Sunbiz, Google, DuckDuckGo (LinkedIn), DuckDuckGo (email). Cycle through all four before moving to the next row.
- Only open Apollo at the **end of the batch**, after you've filtered for rows still missing data. This keeps you out of Apollo's UI during the bulk of the work and protects credits.
- Use **⌘+L** (Mac) / **Ctrl+L** (Windows) to jump straight to the search bar.
- If DuckDuckGo starts feeling slow or shows a CAPTCHA, take a 2-minute break before continuing.
- Do **not** log into LinkedIn from this browser — it will start tracking the activity and rate-limit you.

---

## When to Stop and Ask

Flag the batch and escalate if:

- **More than 10% of Sunbiz lookups fail** — usually means the source data is off.
- **Google/DuckDuckGo both CAPTCHA immediately** — you may need to switch networks or wait a day.
- **Apollo credits run out before the fallback pass is complete** — stop and ping the project lead rather than skipping rows silently.
- **A company name maps to a different industry** (e.g. a trucking company, not a rental PM) — the cleaning step missed a bad row. Note it and skip.

---

## Reference: What "Good" Looks Like

One fully enriched row (LinkedIn from DDG, email from Apollo fallback):

| Column | Example |
|--------|---------|
| Licensee Name | LOYALTY VACATION HOMES LLC |
| Owner Name | Liza Haynes |
| Website | loyaltyvacationhomes.com |
| Owner LinkedIn | linkedin.com/in/liza-haynes-233424aa |
| Owner Email | liza@loyaltyvacationhomes.com |
| Notes | MGR per Sunbiz; Apollo (email) |

**Target per batch of 50:**
- After Pass 1 (free): ~49 owner names, ~24 LinkedIns, ~19 websites, ~2 emails.
- After Pass 2 (Apollo fallback): ~30–35 LinkedIns total, ~15–25 emails total. Apollo typically lifts email fill from ~4% to 30–50% on the gap rows it can match.
