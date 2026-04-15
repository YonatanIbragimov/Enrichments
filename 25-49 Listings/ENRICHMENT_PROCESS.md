# RevWhisper Lead Enrichment Process
## Florida STR Property Manager Outreach — 25-49 Listings Tier

---

### Source Data

Raw input: Florida STR permit database (`fl_str_pm_companies_10plus_units.xlsx`), sheet "25-49 Listings" — 505 licensees with columns: Rank, Licensee Name, Total Units, Unique Addresses, Counties, Cities Served, Phone.

---

### Step 1: Cleaning

Remove non-target rows that are not property management companies:

| Rule | Pattern | Why |
|------|---------|-----|
| Associations & HOAs | Name contains ASSOCIATION, ASSOC, ASN, CONDOMINIUM, CONDO, HOA, HOMEOWNER, TIMESHARE | Building-level entities, not PM companies |
| Single-building operators | Unique Addresses = 1 | Manages one condo tower, not a distributed portfolio |
| Generic entries | Licensee name is just "OWNER" | No identifiable company |
| Duplicates | Exact name match (case-insensitive) | Prevents double-outreach |

**Result:** 505 raw → 413 leads retained (92 removed).

---

### Step 2: Scoring

Each lead scored 0-100 using weighted criteria:

| Signal | Weight | Calculation |
|--------|--------|-------------|
| Distributed portfolio ratio | 40% | (Unique Addresses / Total Units) × 40. Ratio near 1.0 = separate homes, not a single building. |
| Total unit count | 20% | Linear scale within tier: 25 units = 10 pts, 49 units = 20 pts. |
| Has phone number | 10% | Non-empty phone field = 10 pts. |
| Multi-county presence | 12% | 3+ counties = 12 pts, 2 = 8 pts, 1 = 3 pts. |
| Business entity type | 10% | Name contains LLC, INC, CORP, LTD, LP = 10 pts. |
| PM business keywords (bonus) | 8% | Name contains MANAGEMENT, REALTY, PROPERTIES, RENTALS, VACATION, REAL ESTATE = 8 pts. |

Leads sorted highest score first.

---

### Step 3: Batching

Scored leads split into CSV files of 50, ordered by score descending. Each batch CSV includes empty columns ready for enrichment: Owner Name, Owner Email, Owner LinkedIn, Website, Notes.

**Result:** 413 leads → 9 batches (8 × 50 + 1 × 13).

---

### Step 4: Enrichment (per batch)

Automated browser script using Playwright drives two browser tabs — one for Sunbiz, one for search engines. Four searches per lead:

**4a. Sunbiz Officer Lookup (Florida Secretary of State)**
- Navigate to `search.sunbiz.org/Inquiry/CorporationSearch/ByName`
- Search the company name (stripped of LLC/INC suffixes)
- Match the correct entity from search results
- Click through to the detail page
- Extract officers from the "Authorized Person(s)" section
- Priority order: CEO → President → Owner → MGR → Manager → Principal → Member
- Fallback: Registered Agent name if no officers listed
- **Hit rate: 99%** — nearly every FL LLC/Corp has officers on file

**4b. Google Search for Website**
- Query: `"[Company Name]" Florida vacation rental property management`
- Parse search results (h3 elements with parent anchor links)
- Filter out known non-company domains (LinkedIn, Facebook, Yelp, Airbnb, gov sites, etc.)
- Take the first remaining result as the company website
- If Google returns a CAPTCHA, fall back to DuckDuckGo automatically

**4c. DuckDuckGo Search for LinkedIn**
- Query: `site:linkedin.com/in/ "[Owner Name]" Florida`
- If no result, broader query: `linkedin.com/in [Owner Name] [Company Name] Florida`
- Extract the first `linkedin.com/in/` URL from results
- DuckDuckGo used instead of Google because Google aggressively CAPTCHAs `site:linkedin.com` queries from automated browsers

