# Morning report, review-fix pass and merge of 2026-11-04 (late)

Everything below was produced by code in this repository; each number names the command that made
it. This pass fixed the six review items on `features-v3` and then fast-forwarded `main` to it.
No attribution trailers anywhere in the history. The Phase 3 report this replaces is in the git
history (`git show 7383dd9:MORNING_REPORT.md`).

Update 2026-11-05: the replication numbers below are from one re-run of the evaluation on the six
players with 9+ matches (285 s), the same run `docs/EVALUATION.md`, the README and the site's
Methods page now quote:

```
uv run python -m tactics evaluate --player "Viktor AXELSEN" --player "An Se Young" \
    --player "CHOU Tien Chen" --player "CHEN Yufei" --player "LEE Zii Jia" --player "Kento MOMOTA" \
    --out outputs/evaluation_raw.md
```

## What changed in this pass

| Review item | What was done | Where |
|---|---|---|
| 1 Insight stability | the report's top-5 is re-selected once per match of the player (leave-one-match-out); a pattern is ranked only if selected in at least 50% of the folds, prints "stable in X of N folds", and the plain top-5's failures go to a "Less stable" list; `tentative` flag when the interval on the difference is wider than 20 points or n < 60; `--no-stability` skips it | `report.rank_with_stability`, `evaluation.selection_frequency`, `cli.py`, D27, 2 new tests |
| 2 xP framing | every place xP is described now leads with "xP from shot and position data has no signal mid-rally in elite singles (holdout AUC 0.50)"; the 0.79 is "classifying how an already-decisive stroke ends", never a working model | `xp.section`, README, `docs/XP.md`, WALKTHROUGH (section D, questions 2, 18, 20), D23, this file |
| 3 Evaluation honesty | every summary quotes holdout / leave-one-match-out / leave-one-opponent-out side by side with the holdout's 1 strict replicate and 6 fails and the one-line reason | README results table, WALKTHROUGH, `docs/EVALUATION.md` |
| 4 Resume bullets | rewritten under the rules (below) | this file |
| 5 Re-run | `python -m tactics report --player "Viktor AXELSEN"` (now about 2 minutes with the stability folds) and `uv run pytest` after the changes; numbers in the docs checked against the outputs | `docs/examples/Viktor_AXELSEN.md` |
| 6 Merge | `main` fast-forwarded to `features-v3`, tests run on `main`, pushed; `overnight-1` and `features-v3` left on origin | see "Merge" below |

Tests: 72 pass (`uv run pytest`); `ruff check src tests scripts` clean.

## The real numbers

Data (`uv run python -m tactics players`): 94 matches, 81,939 strokes in the flat table, 81,671 of
them in rallies with a known winner.

**Axelsen's report** (`python -m tactics report --player "Viktor AXELSEN"`, 20 matches, 1,394
rallies, 58.1% win rate; every comparison against all other players in the same situation; the
top-5 is unchanged by the stability rule, all five are selected in at least 10 of 20 folds):

| # | insight | stable in | flag |
|---|---|---|---|
| 1 | shots to his body: loses within two shots 7% (n=97, CI 4-14%) vs 20% for typical pros (-13, CI -18 to -5) | 11 of 20 folds | |
| 2 | net shots to his front forehand: 7% (n=751) vs 14% (-7, CI -8 to -4) | 20 of 20 | |
| 3 | smashes to his mid forehand: 16% (n=472) vs 23% (-7, CI -11 to -4) | 15 of 20 | |
| 4 | in game 3, clears: 24% (n=46) vs 11% (+13, CI +3 to +28) | 18 of 20 | tentative (n < 60, interval 25 points wide) |
| 5 | anything he plays to the opponent's mid forehand: 6% (n=1,342) vs 10% (-4, CI -5 to -2) | 10 of 20 | |

The fold counts are the same ones `tactics evaluate` prints (same folds, same k). "How to play
against Axelsen" still leads with the weaknesses: game-3 clears, pushes/rushes to his rear
backhand (35% vs 23%, +11, CI +2 to +23, n=81), game-3 shots to his front backhand (18% vs 11%).

**Replication** (the `tactics evaluate` command above, six players with 9+ matches, 30 insights
per scheme, strict verdicts against the typical-pro reference, D25; the three schemes are always
quoted together):

| scheme | REPLICATES | SAME DIRECTION | FAILS | UNTESTABLE |
|---|---|---|---|---|
| holdout (0-3 matches per player) | 1 | 8 | 6 | 15 |
| leave-one-match-out | 12 | 17 | 1 | 0 |
| leave-one-opponent-out | 8 | 15 | 2 | 5 |

