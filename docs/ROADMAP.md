# Roadmap

Milestone 1 (tactics on ShuttleSet) is done on branch `overnight-1`; see README for results.
Everything below is planned, not started, unless noted.

## M2: own footage -> stroke data (amateur phone video)

Goal: a club match recorded on a phone becomes a ShuttleSet-schema CSV that the M1 analyses
read unchanged, with measured accuracy against hand labels.

Already in place (Phase 5 of the overnight run):
- `tactics.tools.calibrate_court`: 4 clicks -> homography in ShuttleSet's convention.
- `tactics.tools.label_video`: OpenCV labeller for shuttle positions, hit frames, shot types,
  player positions, rally winners; exports the ShuttleSet columns + a TrackNet-format shuttle CSV.
- `tactics.tools.tracknet`: TrackNetV3 (MIT) inference wrapper, proven on a synthetic clip.

Steps:
1. **Record** 3-4 club singles matches from a tripod behind the baseline (the broadcast angle
   TrackNetV3 was trained on), 1080p30 or better. Get consent from both players.
2. **Hand-label** ~300 frames of shuttle positions and every stroke of 2 games with the
   labeller. This is the ground truth for everything else; budget 3-4 hours.
3. **Shuttle tracking**: run TrackNetV3 as is; measure precision/recall/mean pixel error
   against the 300 labelled frames (protocol: hit within 10 px at 1080p, report both the V2-style
   accuracy and F1 at a pixel tolerance). If F1 < 0.8, fine-tune the last blocks on the labelled
   frames (keep InpaintNet frozen). Try the ETH YOLOv8 model (AGPL) only if the camera has to move.
4. **Players and court**: pose estimation (RTMPose or YOLO-pose, check licences) for both
   players; map ankle midpoints through the homography to get `player_location_*` in court
   metres. Track identity across the net by court half.
5. **Hit detection**: a hit is a sharp change in shuttle direction / speed near a player. Start
   with a rule (direction change > 60 degrees within 3 frames and distance to a player < 1.5 m),
   measure against the labelled hit frames (tolerance +-2 frames), then train a small 1-D CNN on
   the trajectory window if the rule's F1 is below 0.85.
6. **Shot classification** (10 coarse types): features = hitter's court position, shuttle speed,
   trajectory apex height proxy, landing position, previous shot. Gradient boosting first;
   report confusion matrix on the labelled strokes. Pro-to-amateur shift is expected: short
   serves, drives and lifts dominate club play.
7. **End-to-end check**: run the M1 report on the auto-extracted strokes and on the hand labels
   for the same game and diff the tables. The difference is the perception error budget.

Risks: moving/shaky phone video (TrackNetV3's median-background assumes a static camera),
lighting in school gyms, two players in similar kit for identity tracking, and the time cost of
labelling. Decision point: if tracking F1 on our footage is < 0.6 after fine-tuning, pivot to a
semi-automatic workflow (model proposes, human corrects in the labeller).

## M3: sequence model to rank patterns

Baseline done (Phase 4, `docs/M3_BASELINE.md`): rally-winner prediction from stroke prefixes
with a match-level split; logistic regression and a GRU against base-rate and heuristic
baselines. Next:
1. Use the model's predicted win probability as a **state value**: the value change caused by a
   stroke (before vs after) is that stroke's influence, which ranks patterns by impact rather
   than by raw win rate. Compare the ranking with the M1 tables.
2. Player conditioning: add a player embedding or per-player fine-tuning; test whether it beats
   the pooled model on the holdout.
3. Calibration: reliability diagrams; shrink toward the base rate where the model is
   over-confident.
4. Re-implement the Shot Influence architecture (ICDM 2021) in our framework for a like-for-like
   comparison, keeping our stricter "no final stroke" protocol.

## M4: FastAPI backend + Next.js dashboard

- API: `POST /matches` (upload CSV or video), `GET /players/{name}/report` (JSON version of the
  Markdown report), `GET /matches/{id}/rallies`. Long jobs (tracking) through a task queue
  (RQ or Celery) with progress polling.
- Dashboard: player page with the top-5 insights, the rate tables with their CIs, the fine-grid
  heatmaps, rally browser with a court-diagram replay from the stroke coordinates.
- Keep the Markdown report as the single source of truth: the API serialises `PlayerReport`,
  the dashboard renders it.

## M5: real users and doubles

- Pilot with the varsity team: 3 players, one match each, a 20-minute feedback session per
  report. Record which insights they agree with (ties into the coach-judgement check in
  `docs/EVALUATION.md`).
- Doubles: two hitters per side changes the data model (hitter identity, partner position) and
  the zones (front/back formation). Add `partner_location_*`, a formation feature (attack vs
  defence), and rotate the analyses to the pair as the unit.
- Deployment: single VM with Docker Compose (API, worker, Postgres, Next.js), GPU optional for
  tracking jobs; nightly re-run of reports.
