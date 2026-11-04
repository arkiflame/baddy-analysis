"""Live advantage experiment (Phase 3 E): state features on live rally prefixes, pass/fail.

    uv run python scripts/live_state.py [--epochs 30] [--seeds 0 1 2] [--cpu]

Writes outputs/m3/live_state.md and live_state.json. Pass condition: live-prefix AUC >= 0.60
on the 14 holdout matches. docs/M3_BASELINE.md quotes the result.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys

import pandas as pd

from tactics import live_state
from tactics.config import PROJECT_ROOT, load_zone_config
from tactics.loader import load_strokes
from tactics.outcome_model import GRUConfig
from tactics.zones import annotate

OUT = PROJECT_ROOT / "outputs" / "m3"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--cpu", action="store_true")
    ap.add_argument("--hidden", type=int, default=64)
    ap.add_argument("--dropout", type=float, default=0.2)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--tag", default="", help="suffix for the output file names")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    cfg = load_zone_config()
    df = annotate(load_strokes(), cfg)
    gru_cfg = GRUConfig(
        epochs=args.epochs,
        device="cpu" if args.cpu else "auto",
        hidden=args.hidden,
        dropout=args.dropout,
        lr=args.lr,
    )
    res = live_state.run_experiment(df, cfg, gru_cfg, seeds=tuple(args.seeds))
    command = "python scripts/live_state.py " + " ".join(sys.argv[1:])

    show = res["table"].copy()
    for c in ("accuracy", "log_loss", "brier", "auc"):
        show[c] = show[c].map(lambda v: f"{v:.3f}")
    verdict = "PASS" if res["pass"] else "FAIL"
    md = [
        "# Live advantage experiment: state features on live prefixes\n",
        f"Command: `{command}`  ",
        f"Device: {res['device']}; platform {platform.platform()}; wall time "
        f"{res['timing']['total_seconds'] / 60:.1f} min (logistic {res['timing']['logistic_seconds']:.0f} s, "
        f"GRU {res['timing']['gru_seconds']:.0f} s for {len(args.seeds)} seeds)\n",
        f"## Verdict: **{verdict}** (best live-prefix AUC {res['best_live_auc']:.3f}, "
        f"pass bar {res['pass_auc']:.2f})\n",
        "## Data\n",
        pd.Series({k: v for k, v in res["counts"].items() if not isinstance(v, list)})
        .to_frame("value")
        .to_markdown(),
        f"\n\nState features per stroke: {', '.join(res['counts']['state_features'])}\n",
        "## Holdout metrics (live prefixes, 14 matches)\n",
        show.to_markdown(index=False),
        "\n\n## GRU config\n",
        pd.Series(res["gru_config"]).to_frame("value").to_markdown(),
        "\n\n## GRU validation curve (seed 0)\n",
        pd.DataFrame(res["gru_histories"]["seed0"]).to_markdown(index=False),
    ]
    (OUT / f"live_state{args.tag}.md").write_text("\n".join(md), encoding="utf-8")
    dump = {k: v for k, v in res.items() if k != "table"}
    dump["table"] = res["table"].to_dict(orient="records")
    dump["command"] = command
    (OUT / f"live_state{args.tag}.json").write_text(
        json.dumps(dump, indent=2, default=str), encoding="utf-8"
    )
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
