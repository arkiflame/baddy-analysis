"""Command line entry point: `python -m tactics <command>` or `tactics <command>`.

Commands
  players                 list players with match / rally coverage
  report --player NAME    write outputs/<player>.md with the top insights and all tables
  evaluate --player NAME  holdout replication of the top insights (can repeat --player)
  zones-check             regenerate the zone-threshold diagnostics
"""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path

from tactics.config import PROJECT_ROOT, load_player_config, load_zone_config

OUTPUTS = PROJECT_ROOT / "outputs"


def _load(all_types: bool = False):
    from tactics.loader import load_strokes
    from tactics.zones import annotate

    return annotate(load_strokes(), load_zone_config())


def _settings(args):
    from tactics.analyses import AnalysisSettings
    from tactics.stats import RateSettings

    return AnalysisSettings(
        rates=RateSettings(min_n=args.min_n, prior_strength=args.prior),
        shot_col="shot" if getattr(args, "all_types", False) else "shot_coarse",
        pressure_from=args.pressure,
    )


def cmd_players(args) -> int:
    from tactics.analyses import coverage
    from tactics.splits import is_holdout

    df = _load()
    cov = coverage(df)
    hold = df[is_holdout(df.match_id)]
    cov["holdout_matches"] = cov.player.map(
        lambda p: hold[(hold.hitter == p) | (hold.receiver == p)].match_id.nunique()
    )
    cov = cov[cov.matches >= args.min_matches]
    cov["win_rate"] = cov.win_rate.map(lambda v: f"{v:.1%}")
    print(cov.to_string(index=False))
    return 0


def cmd_report(args) -> int:
    from tactics import positions
    from tactics.analyses import analyse_player
    from tactics.report import slug, surname, write_report

    df = _load()
    s = _settings(args)
    zcfg = load_zone_config()
    rep = analyse_player(df, args.player, s)
    command = "python -m tactics " + " ".join(shlex.quote(a) for a in sys.argv[1:])
    out_dir = Path(args.out)
    extra: list[str] = []
    if not args.no_positions:
        summary = positions.summarise(df, args.player, zcfg, s)
        img = positions.position_heatmap(
            summary, zcfg, out_dir / f"{slug(args.player)}_img" / "positions.png"
        )
        extra += positions.section(
            summary, surname(args.player), img.relative_to(out_dir).as_posix(), s
        )
    path = write_report(rep, out_dir, s, zcfg, load_player_config(), command, extra)
    print(f"wrote {path}")
    return 0


def cmd_evaluate(args) -> int:
    from tactics.evaluation import replicate, result_markdown

    df = _load()
    s = _settings(args)
    chunks = []
    for player in args.player:
        res = replicate(df, player, s, k=args.top)
        chunks.append(result_markdown(res))
    text = "\n".join(chunks)
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    return 0


def cmd_zones_check(args) -> int:
    import runpy

    runpy.run_path(str(PROJECT_ROOT / "scripts" / "zone_diagnostics.py"), run_name="__main__")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tactics", description="Badminton tactical analyzer (ShuttleSet)"
    )
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp):
        sp.add_argument(
            "--min-n", type=int, default=30, help="minimum rallies for a reliable rate (default 30)"
        )
        sp.add_argument(
            "--prior",
            type=float,
            default=20.0,
            help="shrinkage prior strength in rallies (default 20)",
        )
        sp.add_argument(
            "--pressure", type=int, default=18, help="late-game threshold in points (default 18)"
        )
        sp.add_argument(
            "--all-types", action="store_true", help="use the 18 shot types instead of 10"
        )

    sp = sub.add_parser("players", help="list players and coverage")
    sp.add_argument("--min-matches", type=int, default=1)
    sp.set_defaults(func=cmd_players)

    sp = sub.add_parser("report", help="write a Markdown report for one player")
    sp.add_argument(
        "--player", required=True, help='player name as in the dataset, e.g. "Viktor AXELSEN"'
    )
    sp.add_argument("--out", default=str(OUTPUTS), help="output directory (default outputs/)")
    sp.add_argument("--no-positions", action="store_true", help="skip the position-map section")
    common(sp)
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser("evaluate", help="holdout replication of the top insights")
    sp.add_argument("--player", required=True, action="append", help="repeatable")
    sp.add_argument("--top", type=int, default=5)
    sp.add_argument("--out", default=None, help="optional Markdown file to write")
    common(sp)
    sp.set_defaults(func=cmd_evaluate)

    sp = sub.add_parser("zones-check", help="zone threshold diagnostics")
    sp.set_defaults(func=cmd_zones_check)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
