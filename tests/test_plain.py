"""Plain-language wording (D30): frequencies, court areas, headlines and evidence sentences
contain no statistics vocabulary and no zone codes, and say the same thing as the numbers."""

import re

import pandas as pd
import pytest

from tactics import plain
from tactics.analyses import AnalysisSettings, analyse_player
from tactics.report import top_insights
from tests.synthetic import synthetic_strokes

BANNED = re.compile(
    r"\b(CI|confidence interval|n=|entropy|bits?|AUC|holdout|leave-one|fold|baseline|xP|"
    r"receiver-relative|homography|Wilson|Newcombe|typical pro)\b",
    re.IGNORECASE,
)
ZONE_CODE = re.compile(r"\b(front|mid|rear)_(fh|bh)\b|\bfh\b|\bbh\b")


def _row(analysis, key, delta, rate=0.3, ref_rate=0.2, **extra):
    base = {
        "analysis": analysis,
        "key": key,
        "delta": delta,
        "rate": rate,
        "ref_rate": ref_rate,
        "ref_n": 500,
        "n": 80,
        "ci_lo": rate - 0.05,
        "ci_hi": rate + 0.05,
        "delta_lo": delta - 0.05 if delta > 0 else delta - 0.05,
        "delta_hi": delta + 0.05,
        "selected_folds": 15,
        "folds": 20,
        "tentative": False,
    }
    base.update(extra)
    return pd.Series(base)


def test_frequencies_read_like_speech():
    assert plain.one_in(0.0733) == "about 1 time in 14"
    assert plain.one_in(0.2) == "about 1 time in 5"
    assert plain.one_in(0.345) == "about 35% of the time"
    assert plain.one_in(0) == "almost never"
    assert plain.freq_pair(0.07, 0.2) == ("about 1 time in 14", "about 1 time in 5")
    # one side at 30%+ switches both to whole percentages so they stay comparable
    assert plain.freq_pair(0.345, 0.231) == ("about 35% of the time", "about 23% of the time")
    assert plain.metres_words(2.21) == "2 m" and plain.metres_words(1.67) == "1½ m"
    assert plain.cm(-0.119) == "12 cm"


def test_areas_are_named_like_players_name_them():
    assert plain.area("rear_bh") == "back backhand corner"
    assert plain.at_area("body", "Axelsen's") == "straight at Axelsen's body"
    assert plain.at_area("mid_fh", "your") == "to the middle of your forehand side"
    assert plain.situation_words("clear -> rear_bh", "X's") == "a clear to X's back backhand corner"
    assert plain.situation_words("clear -> any", "X's") == "a clear, wherever it lands"
    assert (
        plain.reply_verb("smash -> mid_fh")
        == "smashes to the middle of the opponent's forehand side"
    )


def test_planted_pattern_gets_an_imperative_headline_and_plain_evidence():
    df = synthetic_strokes()
    s = AnalysisSettings()
    top = top_insights(analyse_player(df, "X", s))
    row = top[top.key == "faced push_rush -> rear_bh"].iloc[0]
    assert plain.headline(row, "X", s) == "Push or rush to X's back backhand corner."
    ev = plain.evidence(row, "X", s)
    assert ev.startswith(
        "When opponents push or rush to X's back backhand corner, X loses the point quickly"
    )
    assert "Most pros lose it" in ev
    for text in (plain.headline(row, "X", s), ev):
        assert not BANNED.search(text), text
        assert not ZONE_CODE.search(text), text
    assert not any(ch.isdigit() for ch in plain.headline(row, "X", s))


@pytest.mark.parametrize(
    "analysis,key,delta,expected",
    [
        (
            "danger_faced",
            "faced net -> front_fh",
            -0.07,
            "Don't rely on net shots to X's front forehand corner.",
        ),
        ("danger_faced_coach_zone", "faced coach_zone body", -0.13, "Don't attack X's body."),
        ("danger_faced_coach_zone", "faced coach_zone body", 0.1, "Hit straight at X's body."),
        ("danger_faced_shot_coarse", "faced shot_coarse clear", 0.1, "Clear more against X."),
        (
            "danger_faced_shot_coarse@game3",
            "faced shot_coarse clear",
            0.1,
            "In a deciding game, clear more against X.",
        ),
        (
            "danger_hit",
            "hit drop -> front_bh",
            0.1,
            "Punish X's drops to your front backhand corner.",
        ),
        (
            "danger_hit_coach_zone",
            "hit coach_zone mid_fh",
            -0.04,
            "Be ready for anything X plays to the middle of your forehand side.",
        ),
        (
            "danger_hit_shot_coarse@pressure",
            "hit shot_coarse lob",
            -0.04,
            "Late in a game, be ready for X's lobs.",
        ),
    ],
)
def test_headline_templates(analysis, key, delta, expected):
    s = AnalysisSettings()
    row = _row(analysis, key, delta)
    assert plain.headline(row, "X", s) == expected
    ev = plain.evidence(row, "X", s)
    assert "loses the point quickly" in ev and not BANNED.search(ev) and not ZONE_CODE.search(ev)
    assert ev[0].isupper() and ev.endswith(".")


