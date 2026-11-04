"""Court geometry: pixel -> metre projection and player-relative frames.

Design decisions
----------------
* ShuttleSet gives positions in camera pixels plus a per-match homography H. Applying H maps the
  court onto a fixed 300 x 660 canvas whose corners are (25,150)-(325,810); we verified this on
  every match. A real court is 6.10 m x 13.40 m, so one canvas unit is 6.10/300 m. We convert
  to metres once, in the loader, and never look at pixels again.
* Court frame: x across the court (0 = left edge as seen from the camera), y along the court
  (0 = far baseline, 13.40 = near baseline, net at 6.70). This is the canvas orientation.
* Player frame: a player on the near half (y > net) faces the far end, so their right hand is
  +x; a player on the far half faces the camera, so their right hand is -x. Flipping for
  left-handers gives the forehand side.
"""

from __future__ import annotations

import ast
from typing import Literal

import numpy as np

CANVAS_ORIGIN = np.array([25.0, 150.0])
CANVAS_SIZE = np.array([300.0, 660.0])
COURT_WIDTH_M = 6.10
COURT_LENGTH_M = 13.40
NET_Y_M = COURT_LENGTH_M / 2
CENTRE_X_M = COURT_WIDTH_M / 2
# The canvas is 300 x 660 for a 6.10 x 13.40 m court, so the two axes have slightly different
# scales (0.02033 vs 0.02030 m per unit). Using one scale would stretch the court by 2 cm.
M_PER_UNIT = COURT_WIDTH_M / CANVAS_SIZE[0]
M_PER_UNIT_XY = np.array([COURT_WIDTH_M, COURT_LENGTH_M]) / CANVAS_SIZE

Half = Literal["far", "near"]
Hand = Literal["left", "right"]


def parse_homography(text: str) -> np.ndarray:
    """ShuttleSet stores H as the Python repr of a nested list."""
    h = np.array(ast.literal_eval(text), dtype=float)
    if h.shape != (3, 3):
        raise ValueError(f"homography must be 3x3, got {h.shape}")
    return h


def pixels_to_metres(h: np.ndarray, xy_px: np.ndarray) -> np.ndarray:
    """Project (n, 2) pixel coordinates to (n, 2) court metres. NaNs pass through."""
    xy_px = np.asarray(xy_px, dtype=float).reshape(-1, 2)
    ones = np.ones((len(xy_px), 1))
    p = np.hstack([xy_px, ones]) @ h.T
    canvas = p[:, :2] / p[:, 2:3]
    return (canvas - CANVAS_ORIGIN) * M_PER_UNIT_XY


def half_of(y_m: float) -> Half:
    return "far" if y_m < NET_Y_M else "near"


def other_half(half: Half) -> Half:
    return "near" if half == "far" else "far"


def depth_from_net(y_m, half: Half):
    """Distance from the net into `half`. Negative means the point is on the other side."""
    return (NET_Y_M - y_m) if half == "far" else (y_m - NET_Y_M)


def lateral_right(x_m, half: Half):
    """Signed distance from the centre line toward the right hand of a player standing in `half`."""
    return (x_m - CENTRE_X_M) if half == "near" else (CENTRE_X_M - x_m)


def lateral_forehand(x_m, half: Half, hand: Hand):
    """Signed distance from the centre line toward the forehand side of the player in `half`."""
    r = lateral_right(x_m, half)
    return r if hand == "right" else -r
