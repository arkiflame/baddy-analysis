# Decision log

Decisions made without the user present, with the reasoning, newest at the bottom. Entries
marked **REVIEW** are ones the user should look at.

## 2026-11-04 (overnight run, branch `overnight-1`)

### D1. GitHub repo created as **private** — REVIEW
The overnight brief said never to create a repo or publish; a later message said "also
create a github repo". The later instruction wins, but the safest reading of both is a
private repo. Flip to public from the repo settings when you are ready.

### D2. Viktor Axelsen is encoded as **right-handed** — REVIEW
The brief states he is left-handed. Every source checked (Wikipedia infobox "Handedness:
Right", player-profile pages) says right-handed. The brief also asked for every player's
hand to be verified from reliable sources, so the sources win over the brief. If you know
otherwise, change one line in `config/players.toml`; every zone label flips automatically.

### D3. Zones are recomputed from court metres, not taken from the dataset's `*_area` codes
The dataset's 1-16 area codes are undocumented and side-relative. Recomputing from the
homography-projected coordinates gives one definition, in metres, that also applies to our
own footage in M2.

### D4. Placeholder rallies are kept but flagged
175 ShuttleSet rallies (and ~100 in ShuttleSet22) consist of one "unknown" stroke with no
outcome while the score still advances. They are loaded (so score-before is right for the
next rally and the winner is inferred from the scoreboard) and marked `annotated=False`;
every analysis excludes them. They are never counted as rally length 1.

### D5. Rallies containing unknown shot types are excluded from sequence analyses only
Rally length and outcome are still valid when one stroke's type is unknown, so those rallies
stay in the length analysis and in the score bookkeeping, and are dropped only where the
shot sequence itself is the variable. This follows the dataset authors' preprocessing, which
drops such rallies entirely for their forecasting benchmarks.

### D6. Receiver half is derived from positions, with fallbacks
Hitter's own feet position relative to the net, else the receiver's position flipped, else
the same player's other strokes in the rally, else the opponent's half flipped. Nobody
changes half within a rally, so the rally-level fallbacks are exact when available.

### D7. Score before the rally = score after minus the winner's point
The CSV stores the score after the point is awarded (first rally of every game reads 1-0 or
0-1). Subtracting the winner's point is exact whenever the winner is known; the
`score_gap` flag records the rare rows where this disagrees with the previous rally's score.

### D8. Zone thresholds kept at the brief's values; evidence recorded
`uv run python scripts/zone_diagnostics.py` (outputs/diagnostics/). Landing depth of in-play
strokes is tri-modal: net play peaks at 0.8-1.5 m, smashes at 3.5-4.2 m, clears/lobs at
5.5-6.2 m. The valley between mid and rear is 4.5-5.0 m, so the **5.0 m split is defensible**;
90.1% of clears/lobs land beyond it and the 10% that land short are genuinely short lifts a
coach wants to see as "mid". The front/mid valley is at ~2.9 m rather than 1.98 m: 1.98 m is a
real line (short service line) and is kept, but a 2.5-3.0 m front boundary would separate net
play from mid-court play more cleanly. **Suggested alternative: front 0-2.5 m.**
Body radius: at 0.5 m, 712 in-play strokes (1.1%) are body shots, 4.5% of smashes and 5.0% of
drives, which is the expected signature. Position noise: the hitter's recorded feet are a median
0.80 m (p75 1.12 m) from the contact point, so 0.5 m is below normal reach and captures only
genuinely jammed shots. **Suggested alternative: 0.75 m (1,626 strokes, 2.5%)** if sample size
matters more than purity. Defaults unchanged.

### D9. "Last 2-3 shots before the point ended" = the strokes before the final stroke
Conditioning on the final stroke is circular (an error loses, a winner wins). The sequence is
therefore the k strokes before the final one; the final stroke is reported separately as counts
("How points end": own winner / opponent error / own error / opponent winner).

### D10. Danger conditions exclude the `out` and `net_error` zones
Those are outcomes of the stroke, not targets. Including them only rediscovers that errors lose
points (the first run of the report had "shots to out" as insight 1).

### D11. "Score pressure" = either player at 18 or more when the rally starts
Simple, matches the brief's "18+ points", and avoids a second parameter. Configurable with
`--pressure`.

### D12. Shrinkage prior strength = 20 rallies
Beta-binomial toward the player's own baseline. 20 pseudo-rallies means a 5/6 pattern reports
~58% against a 50% baseline while 50/60 keeps ~69%. Ranking uses the shrunk value.

### D13. Top-5 selection rule
Candidates must have n >= 30 and a 95% Wilson interval that excludes the baseline; ranked by
|lift| x sqrt(n); at most two per analysis family so one table cannot fill the list.

### D14. Holdout = ShuttleSet22's published validation + test match ids
14 matches (ids 38-40, 46-50, 52-57 of ShuttleSet22). Chosen by the dataset authors before we
ran anything. Axelsen has 2 matches in it (`tactics players` prints the count per player).

### D15. M3 is reported in three settings, not one
The first run trained on all prefixes and evaluated by slice, and every model sat at chance
(AUC 0.50-0.54). A diagnostic showed why: the strongest signal in pro singles is parity, "the
player who hit the stroke before the decisive one wins 65%", and a model that does not know the
rally is about to end cannot use it. So the experiment now reports (a) **live**: all prefixes,
the rally end unknown; (b) **pre-final**: the n-1 strokes before the decisive stroke; (c)
**full, final zone masked**: all n strokes with the last stroke's landing zone hidden, the
closest honest analogue of the Shot Influence paper's input. Each setting has base-rate and
"last hitter wins" heuristics next to the models.

### D16. Lint policy: format at 100 columns, flag only lines over 120
`ruff format` wraps code at 100; the remaining long lines were report sentences in f-strings,
which read worse when split. `max-line-length = 120` in pyproject keeps E501 meaningful.

### D17. TrackNetV3: import only `model.py`, re-implement preprocessing and decoding
The upstream `predict.py` pulls in `test.py` (pycocotools), `dataset.py` (parse) and torch 1.10
pins. The network class is pure PyTorch, so the wrapper imports just that and mirrors the 40
lines of preprocessing (median background, 288x512 resize, channel stacking) and heatmap
decoding (largest contour centre). Verified end to end on a synthetic clip: 28/48 frames
detected, median error 2.4 px, 100% within 15 px (`tests/test_tracknet.py`).

### D18. Two early commits still carry a `Co-Authored-By: Claude` trailer — RESOLVED 2026-11-04
Stripping it needs a history rewrite and a force-push, which the session's safety rules blocked.
Every later commit is trailer-free. To clean the first two (safe: private repo, no other
contributors):

    git filter-branch -f --msg-filter 'grep -v Co-Authored-By' -- main overnight-1
    git push --force origin main overnight-1

Resolved: the user approved the rewrite; `git filter-branch --msg-filter "sed '/Co-Authored-By/d'"`
was run over main, overnight-1 and insights-v2, verified with
`git log --all --format='%h %(trailers:key=Co-Authored-By)'`, and main + overnight-1 were
force-pushed. New heads: main 12e5e15, overnight-1 8be9d7d.

## features-v3 branch (Phase 3, 2026-11-04 evening)

### D19. Every rate is compared with "typical pros": the same pattern over all other players
The reference for "shots faced" is every stroke whose receiver is another player; for "shots
played" every stroke whose hitter is another player. Exclusion is by ROLE, not by match: the
player's opponents facing the player's shots are other pros facing that pattern, so they stay in
the reference. The difference carries Newcombe's hybrid-score 95% interval (checked against the
1998 paper's example 56/70 vs 48/80 -> 0.0524..0.3339). Candidates need n >= 30 on both sides and
an interval that excludes zero; they are ranked by the interval bound nearest zero, i.e. the
smallest difference the data still supports. This replaces ranking by shrunk lift over the
player's own baseline (D12/D13): shrinkage is still computed but no longer drives anything, and
"opponents' smashes hurt" has gone from insight 2 to "Axelsen loses less after smashes than
typical pros", which is the player-specific statement.

For the symmetric win-rate splits (rally length, game number, pressure, serving) the population
is 50% by construction (each rally has one winner and one loser), so their reference is the
player's own overall rate and they are shown as context, never ranked.

### D20. Top insights come only from actionable tables
"Point decided right after P:lob > O:smash" conditions on the rally ending, and rally-length or
game-number effects give a coach nothing to say between points. The ranked top-5 and the two
coach sections ("how to play against", "what to fix") therefore draw only from the danger tables
(shot type x zone, shot alone, zone alone; all data, game 3, 18+). The setups, endings and
splits remain in the report as a descriptive section with their own typical-pro comparison.
Shots of unknown type are excluded from the danger tables.

### D21. Position maps: own-half frame, not mirrored for handedness, axis labelled FH/BH
Positions are expressed as metres from the net into the player's half and metres from the
centre line toward the player's own RIGHT. They are not mirrored for left-handers because base
position is about court geometry (the centre line, the service lines); instead the figure and
the text label the lateral axis with the player's forehand and backhand side from
config/players.toml, so "pulled to the backhand" reads correctly for every player. The frame
also provides `lat_fh` for anyone who wants the mirrored view. Everything is named "position
map", never "footwork", because ShuttleSet has positions only at hit time; the distance per
rally is the straight line between consecutive own-hit positions and is reported as a lower
bound. Base position = median receive position when the opponent hits a non-serve stroke;
"pull" = distance from that base to where the reply was hit, by the opponent's shot type.
Means carry t-intervals and differences Welch intervals.

### D22. Habits, predictability and set plays
* A habit is a reply share compared with other pros in the SAME situation (incoming shot type
  and zone from the replier's view), never with the player's own average reply: "smashes a lot"
  is not a habit, "smashes 75% of clears to the rear backhand when typical pros smash 37%" is.
  Situations are offered at two granularities (shot -> zone, shot -> any) because zone-level
  cells are often under n = 30.
* Predictability uses Shannon entropy with the Miller-Madow correction. Plug-in entropy is
  biased low for small n, and so is the corrected value to a lesser degree, so the population is
  never compared at its full n: its replies are SUBSAMPLED to the player's n (200 draws) and the
  player's entropy is judged against that band. Reply = shot and target zone; replies that ended
  the rally with an error are excluded (an error is an outcome, not a choice).
* Set plays are the first 3 and 4 strokes as shot types, split by who served, ranked by the
  difference in share versus other pros in the same role. The win rate is shown but does not
  drive the ranking: with 30-200 rallies per opening its interval is wide.


### D23. xP: two models, pre-landing for every per-player claim; rally-level intervals
* xP-pre sees only what is known before the shuttle lands and is used for every per-player
  number. xP-post adds the landing and is trained and scored on non-final strokes only, because
  a final stroke's landing is the outcome; even clipping leaks (net errors become tight-net
  landings). The leak is measured and reported (AUC 0.986 on final strokes with the zone
  visible, `docs/XP.md`).
* Hyper-parameters and the model family per feature set are chosen on a match-level validation
  split inside the development matches; the 14 holdout matches are scored once.
* Result: xP from shot and position data has no signal mid-rally in elite singles (holdout AUC
  0.50 on non-final strokes); the 0.79 on final strokes is classifying how an already-decisive
  stroke ends, not a working xP model, and every doc leads with the negative result (review fix,
  2026-11-04). The report says so first, shows "vs own overall" next to "vs typical
  pros", and adds a Finishing table (final strokes) where the model has signal. Per-player
  intervals are over rallies, not strokes: all of a player's strokes in a rally share its outcome.
* xP added keeps the model's value of the final stroke as the terminal state (not the realised
  point), so it measures what the model believed, not hindsight; with a chance-level model it is
  small by construction and labelled as such.

