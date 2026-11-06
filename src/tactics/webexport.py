"""Export the scouting analyses as JSON for the web UI (`scripts/export_web.py`).

One file per player plus `index.json`. Every number is produced by the same functions the
Markdown report uses (`analyses`, `report`, `habits`, `positions`, `xp`, `evaluation`); this
module only reshapes their tables into JSON-friendly records. Nothing is computed here that
the report does not compute, and the UI never shows a number that is not in these files
(DECISIONS D28).
"""

from __future__ import annotations

import datetime as dt
import json
import re
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from tactics import footage, habits, plain, positions, xp
from tactics.analyses import (
    AnalysisSettings,
    PlayerReport,
    analyse_player,
    coverage,
    player_strokes,
)
from tactics.config import PlayerConfig, ZoneConfig
from tactics.evaluation import replicate_all, selection_frequency, summary_table
from tactics.report import (
    MIN_STABLE_SHARE,
    TENTATIVE_CI_WIDTH,
    TENTATIVE_MIN_N,
    TOP_K,
    _parse,
    against_bullet,
    against_reference,
    borderline,
    coach_rows,
    describe,
    fix_bullet,
    is_stable,
    possible_bullet,
    rank_with_stability,
    surname,
    takeaways,
    tentative,
)
from tactics.splits import is_holdout

GRID_BIN_M = 0.25
GRID_X = (-3.5, 3.5)  # metres from the centre line toward the player's own right
GRID_Y = (-0.5, 7.5)  # metres from the net into the player's own half


# ---------------------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------------------


def web_slug(player: str) -> str:
    """'Viktor AXELSEN' -> 'viktor-axelsen', 'PUSARLA V. Sindhu' -> 'pusarla-v-sindhu'."""
    return re.sub(r"[^a-z0-9]+", "-", player.lower()).strip("-")


