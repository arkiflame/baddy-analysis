# Evaluation: are the insights real?

A tactical insight is a claim like "after opponents' pushes to Axelsen's rear backhand he loses
the point within two shots 35% of the time, against an 11% baseline". Three things can make such
a claim wrong: chance (small n), overfitting the selection (we looked at hundreds of patterns and
kept the extremes), and label noise (annotators, zone thresholds). This document describes how
we guard against each and reports the results of the first replication run.

## 1. Guards built into every report

| Risk | Guard | Where |
|---|---|---|
| Small samples | 95% Wilson interval on every rate; rows with n < 30 are flagged `too few` and never ranked | `src/tactics/stats.py` |
| Winner's curse from screening many patterns | Beta-binomial shrinkage toward the player's baseline (prior = 20 rallies); top-5 must have an interval that excludes the baseline; at most two insights per analysis family | `stats.py`, `report.py` |
| Circular conditions | The rally-ending stroke is never a condition: sequences are the strokes *before* the final one; `out` / `net_error` zones are excluded from danger analyses | `analyses.py` (D9, D10) |
| Outcome leakage via labels | Players are keyed by name; the dataset's A/B labels (A = match winner) are never used as a variable | `loader.py`, D5 |
| Threshold sensitivity | All zone thresholds live in `config/zones.toml`; the evidence for them is in `docs/DECISIONS.md` D8 | |

## 2. Holdout replication (the main test)

**Split.** ShuttleSet22 ships match-level validation and test ids in its own
`preprocess_data.py` (ids 38, 46-49 and 39, 40, 50, 52-57). We use those 14 matches as the
holdout and never look at them while developing. The split is by match, so no rally of a holdout
match can influence the development set.

**Procedure** (`python -m tactics evaluate --player NAME ...`, code in `src/tactics/evaluation.py`):

1. Run the full analysis on development matches only and pick the top-5 exactly as the report does.
2. Re-run the same analyses on the holdout matches and look up the same (analysis, pattern) rows.
3. Verdict per insight:
   - **REPLICATES**: holdout effect has the same sign relative to the holdout baseline and the two 95% intervals overlap.
   - **FAILS**: sign flips, or the intervals are disjoint.
   - **UNTESTABLE**: fewer than 10 holdout rallies/strokes match the pattern.

### Results (run 2026-11-04)

Command:

```
uv run python -m tactics evaluate --player "Viktor AXELSEN" --player "An Se Young" \
    --player "CHOU Tien Chen" --player "CHEN Yufei" --player "LEE Zii Jia" --out outputs/evaluation_raw.md
```

| Player | Dev matches | Holdout matches (rallies) | Replicates | Fails | Untestable |
|---|---|---|---|---|---|
| Viktor AXELSEN | 18 | 2 (131) | 2 | 0 | 3 |
| An Se Young | 11 | 1 (76) | 5 | 0 | 0 |
| CHOU Tien Chen | 11 | 0 (0) | 0 | 0 | 5 |
| CHEN Yufei | 6 | 3 (277) | 3 | 0 | 2 |
| LEE Zii Jia | 7 | 2 (164) | 3 | 1 | 1 |
| **Total** | | | **13** | **1** | **11** |

Axelsen, An and Chou are the three best-covered players as the brief asked; Chen Yufei and Lee
Zii Jia were added because they have the most holdout matches.

**What replicated** (development estimate, then holdout):

- Axelsen: opponents' pushes/rushes lead to a lost point within 2 shots 22% (CI 18-26%, n=458) vs 11% baseline; holdout 19% (9-34%, n=37) vs 10%.
- Axelsen: opponents' smashes, 18% (15-21%, n=849) vs 11%; holdout 19% (13-28%, n=118) vs 10%.
- An Se Young: all five replicated, including "lobs to her rear forehand are safe for the opponent only 5% of the time" (CI 3-8%, n=278; holdout 0%, n=21) and "smashes to her mid forehand hurt" (26%, n=208; holdout 14%, n=21).
- Chen Yufei: opponents' pushes/rushes, 29% (22-37%, n=146) vs 15%; holdout 39% (25-55%, n=36) vs 15%. Also "wins more in game 2" (53% vs 46%; holdout 62% vs 52%).
- Lee Zii Jia: opponents' smashes (27% vs 15%; holdout 15% vs 11%), pushes/rushes (24%; holdout 28%), smashes to his mid backhand (25%; holdout 23%).

**What failed:**

- Lee Zii Jia: "after Lee's own defensive returns he loses within 2 shots 16% (CI 12-20%, n=360) vs 11%" did **not** hold: holdout 7% (4-12%, n=158) vs 8%. The holdout interval is disjoint from the development one. Plausible reasons: different opponents in the two holdout matches, or the pattern was a development-set artefact. It should not be presented as a trait.

**What could not be tested:** every zone-specific pattern for Axelsen (the two holdout matches
give only 7-8 instances each) and everything for Chou Tien Chen, who has no holdout match.
Patterns like "pushes to the rear backhand" are the most coach-relevant and the hardest to
verify with 1-3 holdout matches per player.

### Reading these results honestly

- Thirteen of fourteen testable insights replicated, which is encouraging, but the testable ones
  are mostly the coarse, high-n kind ("smashes hurt"). The sharper zone-level claims mostly fell
  into UNTESTABLE. More holdout matches per player are needed before zone-level claims are trusted.
- "Opponents' smashes lead to lost points" replicated for every player tested. That is close to a
  universal truth of badminton, not a player-specific weakness. The player-specific signal is in
  the *magnitude* relative to the baseline and in which zones, which is exactly where n is thin.
- The holdout baselines differ from the development baselines (e.g. Axelsen 10% vs 11%, An 10% vs
  15%), so the test compares lift relative to each set's own baseline, not raw rates.

## 3. Checks still to do

1. **Opponent-adjusted baselines.** A player's rate against one opponent's style can dominate
   when they met several times (Axelsen vs Chou Tien Chen appears repeatedly). Re-run with
   leave-one-opponent-out and report how many insights survive.
2. **Coach judgement.** Give a coach (or the author, blind to the numbers) the list of claims
   mixed with inverted decoys ("loses less after pushes") and record agreement. Target: a
   recorded agreement rate, not an anecdote.
3. **Threshold sensitivity.** Re-run the report with front = 2.5 m and body = 0.75 m (D8) and
   count how many top-5 insights change.
4. **Time ordering.** Train on 2018-2021 (ShuttleSet), test on 2022 (ShuttleSet22) for the
   players present in both; this tests whether patterns persist across seasons.
5. **Own footage (M2).** Once stroke data from club play exists, repeat the replication there;
   the pro patterns may not transfer to amateur rallies.
