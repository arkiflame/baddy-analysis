# Evaluation: are the insights real?

A tactical insight is now a claim like "when opponents push or rush to Axelsen's rear backhand
he loses the point within two shots 35% of the time; typical pros lose 23%". Three things can
make such a claim wrong: chance (small n), selection (we looked at hundreds of patterns and kept
the extremes), and label noise (annotators, zone thresholds). This document describes the guards
against each and reports the replication results of the current (v2) ranking.

## 1. Guards built into every report

| Risk | Guard | Where |
|---|---|---|
| Small samples | 95% Wilson interval on every rate; a row needs n >= 30 for the player AND n >= 30 for the reference before it can be ranked | `stats.py` |
| Universal truths dressed as insights | every rate is compared with the same pattern over all other players ("typical pros"), with Newcombe's interval on the difference; ranking is by the difference, not by lift over the player's own average | `analyses.py`, D19 |
| Winner's curse from screening many patterns | ranking by the interval bound nearest zero (the smallest difference the data still supports) penalises small-n extremes; at most two shot-and-zone rows and one single-factor row per table in the top-5 | `report.py` |
| Circular conditions | the rally-ending stroke is never a condition (sequences are the strokes *before* it); `out` / `net_error` zones are excluded from danger analyses | `analyses.py`, D9, D10 |
| Non-actionable claims in the top-5 | only danger tables (shot type x zone, shot alone, zone alone) are ranked; setups, rally length and game splits are descriptive context | D20 |
| Unstable selection | a top insight is ranked only if selected in at least half of the leave-one-match-out folds ("stable in X of N folds" printed next to it); the rest are listed as "less stable"; `tentative` if the interval on the difference is wider than 20 points or n < 60 | `report.py`, D27 |
| Outcome leakage via labels | players are keyed by name; the dataset's A/B labels (A = match winner) are never a variable | `loader.py`, D5 |
| Threshold sensitivity | all thresholds in `config/zones.toml`; the effect of moving them is measured (section 4) | D8, D26 |

## 2. Replication schemes (D25)

