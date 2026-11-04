"""Render a PlayerReport as a readable Markdown file (plus heatmap PNGs).

Structure (DECISIONS D19, D20):
1. Top insights: the actionable patterns where the player differs most from typical pros.
2. "How to play against <player>" and "What <player> should fix": the same evidence written as
   coaching bullets, one for opponents and one for the player.
3. The danger tables behind them, each row next to the typical-pro rate and the CI on the
   difference.
4. Descriptive context: how points end, the setups before the decisive stroke, rally length,
   game / pressure / serving splits, and position heatmaps.

The report never shows a rate without its n and 95% CI and lists what was excluded.
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
PER_FAMILY = 2  # shot-and-zone rows per table
PER_SINGLE_FAMILY = 1  # shot-alone / zone-alone rows per table (large n, coarse advice)
STABILITY_POOL = 2 * TOP_K  # candidates checked for selection stability (D27)
MIN_STABLE_SHARE = (
    0.5  # ranked only if selected in at least this share of leave-one-match-out folds
)
TENTATIVE_CI_WIDTH = 0.20  # flagged 'tentative' if the interval on the difference is wider (points)
TENTATIVE_MIN_N = 60  # ... or the player's n is smaller

# ---------------------------------------------------------------------------------------
# Insight selection
# ---------------------------------------------------------------------------------------


def _cap(fam: str, per_family: int) -> int:
    return PER_SINGLE_FAMILY if "_single" in fam else per_family


def top_insights(rep: PlayerReport, k: int = TOP_K, per_family: int = PER_FAMILY) -> pd.DataFrame:
    """The k best candidates (see PlayerReport.insights), at most `per_family` from one family
    so a single table cannot fill the list."""
    cand = rep.insights
    cand = cand[cand.candidate]
    chosen, counts = [], {}
    for _, row in cand.iterrows():
        if counts.get(row.family, 0) >= _cap(row.family, per_family):
            continue
        counts[row.family] = counts.get(row.family, 0) + 1
        chosen.append(row)
        if len(chosen) == k:
            break
    return pd.DataFrame(chosen).reset_index(drop=True) if chosen else cand.head(0)


def tentative(row: pd.Series) -> bool:
    """An insight whose interval on the difference is wider than TENTATIVE_CI_WIDTH or whose
    n is under TENTATIVE_MIN_N: shown, but marked (D27)."""
    return bool((row.delta_hi - row.delta_lo) > TENTATIVE_CI_WIDTH or row.n < TENTATIVE_MIN_N)


def rank_with_stability(
    rep: PlayerReport,
    stability: pd.DataFrame | None,
    k: int = TOP_K,
    pool: int = STABILITY_POOL,
    min_share: float = MIN_STABLE_SHARE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Top-k among the `pool` best candidates, keeping only those selected in at least
    `min_share` of the leave-one-match-out folds (`evaluation.selection_frequency`); the
    pool's unstable candidates come back as the second frame. Both carry `selected_folds`,
    `folds` and `tentative`. Without a stability table the plain ranking is returned."""
    cand = top_insights(rep, k=pool).copy()
    if cand.empty:
        return cand, cand
    cand["tentative"] = [tentative(r) for _, r in cand.iterrows()]
    if stability is None or stability.empty:
        cand["selected_folds"], cand["folds"] = 0, 0
        return cand.head(k).reset_index(drop=True), cand.head(0)
    cols = ["analysis", "key", "selected_folds", "folds"]
    cand = cand.merge(stability[cols], on=["analysis", "key"], how="left")
    folds = int(stability.folds.max())
    cand["selected_folds"] = cand.selected_folds.fillna(0).astype(int)
    cand["folds"] = folds
    stable = cand.selected_folds >= min_share * folds
    top = cand[stable].head(k).reset_index(drop=True)
    return top, cand[~stable].reset_index(drop=True)


# ---------------------------------------------------------------------------------------
# Wording
# ---------------------------------------------------------------------------------------

