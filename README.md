# badminton-tactics

A badminton **tactical analyzer**: it finds the rally patterns that win and lose points for a
player, the kind of insight a coach gives, rather than shot counts. Milestone 1 works on 94
professional singles matches (ShuttleSet + ShuttleSet22, 87k annotated strokes) and produces a
per-player Markdown report whose claims carry sample sizes and confidence intervals and are
re-tested on held-out matches.

Perception (shuttle tracking, shot classification) is reused from open-source work with credit;
the effort here goes into the tactics layer.

## What it does today

```
uv run python -m tactics players                       # coverage per player
uv run python -m tactics report --player "Viktor AXELSEN"   # -> outputs/Viktor_AXELSEN.md
uv run python -m tactics evaluate --player "Viktor AXELSEN" --player "An Se Young"
uv run python -m tactics zones-check                   # evidence behind the zone thresholds
```

A report contains the player's top-5 insights in plain language, then every table behind them:
win rate by rally length, by the two or three strokes before the point was decided, "danger
conditions" (shot type x court zone that lead to losing the point within two shots, both for
shots the player hits and shots they face), splits by game number and late-game pressure, how
points end, and fine-grid heatmaps. Example: [docs/examples/Viktor_AXELSEN.md](docs/examples/Viktor_AXELSEN.md).

Zones are computed from the **receiver's** point of view with a per-player handedness table, so
"rear backhand" means the receiver's backhand corner. Every threshold lives in `config/zones.toml`.

## Results (all numbers from commands in this repo, 2026-11-04)

Top insights for Viktor Axelsen (20 matches, 1,394 rallies, 58.1% rally win rate), from
`python -m tactics report --player "Viktor AXELSEN"`:

1. After opponents' pushes/rushes, Axelsen loses the point within 2 shots 21% of the time (95% CI 18-25%, n=495) vs an 11% baseline for shots he faces.
2. After opponents' smashes: 18% (16-21%, n=967) vs 11%.
3. When the point is decided right after an Axelsen lob followed by an opponent smash, he wins 11% (5-26%, n=35) vs 58% overall.
4. When the point is decided right after an opponent lob followed by an Axelsen smash, he wins 94% (83-98%, n=48) vs 58%.
5. After opponents' pushes/rushes to his rear backhand: 35% (25-45%, n=81) vs 11%.

Holdout replication (`docs/EVALUATION.md`): on 14 held-out matches chosen by the dataset authors,
**13 of 14 testable top-5 insights replicated** across five players (same direction, overlapping
95% intervals), 1 failed, and 11 were untestable because the pattern occurred fewer than 10 times
in the holdout.

Rally-outcome prediction baseline (`docs/M3_BASELINE.md`, 14 holdout matches, 1,110 rallies,
match-level split): while a rally is in progress neither logistic regression nor a GRU beats the
base rate (AUC 0.50-0.52); given that the next shot decides the point, "last hitter wins" gets
65.7% accuracy and the models reach AUC 0.73; with the final stroke visible but its landing zone
masked, the GRU reaches accuracy 0.747, AUC 0.815, Brier 0.175.

Shuttle tracking (Milestone 2 tooling): the TrackNetV3 wrapper detects a synthetic shuttle in
28 of 48 frames with a median error of 2.4 px (`tests/test_tracknet.py`). No real footage yet.

## Setup

Requirements: Python 3.12+, [uv](https://docs.astral.sh/uv/), git. GPU optional (M3 and tracking
use it when present).

```powershell
uv sync --extra dev                         # core: pandas, numpy, scipy, matplotlib
uv run python scripts/fetch_shuttleset.py   # ShuttleSet + ShuttleSet22 -> data/raw/ (MIT)
uv run pytest                               # 39 tests
# optional
uv sync --extra dev --extra m3 --extra video   # torch (CUDA 12.8 wheels), scikit-learn, opencv
uv run python scripts/fetch_tracknetv3.py      # TrackNetV3 source + weights (MIT, checksummed)
uv run python scripts/m3_baseline.py           # rally-outcome models
```

## Layout

```
src/tactics/
  loader.py      ShuttleSet CSVs -> Match/Game/Rally/Stroke + flat table (projection, sides, scores)
  court.py       pixel -> metre projection, player-relative frames
  zones.py       receiver-relative coach zones, fine grid, movement features
  stats.py       Wilson CIs, shrinkage, rate tables
  analyses.py    per-player analyses              report.py     Markdown report + heatmaps
  evaluation.py  holdout replication              splits.py     match-level holdout ids
  outcome_model.py  M3 sequence models            cli.py        the four commands
  tools/         court calibration, video labeller, TrackNetV3 wrapper (M2)
config/          zones.toml (thresholds), players.toml (handedness with sources)
scripts/         fetch_shuttleset.py, fetch_tracknetv3.py, zone_diagnostics.py, m3_baseline.py
docs/            DATASET.md, DECISIONS.md, EVALUATION.md, M3_BASELINE.md, ROADMAP.md, WALKTHROUGH.md
tests/           39 tests: geometry, zones at the boundaries, stats, loader on synthetic games
               (score correction, de-dup, placeholder rallies, change of ends at 11), tools
```

`docs/WALKTHROUGH.md` explains every module and the design decisions; `docs/DECISIONS.md` logs
the choices made during the overnight build with their reasoning.

## Roadmap

M2 own footage to stroke data; M3 sequence model to rank patterns; M4 FastAPI + Next.js
dashboard; M5 varsity-team users and doubles. Details in `docs/ROADMAP.md`.

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
