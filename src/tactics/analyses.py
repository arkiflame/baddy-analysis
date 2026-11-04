"""Tactical analyses for one player, each compared with "typical pros".

Every function takes the annotated stroke table (loader.strokes_frame + zones.annotate) and a
player NAME (never the dataset's A/B label: A is always the match winner, which would leak the
outcome). Each returns a rate table from stats.rate_table with a `key` column so the same
analysis can be re-run on other matches and joined row by row.

v2 (features-v3 branch): every rate carries a REFERENCE rate for the same pattern measured on
all other players, and a CI on the difference (stats.compare_to_reference). "After opponents'
smashes Axelsen loses within 2 shots 18% of the time" is only interesting if typical pros lose
less; ranking by the difference removes the universal truths of badminton from the top-5.

Vocabulary
----------
* rally frame      one row per rally the player took part in
* P / O tokens     "P:smash" = the player hit a smash, "O:lob" = the opponent did
* lost_within_2    the point ended on this stroke, the next one, or the one after, and the
                   player lost it. Measured on strokes the player HIT ("what I do that gets
                   me killed") and on strokes the player RECEIVED ("what hurts me").
* population       the same measure over all OTHER players in the same role (receiver for
                   "faced", hitter for "hit"), so the player never sits in their own reference.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from tactics.stats import RateSettings, compare_to_reference, rate_table

# "out" and "net_error" are how a rally ended, not where a shot was aimed. Conditioning on
# them would just rediscover that errors lose points, so danger analyses exclude them.
OUTCOME_ZONES = frozenset({"out", "net_error"})

# Analyses a coach can act on mid-match: a shot type and/or a zone to hit or avoid. Only these
# feed the ranked top insights; rally length, game number and "what happened right before the
# point ended" are descriptive context (DECISIONS D20).
ACTIONABLE_FAMILIES = ("danger_hit", "danger_faced")


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


def _valid(df: pd.DataFrame) -> pd.DataFrame:
    return df[df.annotated & df.rally_winner.notna()]


def _tokens(d: pd.DataFrame) -> pd.DataFrame:
    d["token"] = np.where(d.player_hit, "P:", "O:") + d["shot_coarse"].astype(str)
    d["token18"] = np.where(d.player_hit, "P:", "O:") + d["shot"].astype(str)
    return d


def player_strokes(df: pd.DataFrame, player: str) -> pd.DataFrame:
    """All strokes from rallies the player took part in, with player-centric columns."""
    involved = (df.hitter == player) | (df.receiver == player)
    d = _valid(df[involved]).copy()
    d["player_hit"] = d.hitter.astype(str) == player
    d["player_won"] = d.rally_winner.astype(str) == player
    d["opponent"] = np.where(d.player_hit, d.receiver.astype(str), d.hitter.astype(str))
    return _tokens(d)


def population_strokes(df: pd.DataFrame, player: str, hit_by_player: bool) -> pd.DataFrame:
    """Strokes of all OTHER players in one role, shaped like player_strokes.

    hit_by_player=True : every stroke not hit by the player, seen from its hitter
    hit_by_player=False: every stroke not received by the player, seen from its receiver
    Exclusion is by role, not by match: the player's opponents facing the player's shots are
    other pros facing that pattern, so they belong in the reference (DECISIONS D19).
    """
    d = _valid(df)
    d = d[d.hitter != player] if hit_by_player else d[d.receiver != player]
    d = d.copy()
    who = (d.hitter if hit_by_player else d.receiver).astype(str).to_numpy()
    d["player_hit"] = hit_by_player
    d["player_won"] = d.rally_winner.astype(str).to_numpy() == who
    d["opponent"] = (d.receiver if hit_by_player else d.hitter).astype(str)
    return _tokens(d)


def population_rallies(df: pd.DataFrame, player: str, s: AnalysisSettings) -> pd.DataFrame:
    """Rally frame of all other players: each rally once from the server's view and once from
    the receiver's view (tokens relative to that side), dropping the views that ARE the player."""
    d = _valid(df).sort_values(["rally_id", "stroke_no"])
    server = d.groupby("rally_id", observed=True).hitter.transform("first").astype(str)
    other = pd.Series(np.where(d.hitter == server, d.receiver, d.hitter), index=d.index).astype(str)
    parts = []
    for tag, me in (("S", server), ("R", other)):
        keep = me != player
        x, me_x = d[keep].copy(), me[keep].to_numpy()
        x["player_hit"] = x.hitter.to_numpy() == me_x
        x["player_won"] = x.rally_winner.to_numpy() == me_x
        x["opponent"] = np.where(x.player_hit, x.receiver, x.hitter)
        x["rally_id"] = x.rally_id.astype(str) + "|" + tag
        parts.append(_tokens(x))
    return rally_frame(pd.concat(parts, ignore_index=True), s)


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
    # is circular. The "setup" is the k strokes BEFORE the final one (DECISIONS D9).
    r["last2"] = tokens.map(lambda t: " > ".join(t[-3:-1]) if len(t) >= 3 else None).to_numpy()
    r["last3"] = tokens.map(lambda t: " > ".join(t[-4:-1]) if len(t) >= 4 else None).to_numpy()
    r["end_token"] = tokens.map(lambda t: t[-1]).to_numpy()
    # openings for the set-play analysis: the first k strokes INCLUDING the serve
    r["first3"] = tokens.map(lambda t: " > ".join(t[:3]) if len(t) >= 3 else None).to_numpy()
    r["first4"] = tokens.map(lambda t: " > ".join(t[:4]) if len(t) >= 4 else None).to_numpy()
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


