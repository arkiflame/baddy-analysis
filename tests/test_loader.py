"""Smoke tests on the real dataset; skipped when data/raw is absent (e.g. in CI)."""

import pytest

from tactics.config import DATA_ROOT
from tactics.loader import load_matches, strokes_frame

pytestmark = pytest.mark.skipif(
    not (DATA_ROOT / "ShuttleSet").exists(), reason="dataset not downloaded"
)


@pytest.fixture(scope="module")
def matches():
    return load_matches()


@pytest.fixture(scope="module")
def df(matches):
    return strokes_frame(matches)


def test_duplicates_removed(matches):
    videos = [m.video for m in matches]
    assert len(videos) == len(set(videos)) == 94


def test_every_rally_has_score_and_winner(matches):
    rallies = [r for m in matches for r in m.rallies()]
    assert all(r.winner is not None for r in rallies if r.annotated)
    assert all(sum(r.score_after) - sum(r.score_before) == 1 for r in rallies if r.winner)


def test_score_before_mostly_consistent_with_previous_rally(matches):
    rallies = [r for m in matches for r in m.rallies()]
    assert sum(r.score_gap for r in rallies) / len(rallies) < 0.02


def test_hitter_half_known_for_almost_all_strokes(df):
    assert df.hitter_half.notna().mean() > 0.99


def test_players_never_change_half_within_a_rally(df):
    n_halves = (
        df.dropna(subset=["hitter_half"])
        .groupby(["rally_id", "hitter"], observed=True)
        .hitter_half.nunique()
    )
    assert (n_halves == 1).all()


def test_opponents_are_on_opposite_halves(df):
    d = df.dropna(subset=["hitter_half"])
    per_rally = d.groupby("rally_id", observed=True).agg(
        players=("hitter", "nunique"), halves=("hitter_half", "nunique")
    )
    two_player = per_rally[per_rally.players == 2]
    assert (two_player.halves == 2).all()


def test_landing_points_inside_or_near_court(df):
    d = df.dropna(subset=["land_x"])
    inside = d.land_x.between(-1, 7.1) & d.land_y.between(-1, 14.4)
    assert inside.mean() > 0.99
