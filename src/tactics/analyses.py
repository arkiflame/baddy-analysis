"""Tactical analyses for one player.

Every function takes the annotated stroke table (loader.strokes_frame + zones.annotate) and a
player NAME (never the dataset's A/B label: A is always the match winner, which would leak the
outcome). Each returns a rate table from stats.rate_table with a `key` column so the same
analysis can be re-run on holdout matches and joined row by row.

Vocabulary
----------
* rally frame      one row per rally the player took part in
* P / O tokens     "P:smash" = the player hit a smash, "O:lob" = the opponent did
* lost_within_2    the point ended on this stroke, the next one, or the one after, and the
                   player lost it. Measured on strokes the player HIT ("what I do that gets
                   me killed") and on strokes the player RECEIVED ("what hurts me").
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from tactics.stats import RateSettings, rate_table

# "out" and "net_error" are how a rally ended, not where a shot was aimed. Conditioning on
# them would just rediscover that errors lose points, so danger analyses exclude them.
OUTCOME_ZONES = frozenset({"out", "net_error"})


@dataclass(frozen=True, slots=True)
class AnalysisSettings:
    rates: RateSettings = field(default_factory=RateSettings)
    shot_col: str = "shot_coarse"  # or "shot" for the full 18 types
    pressure_from: int = 18  # a rally is "late game" if either score >= this
    length_bins: tuple[int, ...] = (0, 4, 8, 12, 20, 999)
    length_labels: tuple[str, ...] = ("1-4", "5-8", "9-12", "13-20", "21+")
    within: int = 2  # "loses within the next N shots"


# ---------------------------------------------------------------------------------------
# Frames
# ---------------------------------------------------------------------------------------


def player_strokes(df: pd.DataFrame, player: str) -> pd.DataFrame:
    """All strokes from rallies the player took part in, with player-centric columns."""
    involved = (df.hitter == player) | (df.receiver == player)
    d = df[involved & df.annotated & df.rally_winner.notna()].copy()
    d["player_hit"] = d.hitter == player
    d["player_won"] = d.rally_winner == player
    d["opponent"] = np.where(d.player_hit, d.receiver.astype(str), d.hitter.astype(str))
    d["token"] = np.where(d.player_hit, "P:", "O:") + d["shot_coarse"].astype(str)
    d["token18"] = np.where(d.player_hit, "P:", "O:") + d["shot"].astype(str)
    return d


def rally_frame(ps: pd.DataFrame, s: AnalysisSettings) -> pd.DataFrame:
    """One row per rally: outcome, length bucket, game, pressure, last-k token sequences."""
    ps = ps.sort_values(["rally_id", "stroke_no"])
    shot_token = "token" if s.shot_col == "shot_coarse" else "token18"
    g = ps.groupby("rally_id", observed=True, sort=False)
    r = g.agg(
        match_id=("match_id", "first"),
        game=("game", "first"),
        opponent=("opponent", "first"),
        n_strokes=("n_strokes", "first"),
        player_won=("player_won", "first"),
        has_unknown=("rally_has_unknown", "first"),
        lose_reason=("lose_reason", "first"),
    ).reset_index()
    first = g.first()
    r["player_served"] = first["player_hit"].to_numpy()  # stroke 1 is the serve
    # score before the rally from the player's side (first stroke row carries hitter/receiver view)
    sb_h, sb_r, ph = (
        first["score_before_hitter"],
        first["score_before_receiver"],
        first["player_hit"],
    )
    r["score_player"] = np.where(ph, sb_h, sb_r)
    r["score_opponent"] = np.where(ph, sb_r, sb_h)
    r["pressure"] = np.maximum(r.score_player, r.score_opponent) >= s.pressure_from
    r["length_bin"] = pd.cut(r.n_strokes, bins=list(s.length_bins), labels=list(s.length_labels))
    r["last_hit_by_player"] = g["player_hit"].last().to_numpy()
    tokens = g[shot_token].agg(list)
    # The final stroke is the winner or the error that decided the point, so conditioning on it
    # is circular. The "setup" is the k strokes BEFORE the final one: given the rally reached
    # this pattern and the next shot ended it, who won?
    r["last2"] = tokens.map(lambda t: " > ".join(t[-3:-1]) if len(t) >= 3 else None).to_numpy()
    r["last3"] = tokens.map(lambda t: " > ".join(t[-4:-1]) if len(t) >= 4 else None).to_numpy()
    r["end_token"] = tokens.map(lambda t: t[-1]).to_numpy()
    r["end_type"] = np.select(
        [
            r.player_won & r.last_hit_by_player,
            r.player_won & ~r.last_hit_by_player,
            ~r.player_won & r.last_hit_by_player,
        ],
        ["P winner", "O error", "P error"],
        default="O winner",
    )
    return r


def endings(r: pd.DataFrame, shot_col: str) -> pd.DataFrame:
    """How the player's points end: counts of (end type, final shot). Descriptive, not ranked."""
    t = r.groupby(["end_type", "end_token"], observed=True).size().rename("n").reset_index()
    t["share_of_type"] = t.n / t.groupby("end_type").n.transform("sum")
    t["share_of_all"] = t.n / len(r)
    return t.sort_values(["end_type", "n"], ascending=[True, False]).reset_index(drop=True)


