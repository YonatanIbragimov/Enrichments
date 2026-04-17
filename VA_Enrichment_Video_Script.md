# Video Script — How to Enrich One Lead

**Target runtime:** ~4 minutes
**Format:** Screen recording + voiceover
**Tools visible on screen:** Google Sheets, Sunbiz, Google, DuckDuckGo, Apollo.io

Read the **SAY** lines aloud. The **SCREEN** lines are your cue for what to show or click next. Pause between scenes — don't try to talk and click at the same time on the first take.

---

## 0:00 · Cold open (~15s)

**SCREEN:** Your batch CSV open in Google Sheets, zoomed in on one blank row.

**SAY:**
> Hey — quick walkthrough of how to fill one row of the enrichment batch. We're looking for four things: owner name, website, LinkedIn, and email. Every row takes about three or four minutes. Let's do one together.

---

## 0:15 · What you start with (~15s)

**SCREEN:** Point at the row — highlight `Licensee Name`, `Total Units`, `Counties`.

**SAY:**
> Here's the row. The first eight columns are already filled — that's the source data from the state. Our job is to fill in the last five columns on the right: Owner Name, Email, LinkedIn, Website, and Notes.

---

## 0:30 · Step 1 — Sunbiz for Owner Name (~45s)

**SCREEN:** Open a new tab → `search.sunbiz.org` → select "Search by Name".

**SAY:**
> Step one — Sunbiz. This is Florida's business registry, and it's where we get the owner's name.

**SCREEN:** Copy the Licensee Name. Paste into Sunbiz search — **delete the suffix** (LLC, Inc, Corp).

**SAY:**
> Copy the licensee name, but before you paste — strip off the LLC, Inc, or Corp. Sunbiz is picky about suffixes. Hit search.

**SCREEN:** Click the best-matching result.

**SAY:**
> Pick the result whose name matches closest. If there's an inactive one and an active one, always pick active.

**SCREEN:** Scroll to "Officer/Director Detail" or "Authorized Person(s) Detail". Highlight the title column.

**SAY:**
> Scroll down to the officers section. Pick the first officer using this priority: CEO, president, owner, manager, principal, member. If none of those exist, use the registered agent instead.

**SCREEN:** Copy name → paste into Owner Name cell.

**SAY:**
> Drop the name into the Owner Name column. That's step one. Hit rate here is basically a hundred percent.

---

## 1:15 · Step 2 — Google for Website (~40s)

**SCREEN:** New tab → google.com.

**SAY:**
> Step two — Google, looking for the company website.

**SCREEN:** Type the search, showing quotes around the company name:
`"[Company Name]" Florida vacation rental property management`

**SAY:**
> Put the company name in quotes, then add "Florida vacation rental property management". Quotes keep Google honest.

**SCREEN:** Scroll through top 5 results. Cross out LinkedIn, Facebook, Airbnb, VRBO, any .gov site.

**SAY:**
> Skip LinkedIn, Facebook, Airbnb, VRBO, and any dot-gov site. The first real company website you see — that's the one.

**SCREEN:** Click through → confirm site loads and mentions the company. Copy URL → paste into Website cell.

**SAY:**
> Click through to confirm it actually loads and the company name is on the homepage. If it does, paste the URL. If it's broken or unrelated, leave it blank and move on.

---

## 1:55 · Step 3 — DuckDuckGo for LinkedIn (~40s)

**SCREEN:** New tab → duckduckgo.com.

**SAY:**
> Step three — LinkedIn. We use DuckDuckGo instead of Google here, because Google blocks LinkedIn searches after about ten of them.

**SCREEN:** Type: `site:linkedin.com/in/ "[Owner Name]" Florida`

**SAY:**
> Search for `site:linkedin.com/in/`, then the owner's name in quotes, plus Florida.

**SCREEN:** Click the first `linkedin.com/in/…` result.

**SAY:**
> Click the first LinkedIn-dot-com-slash-in result. LinkedIn will probably hit you with a login wall — that's fine.

**SCREEN:** Zoom on the URL bar. Point at the slug: `/in/jane-smith-a12b3c`.

**SAY:**
> Look at the URL. The slug — the "jane-smith" part — should match the owner name from Sunbiz. First name OR last name match is enough. If it matches, paste the URL. If not, leave it blank. A wrong LinkedIn is worse than a missing one.

---

## 2:35 · Step 4 — DuckDuckGo for Email (~25s)

**SCREEN:** Same DuckDuckGo tab.

**SAY:**
> Step four — email. Honest heads-up: this one usually finds nothing. Don't spend more than two minutes on it.

**SCREEN:** Type: `"[Owner Name]" "[Company Name]" email`

**SAY:**
> Search the owner name and company name in quotes, plus the word "email". Scan the result snippets for anything that looks like `name at domain dot com`.

**SCREEN:** If found, copy → paste. Otherwise leave blank.

**SAY:**
> If you find one, paste it in. If not, move on. We'll come back for the misses in the last step.

---

## 3:00 · Step 5 — Apollo for the gaps (~40s)

**SCREEN:** Switch view to Google Sheets. Filter for rows where LinkedIn or Email is blank.

**SAY:**
> Step five — Apollo. Do this at the end of the batch, not per row. Filter the sheet for rows that are still missing LinkedIn or email.

**SCREEN:** Open apollo.io → People search → Company filter = company name or domain → Location = Florida.

**SAY:**
> In Apollo, search People. Put the company name — or better, the website domain — in the Company filter, and set Location to Florida.

**SCREEN:** Find the person whose name matches. Click through.

**SAY:**
> Find the person whose name matches Sunbiz. First or last name match. If two people match, pick the one with the most senior title.

**SCREEN:** Click "Access Email". Copy email → paste. Copy LinkedIn URL → paste. Add "Apollo" to Notes.

**SAY:**
> Click Access Email. Copy it into the Email column. Grab the LinkedIn URL from their profile. And always tag the Notes column with the word "Apollo" — that way we know which rows came from paid data.

---

## 3:40 · Wrap (~20s)

**SCREEN:** Finished row — all five columns filled.

**SAY:**
> And that's it. Five steps, four data points, usually three to four minutes per row. The full written version of this — with edge cases, troubleshooting, and the batch template CSV — is on the site, linked in the description. If anything breaks or you're not sure about a match, flag it in Notes and move on. When in doubt, leave it blank.

---

## Script notes (not for camera)

- If you fumble a line, pause 2 seconds and restart the sentence — easier to cut cleanly in post.
- For best audio: read the SAY lines in your normal conversational voice, not "announcer" voice.
- Zoom in for URL slugs and search queries — those are small on a 1080p recording.
- Rough word count: **~540 words** → about 3:40 at a relaxed 150 wpm.
- If you're over 4 minutes, drop the 0:15 "what you start with" scene first.
