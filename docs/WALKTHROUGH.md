# Walkthrough: how the project works and why

Written so the author can explain every part without notes. Each module gets: what it does, the
design decision behind it, and the trade-off accepted.

## 1. The one-paragraph pitch

Consumer badminton apps already count smashes and draw shuttle trails. What they do not do is
tell a player *which patterns of play win or lose them points*, the thing a good coach does from
the sideline. This project builds that tactical layer. Milestone 1 does it on 94 professional
singles matches (ShuttleSet + ShuttleSet22, 87k strokes) and produces a Markdown report per
player with its top insights, each with a sample size and a confidence interval, and tests those
insights on held-out matches. Later milestones replace the professional stroke data with stroke
data extracted from the author's own phone footage.

## 2. Data flow

```
ShuttleSet CSVs (pixels, Chinese labels, A/B players, score after the point)
   | loader.py          project to court metres, resolve sides, fix scores, name players
   v
Match > Game > Rally > Stroke  (model.py)   and   one flat stroke table (pandas)
   | zones.py           receiver-relative coach zones, fine grid, movement features
   v
annotated stroke table
   | analyses.py        per-player rate tables (rally length, setups, danger conditions, splits)
   | stats.py           Wilson CI, shrinkage, reliability flags
   v
PlayerReport
   | report.py          top-5 selection, plain-language claims, tables, heatmaps  -> outputs/<player>.md
   | evaluation.py      same analyses on holdout matches, replicate / fail verdicts -> docs/EVALUATION.md
   | outcome_model.py   sequence models for "who wins this rally" (M3 baseline)
```

## 3. Modules

### `config.py` and `config/*.toml`
What: loads zone thresholds and player handedness from TOML (stdlib `tomllib`).
Why: thresholds are opinions a coach may want to change (where does "rear court" start?), so they
are data, not code, and every analysis reads the same numbers.
Trade-off: one more file to keep in sync; worth it because the report and the tests both quote it.

### `court.py`
What: pixel to metre projection through the dataset's per-match homography, and the "player
frame" (depth from the net, lateral offset toward a player's right hand or forehand).
Key fact discovered from the data: the homography maps every court onto a 300 x 660 canvas with
corners at (25,150) and (325,810); a real court is 6.10 x 13.40 m, so the two axes have slightly
different scales (0.02033 vs 0.02030 m per unit). Using one scale would stretch the court by 2 cm.
Why a player frame: "left" and "right" depend on which way the player faces. A near-half player
faces away from the camera (right hand = +x); a far-half player faces the camera (right = -x).
Forehand = right for right-handers, flipped for left-handers.

### `shots.py`
What: the 18 Chinese shot labels to English, the dataset authors' 10-way coarsening, the
rally-ending reason codes, and which of them mean "the hitter made an error".
Why keep both vocabularies: 18 types is what a coach says; 10 types gives enough samples per
category for per-player statistics. The report defaults to 10 (approved decision).

### `model.py`
What: four dataclasses. Positions are tuples in court metres; names, not labels.
Why dataclasses and not an ORM or nested dicts: zero dependencies, readable in a debugger,
`slots=True` keeps 87k strokes cheap, and the flat pandas table is built from them once.

### `loader.py`
What: reads the CSVs and fixes five things on the way in.
1. **Projection** to metres (one matrix multiply per point type).
2. **Which half each player stands in.** Players change ends between games and at 11 in game
   3. Each stroke votes with the hitter's feet position and the receiver's position (flipped);
   votes are summed per rally, so a foot annotated 5 cm past the net on one stroke does not flip
   the rally. Rallies with no positions borrow from the nearest decided rally in the same game and
   the same side period (before/after the 11-point change).
3. **Score before the rally.** The CSV stores the score *after* the point. Subtract the winner's
   point; flag the 1.2% of rallies where this disagrees with the previous rally's score (a point
   missing from the data).
4. **Placeholder rallies.** 4.8% of ShuttleSet rallies are one "unknown" stroke with no outcome
   while the score advances (a broadcast replay cut the strokes). They are kept so scores stay
   right, the winner is inferred from the scoreboard, and `annotated=False` excludes them from
   every analysis. They are never counted as rally length 1.
5. **De-duplication.** ShuttleSet22 re-ships 8 ShuttleSet matches under the same folder names.
Interview point: the A/B labels encode the match winner. Using them as a variable would leak the
outcome, so the loader resolves names immediately and nothing downstream sees A/B (approved
decision 5).

