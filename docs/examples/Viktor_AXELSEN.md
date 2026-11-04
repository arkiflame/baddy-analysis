# Tactical report: Viktor AXELSEN

_Generated 2026-11-04 by `python -m tactics report --player 'Viktor AXELSEN'`._

## Coverage

- Matches: 20 (2 of them in the holdout set, see docs/EVALUATION.md)
- Rallies with a known outcome: 1394; strokes: 15773
- Overall rally win rate: 58.1% (95% CI 55.5%-60.7%)
- Opponents: Anders ANTONSEN, Anthony Sinisuka GINTING, CHEN Long, Hans-Kristian Solberg VITTINGHUS, Jonatan CHRISTIE, Kento MOMOTA, Kodai NARAOKA, Kunlavut VITIDSARN, LEE Zii Jia, LIEW Daren, Lakshya SEN, NG Ka Long Angus, Rasmus GEMKE, SHI Yuqi, ZHAO Jun Peng
- Shot vocabulary: 10 coarse types; minimum n = 30; shrinkage prior = 20 rallies; handedness: right

## Top insights

1. after opponents' push rushs against Axelsen, Axelsen loses the point within 2 shots 21% (95% CI 18%-25%) of the time (n=495), more often than the 11% baseline for shots Axelsen faces.
2. after opponents' smashs against Axelsen, Axelsen loses the point within 2 shots 18% (95% CI 16%-21%) of the time (n=967), more often than the 11% baseline for shots Axelsen faces.
3. when the point is decided right after Axelsen lob, then opponent smash, Axelsen wins 11% (95% CI 5%-26%) (n=35), vs 58% overall.
4. when the point is decided right after opponent lob, then Axelsen smash, Axelsen wins 94% (95% CI 83%-98%) (n=48), vs 58% overall.
5. after opponents' push rush to the rear court, backhand side against Axelsen, Axelsen loses the point within 2 shots 35% (95% CI 25%-45%) of the time (n=81), more often than the 11% baseline for shots Axelsen faces.

Reading the numbers: every rate comes with its sample size and a 95% Wilson interval. `shrunk` pulls small samples toward the baseline (Beta prior worth 20 rallies). Rows marked `too few` have n below 30 and are shown for completeness only; `signal` means the interval excludes the baseline.

## Win rate by rally length

| strokes   |   n | win rate   | 95% CI   | shrunk   | vs baseline   | flag   |
|:----------|----:|:-----------|:---------|:---------|:--------------|:-------|
| 13-20     | 269 | 62%        | 56%-67%  | 61%      | +3%           |        |
| 21+       | 187 | 55%        | 48%-62%  | 55%      | -3%           |        |
| 1-4       | 350 | 56%        | 50%-61%  | 56%      | -2%           |        |
| 5-8       | 346 | 60%        | 55%-65%  | 60%      | +2%           |        |
| 9-12      | 242 | 57%        | 50%-63%  | 57%      | -1%           |        |

## How points end

Share of Axelsen's rallies by how the final stroke decided them (P = Axelsen, O = opponent). Descriptive counts; the next sections condition on what happened before the final stroke.

| ending   |   rallies | share   | most common final shots         |
|:---------|----------:|:--------|:--------------------------------|
| P winner |       272 | 20%     | smash 155, push rush 51, lob 24 |
| O error  |       538 | 39%     | defensive 116, net 96, lob 91   |
| P error  |       372 | 27%     | defensive 81, lob 79, net 66    |
| O winner |       212 | 15%     | smash 87, push rush 57, lob 17  |

## Win rate by the two shots before the point was decided

Tokens: `P:` = Axelsen, `O:` = opponent. The sequence is the two strokes played just before the final stroke (the winner or error). Read: given the rally reached this pattern and the next shot ended it, how often did Axelsen win. Reliable patterns only (n >= 30); 74 rarer patterns omitted.

