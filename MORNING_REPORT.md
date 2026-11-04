# Morning report, Phase 3 run of 2026-11-04 (branch `features-v3`)

Everything below was produced by code in this branch; each number names the command that made it.
The branch is pushed to the private repo (github.com/arkiflame/badminton-tactics) as a backup;
nothing else was published. No Claude attribution anywhere in the history (D18 resolved, the two
early trailers were stripped with your approval and `main` / `overnight-1` force-pushed).

## What got done, in the order you set

| Step | State | Where to look |
|---|---|---|
| 0 Strip trailers, rewrite history | done, verified with `git log --all --format='%h %(trailers:key=Co-Authored-By)'` | D18 |
| A Population baseline | done | `stats.compare_to_reference`, `analyses.population_*`, D19 |
| Phase 2 items 2-3: actionable top-5, two coach sections, wording | done | `report.py`, D20, `docs/examples/Viktor_AXELSEN.md` |
| B Position maps | done | `positions.py`, D21, report section |
| C Habits, predictability, set plays | done | `habits.py`, D22, report section |
| D xP | done, with an honest negative core result | `xp.py`, `scripts/xp_baseline.py`, `docs/XP.md`, D23 |
| E Live advantage bar | experiment run twice, **FAIL**, bar not built | `live_state.py`, `docs/M3_BASELINE.md`, D24 |
| F Docs | done | `README.md`, `docs/WALKTHROUGH.md` (sections 6-7, questions 16-20), this file |
| Phase 2 leftovers: leave-one-match-out / leave-one-opponent-out, threshold sensitivity | done | `evaluation.py`, `scripts/threshold_sensitivity.py`, `docs/EVALUATION.md`, D25, D26 |

Tests: 70 pass (`uv run pytest`, 47 s); `ruff check src tests scripts` clean. Commits on
`features-v3` beyond `overnight-1`: 8, each passing the tests at its commit.

## The real numbers

Data (`uv run python -m tactics players`): 94 matches, 81,939 strokes in the flat table,
81,671 of them in rallies with a known winner. The "87k" in the old README and resume bullets
was the raw pre-de-duplication row count (36,484 + 52,356 = 88,840) and has been replaced
everywhere.

**Axelsen's report v2** (`python -m tactics report --player "Viktor AXELSEN"`, 20 matches,
1,394 rallies, 58.1% win rate; all comparisons against all other players in the same situation):

1. Shots to his body: loses within two shots 7% (n=97, CI 4-14%) vs 20% for typical pros (-13, CI -18 to -5).
2. Net shots to his front forehand: 7% (n=751) vs 14% (-7, CI -8 to -4).
3. Smashes to his mid forehand: 16% (n=472) vs 23% (-7, CI -11 to -4).
4. In game 3, clears: 24% (n=46) vs 11% (+13, CI +3 to +28).
5. Anything he plays to the opponent's mid forehand: 6% (n=1,342) vs 10% (-4, CI -5 to -2).

"How to play against Axelsen" leads with the weaknesses: game-3 clears, pushes/rushes to his rear
backhand (35% vs 23%, +11, CI +2 to +23, n=81), game-3 shots to his front backhand (18% vs 11%).
"Smashes hurt everyone" is gone from the top-5; its v2 form is "smashes hurt Axelsen 8 points
less than typical pros".

**Replication** (`python -m tactics evaluate ...` on five players, 25 insights per scheme, strict
verdicts against the typical-pro reference, D25):

| scheme | REPLICATES | SAME DIRECTION | FAILS | UNTESTABLE |
|---|---|---|---|---|
| holdout (1-3 matches per player) | 1 | 8 | 6 | 10 |
| leave-one-match-out | 8 | 16 | 1 | 0 |
| leave-one-opponent-out | 7 | 13 | 2 | 3 |

Axelsen: 3 replicate / 2 same direction under both leave-one-out schemes, 0 fail. His "net shots
to the front forehand" claim was selected in all 20 folds.

**Threshold sensitivity** (`scripts/threshold_sensitivity.py`): front/mid at 2.5 m keeps 22 of
25 top-5 insights; body 0.75 m keeps 16 of 25; both 14 of 25.

