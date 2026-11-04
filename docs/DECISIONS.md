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

