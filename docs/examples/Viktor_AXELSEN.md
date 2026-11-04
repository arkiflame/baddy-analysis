# Tactical report: Viktor AXELSEN

_Generated 2026-11-04 by `python -m tactics report --player 'Viktor AXELSEN'`._

## Coverage

- Matches: 20 (2 of them in the holdout set, see docs/EVALUATION.md)
- Rallies with a known outcome: 1394; strokes: 15773
- Overall rally win rate: 58.1% (95% CI 55.5%-60.7%)
- Opponents: Anders ANTONSEN, Anthony Sinisuka GINTING, CHEN Long, Hans-Kristian Solberg VITTINGHUS, Jonatan CHRISTIE, Kento MOMOTA, Kodai NARAOKA, Kunlavut VITIDSARN, LEE Zii Jia, LIEW Daren, Lakshya SEN, NG Ka Long Angus, Rasmus GEMKE, SHI Yuqi, ZHAO Jun Peng
- Shot vocabulary: 10 coarse types; minimum n = 30 on both sides of every comparison; handedness: right
- "Typical pros" = all other players in the dataset in the same situation (receiving the same shot to the same zone, or playing it); Axelsen is never part of Axelsen's own reference.

## Top insights

Where Axelsen differs most from typical pros, among patterns a coach can act on mid-match. Ranked by the smallest difference the data still supports (the 95% interval bound nearest zero), with at most 2 per table.

1. When opponents play anything to Axelsen's body, Axelsen loses the point within two shots 7% of the time (n=97, 95% CI 4%-14%); typical pros lose 20% after the same shot (difference -13 points, 95% CI -18 to -5, n=635).
2. When opponents play a net shot to Axelsen's front forehand, Axelsen loses the point within two shots 7% of the time (n=751, 95% CI 6%-10%); typical pros lose 14% after the same shot (difference -7 points, 95% CI -8 to -4, n=6410).
3. When opponents smash to Axelsen's mid forehand, Axelsen loses the point within two shots 16% of the time (n=472, 95% CI 13%-19%); typical pros lose 23% after the same shot (difference -7 points, 95% CI -11 to -4, n=3544).
4. In game 3, when opponents clear, wherever it lands, Axelsen loses the point within two shots 24% of the time (n=46, 95% CI 14%-38%); typical pros lose 11% after the same shot (difference +13 points, 95% CI +3 to +28, n=904).
5. When Axelsen plays anything to the opponent's mid forehand, Axelsen loses the point within two shots 6% of the time (n=1342, 95% CI 5%-7%); typical pros lose 10% after the same shot (difference -4 points, 95% CI -5 to -2, n=10215).

## How to play against Axelsen

For an opponent. Each line is a situation where Axelsen's record differs from typical pros with 95% confidence; 'loses within two shots' means the point ended within two strokes of that shot and Axelsen lost it.

- **In game 3, clear more.** Axelsen loses the point within two shots 24% of the time there, vs 11% for typical pros (n=46).
- **Push or rush to Axelsen's rear backhand.** Axelsen loses the point within two shots 35% of the time there, vs 23% for typical pros (n=81).
- **In game 3, attack Axelsen's front backhand.** Axelsen loses the point within two shots 18% of the time there, vs 11% for typical pros (n=118).
- **Axelsen's body is well covered.** Axelsen loses within two shots only 7% of the time, vs 20% for typical pros (n=97).
- **Smashes are less effective than usual.** Axelsen loses within two shots only 18% of the time, vs 26% for typical pros (n=967).
- **Don't count on net shots to Axelsen's front forehand.** Axelsen loses within two shots only 7% of the time, vs 14% for typical pros (n=751).

## What Axelsen should fix

Situations where Axelsen loses more often than typical pros.

- **In game 3, defending clears.** Axelsen loses the point within two shots 24% of the time there, vs 11% for typical pros (n=46).
- **Defending pushes and rushes to the rear backhand.** Axelsen loses the point within two shots 35% of the time there, vs 23% for typical pros (n=81).
- **In game 3, covering the front backhand.** Axelsen loses the point within two shots 18% of the time there, vs 11% for typical pros (n=118).

## The evidence: danger tables

Each row: probability that Axelsen loses the point within two shots after that shot, with the same probability for typical pros and the difference in percentage points (Newcombe 95% interval). `signal` = the interval excludes zero; `too few` = under 30 strokes; `ref too few` = under 30 in the reference. Zones are always from the receiver's point of view, forehand/backhand by their handedness; shots the rally ended on with an out or net error are excluded (they are outcomes, not targets).

