import pandas as pd
import pytest

from tactics import zones
from tactics.config import load_zone_config

NET = 6.7
CX = 3.05


def row(**kw):
    """A stroke hit by a near-half player toward a right-handed receiver on the far half."""
    base = dict(
        hitter_half="near",
        receiver_handed="right",
        is_last=False,
        lose_reason=None,
        hit_x=CX,
        hit_y=NET + 3.0,
        hitter_x=CX,
        hitter_y=NET + 3.0,
        recv_x=CX,
        recv_y=NET - 3.0,  # receiver 3 m from the net, centre
        land_x=CX,
        land_y=NET - 3.0,
    )
    base.update(kw)
    return base


@pytest.fixture(scope="module")
def cfg():
    return load_zone_config()


def annotate(*rows, cfg):
    return zones.annotate(pd.DataFrame(list(rows)), cfg)


def test_body_shot_takes_priority(cfg):
    out = annotate(row(land_x=CX + 0.2, land_y=NET - 3.1), cfg=cfg)
    assert out.coach_zone.iloc[0] == "body"
    assert out.body_side.iloc[0] == "bh"  # far-half right-hander: +x is their LEFT, i.e. backhand


def test_rear_forehand_corner_for_far_half_right_hander(cfg):
    # Far-half right-hander's forehand is at small x. Land 6 m deep, 2 m toward x=0.
    out = annotate(row(land_x=CX - 2.0, land_y=NET - 6.0), cfg=cfg)
    assert out.coach_zone.iloc[0] == "rear_fh"
    assert out.fine_depth.iloc[0] == "rear" and out.fine_lat.iloc[0] == "fh_sideline"


def test_left_handed_receiver_flips_side(cfg):
    out = annotate(row(receiver_handed="left", land_x=CX - 2.0, land_y=NET - 6.0), cfg=cfg)
    assert out.coach_zone.iloc[0] == "rear_bh"


def test_front_zone_and_movement_forward(cfg):
    out = annotate(row(land_x=CX, land_y=NET - 1.0), cfg=cfg)
    assert out.coach_zone.iloc[0] == "front_fh"  # exactly centre counts as forehand side
    assert out.move_dir.iloc[0] == "forward"


def test_geometric_out_wide(cfg):
    out = annotate(
        row(land_x=CX - 3.0, land_y=NET - 3.0), cfg=cfg
    )  # 3 m from centre > 2.59 singles half-width
    assert out.coach_zone.iloc[0] == "out"


def test_annotated_out_overrides_geometry_on_final_stroke(cfg):
    out = annotate(row(is_last=True, lose_reason="out", land_x=CX, land_y=NET - 5.5), cfg=cfg)
    assert out.coach_zone.iloc[0] == "out"


def test_cross_court_vs_straight(cfg):
    straight = annotate(row(hit_x=CX + 2, land_x=CX + 2), cfg=cfg)
    cross = annotate(row(hit_x=CX + 2, land_x=CX - 2), cfg=cfg)
    centre = annotate(row(hit_x=CX + 2, land_x=CX + 0.1), cfg=cfg)
    assert straight.cross.iloc[0] == "straight"
    assert cross.cross.iloc[0] == "cross"
    assert centre.cross.iloc[0] == "centre"


def test_unknown_half_yields_no_zone(cfg):
    out = annotate(row(hitter_half=None), cfg=cfg)
    assert out.coach_zone.isna().all()