# shot type -> (plural noun, verb for "opponents ...", verb for "<player> ...")
SHOT_PHRASES: dict[str, tuple[str, str, str]] = {
    "push_rush": ("pushes and rushes", "push or rush", "pushes or rushes"),
    "smash": ("smashes", "smash", "smashes"),
    "net": ("net shots", "play a net shot", "plays a net shot"),
    "defensive": ("defensive returns", "play a defensive return", "plays a defensive return"),
    "drop": ("drops", "drop", "drops"),
    "lob": ("lobs", "lob", "lobs"),
    "clear": ("clears", "clear", "clears"),
    "drive": ("drives", "drive", "drives"),
    "short_service": ("short serves", "serve short", "serves short"),
    "long_service": ("long serves", "serve long", "serves long"),
}
NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four"}


def shot_words(shot: str, form: str = "plural") -> str:
    """'push_rush' -> 'pushes and rushes' / 'push or rush' / 'pushes or rushes'."""
    plural, verb, verb3 = SHOT_PHRASES.get(
        shot,
        (
            shot.replace("_", " ") + " shots",
            "play a " + shot.replace("_", " "),
            "plays a " + shot.replace("_", " "),
        ),
    )
    return {"plural": plural, "verb": verb, "verb3": verb3}[form]


def zone_words(zone: str) -> str:
    """'rear_bh' -> 'rear backhand', 'body' -> 'body'."""
    if zone in ("body", "out", "net_error"):
        return zone.replace("_", " ")
    depth, _, side = zone.partition("_")
    return f"{depth} {'forehand' if side == 'fh' else 'backhand'}"


def slug(player: str) -> str:
    return player.replace(" ", "_").replace(".", "")


def surname(player: str) -> str:
    # The dataset writes family names in capitals ("CHOU Tien Chen", "Kento MOMOTA"). The one
    # name without capitals, "An Se Young", is Korean: family name first.
    parts = player.split()
    caps = [p for p in parts if p.isupper() and len(p) > 1]
    return caps[0].title() if caps else parts[0]


def _parse(row: pd.Series, s: AnalysisSettings) -> dict:
    """Pull role, shot, zone and split out of an insight row's analysis/key."""
    base, _, split = row.analysis.partition("@")
    faced = base.startswith("danger_faced")
    cond = row.key.split(" ", 1)[1]
    shot = zone = None
    if " -> " in cond:
        shot, zone = cond.split(" -> ")
    elif cond.startswith("coach_zone "):
        zone = cond.split(" ", 1)[1]
    elif cond.startswith(s.shot_col + " "):
        shot = cond.split(" ", 1)[1]
    else:
        shot = cond
    prefix = {"game3": "In game 3, ", "pressure": f"At {s.pressure_from}+ in a game, "}.get(
        split, ""
    )
    return {"faced": faced, "shot": shot, "zone": zone, "prefix": prefix, "split": split}


def _situation(p: dict, me: str) -> str:
    """'when opponents push or rush to Axelsen's rear backhand' (no leading capital)."""
    shot, zone = p["shot"], p["zone"]
    if p["faced"]:
        if shot and zone:
            return f"when opponents {shot_words(shot, 'verb')} to {me}'s {zone_words(zone)}"
        if shot:
            return f"when opponents {shot_words(shot, 'verb')}, wherever it lands"
        return f"when opponents play anything to {me}'s {zone_words(zone)}"
    if shot and zone:
        return f"when {me} {shot_words(shot, 'verb3')} to the opponent's {zone_words(zone)}"
    if shot:
        return f"when {me} {shot_words(shot, 'verb3')}, wherever it lands"
    return f"when {me} plays anything to the opponent's {zone_words(zone)}"


def _numbers(row: pd.Series, s: AnalysisSettings, me: str) -> str:
    within = NUMBER_WORDS.get(s.within, str(s.within))
    txt = (
        f"{me} loses the point within {within} shots {row.rate:.0%} of the time "
        f"(n={int(row.n)}, 95% CI {row.ci_lo:.0%}-{row.ci_hi:.0%})"
    )
    if row.ref_n:
        txt += (
            f"; typical pros lose {row.ref_rate:.0%} after the same shot "
            f"(difference {row.delta * 100:+.0f} points, 95% CI {row.delta_lo * 100:+.0f} to "
            f"{row.delta_hi * 100:+.0f}, n={int(row.ref_n)})"
        )
    return txt + "."


