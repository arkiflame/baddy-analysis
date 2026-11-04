# badminton-tactics

A badminton **tactical analyzer**: finds the rally patterns that win and lose points for a
player, the kind of insight a coach gives, rather than raw shot counts.

Perception (shuttle tracking, shot classification) is a solved-enough problem with good
open-source work to reuse. The effort in this project goes into the tactics layer.

## Status

| Milestone | Scope | State |
|---|---|---|
| M1 | Tactical analyses on existing pro stroke data (ShuttleSet), CLI Markdown report | in progress |
| M2 | Own footage to stroke data (tracking, pose, court mapping, shot classification) | planned |
| M3 | Sequence model: point-outcome prediction to rank patterns | planned |
| M4 | FastAPI backend + Next.js dashboard | planned |
| M5 | Real users (varsity team), doubles | planned |

See `docs/ROADMAP.md` for details once M1 is complete.

## Setup

Requirements: Python 3.12+ and [uv](https://docs.astral.sh/uv/). No GPU needed for M1.

```powershell
uv sync --extra dev                 # creates .venv and installs deps
uv run python scripts/fetch_shuttleset.py   # downloads ShuttleSet + ShuttleSet22 into data/raw/
uv run pytest                       # run tests
```

## Data

M1 uses **ShuttleSet** (Wang et al., KDD 2023) and its extension **ShuttleSet22**: stroke-level
annotations of professional singles matches (shot type, hit/landing/player positions, score,
rally outcome). Both are published in the MIT-licensed
[CoachAI-Projects](https://github.com/wywyWang/CoachAI-Projects) repository.
`docs/DATASET.md` documents every field and the semantics verified against the data.

The raw files live in `data/raw/` and are not committed (see `.gitignore`). Re-fetch them with
the script above.

## Layout

```
src/tactics/     Python package (`python -m tactics ...`)
scripts/         one-off helpers (data fetching)
docs/            dataset notes, evaluation plan, roadmap
tests/           pytest suite
data/raw/        downloaded datasets (git-ignored)
outputs/         generated reports (git-ignored)
```

## Credits

- ShuttleSet: Wei-Yao Wang, Yung-Chang Huang, Tsi-Ui Ik, Wen-Chih Peng. *ShuttleSet: A
  Human-Annotated Stroke-Level Singles Dataset for Badminton Tactical Analysis.* KDD 2023.
- ShuttleSet22: Wei-Yao Wang, Wei-Wei Du, Wen-Chih Peng. *ShuttleSet22: Benchmarking Stroke
  Forecasting with Stroke-Level Badminton Dataset.* IT4PSS @ IJCAI 2023.