### D24. No live advantage bar: the state-feature experiment failed its pre-set bar
Pass condition was live-prefix AUC >= 0.60 on the holdout. Logistic regression with the last
two strokes' state reached 0.498, the GRU with state per stroke 0.491 (0.488 regularised).
Per the brief, the result is reported in `docs/M3_BASELINE.md` and the bar is not built; the
report's momentum view is xP per shot. The code stays (`src/tactics/live_state.py`,
`scripts/live_state.py`) so the experiment can be re-run when richer per-stroke features exist
(shuttle speed, timing, contact height in metres).

### D25. Replication: three schemes, one verdict rule, reference = typical pros
The holdout scheme keeps ShuttleSet22's published split but tests each insight against the
typical-pro reference it was selected on (not the player's own baseline, which the v2 ranking no
longer uses). Two leave-one-out schemes were added because 1-3 holdout matches per player left
most zone-level claims untestable: leave-one-match-out (select on the other matches, score the
pattern on the held-out match, pool over the folds that selected it) and leave-one-opponent-out
(all matches against one opponent held out, which catches "this is really one opponent's
style"). Verdicts: REPLICATES (same direction and the Newcombe interval of the out-of-sample
difference excludes zero), SAME DIRECTION (same sign, interval includes zero), FAILS (opposite
sign), UNTESTABLE (< 10 out-of-sample instances). SAME DIRECTION is reported separately rather
than folded into either neighbour. The selection count per fold is shown as a stability measure.