### Shots Axelsen faces

Baseline over all shots Axelsen faces: 10.9%.

| opponent shot -> zone   |   n | lost within 2   | 95% CI   | typical pros   | difference (95% CI)   | flag   |
|:------------------------|----:|:----------------|:---------|:---------------|:----------------------|:-------|
| push_rush -> rear_bh    |  81 | 35%             | 25%-45%  | 23% (n=1385)   | +11 (+2 to +23)       | signal |
| push_rush -> mid_fh     | 110 | 22%             | 15%-30%  | 27% (n=804)    | -6 (-13 to +3)        |        |
| push_rush -> rear_fh    | 149 | 20%             | 14%-27%  | 17% (n=1797)   | +3 (-3 to +10)        |        |
| lob -> mid_fh           |  32 | 0%              | 0%-11%   | 9% (n=318)     | -9 (-13 to +2)        |        |
| lob -> rear_fh          | 360 | 5%              | 3%-7%    | 9% (n=4983)    | -4 (-6 to -1)         | signal |
| smash -> mid_bh         | 408 | 16%             | 13%-20%  | 23% (n=3761)   | -7 (-11 to -3)        | signal |
| drop -> mid_bh          | 324 | 6%              | 4%-9%    | 10% (n=1826)   | -4 (-7 to -1)         | signal |
| smash -> mid_fh         | 472 | 16%             | 13%-19%  | 23% (n=3544)   | -7 (-11 to -4)        | signal |
| defensive -> front_bh   | 206 | 6%              | 4%-10%   | 10% (n=1822)   | -4 (-7 to +0)         |        |
| defensive -> mid_bh     | 203 | 6%              | 4%-11%   | 10% (n=1731)   | -3 (-6 to +1)         |        |
| defensive -> mid_fh     | 229 | 7%              | 4%-11%   | 9% (n=1918)    | -2 (-5 to +2)         |        |
| net -> front_fh         | 751 | 7%              | 6%-10%   | 14% (n=6410)   | -7 (-8 to -4)         | signal |

By shot type alone:

| opponent shot   |    n | lost within 2   | 95% CI   | typical pros   | difference (95% CI)   | flag   |
|:----------------|-----:|:----------------|:---------|:---------------|:----------------------|:-------|
| push_rush       |  495 | 21%             | 18%-25%  | 23% (n=5189)   | -1 (-5 to +3)         |        |
| smash           |  967 | 18%             | 16%-21%  | 26% (n=8047)   | -8 (-10 to -5)        | signal |
| drop            |  897 | 7%              | 6%-9%    | 10% (n=6423)   | -3 (-5 to -1)         | signal |
| defensive       |  916 | 8%              | 6%-9%    | 10% (n=8343)   | -3 (-4 to -1)         | signal |
| lob             |  919 | 8%              | 7%-10%   | 10% (n=11584)  | -2 (-4 to -0)         | signal |
| clear           |  520 | 9%              | 7%-12%   | 11% (n=6350)   | -2 (-4 to +1)         |        |
| net             | 1701 | 10%             | 8%-11%   | 14% (n=13692)  | -4 (-6 to -3)         | signal |
| drive           |  262 | 11%             | 8%-15%   | 12% (n=2135)   | -1 (-4 to +4)         |        |

By zone alone:

| zone on Axelsen's side   |    n | lost within 2   | 95% CI   | typical pros   | difference (95% CI)   | flag   |
|:-------------------------|-----:|:----------------|:---------|:---------------|:----------------------|:-------|
| rear_bh                  |  799 | 15%             | 12%-17%  | 15% (n=10280)  | -0 (-2 to +3)         |        |
| front_fh                 | 1138 | 8%              | 6%-9%    | 13% (n=10115)  | -5 (-7 to -3)         | signal |
| body                     |   97 | 7%              | 4%-14%   | 20% (n=635)    | -13 (-18 to -5)       | signal |
| mid_fh                   | 1328 | 12%             | 10%-14%  | 16% (n=10229)  | -4 (-5 to -2)         | signal |
| front_bh                 | 1092 | 10%             | 9%-12%   | 13% (n=9238)   | -3 (-5 to -1)         | signal |
| rear_fh                  |  839 | 11%             | 9%-14%   | 12% (n=10119)  | -1 (-3 to +1)         |        |
| mid_bh                   | 1384 | 11%             | 9%-12%   | 16% (n=11147)  | -5 (-7 to -3)         | signal |