# ---------------------------------------------------------------------------------------
# Analyses (each returns a rate table with a `key` column)
# ---------------------------------------------------------------------------------------


def win_rate_by_length(r: pd.DataFrame, baseline: float, s: AnalysisSettings) -> pd.DataFrame:
    t = rate_table(r, "length_bin", "player_won", baseline, s.rates)
    t["key"] = "length " + t.length_bin.astype(str)
    return t


def win_rate_by_last_sequence(
    r: pd.DataFrame, k: int, baseline: float, s: AnalysisSettings
) -> pd.DataFrame:
    col = f"last{k}"
    d = r[~r.has_unknown & r[col].notna()]
    t = rate_table(d, col, "player_won", baseline, s.rates)
    t["key"] = f"last{k} " + t[col].astype(str)
    return t


def win_rate_by_split(
    r: pd.DataFrame, split: str, baseline: float, s: AnalysisSettings
) -> pd.DataFrame:
    t = rate_table(r, split, "player_won", baseline, s.rates)
    t["key"] = f"{split} " + t[split].astype(str)
    return t


def danger_conditions(
    ps: pd.DataFrame, s: AnalysisSettings, hit_by_player: bool
) -> tuple[pd.DataFrame, float]:
    """P(point lost within the next N shots | shot type x receiver zone).

    hit_by_player=True : strokes the player hit  -> where the player's choices go wrong
    hit_by_player=False: strokes the player faced -> what opponents do that hurts the player
    Baseline is the same probability over all such strokes.
    """
    d = ps[
        (ps.player_hit == hit_by_player)
        & ~ps.is_serve
        & ps.coach_zone.notna()
        & ~ps.coach_zone.isin(OUTCOME_ZONES)
    ].copy()
    d["lost_within"] = (d.strokes_to_end <= s.within) & ~d.player_won
    baseline = float(d.lost_within.mean()) if len(d) else float("nan")
    d["condition"] = d[s.shot_col].astype(str) + " -> " + d.coach_zone.astype(str)
    t = rate_table(d, "condition", "lost_within", baseline, s.rates)
    who = "hit" if hit_by_player else "faced"
    t["key"] = f"{who} " + t.condition.astype(str)
    return t, baseline


def danger_by_single_factor(
    ps: pd.DataFrame, s: AnalysisSettings, hit_by_player: bool, factor: str
) -> tuple[pd.DataFrame, float]:
    d = ps[
        (ps.player_hit == hit_by_player)
        & ~ps.is_serve
        & ps[factor].notna()
        & ~ps.coach_zone.isin(OUTCOME_ZONES)
    ].copy()
    d["lost_within"] = (d.strokes_to_end <= s.within) & ~d.player_won
    baseline = float(d.lost_within.mean()) if len(d) else float("nan")
    t = rate_table(d, factor, "lost_within", baseline, s.rates)
    who = "hit" if hit_by_player else "faced"
    t["key"] = f"{who} {factor} " + t[factor].astype(str)
    return t, baseline


# ---------------------------------------------------------------------------------------
# Everything for one player
# ---------------------------------------------------------------------------------------