def test_flags_and_held_up_are_plain():
    s = AnalysisSettings()
    row = _row("danger_faced", "faced net -> front_fh", 0.1)
    assert plain.flags(row, "X") == []
    assert plain.held_up(row, "X") == (
        "It held up in 15 of 20 re-checks, each one leaving out a different match of X's."
    )
    weak = _row("danger_faced", "faced net -> front_fh", 0.1, tentative=True, selected_folds=4)
    weak["delta_lo"] = 0.002
    assert plain.flags(weak, "X") == [
        "Too close to call.",
        "Early sign: not enough rallies to be sure.",
        "Only showed up in some of X's matches, so treat it as a hunch.",
    ]
    assert plain.held_up(_row("danger_faced", "faced net -> front_fh", 0.1, folds=0), "X") is None
    assert s.within == 2  # the page defines "quickly" as within two shots


def test_habit_predictability_and_opening_sentences():
    habit = pd.Series(
        {"situation": "clear -> rear_bh", "reply": "smash", "rate": 0.754, "ref_rate": 0.375}
    )
    assert plain.habit_sentence(habit, "X") == (
        "After a clear to X's back backhand corner, X smashes about 75% of the time. "
        "Most pros do it about 38% of the time."
    )
    pred = pd.Series(
        {
            "situation": "clear -> rear_bh",
            "entropy_bits": 2.18,
            "ref_entropy_bits": 3.11,
            "more_predictable": True,
            "less_predictable": False,
            "top_reply": "smash -> mid_fh",
            "top_share": 0.467,
        }
    )
    txt = plain.predictability_sentence(pred, "X")
    assert txt.startswith(
        "Easy to read: after a clear to X's back backhand corner, X usually plays one of about 5 shots."
    )
    assert "Most pros mix between about 9." in txt and "(47%)" in txt
    assert plain.effective(2.18) == 5 and plain.effective(3.11) == 9
    play = pd.Series(
        {
            "sequence": "P:short_service > O:net > P:lob",
            "rate": 0.323,
            "ref_rate": 0.191,
            "win_rate": 0.557,
            "ref_win_rate": 0.496,
        }
    )
    txt = plain.set_play_sentence(play, "X", serving=True)
    assert txt.startswith(
        "When X serves, about 32% of the time the rally starts like this: X serves short, "
        "the opponent plays a net shot, X lobs."
    )
    assert "X wins 56% of those rallies; most pros win 50%." in txt
    for t in (plain.habit_sentence(habit, "X"), plain.predictability_sentence(pred, "X"), txt):
        assert not BANNED.search(t) and not ZONE_CODE.search(t)


def test_movement_and_finishing_sentences():
    assert plain.base_sentence("X", 3.82, 0.28, 3.27, 4.40) == (
        "X usually waits about 4 m from the net, a little toward the forehand side. "
        "Most pros wait between 3½ m and 4½ m from the net."
    )
    pull = pd.Series(
        {"label": "net", "mean": 2.213, "ref_mean": 2.289, "delta": -0.0758, "signal": True}
    )
    assert (
        plain.mean_sentence(pull, "X", "pull")
        == "A net shot pulls X about 2 m from base, 8 cm less than most pros."
    )
    same = pd.Series(
        {"label": "defensive", "mean": 1.667, "ref_mean": 1.648, "delta": 0.019, "signal": False}
    )
    assert plain.mean_sentence(same, "X", "pull").endswith("from base, like most pros.")
    fin = pd.Series({"label": "smash", "delta": 0.104, "signal": True})
    assert plain.finishing_sentence(fin, "X") == (
        "When X's smashes end the rally, they are winners rather than mistakes more often than most pros'."
    )
    assert "coin flip" in plain.coin_flip_note()