| setup (two shots)     |   n | win rate   | 95% CI   | shrunk   | vs baseline   | flag   |
|:----------------------|----:|:-----------|:---------|:---------|:--------------|:-------|
| P:lob > O:smash       |  35 | 11%        | 5%-26%   | 28%      | -30%          | signal |
| P:net > O:net         |  41 | 20%        | 10%-34%  | 32%      | -26%          | signal |
| O:lob > P:smash       |  48 | 94%        | 83%-98%  | 83%      | +25%          | signal |
| P:lob > O:clear       |  43 | 74%        | 60%-85%  | 69%      | +11%          | signal |
| O:drop > P:net        |  36 | 75%        | 59%-86%  | 69%      | +11%          | signal |
| O:net > P:net         |  39 | 72%        | 56%-83%  | 67%      | +9%           |        |
| P:net > O:lob         |  51 | 51%        | 38%-64%  | 53%      | -5%           |        |
| O:net > P:lob         |  85 | 64%        | 53%-73%  | 62%      | +4%           |        |
| P:smash > O:defensive |  54 | 63%        | 50%-75%  | 62%      | +4%           |        |
| O:defensive > P:lob   |  30 | 63%        | 46%-78%  | 61%      | +3%           |        |
| O:smash > P:defensive |  55 | 62%        | 49%-73%  | 61%      | +3%           |        |

## Win rate by the three shots before the point was decided

203 rarer patterns omitted.

| setup (three shots)           |   n | win rate   | 95% CI   | shrunk   | vs baseline   | flag   |
|:------------------------------|----:|:-----------|:---------|:---------|:--------------|:-------|
| P:net > O:net > P:lob         |  31 | 65%        | 47%-79%  | 62%      | +4%           |        |
| P:lob > O:smash > P:defensive |  41 | 56%        | 41%-70%  | 57%      | -1%           |        |

## Danger conditions: shots Axelsen plays

Probability that Axelsen loses the point within 2 shots after playing a given shot type to a given zone of the opponent's court (zones from the opponent's view, forehand/backhand by their handedness). Baseline over all of Axelsen's shots: 7.5%.

| shot -> opponent zone   |   n | lost within 2   | 95% CI   | shrunk   | vs baseline   | flag   |
|:------------------------|----:|:----------------|:---------|:---------|:--------------|:-------|
| clear -> rear_bh        | 170 | 14%             | 9%-19%   | 13%      | +5%           | signal |
| smash -> mid_fh         | 517 | 3%              | 2%-5%    | 3%       | -4%           | signal |
| drop -> mid_fh          | 135 | 3%              | 1%-7%    | 4%       | -4%           | signal |
| net -> front_bh         | 566 | 11%             | 8%-13%   | 10%      | +3%           | signal |
| drop -> mid_bh          |  99 | 4%              | 2%-10%   | 5%       | -3%           |        |
| smash -> mid_bh         | 453 | 5%              | 3%-7%    | 5%       | -3%           | signal |
| drive -> mid_fh         |  68 | 10%             | 5%-20%   | 10%      | +2%           |        |
| push_rush -> mid_bh     |  79 | 10%             | 5%-19%   | 10%      | +2%           |        |
| defensive -> mid_bh     | 251 | 10%             | 7%-14%   | 9%       | +2%           |        |
| push_rush -> rear_bh    | 165 | 5%              | 3%-10%   | 6%       | -2%           |        |
| lob -> mid_bh           |  39 | 10%             | 4%-24%   | 9%       | +2%           |        |
| defensive -> front_bh   | 164 | 9%              | 6%-15%   | 9%       | +1%           |        |

By shot type alone:

| shot      |    n | lost within 2   | 95% CI   | shrunk   | vs baseline   | flag   |
|:----------|-----:|:----------------|:---------|:---------|:--------------|:-------|
| clear     |  256 | 12%             | 9%-17%   | 12%      | +5%           | signal |
| smash     | 1035 | 4%              | 3%-5%    | 4%       | -4%           | signal |
| drop      |  338 | 5%              | 3%-8%    | 5%       | -2%           |        |
| drive     |  232 | 9%              | 6%-13%   | 9%       | +1%           |        |
| unknown   |   35 | 6%              | 2%-19%   | 6%       | -1%           |        |
| net       | 1513 | 9%              | 7%-10%   | 9%       | +1%           |        |
| defensive | 1068 | 8%              | 7%-10%   | 8%       | +1%           |        |
| lob       | 1748 | 8%              | 7%-9%    | 8%       | +0%           |        |
| push_rush |  510 | 8%              | 6%-10%   | 8%       | +0%           |        |

By zone alone:

| opponent zone   |    n | lost within 2   | 95% CI   | shrunk   | vs baseline   | flag   |
|:----------------|-----:|:----------------|:---------|:---------|:--------------|:-------|
| body            |   51 | 12%             | 6%-23%   | 11%      | +3%           |        |
| front_bh        |  777 | 10%             | 8%-12%   | 10%      | +3%           | signal |
| mid_fh          | 1342 | 6%              | 5%-7%    | 6%       | -2%           | signal |
| rear_bh         | 1472 | 8%              | 7%-10%   | 8%       | +1%           |        |
| mid_bh          | 1189 | 7%              | 6%-9%    | 7%       | -0%           |        |
| rear_fh         |  928 | 7%              | 6%-9%    | 7%       | -0%           |        |
| front_fh        |  941 | 7%              | 6%-9%    | 7%       | -0%           |        |

## Danger conditions: shots Axelsen faces

Same measure for shots opponents play against Axelsen (zones from Axelsen's view). Baseline: 10.9%.

| opponent shot -> zone   |   n | lost within 2   | 95% CI   | shrunk   | vs baseline   | flag   |
|:------------------------|----:|:----------------|:---------|:---------|:--------------|:-------|
| push_rush -> rear_bh    |  81 | 35%             | 25%-45%  | 30%      | +19%          | signal |
| push_rush -> mid_fh     | 110 | 22%             | 15%-30%  | 20%      | +9%           | signal |
| push_rush -> rear_fh    | 149 | 20%             | 14%-27%  | 19%      | +8%           | signal |
| lob -> mid_fh           |  32 | 0%              | 0%-11%   | 4%       | -7%           | signal |
| lob -> rear_fh          | 360 | 5%              | 3%-7%    | 5%       | -6%           | signal |
| smash -> mid_bh         | 408 | 16%             | 13%-20%  | 16%      | +5%           | signal |
| drop -> mid_bh          | 324 | 6%              | 4%-9%    | 6%       | -5%           | signal |
| smash -> mid_fh         | 472 | 16%             | 13%-19%  | 15%      | +5%           | signal |
| defensive -> front_bh   | 206 | 6%              | 4%-10%   | 7%       | -4%           | signal |
| defensive -> mid_bh     | 203 | 6%              | 4%-11%   | 7%       | -4%           | signal |
| defensive -> mid_fh     | 229 | 7%              | 4%-11%   | 7%       | -4%           | signal |
| net -> front_fh         | 751 | 7%              | 6%-10%   | 8%       | -3%           | signal |

By zone alone:

| zone on Axelsen's side   |    n | lost within 2   | 95% CI   | shrunk   | vs baseline   | flag   |
|:-------------------------|-----:|:----------------|:---------|:---------|:--------------|:-------|
| rear_bh                  |  799 | 15%             | 12%-17%  | 15%      | +4%           | signal |
| front_fh                 | 1138 | 8%              | 6%-9%    | 8%       | -3%           | signal |
| body                     |   97 | 7%              | 4%-14%   | 8%       | -3%           |        |
| mid_fh                   | 1328 | 12%             | 10%-14%  | 12%      | +1%           |        |
| front_bh                 | 1092 | 10%             | 9%-12%   | 10%      | -1%           |        |
| rear_fh                  |  839 | 11%             | 9%-14%   | 11%      | +0%           |        |
| mid_bh                   | 1384 | 11%             | 9%-12%   | 11%      | -0%           |        |

## Splits: game number, pressure, serving

|   game |   n | win rate   | 95% CI   | shrunk   | vs baseline   | flag   |
|-------:|----:|:-----------|:---------|:---------|:--------------|:-------|
|      3 | 183 | 55%        | 47%-62%  | 55%      | -3%           |        |
|      1 | 618 | 59%        | 55%-63%  | 59%      | +1%           |        |
|      2 | 593 | 59%        | 55%-62%  | 59%      | +0%           |        |

| late game (either at 18+)   |    n | win rate   | 95% CI   | shrunk   | vs baseline   | flag   |
|:----------------------------|-----:|:-----------|:---------|:---------|:--------------|:-------|
| True                        |  215 | 55%        | 48%-61%  | 55%      | -3%           |        |
| False                       | 1179 | 59%        | 56%-61%  | 59%      | +1%           |        |

| serving   |   n | win rate   | 95% CI   | shrunk   | vs baseline   | flag   |
|:----------|----:|:-----------|:---------|:---------|:--------------|:-------|
| False     | 595 | 57%        | 53%-61%  | 57%      | -1%           |        |
| True      | 799 | 59%        | 55%-62%  | 59%      | +0%           |        |

### Game 3 only

Baseline win rate in this split: 54.6%.

| strokes   |   n | win rate   | 95% CI   | shrunk   | vs baseline   | flag    |
|:----------|----:|:-----------|:---------|:---------|:--------------|:--------|
| 13-20     |  45 | 60%        | 45%-73%  | 58%      | +4%           |         |
| 5-8       |  44 | 50%        | 36%-64%  | 51%      | -3%           |         |
| 1-4       |  44 | 59%        | 44%-72%  | 58%      | +3%           |         |
| 9-12      |  35 | 54%        | 38%-70%  | 54%      | -0%           |         |
| 21+       |  15 | 40%        | 20%-64%  | 48%      | -6%           | too few |

_no groups reach the minimum sample size (n >= 17)_

| shot -> opponent zone   |   n | lost within 2   | 95% CI   | shrunk   | vs baseline   | flag   |
|:------------------------|----:|:----------------|:---------|:---------|:--------------|:-------|
| lob -> rear_fh          |  63 | 16%             | 9%-27%   | 14%      | +5%           |        |
| smash -> mid_fh         |  61 | 3%              | 1%-11%   | 5%       | -5%           |        |
| net -> front_bh         |  81 | 14%             | 8%-23%   | 13%      | +3%           |        |
| net -> front_fh         |  75 | 5%              | 2%-13%   | 6%       | -3%           |        |
| defensive -> mid_bh     |  34 | 12%             | 5%-27%   | 11%      | +1%           |        |
| defensive -> mid_fh     |  39 | 8%              | 3%-20%   | 8%       | -1%           |        |
| smash -> mid_bh         |  50 | 8%              | 3%-19%   | 8%       | -1%           |        |
| lob -> rear_bh          | 136 | 10%             | 6%-17%   | 10%      | +1%           |        |

### Late game only (18+)

Baseline win rate in this split: 54.9%.

| strokes   |   n | win rate   | 95% CI   | shrunk   | vs baseline   | flag    |
|:----------|----:|:-----------|:---------|:---------|:--------------|:--------|
| 9-12      |  32 | 62%        | 45%-77%  | 60%      | +5%           |         |
| 13-20     |  37 | 49%        | 33%-64%  | 51%      | -4%           |         |
| 1-4       |  71 | 52%        | 41%-63%  | 53%      | -2%           |         |
| 5-8       |  51 | 57%        | 43%-69%  | 56%      | +1%           |         |
| 21+       |  24 | 58%        | 39%-76%  | 57%      | +2%           | too few |

_no groups reach the minimum sample size (n >= 14)_

| shot -> opponent zone   |   n | lost within 2   | 95% CI   | shrunk   | vs baseline   | flag   |
|:------------------------|----:|:----------------|:---------|:---------|:--------------|:-------|
| smash -> mid_fh         |  70 | 0%              | 0%-5%    | 2%       | -7%           | signal |
| smash -> mid_bh         |  68 | 3%              | 1%-10%   | 4%       | -4%           |        |
| defensive -> mid_bh     |  40 | 2%              | 0%-13%   | 5%       | -4%           |        |
| lob -> rear_bh          | 121 | 12%             | 8%-19%   | 12%      | +3%           |        |
| net -> front_bh         |  87 | 11%             | 6%-20%   | 11%      | +2%           |        |
| clear -> rear_bh        |  34 | 12%             | 5%-27%   | 11%      | +2%           |        |
| defensive -> front_fh   |  34 | 12%             | 5%-27%   | 11%      | +2%           |        |
| defensive -> mid_fh     |  34 | 12%             | 5%-27%   | 11%      | +2%           |        |

## Where the shuttle goes (heatmaps, descriptive only)

![Where Axelsen sends the shuttle](Viktor_AXELSEN_img/heatmap_plays.png)

![Where opponents send Axelsen](Viktor_AXELSEN_img/heatmap_faces.png)

## Data notes

- 317 rallies contain a stroke of unknown type; they count for rally length and outcome but are excluded from the shot-sequence tables.
- Placeholder rallies (one unannotated stroke while the score advances) are excluded everywhere.
- Opponents whose handedness is not in config/players.toml default to right-handed: none.
- Zone thresholds: config/zones.toml. Statistics: src/tactics/stats.py.