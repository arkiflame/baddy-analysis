"""Evidence for the zone thresholds in config/zones.toml.

Produces (into outputs/diagnostics/):
  * landing_depth_hist.png   histogram of landing depth from the net, overall and per shot family
  * body_shots.md            body-shot counts at several radii, by shot type
and prints a text summary. Run:  uv run python scripts/zone_diagnostics.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from tactics.config import PROJECT_ROOT, load_zone_config  # noqa: E402
from tactics.loader import load_strokes  # noqa: E402
from tactics.zones import annotate  # noqa: E402

OUT = PROJECT_ROOT / "outputs" / "diagnostics"
SERIES = {"clear / lob": "#2a78d6", "smash": "#eb6834", "drop / net": "#1baf7a", "drive / push": "#eda100"}
FAMILY = {
    "clear": "clear / lob", "lob": "clear / lob",
    "smash": "smash",
    "drop": "drop / net", "net": "drop / net",
    "drive": "drive / push", "push_rush": "drive / push",
}


def ascii_hist(values: np.ndarray, edges: np.ndarray, width: int = 50) -> str:
    counts, _ = np.histogram(values, bins=edges)
    top = counts.max() or 1
    lines = []
    for lo, hi, c in zip(edges[:-1], edges[1:], counts, strict=True):
        bar = "#" * int(round(width * c / top))
        lines.append(f"{lo:4.1f}-{hi:4.1f} m |{bar:<{width}}| {c}")
    return "\n".join(lines)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = load_zone_config()
    df = annotate(load_strokes(), cfg)
    d = df[df.annotated & ~df.is_serve & df.depth.notna()]
    in_play = d[~d.is_last]          # landing = where the receiver struck it: a clean "depth reached"
    enders = d[d.is_last]

    print(f"strokes with a landing point: {len(d)}  (in-play {len(in_play)}, rally-enders {len(enders)})")

    # ---- depth histogram ------------------------------------------------------------------
    edges = np.arange(-0.5, 7.51, 0.25)
    print("\nLanding depth from the net, receiver's side, in-play strokes (negative = did not cross):")
    print(ascii_hist(in_play.depth.to_numpy(), edges))
    split = cfg.coach_bands[1].hi
    for fam in SERIES:
        v = in_play[in_play.shot_coarse.map(FAMILY) == fam].depth
        if len(v):
            print(f"  {fam:13s} n={len(v):6d}  median={v.median():.2f} m  p10={v.quantile(.1):.2f}  p90={v.quantile(.9):.2f}  share beyond {split} m = {(v > split).mean():.1%}")

    fig, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=True, constrained_layout=True)
    axes[0].hist(in_play.depth, bins=edges, color="#2a78d6", edgecolor="white", linewidth=0.5)
    axes[0].set_title("Landing depth from the net (receiver's side), all in-play strokes", loc="left", fontsize=11)
    axes[0].set_ylabel("strokes")
    for ax in axes:
        for b in cfg.coach_bands[1:]:
            ax.axvline(b.lo, color="#52514e", linestyle="--", linewidth=1)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#e5e4df", linewidth=0.6)
        ax.set_axisbelow(True)
    for fam, colour in SERIES.items():
        v = in_play[in_play.shot_coarse.map(FAMILY) == fam].depth
        axes[1].hist(v, bins=edges, histtype="step", linewidth=2, color=colour, label=fam)
    axes[1].set_title("By shot family (dashed lines = coach zone splits)", loc="left", fontsize=11)
    axes[1].set_xlabel("depth from net (m)")
    axes[1].set_ylabel("strokes")
    axes[1].legend(frameon=False)
    fig.savefig(OUT / "landing_depth_hist.png", dpi=130)

    # ---- body shots ------------------------------------------------------------------------
    print("\nBody shots (landing within r of the receiver's position at the time of the hit), in-play strokes:")
    rows = []
    for r in (0.25, 0.5, 0.75, 1.0):
        hit = in_play.dist_to_receiver < r
        rows.append({"radius_m": r, "n_body": int(hit.sum()), "share": f"{hit.mean():.1%}"})
        print(f"  r={r:.2f} m: {hit.sum():6d} strokes ({hit.mean():.1%})")
    radius = cfg.body_radius_m
    body = in_play[in_play.dist_to_receiver < radius]
    by_type = body.shot_coarse.value_counts().rename("body_n").to_frame()
    by_type["share_of_type"] = (by_type.body_n / in_play.shot_coarse.value_counts()).map(lambda v: f"{v:.1%}")
    print(f"\nBody shots at r={radius} m by shot type:")
    print(by_type.to_string())

    # ---- position noise: how far is the hitter's recorded position from the contact point? --
    reach = np.hypot(d.hit_x - d.hitter_x, d.hit_y - d.hitter_y).dropna()
    move = in_play.move_dist.dropna()
    print("\nHitter feet -> contact point distance (reach + annotation noise):")
    print(f"  median={reach.median():.2f} m  p75={reach.quantile(.75):.2f}  p90={reach.quantile(.9):.2f}  p99={reach.quantile(.99):.2f}")
    print("Receiver feet at hit time -> where they struck the next shot (distance moved):")
    print(f"  median={move.median():.2f} m  p25={move.quantile(.25):.2f}  p75={move.quantile(.75):.2f}")

    md = ["# Body-shot counts\n", f"Body radius in config: {radius} m. In-play strokes with positions: {len(in_play)}.\n",
          pd.DataFrame(rows).to_markdown(index=False), "\n\n## By shot type at configured radius\n", by_type.to_markdown()]
    (OUT / "body_shots.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\nwrote {OUT / 'landing_depth_hist.png'} and {OUT / 'body_shots.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