**4d. DuckDuckGo Search for Email**
- Query: `"[Owner Name]" "[Company Name]" email`
- Scan result snippets for email regex patterns
- Filter out junk emails (example.com, noreply, sentry, wixpress)
- If no result, broader query: `"[Owner Name]" email @`

**Pacing:** 2-4 second random delay between searches to avoid rate limiting. 2-minute timeout per lead — if any step hangs (CAPTCHA, navigation failure), the lead is skipped and marked as error. Progress saved to disk after every lead for crash recovery.

**Resume support:** If the script is interrupted, restarting it skips leads already present in the output file.

---

### Step 5: Verification

Separate browser script visits every LinkedIn URL and website URL found during enrichment:

**LinkedIn Verification:**
- Visit each LinkedIn profile URL
- Check that the page loads (not a 404)
- Extract the person's name from the URL slug (e.g., `/in/alessandra-dale-23295bb6` → "Alessandra Dale")
- Slug-based extraction used because LinkedIn blocks profile content behind an auth wall for non-logged-in browsers
- Compare extracted name against the Sunbiz owner name using fuzzy matching (shared first or last name)
- Mark as: valid + name match, valid + name mismatch, or dead link

**Website Verification:**
- Visit each website URL
- Check HTTP status (flag 4xx/5xx as dead)
- Pre-filter known junk domains (DuckDuckGo redirects, gov sites, news sites, aggregator sites)
- For remaining URLs: scrape page title and first 3000 chars of body text
- Check if the company name words or vacation rental keywords appear in the content
- Mark as: valid, likely relevant, unrelated, junk, or dead

---

### Step 6: Data Cleanup

Automated pass over all verified data:

| Action | Trigger | Count (Batches 1-3) |
|--------|---------|---------------------|
| Blank LinkedIn URL | Name mismatch — profile belongs to a different person | 38 blanked |
| Blank Website URL | Junk URL (DDG ad redirect, gov site, news article) | 42 blanked |
| Blank Website URL | Unrelated site (content doesn't mention company or rentals) | 6 blanked |
| Blank Website URL | Dead link (HTTP 403, 429, or connection error) | 6 blanked |

**Output files:**
- `cleaned/batch_XX_clean.csv` — individual batch files with junk removed
- `cleaned/master_clean_all_batches.csv` — all batches combined
- `cleaned/flagged_for_review.csv` — leads that lost data during cleanup (candidates for manual re-search)

---

### Final Data Quality (150 leads, Batches 1-3)

| Field | Rate | Source |
|-------|------|--------|
| Owner Name | 99% (149/150) | Sunbiz FL Secretary of State |
| LinkedIn (verified) | 48% (73/150) | DuckDuckGo search, slug-verified |
| Website (verified) | 39% (59/150) | Google/DDG search, content-verified |
| Email | 4% (6/150) | DuckDuckGo search, snippet extraction |

---

### Tools & Dependencies

| Tool | Purpose |
|------|---------|
| Python 3.11 | Script runtime |
| Playwright (Chromium) | Browser automation |
| Sunbiz (search.sunbiz.org) | Florida LLC/Corp officer lookup |
| Google Search | Company website discovery |
| DuckDuckGo Search | LinkedIn profile + email discovery (CAPTCHA-free) |
| openpyxl | Read source .xlsx file |

---

### Known Limitations

- **Email hit rate is very low (4%)** — small FL vacation rental companies rarely have public email addresses in search results. Recommend using Instantly enrichment or Hunter.io for email discovery on leads where we have owner name + company website.
- **DuckDuckGo LinkedIn search returns wrong person ~34% of the time** — common names (e.g., "Carl Johnson") match unrelated profiles. Verification catches these, but it means re-searching those leads manually or with a logged-in LinkedIn session.
- **Google CAPTCHAs activate after ~12-15 searches** from an automated browser. The script falls back to DuckDuckGo, but DDG website results are lower quality (ad redirects, less relevant).
- **LinkedIn auth wall** prevents extracting full profile details (job title, company confirmation) without a logged-in session. Verification relies on URL slug name matching only.
