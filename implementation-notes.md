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

## Progress (round 4: GitHub hosting)

- [x] Git initialized, connected to `github.com/thawk238/CCDivBets` (confirmed public; user opted to keep it public)
- [x] `.gitignore` (excludes `site/` -- build output, not source), `requirements.txt`
- [x] `.github/workflows/weekly-update.yml` -- Tuesday 13:00 UTC cron (~9AM ET, drifts an hour after DST ends in Nov) + manual `workflow_dispatch`; runs the pipeline, commits `data/` back, deploys `site/` to GitHub Pages
- [x] Pushed, manually triggered once to verify -- caught and fixed a real bug (see Deviations): the deploy only ever included `index.html`, so `preseason.html`/`reports.html`/`reports/week-01.html` 404'd live even though they worked locally
- [x] Live at `https://thawk238.github.io/CCDivBets/`, confirmed all pages load post-fix

## Progress (round 5: Rules & Scoring section + points-by-week chart)

- [x] "Rules & Scoring" section added to the bottom of `index.html.j2` (mirrors the README)
- [x] `scripts/_common.py`: `CHART_PALETTE` + `bettor_colors()` -- data-viz skill's validated categorical palette (7 slots), checked with `validate_palette.js --mode dark --surface #131a2b` (the site's actual card color, not the skill's default dark surface) -- all checks passed
- [x] `generate_site.py` now assigns each bettor a stable color (by file order, not by rank -- color always means the same person even as the leaderboard reshuffles) and passes `chart_series` to the template
- [x] Hand-rolled inline SVG line chart in `index.html.j2` (no charting library, consistent with the rest of the site's zero-external-JS-dependency approach): gridlines, y-axis ticks, 2px rounded lines, end-dot markers with surface-color ring, a line-key legend, and a hover crosshair + tooltip listing every bettor's value at the hovered week, sorted by value
- [x] Chart only renders when `history_weeks|length >= 2`, per the request ("once we get to week 2") -- verified hidden at 1 week, then verified it actually renders and the tooltip/crosshair work using a temporary synthetic 2nd week (`data/scores/2026-wk02-TEST.json`, deleted before committing -- never part of history)

## Deviations

- **Found:** `run_weekly.py` only ever called `generate_site.py`, never
  `generate_preseason.py` / `generate_week_report.py` / `generate_reports_hub.py`.
  This worked locally by accident, because I'd run those other generators
  by hand earlier in the session and the output sat in the (gitignored)
  local `site/` folder. The Action's deploy starts from a clean checkout
  and only builds what the pipeline script actually runs, so it uploaded
  an `index.html`-only site -- the other three pages 404'd live on first
  deploy. **Chose:** made `generate_week_report.py` support `--all` (render
  every week with a write-up, not just the latest), and made
  `run_weekly.py` always rebuild the entire site -- index, preseason,
  every existing week report, and the hub -- every run. **Why:** a Pages
  deploy replaces the whole folder each time, so "only regenerate what
  changed" is the wrong mental model here; everything with committed
  source data has to be rebuilt every run or it silently disappears.
  Caught by actually checking the live deployed URLs, not just the local
  build.

- **Found:** after the Action's first run committed a fresh scrape back to
  `main`, my next local `git push` was rejected (diverged history), and
  rebasing hit a real conflict on `data/standings/2026-wk01.json` /
  `data/scores/2026-wk01.json` -- both the Action and a local test run had
  re-scraped the same live data minutes apart. **Chose:** kept the Action's
  (remote) version of both files during the rebase, since it's the
  authoritative automated run. **Why/how to apply:** this will recur any
  time a local pipeline run and the Action both touch `data/standings/` or
  `data/scores/` around the same time -- `git fetch` before running the
  pipeline locally once the Action is live, to avoid the conflict rather
  than resolve it after the fact.

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
