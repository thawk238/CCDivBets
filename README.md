# Sunday Best Divisional Pool

A file-based NFL divisional standings prediction pool for 7 bettors. Everyone picked a
1st-through-4th finish order for all 8 NFL divisions before the season started. Picks are
locked and never change; only the real Yahoo Sports standings move week to week. This repo
scores everyone against those standings, keeps a full history, and publishes a static site.

**Live site:** https://thawk238.github.io/CCDivBets/

## Rules & scoring

**The pick:** Before the season, each bettor picks a 1st-through-4th finish order for all
8 NFL divisions. Locked in -- no changes once the season starts.

**Scoring (per division):**

| Rule | Points |
|---|---|
| Exact position (1-4) correct | +3 per team |
| Perfect division (all 4 exact) | +8 bonus |
| Top-2 in exact order | +3 bonus |
| Bottom-2 in exact order | +2 bonus |

Division max: 4×3 + 8 + 3 + 2 = **25**. Season max (8 divisions): 8×25 = **200**.

**Tiebreakers, in order:**

1. Most perfect divisions
2. Most top-2-in-order bonuses
3. Most bottom-2-in-order bonuses
4. Most total exact hits (out of 32)
5. Closest guess to a designated week's total points (`data/tiebreaker.json` -- not set up yet)
6. Coin flip

Standings are based on Yahoo Sports' real NFL division standings, updated weekly.

## Project layout

```
data/
  divisions.json          # canonical: 8 divisions, 32 teams, colors, Yahoo's naming
  bettors.json             # the 7 names, ids bettor-1..bettor-7
  picks.json                # LOCKED once entered: everyone's 1-4 order per division
  tiebreaker.json            # inert until a week + guesses are set
  standings/<season>-wkNN.json   # one dated snapshot per week, scraped from Yahoo
  scores/<season>-wkNN.json      # derived: computed points per bettor per week
  preseason_facts.json      # deterministic stats about the picks (locks, variation, etc.)
  preseason_writeup.json     # the actual preseason commentary (hand-written)
  weekly_facts/<season>-wkNN.json    # deterministic stats about that week's results
  weekly_writeups/<season>-wkNN.json # that week's commentary (hand-written)

scripts/            # see "Weekly workflow" below
templates/*.html.j2  # Jinja2 templates for every page, "Blitz" visual style
assets/logos/         # real team logos (ESPN's public CDN, downloaded once)
site/                 # generated output -- gitignored, rebuilt every run
.github/workflows/weekly-update.yml   # Tuesday cron automation
```

## Running it locally

```
pip install -r requirements.txt
python scripts/run_weekly.py
```

This scrapes current Yahoo standings, computes scores, and rebuilds the entire `site/`
folder (leaderboard, preseason report, every week's analysis that has a write-up, and the
reports hub). Open `site/index.html` in a browser to check it.

If Yahoo's page fails to parse correctly, the scraper refuses to publish -- it writes a
`data/standings/<week>.pending-review.json` for you to inspect instead of overwriting good
data with bad. Nothing downstream runs until that's resolved.

## Weekly workflow

Every Tuesday, `.github/workflows/weekly-update.yml` runs automatically (~9 AM Eastern,
drifts an hour once daylight saving ends in November -- see the comment in that file) and:

1. Scrapes Yahoo, computes scores, rebuilds the leaderboard
2. Computes that week's fun-facts stats (`data/weekly_facts/`)
3. Commits the updated `data/` files back to the repo
4. Deploys the rebuilt `site/` to GitHub Pages

**What it does NOT do:** write that week's analysis commentary. That's a deliberate manual
step -- ask Claude (or write it yourself) using the fresh stats in `data/weekly_facts/`,
save it to `data/weekly_writeups/<season>-wkNN.json` (same shape as an existing week), then:

```
python scripts/generate_week_report.py --all
python scripts/generate_reports_hub.py
git add data/weekly_writeups site
git commit -m "Week N analysis"
git push
```

(Only `data/` needs pushing for the *next* automated run to have it; `site/` is gitignored
and only matters if you're checking it locally -- the Action rebuilds and deploys it fresh
from `data/` either way.)

## Entering or changing picks

```
python scripts/entry_form.py
```

Opens a local form at `http://localhost:8765/` pre-filled with the current picks. Duplicate
teams within a division are caught and highlighted before you can save. Saving overwrites
`data/bettors.json` and `data/picks.json` directly -- commit and push those afterward the
same as any other data change.

## Repo/hosting notes

- The repo is public by choice (names and picks, no financial info beyond who owes $20).
- GitHub Pages is configured to deploy from GitHub Actions (Settings → Pages → Source), and
  the workflow needs "Read and write permissions" under Settings → Actions → General so it
  can commit data back to the repo.
- `run_weekly.py` always rebuilds the *entire* site, not just what changed -- a Pages deploy
  replaces the whole folder each run, so anything not rebuilt would vanish from the live
  site even though its source data is still sitting in `data/`.
- If you run the pipeline locally around the same time the Action runs, `git fetch` first --
  both write to `data/standings/` and `data/scores/`, and a conflict there is a real
  possibility (see `implementation-notes.md` for what happened the first time).

## Team logos

Real logos live in `assets/logos/`, downloaded once via `python scripts/fetch_logos.py`
from ESPN's public team-logo CDN and committed to the repo (not hotlinked at request time).
Non-commercial private-pool use.