def stroke_pressure(ps: pd.DataFrame, s: AnalysisSettings) -> pd.Series:
    """Late-game flag per stroke; identical to the rally-level flag because both score columns
    describe the score before the rally."""
    return np.maximum(ps.score_before_hitter, ps.score_before_receiver) >= s.pressure_from


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


def _danger_frame(ps: pd.DataFrame, s: AnalysisSettings, hit_by_player: bool) -> pd.DataFrame:
    d = ps[
        (ps.player_hit == hit_by_player)
        & ~ps.is_serve
        & ps.coach_zone.notna()
        & ~ps.coach_zone.isin(OUTCOME_ZONES)
        & (ps[s.shot_col].astype(str) != "unknown")
    ].copy()
    d["lost_within"] = (d.strokes_to_end <= s.within) & ~d.player_won
    return d


def danger_conditions(
    ps: pd.DataFrame, s: AnalysisSettings, hit_by_player: bool
) -> tuple[pd.DataFrame, float]:
    """P(point lost within the next N shots | shot type x receiver zone).

    hit_by_player=True : strokes the player hit  -> where the player's choices go wrong
    hit_by_player=False: strokes the player faced -> what opponents do that hurts the player
    Baseline is the same probability over all such strokes.
    """
    d = _danger_frame(ps, s, hit_by_player)
    baseline = float(d.lost_within.mean()) if len(d) else float("nan")
    d["condition"] = d[s.shot_col].astype(str) + " -> " + d.coach_zone.astype(str)
    t = rate_table(d, "condition", "lost_within", baseline, s.rates)
    who = "hit" if hit_by_player else "faced"
    t["key"] = f"{who} " + t.condition.astype(str)
    return t, baseline


def danger_by_single_factor(
    ps: pd.DataFrame, s: AnalysisSettings, hit_by_player: bool, factor: str
) -> tuple[pd.DataFrame, float]:
    d = _danger_frame(ps, s, hit_by_player)
    d = d[d[factor].notna()]
    baseline = float(d.lost_within.mean()) if len(d) else float("nan")
    t = rate_table(d, factor, "lost_within", baseline, s.rates)
    who = "hit" if hit_by_player else "faced"
    t["key"] = f"{who} {factor} " + t[factor].astype(str)
    return t, baseline


# ---------------------------------------------------------------------------------------
# Everything for one player
# ---------------------------------------------------------------------------------------

INSIGHT_COLUMNS = [
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
    "ref_n",
    "ref_wins",
    "ref_rate",
    "delta",
    "delta_lo",
    "delta_hi",
    "ref_reliable",
    "delta_excludes_zero",
    "score",
    "ref_kind",
]


def family(analysis: str) -> str:
    """'danger_faced_coach_zone@game3' -> 'danger_faced_single@game3'.

    Shot-and-zone tables keep their own family; the two single-factor tables (shot alone, zone
    alone) share one, so the top-5 cap can allow fewer of the coarse rows, which otherwise win
    every ranking because their n is largest."""
    base, _, split = analysis.partition("@")
    for fam in ACTIONABLE_FAMILIES:
        if base == fam:
            break
        if base.startswith(fam):
            base = fam + "_single"
            break
    return base + ("@" + split if split else "")


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
        """Rows of the actionable tables, ranked by how far the player sits from typical pros.

        A row is a candidate when the player's n and the reference n both reach min_n and the
        95% CI of (player rate - reference rate) excludes zero. Candidates are ordered by `score`,
        the CI bound nearest zero, i.e. the smallest difference the data still supports.
        """
        parts = []
        for name, t in self.tables.items():
            if t.empty or not name.startswith(ACTIONABLE_FAMILIES):
                continue
            x = t[INSIGHT_COLUMNS].copy()
            x.insert(0, "analysis", name)
            x.insert(1, "family", family(name))
            parts.append(x)
        allx = pd.concat(parts, ignore_index=True)
        allx["candidate"] = allx.reliable & allx.ref_reliable & allx.delta_excludes_zero
        return allx.sort_values(["candidate", "score"], ascending=False).reset_index(drop=True)


