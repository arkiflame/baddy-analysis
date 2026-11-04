"""Milestone 3 baseline runner: rally-outcome prediction from stroke prefixes.

    uv run python scripts/m3_baseline.py [--epochs 30] [--seeds 0 1 2] [--cpu]

Writes outputs/m3/results.json and outputs/m3/results.md (the tables docs/M3_BASELINE.md quotes).
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time

import pandas as pd

from tactics.config import PROJECT_ROOT, load_zone_config
from tactics.loader import load_strokes
from tactics.outcome_model import GRUConfig, run_experiment
from tactics.zones import annotate

OUT = PROJECT_ROOT / "outputs" / "m3"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--cpu", action="store_true")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    df = annotate(load_strokes(), load_zone_config())
    cfg = GRUConfig(epochs=args.epochs, device="cpu" if args.cpu else "auto")
    res = run_experiment(df, cfg, seeds=tuple(args.seeds))
    res["wall_seconds"] = time.time() - t0
    res["command"] = "python scripts/m3_baseline.py " + " ".join(sys.argv[1:])
    res["platform"] = platform.platform()

    table: pd.DataFrame = res["table"]
    show = table.copy()
    for c in ("accuracy", "log_loss", "brier", "auc"):
        show[c] = show[c].map(lambda v: f"{v:.3f}")
    timing = ", ".join(f"{k} {v:.0f} s" for k, v in res["timing"].items())
    md = [
        "# M3 baseline results\n",
        f"Command: `{res['command']}`  ",
        f"Device: {res['device']}; wall time {res['wall_seconds'] / 60:.1f} min ({timing})\n",
        "## Settings\n",
        "\n".join(f"- **{k}**: {v}" for k, v in res["settings"].items()),
        "\n\n## Data\n",
        pd.Series({k: v for k, v in res["counts"].items() if not isinstance(v, dict)}).to_frame("value").to_markdown(),
        f"\n\nP(server wins | last pre-final stroke by server / receiver), train: "
        f"{res['counts']['last_hitter_rates_prefinal_train']}\n",
        "\n## Metrics on the 14 holdout matches\n",
        show.to_markdown(index=False),
        "\n\n## GRU config\n",
        pd.Series(res["gru_config"]).to_frame("value").to_markdown(),
        "\n\n## GRU validation curves (seed 0)\n",
    ]
    for key, hist in res["gru_histories"].items():
        if key.endswith("seed0"):
            md.append(f"\n{key}\n\n" + pd.DataFrame(hist).to_markdown(index=False))
    (OUT / "results.md").write_text("\n".join(md), encoding="utf-8")
    dump = {k: v for k, v in res.items() if k != "table"}
    dump["table"] = table.to_dict(orient="records")
    (OUT / "results.json").write_text(json.dumps(dump, indent=2, default=str), encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
