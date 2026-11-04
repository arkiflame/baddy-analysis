"""Court calibration: four clicks -> homography in ShuttleSet's convention.

    uv run python -m tactics.tools.calibrate_court VIDEO --out data/own/homography.csv [--frame 0]

Click the court corners in this order: far-left, far-right, near-left, near-right (as seen on
screen, "far" = the end away from the camera). Press `u` to undo a click, `r` to reset,
`Enter` to save, `q` to quit without saving.

The homography maps camera pixels onto the same 300 x 660 canvas ShuttleSet uses (corners at
(25,150), (325,150), (25,810), (325,810)), so everything downstream (court.py, zones) works on
our footage without changes. The pure function `homography_from_corners` is testable without a
display.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from tactics.court import CANVAS_ORIGIN, CANVAS_SIZE

CORNER_NAMES = ("upleft", "upright", "downleft", "downright")


def canvas_corners() -> np.ndarray:
    x0, y0 = CANVAS_ORIGIN
    w, h = CANVAS_SIZE
    return np.array([[x0, y0], [x0 + w, y0], [x0, y0 + h], [x0 + w, y0 + h]], dtype=float)


def homography_from_corners(corners_px: np.ndarray) -> np.ndarray:
    """3x3 matrix H with  canvas = H @ pixel  (homogeneous), from 4 pixel corners."""
    import cv2

    src = np.asarray(corners_px, dtype=np.float32).reshape(4, 2)
    dst = canvas_corners().astype(np.float32)
    h, _ = cv2.findHomography(src, dst)
    if h is None:
        raise ValueError("degenerate corners: cannot compute a homography")
    return h / h[2, 2]


def homography_row(video: str, corners_px: np.ndarray, match_id: int = 1) -> dict:
    """One row in ShuttleSet's homography.csv format."""
    h = homography_from_corners(corners_px)
    c = np.asarray(corners_px, dtype=float).reshape(4, 2)
    row = {"id": match_id, "video": video, "homography_matrix": json.dumps(h.tolist())}
    row.update({f"{n}_x": float(c[i, 0]) for i, n in enumerate(CORNER_NAMES)})
    row.update({f"{n}_y": float(c[i, 1]) for i, n in enumerate(CORNER_NAMES)})
    return row


def append_row(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([row])
    if path.exists():
        old = pd.read_csv(path)
        old = old[old.video != row["video"]]
        df = pd.concat([old, df], ignore_index=True)
    df.to_csv(path, index=False)


def grab_frame(video: Path, index: int) -> np.ndarray:
    import cv2

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise FileNotFoundError(video)
    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise ValueError(f"could not read frame {index} of {video}")
    return frame


def interactive(video: Path, out: Path, frame_index: int, match_id: int) -> int:
    import cv2

    frame = grab_frame(video, frame_index)
    clicks: list[tuple[int, int]] = []
    win = "calibrate court: click far-left, far-right, near-left, near-right"

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(clicks) < 4:
            clicks.append((x, y))

    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(win, on_mouse)
    while True:
        img = frame.copy()
        for i, (x, y) in enumerate(clicks):
            cv2.circle(img, (x, y), 6, (0, 0, 255), -1)
            cv2.putText(
                img, CORNER_NAMES[i], (x + 8, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2
            )
        if len(clicks) == 4:
            order = [0, 1, 3, 2, 0]
            for a, b in zip(order, order[1:], strict=False):
                cv2.line(img, clicks[a], clicks[b], (0, 255, 0), 2)
        cv2.putText(
            img,
            f"{len(clicks)}/4 corners  [u]ndo [r]eset [Enter]=save [q]uit",
            (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )
        cv2.imshow(win, img)
        key = cv2.waitKey(30) & 0xFF
        if key == ord("q"):
            cv2.destroyAllWindows()
            return 1
        if key == ord("u") and clicks:
            clicks.pop()
        if key == ord("r"):
            clicks.clear()
        if key in (13, 10) and len(clicks) == 4:
            break
    cv2.destroyAllWindows()
    row = homography_row(video.stem, np.array(clicks), match_id)
    append_row(out, row)
    print(f"saved homography for {video.stem} to {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("video", type=Path)
    ap.add_argument("--out", type=Path, default=Path("data/own/homography.csv"))
    ap.add_argument("--frame", type=int, default=0)
    ap.add_argument("--match-id", type=int, default=1)
    a = ap.parse_args(argv)
    return interactive(a.video, a.out, a.frame, a.match_id)


if __name__ == "__main__":
    sys.exit(main())
