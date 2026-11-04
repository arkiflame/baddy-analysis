"""Threshold sensitivity: do the top-5 insights change when the zone thresholds move?

    uv run python scripts/threshold_sensitivity.py [--player NAME ...]

Re-annotates the strokes with the alternatives suggested in DECISIONS D8 (front/mid boundary
2.5 m instead of 1.98 m; body radius 0.75 m instead of 0.5 m; both), recomputes each player's
top-5 under the same selection rule, and counts how many of the default top-5 survive.
Writes outputs/sensitivity.md.
"""

from __future__ import annotations

import argparse
import dataclasses
import sys

import pandas as pd

from tactics.analyses import AnalysisSettings, analyse_player
from tactics.config import PROJECT_ROOT, Band, load_zone_config
from tactics.loader import load_strokes
from tactics.report import describe, top_insights
from tactics.zones import annotate

DEFAULT_PLAYERS = ["Viktor AXELSEN", "An Se Young", "CHOU Tien Chen", "CHEN Yufei", "LEE Zii Jia"]


def variants(base):
    def with_front(cfg, hi):
        coach = (Band("front", 0.0, hi), Band("mid", hi, cfg.coach_bands[1].hi), cfg.coach_bands[2])
        fine = (
            cfg.fine_bands[0],
            Band("front", cfg.fine_bands[0].hi, hi),
            Band("mid", hi, cfg.fine_bands[2].hi),
            cfg.fine_bands[3],
        )
        return dataclasses.replace(cfg, coach_bands=coach, fine_bands=fine)

    return {
        "default (front 1.98 m, body 0.50 m)": base,
        "front 2.5 m": with_front(base, 2.5),
        "body 0.75 m": dataclasses.replace(base, body_radius_m=0.75),
        "front 2.5 m + body 0.75 m": dataclasses.replace(with_front(base, 2.5), body_radius_m=0.75),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--player", action="append", default=None)
    args = ap.parse_args()
    players = args.player or DEFAULT_PLAYERS
    raw = load_strokes()
    s = AnalysisSettings()
    cfgs = variants(load_zone_config())

    tops: dict[str, dict[str, pd.DataFrame]] = {}
    for name, cfg in cfgs.items():
        df = annotate(raw, cfg)
        tops[name] = {p: top_insights(analyse_player(df, p, s)) for p in players}

    rows, detail = [], []
    default_name = next(iter(cfgs))
    for p in players:
        base_keys = [(r.analysis, r.key) for _, r in tops[default_name][p].iterrows()]
        for name in cfgs:
            if name == default_name:
                continue
            keys = [(r.analysis, r.key) for _, r in tops[name][p].iterrows()]
            kept = [k for k in base_keys if k in keys]
            rows.append(
                {
                    "player": p,
                    "variant": name,
                    "default top-5": len(base_keys),
                    "still in top-5": len(kept),
                    "dropped": len(base_keys) - len(kept),
                    "new": len([k for k in keys if k not in base_keys]),
                }
            )
            for _, r in tops[name][p].iterrows():
                if (r.analysis, r.key) not in base_keys:
                    detail.append({"player": p, "variant": name, "new insight": describe(r, p, s)})
            for _, r in tops[default_name][p].iterrows():
                if (r.analysis, r.key) not in keys:
                    detail.append(
                        {"player": p, "variant": name, "dropped insight": describe(r, p, s)}
                    )
    table = pd.DataFrame(rows)
    total = (
        table.groupby("variant")[["default top-5", "still in top-5", "dropped", "new"]]
        .sum()
        .reset_index()
    )

    command = "python scripts/threshold_sensitivity.py " + " ".join(sys.argv[1:])
    md = [
        "# Threshold sensitivity of the top-5 insights\n",
        f"Command: `{command}`\n",
        "Zone thresholds moved as suggested in DECISIONS D8; everything else (selection rule, "
        "min n = 30, typical-pro reference) unchanged. An insight 'survives' when the same "
        "(analysis, pattern) is still in the player's top-5; a pattern that merely changes its zone "
        "label (e.g. a 2.2 m landing moving from mid to front) counts as dropped + new.\n",
        "## Totals over the five players\n",
        total.to_markdown(index=False),
        "\n\n## Per player\n",
        table.to_markdown(index=False),
        "\n\n## What changed\n",
        pd.DataFrame(detail).fillna("").to_markdown(index=False) if detail else "_nothing_",
        "",
    ]
    out = PROJECT_ROOT / "outputs" / "sensitivity.md"
    out.write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    return 0


if __name__ == "__main__":
    sys.exit(main())