### Shots Axelsen plays

Baseline over all of Axelsen's shots: 7.5%.

| shot -> opponent zone   |   n | lost within 2   | 95% CI   | typical pros   | difference (95% CI)   | flag   |
|:------------------------|----:|:----------------|:---------|:---------------|:----------------------|:-------|
| clear -> rear_bh        | 170 | 14%             | 9%-19%   | 12% (n=2631)   | +1 (-3 to +7)         |        |
| smash -> mid_fh         | 517 | 3%              | 2%-5%    | 6% (n=3499)    | -3 (-4 to -1)         | signal |
| drop -> mid_fh          | 135 | 3%              | 1%-7%    | 6% (n=2113)    | -3 (-6 to +1)         |        |
| net -> front_bh         | 566 | 11%             | 8%-13%   | 10% (n=6292)   | +1 (-2 to +4)         |        |
| drop -> mid_bh          |  99 | 4%              | 2%-10%   | 6% (n=2051)    | -2 (-5 to +4)         |        |
| smash -> mid_bh         | 453 | 5%              | 3%-7%    | 6% (n=3716)    | -2 (-4 to +1)         |        |
| drive -> mid_fh         |  68 | 10%             | 5%-20%   | 9% (n=689)     | +2 (-4 to +11)        |        |
| push_rush -> mid_bh     |  79 | 10%             | 5%-19%   | 12% (n=1110)   | -2 (-7 to +7)         |        |
| defensive -> mid_bh     | 251 | 10%             | 7%-14%   | 11% (n=1683)   | -1 (-4 to +3)         |        |
| push_rush -> rear_bh    | 165 | 5%              | 3%-10%   | 9% (n=1301)    | -4 (-7 to +1)         |        |
| lob -> mid_bh           |  39 | 10%             | 4%-24%   | 22% (n=509)    | -12 (-19 to +2)       |        |
| defensive -> front_bh   | 164 | 9%              | 6%-15%   | 11% (n=1864)   | -2 (-6 to +4)         |        |

By shot type alone:

| shot      |    n | lost within 2   | 95% CI   | typical pros   | difference (95% CI)   | flag   |
|:----------|-----:|:----------------|:---------|:---------------|:----------------------|:-------|
| clear     |  256 | 12%             | 9%-17%   | 14% (n=6614)   | -1 (-5 to +3)         |        |
| smash     | 1035 | 4%              | 3%-5%    | 6% (n=7979)    | -2 (-3 to -1)         | signal |
| drop      |  338 | 5%              | 3%-8%    | 8% (n=6982)    | -3 (-5 to +0)         |        |
| drive     |  232 | 9%              | 6%-13%   | 8% (n=2165)    | +1 (-2 to +5)         |        |
| net       | 1513 | 9%              | 7%-10%   | 10% (n=13880)  | -1 (-3 to +0)         |        |
| defensive | 1068 | 8%              | 7%-10%   | 12% (n=8191)   | -3 (-5 to -1)         | signal |
| lob       | 1748 | 8%              | 7%-9%    | 12% (n=10755)  | -4 (-5 to -2)         | signal |
| push_rush |  510 | 8%              | 6%-10%   | 10% (n=5174)   | -2 (-4 to +1)         |        |

By zone alone:

| opponent zone   |    n | lost within 2   | 95% CI   | typical pros   | difference (95% CI)   | flag   |
|:----------------|-----:|:----------------|:---------|:---------------|:----------------------|:-------|
| body            |   51 | 12%             | 6%-23%   | 11% (n=681)    | +1 (-6 to +13)        |        |
| front_bh        |  777 | 10%             | 8%-12%   | 10% (n=9553)   | -0 (-2 to +2)         |        |
| mid_fh          | 1342 | 6%              | 5%-7%    | 10% (n=10215)  | -4 (-5 to -2)         | signal |
| rear_bh         | 1472 | 8%              | 7%-10%   | 11% (n=9607)   | -3 (-4 to -1)         | signal |
| mid_bh          | 1189 | 7%              | 6%-9%    | 9% (n=11342)   | -2 (-3 to -0)         | signal |
| rear_fh         |  928 | 7%              | 6%-9%    | 10% (n=10030)  | -3 (-4 to -1)         | signal |
| front_fh        |  941 | 7%              | 6%-9%    | 10% (n=10312)  | -3 (-5 to -1)         | signal |

