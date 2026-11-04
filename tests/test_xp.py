"""xP feature frame, bookkeeping identities and a full small run on the synthetic table."""

import numpy as np
import pytest

from tactics import xp
from tactics.config import load_zone_config
from tactics.zones import annotate
from tests.synthetic import synthetic_strokes


@pytest.fixture(scope="module")
def cfg():
    return load_zone_config()


@pytest.fixture(scope="module")
def df(cfg):
    d = synthetic_strokes(rallies_per_game=50)
    # the synthetic table has no landing data; give annotate what it needs
    d["land_x"] = d.recv_x + np.random.default_rng(1).normal(0, 0.8, len(d))
    d["land_y"] = d.recv_y + np.random.default_rng(2).normal(0, 0.8, len(d))
    d["hit_x"], d["hit_y"] = d.hitter_x, d.hitter_y
    d["backhand"] = False
    d["aroundhead"] = False
    d["hit_height"] = 2.0
    d["lose_reason"] = None
    return annotate(d, cfg)


def test_feature_frame_is_leak_free_by_construction(df, cfg):
    bases, fallback = xp.receiver_bases(df)
    f = xp.feature_frame(df, cfg, bases, fallback)
    assert len(f) == len(df)
    assert (f.hit_depth > 0).all() and f.recv_from_base.notna().all()
    # pre features never include landing information
    assert not set(xp.PRE_CATS + xp.PRE_NUMS) & {
        "land_zone",
        "land_depth",
        "land_lat_fh",
        "recv_move",
        "move_dir",
        "body",
        "cross",
    }
    assert set(f.hit_band.unique()) <= {"front", "mid", "rear"}


def test_xp_added_telescopes_per_rally(df, cfg):
    bases, fallback = xp.receiver_bases(df)
    f = xp.feature_frame(df, cfg, bases, fallback)
    rng = np.random.default_rng(0)
    f["xp_pre"] = rng.uniform(0.2, 0.8, len(f))
    f["added"] = xp.xp_added(f, server_rate=0.5)
    # server's total + (-receiver's total) == v_last - v_0 for every rally
    for rid, g in f.groupby("rally_id"):
        g = g.sort_values("stroke_no")
        last = g.iloc[-1]
        v_last = last.xp_pre if last.hitter_is_server else 1 - last.xp_pre
        net = g[g.hitter_is_server].added.sum() - g[~g.hitter_is_server].added.sum()
        assert net == pytest.approx(v_last - 0.5, abs=1e-9), rid


def test_run_experiment_and_player_tables(df, cfg):
    res = xp.run_experiment(df, cfg, seed=0, holdout_ids={"syn:4"})
    assert res.counts["holdout_matches"] == 1 and res.counts["dev_matches"] == 4
    assert set(res.chosen) == {"pre", "post"}
    assert res.frame.xp_pre.between(0, 1).all()
    assert res.frame.loc[res.frame.is_last, "xp_post"].isna().all()
    assert 0 <= res.leaky_auc <= 1 and 0 <= res.leaky_auc_final <= 1
    t = res.table
    assert {"all strokes", "non-final strokes", "final strokes"} <= set(
        t[t.feature_set == "pre"]["slice"]
    )
    px = xp.player_xp(res, "X", min_n=10)
    assert px.n_rallies > 0 and "defensive" in set(px.by_shot.label)
    assert px.finishing.n.sum() <= px.n_rallies
    text = "\n".join(xp.section(px, "X", res, None))
    assert "Read this first" in text and "Finishing" in text
