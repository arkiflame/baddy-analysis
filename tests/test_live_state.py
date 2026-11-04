"""State features for the live experiment: shapes, movement identities, sequence building."""

import numpy as np
import pytest

from tactics import live_state
from tactics.config import load_zone_config
from tests.synthetic import synthetic_annotated


@pytest.fixture(scope="module")
def frame():
    return live_state.state_frame(synthetic_annotated(), load_zone_config())


def test_state_columns_present_and_finite_where_defined(frame):
    assert set(live_state.STATE_COLS) <= set(frame.columns)
    assert frame.hitter_from_base.notna().all()
    # a serve has no previous stroke, so the receiver's "move since last hit" is undefined
    assert frame.loc[frame.stroke_no == 1, "recv_moved_last"].isna().all()
    assert frame.loc[frame.stroke_no >= 2, "recv_moved_last"].notna().all()
    assert frame.loc[frame.stroke_no >= 4, "recv_moved_prev"].notna().all()
    assert frame.loc[frame.stroke_no >= 3, "hitter_moved_last"].notna().all()


def test_receiver_move_matches_positions(frame):
    g = frame[frame.rally_id == frame.rally_id.iloc[0]].sort_values("stroke_no")
    s1, s2 = g.iloc[0], g.iloc[1]
    expected = np.hypot(s2.recv_lat_fh - s1.hit_lat_fh, s2.recv_depth - s1.hit_depth)
    assert s2.recv_moved_last == pytest.approx(expected)


def test_sequences_and_scaler(frame):
    seqs = live_state.build_state_sequences(frame)
    assert all(s.state.shape == (s.seq.n, len(live_state.STATE_COLS)) for s in seqs)
    assert all(t.split("|")[2] != "out" for s in seqs for t in s.seq.tokens)
    scaler = live_state.Scaler(seqs)
    z = scaler(seqs[0].state)
    assert np.isfinite(z).all() and z.shape == seqs[0].state.shape
    items = live_state._prefix_items(seqs)
    assert all(1 <= k <= s.seq.n - 1 for s, k in items)
