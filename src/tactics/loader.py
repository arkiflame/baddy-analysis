"""Read ShuttleSet / ShuttleSet22 CSVs into the domain model and a flat stroke table.

What the loader fixes on the way in (all verified in docs/DATASET.md):
* pixels -> court metres via the per-match homography
* which half of the court the hitter stands in (players switch sides between games and at 11
  in game 3), from the hitter's own position with rally-level fallbacks
* score BEFORE each rally (the CSV stores the score after the point)
* placeholder rallies (one "unknown" stroke, no outcome): kept so scores stay right, flagged
  so analyses can exclude them
* ShuttleSet22 re-ships 8 ShuttleSet matches; duplicates are dropped by video name
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

from tactics import court, shots
from tactics.config import DATA_ROOT, PlayerConfig, load_player_config
from tactics.model import Game, Match, Rally, Stroke

DATASETS = ("ShuttleSet", "ShuttleSet22")
_PIXEL_COLS = {
    "hit": ("hit_x", "hit_y"),
    "landing": ("landing_x", "landing_y"),
    "hitter": ("player_location_x", "player_location_y"),
    "receiver": ("opponent_location_x", "opponent_location_y"),
}


def load_matches(
    root: Path = DATA_ROOT, datasets: tuple[str, ...] = DATASETS, dedupe: bool = True
) -> list[Match]:
    matches: list[Match] = []
    seen_videos: set[str] = set()
    for ds in datasets:
        meta = pd.read_csv(root / ds / "set" / "match.csv")
        homo = pd.read_csv(root / ds / "set" / "homography.csv").set_index("id")
        for _, m in meta.iterrows():
            if dedupe and m.video in seen_videos:
                continue
            seen_videos.add(m.video)
            h = court.parse_homography(homo.loc[m.id, "homography_matrix"])
            match = Match(
                id=f"{ds}:{int(m.id)}",
                dataset=ds,
                video=m.video,
                tournament=str(m.tournament).strip(),
                round=str(m["round"]).strip(),
                date=_iso_date(m),
                player_a=_clean_name(m.winner),
                player_b=_clean_name(m.loser),
                homography=h,
            )
            folder = root / ds / "set" / m.video
            for n in (1, 2, 3):
                f = folder / f"set{n}.csv"
                if f.exists():
                    match.games.append(load_game(f, n, match))
            matches.append(match)
    return matches


def load_game(path: Path, number: int, match: Match) -> Game:
    """Parse one set{n}.csv into a Game. Public so tests can feed synthetic files."""
    df = pd.read_csv(path).reset_index(drop=True)
    return game_from_frame(df, number, match)


def game_from_frame(df: pd.DataFrame, number: int, match: Match) -> Game:
    # --- pixels -> metres, one projection per point type -------------------------------
    metres: dict[str, np.ndarray] = {}
    for key, (cx, cy) in _PIXEL_COLS.items():
        metres[key] = court.pixels_to_metres(match.homography, df[[cx, cy]].to_numpy(dtype=float))

    df = df.copy()
    df["_half"] = infer_hitter_half(df, metres["hitter"][:, 1], metres["receiver"][:, 1])

    names = {"A": match.player_a, "B": match.player_b}
    rallies: list[Rally] = []
    prev_after = (0, 0)
    for rally_no, g in df.groupby("rally", sort=False):
        strokes = [_stroke(g.loc[i], metres, i, names) for i in g.index]
        last = g.iloc[-1]
        after = (int(last.roundscore_A), int(last.roundscore_B))
        winner_lbl = last.getpoint_player if isinstance(last.getpoint_player, str) else None
        if winner_lbl is None:  # not annotated: infer from the scoreboard movement
            da, db = after[0] - prev_after[0], after[1] - prev_after[1]
            winner_lbl = "A" if (da, db) == (1, 0) else "B" if (da, db) == (0, 1) else None
        if winner_lbl == "A":
            before = (after[0] - 1, after[1])
        elif winner_lbl == "B":
            before = (after[0], after[1] - 1)
        else:
            before = after
        lose_zh = last.lose_reason if isinstance(last.lose_reason, str) else None
        types = [s.shot for s in strokes]
        rallies.append(
            Rally(
                number=int(rally_no),
                strokes=strokes,
                winner=names.get(winner_lbl),
                lose_reason=shots.LOSE_REASON_ZH_TO_EN.get(lose_zh) if lose_zh else None,
                score_before=before,
                score_after=after,
                # placeholder rows: every stroke unknown and no annotated outcome
                annotated=not (all(t == shots.UNKNOWN for t in types) and not isinstance(last.getpoint_player, str)),
                has_unknown=shots.UNKNOWN in types,
                flawed=any(s.flaw for s in strokes),
                score_gap=before != prev_after,
            )
        )
        prev_after = after
    _fill_half_from_neighbours(rallies, number, names)
    return Game(number=number, rallies=rallies)


def _side_period(rally: Rally, game_number: int) -> int:
    """Players change ends between games and, in game 3, when the leader first reaches 11."""
    return 1 if game_number == 3 and max(rally.score_before) >= 11 else 0


def _fill_half_from_neighbours(rallies: list[Rally], game_number: int, names: dict[str, str]) -> None:
    """Rallies with no position data at all borrow the half from the nearest decided rally in
    the same game and the same side period (so the 11-point change of ends is respected)."""
    decided: dict[int, dict[str, str]] = {}
    for i, r in enumerate(rallies):
        halves = {s.hitter: s.hitter_half for s in r.strokes if s.hitter_half}
        if halves:
            decided[i] = halves
    for i, r in enumerate(rallies):
        if i in decided:
            continue
        period = _side_period(r, game_number)
        candidates = [j for j in decided if _side_period(rallies[j], game_number) == period]
        if not candidates:
            continue
        j = min(candidates, key=lambda j: (abs(j - i), j > i))  # nearest, prefer earlier
        ref = decided[j]
        for s in r.strokes:
            if s.hitter in ref:
                s.hitter_half = ref[s.hitter]
            else:  # only the opponent is known in the reference rally: take the other half
                other = next(iter(ref.values()))
                s.hitter_half = _flip(other)


def infer_hitter_half(df: pd.DataFrame, hitter_y: np.ndarray, recv_y: np.ndarray) -> pd.Series:
    """Which half ("far"/"near") the hitter of each stroke stands in, decided per rally.

    Each stroke casts votes: the hitter's own feet position (near the net a player's feet can
    be annotated a few centimetres past the line, so single strokes are noisy) and the
    receiver's position, flipped. Votes are summed per (rally, player); if one player's
    votes are missing the opponent's result is flipped. The two players always end up on
    opposite halves.
    """
    # vote > 0 means "near" (y beyond the net), < 0 means "far"
    own_vote = np.where(np.isnan(hitter_y), 0.0, np.sign(hitter_y - court.NET_Y_M))
    opp_vote = np.where(np.isnan(recv_y), 0.0, -np.sign(recv_y - court.NET_Y_M))
    votes = pd.DataFrame({"rally": df["rally"].to_numpy(), "player": df["player"].to_numpy(),
                          "v": own_vote + opp_vote})
    per_player = votes.groupby(["rally", "player"])["v"].sum()
    # net vote for "player A is near": A's votes minus B's votes within the rally
    signed = per_player.reset_index()
    signed["v"] = np.where(signed["player"] == "A", signed["v"], -signed["v"])
    a_near = signed.groupby("rally")["v"].sum()
    half_a = a_near.map(lambda v: "near" if v > 0 else "far" if v < 0 else None)
    half = pd.Series(
        [half_a.get(r) if p == "A" else _flip(half_a.get(r)) for r, p in zip(df["rally"], df["player"], strict=True)],
        index=df.index, dtype=object,
    )
    return half


def _flip(h):
    return {"far": "near", "near": "far"}.get(h)


def _stroke(row: pd.Series, metres: dict[str, np.ndarray], i: int, names: dict[str, str]) -> Stroke:
    hitter_lbl = row.player
    receiver_lbl = "B" if hitter_lbl == "A" else "A"
    return Stroke(
        number=int(row.ball_round),
        hitter=names[hitter_lbl],
        receiver=names[receiver_lbl],
        shot=shots.to_english(row.type),
        shot_zh=row.type,
        backhand=_flag(row.backhand),
        aroundhead=_flag(row.aroundhead),
        hit_height=_int_or_none(row.hit_height),
        landing_height=_int_or_none(row.landing_height),
        hit=_point(metres["hit"][i]),
        landing=_point(metres["landing"][i]),
        hitter_pos=_point(metres["hitter"][i]),
        receiver_pos=_point(metres["receiver"][i]),
        hitter_half=row._half if isinstance(row._half, str) else None,
        flaw=_flag(row.flaw),
        time_s=_time_to_seconds(row.time),
    )


# ---------------------------------------------------------------------------------------
# Flat table
# ---------------------------------------------------------------------------------------

def strokes_frame(matches: list[Match], players: PlayerConfig | None = None) -> pd.DataFrame:
    """One row per stroke with match/game/rally context attached. The analyses work on this."""
    players = players or load_player_config()
    rows: list[dict] = []
    for m in matches:
        for g in m.games:
            for r in g.rallies:
                n = r.length
                for s in r.strokes:
                    a_is_hitter = s.hitter == m.player_a
                    sb_h, sb_r = r.score_before if a_is_hitter else r.score_before[::-1]
                    rows.append({
                        "dataset": m.dataset, "match_id": m.id, "video": m.video,
                        "tournament": m.tournament, "date": m.date,
                        "game": g.number, "rally_no": r.number,
                        "rally_id": f"{m.id}/g{g.number}/r{r.number}",
                        "stroke_no": s.number, "n_strokes": n, "strokes_to_end": n - s.number,
                        "is_serve": s.number == 1, "is_last": s.number == n,
                        "hitter": s.hitter, "receiver": s.receiver,
                        "hitter_handed": players.handed(s.hitter),
                        "receiver_handed": players.handed(s.receiver),
                        "shot": s.shot, "shot_coarse": shots.COARSE[s.shot],
                        "backhand": s.backhand, "aroundhead": s.aroundhead,
                        "hit_height": s.hit_height, "landing_height": s.landing_height,
                        "hit_x": _x(s.hit), "hit_y": _y(s.hit),
                        "land_x": _x(s.landing), "land_y": _y(s.landing),
                        "hitter_x": _x(s.hitter_pos), "hitter_y": _y(s.hitter_pos),
                        "recv_x": _x(s.receiver_pos), "recv_y": _y(s.receiver_pos),
                        "hitter_half": s.hitter_half,
                        "rally_winner": r.winner,
                        "hitter_won": (r.winner == s.hitter) if r.winner else None,
                        "lose_reason": r.lose_reason,
                        "score_before_hitter": sb_h, "score_before_receiver": sb_r,
                        "server": r.server,
                        "annotated": r.annotated, "rally_has_unknown": r.has_unknown,
                        "rally_flawed": r.flawed, "score_gap": r.score_gap,
                        "time_s": s.time_s,
                    })
    df = pd.DataFrame(rows)
    for c in ("shot", "shot_coarse", "hitter", "receiver", "lose_reason", "hitter_half", "dataset"):
        df[c] = df[c].astype("category")
    return df


def load_strokes(root: Path = DATA_ROOT, **kw) -> pd.DataFrame:
    return strokes_frame(load_matches(root, **kw))


# ---------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------

def _fill_majority(s: pd.Series) -> pd.Series:
    vals = s.dropna()
    if vals.empty or s.notna().all():
        return s
    return s.fillna(vals.mode().iloc[0])


def _flag(v) -> bool:
    return not (v is None or (isinstance(v, float) and math.isnan(v))) and float(v) == 1.0


def _int_or_none(v) -> int | None:
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else int(v)


def _point(xy: np.ndarray) -> tuple[float, float] | None:
    return None if np.isnan(xy).any() else (float(xy[0]), float(xy[1]))


def _x(p):
    return None if p is None else p[0]


def _y(p):
    return None if p is None else p[1]


def _time_to_seconds(t) -> float | None:
    if not isinstance(t, str):
        return None
    try:
        h, m, s = t.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)
    except ValueError:
        return None


def _clean_name(n: str) -> str:
    return " ".join(str(n).split())


def _iso_date(m: pd.Series) -> str:
    try:
        return f"{int(m.year):04d}-{int(m.month):02d}-{int(m.day):02d}"
    except (ValueError, TypeError):
        return ""
