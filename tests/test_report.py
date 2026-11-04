"""Wording and selection rules of the Markdown report, on the synthetic table."""

import re

import pytest

from tactics.analyses import AnalysisSettings, analyse_player
from tactics.report import (
    against_bullet,
    coach_sections,
    describe,
    fix_bullet,
    shot_words,
    surname,
    top_insights,
    zone_words,
)
from tests.synthetic import synthetic_strokes


@pytest.fixture(scope="module")
def rep():
    return analyse_player(synthetic_strokes(), "X")


def test_shot_and_zone_words():
    assert shot_words("push_rush") == "pushes and rushes"
    assert shot_words("push_rush", "verb") == "push or rush"
    assert shot_words("smash", "verb3") == "smashes"
    assert shot_words("net", "verb") == "play a net shot"
    assert zone_words("rear_bh") == "rear backhand"
    assert zone_words("body") == "body"


def test_surnames():
    assert surname("Viktor AXELSEN") == "Axelsen"
    assert surname("An Se Young") == "An"
    assert surname("CHOU Tien Chen") == "Chou"


def test_top_insight_reads_naturally(rep):
    s = AnalysisSettings()
    top = top_insights(rep)
    assert not top.empty
    text = describe(top.iloc[0], "X", s)
    assert text.startswith("When opponents push or rush to X's rear backhand, X loses the point")
    assert "typical pros lose" in text and "difference +" in text
    assert "pushes/rushes" not in text and "smashs" not in text
    assert re.search(r"n=\d+, 95% CI \d+%-\d+%", text)


def test_coach_sections_put_the_weakness_in_both(rep):
    s = AnalysisSettings()
    against, fix = coach_sections(rep, s)
    assert any("Push or rush to X's rear backhand" in b for b in against)
    assert any("Defending pushes and rushes to the rear backhand" in b for b in fix)
    assert all(b.startswith("**") and "vs " in b for b in against + fix)


def test_bullets_for_every_shape(rep):
    s = AnalysisSettings()
    row = top_insights(rep).iloc[0].copy()
    for analysis, key in (
        ("danger_faced", "faced smash -> body"),
        ("danger_faced_shot_coarse", "faced shot_coarse smash"),
        ("danger_faced_coach_zone", "faced coach_zone mid_fh"),
        ("danger_hit", "hit lob -> rear_bh"),
        ("danger_hit_shot_coarse", "hit shot_coarse lob"),
        ("danger_hit_coach_zone@game3", "hit coach_zone front_fh"),
    ):
        row["analysis"], row["key"] = analysis, key
        for sign in (1, -1):
            row["delta"] = sign * 0.1
            text = against_bullet(row, "X", s) + fix_bullet(row, "X", s) + describe(row, "X", s)
            assert "'s anything" not in text and "  " not in text
    assert "In game 3" in describe(row, "X", s)
