# M3 baseline: who wins the rally, from the strokes so far

Command (RTX 3070 Ti, CUDA 12.8 wheels, torch 2.11):

```
uv run python scripts/m3_baseline.py        # writes outputs/m3/results.md and results.json
```

Wall time 2.1 min for everything below (three settings x (logistic + 3 GRU seeds)).

## Task and data

- **Unit**: a rally with at least two strokes, a known winner and no "unknown" shot type.
  Tokens per stroke: `who|shot|zone` with who in {S = server, R = receiver}, the 10 coarse shot
  types, and the receiver-relative coach zone (or `nozone`). Score at the start of the rally
  and prefix length are extra inputs.
- **Label**: did the **server** win. The server is the reference because every rally has one,
  so no player identity enters the model (and the dataset's A/B labels never do).
- **Split by match**: development = 80 matches (train 4,258 rallies, validation 645 for GRU early
  stopping); holdout = the 14 ShuttleSet22 validation+test matches (1,110 rallies). Vocabulary 172 tokens.
- **Three settings** (DECISIONS D15), because "the strokes so far" means different things:

| setting | input | what it measures |
|---|---|---|
| live | every prefix k <= n-1 (42,161 train / 10,495 holdout prefixes) | can you call the rally while it is being played, not knowing when it ends |
| pre-final | the n-1 strokes before the decisive stroke | given the next shot decides the point, who wins |
| full, final zone masked | all n strokes, the last stroke's landing zone hidden | the closest honest analogue of the Shot Influence setting |

The final stroke's landing zone is never an input anywhere: `out` / `net_error` *is* the outcome.
With it included, a logistic regression reaches AUC 0.992 on the holdout (diagnostic run), which is
why that number is not reported as a result.

## Models

- **base rate**: the training server-win rate (0.506) for every rally.
- **heuristic, last hitter wins**: P(server wins | who hit the last input stroke), from training
  data. In the pre-final setting the player who hit the stroke before the decisive one wins 65%
  of the time (train: S 0.650, R 0.352).
- **logistic regression**: bag of token counts over the prefix + one-hot of the last token +
  prefix length + score difference + max score + parity; standardised, C = 0.3.
- **GRU**: 32-d token embedding, 1-layer GRU (64), concat with score/length, 2-layer head;
  AdamW 2e-3, batch 256, early stopping on validation log loss (patience 5, max 30 epochs);
  mean of 3 seeds. Per-seed numbers are in `outputs/m3/results.md`.

## Results on the 14 holdout matches (1,110 rallies)

| setting | model | accuracy | log loss | Brier | AUC |
|---|---|---|---|---|---|
| live, all prefixes (n=10,495) | base rate | 0.482 | 0.694 | 0.250 | 0.500 |
| | last hitter wins | 0.482 | 0.694 | 0.250 | 0.510 |
| | logistic regression | 0.500 | 0.723 | 0.259 | 0.516 |
| | GRU (3 seeds) | 0.495 | 0.698 | 0.252 | 0.499 |
| live, k = 6 (n=698) | logistic regression | 0.507 | 0.714 | 0.256 | 0.519 |
| | GRU (3 seeds) | 0.493 | 0.699 | 0.253 | 0.492 |
| pre-final (n=1,110) | base rate | 0.505 | 0.693 | 0.250 | 0.500 |
| | last hitter wins | 0.657 | 0.643 | 0.225 | 0.657 |
| | logistic regression | **0.668** | 0.635 | 0.213 | **0.730** |
| | GRU (3 seeds) | 0.661 | **0.608** | **0.211** | 0.725 |
| full, final zone masked (n=1,110) | base rate | 0.505 | 0.693 | 0.250 | 0.500 |
| | last hitter wins | 0.657 | 0.643 | 0.225 | 0.657 |
| | logistic regression | 0.737 | 0.556 | 0.182 | 0.800 |
| | GRU (3 seeds) | **0.747** | **0.529** | **0.175** | **0.815** |

(The "last hitter wins" heuristic gives identical numbers in the last two settings because the
final and pre-final hitters alternate, so it is the same predictor.)

## What this says

1. **Live prediction is at chance.** While a professional rally is in progress, neither a bag of
   shot/zone tokens nor a GRU over the sequence predicts the winner better than the base rate
   (AUC 0.50-0.52 at every prefix length). Elite singles rallies are balanced until the decisive
   exchange; the score at the start of the rally carries no usable signal either.
2. **The decisive exchange is predictable.** Knowing that the next shot ends the point, who hit
   the last stroke already gives 65.7% accuracy, and the models add about 1 point of accuracy and
   7 points of AUC on top (0.73 vs 0.66). The GRU is better calibrated (log loss 0.608 vs 0.635)
   while the logistic regression has slightly higher AUC. This is the signal the M1 "setup"
   tables exploit, which is why those tables are the right place to look for tactics.
3. **With the final stroke's type and hitter (zone masked), AUC reaches 0.80-0.82.** Most of the
   gain over pre-final comes from knowing *what* the final shot was (a smash that ends the rally
   is usually a winner, a lob that ends it is usually an error).
4. **Model capacity is not the bottleneck; information is.** GRU and logistic regression are
   within noise of each other in every setting (per-seed GRU AUC spread in the live setting is
   0.48-0.53). More data or a bigger model will not fix the live setting; richer per-stroke
   features (shuttle speed, contact height, player displacement) might.

## Comparison with the Shot Influence paper (Wang et al., ICDM 2021)

Reported on their private data (19 men's singles matches, 1,409 rallies, 15,742 shots, split by
match 17/1/1): their model AUC **0.8966**, Brier **0.1329**; baselines BiLSTM 0.7436 / 0.1859,
Transformer 0.7538 / 0.2009, ON-LSTM 0.7487, DeepMoji 0.7385, ProSeNet 0.5333. Inputs: the full
rally (player, timestamp, type, backhand, around-head, hit area, player area, opponent area) plus
the start score; end reason and winner excluded.

Are our numbers comparable? Only loosely:

- Their input includes **every stroke of the rally**, so the nearest of our settings is
  "full, final zone masked" (AUC 0.80-0.82, Brier 0.175-0.182). Their features include each
  stroke's *hit* area (where it was struck, not where it landed) and a timestamp; ours include
  where it was struck only indirectly (the previous landing zone) and no timing.
- Their test set is **two matches**; ours is 14. Two-match AUCs have wide intervals.
- Their rallies come from 2018-2020 men's singles only; ours mix men's and women's singles
  2018-2022 from a different (public) annotation effort.
- Their baselines (BiLSTM, Transformer at AUC 0.74-0.75) sit between our pre-final and masked
  settings, which suggests the regimes are similar once the final stroke is partially visible.

So: same task family, different inputs and test sets. Our contribution is the stricter protocol
(final-stroke zone never visible, 14 holdout matches, heuristics reported) rather than a higher
number. Reproducing their architecture on ShuttleSet under both protocols is the first M3 roadmap
item.

## Reproducibility

- `scripts/m3_baseline.py` (seeds 0, 1, 2; `--seeds` to change; `--cpu` to run without a GPU).
- Raw per-seed table and validation curves: `outputs/m3/results.md`, `outputs/m3/results.json`.
- Code: `src/tactics/outcome_model.py`.
