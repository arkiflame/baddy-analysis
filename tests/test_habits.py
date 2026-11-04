"""Habits, predictability and set plays on the synthetic table with planted regularities."""

import numpy as np
import pytest

from tactics import habits
from tactics.analyses import AnalysisSettings
from tests.synthetic import synthetic_strokes


@pytest.fixture(scope="module")
def df():
    return synthetic_strokes(rallies_per_game=80)


@pytest.fixture(scope="module")
def summary(df):
    return habits.summarise(df, "X", AnalysisSettings())


def test_entropy_values():
    assert habits.entropy_mm(np.array([100])) == pytest.approx(0.0)
    assert habits.entropy_mm(np.array([1000, 1000, 1000, 1000])) == pytest.approx(2.0, abs=0.01)
    # the Miller-Madow correction raises the plug-in value: (K-1)/(2n ln2) with K=2, n=10
    assert habits.entropy_mm(np.array([5, 5])) == pytest.approx(1.0 + 1 / (20 * np.log(2)))


def test_reply_frame_shapes(df):
    rf = habits.reply_frame(df)
    assert not rf.situation.str.contains("short_service").all()
    assert rf.situation_any.str.endswith("-> any").all()
    assert (rf.reply_shot != "unknown").all()


def test_planted_habit_is_found(summary):
    t = summary.tendencies_shot
    top = t[t.habit].iloc[0]
    assert top.situation == "smash -> any" and top.reply == "defensive"
    assert top.rate > 0.8 and top.ref_rate < 0.3 and top.delta_lo > 0.4


def test_planted_habit_lowers_entropy(summary):
    p = summary.predictability.set_index("situation")
    assert "smash -> any" in p.index
    row = p.loc["smash -> any"]
    assert row.more_predictable and row.entropy_bits < row.ref_lo
    assert row.top_reply.startswith("defensive")


def test_planted_opening_is_distinctive(summary):
    t = summary.set_plays[(3, True)]
    top = t.iloc[0]
    assert top.sequence == "P:short_service > O:net > P:lob"
    assert top.candidate and top.delta > 0.2
    assert 0 <= top.win_rate <= 1 and top.ref_win_rate == top.ref_win_rate  # not NaN
    receiving = summary.set_plays[(3, False)]
    assert receiving.sequence.str.startswith("O:short_service").all()


def test_section_renders(summary):
    text = "\n".join(habits.section(summary, "X", AnalysisSettings()))
    assert "smash -> any" in text and "defensive" in text
    assert "more predictable" in text and "distinctive" in text
