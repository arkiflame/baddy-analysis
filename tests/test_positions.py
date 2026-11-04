"""Position maps on the synthetic table and on hand-built rallies."""

import numpy as np
import pandas as pd
import pytest

from tactics import positions
from tactics.analyses import AnalysisSettings
from tactics.config import load_zone_config
from tests.synthetic import synthetic_strokes


@pytest.fixture(scope="module")
def cfg():
    return load_zone_config()


@pytest.fixture(scope="module")
def df():
    return synthetic_strokes()


def test_two_rows_per_stroke_in_own_half_frame(df, cfg):
    pos = positions.all_positions(df, cfg)
    assert len(pos) == 2 * len(df)
    assert (pos.depth > 0).all()  # every position is on the player's own side
    near = pos[pos.half == "near"]
    far = pos[pos.half == "far"]
    assert np.allclose(near.lat_right, near.x - cfg.centre_x)
    assert np.allclose(far.lat_right, cfg.centre_x - far.x)
    hit = pos[(pos.role == "hit") & (pos.stroke_no == 2)]
    assert (hit.incoming == "short_service").all()  # stroke 2 answers the serve


def test_base_and_pull_on_a_fixed_rally(cfg):
    # one rally: X serves from the far half, Y answers; X's receive positions are fixed so the
    # base is known, and X's hit positions are chosen so the pull from base is 1 m then 2 m.
    net = cfg.net_y
    rows = []
    x_recv = (
        [(cfg.centre_x + 0.5, net - 3.0)] * 10
    )  # X on the far half, 3 m deep, 0.5 m LEFT of centre... in far half +x is the player's LEFT
    strokes = [
        ("X", "short_service", (cfg.centre_x + 0.5, net - 1.5)),
        ("Y", "lob", (cfg.centre_x, net + 2.0)),
        ("X", "clear", (cfg.centre_x + 0.5, net - 4.0)),  # 1 m deeper than base
        ("Y", "drop", (cfg.centre_x, net + 2.0)),
        ("X", "net", (cfg.centre_x + 0.5, net - 1.0)),  # 2 m in front of base
        ("Y", "lob", (cfg.centre_x, net + 2.0)),
    ]
    for i, (h, shot, (hx, hy)) in enumerate(strokes):
        r = "Y" if h == "X" else "X"
        rx, ry = x_recv[i] if r == "X" else (cfg.centre_x, net + 2.0)
        rows.append(
            dict(
                match_id="m",
                game=1,
                rally_id="r1",
                stroke_no=i + 1,
                n_strokes=len(strokes),
                is_serve=i == 0,
                hitter=h,
                receiver=r,
                hitter_handed="right",
                receiver_handed="right",
                hitter_half="far" if h == "X" else "near",
                hitter_x=hx,
                hitter_y=hy,
                recv_x=rx,
                recv_y=ry,
                shot_coarse=shot,
                rally_winner="Y",
                score_before_hitter=0,
                score_before_receiver=0,
                annotated=True,
            )
        )
    df = pd.DataFrame(rows)
    pos = positions.all_positions(df, cfg)
    bases = positions.base_positions(pos)
    bx = bases.set_index("player").loc["X"]
    assert bx.base_depth == pytest.approx(3.0)
    assert bx.base_lat_right == pytest.approx(-0.5)  # far half: +x is the player's left
    pulled = positions.pull_from_base(pos, bases)
    px = pulled[pulled.player == "X"].sort_values("stroke_no")
    assert list(px.incoming) == ["lob", "drop"]
    assert list(px.pull.round(6)) == [1.0, 2.0]
    dist = positions.distance_per_rally(pos).set_index("player")
    # X hit at depths 1.5, 4.0, 1.0 (same lateral): 2.5 + 3.0 = 5.5 m lower bound
    assert dist.loc["X", "distance"] == pytest.approx(5.5)
    assert dist.loc["X", "own_hits"] == 3
    assert dist.loc["Y", "distance"] == pytest.approx(0.0)


def test_summary_and_figure(df, cfg, tmp_path):
    summary = positions.summarise(df, "X", cfg, AnalysisSettings())
    assert summary.base.n > 0 and len(summary.ref_base) == 3
    assert "all shots" in set(summary.pull.label)
    assert set(summary.distance.label) >= {"all rallies", "game 1", "game 2", "at 18+"}
    path = positions.position_heatmap(summary, cfg, tmp_path / "p.png")
    assert path.exists() and path.stat().st_size > 1000
    text = "\n".join(positions.section(summary, "X", "p.png", AnalysisSettings()))
    assert "position maps, not footwork paths" in text and "lower bound" in text
    assert "footwork path" not in text.replace("not footwork paths", "")
