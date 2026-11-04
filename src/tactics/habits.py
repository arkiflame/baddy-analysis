"""Habit shots, predictability and set plays, each against "typical pros".

Three scouting questions:

1. **Response tendencies.** Given what just came at the player (opponent's shot type and the
   coach zone it landed in, body included), what does the player reply with (shot type, and
   shot type + target zone)? A HABIT is a reply the player chooses significantly more often than
   other pros in the same situation (situation n >= 30 on both sides, Newcombe interval on the
   difference of shares excludes zero).
2. **Predictability.** The Shannon entropy (bits) of the reply distribution per situation. Low
   entropy = few replies = easy to anticipate. Plug-in entropy is biased low for small samples,
   so we use the Miller-Madow correction and compare with the population entropy estimated by
   SUBSAMPLING the population's replies to the player's n (DECISIONS D22); a situation is
   "more predictable" when the player's entropy sits below the 2.5th percentile of those
   subsamples.
3. **Set plays.** The first 3 and 4 strokes of the rally (serve, return, third, fourth) as shot
   types, split by who served. Ranked by how DISTINCTIVE the sequence is (difference between
   the player's share and other pros' share), with the win rate attached.

Everything excludes strokes of unknown type. Reply zones exclude rally-ending out / net errors
(they are outcomes, not choices); the shot-type level keeps every stroke.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from tactics.analyses import (
    OUTCOME_ZONES,
    AnalysisSettings,
    player_strokes,
    population_rallies,
    rally_frame,
)
from tactics.stats import RateSettings, compare_to_reference, wilson_ci

LN2 = float(np.log(2))


# ---------------------------------------------------------------------------------------
# Reply frame (all hitters at once)
# ---------------------------------------------------------------------------------------


def reply_frame(df: pd.DataFrame) -> pd.DataFrame:
    """One row per non-serve stroke that answers a known in-play shot.

    Columns: player (the hitter), situation ('incoming shot -> incoming zone', zone from the
    player's own view), situation_any ('incoming shot -> any'), reply_shot, reply (shot ->
    target zone, None when the stroke ended the rally with an error), player_won, rally_id,
    match_id.
    """
    d = df[df.annotated & df.rally_winner.notna()].sort_values(["rally_id", "stroke_no"])
    g = d.groupby("rally_id", observed=True)
    prev_shot = g["shot_coarse"].shift(1).astype("string")
    prev_zone = g["coach_zone"].shift(1).astype("string")
    shot = d.shot_coarse.astype("string")
    zone = d.coach_zone.astype("string")
    ok = (
        ~d.is_serve
        & prev_shot.notna()
        & prev_zone.notna()
        & ~prev_zone.isin(OUTCOME_ZONES)
        & (prev_shot != "unknown")
        & (shot != "unknown")
    )
    out = pd.DataFrame(
        {
            "player": d.hitter.astype(str),
            "match_id": d.match_id.astype(str),
            "rally_id": d.rally_id,
            "stroke_no": d.stroke_no,
            "situation": prev_shot + " -> " + prev_zone,
            "situation_any": prev_shot + " -> any",
            "reply_shot": shot,
            "reply": (shot + " -> " + zone).where(zone.notna() & ~zone.isin(OUTCOME_ZONES)),
            "player_won": d.rally_winner.astype(str).to_numpy() == d.hitter.astype(str).to_numpy(),
        }
    )[ok.to_numpy()]
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------------------
# 1. Response tendencies
# ---------------------------------------------------------------------------------------


def _share_table(rf: pd.DataFrame, sit_col: str, reply_col: str) -> pd.DataFrame:
    """Rows (situation, reply) with n = situation count, wins = reply count, rate = share."""
    d = rf.dropna(subset=[reply_col])
    counts = d.groupby([sit_col, reply_col], observed=True).size().rename("wins").reset_index()
    totals = d.groupby(sit_col, observed=True).size().rename("n")
    counts = counts.merge(totals, left_on=sit_col, right_index=True)
    counts["rate"] = counts.wins / counts.n
    counts["key"] = counts[sit_col].astype(str) + " | " + counts[reply_col].astype(str)
    counts = counts.rename(columns={sit_col: "situation", reply_col: "reply"})
    lo, hi = wilson_ci(counts.wins, counts.n)
    counts["ci_lo"], counts["ci_hi"] = lo, hi
    return counts


def response_tendencies(
    rf: pd.DataFrame, player: str, level: str, settings: RateSettings
) -> pd.DataFrame:
    """level: 'shot' (reply shot type, any zone), 'shot_zone' (reply shot -> target zone);
    situations at both granularities ('shot -> zone' and 'shot -> any')."""
    reply_col = "reply_shot" if level == "shot" else "reply"
    mine, others = rf[rf.player == player], rf[rf.player != player]
    parts = []
    for sit_col in ("situation", "situation_any"):
        t = _share_table(mine, sit_col, reply_col)
        ref = _share_table(others, sit_col, reply_col)
        if t.empty:
            continue
        parts.append(compare_to_reference(t, ref, settings))
    if not parts:
        return pd.DataFrame()
    out = pd.concat(parts, ignore_index=True)
    out["reliable"] = out.n >= settings.min_n
    out["habit"] = out.reliable & out.ref_reliable & (out.delta_lo > 0)
    out["candidate"] = out.reliable & out.ref_reliable & out.delta_excludes_zero
    return out.sort_values(["habit", "score"], ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------------------
# 2. Predictability (entropy)
# ---------------------------------------------------------------------------------------


def entropy_mm(counts: np.ndarray) -> float:
    """Miller-Madow corrected Shannon entropy in bits: H_plugin + (K - 1) / (2 n ln 2)."""
    counts = np.asarray(counts, dtype=float)
    counts = counts[counts > 0]
    n = counts.sum()
    if n <= 0:
        return float("nan")
    p = counts / n
    h = -(p * np.log(p)).sum()
    k = len(counts)
    return float((h + (k - 1) / (2 * n)) / LN2)


def _entropy_of(labels: np.ndarray) -> float:
    _, c = np.unique(labels, return_counts=True)
    return entropy_mm(c)


def predictability(
    rf: pd.DataFrame,
    player: str,
    settings: RateSettings,
    n_boot: int = 200,
    seed: int = 0,
    reply_col: str = "reply",
) -> pd.DataFrame:
    """Per situation (n >= min_n): the player's reply entropy with a bootstrap interval, the
    population's entropy subsampled to the same n (mean and 2.5-97.5 percentiles), and the
    effective number of replies 2^H."""
    rng = np.random.default_rng(seed)
    mine = rf[(rf.player == player)].dropna(subset=[reply_col])
    others = rf[(rf.player != player)].dropna(subset=[reply_col])
    rows = []
    for sit_col in ("situation", "situation_any"):
        for sit, grp in mine.groupby(sit_col, observed=True):
            n = len(grp)
            if n < settings.min_n:
                continue
            pool = others[others[sit_col] == sit][reply_col].to_numpy()
            if len(pool) < settings.min_n:
                continue
            labels = grp[reply_col].to_numpy()
            h = _entropy_of(labels)
            boot = np.array(
                [_entropy_of(rng.choice(labels, n, replace=True)) for _ in range(n_boot)]
            )
            sub = np.array([_entropy_of(rng.choice(pool, n, replace=True)) for _ in range(n_boot)])
            top = pd.Series(labels).value_counts()
            rows.append(
                {
                    "situation": sit,
                    "n": n,
                    "entropy_bits": h,
                    "lo": float(np.percentile(boot, 2.5)),
                    "hi": float(np.percentile(boot, 97.5)),
                    "effective_replies": float(2**h),
                    "ref_n": int(len(pool)),
                    "ref_entropy_bits": float(sub.mean()),
                    "ref_lo": float(np.percentile(sub, 2.5)),
                    "ref_hi": float(np.percentile(sub, 97.5)),
                    "delta": h - float(sub.mean()),
                    "more_predictable": h < float(np.percentile(sub, 2.5)),
                    "less_predictable": h > float(np.percentile(sub, 97.5)),
                    "top_reply": str(top.index[0]),
                    "top_share": float(top.iloc[0] / n),
                }
            )
    out = pd.DataFrame(rows)
    return out.sort_values("delta").reset_index(drop=True) if len(out) else out


# ---------------------------------------------------------------------------------------
# 3. Set plays
# ---------------------------------------------------------------------------------------


def set_plays(
    r: pd.DataFrame, pop_r: pd.DataFrame, k: int, serving: bool, settings: RateSettings
) -> pd.DataFrame:
    """Frequency and win rate of the first k strokes (shot types, P/O tokens) in rallies the
    player served (serving=True) or received, next to other pros in the same role."""
    col = f"first{k}"
    mine = r[(r.player_served == serving) & r[col].notna() & ~r.has_unknown]
    others = pop_r[(pop_r.player_served == serving) & pop_r[col].notna() & ~pop_r.has_unknown]
    if mine.empty:
        return pd.DataFrame()

    def table(d: pd.DataFrame) -> pd.DataFrame:
        g = d.groupby(col, observed=True)
        t = g.agg(wins=("player_won", "size"), rally_wins=("player_won", "sum")).reset_index()
        t["n"] = len(d)
        t["rate"] = t.wins / t.n  # share of rallies that start this way
        t["key"] = t[col].astype(str)
        t["win_rate"] = t.rally_wins / t.wins
        t["win_lo"], t["win_hi"] = wilson_ci(t.rally_wins, t.wins)
        return t.rename(columns={col: "sequence"})

    t, ref = table(mine), table(others)
    out = compare_to_reference(t, ref, settings)
    out = out.merge(
        ref[["key", "win_rate"]].rename(columns={"win_rate": "ref_win_rate"}), on="key", how="left"
    )
    out["reliable"] = out.wins >= settings.min_n  # enough rallies with this sequence
    out["candidate"] = out.reliable & out.ref_reliable & out.delta_excludes_zero
    return out.sort_values(["candidate", "score"], ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------------------
# All together + report section
# ---------------------------------------------------------------------------------------


@dataclass(slots=True)
class HabitSummary:
    player: str
    tendencies_shot: pd.DataFrame
    tendencies_zone: pd.DataFrame
    predictability: pd.DataFrame
    set_plays: dict[tuple[int, bool], pd.DataFrame]
    n_replies: int


def summarise(df: pd.DataFrame, player: str, s: AnalysisSettings | None = None) -> HabitSummary:
    s = s or AnalysisSettings()
    rf = reply_frame(df)
    ps = player_strokes(df, player)
    r = rally_frame(ps, s)
    pop_r = population_rallies(df, player, s)
    plays = {
        (k, serving): set_plays(r, pop_r, k, serving, s.rates)
        for k in (3, 4)
        for serving in (True, False)
    }
    return HabitSummary(
        player,
        response_tendencies(rf, player, "shot", s.rates),
        response_tendencies(rf, player, "shot_zone", s.rates),
        predictability(rf, player, s.rates),
        plays,
        int((rf.player == player).sum()),
    )


def _pct(v) -> str:
    return "-" if pd.isna(v) else f"{v:.0%}"


def _tendency_table(t: pd.DataFrame, top: int) -> str:
    d = t[t.habit].head(top)
    if d.empty:
        return "_No reply is chosen significantly more often than typical pros (situation n >= 30 on both sides)._\n"
    out = pd.DataFrame(
        {
            "situation (incoming shot -> zone)": d.situation,
            "reply": d.reply,
            "n (situations)": d.n.astype(int),
            "share": d.rate.map(_pct),
            "95% CI": [f"{lo:.0%}-{hi:.0%}" for lo, hi in zip(d.ci_lo, d.ci_hi, strict=True)],
            "typical pros": [
                f"{_pct(r)} (n={int(n)})" for r, n in zip(d.ref_rate, d.ref_n, strict=True)
            ],
            "difference (95% CI)": [
                f"{x * 100:+.0f} ({lo * 100:+.0f} to {hi * 100:+.0f})"
                for x, lo, hi in zip(d.delta, d.delta_lo, d.delta_hi, strict=True)
            ],
        }
    )
    return out.to_markdown(index=False, disable_numparse=True) + "\n"


def _predictability_table(t: pd.DataFrame, top: int, most: bool) -> str:
    if t.empty:
        return "_No situation reaches n >= 30 on both sides._\n"
    d = t.head(top) if most else t.sort_values("delta", ascending=False).head(top)
    out = pd.DataFrame(
        {
            "situation": d.situation,
            "n": d.n.astype(int),
            "entropy (bits)": [
                f"{h:.2f} ({lo:.2f}-{hi:.2f})"
                for h, lo, hi in zip(d.entropy_bits, d.lo, d.hi, strict=True)
            ],
            "typical pros at same n": [
                f"{h:.2f} ({lo:.2f}-{hi:.2f})"
                for h, lo, hi in zip(d.ref_entropy_bits, d.ref_lo, d.ref_hi, strict=True)
            ],
            "effective replies": d.effective_replies.map(lambda v: f"{v:.1f}"),
            "most common reply": [
                f"{r} ({s:.0%})" for r, s in zip(d.top_reply, d.top_share, strict=True)
            ],
            "flag": np.where(
                d.more_predictable,
                "more predictable",
                np.where(d.less_predictable, "less predictable", ""),
            ),
        }
    )
    return out.to_markdown(index=False, disable_numparse=True) + "\n"


def _set_play_table(t: pd.DataFrame, me: str, top: int) -> str:
    if t.empty:
        return "_no data_\n"
    d = t[t.reliable].head(top)
    if d.empty:
        return f"_No opening sequence occurs {30} times or more._\n"
    out = pd.DataFrame(
        {
            f"opening (P = {me}, O = opponent)": d.sequence.astype(str),
            "rallies": d.wins.astype(int),
            "share": d.rate.map(_pct),
            "typical pros": [
                f"{_pct(r)} (n={int(n)})" for r, n in zip(d.ref_rate, d.ref_n, strict=True)
            ],
            "difference (95% CI)": [
                f"{x * 100:+.0f} ({lo * 100:+.0f} to {hi * 100:+.0f})" if n else "-"
                for x, lo, hi, n in zip(d.delta, d.delta_lo, d.delta_hi, d.ref_n, strict=True)
            ],
            f"{me} wins": [
                f"{w:.0%} ({lo:.0%}-{hi:.0%})"
                for w, lo, hi in zip(d.win_rate, d.win_lo, d.win_hi, strict=True)
            ],
            "typical pros win": d.ref_win_rate.map(_pct),
            "flag": np.where(d.candidate, "distinctive", ""),
        }
    )
    return out.to_markdown(index=False, disable_numparse=True) + "\n"


def section(h: HabitSummary, me: str, s: AnalysisSettings, top: int = 10) -> list[str]:
    n_hab_shot = int(h.tendencies_shot.habit.sum()) if len(h.tendencies_shot) else 0
    n_hab_zone = int(h.tendencies_zone.habit.sum()) if len(h.tendencies_zone) else 0
    L = [
        "## Habits and set plays\n",
        f"Based on {h.n_replies} of {me}'s replies to a known in-play shot. A *situation* is the "
        "opponent's shot type and the zone it landed in (from "
        f"{me}'s view, body included); '-> any' pools the zones. A *habit* is a reply chosen "
        f"significantly more often than typical pros in the same situation (n >= {s.rates.min_n} "
        "situations on both sides, Newcombe 95% interval on the difference of shares excludes zero). "
        f"Habits found: {n_hab_shot} by reply shot type, {n_hab_zone} by reply shot and target zone.\n",
        "### Habits by reply shot type\n",
        _tendency_table(h.tendencies_shot, top),
        "### Habits by reply shot and target zone\n",
        "Target zone from the opponent's view; replies that ended the rally with an error are excluded here.\n",
        _tendency_table(h.tendencies_zone, top),
        "### Most predictable situations\n",
        f"Shannon entropy (bits, Miller-Madow corrected, bootstrap 95% interval) of {me}'s reply "
        "(shot and target zone) per situation, next to typical pros' entropy estimated by subsampling "
        f"their replies to {me}'s n (mean and 2.5-97.5 percentiles over 200 draws). "
        "'Effective replies' = 2^entropy: how many equally likely replies the distribution is worth. "
        "A situation is flagged when the entropy falls outside the typical-pro band.\n",
        _predictability_table(h.predictability, top, most=True),
        "Least predictable situations:\n",
        _predictability_table(h.predictability, 5, most=False),
    ]
    for serving, label in ((True, f"when {me} serves"), (False, f"when {me} receives")):
        L.append(f"### Set plays {label}\n")
        L.append(
            f"The first three and four strokes as shot types (P = {me}, O = opponent), ranked by how "
            f"distinctive the opening is versus typical pros in the same role (difference in share of "
            f"rallies, 95% interval); openings seen fewer than {s.rates.min_n} times are omitted.\n"
        )
        for k in (3, 4):
            L.append(f"First {k} strokes:\n")
            L.append(_set_play_table(h.set_plays[(k, serving)], me, 8))
    return L
