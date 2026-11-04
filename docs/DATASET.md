# ShuttleSet / ShuttleSet22: field dictionary and verified semantics

Source: [CoachAI-Projects](https://github.com/wywyWang/CoachAI-Projects) (MIT license,
`Copyright (c) 2022 Wei-Yao Wang`). The dataset folders carry no separate license, only a
citation request. Papers: ShuttleSet [arXiv:2306.04948](https://arxiv.org/abs/2306.04948)
(KDD 2023), ShuttleSet22 [arXiv:2306.15664](https://arxiv.org/abs/2306.15664).

Everything marked **verified** below was checked against the CSVs on 2026-11-04, not taken
from the README.

## Size

| | ShuttleSet | ShuttleSet22 | Combined, de-duplicated |
|---|---|---|---|
| Matches | 44 (2018-2021) | 58 (2021-2022) | 94 |
| Set files | 104 | 140 | 236 |
| Rallies | 3,683 | 4,944 | ~8,500 |
| Strokes | 36,484 | 52,356 | ~87,000 |
| Players | 27 | 35 | 43 |

**Verified:** all 8 of ShuttleSet22's 2021 matches are byte-identical duplicates of
ShuttleSet matches (same `video` folder names). De-duplicate on `video` when combining.

Best-covered players after de-duplication (matches): Viktor AXELSEN 20, An Se Young 12,
CHOU Tien Chen 11, LEE Zii Jia 9, NG Ka Long Angus 8, Kento MOMOTA 9, CHEN Yufei 9.

## Files

```
set/match.csv          one row per match
set/homography.csv     one row per match: camera -> court transform
set/<video>/set{1,2,3}.csv   one row per stroke
```

### match.csv
`id, video, tournament, round, year, month, day, set, duration, winner, loser, downcourt, url`
(`url` only in ShuttleSet, `db` only in ShuttleSet22). `set` = number of games played (2 or 3).
`downcourt` is undocumented; we do not rely on it (see "Court sides").

### homography.csv
`homography_matrix` (3x3, as a Python literal string) plus the four court corners in camera
pixels. **Verified:** applying `H` to the pixel corners gives exactly
`(25,150), (325,150), (25,810), (325,810)`, i.e. a court canvas 300 units wide and 660 units
long. A real court is 6.10 m x 13.40 m, so **1 unit = 2.033 cm**, the net is at `y = 480`,
and the centre line is at `x = 175`.

### set{n}.csv, one row per stroke (32 columns)

| Column | Meaning | Verified notes |
|---|---|---|
| `rally` | rally number | restarts at 1 in every set file |
| `ball_round` | stroke index within the rally, from 1 | consecutive except 2 rallies |
| `time`, `frame_num` | hit time in the source video | video not included |
| `roundscore_A/B` | game score | **score after the rally is scored** (first rally of each game already reads 1-0 or 0-1) |
| `player` | `A` = match winner, `B` = match loser | names come from `match.csv` |
| `server` | undocumented | **actually a position marker**: 1 = serve, 2 = mid-rally, 3 = final stroke of the rally |
| `type` | shot type, Chinese label | 18 documented + `未知球種` ("unknown", 3.9% of strokes); `過度切球` in data vs `過渡切球` in README |
| `aroundhead`, `backhand` | 1 or blank | blank means 0 |
| `hit_height`, `landing_height` | 1 = below net height, 2 = above | README says 0/1, data says 1/2 |
| `hit_area`, `hit_x`, `hit_y` | where the shuttle was struck | **99.96% identical to the previous stroke's landing point**; blank for serves |
| `landing_area`, `landing_x`, `landing_y` | where the shuttle landed / was next struck | camera pixels; apply `H` for court coordinates |
| `player_location_*`, `opponent_location_*` | hitter and receiver positions at contact | camera pixels; ~3% blank |
| `lose_reason`, `win_reason` | why the rally ended, from loser's / winner's view | only on the final stroke |
| `getpoint_player` | `A` or `B` | only on the final stroke |
| `flaw` | 1 = annotator flagged a problem | 97% of flagged strokes are `unknown` type |
| `db` | always 0 | ignore |

### Area codes (`*_area`)
1-9 are inside the court, 10-16 outside. From projected coordinates the in-court cells form
a 3x3 grid: rows front / mid / back = {1,2,7} / {5,6,8} / {3,4,9}; columns = {1,5,3},
{7,8,9} (centre), {2,6,4}. The numbering is relative to the hitter's side, not the camera.
We recompute zones from real court coordinates instead of trusting these codes, so the zone
definition is ours and consistent across datasets.

### Rally outcome codes
| `lose_reason` | English | Final-stroke hitter won? (verified) |
|---|---|---|
| 對手落地致勝 | opponent's shot landed in (a winner) | yes, 99.7% |
| 出界 | hit out | no, 99.1% |
| 掛網 | into the net | no, 99.5% |
| 未過網 | did not cross the net | no, 99.7% |
| 落點判斷失誤 | misjudged the landing (left it, it was in) | yes, 93% |
| 對手落地判斷失誤 | opponent misjudged the landing (7 rows) | yes |
| 犯規 | fault (4-6 rows) | mixed |

Ground truth for who won a rally is always `getpoint_player`; `lose_reason` describes *how*.

## Data quality issues to handle

1. **175 rallies (4.8%) in ShuttleSet have no outcome.** All are single-stroke rallies of
   type `unknown`: the point was played and scored (the score advances) but the strokes
   were not annotated, presumably a broadcast replay or camera cut. ShuttleSet22 has a
   similar 2.1%. Keep them for score bookkeeping, exclude from pattern analyses, never count
   them as "rally length 1".
2. **Unknown shot types** (`未知球種`): the authors drop any rally containing one. We keep
   rally length and outcome but exclude such rallies from shot-sequence patterns.
3. **Court sides switch** between games and at 11 points in game 3. The hitter's half is
   recovered from the projected `player_location_y` relative to the net (`y = 480`);
   within a rally a player never changes half, so missing positions fall back to the rally
   majority.
4. **Score before vs after.** `roundscore_*` includes the point just won. For "score
   pressure" analyses we subtract the winner's point to get the score at the start of the
   rally.
5. **Serve stroke has no hit position** (it starts the chain). The receiver's position is
   available via `opponent_location_*`.
6. `landing_height` is blank for 17% of ShuttleSet strokes (0.7% in ShuttleSet22).

## Benchmark splits (ShuttleSet22)
`preprocess_data.py` in the dataset folder defines match-level validation ids
`[38, 46, 47, 48, 49]` and test ids `[39, 40, 50, 52, 53, 54, 55, 56, 57]`. Useful as a
ready-made holdout for our own evaluation.
