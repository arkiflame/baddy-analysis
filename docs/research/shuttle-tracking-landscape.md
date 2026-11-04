# Shuttle tracking landscape (for Milestone 2)

Verified 2026-11-04 by fetching each repo's LICENSE / README. Kept here so M2 can start from
a vetted shortlist instead of re-researching. Items marked UNVERIFIED could not be confirmed.

## Shortlist

| Model | Framework | License | Badminton weights | Reported badminton accuracy | Notes |
|---|---|---|---|---|---|
| **TrackNetV3** (Chen & Wang, MMAsia 2023) <https://github.com/qaz812345/TrackNetV3> | PyTorch | MIT (code + checkpoints per README) | Yes: Google Drive `TrackNetV3_ckpts.zip` (`TrackNet_best.pt`, `InpaintNet_best.pt`); checksummed mirror at <https://github.com/Agastyasingh1106/Badminton-AI/releases/tag/tracknetv3-weights> | Acc 97.5 / P 97.8 / R 99.3 / F1 98.6 on the Shuttlecock Trajectory Dataset test split | 8-frame input + median-background, 288x512; `predict.py --video_file` writes CSV + overlay. Pinned to torch 1.10 but runs on torch 2.x with cosmetic fixes. CPU works with `map_location='cpu'`. Users report ~3 FPS on a T4 (issue #9) |
| **WASB-SBDT** (Tarashima et al., BMVC 2023) <https://github.com/nttcom/WASB-SBDT> | PyTorch | MIT (checkpoint license question open in issue #12) | Yes, 7 architectures incl. TrackNetV2, MonoTrack detector, WASB (MODEL_ZOO.md) | WASB F1 93.1 / Acc 89.0 at tau=4 px on the TrackNetV2 set | Best-engineered codebase, but no custom-video inference script (community one: indicium15/wasb-sbdt-inference, no LICENSE) |
| TrackNetV4 (ICASSP 2025) <https://github.com/TrackNetV4/TrackNetV4> | TensorFlow | MIT | **No**: official download links are placeholders (issues #1, #4 open since 2025) | +0.3 F1 over V3 | Skip |
| TrackNetV5 (two unrelated 2025/26 preprints, NYCU and Tang et al.) | - | - | No code | F1 ~98.5 | Skip until released |
| MonoTrack (CVPRW 2022) | - | - | 2D detector only, via WASB | F1 90.9 (WASB eval) | No official repo; 3D reconstruction not released |
| ETH one-shot YOLOv8 shuttle detector (2026) <https://github.com/leggedrobotics/shuttle_detection> | Ultralytics | AGPL-3.0 | Yes (`runs/final-model/best.pt`) + 20.5k-frame amateur/moving-camera dataset | F1 0.86 similar venues / 0.70 unseen | Only option trained on non-broadcast, moving-camera footage. AGPL |
| Community YOLO11s <https://huggingface.co/Huydinh1205/shuttle_yolo11s> | Ultralytics | AGPL-3.0 | Yes | mAP50 0.71 | Weak |

Original TrackNet / TrackNetV2 GitLab (nol.cs.nctu.edu.tw) was unreachable; unofficial
PyTorch ports (ChgygLin, wolfyeva) have no LICENSE file, so do not copy their code.

## Datasets with shuttle pixel coordinates

| Dataset | Content | License |
|---|---|---|
| Shuttlecock Trajectory Dataset (NYCU, "TrackNetV2 dataset") <https://hackmd.io/Nf8Rh1NrSrqNUzmO0sQKZw> | ~78k broadcast frames, per-frame `Frame, Visibility, X, Y`; includes 3 amateur matches | **None stated**; BWF broadcast frames, do not redistribute |
| ETH shuttlecockfinder <https://drive.google.com/drive/folders/1neBfC7-Fp-l53muxZiIbIET6lYH5xv9s> | 20,510 bbox-labelled frames, 11 amateur venues | None stated for data |
| BadmintonDB <https://github.com/kwban/badminton-db> | 9 matches, stroke-level ELAN annotations | No LICENSE file |

ShuttleSet / ShuttleSet22 have **no per-frame shuttle positions** (one row per stroke).

## Implications for M2

1. Start with TrackNetV3 weights (MIT, best accuracy, inference script exists). Wrap it,
   do not fork it; credit it in the README.
2. All TrackNet-family weights assume a static camera at the broadcast angle; V3's
   median-background input breaks on handheld video. Shoot from a tripod behind the baseline,
   and expect to fine-tune on a few hundred hand-labelled frames from our own gym.
3. For moving phone footage the ETH YOLOv8 model is the only trained option, at the cost of
   AGPL-3.0 and lower accuracy. Decide per use case.
4. Accuracy numbers across papers use different protocols (V2-style "accuracy" with true
   negatives vs F1 at a pixel tolerance). Report the protocol with any number we publish.
5. Dataset licensing, not model licensing, is the portfolio risk: use the NYCU frames for
   training/eval only, never commit or re-host them.