### Game 3 only

Shots Axelsen faces:

| opponent shot -> zone   |   n | lost within 2   | 95% CI   | typical pros   | difference (95% CI)   | flag   |
|:------------------------|----:|:----------------|:---------|:---------------|:----------------------|:-------|
| smash -> mid_fh         |  66 | 23%             | 14%-34%  | 21% (n=643)    | +2 (-7 to +14)        |        |
| lob -> rear_bh          |  48 | 4%              | 1%-14%   | 11% (n=962)    | -6 (-10 to +4)        |        |
| defensive -> front_fh   |  32 | 3%              | 1%-16%   | 9% (n=458)     | -6 (-10 to +7)        |        |
| lob -> rear_fh          |  52 | 6%              | 2%-16%   | 8% (n=858)     | -2 (-7 to +8)         |        |
| net -> front_bh         |  80 | 18%             | 11%-27%  | 13% (n=1229)   | +5 (-2 to +15)        |        |
| net -> front_fh         |  96 | 10%             | 6%-18%   | 13% (n=1294)   | -3 (-8 to +5)         |        |
| smash -> mid_bh         |  51 | 14%             | 7%-26%   | 20% (n=654)    | -6 (-14 to +6)        |        |

Shots Axelsen plays:

| shot -> opponent zone   |   n | lost within 2   | 95% CI   | typical pros   | difference (95% CI)   | flag   |
|:------------------------|----:|:----------------|:---------|:---------------|:----------------------|:-------|
| lob -> rear_fh          |  63 | 16%             | 9%-27%   | 10% (n=847)    | +6 (-1 to +17)        |        |
| smash -> mid_fh         |  61 | 3%              | 1%-11%   | 5% (n=648)     | -1 (-4 to +7)         |        |
| net -> front_bh         |  81 | 14%             | 8%-23%   | 10% (n=1228)   | +4 (-2 to +13)        |        |
| net -> front_fh         |  75 | 5%              | 2%-13%   | 11% (n=1315)   | -5 (-9 to +3)         |        |
| defensive -> mid_bh     |  34 | 12%             | 5%-27%   | 13% (n=254)    | -2 (-10 to +14)       |        |
| defensive -> mid_fh     |  39 | 8%              | 3%-20%   | 10% (n=314)    | -2 (-8 to +11)        |        |
| smash -> mid_bh         |  50 | 8%              | 3%-19%   | 6% (n=655)     | +2 (-3 to +13)        |        |
| lob -> rear_bh          | 136 | 10%             | 6%-17%   | 11% (n=874)    | -0 (-5 to +6)         |        |

### At 18+ only

Shots Axelsen faces:

| opponent shot -> zone   |   n | lost within 2   | 95% CI   | typical pros   | difference (95% CI)   | flag   |
|:------------------------|----:|:----------------|:---------|:---------------|:----------------------|:-------|
| drop -> mid_bh          |  47 | 4%              | 1%-14%   | 12% (n=237)    | -8 (-14 to +3)        |        |
| drop -> mid_fh          |  31 | 3%              | 1%-16%   | 10% (n=287)    | -7 (-12 to +6)        |        |
| defensive -> mid_bh     |  33 | 6%              | 2%-20%   | 12% (n=270)    | -6 (-12 to +8)        |        |
| clear -> rear_fh        |  40 | 18%             | 9%-32%   | 13% (n=411)    | +5 (-5 to +20)        |        |
| clear -> rear_bh        |  30 | 7%              | 2%-21%   | 12% (n=418)    | -6 (-12 to +9)        |        |
| smash -> mid_fh         |  67 | 16%             | 9%-27%   | 20% (n=513)    | -3 (-11 to +8)        |        |
| smash -> mid_bh         |  56 | 16%             | 9%-28%   | 21% (n=557)    | -5 (-14 to +7)        |        |
| net -> front_bh         |  72 | 15%             | 9%-25%   | 16% (n=896)    | -0 (-7 to +10)        |        |

Shots Axelsen plays:

