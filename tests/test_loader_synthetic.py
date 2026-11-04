"""Loader logic on a hand-built dataset: score correction, placeholder rallies, de-dup,
side detection (including the change of ends at 11 in game 3), and the whole file layout.

Positions are written in court metres and converted to canvas units with an identity
homography, so the numbers in the tests read like court positions.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tactics import court
from tactics.loader import load_matches, strokes_frame
from tactics.model import Match

A, B = "Alice ALPHA", "Bob BETA"
COLUMNS = [
    "rally",
    "ball_round",
    "time",
    "frame_num",
    "roundscore_A",
    "roundscore_B",
    "player",
    "server",
    "type",
    "aroundhead",
    "backhand",
    "hit_height",
    "hit_area",
    "hit_x",
    "hit_y",
    "landing_height",
    "landing_area",
    "landing_x",
    "landing_y",
    "lose_reason",
    "win_reason",
    "getpoint_player",
    "flaw",
    "player_location_area",
    "player_location_x",
    "player_location_y",
    "opponent_location_area",
    "opponent_location_x",
    "opponent_location_y",
    "db",
]


def px(x_m: float, y_m: float) -> tuple[float, float]:
    """Court metres -> canvas units (identity homography makes canvas units == pixels)."""
    return (25 + x_m / court.M_PER_UNIT_XY[0], 150 + y_m / court.M_PER_UNIT_XY[1])


def stroke(
    rally,
    n,
    player,
    score,
    shot="放小球",
    hitter_pos=None,
    recv_pos=None,
    landing=(3.0, 3.0),
    getpoint=None,
    lose_reason=None,
):
    hp = px(*hitter_pos) if hitter_pos else (np.nan, np.nan)
    rp = px(*recv_pos) if recv_pos else (np.nan, np.nan)
    lp = px(*landing)
    return dict(
        zip(
            COLUMNS,
            [
                rally,
                n,
                "00:00:01",
                30,
                score[0],
                score[1],
                player,
                2 if n > 1 else 1,
                shot,
                np.nan,
                np.nan,
                2,
                np.nan,
                np.nan,
                np.nan,
                2,
                1,
                lp[0],
                lp[1],
                lose_reason,
                None,
                getpoint,
                np.nan,
                8,
                hp[0],
                hp[1],
                8,
                rp[0],
                rp[1],
                0,
            ],
            strict=True,
        )
    )


def write_dataset(
    root: Path, name: str, video: str, games: dict[int, list[dict]], match_id: int = 1
) -> None:
    d = root / name / "set" / video
    d.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "id": match_id,
                "video": video,
                "tournament": "T",
                "round": "F",
                "year": 2021,
                "month": 1,
                "day": 1,
                "set": len(games),
                "duration": 40,
                "winner": A,
                "loser": B,
                "downcourt": 0,
            }
        ]
    ).to_csv(root / name / "set" / "match.csv", index=False)
    pd.DataFrame(
        [
            {
                "id": match_id,
                "video": video,
                "homography_matrix": json.dumps(np.eye(3).tolist()),
                **{
                    k: 0
                    for k in [
                        "upleft_x",
                        "upright_x",
                        "downleft_x",
                        "downright_x",
                        "upleft_y",
                        "upright_y",
                        "downleft_y",
                        "downright_y",
                    ]
                },
            }
        ]
    ).to_csv(root / name / "set" / "homography.csv", index=False)
    for n, rows in games.items():
        pd.DataFrame(rows, columns=COLUMNS).to_csv(d / f"set{n}.csv", index=False)


NEAR_A, FAR_B = (3.0, 10.0), (3.0, 3.0)  # A on the near half, B on the far half


@pytest.fixture
def dataset(tmp_path: Path) -> Path:
    game1 = [
        # rally 1: A serves, B wins with a net shot error by A -> score 0-1
        stroke(1, 1, "A", (0, 1), "發短球", hitter_pos=NEAR_A, recv_pos=FAR_B),
        stroke(1, 2, "B", (0, 1), hitter_pos=FAR_B, recv_pos=NEAR_A),
        stroke(
            1, 3, "A", (0, 1), hitter_pos=NEAR_A, recv_pos=FAR_B, getpoint="B", lose_reason="掛網"
        ),
        # rally 2: placeholder (one unknown stroke, no outcome) while the score moves to 1-1
        stroke(2, 1, "B", (1, 1), "未知球種"),
        # rally 3: no positions at all; A wins -> 2-1 (half must come from neighbours)
        stroke(3, 1, "B", (2, 1), "發短球"),
        stroke(3, 2, "A", (2, 1), getpoint="A", lose_reason="對手落地致勝"),
        # rally 4: A's feet annotated 5 cm past the net on one stroke (noise); vote must still say near
        stroke(4, 1, "A", (3, 1), "發短球", hitter_pos=NEAR_A, recv_pos=FAR_B),
        stroke(4, 2, "B", (3, 1), hitter_pos=FAR_B, recv_pos=NEAR_A),
        stroke(4, 3, "A", (3, 1), hitter_pos=(3.0, 6.65), recv_pos=FAR_B),
        stroke(
            4, 4, "B", (3, 1), hitter_pos=FAR_B, recv_pos=NEAR_A, getpoint="A", lose_reason="出界"
        ),
    ]
    # game 3: A starts on the FAR half; ends change after the point that takes the leader to 11,
    # so a rally whose score BEFORE it has a player on 11+ is played at the other end.
    game3 = [
        stroke(
            1,
            1,
            "A",
            (1, 0),
            "發短球",
            hitter_pos=FAR_B,
            recv_pos=NEAR_A,
            getpoint="A",
            lose_reason="對手落地致勝",
        ),
        stroke(2, 1, "B", (3, 2), "發短球"),  # no positions, before 11 -> A far
        stroke(2, 2, "A", (3, 2), getpoint="A", lose_reason="對手落地致勝"),
        stroke(
            3,
            1,
            "A",
            (12, 5),
            "發短球",
            hitter_pos=NEAR_A,
            recv_pos=FAR_B,
            getpoint="A",
            lose_reason="對手落地致勝",
        ),
        stroke(4, 1, "A", (13, 5), "發短球"),  # no positions, after 11 -> A near
        stroke(4, 2, "B", (13, 5), getpoint="A", lose_reason="出界"),
    ]
    write_dataset(tmp_path, "ShuttleSet", "Alice_v_Bob", {1: game1, 3: game3})
    write_dataset(
        tmp_path, "ShuttleSet22", "Alice_v_Bob", {1: game1}, match_id=7
    )  # duplicate video
    return tmp_path


def test_duplicate_video_is_loaded_once(dataset):
    assert len(load_matches(dataset)) == 1
    assert len(load_matches(dataset, dedupe=False)) == 2


def test_score_before_and_winner(dataset):
    (m,) = load_matches(dataset)
    g1 = m.games[0]
    r1, r2, r3, r4 = g1.rallies
    assert (r1.score_before, r1.score_after, r1.winner) == ((0, 0), (0, 1), B)
    assert (
        not r2.annotated and r2.winner == A and r2.score_before == (0, 1)
    )  # inferred from the scoreboard
    assert r3.annotated and r3.winner == A and r3.score_before == (1, 1)
    assert r4.winner == A and r4.lose_reason == "out" and not r4.score_gap


def test_placeholder_rally_is_not_length_one(dataset):
    df = strokes_frame(load_matches(dataset))
    placeholder = df[~df.annotated]
    assert len(placeholder) == 1 and placeholder.shot.iloc[0] == "unknown"
    # genuine one-stroke rallies (service winners in game 3) stay annotated
    aces = df[df.annotated & (df.n_strokes == 1)]
    assert len(aces) == 2 and (aces.shot == "short_service").all()


def test_half_from_votes_fallbacks_and_noise(dataset):
    (m,) = load_matches(dataset)
    r1, _, r3, r4 = m.games[0].rallies
    assert {s.hitter: s.hitter_half for s in r1.strokes} == {A: "near", B: "far"}
    assert {s.hitter: s.hitter_half for s in r3.strokes} == {
        A: "near",
        B: "far",
    }  # borrowed from neighbours
    assert all(
        s.hitter_half == ("near" if s.hitter == A else "far") for s in r4.strokes
    )  # noise outvoted


def test_change_of_ends_at_eleven_in_game_three(dataset):
    (m,) = load_matches(dataset)
    g3 = m.games[1]
    assert g3.number == 3
    halves = [{s.hitter: s.hitter_half for s in r.strokes} for r in g3.rallies]
    assert halves[0][A] == "far"
    assert halves[1] == {B: "near", A: "far"}  # before 11: same ends as rally 1
    assert halves[2][A] == "near"
    assert halves[3] == {A: "near", B: "far"}  # after 11: borrowed from rally 3, not rally 1


def test_strokes_frame_is_keyed_by_name_not_label(dataset):
    df = strokes_frame(load_matches(dataset))
    assert set(df.hitter.astype(str)) == {A, B}
    assert "player" not in df.columns and "getpoint_player" not in df.columns


def test_frame_time_and_handedness_columns(dataset):
    df = strokes_frame(load_matches(dataset))
    assert df.time_s.iloc[0] == 1.0
    assert set(df.hitter_handed) == {"right"}  # unknown players default to right


def test_match_metadata(dataset):
    (m,) = load_matches(dataset)
    assert isinstance(m, Match) and m.players == (A, B) and m.date == "2021-01-01"
