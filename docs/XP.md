# xP, expected points: what one shot is worth

Command (12 s on the laptop CPU, scikit-learn):

```
uv run python scripts/xp_baseline.py          # writes outputs/xp/results.md, results.json, calibration.png
```

All numbers below are copied from `outputs/xp/results.md` produced by that command on 2026-11-04.

## The question and the two models

xP is P(the hitter wins the rally | the shot just played), one number per stroke, like football's
xG for one shot. The honest input set depends on *when* you ask (DECISIONS D23):

| model | inputs | domain |
|---|---|---|
| **xP-pre** | shot type, backhand / around-the-head / contact height, hitter position (depth from net, metres toward the forehand), receiver position, receiver distance from their own base position, stroke index, hitter is server | every stroke, final ones included |
| **xP-post** | xP-pre inputs + landing zone (receiver-relative), landing metres, receiver distance moved and direction, body flag, cross / straight | **non-final strokes only** |

Why the split: the landing of a final stroke *is* the outcome (out, net, winner). Clipping or
re-labelling those landings still leaks, because every net error becomes a tight-net front-zone
landing. So xP-post, the model that sees the landing, is trained and scored only on strokes that
were returned, and every per-player claim uses xP-pre.

Both are fitted as a logistic regression and as a gradient-boosted tree model
(`HistGradientBoostingClassifier`). Hyper-parameters (C in {0.1, 1, 10}; trees in {100, 200, 400}
at learning rate 0.05) are chosen on a match-level validation split inside the 80 development
matches, and the model family per feature set is chosen the same way (lowest validation log
loss). Nothing is tuned on the 14 ShuttleSet22 holdout matches. Receiver base positions come
from development matches only.

Data: 69,438 development strokes, 12,233 holdout strokes (11,051 non-final, 1,182 final).
Development base rate P(hitter wins) = 0.493; server win rate = 0.501.

## Holdout results

| feature set | model | strokes | n | accuracy | log loss | Brier | AUC |
|---|---|---|---|---|---|---|---|
| pre | base rate | all | 12,233 | 0.508 | 0.693 | 0.250 | 0.500 |
| pre | logistic (chosen) | all | 12,233 | 0.521 | 0.692 | 0.249 | 0.523 |
| pre | logistic | **non-final** | 11,051 | 0.501 | 0.696 | 0.251 | **0.500** |
| pre | logistic | **final** | 1,182 | 0.702 | 0.655 | 0.231 | **0.791** |
| pre | gbm | all | 12,233 | 0.521 | 0.691 | 0.249 | 0.524 |
| pre | gbm | non-final | 11,051 | 0.502 | 0.696 | 0.252 | 0.502 |
| pre | gbm | final | 1,182 | 0.696 | 0.644 | 0.226 | 0.780 |
| post | base rate | non-final | 11,051 | 0.492 | 0.693 | 0.250 | 0.500 |
| post | logistic (chosen) | non-final | 11,051 | 0.503 | 0.694 | 0.250 | 0.504 |
| post | gbm | non-final | 11,051 | 0.509 | 0.693 | 0.250 | 0.514 |

**Leak check.** The post features on *all* strokes with the final stroke's out / net zone visible
reach AUC 0.589 over all holdout strokes and **0.986 on the final strokes**. That is the outcome
re-labelled, not a prediction; it is the number a careless xP model would report.

Calibration (`outputs/xp/calibration.png`): xP-pre spans only about 0.40-0.62 in predicted
probability on the holdout, and the observed share won follows the diagonal across those bins;
xP-post on non-final strokes is a flat cloud around 0.5, as the AUC says.

## What this means

1. **Mid-rally, one shot carries no measurable information about who wins.** With shot type,
   how it was hit, both players' positions and the receiver's displacement from base, AUC on
   strokes that did not end the rally is 0.50 for both feature sets and both model families.
   Adding where the shuttle landed and how far the receiver had to move (xP-post) does not
   change that (0.50-0.51). This agrees with the M3 live result (`docs/M3_BASELINE.md`): elite
   singles rallies are balanced until the decisive exchange.
2. **At the final stroke the same features are informative (AUC 0.79).** Given that the stroke
   ended the rally, shot type and position tell a winner from an error reasonably well: a smash
   from the rear court with the receiver out of position is usually a winner, a lob from the
   front court that ends the rally is usually an error.
3. **So per-player xP claims must be read carefully.** "Actual minus xP" on all strokes mostly
   measures how often the player wins rallies that contain that shot, because xP is close to the
   base rate mid-rally. The report therefore shows, for every shot type and court band:
   the player's points above expectation, the same for all other pros, the difference with a
   Welch interval, and **"vs own overall"**, the within-player contrast that removes the player's
   general edge. Intervals are computed over rallies, not strokes, because every stroke a
   player hits in a rally shares that rally's outcome.
4. **"Finishing" is where xP adds information.** On final strokes only, "actual minus xP" is a
   genuine execution number: given that the player's stroke ended the rally and what the model
   expected from the situation, how often was it a winner.

## Viktor Axelsen (from the same run; `python -m tactics report --player "Viktor AXELSEN"` shows the full tables)

- Overall points above expectation: **+0.085 per rally** (95% CI +0.059 to +0.111, n=1,374 rallies); other pros -0.005.
- By shot and band, every reliable row is 0.06-0.15 above typical pros, but **no row differs from
  his own overall** (every "vs own overall" interval contains zero). The honest statement is
  "Axelsen wins more rallies than the model expects whatever shot he is playing", not "his
  rear-court smashes are special".
- **Finishing smash: +0.146 above expectation** (95% CI +0.086 to +0.207, n=220 final smashes) vs
  +0.043 for other pros (n=1,737); difference **+0.104 (95% CI +0.039 to +0.168)**. When Axelsen's
  smash ends the rally it is a winner about 10 points more often than the model expects, over and
  above the typical pro's margin. No other finishing shot differs from typical pros with
  confidence.
- Situation quality (mean xP of the shots he chooses) differs from typical pros by at most
  0.014 for any shot type: he does not play from better positions, by the model's measure.
- xP added per rally: -0.084 vs -0.074 for other pros. With a model at chance mid-rally these
  sums are small by construction and are reported for completeness only.

## Reproducibility and limits

- `src/tactics/xp.py` (features, models, per-player tables), `scripts/xp_baseline.py` (this
  document's numbers), `tests/test_xp.py` (feature leak guard, telescoping identity of xP added,
  a full run on synthetic data).
- Positions are feet positions at hit time with a median 0.80 m offset from the contact point
  (D8), and ShuttleSet has no timing or shuttle-speed information. Richer per-stroke features are
  the obvious next step and are the only thing likely to move the non-final AUC off 0.50.
- The per-player comparison is "this player vs all other players in the dataset", which includes
  women's singles and players with 1-2 matches; it is a reference, not a ranking of peers.
