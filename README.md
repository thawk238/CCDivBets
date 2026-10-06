# Sunday Best Divisional Pool

An NFL division-standings prediction pool for 7 bettors. Before the season, everyone picked
a 1st-through-4th finish order for all 8 divisions. Picks are locked; only the real Yahoo
Sports standings move. This repo scores everyone against those standings each week, keeps
the full history, and publishes a static site.

**Live site:** https://thawk238.github.io/CCDivBets/

---

## Every week (the 2-minute checklist)

Run this any time after Monday Night Football finishes (usually Tuesday).

1. **Update the standings.** GitHub → **Actions** → **Weekly Update** → **Run workflow**
   (branch `main`). Takes about a minute. This scrapes Yahoo, rescores everyone, commits
   the new `data/` files, and redeploys the live site.
2. **Write the week's analysis.** Ask Claude: *"write the Week N analysis"*. The commentary
   is written from the stats the run just produced (`data/weekly_facts/<season>-wkNN.json`)
   and saved to `data/weekly_writeups/<season>-wkNN.json`, then pushed.
3. **Publish the analysis.** Click **Run workflow** once more so the live site picks up the
   new write-up.
4. **Spot-check** the live leaderboard and `reports.html`.

The workflow is **manual only** — there is no schedule. If nobody clicks the button, the
site doesn't update. (The old Tuesday cron was removed because GitHub fired it 4–5 hours
late.)

---

## Rules & scoring

**The pick:** each bettor picks a 1–4 finish order for all 8 divisions before the season.
No changes once the season starts.

**Scoring (per division):**

| Rule | Points |
|---|---|
| Exact position (1–4) correct | +3 per team |
| Perfect division (all 4 exact) | +8 bonus |
| Top-2 in exact order | +3 bonus |
| Bottom-2 in exact order | +2 bonus |

Division max: 4×3 + 8 + 3 + 2 = **25**. Season max (8 divisions): **200**.

**Tiebreakers, in order:**

1. Most perfect divisions
2. Most top-2-in-order bonuses
3. Most bottom-2-in-order bonuses
4. Most total exact hits (out of 32)
5. Closest guess to a designated week's total points — `data/tiebreaker.json`
   (**not set up yet**; needs a week + everyone's guesses before season's end)
6. Coin flip

---

## Running it locally

Requires Python 3.12 (the version the GitHub workflow uses).

```
pip install -r requirements.txt
python scripts/run_weekly.py
```

This scrapes current Yahoo standings, computes scores and weekly stats, and rebuilds the
whole `site/` folder. Open `site/index.html` (or `site/reports/week-NN.html`) in a browser
to check it.

Running locally does **not** update the live site — only the GitHub workflow deploys. If
you run locally, commit and push `data/` and then run the workflow. Do `git pull` first so
you don't conflict with the bot's commits to `data/standings/` and `data/scores/`.

**After editing a write-up**, rebuild just the report pages:

```
python scripts/generate_week_report.py --all
python scripts/generate_reports_hub.py
```

### Safety checks

- **Bad scrape:** if Yahoo's page doesn't validate (8 divisions, 4 known teams each), the
  scraper refuses to publish and writes `data/standings/<week>.pending-review.json` instead.
  Nothing downstream runs until that's resolved.
- **Wrong week number:** the week is auto-computed from `SEASON_START` in
  `scripts/scrape_standings.py` (2026-09-10). To force it, use
  `python scripts/scrape_standings.py --week N` and `python scripts/compute_scores.py --week N`.
  Sanity check: every team's W+L+T should equal the week number.

---

## Entering or changing picks

```
python scripts/entry_form.py
```

Opens a local form at `http://localhost:8765/` pre-filled with the current picks. Duplicate
teams within a division are flagged before saving. Saving overwrites `data/bettors.json` and
`data/picks.json` — commit and push those afterward.

---

## Project layout

```
data/
  divisions.json                     # 8 divisions, 32 teams, colors, Yahoo naming
  bettors.json                       # the 7 names (bettor-1..bettor-7)
  picks.json                         # LOCKED: everyone's 1–4 order per division
  tiebreaker.json                    # tiebreaker #5 -- inert until set up
  standings/<season>-wkNN.json       # weekly Yahoo snapshot
  scores/<season>-wkNN.json          # derived points per bettor per week
  weekly_facts/<season>-wkNN.json    # derived stats for that week's analysis
  weekly_writeups/<season>-wkNN.json # that week's commentary (hand-written)
  preseason_facts.json / preseason_writeup.json   # one-time preseason report

scripts/
  run_weekly.py            # entrypoint: scrape -> score -> analyze -> rebuild site/
  scrape_standings.py      # Yahoo standings (JSON-LD) with validation gate
  compute_scores.py        # scoring + tiebreakers
  analyze_week.py          # weekly stats (deltas, gaps, locks, division-winner hopes)
  generate_*.py            # one per page: site, preseason, week reports, reports hub
  entry_form.py            # local pick-entry form
  fetch_logos.py           # one-time logo download
  _common.py               # shared helpers (ranking with ties, colors, asset sync)

templates/*.html.j2        # Jinja2 templates for every page ("Blitz" style)
assets/logos/              # team logos, committed (ESPN public CDN, downloaded once)
site/                      # generated output -- gitignored, rebuilt every run
.github/workflows/weekly-update.yml   # the manual weekly workflow
implementation-notes.md    # build log + every design deviation and why
```

---

## Hosting notes

- The repo is **public** by choice (names and picks only).
- GitHub Pages deploys from GitHub Actions (Settings → Pages → Source). The workflow needs
  "Read and write permissions" (Settings → Actions → General) to commit `data/` back.
- Every run rebuilds the **entire** site, not just what changed. A Pages deploy replaces
  the whole folder, so any page not rebuilt would disappear from the live site.

## Backups

- **Primary:** GitHub (`thawk238/CCDivBets`). Everything that matters lives in `data/`,
  which is committed every run; `site/` can always be regenerated from it.
- **Local snapshots:** zipped copies of the whole folder (including git history) in
  `C:\aa\VibeCoding\Backups\`, named `NFLDivBets-YYYY-MM-DD.zip`.

## Team logos

Real logos in `assets/logos/`, downloaded once via `python scripts/fetch_logos.py` from
ESPN's public team-logo CDN and committed (not hotlinked). Non-commercial private-pool use.
