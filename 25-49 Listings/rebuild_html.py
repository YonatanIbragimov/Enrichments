#!/usr/bin/env python3.11
"""
Rebuild the HTML files after more batches get verified.
Run this any time new verified batches arrive — it rediscovers everything
available and regenerates the master clean CSV and both HTML pages.
"""
import csv
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)

VERIFIED_DIR = Path(__file__).parent / "verified"
CLEAN_DIR = Path(__file__).parent / "cleaned"
CLEAN_DIR.mkdir(exist_ok=True)

all_clean = []
flagged_rows = []
stats = {"li_blanked": 0, "web_blanked": 0, "needs_review": 0, "total_clean": 0}
batches_processed = []

# Auto-discover all verified batches
verified_files = sorted(VERIFIED_DIR.glob("batch_*_verified.csv"))

for verified_file in verified_files:
    batch_num = int(verified_file.stem.replace("batch_", "").replace("_verified", ""))
    leads = list(csv.DictReader(open(verified_file)))
    print(f"Batch {batch_num:02d}: {len(leads)} leads")
    batches_processed.append(batch_num)

    cleaned = []
    for lead in leads:
        flags = []

        if lead.get("Owner LinkedIn") and lead.get("LI Name Match") == "no":
            flags.append("LinkedIn blanked (name mismatch)")
            lead["Owner LinkedIn"] = ""
            stats["li_blanked"] += 1

        web_status = lead.get("Web Status", "")
        if lead.get("Website") and (
            web_status in ["junk_url", "unrelated"]
            or web_status.startswith("http_")
            or web_status.startswith("error")
        ):
            flags.append(f"Website blanked ({web_status})")
            lead["Website"] = ""
            stats["web_blanked"] += 1

        missing = []
        if not lead.get("Owner Name"): missing.append("Owner Name")
        if not lead.get("Owner LinkedIn"): missing.append("LinkedIn")
        if not lead.get("Website"): missing.append("Website")
        if not lead.get("Owner Email"): missing.append("Email")
        lead["Notes"] = "Complete" if not missing else f"Missing: {', '.join(missing)}"

        if flags:
            stats["needs_review"] += 1
            flagged_rows.append({
                "Batch": f"batch_{batch_num:02d}",
                "Company": lead.get("Licensee Name", ""),
                "Owner Name": lead.get("Owner Name", ""),
                "Flags": " | ".join(flags),
                "Missing After Clean": ", ".join(missing) if missing else "None",
            })
        else:
            stats["total_clean"] += 1

        clean_row = {
            "Rank": lead.get("Rank", ""),
            "Licensee Name": lead.get("Licensee Name", ""),
            "Total Units": lead.get("Total Units", ""),
            "Unique Addresses": lead.get("Unique Addresses", ""),
            "Counties": lead.get("Counties", ""),
            "Cities Served": lead.get("Cities Served", ""),
            "Phone": lead.get("Phone", ""),
            "Score": lead.get("Score", ""),
            "Owner Name": lead.get("Owner Name", ""),
            "Owner Email": lead.get("Owner Email", ""),
            "Owner LinkedIn": lead.get("Owner LinkedIn", ""),
            "Website": lead.get("Website", ""),
            "Notes": lead.get("Notes", ""),
        }
        cleaned.append(clean_row)
        all_clean.append(clean_row)

    with open(CLEAN_DIR / f"batch_{batch_num:02d}_clean.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(cleaned[0].keys()))
        writer.writeheader()
        writer.writerows(cleaned)

# Write master + flagged files
with open(CLEAN_DIR / "master_clean_all_batches.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=list(all_clean[0].keys()))
    writer.writeheader()
    writer.writerows(all_clean)

with open(CLEAN_DIR / "flagged_for_review.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["Batch", "Company", "Owner Name", "Flags", "Missing After Clean"])
    writer.writeheader()
    writer.writerows(flagged_rows)

total = len(all_clean)
has_name = sum(1 for l in all_clean if l["Owner Name"])
has_li = sum(1 for l in all_clean if l["Owner LinkedIn"])
has_email = sum(1 for l in all_clean if l["Owner Email"])
has_web = sum(1 for l in all_clean if l["Website"])

print(f"\n═══ CLEAN TOTALS (Batches {batches_processed[0]:02d}-{batches_processed[-1]:02d}) ═══")
print(f"Total:       {total}")
print(f"Owner Name:  {has_name} ({100*has_name//total}%)")
print(f"LinkedIn:    {has_li} ({100*has_li//total}%)")
print(f"Website:     {has_web} ({100*has_web//total}%)")
print(f"Email:       {has_email} ({100*has_email//total}%)")

# ═══ Rebuild embedded JSON for enriched_leads.html ═══
leads_json_data = []
for i, row in enumerate(all_clean):
    leads_json_data.append({
        "rank": row["Rank"],
        "name": row["Licensee Name"],
        "units": row["Total Units"],
        "addrs": row["Unique Addresses"],
        "counties": row["Counties"],
        "cities": row["Cities Served"],
        "phone": row["Phone"],
        "score": float(row["Score"]) if row["Score"] else 0,
        "owner": row["Owner Name"],
        "email": row["Owner Email"],
        "linkedin": row["Owner LinkedIn"],
        "website": row["Website"],
        "notes": row["Notes"],
        "batch": (i // 50) + 1,
    })
leads_compact = json.dumps(leads_json_data, separators=(',', ':'))
Path(__file__).parent.joinpath("leads_compact.json").write_text(leads_compact)

# ═══ Update enriched_leads.html ═══
p = Path(__file__).parent / "enriched_leads.html"
html = p.read_text()

# Replace LEADS = [...]
html = re.sub(
    r'const LEADS = \[.*?\];',
    f'const LEADS = {leads_compact};',
    html, count=1, flags=re.DOTALL
)

# Update the H1 count
html = re.sub(
    r'>\d+ Florida Property Managers<',
    f'>{total} Florida Property Managers<',
    html
)

# Update stats bar
html = re.sub(r'<div class="v" id="s-total">\d+</div>', f'<div class="v" id="s-total">{total}</div>', html)
html = re.sub(r'<div class="v fern" id="s-name">\d+</div>', f'<div class="v fern" id="s-name">{has_name}</div>', html)
html = re.sub(r'<div class="v fern" id="s-li">\d+</div>', f'<div class="v fern" id="s-li">{has_li}</div>', html)
html = re.sub(r'<div class="v fern" id="s-web">\d+</div>', f'<div class="v fern" id="s-web">{has_web}</div>', html)
html = re.sub(r'<div class="v fern" id="s-email">\d+</div>', f'<div class="v fern" id="s-email">{has_email}</div>', html)

# Update the "Showing X of Y" placeholder on initial load
html = re.sub(
    r'Showing <span class="hi">\d+</span> of <span class="hi">\d+</span> leads',
    f'Showing <span class="hi">{total}</span> of <span class="hi">{total}</span> leads',
    html
)

# Update the batch filter dropdown: rebuild it to cover all processed batches
# We'll compute each batch's score range from the actual leads
batch_ranges = {}
for b in batches_processed:
    batch_leads = [l for i, l in enumerate(leads_json_data) if l["batch"] == b]
    if batch_leads:
        scores = [l["score"] for l in batch_leads]
        batch_ranges[b] = (min(scores), max(scores))

batch_options = '<option value="">All batches</option>\n'
for b in batches_processed:
    if b in batch_ranges:
        lo, hi = batch_ranges[b]
        batch_options += f'        <option value="{b}">Batch {b:02d} ({int(lo)}–{int(hi)})</option>\n'

html = re.sub(
    r'<select id="f-batch">.*?</select>',
    f'<select id="f-batch">\n        {batch_options.strip()}\n      </select>',
    html, flags=re.DOTALL
)

# Update topbar meta
html = re.sub(
    r'INTERNAL · 25–49 TIER · BATCHES 1–\d+',
    f'INTERNAL · 25–49 TIER · BATCHES 1–{batches_processed[-1]}',
    html
)

p.write_text(html)
print(f"\nUpdated enriched_leads.html ({len(html):,} chars)")

# ═══ Update enrichment_process.html ═══
p2 = Path(__file__).parent / "enrichment_process.html"
proc_html = p2.read_text()

# Hero meta "Enriched:" value
proc_html = re.sub(
    r'(<span class="label">Enriched</span>\s*<span class="value">)\d+',
    rf'\g<1>{total}',
    proc_html
)

# Funnel STAGE 04 & 05 counter targets + widths
pct = int(100 * total / 413)
proc_html = re.sub(
    r'(STAGE 04[\s\S]{1,200}?counter" data-target=")\d+',
    rf'\g<1>{total}',
    proc_html
)
proc_html = re.sub(
    r'(STAGE 05[\s\S]{1,200}?counter" data-target=")\d+',
    rf'\g<1>{total}',
    proc_html
)
proc_html = re.sub(
    r'(STAGE 04[\s\S]{1,400}?--w: )\d+%',
    rf'\g<1>{pct}%',
    proc_html
)
proc_html = re.sub(
    r'(STAGE 05[\s\S]{1,400}?--w: )\d+%',
    rf'\g<1>{pct}%',
    proc_html
)

# Footer labels
proc_html = re.sub(
    r'Batches 1–\d+', f'Batches 1–{batches_processed[-1]}', proc_html
)
proc_html = re.sub(
    r'BATCHES 1–\d+', f'BATCHES 1–{batches_processed[-1]}', proc_html
)

# Update verification copy if present
proc_html = re.sub(
    r'\d+ leads verified across (?:three|four|five|six|seven|eight|nine) batches',
    f'{total} leads verified across {batches_processed[-1]} batches',
    proc_html
)

p2.write_text(proc_html)
print(f"Updated enrichment_process.html ({len(proc_html):,} chars)")

print("\n✓ Both HTML files refreshed")

# ═══ Optional: commit + push to trigger live redeploy ═══
if "--push" in sys.argv:
    import subprocess
    repo_root = Path(__file__).parent.parent  # Enrichments/ repo root

    last_batch = batches_processed[-1] if batches_processed else 0
    msg = f"Refresh: batch_{last_batch:02d} verified · {total} total leads · {has_name}/{has_li}/{has_web} name/LI/web"

    def run(cmd, cwd=repo_root):
        print(f"  $ {' '.join(cmd)}")
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  ⚠ {r.stderr.strip()}")
            return False
        if r.stdout.strip():
            print(f"  {r.stdout.strip()[:200]}")
        return True

    print("\n═══ Pushing to GitHub ═══")
    run(["git", "add", "-A"])
    # Check if there's anything to commit
    diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=repo_root)
    if diff_check.returncode == 0:
        print("  Nothing to commit.")
    else:
        if run(["git", "commit", "-m", msg]):
            if run(["git", "push"]):
                print("  ✓ Pushed — deploy should fire within 1–3 min")
