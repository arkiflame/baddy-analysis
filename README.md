# badminton-tactics

A badminton **tactical analyzer**: it finds the rally patterns that win and lose points for a
player, the kind of insight a coach gives, rather than shot counts. It works on 94 professional
singles matches (ShuttleSet + ShuttleSet22, 81,939 annotated strokes) and produces a per-player
Markdown report whose claims compare the player with every other pro in the same situation,
carry sample sizes and confidence intervals, and are re-tested on matches that were not used to
find them.

Perception (shuttle tracking, shot classification) is reused from open-source work with credit;
the effort here goes into the tactics layer.

## What it does today

```
uv run python -m tactics players                             # coverage per player
uv run python -m tactics report --player "Viktor AXELSEN"    # -> outputs/Viktor_AXELSEN.md (+ PNGs)
uv run python -m tactics evaluate --player "Viktor AXELSEN"  # holdout / leave-one-match-out / leave-one-opponent-out
uv run python -m tactics zones-check                         # evidence behind the zone thresholds
```

A report (example: [docs/examples/Viktor_AXELSEN.md](docs/examples/Viktor_AXELSEN.md)) contains:

- **Top insights**: the shot-and-zone situations where the player differs most from typical
  pros, ranked by the smallest difference the data still supports, kept only if the same
  pattern is selected in at least half of the leave-one-match-out folds ("stable in 15 of 20
  folds" is printed next to each), and flagged `tentative` when the interval on the difference
  is wider than 20 points or n is under 60.
- **How to play against the player** and **what the player should fix**, in coach language.
- **The evidence**: every danger table (P(point lost within two shots | shot type x zone), for
  shots faced and shots played) with the typical-pro rate and the difference's 95% interval.
- **Position maps** (positions at hit time only): heatmaps on a court drawn to scale, base
  position, how far each opponent shot pulls the player from it, distance per rally as a lower bound.
- **Habits and set plays**: replies chosen more often than typical pros in the same situation,
  the most predictable situations (entropy), distinctive openings with their win rates.
- **Expected points (xP)**: a negative result, stated first. xP from shot and position data
  has no signal mid-rally in elite singles (holdout AUC 0.50); the same features only classify
  how an already-decisive stroke ends (AUC 0.79). The section shows what that does to per-shot
  claims and keeps a finishing table, the one place the number is an execution measure.
- **Context**: how points end, the setups before the decisive stroke, rally length and splits.

Zones are computed from the **receiver's** point of view with a per-player handedness table, so
"rear backhand" means the receiver's backhand corner. Every threshold lives in `config/zones.toml`.

## Web UI (Milestone 4a)

`web/` is a statically exported Next.js site (App Router, TypeScript, Tailwind) that renders the
same reports for every player with at least 3 matches: a searchable player list, a player page
(scouting summary on top, tabs for insights, habits, set plays, position maps and xP), an
interactive SVG court drawn to scale with the seven coach zones coloured by the player-vs-typical-pro
difference and hover / keyboard tooltips with n and the 95% interval, and a Methods page. The site
computes nothing: every number comes from JSON written by `scripts/export_web.py`, which calls the
same functions as the Markdown report. Tentative and less-stable insights are marked, every rate
carries its n and interval, light and dark mode, responsive to phone width, no meaning carried by
colour alone (D28).

```powershell
uv run python scripts/export_web.py          # -> web/public/data/index.json + players/*.json (about 20 min)
cd web
npm install
npm run dev                                   # http://localhost:3000
npm run build                                 # static site in web/out
```

### Deploying to Vercel

1. Make sure `web/public/data/` is committed (the export is not run on Vercel: it needs the dataset
   and about 20 minutes). Re-run `scripts/export_web.py` and commit whenever the analysis changes.
2. On vercel.com, **Add New Project**, import this repository, and set **Root Directory** to `web`.
   Framework preset: Next.js (detected). Build command `npm run build`, output directory `out`
   (the `output: "export"` setting in `web/next.config.ts` makes the build static; Vercel serves
   `out/` as plain files). No environment variables are needed.
3. Deploy. Every push to the production branch rebuilds; preview deployments are created for other
   branches. The site has no server component at runtime, so it can equally be hosted on GitHub
   Pages or any static host by uploading `web/out/`.

## Results (all numbers from commands in this repo, 2026-11-04)

**Viktor Axelsen** (20 matches, 1,394 rallies, 58.1% rally win rate), `python -m tactics report --player "Viktor AXELSEN"`:

1. Opponents' shots to his body: he loses within two shots 7% of the time (n=97, 95% CI 4-14%); typical pros lose 20% (difference -13 points, CI -18 to -5).
2. Opponents' net shots to his front forehand: 7% (n=751) vs 14% (-7, CI -8 to -4).
3. Opponents' smashes to his mid forehand: 16% (n=472) vs 23% (-7, CI -11 to -4).
4. In game 3, opponents' clears: 24% (n=46) vs 11% (+13, CI +3 to +28).
5. Anything he plays to the opponent's mid forehand: 6% (n=1,342) vs 10% (-4, CI -5 to -2).

The one weakness that survives the tests at all game stages: pushes and rushes to his rear
backhand, 35% (n=81) vs 23% for typical pros (+11, CI +2 to +23).

| Feature | Verified result |
|---|---|
| Replication, 5 players x 5 insights (`docs/EVALUATION.md`), verdicts REPLICATES / SAME DIRECTION / FAILS / UNTESTABLE | holdout (1-3 matches per player): 1 / 8 / 6 / 10; leave-one-match-out: 8 / 16 / 1 / 0; leave-one-opponent-out: 7 / 13 / 2 / 3. The holdout's 1-3 matches cannot resolve the 4-13 point differences the insights are made of, so its 1 strict replicate and 6 fails are reported next to the two leave-one-out schemes, not instead of them |
| Threshold sensitivity (`outputs/sensitivity.md`) | front/mid at 2.5 m keeps 22 of 25 top-5 insights; body radius 0.75 m keeps 16 of 25 |
| Position maps (Axelsen) | base position 3.82 m from the net; pulled 1.22 m from base by pushes vs 1.62 m for typical pros (-0.39, CI -0.47 to -0.32); 1.58 m per own stroke vs 1.70 m |
| Habits (Axelsen) | smashes 75% of clears to his rear backhand vs 37% for typical pros (+38, CI +31 to +44); reply entropy there 2.18 bits vs 3.11 for typical pros at the same n; opens short serve > net > lob in 32% of service rallies vs 19% |
| xP (`docs/XP.md`) | **negative result**: xP from shot and position data has no signal mid-rally (holdout AUC 0.50 on non-final strokes, both feature sets, both model families); 0.79 only when classifying how an already-decisive stroke ends; leak check with the final zone visible 0.986; finishing table: Axelsen's final smashes are winners 10 points more often than typical pros' (+0.104, CI +0.039 to +0.168) |
| Live advantage experiment (`docs/M3_BASELINE.md`) | FAIL: best live-prefix AUC 0.498 vs the 0.60 bar; no bar built |
| M3 baseline (`docs/M3_BASELINE.md`) | live AUC 0.50-0.52; pre-final logistic AUC 0.730; full rally with the final zone masked GRU AUC 0.815 |
| Shuttle tracking (M2 tooling) | TrackNetV3 wrapper detects a synthetic shuttle in 28 of 48 frames, median error 2.4 px |

Two negative results are part of the deliverable. xP from shot and position data has no signal
mid-rally in elite singles (holdout AUC 0.50), and a rally in progress does not reveal its winner
to a sequence model either, with or without position and movement features (AUC 0.50 against a
0.60 pass bar set in advance). Both are documented with the commands that show it.

## Setup

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/), git. GPU optional (M3 and tracking
use it when present; xP runs on the CPU in seconds).

