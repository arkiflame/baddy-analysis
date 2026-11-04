"""Render a PlayerReport as a readable Markdown file (plus heatmap PNGs).

The report never shows a rate without its n and 95% CI, marks rows under the minimum sample
size, and lists what was excluded. The top-5 are chosen from rows that are both reliable
(n >= min_n) and whose CI excludes the baseline, ranked by |lift| * sqrt(n), with at most two
per analysis so one table cannot fill the list.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from tactics.analyses import AnalysisSettings, PlayerReport  # noqa: E402
from tactics.config import PlayerConfig, ZoneConfig  # noqa: E402
from tactics.splits import is_holdout  # noqa: E402
from tactics.stats import fmt_rate  # noqa: E402

TOP_K = 5
PER_ANALYSIS = 2


# ---------------------------------------------------------------------------------------
# Insight selection and wording
# ---------------------------------------------------------------------------------------


def top_insights(
    rep: PlayerReport, k: int = TOP_K, per_analysis: int = PER_ANALYSIS
) -> pd.DataFrame:
    cand = rep.insights
    cand = cand[cand.reliable & cand.ci_excludes_baseline]
    # drop the single-factor duplicates when the combined condition already made it
    chosen, counts = [], {}
    for _, row in cand.iterrows():
        fam = row.analysis.split("@")[0]
        if counts.get(fam, 0) >= per_analysis:
            continue
        counts[fam] = counts.get(fam, 0) + 1
        chosen.append(row)
        if len(chosen) == k:
            break
    return pd.DataFrame(chosen).reset_index(drop=True) if chosen else cand.head(0)


def surname(player: str) -> str:
    # The dataset writes family names in capitals ("CHOU Tien Chen", "Kento MOMOTA"). The one
    # name without capitals, "An Se Young", is Korean: family name first.
    parts = player.split()
    caps = [p for p in parts if p.isupper() and len(p) > 1]
    return caps[0].title() if caps else parts[0]


def describe(row: pd.Series, player: str, s: AnalysisSettings) -> str:
    """One sentence per insight, numbers included. Written for a coach, not a statistician."""
    me = surname(player)
    analysis, key = row.analysis, row.key
    base_name, _, split_name = analysis.partition("@")
    prefix = {"game3": "In game 3, ", "pressure": f"Late in games ({s.pressure_from}+), "}.get(
        split_name, ""
    )
    rate = fmt_rate(row.rate, row.ci_lo, row.ci_hi)
    n = int(row.n)
    base = f"{row.baseline:.0%}"
    direction = "more" if row.lift > 0 else "less"

    def seq(tokens: str) -> str:
        out = []
        for t in tokens.split(" > "):
            who, shot = t.split(":", 1)
            out.append(f"{me if who == 'P' else 'opponent'} {shot.replace('_', ' ')}")
        return ", then ".join(out)

    if base_name == "length":
        return f"{prefix}{me} wins {rate} of rallies lasting {key.split(' ', 1)[1]} strokes (n={n}), vs {base} overall."
    if base_name in ("last2", "last3"):
        return (
            f"{prefix}when the point is decided right after {seq(key.split(' ', 1)[1])}, "
            f"{me} wins {rate} (n={n}), vs {base} overall."
        )
    if base_name == "game":
        return f"{me} wins {rate} of rallies in game {key.split()[-1]} (n={n}), vs {base} across all games."
    if base_name == "pressure":
        when = (
            f"late in games (either player at {s.pressure_from}+)"
            if key.endswith("True")
            else f"before either player reaches {s.pressure_from}"
        )
        return f"{me} wins {rate} of rallies {when} (n={n}), vs {base} overall."
    if base_name == "serving":
        when = "when serving" if key.endswith("True") else "when receiving"
        return f"{me} wins {rate} of rallies {when} (n={n}), vs {base} overall."
    if base_name.startswith("danger"):
        faced = "faced" in base_name
        cond = key.split(" ", 1)[1]
        if " -> " in cond:
            shot, zone = cond.split(" -> ")
            what = f"{shot_words(shot)} to the {zone_words(zone)}"
        elif cond.startswith("coach_zone "):
            what = f"shots to the {zone_words(cond.split(' ', 1)[1])}"
        else:
            what = shot_words(cond.split(" ", 1)[1])
        actor = f"opponents' {what} against {me}" if faced else f"{me}'s {what}"
        return (
            f"{prefix}after {actor}, {me} loses the point within {s.within} shots {rate} of the time "
            f"(n={n}), {direction} often than the {base} baseline for shots {me} {'faces' if faced else 'plays'}."
        )
    return f"{prefix}{analysis} {key}: {rate}, n={n}, baseline {base}."


def shot_words(shot: str) -> str:
    names = {
        "push_rush": "pushes/rushes",
        "smash": "smashes",
        "net": "net shots",
        "defensive": "defensive returns",
        "drop": "drops",
        "lob": "lobs",
        "clear": "clears",
        "drive": "drives",
        "short_service": "short serves",
        "long_service": "long serves",
    }
    return names.get(shot, shot.replace("_", " ") + " shots")


def zone_words(zone: str) -> str:
    names = {"fh": "forehand", "bh": "backhand"}
    if zone == "body":
        return "body"
    if zone in ("out", "net_error"):
        return zone.replace("_", " ")
    depth, _, side = zone.partition("_")
    return f"{depth} court, {names.get(side, side)} side"


# ---------------------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------------------


def md_table(
    t: pd.DataFrame,
    label_col: str,
    label_name: str,
    outcome: str = "win rate",
    max_rows: int | None = None,
    reliable_only: bool = False,
) -> str:
    if t.empty:
        return "_no data_\n"
    d = t.copy()
    if reliable_only:
        d = d[d.reliable]
    if max_rows:
        d = d.head(max_rows)
    if d.empty:
        return f"_no groups reach the minimum sample size (n >= {int(t.n.max()) if len(t) else '?'})_\n"
    out = pd.DataFrame(
        {
            label_name: d[label_col].astype(str),
            "n": d.n.astype(int),
            outcome: d.rate.map(lambda v: f"{v:.0%}"),
            "95% CI": [f"{lo:.0%}-{hi:.0%}" for lo, hi in zip(d.ci_lo, d.ci_hi, strict=True)],
            "shrunk": d.shrunk.map(lambda v: f"{v:.0%}"),
            "vs baseline": d.lift.map(lambda v: f"{v:+.0%}"),
            "flag": np.where(
                ~d.reliable, "too few", np.where(d.ci_excludes_baseline, "signal", "")
            ),
        }
    )
    return out.to_markdown(index=False) + "\n"


def endings_table(e: pd.DataFrame, n_rallies: int, top: int = 3) -> str:
    rows = []
    for end_type in ("P winner", "O error", "P error", "O winner"):
        sub = e[e.end_type == end_type]
        if sub.empty:
            continue
        n = int(sub.n.sum())
        shots = ", ".join(
            f"{t.replace('P:', '').replace('O:', '').replace('_', ' ')} {int(c)}"
            for t, c in zip(sub.end_token.head(top), sub.n.head(top), strict=True)
        )
        rows.append(
            {
                "ending": end_type,
                "rallies": n,
                "share": f"{n / n_rallies:.0%}",
                "most common final shots": shots,
            }
        )
    return pd.DataFrame(rows).to_markdown(index=False) + "\n"


# ---------------------------------------------------------------------------------------
# Heatmaps (fine grid, never ranked)
# ---------------------------------------------------------------------------------------


def fine_grid_heatmap(
    strokes: pd.DataFrame, cfg: ZoneConfig, title: str, path: Path
) -> Path | None:
    d = strokes.dropna(subset=["fine_depth", "fine_lat"])
    d = d[(d.fine_lat != "out") & (d.fine_depth.notna())]
    if d.empty:
        return None
    depth_order = [b.name for b in reversed(cfg.fine_bands)]  # rear at the top of the picture
    lat_order = ["bh_sideline", "bh_inner", "fh_inner", "fh_sideline"]
    grid = (
        pd.crosstab(d.fine_depth, d.fine_lat)
        .reindex(index=depth_order, columns=lat_order)
        .fillna(0)
    )
    share = grid / grid.to_numpy().sum()
    fig, ax = plt.subplots(figsize=(5.2, 4.6), constrained_layout=True)
    im = ax.imshow(share.to_numpy(), cmap="Blues", aspect="auto")
    ax.set_xticks(range(len(lat_order)), [c.replace("_", "\n") for c in lat_order])
    ax.set_yticks(
        range(len(depth_order)),
        [f"{b.name}\n{b.lo:.1f}-{b.hi:.1f} m" for b in reversed(cfg.fine_bands)],
    )
    for i in range(len(depth_order)):
        for j in range(len(lat_order)):
            v = share.iat[i, j]
            ax.text(
                j,
                i,
                f"{v:.0%}\n({int(grid.iat[i, j])})",
                ha="center",
                va="center",
                fontsize=8,
                color="white" if v > share.to_numpy().max() * 0.6 else "#0b0b0b",
            )
    ax.set_title(title, loc="left", fontsize=10)
    ax.set_xlabel("receiver's backhand  <->  forehand")
    ax.set_ylabel("depth from net (receiver's side)")
    fig.colorbar(im, ax=ax, fraction=0.046, label="share of strokes")
    for sp in ax.spines.values():
        sp.set_visible(False)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------------------


def write_report(
    rep: PlayerReport,
    out_dir: Path,
    s: AnalysisSettings,
    zone_cfg: ZoneConfig,
    players_cfg: PlayerConfig,
    command: str,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = rep.player.replace(" ", "_").replace(".", "")
    path = out_dir / f"{slug}.md"
    r, ps = rep.rallies, rep.strokes
    me = surname(rep.player)
    top = top_insights(rep)
    n_hold = int(r[is_holdout(r.match_id)].match_id.nunique())
    base_lo, base_hi = _ci(int(r.player_won.sum()), len(r))

    L: list[str] = []
    L.append(f"# Tactical report: {rep.player}\n")
    L.append(f"_Generated {dt.date.today().isoformat()} by `{command}`._\n")
    L.append("## Coverage\n")
    L.append(
        f"- Matches: {r.match_id.nunique()} ({n_hold} of them in the holdout set, see docs/EVALUATION.md)"
    )
    L.append(f"- Rallies with a known outcome: {len(r)}; strokes: {len(ps)}")
    L.append(
        f"- Overall rally win rate: {rep.baseline_win:.1%} (95% CI {base_lo:.1%}-{base_hi:.1%})"
    )
    L.append(f"- Opponents: {', '.join(sorted(r.opponent.unique()))}")
    L.append(
        f"- Shot vocabulary: {'10 coarse types' if s.shot_col == 'shot_coarse' else '18 types'}; "
        f"minimum n = {s.rates.min_n}; shrinkage prior = {s.rates.prior_strength:g} rallies; "
        f"handedness: {players_cfg.handed(rep.player)}"
    )
    L.append("")

    L.append("## Top insights\n")
    if top.empty:
        L.append(
            "_No pattern passes both the minimum sample size and the confidence-interval test._\n"
        )
    for i, row in top.iterrows():
        L.append(f"{i + 1}. {describe(row, rep.player, s)}")
    L.append("")
    L.append(
        "Reading the numbers: every rate comes with its sample size and a 95% Wilson interval. "
        "`shrunk` pulls small samples toward the baseline (Beta prior worth "
        f"{s.rates.prior_strength:g} rallies). Rows marked `too few` have n below {s.rates.min_n} and are "
        "shown for completeness only; `signal` means the interval excludes the baseline.\n"
    )

    T = rep.tables
    L.append("## Win rate by rally length\n")
    L.append(md_table(T["length"], "length_bin", "strokes"))
    L.append("## How points end\n")
    L.append(
        f"Share of {me}'s rallies by how the final stroke decided them (P = {me}, O = opponent). "
        "Descriptive counts; the next sections condition on what happened before the final stroke.\n"
    )
    L.append(endings_table(rep.endings, len(r)))
    L.append("## Win rate by the two shots before the point was decided\n")
    L.append(
        f"Tokens: `P:` = {me}, `O:` = opponent. The sequence is the two strokes played just before the "
        "final stroke (the winner or error). Read: given the rally reached this pattern and the next "
        f"shot ended it, how often did {me} win. Reliable patterns only (n >= {s.rates.min_n}); "
        f"{int((~T['last2'].reliable).sum())} rarer patterns omitted.\n"
    )
    L.append(md_table(T["last2"], "last2", "setup (two shots)", max_rows=12, reliable_only=True))
    L.append("## Win rate by the three shots before the point was decided\n")
    L.append(f"{int((~T['last3'].reliable).sum())} rarer patterns omitted.\n")
    L.append(md_table(T["last3"], "last3", "setup (three shots)", max_rows=12, reliable_only=True))

    L.append(f"## Danger conditions: shots {me} plays\n")
    L.append(
        f"Probability that {me} loses the point within {s.within} shots after playing a given shot type "
        f"to a given zone of the opponent's court (zones from the opponent's view, forehand/backhand by "
        f"their handedness). Baseline over all of {me}'s shots: {rep.baselines['danger_hit']:.1%}.\n"
    )
    L.append(
        md_table(
            T["danger_hit"],
            "condition",
            "shot -> opponent zone",
            outcome="lost within 2",
            max_rows=12,
            reliable_only=True,
        )
    )
    L.append("By shot type alone:\n")
    L.append(md_table(T[f"danger_hit_{s.shot_col}"], s.shot_col, "shot", outcome="lost within 2"))
    L.append("By zone alone:\n")
    L.append(
        md_table(T["danger_hit_coach_zone"], "coach_zone", "opponent zone", outcome="lost within 2")
    )

    L.append(f"## Danger conditions: shots {me} faces\n")
    L.append(
        f"Same measure for shots opponents play against {me} (zones from {me}'s view). "
        f"Baseline: {rep.baselines['danger_faced']:.1%}.\n"
    )
    L.append(
        md_table(
            T["danger_faced"],
            "condition",
            "opponent shot -> zone",
            outcome="lost within 2",
            max_rows=12,
            reliable_only=True,
        )
    )
    L.append("By zone alone:\n")
    L.append(
        md_table(
            T["danger_faced_coach_zone"],
            "coach_zone",
            f"zone on {me}'s side",
            outcome="lost within 2",
        )
    )

    L.append("## Splits: game number, pressure, serving\n")
    L.append(md_table(T["game"], "game", "game"))
    L.append(md_table(T["pressure"], "pressure", f"late game (either at {s.pressure_from}+)"))
    L.append(md_table(T["serving"], "player_served", "serving"))
    for split_name, title in (
        ("game3", "Game 3 only"),
        ("pressure", f"Late game only ({s.pressure_from}+)"),
    ):
        if f"length@{split_name}" in T:
            L.append(f"### {title}\n")
            L.append(
                f"Baseline win rate in this split: {rep.baselines[f'length@{split_name}']:.1%}.\n"
            )
            L.append(md_table(T[f"length@{split_name}"], "length_bin", "strokes"))
            L.append(
                md_table(
                    T[f"last2@{split_name}"],
                    "last2",
                    "last two shots",
                    max_rows=8,
                    reliable_only=True,
                )
            )
            L.append(
                md_table(
                    T[f"danger_hit@{split_name}"],
                    "condition",
                    "shot -> opponent zone",
                    outcome="lost within 2",
                    max_rows=8,
                    reliable_only=True,
                )
            )

    L.append("## Where the shuttle goes (heatmaps, descriptive only)\n")
    img_dir = out_dir / f"{slug}_img"
    for tag, mask, title in (
        ("plays", ps.player_hit, f"Where {me} sends the shuttle"),
        ("faces", ~ps.player_hit, f"Where opponents send {me}"),
    ):
        p = fine_grid_heatmap(
            ps[mask & ~ps.is_serve], zone_cfg, title, img_dir / f"heatmap_{tag}.png"
        )
        if p:
            L.append(f"![{title}]({p.relative_to(out_dir).as_posix()})\n")

    L.append("## Data notes\n")
    excluded_unknown = int(r.has_unknown.sum())
    L.append(
        f"- {excluded_unknown} rallies contain a stroke of unknown type; they count for rally length and "
        "outcome but are excluded from the shot-sequence tables."
    )
    L.append(
        "- Placeholder rallies (one unannotated stroke while the score advances) are excluded everywhere."
    )
    L.append(
        f"- Opponents whose handedness is not in config/players.toml default to right-handed: "
        f"{', '.join(sorted(o for o in r.opponent.unique() if o not in players_cfg.handedness)) or 'none'}."
    )
    L.append("- Zone thresholds: config/zones.toml. Statistics: src/tactics/stats.py.")
    path.write_text("\n".join(L), encoding="utf-8")
    return path


def _ci(k: int, n: int) -> tuple[float, float]:
    from tactics.stats import wilson_ci

    lo, hi = wilson_ci(k, n)
    return float(lo), float(hi)
