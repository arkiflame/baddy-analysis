"""Tests for the M2 tooling that does not need a display: label session logic and calibration."""

import numpy as np
import pytest

from tactics import court
from tactics.tools.label_video import SET_COLUMNS, LabelSession

cv2 = pytest.importorskip("cv2")


# ---- label session -------------------------------------------------------------------------

def test_hits_landing_and_score_follow_shuttleset_conventions():
    s = LabelSession(video="v.mp4", fps=30.0)
    s.click(10, 100, 200)
    s.add_hit(10)                    # A serves (default player A)
    s.set_shot("1")                  # short service
    s.click(25, 300, 220)
    s.add_hit(25)                    # B replies
    s.set_shot("4")                  # lob
    s.set_position("hitter", 310, 400)
    s.set_position("opponent", 90, 390)
    s.click(40, 120, 260)
    s.add_hit(40)                    # A
    s.set_shot("7")                  # smash
    s.end_rally("A")

    df = s.strokes_frame()
    assert list(df.columns) == SET_COLUMNS
    assert df.rally.tolist() == [1, 1, 1] and df.ball_round.tolist() == [1, 2, 3]
    assert df.player.tolist() == ["A", "B", "A"]
    assert df.type.tolist() == ["發短球", "挑球", "殺球"]
    # landing of stroke k == hit point of stroke k+1; the final stroke has no landing yet
    assert (df.landing_x.iloc[0], df.landing_y.iloc[0]) == (300, 220)
    assert (df.hit_x.iloc[1], df.hit_y.iloc[1]) == (300, 220)
    assert np.isnan(df.landing_x.iloc[2])
    # positions recorded for the lob
    assert (df.player_location_x.iloc[1], df.opponent_location_y.iloc[1]) == (310, 390)
    # score is written as the score AFTER the rally, like ShuttleSet; winner only on the last stroke
    assert df.roundscore_A.tolist() == [1, 1, 1] and df.roundscore_B.tolist() == [0, 0, 0]
    assert df.getpoint_player.isna().tolist()[:2] == [True, True] and df.getpoint_player.iloc[2] == "A"
    assert df.server.tolist() == [1, 2, 3]
    assert df.time.iloc[2] == "00:00:01"
    assert s.current_player == "A"   # the winner serves next


def test_second_rally_and_undo():
    s = LabelSession(video="v.mp4", fps=25.0)
    s.add_hit(1); s.set_shot("1"); s.end_rally("B")
    assert s.score == (0, 1) and s.current_player == "B"
    s.add_hit(50)                    # B serves rally 2
    s.add_hit(60)                    # A
    s.delete_last_hit()              # undo A's hit
    assert len(s.rallies) == 2 and len(s.rallies[1].hits) == 1 and s.current_player == "A"
    s.delete_last_hit()              # undo B's serve: the empty rally disappears
    assert len(s.rallies) == 1
    s.delete_last_hit()              # cannot undo into a finished rally
    assert len(s.rallies) == 1 and s.rallies[0].winner == "B"


def test_session_round_trips_through_json():
    s = LabelSession(video="v.mp4", fps=30.0)
    s.click(3, 1.5, 2.5)
    s.add_hit(3); s.set_shot("3"); s.set_position("hitter", 5, 6)
    s.end_rally("A")
    s.add_hit(9)
    t = LabelSession.from_json(s.to_json())
    assert t.shuttle == {3: (1.5, 2.5)} and t.score == (1, 0) and t.current_player == "B"
    assert t.rallies[0].hits[0].hitter_xy == (5, 6) and t.rallies[1].winner is None
    assert t.strokes_frame().equals(s.strokes_frame())
    assert t.shuttle_frame().columns.tolist() == ["Frame", "Visibility", "X", "Y"]


def test_loader_reads_labelled_output(tmp_path):
    """The exporter's columns and conventions are accepted by the ShuttleSet loader."""
    from tactics.loader import game_from_frame
    from tactics.model import Match

    s = LabelSession(video="v.mp4", fps=30.0)
    for f, (x, y) in enumerate([(100, 700), (500, 300), (120, 690)], start=1):
        s.click(f, x, y)
        s.add_hit(f)
        s.set_shot("3")
    s.end_rally("B")
    m = Match(id="own:1", dataset="own", video="v", tournament="club", round="-", date="",
              player_a="Me", player_b="You", homography=np.eye(3))
    g = game_from_frame(s.strokes_frame(), 1, m)
    assert g.rallies[0].winner == "You" and g.rallies[0].length == 3
    assert g.rallies[0].score_before == (0, 0) and g.rallies[0].score_after == (0, 1)


# ---- calibration ---------------------------------------------------------------------------

def test_homography_maps_clicked_corners_onto_the_canvas():
    from tactics.tools.calibrate_court import homography_from_corners, homography_row

    corners = np.array([[400, 300], [880, 300], [250, 700], [1030, 700]], dtype=float)  # a trapezoid
    h = homography_from_corners(corners)
    m = court.pixels_to_metres(h, corners)
    np.testing.assert_allclose(m, [[0, 0], [6.1, 0], [0, 13.4], [6.1, 13.4]], atol=1e-6)
    row = homography_row("clip", corners)
    assert row["upleft_x"] == 400 and row["downright_y"] == 700
    assert set(row) >= {"id", "video", "homography_matrix", "upleft_x", "downright_y"}
    # the stored matrix string parses back with the same loader code path
    np.testing.assert_allclose(court.parse_homography(row["homography_matrix"]), h)