def _with_reference(t: pd.DataFrame, ref: pd.DataFrame, s: AnalysisSettings, kind: str):
    out = compare_to_reference(t, ref, s.rates)
    out["ref_kind"] = kind
    return out


def _own_baseline_ref(t: pd.DataFrame, r: pd.DataFrame) -> pd.DataFrame:
    """Reference for symmetric win-rate splits (length, game, pressure, serving): the player's
    own overall rate. Across the population these splits are 50% by construction (every rally
    has one winner and one loser), so 'typical pros' show no effect to compare against."""
    return pd.DataFrame({"key": t.key, "n": len(r), "wins": int(r.player_won.sum())})


def analyse_player(
    df: pd.DataFrame,
    player: str,
    s: AnalysisSettings | None = None,
    with_population: bool = True,
) -> PlayerReport:
    s = s or AnalysisSettings()
    ps = player_strokes(df, player)
    if ps.empty:
        raise ValueError(f"no rallies found for {player!r}; run `tactics players` to list names")
    r = rally_frame(ps, s)
    base = float(r.player_won.mean())
    tables: dict[str, pd.DataFrame] = {}
    baselines: dict[str, float] = {}

    # -- symmetric win-rate splits: reference = own baseline
    for name, t in (
        ("length", win_rate_by_length(r, base, s)),
        ("game", win_rate_by_split(r, "game", base, s)),
        ("pressure", win_rate_by_split(r, "pressure", base, s)),
        ("serving", win_rate_by_split(r, "player_served", base, s)),
    ):
        tables[name] = _with_reference(t, _own_baseline_ref(t, r), s, "own baseline")
        baselines[name] = base

    # -- setups before the decisive stroke: reference = other players, same setup
    pop_r = population_rallies(df, player, s) if with_population else None
    for k in (2, 3):
        t = win_rate_by_last_sequence(r, k, base, s)
        if pop_r is not None:
            ref = win_rate_by_last_sequence(pop_r, k, float(pop_r.player_won.mean()), s)
            tables[f"last{k}"] = _with_reference(t, ref, s, "typical pros")
        else:
            tables[f"last{k}"] = _with_reference(t, t.head(0), s, "none")
        baselines[f"last{k}"] = base

    # -- danger conditions: reference = other players in the same role
    ps_pressure = stroke_pressure(ps, s)
    for hit_by_player, tag in ((True, "hit"), (False, "faced")):
        pop = population_strokes(df, player, hit_by_player) if with_population else None
        pop_pressure = stroke_pressure(pop, s) if pop is not None else None
        for split_name, mask, pmask in (
            ("", slice(None), slice(None)),
            ("@game3", ps.game == 3, (pop.game == 3) if pop is not None else None),
            ("@pressure", ps_pressure, pop_pressure),
        ):
            sub = ps[mask]
            if sub.empty:
                continue
            psub = pop[pmask] if pop is not None else None
            t, b = danger_conditions(sub, s, hit_by_player)
            ref = danger_conditions(psub, s, hit_by_player)[0] if psub is not None else t.head(0)
            tables[f"danger_{tag}{split_name}"] = _with_reference(t, ref, s, "typical pros")
            baselines[f"danger_{tag}{split_name}"] = b
            for factor in (s.shot_col, "coach_zone"):
                t, b = danger_by_single_factor(sub, s, hit_by_player, factor)
                ref = (
                    danger_by_single_factor(psub, s, hit_by_player, factor)[0]
                    if psub is not None
                    else t.head(0)
                )
                name = f"danger_{tag}_{factor}{split_name}"
                tables[name] = _with_reference(t, ref, s, "typical pros")
                baselines[name] = b

    # -- descriptive splits of the symmetric tables
    for split_name, mask in (("game3", r.game == 3), ("pressure", r.pressure)):
        sub = r[mask]
        if len(sub):
            b = float(sub.player_won.mean())
            t = win_rate_by_length(sub, b, s)
            tables[f"length@{split_name}"] = _with_reference(
                t, _own_baseline_ref(t, sub), s, "own baseline"
            )
            baselines[f"length@{split_name}"] = b

    return PlayerReport(player, r, ps, base, tables, baselines, endings(r, s.shot_col))


def coverage(df: pd.DataFrame) -> pd.DataFrame:
    """Matches, rallies and win rate per player, for `tactics players`."""
    d = _valid(df)
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