def _clean(v):
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return None if np.isnan(v) else float(v)
    if v is pd.NA or v is None:
        return None
    if isinstance(v, (np.ndarray, list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, (str, int)):
        return v
    return str(v)


def records(df: pd.DataFrame | None, cols: list[str] | None = None) -> list[dict]:
    """DataFrame -> list of plain dicts (NaN -> null, numpy scalars -> Python)."""
    if df is None or len(df) == 0:
        return []
    d = df[cols] if cols else df
    return [{k: _clean(v) for k, v in row.items()} for row in d.astype(object).to_dict("records")]


# ---------------------------------------------------------------------------------------
# Pieces
# ---------------------------------------------------------------------------------------

RATE_COLS = [
    "n",
    "wins",
    "rate",
    "ci_lo",
    "ci_hi",
    "ref_n",
    "ref_rate",
    "delta",
    "delta_lo",
    "delta_hi",
    "reliable",
    "ref_reliable",
    "delta_excludes_zero",
    "score",
]


ExamplesFor = Callable[[pd.Series], list[dict]]


def insight_record(
    row: pd.Series,
    player: str,
    s: AnalysisSettings,
    rank: int | None,
    examples_for: ExamplesFor | None = None,
) -> dict:
    """One insight as JSON: the report's sentence and numbers, the plain-language headline,
    evidence and warnings (D30), and the example rallies with footage when there are any."""
    p = _parse(row, s)
    rec = {
        "rank": rank,
        "text": describe(row, player, s),
        "headline": plain.headline(row, player, s),
        "evidence": plain.evidence(row, player, s),
        "held_up": plain.held_up(row, player),
        "flags": plain.flags(row),
        "examples": examples_for(row) if examples_for else [],
        "analysis": str(row.analysis),
        "key": str(row.key),
        "role": "faced" if p["faced"] else "hit",
        "shot": p["shot"],
        "zone": p["zone"],
        "split": p["split"] or None,
        **{c: _clean(row[c]) for c in RATE_COLS if c in row.index},
        "selected_folds": _clean(row.get("selected_folds", None)),
        "folds": _clean(row.get("folds", None)),
        "tentative": bool(row["tentative"]) if "tentative" in row.index else tentative(row),
    }
    rec["stable"] = is_stable(row)
    rec["borderline"] = bool(row.get("candidate", True)) and borderline(row)
    return rec


def _split_bullet(text: str) -> tuple[str, str]:
    m = re.match(r"\*\*(.+?)\*\*\s*(.*)", text)
    return (m.group(1), m.group(2)) if m else (text, "")


def _with_stability(row: pd.Series, stability: pd.DataFrame | None) -> pd.Series:
    """Attach selected_folds / folds from the selection-frequency table (0 if never selected)."""
    row = row.copy()
    if stability is None or stability.empty:
        row["selected_folds"], row["folds"] = 0, 0
        return row
    hit = stability[(stability.analysis == row.analysis) & (stability.key == row.key)]
    row["selected_folds"] = int(hit.selected_folds.iloc[0]) if len(hit) else 0
    row["folds"] = int(stability.folds.max())
    return row


def coach_json(
    rep: PlayerReport,
    s: AnalysisSettings,
    stability: pd.DataFrame | None,
    examples_for: ExamplesFor | None = None,
) -> dict:
    """The coach cards (D29): `against` = strengths an opponent should not feed, plus
    `against_reference` pointing at the weaknesses; `fix` = the weaknesses as training
    priorities; `possible` = borderline candidates with the reason they are not confident.
    The site shows `fix` as "How to beat <player>" and `against` as "What <player> does well",
    each item led by its plain-language headline (D30)."""
    weak, strong, maybe = coach_rows(rep, s)
    me = surname(rep.player)

    def items(rows, bullet):
        out = []
        for r in rows:
            title, detail = _split_bullet(bullet(r, rep.player, s))
            r = _with_stability(r, stability)
            out.append(
                {
                    "title": title,
                    "detail": detail,
                    "insight": insight_record(r, rep.player, s, None, examples_for),
                }
            )
        return out

    return {
        "against": items(strong, against_bullet),
        "against_reference": against_reference(me, len(weak)),
        "against_reference_plain": (
            f"The places to attack are listed under “How to beat {me}”." if weak else None
        ),
        "fix": items(weak, fix_bullet),
        "possible": items(maybe, possible_bullet),
        "possible_note": (
            "The 95% interval on the difference excludes zero by less than half a point, so "
            "printed to whole points it touches zero: a lead, not a finding."
        ),
        "possible_note_plain": (
            "These looked real but the margin is too thin to be sure. Treat them as leads to "
            "watch for, not as findings."
        ),
    }


def summary_json(
    top: pd.DataFrame,
    player: str,
    s: AnalysisSettings,
    examples_for: ExamplesFor | None = None,
) -> list[dict]:
    """Plain-language takeaways from the stable, non-tentative top insights (D29)."""
    return [
        {"text": text, "insight": insight_record(row, player, s, None, examples_for)}
        for text, row in takeaways(top, player, s)
    ]


def _danger_rows(t: pd.DataFrame, label_col: str) -> list[dict]:
    if t is None or t.empty:
        return []
    d = t.copy()
    d["label"] = d[label_col].astype(str)
    if label_col == "condition":
        parts = d.label.str.split(" -> ", n=1, expand=True)
        d["shot"], d["zone"] = parts[0], parts[1]
    elif label_col == "coach_zone":
        d["shot"], d["zone"] = None, d.label
    else:
        d["shot"], d["zone"] = d.label, None
    d["signal"] = d.reliable & d.ref_reliable & d.delta_excludes_zero
    cols = ["label", "shot", "zone", *RATE_COLS, "signal"]
    return records(d, [c for c in cols if c in d.columns])


def danger_json(rep: PlayerReport, s: AnalysisSettings) -> dict:
    T = rep.tables
    out = {}
    for split, name in (("", "all"), ("@game3", "game3"), ("@pressure", "pressure")):
        block = {}
        for role in ("faced", "hit"):
            base = f"danger_{role}{split}"
            if base not in T:
                continue
            block[role] = _danger_rows(T[base], "condition")
            if f"danger_{role}_coach_zone{split}" in T:
                block[f"{role}_zone"] = _danger_rows(
                    T[f"danger_{role}_coach_zone{split}"], "coach_zone"
                )
            if f"danger_{role}_{s.shot_col}{split}" in T:
                block[f"{role}_shot"] = _danger_rows(
                    T[f"danger_{role}_{s.shot_col}{split}"], s.shot_col
                )
        if block:
            block["baseline_faced"] = _clean(rep.baselines.get(f"danger_faced{split}", np.nan))
            block["baseline_hit"] = _clean(rep.baselines.get(f"danger_hit{split}", np.nan))
            out[name] = block
    return out


def habits_json(h: habits.HabitSummary, player: str) -> dict:
    tend_cols = [
        "situation",
        "reply",
        "n",
        "wins",
        "rate",
        "ci_lo",
        "ci_hi",
        "ref_n",
        "ref_rate",
        "delta",
        "delta_lo",
        "delta_hi",
        "reliable",
        "ref_reliable",
        "habit",
    ]
    pred_cols = [
        "situation",
        "n",
        "entropy_bits",
        "lo",
        "hi",
        "ref_entropy_bits",
        "ref_lo",
        "ref_hi",
        "delta",
        "effective_replies",
        "more_predictable",
        "less_predictable",
        "top_reply",
        "top_share",
    ]
    play_cols = [
        "sequence",
        "wins",
        "n",
        "rate",
        "ci_lo",
        "ci_hi",
        "ref_n",
        "ref_rate",
        "delta",
        "delta_lo",
        "delta_hi",
        "win_rate",
        "win_lo",
        "win_hi",
        "ref_win_rate",
        "reliable",
        "ref_reliable",
        "candidate",
    ]

    def tend(t):
        if t is None or t.empty:
            return []
        d = t[t.reliable & t.ref_reliable] if "ref_reliable" in t else t[t.reliable]
        out = records(d, [c for c in tend_cols if c in d.columns])
        for rec in out:
            rec["plain"] = plain.habit_sentence(pd.Series(rec), player)
        return out

    def plays(t, serving):
        if t is None or t.empty:
            return []
        d = t[t.reliable]
        out = records(d, [c for c in play_cols if c in d.columns])
        for rec in out:
            rec["plain"] = plain.set_play_sentence(pd.Series(rec), player, serving)
        return out

    pred = h.predictability
    pred_out = records(pred, [c for c in pred_cols if c in pred.columns]) if len(pred) else []
    for rec in pred_out:
        rec["ref_effective_replies"] = plain.effective(rec["ref_entropy_bits"])
        rec["plain"] = plain.predictability_sentence(pd.Series(rec), player)
    return {
        "n_replies": int(h.n_replies),
        "by_shot": tend(h.tendencies_shot),
        "by_shot_zone": tend(h.tendencies_zone),
        "predictability": pred_out,
        "set_plays": {
            f"{'serve' if serving else 'receive'}{k}": plays(h.set_plays[(k, serving)], serving)
            for (k, serving) in h.set_plays
        },
    }


MEAN_COLS = [
    "label",
    "n",
    "mean",
    "lo",
    "hi",
    "ref_n",
    "ref_mean",
    "ref_lo",
    "ref_hi",
    "delta",
    "delta_lo",
    "delta_hi",
    "reliable",
    "signal",
]


def _grid(pos: pd.DataFrame, role: str) -> dict:
    d = pos[pos.role == role]
    xedges = np.arange(GRID_X[0], GRID_X[1] + 1e-9, GRID_BIN_M)
    yedges = np.arange(GRID_Y[0], GRID_Y[1] + 1e-9, GRID_BIN_M)
    counts, _, _ = np.histogram2d(
        d.lat_right.to_numpy(float), d.depth.to_numpy(float), bins=[xedges, yedges]
    )
    return {
        "x0": GRID_X[0],
        "y0": GRID_Y[0],
        "bin": GRID_BIN_M,
        "nx": len(xedges) - 1,
        "ny": len(yedges) - 1,
        "n": int(len(d)),
        "counts": counts.astype(int).tolist(),  # counts[ix][iy]; x = own right, y = depth
    }


def positions_json(ps: positions.PositionSummary, cfg: ZoneConfig, player: str) -> dict:
    b = ps.base
    rb = ps.ref_base
    handed = str(ps.positions.handed.iloc[0]) if len(ps.positions) else "right"

    def means(t, kind):
        out = records(t, [c for c in MEAN_COLS if c in t.columns])
        for rec in out:
            rec["plain"] = (
                plain.mean_sentence(pd.Series(rec), player, kind)
                if rec["mean"] is not None
                else None
            )
        return out

    lat_fh = float(b.base_lat_right) * (1 if handed == "right" else -1)
    return {
        "handedness": handed,
        "plain_base": plain.base_sentence(
            player,
            float(b.base_depth),
            lat_fh,
            float(rb.base_depth.min()),
            float(rb.base_depth.max()),
        ),
        "frame": {
            "x": "metres from the centre line toward the player's own right",
            "y": "metres from the net into the player's own half",
            "singles_half_width_m": cfg.singles_half_width_m,
            "half_length_m": cfg.net_y,
            "court_half_width_m": cfg.centre_x,
            "coach_bands": [{"name": bd.name, "lo": bd.lo, "hi": bd.hi} for bd in cfg.coach_bands],
            "body_radius_m": cfg.body_radius_m,
        },
        "base": {
            "n": int(b.n),
            "depth": float(b.base_depth),
            "lat_right": float(b.base_lat_right),
            "depth_q1": float(b.depth_q1),
            "depth_q3": float(b.depth_q3),
            "lat_q1": float(b.lat_q1),
            "lat_q3": float(b.lat_q3),
        },
        "ref_base": {
            "players": int(len(rb)),
            "depth_median": float(rb.base_depth.median()),
            "depth_min": float(rb.base_depth.min()),
            "depth_max": float(rb.base_depth.max()),
            "lat_abs_median": float(rb.base_lat_right.abs().median()),
        },
        "grids": {"hit": _grid(ps.positions, "hit"), "receive": _grid(ps.positions, "receive")},
        "pull": means(ps.pull, "pull"),
        "distance": means(ps.distance, "distance"),
        "per_hit": means(ps.per_hit, "per_hit"),
    }


XP_COLS = [
    "label",
    "n",
    "xp",
    "mean",
    "lo",
    "hi",
    "ref_n",
    "ref_mean",
    "delta",
    "delta_lo",
    "delta_hi",
    "own_delta",
    "own_lo",
    "own_hi",
    "reliable",
    "signal",
    "own_signal",
]


def xp_json(px: xp.PlayerXP, res: xp.XPResult, player: str) -> dict:
    auc_nonfinal = xp._auc(res, "pre", "non-final strokes")
    auc_final = xp._auc(res, "pre", "final strokes")

    def tab(t):
        return records(t, [c for c in XP_COLS if c in t.columns]) if len(t) else []

    finishing = tab(px.finishing)
    for rec in finishing:
        rec["plain"] = plain.finishing_sentence(pd.Series(rec), player) if rec["reliable"] else None
    return {
        "plain_note": plain.coin_flip_note(),
        "caveat": (
            "Read this first: xP from shot and position data has no signal mid-rally in elite "
            f"singles (holdout AUC {auc_nonfinal:.2f} on strokes that did not end the rally). The "
            f"same features reach AUC {auc_final:.2f} only on final strokes, where the task is "
            "classifying how an already-decisive stroke ends (winner or error), not predicting a "
            "rally. Nothing in this section is a working expected-points model."
        ),
        "auc_nonfinal": _clean(auc_nonfinal),
        "auc_final": _clean(auc_final),
        "leaky_auc_final": _clean(res.leaky_auc_final),
        "chosen": {k: str(v) for k, v in res.chosen.items()},
        "dev_matches": int(res.counts["dev_matches"]),
        "holdout_matches": int(res.counts["holdout_matches"]),
        "n_shots": int(px.n_shots),
        "n_rallies": int(px.n_rallies),
        "overall": {k: _clean(v) for k, v in px.overall.items()},
        "by_shot": tab(px.by_shot),
        "by_shot_band": tab(px.by_shot_band),
        "finishing": finishing,
        "situation": tab(px.situation),
    }


def coverage_json(rep: PlayerReport, df_cov: pd.DataFrame, pcfg: PlayerConfig) -> dict:
    r = rep.rallies
    from tactics.stats import wilson_ci

    lo, hi = wilson_ci(int(r.player_won.sum()), len(r))
    return {
        "matches": int(r.match_id.nunique()),
        "holdout_matches": int(r[is_holdout(r.match_id)].match_id.nunique()),
        "rallies": int(len(r)),
        "strokes": int(len(rep.strokes)),
        "win_rate": float(rep.baseline_win),
        "win_lo": float(lo),
        "win_hi": float(hi),
        "opponents": sorted(r.opponent.astype(str).unique().tolist()),
        "handedness": pcfg.handed(rep.player),
        "handedness_known": rep.player in pcfg.handedness,
    }


# ---------------------------------------------------------------------------------------
# Per player and index
# ---------------------------------------------------------------------------------------


def export_player(
    df: pd.DataFrame,
    player: str,
    cfg: ZoneConfig,
    pcfg: PlayerConfig,
    s: AnalysisSettings,
    res: xp.XPResult | None,
    with_stability: bool = True,
    command: str = "",
    videos: dict[str, dict] | None = None,
) -> dict:
    """videos: match_id -> live footage (footage.live_videos); None means no example rallies."""
    rep = analyse_player(df, player, s)
    stability = selection_frequency(df, player, s, k=TOP_K) if with_stability else None
    top, unstable = rank_with_stability(rep, stability)
    ps = player_strokes(df, player)
    videos = videos or {}
    cache: dict[str, list[dict]] = {}

    def examples_for(row: pd.Series) -> list[dict]:
        key = f"{row.analysis}|{row.key}"
        if key not in cache:
            p = _parse(row, s)
            cache[key] = footage.pick_examples(
                ps,
                player,
                s,
                "faced" if p["faced"] else "hit",
                p["shot"],
                p["zone"],
                p["split"] or None,
                float(row.delta) > 0,
                videos,
            )
        return cache[key]

    my_matches = set(ps.match_id.astype(str).unique())
    out = {
        "player": player,
        "slug": web_slug(player),
        "surname": surname(player),
        "generated": dt.date.today().isoformat(),
        "command": command,
        "footage": {
            "matches": len(my_matches),
            "matches_with_video": len(my_matches & set(videos)),
        },
        "settings": {
            "min_n": s.rates.min_n,
            "within": s.within,
            "pressure_from": s.pressure_from,
            "shot_vocabulary": "10 coarse types" if s.shot_col == "shot_coarse" else "18 types",
            "stability": {
                "min_share": MIN_STABLE_SHARE,
                "tentative_ci_width": TENTATIVE_CI_WIDTH,
                "tentative_min_n": TENTATIVE_MIN_N,
                "folds": int(top.folds.max()) if with_stability and len(top) else None,
                "checked": bool(with_stability),
            },
        },
        "coverage": coverage_json(rep, None, pcfg),
        "insights": {
            "top": [insight_record(r, player, s, i + 1, examples_for) for i, r in top.iterrows()],
            "less_stable": [
                insight_record(r, player, s, None, examples_for) for _, r in unstable.iterrows()
            ],
        },
        "summary": summary_json(top, player, s, examples_for),
        "coach": coach_json(rep, s, stability, examples_for),
        "danger": danger_json(rep, s),
        "habits": habits_json(habits.summarise(df, player, s), player),
        "positions": positions_json(positions.summarise(df, player, cfg, s), cfg, player),
        "xp": (
            xp_json(xp.player_xp(res, player, s.rates.min_n), res, player)
            if res is not None
            else None
        ),
    }
    return out


def dataset_json(df: pd.DataFrame) -> dict:
    valid = df[df.annotated] if "annotated" in df else df
    rallies = valid.drop_duplicates("rally_id")
    known = rallies[rallies.rally_winner.notna() & (rallies.rally_winner.astype(str) != "unknown")]
    return {
        "matches": int(df.match_id.nunique()),
        "strokes": int(len(df)),
        "rallies": int(len(rallies)),
        "rallies_known_winner": int(len(known)),
        "strokes_known_winner": int(valid[valid.rally_id.isin(known.rally_id)].shape[0]),
        "players": int(len(coverage(df))),
    }


def evaluation_json(df: pd.DataFrame, players: list[str], s: AnalysisSettings) -> dict:
    results = []
    for p in players:
        results += replicate_all(df, p, s, k=TOP_K)
    summary = summary_table(results)
    totals = summary.groupby("scheme", sort=False)[list(summary.columns[3:])].sum().reset_index()
    per_insight = []
    for r in results:
        for _, row in r.table.iterrows():
            per_insight.append(
                {
                    "player": r.player,
                    "scheme": r.scheme,
                    "claim": row.claim,
                    "verdict": row.verdict,
                    "test_n": _clean(row.test_n),
                    "test_rate": _clean(row.test_rate),
                    "test_delta": _clean(row.test_delta),
                    "test_delta_lo": _clean(row.test_delta_lo),
                    "test_delta_hi": _clean(row.test_delta_hi),
                    "selected_folds": _clean(row.selected_folds),
                    "folds": _clean(row.folds),
                }
            )
    return {
        "players": players,
        "summary": records(summary),
        "totals": records(totals),
        "per_insight": per_insight,
    }


def live_json(root: Path) -> list[dict]:
    """The live-advantage experiment's verdicts, read from scripts/live_state.py's JSON output
    if it exists (never recomputed here; the web UI shows them only when present)."""
    out = []
    for name in ("live_state.json", "live_state_reg.json"):
        p = root / "outputs" / "m3" / name
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        out.append(
            {
                "file": f"outputs/m3/{name}",
                "pass": bool(d.get("pass")),
                "best_live_auc": _clean(d.get("best_live_auc")),
                "pass_auc": _clean(d.get("pass_auc")),
                "command": d.get("command"),
            }
        )
    return out


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