Code: `src/tactics/evaluation.py`. Command used for every number below, run 2026-11-05 on the
six players with at least 9 matches (the same set `scripts/export_web.py` evaluates for the site,
so the Methods page totals are this run's); it took 285 s:

```
uv run python -m tactics evaluate --player "Viktor AXELSEN" --player "An Se Young" \
    --player "CHOU Tien Chen" --player "CHEN Yufei" --player "LEE Zii Jia" --player "Kento MOMOTA" \
    --out outputs/evaluation_raw.md
```

* **holdout**: select the top-5 on the development matches; ShuttleSet22's own validation and
  test ids (14 matches) are held out and were never looked at while developing. Each insight is
  then measured on the player's holdout matches.
* **leave-one-match-out (lomo)**: for each of the player's matches, select the top-5 without it
  and record each selected pattern's count on that match. Each report insight is tested on the
  pooled out-of-sample counts from the folds that selected it; "selected in 15 of 20 folds" is
  reported as a stability measure.
* **leave-one-opponent-out (looo)**: the same with all matches against one opponent held out at
  once; an insight that only exists against one opponent is that opponent's style, not the
  player's trait.

Verdict per insight, always against the typical-pro reference it was selected on:

| verdict | meaning |
|---|---|
| REPLICATES | out-of-sample difference from typical pros has the same sign and its Newcombe 95% interval excludes zero |
| SAME DIRECTION | same sign, interval includes zero |
| FAILS | opposite sign |
| UNTESTABLE | fewer than 10 out-of-sample instances |

This rule is stricter than the first version's ("same sign and the two intervals overlap"), which
is why the counts below are not comparable with the numbers reported before Phase 3.

## 3. Results (run 2026-11-05, six players, 30 insights per scheme)

| player | matches | scheme | folds | REPLICATES | SAME DIRECTION | FAILS | UNTESTABLE |
|---|---|---|---|---|---|---|---|
| Viktor AXELSEN | 20 | holdout | 2 holdout matches | 1 | 3 | 0 | 1 |
| | | lomo | 20 | 3 | 2 | 0 | 0 |
| | | looo | 15 | 3 | 2 | 0 | 0 |
| An Se Young | 12 | holdout | 1 | 0 | 1 | 2 | 2 |
| | | lomo | 12 | 2 | 3 | 0 | 0 |
| | | looo | 7 | 2 | 2 | 1 | 0 |
| CHOU Tien Chen | 11 | holdout | 0 | 0 | 0 | 0 | 5 |
| | | lomo | 11 | 1 | 4 | 0 | 0 |
| | | looo | 5 | 1 | 2 | 0 | 2 |
| CHEN Yufei | 9 | holdout | 3 | 0 | 2 | 2 | 1 |
| | | lomo | 9 | 1 | 3 | 1 | 0 |
| | | looo | 5 | 0 | 3 | 1 | 1 |
| LEE Zii Jia | 9 | holdout | 2 | 0 | 2 | 2 | 1 |
| | | lomo | 9 | 1 | 4 | 0 | 0 |
| | | looo | 9 | 1 | 4 | 0 | 0 |
| Kento MOMOTA | 9 | holdout | 0 | 0 | 0 | 0 | 5 |
| | | lomo | 9 | 4 | 1 | 0 | 0 |
| | | looo | 4 | 1 | 2 | 0 | 2 |
| **Total** | | **holdout** | | **1** | **8** | **6** | **15** |
| | | **lomo** | | **12** | **17** | **1** | **0** |
| | | **looo** | | **8** | **15** | **2** | **5** |

Full per-insight output with out-of-sample rates, intervals and fold counts: `outputs/evaluation_raw.md`.

The three schemes are always quoted together. The holdout's 1 strict replicate and 6 fails are
real, and so is the reason: 1-3 holdout matches per player cannot resolve the 4-13 point
differences the v2 insights are made of (the out-of-sample interval on such a difference is
10-20 points wide). The two leave-one-out schemes test every insight on every match.

### Reading these results honestly

- **The holdout scheme is too thin for v2 insights.** The v2 ranking produces differences of
  4-13 percentage points against typical pros; on 1-3 holdout matches the out-of-sample interval
  for such a difference is 10-20 points wide. Six of the 30 came out with the opposite sign on the
  holdout, all with intervals that include the development value (e.g. An Se Young, "anything to
  the front forehand": 18% vs 12% in development, 7% on 59 holdout strokes); 15 are untestable,
  10 of them because Chou Tien Chen and Kento Momota have no holdout match at all. The first version's
  "13 of 14 replicated" rested on a lenient rule and on coarse claims; under the strict rule the
  holdout alone cannot confirm or refute most v2 insights.
- **Leave-one-match-out is the informative test.** Every insight is testable, 12 of 30 replicate
  with the interval excluding zero, 17 keep the same direction, 1 fails (Chen Yufei, "game-3 lobs
  to the rear forehand", 15% in development vs 7% out of sample on 41 strokes). Axelsen's
  three strongest claims (net shots to his front forehand 7% vs 14%, smashes to his mid forehand
  16% vs 23%, anything he plays to the opponent's mid forehand 6% vs 10%) replicate under both
  leave-one-out schemes, and the first was selected in every fold. Kento Momota replicates 4 of 5
  (pushes and rushes wherever they land 15% vs 23%, anything he plays to the opponent's front
  backhand 4% vs 11%, drops at 18+ in a game 0% vs 11%, net shots to the opponent's front
  backhand 4% vs 10%).
- **Selection is less stable than the point estimates suggest.** Several insights are selected in
  only half of the folds (Axelsen's body-zone claim 11 of 20, his "anything to the opponent's mid
  forehand" 10 of 20). The report's top-5 should be read as "five of the roughly ten patterns that
  the data supports", not as a fixed ranking.
- **Leave-one-opponent-out agrees with leave-one-match-out** (8 replicate, 15 same direction, 2
  fail, 5 untestable), so no evaluated insight is one opponent's style in disguise; the two
  failures (An Se Young's "pushes to the mid forehand", Chen Yufei's game-3 lob claim) are small-n
  claims that also look weak under the other schemes. The 5 untestable insights belong to the
  three players with only 4-5 distinct opponents (Chou, Chen, Momota): holding one opponent out
  removes a fifth or more of their rallies.
- **Game-3 and 18+ claims are the least reliable family**: small n by construction. The one
  insight that fails under both leave-one-out schemes is a game-3 claim (Chen Yufei's lobs to the
  rear forehand), and one of the 6 holdout failures is too (Chen Yufei's game-3 smashes). Momota's
  18+ drop claim is the exception that replicates (0% vs 11%, n=43 out of sample).

## 4. Threshold sensitivity (D26)

```
uv run python scripts/threshold_sensitivity.py        # writes outputs/sensitivity.md
```

The first five players above (the script was run before Momota was added, hence 25 top-5
insights), same selection rule, zone thresholds moved to the alternatives from D8:

| variant | default top-5 | still in top-5 | dropped | new |
|---|---|---|---|---|
| front/mid at 2.5 m (instead of 1.98) | 25 | 22 | 3 | 3 |
| body radius 0.75 m (instead of 0.50) | 25 | 16 | 9 | 9 |
| both | 25 | 14 | 11 | 11 |

The front/mid boundary barely matters. The body radius does: it decides which strokes count as
"to the body", so body-zone rows move in and out of the top-5 (Lee Zii Jia loses 4 of 5 at
0.75 m, Axelsen 2 of 5). Body-zone insights are therefore "at 0.5 m" claims and the report
states the thresholds it used. Defaults are unchanged.

## 5. Checks still to do

1. **Coach judgement.** Give a coach (or the author, blind to the numbers) the list of claims
   mixed with inverted decoys ("loses less after pushes") and record agreement. Target: a
   recorded agreement rate, not an anecdote.
2. **Time ordering.** Select on 2018-2021 (ShuttleSet), test on 2022 (ShuttleSet22) for the
   players present in both; this tests whether patterns persist across seasons.
3. **A peer reference.** "Typical pros" pools men's and women's singles and players with one or
   two matches. Re-run with the reference restricted to the same event and to players with at
   least five matches, and report how many insights change.
4. **Own footage (M2).** Once stroke data from club play exists, repeat the replication there;
   the pro patterns may not transfer to amateur rallies.
