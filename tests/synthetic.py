"""A small synthetic annotated stroke table for testing the analyses without the dataset.

Four players, five matches, random shots and zones, 50/50 outcomes, plus one PLANTED pattern:
whenever player X loses a rally, with probability `plant` the last opponent stroke among the
final two becomes a push/rush to X's rear backhand. Everything else is noise, so a correct
analysis must rank "faced push_rush -> rear_bh" first for X and nothing comparable for others.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

PLAYERS = ("X", "Y", "Z", "W")
MATCHES = (("X", "Y"), ("X", "Z"), ("Y", "Z"), ("Y", "W"), ("Z", "W"))
SHOTS = ("net", "lob", "smash", "clear", "drop", "push_rush", "defensive")
ZONES = ("front_fh", "front_bh", "mid_fh", "mid_bh", "rear_fh", "rear_bh", "body")
FINE_DEPTH = ("tight_net", "front", "mid", "rear")
FINE_LAT = ("bh_sideline", "bh_inner", "fh_inner", "fh_sideline")


def synthetic_strokes(
    rallies_per_game: int = 60, games: int = 2, plant: float = 0.6, seed: int = 0
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for mi, (a, b) in enumerate(MATCHES):
        match_id = f"syn:{mi}"
        for game in range(1, games + 1):
            score = {a: 0, b: 0}
            for rn in range(rallies_per_game):
                n = int(2 + rng.geometric(0.25))
                server = a if rng.random() < 0.5 else b
                other = b if server == a else a
                hitters = [server if i % 2 == 0 else other for i in range(n)]
                winner = a if rng.random() < 0.5 else b
                shots = ["short_service"] + list(rng.choice(SHOTS, n - 1))
                zones = list(rng.choice(ZONES, n))
                if "X" in (a, b) and winner != "X" and rng.random() < plant:
                    # last stroke hit by the opponent among the final two strokes
                    for i in (n - 1, n - 2):
                        if i >= 1 and hitters[i] != "X":
                            shots[i], zones[i] = "push_rush", "rear_bh"
                            break
                server_near = rng.random() < 0.5
                for i in range(n):
                    h = hitters[i]
                    r = other if h == server else server
                    h_near = server_near if h == server else not server_near
                    # feet positions: each player somewhere in their own half
                    hx, hd = rng.uniform(0.8, 5.3), rng.uniform(1.0, 6.2)
                    rx, rd = rng.uniform(0.8, 5.3), rng.uniform(2.5, 4.5)
                    rows.append(
                        {
                            "dataset": "syn",
                            "match_id": match_id,
                            "game": game,
                            "rally_no": rn + 1,
                            "rally_id": f"{match_id}:{game}:{rn + 1}",
                            "stroke_no": i + 1,
                            "n_strokes": n,
                            "strokes_to_end": n - 1 - i,
                            "is_serve": i == 0,
                            "is_last": i == n - 1,
                            "hitter": h,
                            "receiver": r,
                            "hitter_handed": "right",
                            "receiver_handed": "right",
                            "hitter_half": "near" if h_near else "far",
                            "hitter_x": hx,
                            "hitter_y": 6.7 + hd if h_near else 6.7 - hd,
                            "recv_x": rx,
                            "recv_y": 6.7 - rd if h_near else 6.7 + rd,
                            "shot": shots[i],
                            "shot_coarse": shots[i],
                            "coach_zone": zones[i],
                            "fine_depth": rng.choice(FINE_DEPTH),
                            "fine_lat": rng.choice(FINE_LAT),
                            "rally_winner": winner,
                            "hitter_won": winner == h,
                            "lose_reason": None,
                            "score_before_hitter": score[h],
                            "score_before_receiver": score[r],
                            "server": 1 if i == 0 else 2,
                            "annotated": True,
                            "rally_has_unknown": False,
                            "rally_flawed": False,
                        }
                    )
                score[winner] += 1
    df = pd.DataFrame(rows)
    for c in ("hitter", "receiver", "rally_winner", "shot", "shot_coarse", "coach_zone"):
        df[c] = df[c].astype("category")
    return df