| shot -> opponent zone   |   n | lost within 2   | 95% CI   | typical pros   | difference (95% CI)   | flag   |
|:------------------------|----:|:----------------|:---------|:---------------|:----------------------|:-------|
| smash -> mid_fh         |  70 | 0%              | 0%-5%    | 7% (n=510)     | -7 (-10 to -2)        | signal |
| smash -> mid_bh         |  68 | 3%              | 1%-10%   | 6% (n=545)     | -3 (-6 to +4)         |        |
| defensive -> mid_bh     |  40 | 2%              | 0%-13%   | 8% (n=263)     | -5 (-10 to +5)        |        |
| lob -> rear_bh          | 121 | 12%             | 8%-19%   | 10% (n=800)    | +2 (-3 to +9)         |        |
| net -> front_bh         |  87 | 11%             | 6%-20%   | 11% (n=881)    | +1 (-5 to +9)         |        |
| clear -> rear_bh        |  34 | 12%             | 5%-27%   | 14% (n=414)    | -2 (-10 to +13)       |        |
| defensive -> front_fh   |  34 | 12%             | 5%-27%   | 9% (n=354)     | +3 (-5 to +18)        |        |
| defensive -> mid_fh     |  34 | 12%             | 5%-27%   | 16% (n=268)    | -5 (-13 to +11)       |        |

## Context (descriptive, not ranked)

### How points end

Share of Axelsen's rallies by how the final stroke decided them (P = Axelsen, O = opponent).

| ending   |   rallies | share   | most common final shots         |
|:---------|----------:|:--------|:--------------------------------|
| P winner |       272 | 20%     | smash 155, push rush 51, lob 24 |
| O error  |       538 | 39%     | defensive 116, net 96, lob 91   |
| P error  |       372 | 27%     | defensive 81, lob 79, net 66    |
| O winner |       212 | 15%     | smash 87, push rush 57, lob 17  |

### The two shots before the point was decided

Tokens: `P:` = Axelsen, `O:` = opponent. Given the rally reached this pattern and the next shot ended it, how often did Axelsen win, next to typical pros in the same setup. These condition on the rally ending, so they describe how points are decided rather than what to do next. Reliable patterns only (n >= 30); 74 rarer patterns omitted.

| setup (two shots)     |   n | win rate   | 95% CI   | typical pros   | difference (95% CI)   | flag   |
|:----------------------|----:|:-----------|:---------|:---------------|:----------------------|:-------|
| P:lob > O:smash       |  35 | 11%        | 5%-26%   | 9% (n=317)     | +2 (-6 to +17)        |        |
| P:net > O:net         |  41 | 20%        | 10%-34%  | 37% (n=497)    | -18 (-28 to -2)       | signal |
| O:lob > P:smash       |  48 | 94%        | 83%-98%  | 90% (n=304)    | +4 (-7 to +9)         |        |
| P:lob > O:clear       |  43 | 74%        | 60%-85%  | 54% (n=300)    | +20 (+4 to +32)       | signal |
| O:drop > P:net        |  36 | 75%        | 59%-86%  | 79% (n=255)    | -4 (-21 to +8)        |        |
| O:net > P:net         |  39 | 72%        | 56%-83%  | 64% (n=499)    | +8 (-8 to +20)        |        |
| P:net > O:lob         |  51 | 51%        | 38%-64%  | 46% (n=678)    | +5 (-9 to +18)        |        |
| O:net > P:lob         |  85 | 64%        | 53%-73%  | 52% (n=644)    | +12 (+0 to +22)       | signal |
| P:smash > O:defensive |  54 | 63%        | 50%-75%  | 41% (n=516)    | +22 (+8 to +34)       | signal |
| O:defensive > P:lob   |  30 | 63%        | 46%-78%  | 61% (n=141)    | +2 (-17 to +19)       |        |
| O:smash > P:defensive |  55 | 62%        | 49%-73%  | 56% (n=515)    | +6 (-8 to +18)        |        |

### The three shots before the point was decided

203 rarer patterns omitted.

| setup (three shots)           |   n | win rate   | 95% CI   | typical pros   | difference (95% CI)   | flag   |
|:------------------------------|----:|:-----------|:---------|:---------------|:----------------------|:-------|
| P:net > O:net > P:lob         |  31 | 65%        | 47%-79%  | 47% (n=228)    | +17 (-2 to +33)       |        |
| P:lob > O:smash > P:defensive |  41 | 56%        | 41%-70%  | 59% (n=222)    | -2 (-19 to +13)       |        |

### Rally length, game number, pressure, serving

The reference here is the player's own overall win rate: across all pros these splits are 50% by construction (every rally has one winner and one loser).