def describe(row: pd.Series, player: str, s: AnalysisSettings) -> str:
    """One sentence per insight, numbers included. Written for a coach, not a statistician."""
    me = surname(player)
    base = row.analysis.partition("@")[0]
    if base.startswith("danger"):
        p = _parse(row, s)
        sit = _situation(p, me)
        sentence = f"{p['prefix']}{sit}, {_numbers(row, s, me)}"
        return sentence[0].upper() + sentence[1:]
    # descriptive analyses (not ranked, but describe() is used by the evaluation output too)
    rate = fmt_rate(row.rate, row.ci_lo, row.ci_hi)
    n = int(row.n)
    key = row.key.split(" ", 1)[1]
    if base in ("last2", "last3"):
        ref = f"; typical pros win {row.ref_rate:.0%} (n={int(row.ref_n)})" if row.ref_n else ""
        return (
            f"When the point is decided right after {_seq(key, me)}, {me} wins {rate} (n={n}){ref}."
        )
    if base == "length":
        return f"{me} wins {rate} of rallies lasting {key} strokes (n={n}), vs {row.ref_rate:.0%} overall."
    if base == "game":
        return f"{me} wins {rate} of rallies in game {key} (n={n}), vs {row.ref_rate:.0%} across all games."
    if base == "pressure":
        when = (
            f"at {s.pressure_from}+"
            if key == "True"
            else f"before either player reaches {s.pressure_from}"
        )
        return f"{me} wins {rate} of rallies {when} (n={n}), vs {row.ref_rate:.0%} overall."
    if base == "serving":
        when = "when serving" if key == "True" else "when receiving"
        return f"{me} wins {rate} of rallies {when} (n={n}), vs {row.ref_rate:.0%} overall."
    return f"{row.analysis} {row.key}: {rate}, n={n}."


def _seq(tokens: str, me: str) -> str:
    out = []
    for t in tokens.split(" > "):
        who, shot = t.split(":", 1)
        out.append(f"{'a ' + me if who == 'P' else 'an opponent'} {shot.replace('_', ' ')}")
    return ", then ".join(out)


# ---------------------------------------------------------------------------------------
# Coach sections
# ---------------------------------------------------------------------------------------


def _ref_clause(row: pd.Series) -> str:
    return f"vs {row.ref_rate:.0%} for typical pros (n={int(row.n)})"


def against_bullet(row: pd.Series, player: str, s: AnalysisSettings) -> str:
    """Advice for an opponent of the player."""
    me = surname(player)
    p = _parse(row, s)
    shot, zone, faced, worse = p["shot"], p["zone"], p["faced"], row.delta > 0
    within = NUMBER_WORDS.get(s.within, str(s.within))
    z = zone_words(zone) if zone else None
    if faced:
        if worse:
            head = (
                f"{shot_words(shot, 'verb').capitalize()} to {me}'s {z}"
                if shot and zone
                else (
                    f"{shot_words(shot, 'verb').capitalize()} more"
                    if shot
                    else f"Attack {me}'s {z}"
                )
            )
            body = f"{me} loses the point within {within} shots {row.rate:.0%} of the time there"
        else:
            head = (
                f"Don't count on {shot_words(shot)} to {me}'s {z}"
                if shot and zone
                else (
                    f"{shot_words(shot).capitalize()} are less effective than usual"
                    if shot
                    else f"{me}'s {z} is well covered"
                )
            )
            body = f"{me} loses within {within} shots only {row.rate:.0%} of the time"
    else:
        target = (
            f"{me}'s {shot_words(shot)} to your {z}"
            if shot and zone
            else (f"{me}'s {shot_words(shot)}" if shot else f"anything {me} plays to your {z}")
        )
        if worse:
            head = f"Punish {target}"
            body = (
                f"after them {me} loses the point within {within} shots {row.rate:.0%} of the time"
            )
        else:
            head = f"Be ready for {target}"
            body = f"after them {me} loses within {within} shots only {row.rate:.0%} of the time, a strength"
    head = p["prefix"] + head[0].lower() + head[1:] if p["prefix"] else head
    return f"**{head}.** {body[0].upper() + body[1:]}, {_ref_clause(row)}."