@dataclass(slots=True)
class PlayerReport:
    player: str
    rallies: pd.DataFrame
    strokes: pd.DataFrame
    baseline_win: float
    tables: dict[str, pd.DataFrame]
    baselines: dict[str, float]
    endings: pd.DataFrame

    @property
    def insights(self) -> pd.DataFrame:
        """All rows of all tables, with the analysis name attached, ranked for the top-5."""
        parts = []
        for name, t in self.tables.items():
            if t.empty:
                continue
            x = t[
                [
                    "key",
                    "n",
                    "wins",
                    "rate",
                    "ci_lo",
                    "ci_hi",
                    "shrunk",
                    "lift",
                    "reliable",
                    "ci_excludes_baseline",
                    "baseline",
                ]
            ].copy()
            x.insert(0, "analysis", name)
            parts.append(x)
        allx = pd.concat(parts, ignore_index=True)
        allx["score"] = allx.lift.abs() * np.sqrt(allx.n)
        return allx.sort_values(
            ["reliable", "ci_excludes_baseline", "score"], ascending=False
        ).reset_index(drop=True)


def analyse_player(
    df: pd.DataFrame, player: str, s: AnalysisSettings | None = None
) -> PlayerReport:
    s = s or AnalysisSettings()
    ps = player_strokes(df, player)
    if ps.empty:
        raise ValueError(f"no rallies found for {player!r}; run `tactics players` to list names")
    r = rally_frame(ps, s)
    base = float(r.player_won.mean())
    tables: dict[str, pd.DataFrame] = {}
    baselines: dict[str, float] = {}

    tables["length"] = win_rate_by_length(r, base, s)
    tables["last2"] = win_rate_by_last_sequence(r, 2, base, s)
    tables["last3"] = win_rate_by_last_sequence(r, 3, base, s)
    tables["game"] = win_rate_by_split(r, "game", base, s)
    tables["pressure"] = win_rate_by_split(r, "pressure", base, s)
    tables["serving"] = win_rate_by_split(r, "player_served", base, s)
    for name in ("length", "last2", "last3", "game", "pressure", "serving"):
        baselines[name] = base

    for hit_by_player, tag in ((True, "hit"), (False, "faced")):
        t, b = danger_conditions(ps, s, hit_by_player)
        tables[f"danger_{tag}"] = t
        baselines[f"danger_{tag}"] = b
        for factor in (s.shot_col, "coach_zone"):
            t, b = danger_by_single_factor(ps, s, hit_by_player, factor)
            tables[f"danger_{tag}_{factor}"] = t
            baselines[f"danger_{tag}_{factor}"] = b

    # splits of the main tables by game and by pressure
    for split_name, mask in (("game3", r.game == 3), ("pressure", r.pressure)):
        sub = r[mask]
        if len(sub):
            b = float(sub.player_won.mean())
            tables[f"length@{split_name}"] = win_rate_by_length(sub, b, s)
            tables[f"last2@{split_name}"] = win_rate_by_last_sequence(sub, 2, b, s)
            baselines[f"length@{split_name}"] = b
            baselines[f"last2@{split_name}"] = b
        subs = ps[ps.rally_id.isin(sub.rally_id)]
        if len(subs):
            t, b = danger_conditions(subs, s, True)
            tables[f"danger_hit@{split_name}"] = t
            baselines[f"danger_hit@{split_name}"] = b

    return PlayerReport(player, r, ps, base, tables, baselines, endings(r, s.shot_col))


def coverage(df: pd.DataFrame) -> pd.DataFrame:
    """Matches, rallies and win rate per player, for `tactics players`."""
    d = df[df.annotated & df.rally_winner.notna()]
    rows = []
    for player in sorted(set(d.hitter.astype(str)) | set(d.receiver.astype(str))):
        inv = d[(d.hitter == player) | (d.receiver == player)]
        rallies = inv.drop_duplicates("rally_id")
        rows.append(
            {
                "player": player,
                "matches": inv.match_id.nunique(),
                "rallies": len(rallies),
                "win_rate": float((rallies.rally_winner == player).mean()),
            }
        )
    return (
        pd.DataFrame(rows)
        .sort_values(["matches", "rallies"], ascending=False)
        .reset_index(drop=True)
    )
