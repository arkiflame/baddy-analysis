"""Population reference and ranking on a synthetic table with one planted pattern."""

import pytest

from tactics.analyses import (
    AnalysisSettings,
    analyse_player,
    family,
    population_strokes,
)
from tests.synthetic import synthetic_strokes


@pytest.fixture(scope="module")
def df():
    return synthetic_strokes()


@pytest.fixture(scope="module")
def rep(df):
    return analyse_player(df, "X", AnalysisSettings())


def test_population_excludes_the_player_only_in_their_role(df):
    faced = population_strokes(df, "X", hit_by_player=False)
    hit = population_strokes(df, "X", hit_by_player=True)
    assert not (faced.receiver.astype(str) == "X").any()
    assert not (hit.hitter.astype(str) == "X").any()
    # the player's opponents facing the player's shots stay in the "faced" reference ...
    assert (faced.hitter.astype(str) == "X").any()
    # ... and player_won is from the reference player's point of view
    row = faced[faced.hitter.astype(str) == "X"].iloc[0]
    assert row.player_won == (str(row.rally_winner) == str(row.receiver))


def test_planted_pattern_ranks_first_against_typical_pros(rep):
    ins = rep.insights
    top = ins[ins.candidate].iloc[0]
    assert top.key == "faced push_rush -> rear_bh"
    assert top.delta > 0 and top.delta_lo > 0
    assert top.ref_n >= 30 and top.n >= 30
    # the planted pattern is not in the reference, so the reference rate stays near base level
    assert top.ref_rate < top.rate / 2


def test_only_actionable_tables_are_ranked(rep):
    fams = set(rep.insights.family)
    allowed = set()
    for role in ("danger_hit", "danger_faced"):
        for split in ("", "@game3", "@pressure"):
            allowed |= {role + split, role + "_single" + split}
    assert fams <= allowed
    assert not rep.insights.analysis.str.startswith(("last", "length", "game", "serving")).any()


def test_symmetric_splits_use_own_baseline_and_setups_use_population(rep):
    length = rep.tables["length"]
    assert (length.ref_kind == "own baseline").all()
    assert length.ref_rate.iloc[0] == pytest.approx(rep.baseline_win)
    last2 = rep.tables["last2"]
    assert (last2.ref_kind == "typical pros").all()
    assert (last2.ref_n > 0).any()


def test_unknown_shot_type_never_appears(df):
    d = df.copy()
    d["shot_coarse"], d["shot"] = d.shot_coarse.astype(str), d.shot.astype(str)
    idx = d.index[~d.is_serve][:50]
    d.loc[idx, "shot_coarse"] = "unknown"
    d.loc[idx, "shot"] = "unknown"
    rep = analyse_player(d, "X")
    for name, t in rep.tables.items():
        if name.startswith("danger"):
            assert not t.key.str.contains("unknown").any(), name


def test_family_folds_single_factor_tables():
    assert family("danger_faced_coach_zone@game3") == "danger_faced_single@game3"
    assert family("danger_hit_shot_coarse") == "danger_hit_single"
    assert family("danger_hit") == "danger_hit"
    assert family("last2") == "last2"


def test_without_population_is_a_valid_fast_path(df):
    rep = analyse_player(df, "X", with_population=False)
    assert rep.tables["danger_faced"].ref_n.eq(0).all()
    assert not rep.insights.candidate.any()
