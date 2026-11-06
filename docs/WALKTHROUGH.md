# Walkthrough: how the project works and why

Written so the author can explain every part without notes. Each module gets: what it does, the
design decision behind it, and the trade-off accepted. Sections 6-7 cover the Phase 3 features
(population baseline, position maps, habits, xP, the live-advantage experiment).

## 1. The one-paragraph pitch

Consumer badminton apps already count smashes and draw shuttle trails. What they do not do is
tell a player *which patterns of play win or lose them points*, the thing a good coach does from
the sideline. This project builds that tactical layer. It works on 94 professional singles
matches (ShuttleSet + ShuttleSet22: 81,939 strokes in the flat table, 81,671 of them in rallies
with a known winner) and produces a Markdown report per player: where the player differs from
typical pros, written as advice for an opponent and for the player, every claim with a sample
size and a confidence interval, re-tested on matches that were not used to find it. Later
milestones replace the professional stroke data with stroke data extracted from the author's own
phone footage.

## 2. Data flow

```
ShuttleSet CSVs (pixels, Chinese labels, A/B players, score after the point)
   | loader.py          project to court metres, resolve sides, fix scores, name players
   v
Match > Game > Rally > Stroke  (model.py)   and   one flat stroke table (pandas)
   | zones.py           receiver-relative coach zones, fine grid, movement features
   v
annotated stroke table
   | analyses.py        per-player rate tables + the same tables for all OTHER players
   | stats.py           Wilson CI, Newcombe CI on the difference, t / Welch intervals for means
   v
PlayerReport                     positions.py   habits.py   xp.py
   | report.py          top-5, coach sections, tables, heatmaps, extra sections -> outputs/<player>.md
   | evaluation.py      holdout / leave-one-match-out / leave-one-opponent-out -> docs/EVALUATION.md
   | outcome_model.py, live_state.py   "who wins this rally" models (M3, docs/M3_BASELINE.md)
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
`slots=True` keeps 82k strokes cheap, and the flat pandas table is built from them once.

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
Evidence for thresholds (DECISIONS D8, D26): landing depth is tri-modal with a valley at
4.5-5.0 m, so 5.0 m is a natural rear boundary; moving the front/mid line to 2.5 m changes 3 of
25 top-5 insights across five players, moving the body radius to 0.75 m changes 9 of 25
(`outputs/sensitivity.md`).

### `stats.py`
What: Wilson 95% intervals; Newcombe's hybrid-score interval for the difference of two rates
(checked against the paper's example); `rate_table` and `compare_to_reference`, which every
analysis returns; t and Welch intervals for means (positions, xP).
Why Wilson: the normal interval collapses at 0/10 or 10/10; Wilson stays sensible.
Why Newcombe for differences: it combines the two Wilson intervals, so it behaves when one rate is
near 0 or one sample is small, which is exactly the regime of "this player vs everyone else".
Shrinkage toward the player's baseline is still computed (`shrunk`) but no longer drives any
ranking (D19).

### `analyses.py`
What: the per-player analyses, each a rate table with a `key` column so the same row can be
looked up on other matches, and each with a **reference** column: the same pattern measured on all
other players in the same role (receiver for "shots faced", hitter for "shots played").
- Danger conditions: P(point lost within 2 shots | shot type x receiver zone), for shots the
  player hits (their choices) and shots they face (their weaknesses), plus shot-alone and
  zone-alone versions, overall, in game 3 and at 18+. These are the **actionable** tables and the
  only source of ranked insights (D20).
- Context: win rate by rally-length bucket, by the 2 and 3 strokes before the decisive stroke
  (setups, D9), by game number, pressure and serve. Setups are compared with typical pros in the
  same setup; the symmetric splits with the player's own overall rate (across all pros they are
  50% by construction).
Out/net-error zones are excluded from danger analyses because they are outcomes (D10); unknown
shot types are excluded.
Ranking: a row is a candidate when both n >= 30 and the Newcombe interval of (player - typical
pros) excludes zero; candidates are ordered by the interval bound nearest zero, the smallest
difference the data still supports. Shot-alone and zone-alone rows have the largest n and would
win every ranking, so they are capped at one per table in the top-5.

### `report.py`
What: the top-5; "How to play against <player>" (weaknesses first, then strengths an opponent
should stop feeding) and "What <player> should fix" in coach language; every table with n, rate,
CI, the typical-pro rate and the difference with its interval; a descriptive context section; the
landing heatmaps; and hooks for the position, habit and xP sections.
Why sentences: the audience is a player or coach. "When opponents push or rush to Axelsen's rear
backhand, Axelsen loses the point within two shots 35% of the time (n=81); typical pros lose 23%"
is actionable; a table is not. The wording module knows verb forms per shot type so the sentences
read naturally ("push or rush", "plays a net shot").
Surname handling: the dataset writes family names in capitals; "An Se Young" is the exception
(Korean, family name first).

### `splits.py` and `evaluation.py`
What: the match-level holdout (ShuttleSet22's own validation + test ids, 14 matches) and three
replication schemes: holdout, leave-one-match-out, leave-one-opponent-out (D25). Verdicts per
insight: REPLICATES (out-of-sample difference from typical pros has the same sign and its
interval excludes zero), SAME DIRECTION, FAILS, UNTESTABLE (< 10 instances); plus, for the
leave-one-out schemes, in how many folds the insight was selected at all.
Why match-level: rallies of one match share players, form and annotator; a rally-level split
leaks. Why leave-one-out as well: 1-3 holdout matches per player left zone-level claims
untestable; leave-one-match-out tests every insight on every match while never selecting on it.
Current counts (six players with 9+ matches, 30 insights per scheme, REPLICATES / SAME DIRECTION /
FAILS / UNTESTABLE): holdout 1 / 8 / 6 / 15, leave-one-match-out 12 / 17 / 1 / 0,
leave-one-opponent-out 8 / 15 / 2 / 5. The holdout's 0-3 matches per player cannot resolve 4-13 point differences, which
is why its 1 strict replicate and 6 fails are always quoted next to the other two schemes.
Details in `docs/EVALUATION.md`. The report itself uses the leave-one-match-out folds a second
way: a top insight is ranked only if it was selected in at least half of them (D27).

### `cli.py`
`tactics players`, `tactics report --player NAME [--no-positions --no-habits --no-xp]`,
`tactics evaluate --player NAME ... [--scheme holdout|lomo|looo|all]`, `tactics zones-check`.
Argparse, no framework.

### `outcome_model.py` (M3 baseline) and `live_state.py`
What: predict whether the **server** wins the rally from a prefix of strokes, with a bag-of-tokens
logistic regression and a small GRU, against base-rate and "last hitter wins" heuristics, in
three settings (live prefix / pre-final / full rally with the final zone masked, D15);
`live_state.py` repeats the live setting with per-stroke state features (section 6E).
Why the server as reference: every rally has exactly one, so no player identity enters the model.
Why never the final stroke's zone: it is the outcome.

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
   need uncertainty, not just point estimates, and an out-of-sample test, not just a p-value.
2. **Compare with typical pros, not with the player's own average.** "Smashes hurt" is true of
   everyone; "smashes hurt Axelsen 8 points less than typical pros" is about Axelsen.
3. **Receiver-relative, handedness-aware zones.** Most tools draw heatmaps in camera coordinates.
   Ours answer "where did the shot send the opponent, relative to their backhand".
4. **No circular conditions.** Dropping the decisive stroke from sequences and the outcome zones
   from danger analyses cost us the most "impressive" numbers (95-99% rates) and replaced them
   with real ones.
5. **Match-level everything.** Splits, holdout, leave-one-out and both model experiments split
   by match; hyper-parameters are chosen on a validation split inside the development matches.
6. **Report negative results as results.** Live rally prediction is at chance with and without
   state features; mid-rally xP is at chance. Both are documented with the commands that show it,
   and the features that were promised on a pass were not built.
7. **Reuse perception, own the tactics.** TrackNetV3 is wrapped, credited and left unmodified.
8. **Reproducibility.** Every number in the docs comes from a command written next to it;
   thresholds live in TOML; the dataset is fetched by a script.

## 5. Fifteen likely interview questions (Milestone 1)

1. *Why ShuttleSet and not your own data first?*  It has 82k expert-labelled strokes with positions
   and outcomes, MIT licensed. Building perception first would have meant months before any
   tactical result; this way the tactics layer exists and the perception layer plugs into it.
2. *How do you know an insight is real?*  Wilson CI on the rate, Newcombe CI on the difference
   from typical pros, a minimum n of 30 on both sides, a stability rule (ranked only if selected
   in at least half of the leave-one-match-out folds, `tentative` if the interval on the
   difference is wider than 20 points or n is under 60), and three out-of-sample replication
   schemes with explicit verdicts, always reported side by side (`docs/EVALUATION.md`: holdout
   1 / 8 / 6 / 15, leave-one-match-out 12 / 17 / 1 / 0, leave-one-opponent-out 8 / 15 / 2 / 5).
3. *What is the winner's curse here and how do you handle it?*  Screening hundreds of patterns
   and keeping the extremes inflates them. Ranking by the conservative bound of the interval
   penalises small-n extremes, and leave-one-match-out re-measures each chosen insight on matches
   that did not take part in choosing it.
4. *Why not use the dataset's area codes?*  Undocumented, side-relative, and useless for our own
   footage. Recomputing from metres gives one definition that transfers.
5. *How do you know which half a player is on?*  Positions relative to the net, voted per rally,
   with the 11-point change of ends handled by "side periods". Tested on synthetic games.
6. *What did the first report get wrong?*  Its top insight was "shots that go out lose the point".
   Conditioning on outcomes is circular; the fix was to exclude outcome zones and the decisive
   stroke. The second version's top insight was "smashes hurt", true of everyone; the fix was the
   population reference.
7. *Why Wilson instead of a normal interval or a Bayesian credible interval?*  Correct coverage at
   small n and extreme rates, closed form, standard. A Beta posterior would be equivalent in spirit.
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
    captures jammed shots only; at 0.5 m body shots are 4-5% of smashes and drives, the expected
    signature. 0.75 m is the documented alternative and the sensitivity run shows it changes 9 of
    25 top-5 insights, so body-zone claims are read as "at 0.5 m" claims.
12. *What breaks when you move to phone footage?*  Camera motion (TrackNetV3's median background),
    lighting, player identity, and amateur shot mix. The roadmap measures each against hand labels.
13. *How do you keep the A/B label from leaking?*  The loader resolves names immediately; the flat
    table has no A/B column; tests assert it.
14. *What would you do with 10x more data?*  Per-player models (M3 with player embeddings),
    opponent-adjusted baselines, and finer zone-level tests.
15. *What is the licence situation?*  Dataset repo MIT; TrackNetV3 code and weights MIT (checksum
    recorded); our code MIT-compatible. Broadcast frames are never stored or redistributed.

## 6. Phase 3 features, in plain words

### A. Population baseline (`stats.compare_to_reference`, `analyses.population_strokes`)
Every rate the report shows for a player is computed a second time for *all other players in the
same situation*: receiving the same shot to the same zone, or playing it. The two rates are
compared with Newcombe's interval on their difference. Exclusion is by role, not by match, so the
player's opponents facing the player's shots are part of the "typical pro" reference for that
pattern. Insights are ranked by the smallest difference the data still supports (D19).

### B. Position maps (`positions.py`)
ShuttleSet records where each player stands only at the instant a stroke is hit, so these are
position maps, not footwork paths. Positions are put in the player's own half (metres from the
net, metres from the centre line toward their own right; the axis is labelled with their forehand
and backhand side from `players.toml`, D21). From them: two heatmaps on a court drawn to scale
(when hitting, when the opponent hits), the base position (median position when the opponent
hits a non-serve stroke) with how far each opponent shot type pulls the player from it, and the
distance per rally and per own stroke as a lower bound, split by game and by 18+ pressure. All of
it next to the same numbers for all other players, with t and Welch intervals.

### C. Habits and set plays (`habits.py`)
A situation is the opponent's shot type and the zone it landed in, from the player's view. For
each situation the module measures what the player replies with (shot type; shot type and target
zone) and compares each reply's share with other pros in the same situation; a habit is a reply
chosen significantly more often (D22). Predictability is the Shannon entropy of the reply
distribution, Miller-Madow corrected, compared with the population's entropy after subsampling
the population to the player's n, so small samples do not look falsely predictable. Set plays are
the first three and four strokes from the serve, by who served, ranked by how distinctive the
opening is versus other pros in the same role, with the win rate attached.

### D. xP, expected points (`xp.py`, `docs/XP.md`)
P(the hitter wins the rally | the shot just played). Two models because the honest inputs depend
on when you ask: xP-pre sees only what is known before the shuttle lands and is used for every
per-player number; xP-post adds the landing and is restricted to non-final strokes, because a
final stroke's landing is the outcome (D23). Logistic regression and gradient boosting, chosen on
a validation split, scored once on the 14 holdout matches. Result, and the first sentence of
every place xP is described: xP from shot and position data has no signal mid-rally in elite
singles (holdout AUC 0.50). The 0.79 on final strokes is classifying how an already-decisive
stroke ends (winner or error), not a working expected-points model. The report leads with that,
shows "points above expectation" per shot and court band next to typical pros and next to the
player's own overall so the reader sees what a chance-level model does to per-shot claims, and
keeps a Finishing table on final strokes, the one execution measure. Intervals are over rallies,
not strokes.

### E. Live advantage experiment (`live_state.py`, `docs/M3_BASELINE.md`)
Does per-stroke state (both positions, distance from base, recent movement, stroke index) give
live prediction the signal that tokens lack? Pass bar set in advance: holdout live-prefix AUC
>= 0.60. Result: 0.498 (logistic) and 0.491 / 0.488 (GRU, default and regularised). FAIL; no
advantage bar was built (D24). The report's momentum view is xP per shot.

## 7. Five more interview questions (Phase 3)

16. *Why compare with "typical pros" instead of a player's own baseline, and what is the
    catch?*  The own-baseline ranking surfaces universal truths ("smashes hurt"); the population
    comparison surfaces what is specific to the player. The catch is that the reference pools
    men's and women's singles and players with one or two matches, so "typical pro" means "this
    dataset", and the role-based exclusion means the player's own shots are in other players'
    "faced" references. Both are stated in the report.
17. *Why is the statistical unit a rally in the xP tables but a stroke in the danger tables?*
    "Points above expectation" averages (outcome - xP) over a player's strokes, and every stroke
    in a rally shares that rally's outcome, so stroke-level intervals would be far too narrow;
    aggregating within rally first fixes that. The danger tables condition on a single stroke and
    an event within two strokes of it, where the rally-sharing is much weaker; the holdout and
    leave-one-match-out schemes are the guard there.
18. *You built xP and it is at chance mid-rally. Was it wasted?*  It is a negative result and
    is presented as one: xP from shot and position data has no signal mid-rally in elite singles
    (holdout AUC 0.50), which explains the M3 live result and the failed live-advantage
    experiment. What survives is a finishing metric on strokes already known to be decisive
    (Axelsen's final smashes are winners 10 points more often than the model expects, over and
    above other pros) and the leak check, which shows what a careless xP model would have
    reported (AUC 0.986 on final strokes with the landing visible). The 0.79 on final strokes is
    a winner-versus-error classifier, and the write-up never calls it an expected-points model.
19. *How do you stop entropy from flattering players with few samples?*  Plug-in entropy is biased
    low for small n. We apply the Miller-Madow correction and, more importantly, never compare
    with the population at its full n: the population's replies are subsampled to the player's n
    200 times and the player's value is judged against that band.
20. *What did the leave-one-out evaluation change about how you present insights?*  It made
    selection stability part of the ranking: the report prints "stable in 15 of 20 folds" next to
    each top insight, ranks only patterns selected in at least half of the folds and lists the
    rest as "less stable"; it flags `tentative` rows (interval on the difference wider than 20
    points, or n under 60); and it separated REPLICATES from SAME DIRECTION, so an insight
    supported by one or two matches is labelled as such instead of being called replicated
    because a wide holdout interval happened to overlap.

## 8. The web UI (Milestone 4a, `web/` and `src/tactics/webexport.py`)

What: a statically exported Next.js site. `scripts/export_web.py` runs the same analysis functions
as the Markdown report for every player with at least 3 matches and writes one JSON file per
player plus `index.json`; the site reads those files at build time and renders them. Pages: a
searchable player list with coverage, a player page (scouting summary first, then tabs), a
Methods page. The court is an SVG drawn in metres (real lines, the three depth bands x
forehand / backhand side, the body circle at the player's base position) with zones coloured by
the difference from typical pros and tooltips showing n and the 95% interval; the same SVG shows
the position grids as a heatmap. Why static: nothing on the site needs a server, every number is
precomputed and reviewable in the repo, and a static site is the cheapest thing to host and the
hardest to break. Why the site computes nothing: the honesty rule ("never show a number the
export didn't produce") is easy to audit when the only arithmetic in the frontend is formatting.
Polish pass (D29): the page opens with a plain-language scouting summary (stable, non-tentative
insights only, numbers behind a "Show the numbers" toggle), the two coach cards never repeat a
situation (weaknesses are training priorities, the opponent card points at them), and
candidates whose interval bound rounds to 0 points are listed as "possible, not confident".

21. *Why export JSON instead of calling the Python code from the site?*  Separation of trust: the
    numbers are produced once, by the code that is tested, and committed; the UI is a renderer
    that can be reviewed for "does it show n and the interval next to every number" without
    reading any statistics code. It also makes the site static, so it has no runtime, no secrets
    and nothing to keep alive. The cost is a 20-minute export whenever the analysis changes, and a
    JSON schema that the TypeScript types mirror by hand.
22. *How does the court avoid lying with colour?*  Three ways. The diverging fill (blue = loses
    less than typical pros, red = loses more, grey midpoint) is reinforced by the printed
    difference in points and the n inside every zone, so a colour-blind reader loses nothing; zones
    whose interval includes zero are hatched rather than coloured, so a strong-looking hue cannot
    appear without a finding behind it; and a table with the same rows sits under the court. The
    body zone is receiver-relative, so it is drawn as a circle at the player's base position and
    labelled as such instead of being pretended into a fixed area of the court.
23. *What did Lighthouse and the accessibility pass change?*  Tabs follow the WAI-ARIA pattern
    (roving tab stop, arrow keys), every zone on the court is focusable with an aria-label that
    reads the full sentence, the search input and radio groups have real labels, tooltips are
    duplicated in text, contrast was chosen from a validated palette with separate dark-mode
    steps, and the "tentative" and "less stable" marks are text badges with an icon. The score is
    recorded with its command in `docs/DECISIONS.md` (D28), not quoted from memory.
24. *Why hide the numbers behind a toggle if honesty is the point?*  Because two audiences read
    the same page. A coach wants the sentence ("smashes to his mid forehand win fewer points
    than against typical pros"); a reviewer wants n, the interval and the fold count. Putting the
    pills one click away serves the first without taking anything from the second, and the
    honesty marks that change the meaning of a sentence ("tentative", "less stable", "possible,
    not confident") stay visible, since a reader must not need a click to learn that a claim is
    weak. The sentences themselves are generated only from insights that are stable and not
    tentative, so a numbers-free line is never a weaker claim in disguise.