### `zones.py`
What: three layers of spatial features from the **receiver's** point of view.
- Coach zones (statistics): {front 0-1.98, mid 1.98-5.0, rear 5.0-6.7 m} x {forehand, backhand}
  + body (within 0.5 m of the receiver's position at the time of the hit, priority over the court
  zone, with a fh/bh sub-label). Out and net-error are separate categories for rally enders.
- Fine grid (heatmaps only): 4 depth bands x 4 lateral bands.
- Receiver-relative features: distance to move, direction (forward/back/lateral, fh/bh side),
  cross-court vs straight relative to the hitter's contact point.
Why receiver's view: a shot's tactical meaning is where it sends the opponent. A left-handed
receiver flips the lateral axis and nothing else changes.
Evidence for thresholds (DECISIONS D8): landing depth is tri-modal with a valley at 4.5-5.0 m, so
5.0 m is a natural rear boundary; the front/mid valley is nearer 2.9 m than the 1.98 m service
line (kept because it is a real line; 2.5 m suggested). Body shots at 0.5 m are 1.1% of strokes
and are 4-5% of smashes and drives, the expected signature.

### `stats.py`
What: Wilson 95% intervals, Beta-binomial shrinkage toward a baseline, and `rate_table`, which
every analysis returns.
Why Wilson: the normal interval collapses at 0/10 or 10/10; Wilson stays sensible.
Why shrinkage: screening hundreds of patterns and keeping the extremes is the winner's curse. A
prior worth 20 rallies means 5/6 (83%) reports as 58% against a 50% baseline while 50/60 stays
at 69%. Ranking uses the shrunk value; the raw rate and interval are always shown next to it.
Trade-off: the prior strength is a judgement call (D12). It is a CLI flag.

### `analyses.py`
What: the per-player analyses, each a rate table with a `key` column so the same row can be
looked up on holdout data.
- Win rate by rally-length bucket (1-4, 5-8, 9-12, 13-20, 21+).
- Win rate by the 2 and 3 strokes **before the decisive stroke** ("setups"). Conditioning on the
  final stroke itself would be circular: an error loses, a winner wins (D9). The final stroke is
  reported separately as counts: own winner / opponent error / own error / opponent winner.
- Danger conditions: P(point lost within 2 shots | shot type x receiver zone), for shots the
  player hits (their choices) and shots they face (their weaknesses). Out/net-error zones are
  excluded because they are outcomes (D10).
- Splits by game number, by late-game pressure (either player at 18+), and serve/receive.
Why "within 2 shots": a bad shot usually costs the point on the next stroke or the one after;
longer horizons wash out into the rally baseline.

### `report.py`
What: picks the top 5 (n >= 30, interval excludes the baseline, ranked by |lift| x sqrt(n), at
most two per analysis family, D13), writes a sentence per insight with the numbers inline, then
every table with n, rate, CI, shrunk value, lift and a flag, then fine-grid heatmaps.
Why sentences: the audience is a player or coach. "After opponents' pushes to his rear backhand
Axelsen loses the point within 2 shots 35% of the time (n=81) vs 11%" is actionable; a table is not.
Surname handling: the dataset writes family names in capitals; "An Se Young" is the exception
(Korean, family name first).

