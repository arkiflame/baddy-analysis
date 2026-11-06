"""Export the scouting analyses as JSON for the web UI.

    uv run python scripts/export_web.py                      # every player with >= 3 matches
    uv run python scripts/export_web.py --player "Viktor AXELSEN" --no-evaluate
    uv run python scripts/export_web.py --no-stability       # faster: no leave-one-match-out folds

Writes web/public/data/index.json and web/public/data/players/<slug>.json. Every number comes
from the same analysis functions as the Markdown report (src/tactics/webexport.py).
"""

from __future__ import annotations

import argparse
import datetime as dt
import shlex
import sys
import time
from pathlib import Path

from tactics import footage, webexport, xp
from tactics.analyses import AnalysisSettings, coverage
from tactics.config import PROJECT_ROOT, load_player_config, load_zone_config
from tactics.loader import load_strokes
from tactics.report import (
    MIN_STABLE_SHARE,
    TENTATIVE_CI_WIDTH,
    TENTATIVE_MIN_N,
    TOP_K,
)
from tactics.zones import annotate


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(PROJECT_ROOT / "web" / "public" / "data"))
    ap.add_argument("--min-matches", type=int, default=3)
    ap.add_argument("--player", action="append", help="only these players (repeatable)")
    ap.add_argument("--no-stability", action="store_true")
    ap.add_argument("--no-evaluate", action="store_true", help="skip the replication schemes")
    ap.add_argument(
        "--evaluate-min-matches",
        type=int,
        default=9,
        help="players with at least this many matches get the three replication schemes",
    )
    args = ap.parse_args(argv)
    command = "python scripts/export_web.py " + " ".join(shlex.quote(a) for a in sys.argv[1:])
    out = Path(args.out)
    t0 = time.perf_counter()

    cfg, pcfg, s = load_zone_config(), load_player_config(), AnalysisSettings()
    df = annotate(load_strokes(), cfg)
    cov = coverage(df)
    players = (
        args.player
        if args.player
        else cov[cov.matches >= args.min_matches].player.astype(str).tolist()
    )
    print(f"loaded {len(df)} strokes in {time.perf_counter() - t0:.0f} s; {len(players)} players")

    res = xp.run_experiment(df, cfg)
    print(f"xP fitted in {time.perf_counter() - t0:.0f} s")

    # Footage: only matches whose YouTube URL scripts/check_video_urls.py found live get
    # example rallies; without the status file every "Watch it" button stays hidden.
    meta = footage.match_meta()
    status = footage.load_status(PROJECT_ROOT / footage.STATUS_FILE)
    videos = footage.live_videos(meta, status)
    if not status:
        print(f"no {footage.STATUS_FILE}: run scripts/check_video_urls.py to enable footage")
    print(f"footage: {len(videos)} matches with a live URL out of {len(meta)}")

    index_players = []
    for i, player in enumerate(players, 1):
        t1 = time.perf_counter()
        data = webexport.export_player(
            df,
            player,
            cfg,
            pcfg,
            s,
            res,
            with_stability=not args.no_stability,
            command=command,
            videos=videos,
        )
        webexport.write_json(out / "players" / f"{data['slug']}.json", data)
        c = data["coverage"]
        index_players.append(
            {
                "player": player,
                "slug": data["slug"],
                "surname": data["surname"],
                "file": f"players/{data['slug']}.json",
                "matches": c["matches"],
                "holdout_matches": c["holdout_matches"],
                "rallies": c["rallies"],
                "win_rate": c["win_rate"],
                "win_lo": c["win_lo"],
                "win_hi": c["win_hi"],
                "handedness": c["handedness"],
                "n_top": len(data["insights"]["top"]),
                "n_tentative": sum(x["tentative"] for x in data["insights"]["top"]),
            }
        )
        print(f"[{i}/{len(players)}] {player}: {time.perf_counter() - t1:.0f} s")

    evaluation = None
    if not args.no_evaluate:
        ev_players = [
            p
            for p in players
            if int(cov[cov.player == p].matches.iloc[0]) >= args.evaluate_min_matches
        ]
        if ev_players:
            t1 = time.perf_counter()
            evaluation = webexport.evaluation_json(df, ev_players, s)
            print(f"replication for {len(ev_players)} players: {time.perf_counter() - t1:.0f} s")

    index = {
        "generated": dt.date.today().isoformat(),
        "command": command,
        "dataset": webexport.dataset_json(df),
        "settings": {
            "min_n": s.rates.min_n,
            "within": s.within,
            "pressure_from": s.pressure_from,
            "top_k": TOP_K,
            "stability": {
                "min_share": MIN_STABLE_SHARE,
                "tentative_ci_width": TENTATIVE_CI_WIDTH,
                "tentative_min_n": TENTATIVE_MIN_N,
                "checked": not args.no_stability,
            },
            "min_matches": args.min_matches,
        },
        "xp": {
            "auc_nonfinal": webexport._clean(xp._auc(res, "pre", "non-final strokes")),
            "auc_final": webexport._clean(xp._auc(res, "pre", "final strokes")),
            "leaky_auc_final": webexport._clean(res.leaky_auc_final),
            "dev_matches": int(res.counts["dev_matches"]),
            "holdout_matches": int(res.counts["holdout_matches"]),
            "metrics": webexport.records(res.table),
            "chosen": {k: str(v) for k, v in res.chosen.items()},
        },
        "live": webexport.live_json(PROJECT_ROOT),
        "evaluation": evaluation,
        "footage": footage.footage_summary(meta, status, videos),
        "players": index_players,
    }
    webexport.write_json(out / "index.json", index)
    print(
        f"wrote {out / 'index.json'} and {len(index_players)} player files in {time.perf_counter() - t0:.0f} s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