The holdout's 1 strict replicate and 6 fails are real; 0-3 holdout matches cannot resolve the
4-13 point differences the insights are made of, which is why the two leave-one-out schemes exist
and why none of the three is quoted alone. Axelsen: 3 replicate / 2 same direction under both
leave-one-out schemes, 0 fail.

**Threshold sensitivity** (`scripts/threshold_sensitivity.py`): front/mid at 2.5 m keeps 22 of 25
top-5 insights; body 0.75 m keeps 16 of 25; both 14 of 25.

**Position maps** (Axelsen): base 3.82 m from the net, 0.28 m to the forehand side (other players'
bases 3.27-4.40 m). Pulled from base 1.22 m by pushes/rushes vs 1.62 m for typical pros (-0.39,
CI -0.47 to -0.32); by clears 2.27 vs 2.05 m (+0.22). Distance per own stroke 1.58 m vs 1.70 m
(-0.12, CI -0.17 to -0.07), a lower bound in both cases.

**Habits** (Axelsen): smashes 75% of clears to his rear backhand (n=191) vs 37% for typical pros
(+38, CI +31 to +44); 72% of lobs to his rear backhand vs 41%. Reply entropy after a clear to the
rear backhand 2.18 bits (4.5 effective replies) vs 3.11 for typical pros at the same n. Opens short
serve > opponent net > lob in 32% of his service rallies vs 19%.

**xP, a negative result** (`scripts/xp_baseline.py`, 12 s): xP from shot and position data has no
signal mid-rally in elite singles, holdout AUC 0.50 on non-final strokes for xP-pre and xP-post,
logistic and gradient boosting alike. The same features reach 0.79 only on final strokes, which is
classifying how an already-decisive stroke ends, not a working expected-points model; with the
final stroke's out / net zone visible the number is 0.986 (the leak). What survives: Axelsen's
finishing smashes are winners +0.146 above expectation vs +0.043 for other pros (difference +0.104,
CI +0.039 to +0.168, n=220).

**Live advantage, a negative result** (`scripts/live_state.py`): best live-prefix AUC 0.498
(logistic with the last two strokes' state), GRU 0.491, regularised GRU 0.488; pass bar 0.60. FAIL,
bar not built.

## Merge

Done after the last commit on `features-v3`, in this order:

```
git checkout main && git merge --ff-only features-v3     # no merge commit
uv run pytest                                            # on main
git push origin main
gh repo view --json defaultBranchRef                      # must say main
gh api repos/arkiflame/baddy-analysis/readme -H "Accept: application/vnd.github.raw" | head
```

`overnight-1` and `features-v3` on origin were left as they were (`features-v3` on origin still
points at the last Phase 3 commit, 7383dd9; everything after it is on `main`). The recap at the
end of the session states the result of each command.

## Decisions you should review

1. **D27 stability rule.** 50% of folds, 20-point interval width, n = 60 are constants in
   `report.py`; all three are judgement calls, logged with the reason.
2. **D19 role-based population.** The reference for "shots Axelsen faces" includes other players
   facing Axelsen's own shots. Defensible, but a peer reference (same event, >= 5 matches) is the
   next check (EVALUATION.md section 5).
3. **D20 top-5 only from danger tables**, single-factor rows capped at one per table.
4. **D2 Axelsen handedness** is still encoded right-handed with sources.
5. **D1 repo private.**

## Three resume bullets (verified numbers only; each two lines)

- Built a badminton scouting tool on 94 professional matches (81,939 annotated strokes): habit and set-play tables,
  reply-entropy predictability, position maps, and a player-vs-typical-pro comparison with a confidence interval on every difference.
- Replicated the insights out of sample under three schemes, always reported together: 12 of 30 replicate strictly under
  leave-one-match-out (17 more keep their direction), 8 under leave-one-opponent-out, 1 on the thin 0-3-match holdout.
- Reported two negative results instead of hiding them: expected points from shot and position data has no signal
  mid-rally in elite singles (holdout AUC 0.50), and live rally prediction scored 0.50 against a 0.60 bar set in advance.

## Suggested first hour this morning

1. `git checkout main && uv sync --extra dev --extra m3 && uv run pytest`
2. Read `docs/examples/Viktor_AXELSEN.md` top to bottom: the top-insights table with its fold
   counts and the tentative flag, then the two coach sections, then the xP section's first sentence.
3. Pick the next evaluation check: peer reference or coach judgement (EVALUATION.md section 5).
