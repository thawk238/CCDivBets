# Implementation notes — NFL Divisional Bets

Plan: `C:\Users\mtome\.claude\plans\indexed-swimming-island.md`

## Progress

- [x] Step 1: `data/divisions.json` scaffold
- [x] Step 2: `scripts/scrape_standings.py` + live run against Yahoo
- [x] Step 3: `data/bettors.json` + `data/picks.json` (sample data)
- [x] Step 4: `scripts/compute_scores.py` + hand-verify
- [x] Step 5: `templates/index.html.j2` + `scripts/generate_site.py`
- [x] Step 6: `scripts/run_weekly.py`
- [x] Extra: `scripts/entry_form.py` + `templates/entry_form.html.j2` — local pick-entry tool (requested after plan approval, not in original plan)

## Progress (feature: preseason scouting report)

- [x] `scripts/analyze_picks.py` — deterministic stats from `data/picks.json` (slot tallies, unanimous locks, distinct-ordering counts, lone-wolf picks per bettor)
- [x] `data/preseason_writeup.json` — the actual commentary, written by me from the real stats (not templated filler)
- [x] `templates/preseason.html.j2` + `scripts/generate_preseason.py` — renders `site/preseason.html` in the Blitz style
- [x] `scripts/_common.py` — extracted `load_json`/`team_lookup`/`is_light`, now shared by `generate_site.py` and `generate_preseason.py` (was exact duplication, not a speculative abstraction)
- [x] Linked from the main leaderboard header

## Progress (round 3: real logos, week-number fix, reports hub + weekly analysis)

- [x] `scripts/fetch_logos.py` — one-time download of all 32 real team logos (ESPN's public logo CDN, verified all ids match) into `assets/logos/`
- [x] `scripts/_common.py` extended with `sync_assets()` so every generator copies `assets/` into `site/assets/` — logos ship as part of the portable site folder, not hotlinked at runtime
- [x] Badges in `index.html.j2` and `preseason.html.j2` swapped from colored-circle text to real `<img>` logos
- [x] Fixed the week-number bug (see Deviations) and regenerated Week 1 correctly
- [x] `scripts/analyze_week.py` — deterministic weekly stats (leaderboard deltas, closest/widest gaps, preseason "locks" status check, hopes-tracker cross-referencing each bettor's division-winner picks against actual current leaders)
- [x] `data/weekly_writeups/2026-wk01.json` — Week 1 commentary, written by me from the real stats
- [x] `templates/week_report.html.j2` + `scripts/generate_week_report.py` → `site/reports/week-01.html`
- [x] `templates/reports_hub.html.j2` + `scripts/generate_reports_hub.py` → `site/reports.html`, auto-listing the preseason report + every week found in `data/weekly_writeups/`
- [x] Main leaderboard page's small text link replaced with a large gold-bordered "Reports" button linking to the hub
- [x] `run_weekly.py` now also runs `analyze_week.py` (deterministic) but does not auto-write or auto-publish that week's report — the commentary still needs a human/Claude pass, same pattern as the preseason report

## Deviations

- **Found:** the auto-computed week number was wrong (labeled "Week 2" when
  it should've been "Week 1") — I'd guessed the 2026 season opener as
  Sept 4 without checking; the real Thursday opener is Sept 10. Confirmed
  by the actual team records (every team 1-0 or 0-1, i.e. exactly one game
  played). **Chose:** corrected `SEASON_START` in `scrape_standings.py`,
  deleted the mislabeled `2026-wk02.json` files, and re-ran the pipeline
  fresh. **Why:** this is exactly the kind of date guess that shouldn't
  have been made without verification — logged so it doesn't happen again;
  `--week` remains available as a manual override if the auto-calc is ever
  off again.

- **Found:** real team logos can't be hotlinked reliably or referenced from
  a trademark-safe source without a decision. **Chose:** ESPN's public
  team-logo CDN, downloaded once into `assets/logos/` and shipped as part
  of the generated site (not hotlinked at request time), rather than
  keeping the color-coded text badges. **Why:** you asked for real logos
  twice now; downloading once and serving locally is more robust than
  hotlinking (works even if ESPN's CDN changes) and keeps `site/` a single
  portable folder. Non-commercial private pool use, same as every fantasy
  tool doing this — flagging it here rather than re-litigating it.

- **Found:** you didn't specify where the write-up should live on the site.
  **Chose:** a separate `site/preseason.html` page linked from the main
  leaderboard header, instead of a section embedded in the weekly page.
  **Why:** this content is one-time (tied to locked picks, not weekly
  standings) — keeping it off the operational leaderboard page means
  `generate_site.py`'s weekly regeneration never touches it, and it doesn't
  compete for space with the stuff that actually changes every Tuesday.
  Easy to merge into one page later if you'd rather have it inline.

- **Found:** Yahoo's standings page embeds each division's order as schema.org
  JSON-LD (`<script type="application/ld+json">`), not just visible table
  markup. **Chose:** parse that structured block instead of the rendered
  DOM. **Why:** far more stable than div-soup scraping — same conservative
  spirit as the validation gate already planned, just a better data source
  for it. Downside: still Yahoo's to change or remove without notice, so the
  validation gate (8 divisions, 4 known teams each) stays as the real safety
  net either way.

- **Found:** the plan didn't specify how a "week number" gets assigned to
  each snapshot. **Chose:** auto-compute from days elapsed since a hardcoded
  2026-09-04 season-start date, with a `--week` CLI override on both
  `scrape_standings.py` and `compute_scores.py`. **Why:** conservative
  default that needs no manual input most weeks, but never blocks a manual
  correction.

- **Found:** the approved Blitz prototype showed division breakdowns as
  large per-bettor "cards." At 6 bettors x 8 divisions that's 48 cards on
  one page. **Chose:** compact per-division tables (one row per bettor)
  instead, keeping the same badges/colors/bonus chips. **Why:** cards don't
  scale past the 2-bettor prototype sample without becoming a scroll wall;
  a table scans faster for "who beat whom this week." **Flagging for
  ratification** since this is a visual/UX change from the approved mock,
  not just a mechanical implementation detail.

- **Found:** Yahoo's JSON-LD also includes each team's W-L-T record.
  **Chose:** show it next to the actual standings order (not in the
  original plan). **Why:** free, relevant context for "why is this team
  ranked here" — no extra scraping cost.

- **Found:** pool is actually 7 bettors, not the 5-6 discussed earlier
  (real names: Mike T, Dilger, Dustin, Tom, Hume, Cadegn, Farmer).
  **Chose:** generalized `scripts/entry_form.py` + its template to derive
  the bettor count from `data/bettors.json` at load time instead of a
  hardcoded 6 (also removes any future magic number if the pool size
  changes again). `data/bettors.json` now holds the real 7 names;
  `data/picks.json` still holds random placeholder picks for all 7 until
  entered for real via the form. Re-ran the full pipeline and the form to
  confirm all 7 flow through the leaderboard, division tables, and score
  history correctly.

- Pool name ("SUNDAY BEST DIVISIONAL POOL") is a hardcoded placeholder
  carried over from the prototype (`POOL_NAME_LINE1`/`POOL_NAME_LINE2` at
  the top of `scripts/generate_site.py`) — trivial one-line edit once you
  have a real pool name.