**Position maps** (Axelsen): base 3.82 m from the net, 0.28 m to the forehand side (other
players' bases 3.27-4.40 m). Pulled from base 1.22 m by pushes/rushes vs 1.62 m for typical pros
(-0.39, CI -0.47 to -0.32); by clears 2.27 vs 2.05 m (+0.22). Distance per own stroke 1.58 m vs
1.70 m (-0.12, CI -0.17 to -0.07), a lower bound in both cases.

**Habits** (Axelsen): smashes 75% of clears to his rear backhand (n=191) vs 37% for typical pros
(+38, CI +31 to +44); 72% of lobs to his rear backhand vs 41%. Reply entropy after a clear to the
rear backhand 2.18 bits (4.5 effective replies) vs 3.11 for typical pros at the same n. Opens
short serve > opponent net > lob in 32% of his service rallies vs 19%.

**xP** (`scripts/xp_baseline.py`, 12 s): holdout AUC 0.50 on non-final strokes for xP-pre and
xP-post, logistic and gradient boosting alike; 0.79 on final strokes; with the final stroke's
out / net zone visible, 0.986 (the leak). Axelsen: +0.085 points above expectation per rally
overall; no shot type differs from his own overall; finishing smashes +0.146 vs +0.043 for other
pros (difference +0.104, CI +0.039 to +0.168, n=220).

**Live advantage** (`scripts/live_state.py`): best live-prefix AUC 0.498 (logistic with the last
two strokes' state), GRU 0.491, regularised GRU 0.488; pass bar 0.60. FAIL.

## What failed or was changed from the brief, and why

- **The live advantage bar was not built** (E failed its pre-set bar). The report's momentum view
  is the xP section.
- **xP is honest rather than flattering.** The "+0.08 points for rear-court smashes" style claim
  does not survive: mid-rally xP is at chance, so per-shot "points above expectation" mostly
  measures the player's overall edge. The report says so first, shows a "vs own overall" column,
  and gives the finishing table where the model has signal. Intervals are over rallies, not
  strokes (every stroke in a rally shares its outcome).
- **The holdout replication looks worse than before** (1 of 25 replicates strictly, 6 fail). Two
  reasons, both documented: the v2 rule is stricter (interval on the difference must exclude
  zero, not merely overlap), and v2 insights are 4-13 point differences that 1-3 holdout matches
  cannot resolve. Leave-one-match-out, which tests every insight on every match, is the
  informative scheme and the one quoted first.
- **Selection stability is moderate**: several top-5 insights are selected in only half of the
  leave-one-out folds. The report's top-5 is "five of roughly ten supported patterns".
- **Body-zone claims depend on the 0.5 m radius** (9 of 25 insights change at 0.75 m).
- **Shrinkage no longer drives anything** (D19); `--prior` still exists but only fills the
  `shrunk` column, which the report no longer prints.
- The full `tactics report` now takes about 40 s (loading 13 s, xP 12 s, habits 4 s, the rest
  under 2 s); `--no-xp`, `--no-habits`, `--no-positions` skip sections.

## Decisions you should review

1. **D19 role-based population.** The reference for "shots Axelsen faces" includes other players
   facing Axelsen's own shots. Defensible, but a peer reference (same event, >= 5 matches) is the
   next check (EVALUATION.md section 5).
2. **D20 top-5 only from danger tables**, single-factor rows capped at one per table. If you want
   setups back in the ranking, it is one tuple in `analyses.py`.
3. **D23 xP framing.** Keep the "Read this first" paragraph in the report; it is the difference
   between a result and a misleading one.
4. **D2 Axelsen handedness** is still encoded right-handed with sources; unchanged from last night.
5. **D1 repo private.**

## Three resume bullets (verified numbers only)

- Built a badminton tactical analyzer on 94 professional matches (81,939 annotated strokes) that
  compares each player with every other pro in the same situation (Newcombe intervals on the
  difference) and writes coaching reports; under leave-one-match-out replication 8 of 25 top
  insights replicate strictly and 24 of 25 keep their direction.
- Designed receiver-relative, handedness-aware court zones, position maps, habit / entropy
  scouting tables and a leak-free expected-points model (holdout AUC 0.79 at the decisive stroke,
  0.50 mid-rally, 0.986 with the outcome leaked), all with match-level splits and 70 tests.
- Ran and documented two pre-registered negative results (live rally prediction with sequence
  and state features, AUC 0.50 vs a 0.60 bar) and wrapped MIT-licensed TrackNetV3 end to end
  (median error 2.4 px on a synthetic clip).

## Suggested first hour this morning

1. `git checkout features-v3 && uv sync --extra dev --extra m3 && uv run pytest`
2. Read `outputs/Viktor_AXELSEN.md` top to bottom with a coach's eye, especially the two coach
   sections and the habits tables.
3. Decide whether `features-v3` merges into `main` (overnight-1 is already its base).
4. Pick the next evaluation check: peer reference or coach judgement (EVALUATION.md section 5).