```powershell
uv sync --extra dev                         # core: pandas, numpy, scipy, matplotlib
uv run python scripts/fetch_shuttleset.py   # ShuttleSet + ShuttleSet22 -> data/raw/ (MIT)
uv run pytest                               # 72 tests
# optional
uv sync --extra dev --extra m3 --extra video   # torch (CUDA 12.8 wheels), scikit-learn, opencv
uv run python scripts/fetch_tracknetv3.py      # TrackNetV3 source + weights (MIT, checksummed)
uv run python scripts/xp_baseline.py           # xP models, holdout metrics, calibration plot
uv run python scripts/m3_baseline.py           # rally-outcome sequence models
uv run python scripts/live_state.py            # live advantage experiment
uv run python scripts/threshold_sensitivity.py # top-5 under alternative zone thresholds
```

## Layout

```
src/tactics/
  loader.py      ShuttleSet CSVs -> Match/Game/Rally/Stroke + flat table (projection, sides, scores)
  court.py       pixel -> metre projection, player-relative frames
  zones.py       receiver-relative coach zones, fine grid, movement features
  stats.py       Wilson CI, Newcombe CI on a difference, rate tables, t / Welch intervals
  analyses.py    per-player analyses + the same for all other players (typical pros)
  report.py      top-5, coach sections, tables, heatmaps
  positions.py   position maps          habits.py       habits, entropy, set plays
  xp.py          expected points        live_state.py   live advantage experiment
  evaluation.py  three replication schemes            splits.py   match-level holdout ids
  outcome_model.py  M3 sequence models  cli.py          the four commands
  webexport.py   JSON for the web UI (same functions as the report)
  tools/         court calibration, video labeller, TrackNetV3 wrapper (M2)
config/          zones.toml (thresholds), players.toml (handedness with sources)
scripts/         fetch_*.py, zone_diagnostics.py, m3_baseline.py, xp_baseline.py, live_state.py,
                 threshold_sensitivity.py, export_web.py
web/             Next.js static site (src/app pages, src/components Court / PlayerView / Tables,
                 public/data the exported JSON)
docs/            DATASET.md, DECISIONS.md (D1-D26), EVALUATION.md, XP.md, M3_BASELINE.md,
                 ROADMAP.md, WALKTHROUGH.md (modules, 20 interview questions)
tests/           72 tests: geometry, zones, stats (incl. Newcombe's published example), loader on
                 synthetic games, analyses / report / positions / habits / xp / evaluation on a
                 synthetic table with planted patterns, tools, TrackNet
```