### `splits.py` and `evaluation.py`
What: the match-level holdout (ShuttleSet22's own validation + test ids, 14 matches) and the
replication procedure: top-5 on development data, re-measure on holdout, verdict REPLICATES
(same sign, intervals overlap), FAILS, or UNTESTABLE (< 10 holdout instances).
Why match-level: rallies of one match share players, form and annotator; a rally-level split
leaks. Why the dataset's ids: chosen before we ran anything, so the holdout is not ours to tune.
Result so far: 13 of 14 testable insights replicated across five players, 11 were untestable
(zone-level claims need more holdout matches), 1 failed (docs/EVALUATION.md).

### `cli.py`
`tactics players`, `tactics report --player NAME`, `tactics evaluate --player NAME ...`,
`tactics zones-check`. Argparse, no framework: the interface is four commands.

### `outcome_model.py` (M3 baseline)
What: predict whether the **server** wins the rally from a prefix of strokes, with a bag-of-tokens
logistic regression and a small GRU, against base-rate and "last hitter wins" heuristics, in
three settings (live prefix / pre-final / full rally with the final zone masked, D15).
Why the server as reference: every rally has exactly one, so no player identity enters the model.
Why never the final stroke's zone: it is the outcome.
Key finding: see docs/M3_BASELINE.md.

### `tools/` (M2 tooling)
- `calibrate_court.py`: four clicks give a homography in ShuttleSet's convention, so our footage
  flows through the same `court.py`.
- `label_video.py`: a state machine (`LabelSession`, tested without a display) plus a thin OpenCV
  loop; exports the ShuttleSet columns with Chinese shot labels so `loader.py` reads our files
  unchanged, and a TrackNet-format shuttle CSV for fine-tuning.
- `tracknet.py`: imports only the upstream network class (MIT) and re-implements the 40 lines of
  preprocessing/decoding (D17). Verified end to end on a synthetic clip.

## 4. Design decisions worth defending in an interview

1. **Statistics before models.** The deliverable is a list of claims a coach can act on. Claims
   need uncertainty, not just point estimates, and a holdout test, not just a p-value.
2. **Receiver-relative, handedness-aware zones.** Most tools draw heatmaps in camera coordinates.
   Ours answer "where did the shot send the opponent, relative to their backhand".
3. **No circular conditions.** Dropping the decisive stroke from sequences and the outcome zones
   from danger analyses cost us the most "impressive" numbers (95-99% rates) and replaced them
   with real ones (18-35%).
4. **Match-level everything.** Splits, holdout and the M3 experiment all split by match.
5. **Reuse perception, own the tactics.** TrackNetV3 is wrapped, credited and left unmodified;
   the effort went into the analysis layer.
6. **Reproducibility.** Every number in the docs comes from a command written next to it;
   thresholds live in TOML; the dataset is fetched by a script.

## 5. Fifteen likely interview questions

1. *Why ShuttleSet and not your own data first?*  It has 87k expert-labelled strokes with positions
   and outcomes, MIT licensed. Building perception first would have meant months before any
   tactical result; this way the tactics layer exists and the perception layer plugs into it.
2. *How do you know an insight is real?*  Wilson CI, shrinkage toward the baseline, a minimum n of
   30, and a match-level holdout replication with explicit verdicts. 13/14 testable claims
   replicated; one failed and is documented.
3. *What is the winner's curse here and how do you handle it?*  Screening hundreds of patterns
   and keeping the extremes inflates them. Shrinkage pulls small-n extremes toward the baseline
   and the holdout re-measures the chosen ones without selection.
4. *Why not use the dataset's area codes?*  Undocumented, side-relative, and useless for our own
   footage. Recomputing from metres gives one definition that transfers.
5. *How do you know which half a player is on?*  Positions relative to the net, voted per rally,
   with the 11-point change of ends handled by "side periods". Tested on synthetic games.
6. *What did the first report get wrong?*  Its top insight was "shots that go out lose the point".
   Conditioning on outcomes is circular; the fix was to exclude outcome zones and the decisive stroke.
7. *Why Wilson instead of a normal interval or a Bayesian credible interval?*  Correct coverage at
   small n and extreme rates, closed form, standard. A Beta posterior would be equivalent in spirit;
   shrinkage already uses a Beta prior.
8. *Why is the M3 model at chance in the "live" setting?*  Pro singles rallies are balanced until
   the decisive exchange; the strongest signal is parity of the pre-final stroke, which a model
   that does not know the rally is ending cannot use. In the pre-final setting the models beat the
   base rate clearly (see M3_BASELINE.md for the numbers).
9. *How does your number compare with the Shot Influence paper (AUC 0.90)?*  Their input includes
   every stroke of the rally; ours masks the final stroke's landing zone or drops the final stroke
   entirely. Including the final zone gives AUC 0.99 here because the zone *is* the outcome, so the
   comparable setting is "full, final zone masked".
10. *Handedness: how do you know?*  Every player verified from a Wikipedia infobox or a news
    profile, with the URL in `config/players.toml`. Five left-handers in the data.
11. *Why a 0.5 m body radius?*  It is below the median feet-to-contact distance (0.80 m), so it
    captures jammed shots only; at 0.5 m body shots are 4-5% of smashes and drives and under 0.5% of
    lifts, which is the expected signature. 0.75 m is the documented alternative.
12. *What breaks when you move to phone footage?*  Camera motion (TrackNetV3's median background),
    lighting, player identity, and amateur shot mix. The roadmap measures each against hand labels.
13. *How do you keep the A/B label from leaking?*  The loader resolves names immediately; the flat
    table has no A/B column; tests assert it.
14. *What would you do with 10x more data?*  Per-player models (M3 with player embeddings),
    opponent-adjusted baselines, and zone-level holdout tests that are currently UNTESTABLE.
15. *What is the licence situation?*  Dataset repo MIT; TrackNetV3 code and weights MIT (checksum
    recorded); our code MIT-compatible. Broadcast frames are never stored or redistributed.