def fix_bullet(row: pd.Series, player: str, s: AnalysisSettings) -> str:
    """Advice for the player (only rows where the player loses MORE than typical pros)."""
    me = surname(player)
    p = _parse(row, s)
    shot, zone = p["shot"], p["zone"]
    within = NUMBER_WORDS.get(s.within, str(s.within))
    z = zone_words(zone) if zone else None
    if p["faced"]:
        head = (
            f"Defending {shot_words(shot)} to the {z}"
            if shot and zone
            else (f"Defending {shot_words(shot)}" if shot else f"Covering the {z}")
        )
        body = f"{me} loses the point within {within} shots {row.rate:.0%} of the time there"
    else:
        head = (
            f"{shot_words(shot).capitalize()} to the opponent's {z}"
            if shot and zone
            else (shot_words(shot).capitalize() if shot else f"Shots to the opponent's {z}")
        )
        body = f"they cost the point within {within} shots {row.rate:.0%} of the time"
    head = p["prefix"] + head[0].lower() + head[1:] if p["prefix"] else head
    return f"**{head}.** {body[0].upper() + body[1:]}, {_ref_clause(row)}."


def coach_sections(
    rep: PlayerReport, s: AnalysisSettings, k: int = 6, per_family: int = 2
) -> tuple[list[str], list[str]]:
    """Bullets for the two coach sections, best-supported first.

    'How to play against': the player's weaknesses first (loses more than typical pros), then
    the strengths an opponent should stop feeding, at most k lines and per_family per table.
    'What to fix': the weaknesses only.
    """
    cand = rep.insights
    cand = cand[cand.candidate]

    def pick(rows: pd.DataFrame, limit: int) -> list[pd.Series]:
        out, counts = [], {}
        for _, row in rows.iterrows():
            if counts.get(row.family, 0) >= per_family:
                continue
            counts[row.family] = counts.get(row.family, 0) + 1
            out.append(row)
            if len(out) == limit:
                break
        return out

    weak = pick(cand[cand.delta > 0], k)
    strong = pick(cand[cand.delta < 0], max(k - len(weak), k // 2))
    against = [against_bullet(r, rep.player, s) for r in (weak + strong)[:k]]
    fix = [fix_bullet(r, rep.player, s) for r in weak]
    return against, fix


# ---------------------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------------------


def top_insights_table(
    top: pd.DataFrame, player: str, s: AnalysisSettings, with_folds: bool = True
) -> str:
    """Markdown table: rank, the insight sentence, 'stable in X of N folds', tentative flag."""
    if top.empty:
        return "_No pattern passes the sample-size, interval and stability tests._\n"
    rows = []
    for i, row in top.iterrows():
        rec = {"#": i + 1, "insight": describe(row, player, s)}
        if with_folds:
            rec["stable in"] = f"{int(row.selected_folds)} of {int(row.folds)} folds"
        rec["flag"] = "tentative" if row.tentative else ""
        rows.append(rec)
    return pd.DataFrame(rows).to_markdown(index=False, disable_numparse=True) + "\n"


def _flag(d: pd.DataFrame) -> np.ndarray:
    return np.where(
        ~d.reliable,
        "too few",
        np.where(~d.ref_reliable, "ref too few", np.where(d.delta_excludes_zero, "signal", "")),
    )


def md_table(
    t: pd.DataFrame,
    label_col: str,
    label_name: str,
    outcome: str = "win rate",
    max_rows: int | None = None,
    reliable_only: bool = False,
    ref_name: str = "typical pros",
) -> str:
    """Rate table with the reference rate and the CI on the difference, in percentage points."""
    if t.empty:
        return "_no data_\n"
    d = t.copy()
    if reliable_only:
        d = d[d.reliable]
    if max_rows:
        d = d.head(max_rows)
    if d.empty:
        return "_no groups reach the minimum sample size_\n"
    out = pd.DataFrame(
        {
            label_name: d[label_col].astype(str),
            "n": d.n.astype(int),
            outcome: d.rate.map(lambda v: f"{v:.0%}"),
            "95% CI": [f"{lo:.0%}-{hi:.0%}" for lo, hi in zip(d.ci_lo, d.ci_hi, strict=True)],
            ref_name: [
                f"{r:.0%} (n={int(n)})" if n else "-"
                for r, n in zip(d.ref_rate, d.ref_n, strict=True)
            ],
            "difference (95% CI)": [
                f"{x * 100:+.0f} ({lo * 100:+.0f} to {hi * 100:+.0f})" if n else "-"
                for x, lo, hi, n in zip(d.delta, d.delta_lo, d.delta_hi, d.ref_n, strict=True)
            ],
            "flag": _flag(d),
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
    extra_sections: list[str] | None = None,
    stability: pd.DataFrame | None = None,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    name = slug(rep.player)
    path = out_dir / f"{name}.md"
    r, ps = rep.rallies, rep.strokes
    me = surname(rep.player)
    top, unstable = rank_with_stability(rep, stability)
    against, fix = coach_sections(rep, s)
    n_hold = int(r[is_holdout(r.match_id)].match_id.nunique())
    base_lo, base_hi = _ci(int(r.player_won.sum()), len(r))
    within = NUMBER_WORDS.get(s.within, str(s.within))
    T = rep.tables

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
        f"minimum n = {s.rates.min_n} on both sides of every comparison; "
        f"handedness: {players_cfg.handed(rep.player)}"
    )
    L.append(
        f'- "Typical pros" = all other players in the dataset in the same situation '
        f"(receiving the same shot to the same zone, or playing it); {me} is never part of "
        f"{me}'s own reference.\n"
    )

    L.append("## Top insights\n")
    stability_note = ""
    if stability is not None and not top.empty:
        stability_note = (
            f"Only patterns selected in at least {MIN_STABLE_SHARE:.0%} of the "
            f"leave-one-match-out folds are ranked (the top-{TOP_K} is re-selected "
            f"{int(top.folds.max())} times, each time without one match); the rest are listed "
            f"under 'less stable'. "
        )
    L.append(
        f"Where {me} differs most from typical pros, among patterns a coach can act on mid-match. "
        f"Ranked by the smallest difference the data still supports (the 95% interval bound "
        f"nearest zero), with at most {PER_FAMILY} per table. {stability_note}"
        f"`tentative` = the interval on the difference is wider than "
        f"{TENTATIVE_CI_WIDTH * 100:.0f} points or n is under {TENTATIVE_MIN_N}.\n"
    )
    L.append(top_insights_table(top, rep.player, s, with_folds=stability is not None))
    if not unstable.empty:
        L.append("### Less stable\n")
        L.append(
            f"Among the {STABILITY_POOL} best-ranked patterns on the full data, these are "
            f"selected in fewer than half of the leave-one-match-out folds; read them as "
            f"candidates, not findings.\n"
        )
        for _, row in unstable.iterrows():
            L.append(
                f"- {describe(row, rep.player, s)} Selected in {int(row.selected_folds)} of "
                f"{int(row.folds)} folds{'; tentative' if row.tentative else ''}."
            )
        L.append("")

    L.append(f"## How to play against {me}\n")
    L.append(
        f"For an opponent. Each line is a situation where {me}'s record differs from typical "
        f"pros with 95% confidence; 'loses within {within} shots' means the point ended within "
        f"{within} strokes of that shot and {me} lost it.\n"
    )
    L.extend(f"- {b}" for b in against) if against else L.append("_Nothing passes the tests._")
    L.append("")
    L.append(f"## What {me} should fix\n")
    L.append(f"Situations where {me} loses more often than typical pros.\n")
    if fix:
        L.extend(f"- {b}" for b in fix)
    else:
        L.append(
            f"_No situation where {me} loses more than typical pros passes the sample-size and "
            "interval tests._"
        )
    L.append("")

    L.append("## The evidence: danger tables\n")
    L.append(
        f"Each row: probability that {me} loses the point within {within} shots after that shot, "
        f"with the same probability for typical pros and the difference in percentage points "
        f"(Newcombe 95% interval). `signal` = the interval excludes zero; `too few` = under "
        f"{s.rates.min_n} strokes; `ref too few` = under {s.rates.min_n} in the reference. "
        f"Zones are always from the receiver's point of view, forehand/backhand by their "
        f"handedness; shots the rally ended on with an out or net error are excluded "
        f"(they are outcomes, not targets).\n"
    )
    lost = f"lost within {s.within}"
    L.append(f"### Shots {me} faces\n")
    L.append(f"Baseline over all shots {me} faces: {rep.baselines['danger_faced']:.1%}.\n")
    L.append(md_table(T["danger_faced"], "condition", "opponent shot -> zone", lost, 12, True))
    L.append("By shot type alone:\n")
    L.append(md_table(T[f"danger_faced_{s.shot_col}"], s.shot_col, "opponent shot", lost))
    L.append("By zone alone:\n")
    L.append(md_table(T["danger_faced_coach_zone"], "coach_zone", f"zone on {me}'s side", lost))

    L.append(f"### Shots {me} plays\n")
    L.append(f"Baseline over all of {me}'s shots: {rep.baselines['danger_hit']:.1%}.\n")
    L.append(md_table(T["danger_hit"], "condition", "shot -> opponent zone", lost, 12, True))
    L.append("By shot type alone:\n")
    L.append(md_table(T[f"danger_hit_{s.shot_col}"], s.shot_col, "shot", lost))
    L.append("By zone alone:\n")
    L.append(md_table(T["danger_hit_coach_zone"], "coach_zone", "opponent zone", lost))

    for split_name, title in (
        ("game3", "Game 3 only"),
        ("pressure", f"At {s.pressure_from}+ only"),
    ):
        if f"danger_faced@{split_name}" not in T:
            continue
        L.append(f"### {title}\n")
        L.append(f"Shots {me} faces:\n")
        L.append(
            md_table(
                T[f"danger_faced@{split_name}"], "condition", "opponent shot -> zone", lost, 8, True
            )
        )
        L.append(f"Shots {me} plays:\n")
        L.append(
            md_table(
                T[f"danger_hit@{split_name}"], "condition", "shot -> opponent zone", lost, 8, True
            )
        )

    if extra_sections:
        L.extend(extra_sections)

    L.append("## Context (descriptive, not ranked)\n")
    L.append("### How points end\n")
    L.append(
        f"Share of {me}'s rallies by how the final stroke decided them (P = {me}, O = opponent).\n"
    )
    L.append(endings_table(rep.endings, len(r)))
    L.append("### The two shots before the point was decided\n")
    L.append(
        f"Tokens: `P:` = {me}, `O:` = opponent. Given the rally reached this pattern and the next "
        f"shot ended it, how often did {me} win, next to typical pros in the same setup. These "
        f"condition on the rally ending, so they describe how points are decided rather than "
        f"what to do next. Reliable patterns only (n >= {s.rates.min_n}); "
        f"{int((~T['last2'].reliable).sum())} rarer patterns omitted.\n"
    )
    L.append(md_table(T["last2"], "last2", "setup (two shots)", "win rate", 12, True))
    L.append("### The three shots before the point was decided\n")
    L.append(f"{int((~T['last3'].reliable).sum())} rarer patterns omitted.\n")
    L.append(md_table(T["last3"], "last3", "setup (three shots)", "win rate", 12, True))
    L.append("### Rally length, game number, pressure, serving\n")
    L.append(
        "The reference here is the player's own overall win rate: across all pros these splits "
        "are 50% by construction (every rally has one winner and one loser).\n"
    )
    own = "own overall"
    L.append(md_table(T["length"], "length_bin", "strokes", ref_name=own))
    L.append(md_table(T["game"], "game", "game", ref_name=own))
    L.append(
        md_table(
            T["pressure"], "pressure", f"late game (either at {s.pressure_from}+)", ref_name=own
        )
    )
    L.append(md_table(T["serving"], "player_served", "serving", ref_name=own))
    for split_name, title in (
        ("game3", "Game 3 only"),
        ("pressure", f"At {s.pressure_from}+ only"),
    ):
        if f"length@{split_name}" in T:
            L.append(f"{title}, by rally length:\n")
            L.append(md_table(T[f"length@{split_name}"], "length_bin", "strokes", ref_name=own))

    L.append("### Where the shuttle goes (landing heatmaps)\n")
    img_dir = out_dir / f"{name}_img"
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
        "outcome but are excluded from the shot-sequence tables, and unknown-type strokes are "
        "excluded from the danger tables."
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
