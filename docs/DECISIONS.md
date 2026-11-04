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
