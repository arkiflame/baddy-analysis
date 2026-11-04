"""End-to-end check of the TrackNetV3 wrapper on a synthetic clip.

A white "shuttle" blob flies along a parabola over a green court-like background. We assert the
pipeline produces one row per frame with the expected columns, and we record how close the
detections are to the truth. The pretrained model was trained on broadcast footage, so the
accuracy on a cartoon clip is a smoke signal, not a benchmark; the assertion on accuracy is
deliberately loose and the measured numbers are printed for the docs.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tactics.tools.tracknet import DEFAULT_WEIGHTS, THIRD_PARTY

cv2 = pytest.importorskip("cv2")
torch = pytest.importorskip("torch")

pytestmark = pytest.mark.skipif(
    not (DEFAULT_WEIGHTS.exists() and (THIRD_PARTY / "model.py").exists()),
    reason="TrackNetV3 weights or source not present",
)


def make_synthetic_video(
    path: Path, n_frames: int = 48, size=(640, 360), fps: int = 30
) -> np.ndarray:
    """Write a clip and return the ground-truth (n_frames, 2) shuttle centre per frame."""
    w, h = size
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    truth = np.zeros((n_frames, 2))
    rng = np.random.default_rng(0)
    for i in range(n_frames):
        frame = np.full((h, w, 3), (40, 110, 40), dtype=np.uint8)  # green floor
        cv2.rectangle(frame, (120, 40), (520, 330), (230, 230, 230), 2)  # court lines
        cv2.line(frame, (120, 185), (520, 185), (230, 230, 230), 2)
        # two static "players"
        cv2.rectangle(frame, (300, 60), (330, 130), (30, 30, 200), -1)
        cv2.rectangle(frame, (310, 240), (340, 320), (200, 30, 30), -1)
        t = i / (n_frames - 1)
        x = 160 + t * 320
        y = 300 - 4 * 220 * t * (1 - t)  # parabola from the near side to the far side
        truth[i] = (x, y)
        cv2.circle(frame, (int(x), int(y)), 4, (255, 255, 255), -1)
        noise = rng.integers(0, 6, size=frame.shape, dtype=np.uint8)
        writer.write(cv2.add(frame, noise))
    writer.release()
    return truth


def test_wrapper_runs_end_to_end(tmp_path):
    from tactics.tools.tracknet import Tracker

    video = tmp_path / "synthetic.mp4"
    truth = make_synthetic_video(video)
    tracker = Tracker.load()
    df = tracker.track(video)

    assert list(df.columns) == ["frame", "x", "y", "visible"]
    assert df.frame.tolist() == list(range(len(truth)))
    assert set(df.visible.unique()) <= {0, 1}
    assert df.x.between(0, 640).all() and df.y.between(0, 360).all()

    vis = df[df.visible == 1]
    err = (
        np.hypot(vis.x - truth[vis.frame, 0], vis.y - truth[vis.frame, 1])
        if len(vis)
        else np.array([])
    )
    print(
        f"\nsynthetic clip: {len(df)} frames, {len(vis)} detections, "
        f"median error {np.median(err) if len(err) else float('nan'):.1f} px, "
        f"within 15 px: {(err < 15).mean() if len(err) else 0:.0%}"
    )
    # loose: the pipeline must detect *something* and at least some detections must be on the blob
    assert len(vis) > 0
    assert (err < 15).mean() > 0.3