| strokes   |   n | win rate   | 95% CI   | own overall   | difference (95% CI)   | flag   |
|:----------|----:|:-----------|:---------|:--------------|:----------------------|:-------|
| 13-20     | 269 | 62%        | 56%-67%  | 58% (n=1394)  | +4 (-3 to +10)        |        |
| 21+       | 187 | 55%        | 48%-62%  | 58% (n=1394)  | -3 (-11 to +4)        |        |
| 1-4       | 350 | 56%        | 50%-61%  | 58% (n=1394)  | -2 (-8 to +3)         |        |
| 5-8       | 346 | 60%        | 55%-65%  | 58% (n=1394)  | +2 (-4 to +8)         |        |
| 9-12      | 242 | 57%        | 50%-63%  | 58% (n=1394)  | -1 (-8 to +5)         |        |

|   game |   n | win rate   | 95% CI   | own overall   | difference (95% CI)   | flag   |
|-------:|----:|:-----------|:---------|:--------------|:----------------------|:-------|
|      3 | 183 | 55%        | 47%-62%  | 58% (n=1394)  | -3 (-11 to +4)        |        |
|      1 | 618 | 59%        | 55%-63%  | 58% (n=1394)  | +1 (-4 to +5)         |        |
|      2 | 593 | 59%        | 55%-62%  | 58% (n=1394)  | +0 (-4 to +5)         |        |

| late game (either at 18+)   |    n | win rate   | 95% CI   | own overall   | difference (95% CI)   | flag   |
|:----------------------------|-----:|:-----------|:---------|:--------------|:----------------------|:-------|
| True                        |  215 | 55%        | 48%-61%  | 58% (n=1394)  | -3 (-10 to +4)        |        |
| False                       | 1179 | 59%        | 56%-61%  | 58% (n=1394)  | +1 (-3 to +4)         |        |

| serving   |   n | win rate   | 95% CI   | own overall   | difference (95% CI)   | flag   |
|:----------|----:|:-----------|:---------|:--------------|:----------------------|:-------|
| False     | 595 | 57%        | 53%-61%  | 58% (n=1394)  | -1 (-5 to +4)         |        |
| True      | 799 | 59%        | 55%-62%  | 58% (n=1394)  | +0 (-4 to +5)         |        |

Game 3 only, by rally length:

| strokes   |   n | win rate   | 95% CI   | own overall   | difference (95% CI)   | flag    |
|:----------|----:|:-----------|:---------|:--------------|:----------------------|:--------|
| 13-20     |  45 | 60%        | 45%-73%  | 55% (n=183)   | +5 (-11 to +20)       |         |
| 5-8       |  44 | 50%        | 36%-64%  | 55% (n=183)   | -5 (-20 to +11)       |         |
| 1-4       |  44 | 59%        | 44%-72%  | 55% (n=183)   | +4 (-12 to +20)       |         |
| 9-12      |  35 | 54%        | 38%-70%  | 55% (n=183)   | -0 (-18 to +17)       |         |
| 21+       |  15 | 40%        | 20%-64%  | 55% (n=183)   | -15 (-36 to +11)      | too few |

At 18+ only, by rally length:

| strokes   |   n | win rate   | 95% CI   | own overall   | difference (95% CI)   | flag    |
|:----------|----:|:-----------|:---------|:--------------|:----------------------|:--------|
| 9-12      |  32 | 62%        | 45%-77%  | 55% (n=215)   | +8 (-11 to +24)       |         |
| 13-20     |  37 | 49%        | 33%-64%  | 55% (n=215)   | -6 (-23 to +11)       |         |
| 1-4       |  71 | 52%        | 41%-63%  | 55% (n=215)   | -3 (-16 to +10)       |         |
| 5-8       |  51 | 57%        | 43%-69%  | 55% (n=215)   | +2 (-13 to +16)       |         |
| 21+       |  24 | 58%        | 39%-76%  | 55% (n=215)   | +3 (-17 to +22)       | too few |

### Where the shuttle goes (landing heatmaps)

![Where Axelsen sends the shuttle](Viktor_AXELSEN_img/heatmap_plays.png)

![Where opponents send Axelsen](Viktor_AXELSEN_img/heatmap_faces.png)

## Data notes

- 317 rallies contain a stroke of unknown type; they count for rally length and outcome but are excluded from the shot-sequence tables, and unknown-type strokes are excluded from the danger tables.
- Placeholder rallies (one unannotated stroke while the score advances) are excluded everywhere.
- Opponents whose handedness is not in config/players.toml default to right-handed: none.
- Zone thresholds: config/zones.toml. Statistics: src/tactics/stats.py.