# Rev Whisper — Florida STR Lead Enrichment

Automated enrichment pipeline for the Florida short-term rental permit database. Produces outreach-ready lead lists for LinkedIn drip campaigns (Dripify) and cold email (Instantly).

## Pipeline

1. **Clean** — remove associations, HOAs, condos, timeshares, single-building operators
2. **Score** — weighted 0–100 rubric (portfolio distribution, unit count, multi-county, entity type)
3. **Batch** — split into CSVs of 50, highest score first
4. **Enrich** — Sunbiz officer lookup + Google/DuckDuckGo for website, LinkedIn, email
5. **Verify** — visit each LinkedIn and website URL; slug-match names against Sunbiz
6. **Cleanup** — blank mismatched LinkedIns, junk redirects, dead sites; produce final CSVs

## Tiers

| Tier | Listings | Leads | Status |
|------|----------|-------|--------|
| 01 | 25–49 | 412 | Complete |
| 02 | 50–99 | ~75 | Pending |
| 03 | 100–199 | ~135 | Pending |
| 04 | 200+ | ~95 | Pending |

## Live Site

- **Landing:** [index.html](./index.html)
- **25–49 Tier Process:** [`25-49 Listings/enrichment_process.html`](./25-49%20Listings/enrichment_process.html)
- **25–49 Tier Leads:** [`25-49 Listings/enriched_leads.html`](./25-49%20Listings/enriched_leads.html)

## Scripts

| Script | Purpose |
|--------|---------|
| `enrich_batch.py` | Drives browser automation across Sunbiz + Google + DDG for one batch |
| `verify_enrichment.py` | Visits every LinkedIn + website URL to confirm validity |
| `rebuild_html.py` | Regenerates `master_clean_all_batches.csv` and updates both HTML files with the latest verified data |

## Running a New Batch

```bash
# From inside the tier folder (e.g., "25-49 Listings/")
python3.11 enrich_batch.py batches/batch_0X.csv
python3.11 verify_enrichment.py enriched/batch_0X_enriched.csv
python3.11 rebuild_html.py                    # refreshes both HTML files + master CSV
python3.11 rebuild_html.py --push             # also commits + pushes to trigger redeploy
```

## Tools

- **Sunbiz** (`search.sunbiz.org`) — FL Secretary of State officer records
- **Google Search** — company website discovery (falls back to DuckDuckGo on CAPTCHA)
- **DuckDuckGo** — LinkedIn profile + email discovery (no CAPTCHAs)
- **Playwright** — browser automation

## Data Notes

- Owner names from Sunbiz are highly reliable (~99% hit rate across tier 01)
- LinkedIn profiles get ~75% raw hit rate; after slug-based name verification, ~52% are confirmed correct
- Email discovery via public search is weak (~1–2%) — recommend Hunter.io or Instantly enrichment for email-specific needs
