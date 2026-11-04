"""xP (expected points) experiment: fit, holdout metrics, leak check, calibration plot.

    uv run python scripts/xp_baseline.py [--seed 0] [--player "Viktor AXELSEN"]

Writes outputs/xp/results.md, results.json, calibration.png and strokes_xp.csv (per-stroke
xP for the holdout matches). docs/XP.md quotes results.md.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys

import pandas as pd

from tactics import xp
from tactics.config import PROJECT_ROOT, load_zone_config
from tactics.loader import load_strokes
from tactics.report import surname
from tactics.zones import annotate

OUT = PROJECT_ROOT / "outputs" / "xp"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--player", default="Viktor AXELSEN")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    cfg = load_zone_config()
    df = annotate(load_strokes(), cfg)
    res = xp.run_experiment(df, cfg, seed=args.seed)
    img = xp.calibration_plot(res, OUT / "calibration.png")
    px = xp.player_xp(res, args.player)

    val = []
    for (fs, kind), fit in res.fits.items():
        v = fit.validation.copy()
        v.insert(0, "feature_set", fs)
        v.insert(1, "model", kind)
        v["chosen"] = [hp == fit.hp for hp in xp.GRIDS[kind]]
        val.append(v)
    val = pd.concat(val, ignore_index=True)
    for c in ("accuracy", "log_loss", "brier", "auc"):
        val[c] = val[c].map(lambda x: f"{x:.3f}")

    command = "python scripts/xp_baseline.py " + " ".join(sys.argv[1:])
    md = [
        "# xP results\n",
        f"Command: `{command}`  ",
        f"Platform: {platform.platform()}; wall time {res.timing['total'] / 60:.1f} min "
        f"({', '.join(f'{k} {v:.0f} s' for k, v in res.timing.items() if k != 'total')})\n",
        "## Data\n",
        pd.Series(res.counts).to_frame("value").to_markdown(),
        f"\n\nBase rate P(hitter wins) on development strokes: {res.base_rate:.3f}; "
        f"server win rate {res.server_rate:.3f}.\n",
        "## Features\n",
        f"- xP-pre categorical: {', '.join(xp.PRE_CATS)}; numeric: {', '.join(xp.PRE_NUMS)}",
        f"- xP-post adds categorical: {', '.join(c for c in xp.POST_CATS if c not in xp.PRE_CATS)}; "
        f"numeric: {', '.join(c for c in xp.POST_NUMS if c not in xp.PRE_NUMS)}\n",
        "## Hyper-parameter choice (match-level validation split inside the development matches)\n",
        val.to_markdown(index=False),
        f"\n\nChosen per feature set (lowest validation log loss): {res.chosen}\n",
        "## Holdout metrics (14 ShuttleSet22 matches)\n",
        xp.metrics_markdown(res),
        f"\nLeak check: the same post features on ALL strokes with the final stroke's out / net zone "
        f"visible reach AUC {res.leaky_auc:.3f} over all holdout strokes and {res.leaky_auc_final:.3f} on "
        "the final strokes. That number is the outcome re-labelled, not a prediction, which is why "
        "xP-post is restricted to non-final strokes.\n",
        f"![calibration]({img.name})\n",
        f"## {args.player}\n",
        "\n".join(xp.section(px, surname(args.player), res, None)[1:]),
    ]
    (OUT / "results.md").write_text("\n".join(md), encoding="utf-8")
    dump = {
        "command": command,
        "counts": res.counts,
        "timing": res.timing,
        "base_rate": res.base_rate,
        "server_rate": res.server_rate,
        "chosen": res.chosen,
        "leaky_auc": res.leaky_auc,
        "holdout_metrics": res.table.to_dict(orient="records"),
        "validation": {
            f"{fs}/{k}": f.validation.to_dict(orient="records") for (fs, k), f in res.fits.items()
        },
    }
    (OUT / "results.json").write_text(json.dumps(dump, indent=2, default=str), encoding="utf-8")
    hold = res.frame[res.frame.is_holdout]
    hold[
        [
            "match_id",
            "rally_id",
            "stroke_no",
            "hitter",
            "shot",
            "hit_band",
            "hitter_won",
            "xp_pre",
            "xp_post",
        ]
    ].to_csv(OUT / "strokes_xp.csv", index=False)
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
