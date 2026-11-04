import numpy as np

from tactics import court


def test_canvas_corners_map_to_court_metres():
    # Identity homography means pixels == canvas units; corners must land on the court outline.
    h = np.eye(3)
    pts = court.pixels_to_metres(h, np.array([[25, 150], [325, 150], [25, 810], [325, 810]]))
    np.testing.assert_allclose(pts, [[0, 0], [6.1, 0], [0, 13.4], [6.1, 13.4]], atol=1e-9)


def test_nan_passes_through():
    out = court.pixels_to_metres(np.eye(3), np.array([[np.nan, 1.0]]))
    assert np.isnan(out).all()


def test_depth_is_measured_into_each_half():
    assert court.depth_from_net(5.7, "far") == 1.0  # 1 m beyond the net on the far side
    assert court.depth_from_net(7.7, "near") == 1.0
    assert court.depth_from_net(7.7, "far") == -1.0  # still on the other side


def test_right_hand_depends_on_which_way_the_player_faces():
    # Near-half player faces the far end: +x is their right. Far-half player: -x is their right.
    assert court.lateral_right(4.05, "near") == 1.0
    assert court.lateral_right(4.05, "far") == -1.0


def test_left_hander_flips_forehand_side():
    assert court.lateral_forehand(4.05, "near", "right") == 1.0
    assert court.lateral_forehand(4.05, "near", "left") == -1.0