`docs/WALKTHROUGH.md` explains every module and the design decisions; `docs/DECISIONS.md` logs
the choices made during the builds with their reasoning.

## Roadmap

M2 own footage to stroke data; M3 sequence model to rank patterns; M4 web UI (4a, the static
scouting site, is done; 4b would add a backend for uploads); M5 varsity-team users and doubles.
Details in `docs/ROADMAP.md`.

## Credits and licences

- **ShuttleSet**: Wei-Yao Wang, Yung-Chang Huang, Tsi-Ui Ik, Wen-Chih Peng. *ShuttleSet: A
  Human-Annotated Stroke-Level Singles Dataset for Badminton Tactical Analysis.* KDD 2023.
  **ShuttleSet22**: Wei-Yao Wang, Wei-Wei Du, Wen-Chih Peng. IT4PSS @ IJCAI 2023. Both from the
  MIT-licensed [CoachAI-Projects](https://github.com/wywyWang/CoachAI-Projects) repository.
- **TrackNetV3**: Yu-Jou Chen and Yu-Shuen Wang. *TrackNetV3: Enhancing ShuttleCock Tracking with
  Augmentations and Trajectory Rectification.* ACM MMAsia 2023. Code and checkpoints MIT,
  [qaz812345/TrackNetV3](https://github.com/qaz812345/TrackNetV3); used unmodified via
  `src/tactics/tools/tracknet.py`.
- Player handedness: Wikipedia infoboxes and news profiles, URLs in `config/players.toml`.