### D26. Threshold sensitivity: front 2.5 m barely matters, body 0.75 m does
`scripts/threshold_sensitivity.py` re-annotates with the D8 alternatives and recomputes the
top-5 for the five evaluated players (25 insights). Front/mid at 2.5 m keeps 22 of 25; body at
0.75 m keeps 16 of 25; both together 14 of 25 (`outputs/sensitivity.md`). The body radius
decides which strokes count as "to the body" and therefore moves body-zone rows in and out of
the top-5, so body-zone insights should be read as "at 0.5 m" claims. Defaults unchanged; the
report states the thresholds it used.

## Review fixes before the merge (2026-11-04, late)

### D27. Top insights are ranked only if their selection is stable; tentative flag
* The report's top-5 now comes from the 10 best-ranked candidates on the full data, keeping
  only those selected in at least 50% of the leave-one-match-out folds (the top-5 re-selected
  once per match of the player, same folds and same k as `tactics evaluate`, so the "selected
  in X of N folds" counts agree between the report and `docs/EVALUATION.md`). Patterns the
  plain top-5 would have shown but that fail the rule are listed under "Less stable" with their
  fold counts, as candidates rather than findings; stable patterns ranked 6-10 move up.
* Any ranked insight whose Newcombe interval on the difference is wider than 20 points or
  whose n is under 60 is flagged `tentative`. The thresholds are constants in `report.py`
  (`MIN_STABLE_SHARE`, `TENTATIVE_CI_WIDTH`, `TENTATIVE_MIN_N`).
* `tactics evaluate` still scores the plain data-ranked top-5 (it is what the stability check
  is computed on; filtering by stability inside the evaluation would be selecting on the test).
  `tactics report --no-stability` skips the folds (about 1 minute for a 20-match player).
* Reason: the leave-one-out results showed several top-5 rows selected in only half of the
  folds; a coach reading the top-5 should see that, not discover it in the evaluation doc.

## web-ui branch (Milestone 4a, 2026-11-04/05)

### D28. Web UI: static export of precomputed JSON; the site computes nothing
* `scripts/export_web.py` writes `web/public/data/index.json` and one file per player with at
  least 3 matches, using the same functions as the Markdown report (`webexport.py` only reshapes
  tables into records). The replication schemes are run for players with at least 9 matches (six
  players: the five of `docs/EVALUATION.md` plus Kento Momota, so the Methods page totals differ
  from that document) and stored in `index.json` for the Methods page; the
  live-advantage verdicts are read from `outputs/m3/live_state*.json` if present, never recomputed.
* The Next.js site (`web/`, App Router, TypeScript, Tailwind v4) is built with `output: "export"`,
  reads the JSON at build time, and contains no arithmetic beyond number formatting. Rule: the UI
  never shows a number the export did not produce. The JSON is committed so a Vercel build needs
  neither the dataset nor Python.
* Honesty marks: every rate shows n and its 95% interval; `tentative` and `less stable` are text
  badges with an icon; court zones whose interval includes zero are hatched; the body zone is
  drawn as a circle at the player's base position and labelled as receiver-relative.
* Colour: the reference data-viz palette (blue sequential ramp, blue <-> red diverging pair with a
  grey midpoint, separate dark-mode steps); meaning is always also carried by text or pattern.
* Lighthouse (2026-11-04, `npx lighthouse http://localhost:3999/<page> --only-categories=accessibility,best-practices,performance --chrome-flags=--headless=new` against `npx serve out -l 3999` after `npm run build`): accessibility 100 on `/`, `/players/viktor-axelsen/` and `/methods/` (target: >= 90); best practices 96 on all three, the only failing audit being console 404s for Next's segment-prefetch `.txt` files under `serve`, which does not affect the pages; performance 100 / 98 / 100. Horizontal overflow checked at 390 px with puppeteer-core: scrollWidth equals the viewport on all three pages.

### D29. Plain language first; one situation, one card; "possible" is not "confident" (2026-11-05)
* **Scouting summary.** Each report and player page opens with up to four one-sentence takeaways
  in coach language and without numbers (`report.takeaways`), generated only from top insights
  that are stable (selected in at least half of the leave-one-match-out folds) and not
  tentative. On the site the n, the rate against typical pros, the difference with its interval
  and the fold count sit behind a "Show the numbers" toggle on every item; the same numbers stay
  in the evidence tables. Players with no stable, non-tentative insight get a sentence saying so
  rather than a weaker takeaway.
* **Coach cards without repeats.** A weakness used to appear both as "push to his rear backhand"
  under *How to play against* and as "defending pushes to the rear backhand" under *What to fix*.
  Now the weaknesses live once, as training priorities under *What <player> should fix*, and
  *How to play against* lists the strengths (what an opponent should not do) plus one line that
  points at the training priorities as the places to attack. Rule: a situation appears on one
  card only; the other card refers to it.
* **"With 95% confidence" means clearing zero by half a point.** The candidate flag in
  `stats.py` is strict (`delta_lo > 0` or `delta_hi < 0`), but a bound of +0.4 points prints as
  "+0", and a reader who sees "+0 to +14" next to "with 95% confidence" is right to object.
  `report.borderline` marks candidates whose bound nearest zero is below `BORDERLINE_PTS`
  (0.005); they are excluded from both cards and listed under *Possible, not confident* with the
  reason. Zero bounds print as "0" (never "-0"). Tested in `tests/test_report.py`.
* **Landing page.** A hero with one sentence, three headline cards (the demo player's first
  takeaway, the xP negative result, the replication totals for all three schemes) and the data
  credit, all read from the export; the README's recruiter section repeats the same three with
  the numbers and a screenshot of the Axelsen page (`docs/screenshot-player.png`).
* Checks (2026-11-05, after `python scripts/export_web.py` (1035 s, 27 players) and `npm run build`,
  against `npx serve out -l 3999`): `npx lighthouse http://localhost:3999/<page>
  --only-categories=accessibility,best-practices,performance --chrome-flags=--headless=new` gives
  accessibility 100 on `/`, `/players/viktor-axelsen/` and `/methods/`; best practices 96 on all
  three (the console 404s for Next's segment-prefetch `.txt` files under `serve`, as in D28);
  performance 98 / 96 / 99. Horizontal overflow at 390 px with puppeteer-core: scrollWidth equals
  the viewport on all three pages. `docs/screenshot-player.png` is the Axelsen page at 1280 px
  from the same build with the first "Show the numbers" toggle open.
