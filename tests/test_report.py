"""Wording and selection rules of the Markdown report, on the synthetic table."""

import re
from types import SimpleNamespace

import pytest

from tactics.analyses import AnalysisSettings, analyse_player
from tactics.report import (
    against_bullet,
    against_reference,
    coach_rows,
    coach_sections,
    describe,
    fix_bullet,
    possible_bullet,
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


def test_coach_sections_list_each_situation_once(rep):
    """D29: weaknesses are training priorities under 'should fix'; 'how to play against'
    only refers to them and lists the strengths (what not to do)."""
    s = AnalysisSettings()
    against, fix, possible = coach_sections(rep, s)
    assert any("Defending pushes and rushes to the rear backhand" in b for b in fix)
    assert not any("rear backhand" in b for b in against)
    assert all(r.delta < 0 for r in coach_rows(rep, s)[1])  # against = strengths only
    assert all(b.startswith("**") and "vs " in b for b in against + fix)
    ref = against_reference("X", len(fix))
    assert ref and "What X should fix" in ref and "loses more often" in ref
    assert against_reference("X", 0) is None
    # the two cards never share an insight
    weak, strong, maybe = coach_rows(rep, s)
    keys = lambda rows: {(r.analysis, r.key) for r in rows}  # noqa: E731
    assert not (keys(weak) & keys(strong)) and not (keys(weak) & keys(maybe))


def test_borderline_intervals_are_possible_not_confident(rep):
    """D29: 'with 95% confidence' needs the interval on the difference to exclude zero by at
    least half a point (so it still excludes zero once printed to whole points); a bound at
    zero, or closer than that, goes to the 'possible' list."""
    from tactics.report import borderline

    s = AnalysisSettings()
    row = top_insights(rep).iloc[0].copy()
    row["delta"], row["delta_hi"] = 0.08, 0.16
    for lo, expect in ((0.0, True), (0.004, True), (0.005, False), (0.02, False)):
        row["delta_lo"] = lo
        assert borderline(row) is expect, lo
    row["delta"], row["delta_lo"], row["delta_hi"] = -0.08, -0.16, -0.0
    assert borderline(row)
    # plant a borderline candidate in the report and check which list it lands in
    ins = rep.insights.copy()
    i = ins.index[ins.candidate][0]
    ins.loc[i, ["delta_lo", "candidate"]] = [0.0, True]
    planted = (ins.loc[i, "analysis"], ins.loc[i, "key"])
    rep2 = SimpleNamespace(player="X", insights=ins)  # coach_rows only reads .insights
    weak, strong, maybe = coach_rows(rep2, s)
    assert planted in {(r.analysis, r.key) for r in maybe}
    assert planted not in {(r.analysis, r.key) for r in weak + strong}
    text = possible_bullet(ins.loc[i], "X", s)
    assert text.startswith("**") and "touches zero" in text and "(0 to" in text
    row = ins.loc[i].copy()
    row["delta"], row["delta_lo"], row["delta_hi"] = -0.05, -0.1, -0.004
    assert "-0" not in possible_bullet(row, "X", s).split("(")[-1]  # never prints '-0'
    assert "to 0)" in possible_bullet(row, "X", s)


def test_takeaways_use_stable_non_tentative_insights_without_numbers(rep):
    from tactics.report import rank_with_stability, takeaway, takeaways

    s = AnalysisSettings()
    pool = top_insights(rep, k=10)
    stab = pool[["analysis", "key"]].copy()
    stab["selected_folds"] = 4
    stab["folds"] = 4
    top, _ = rank_with_stability(rep, stab, k=5)
    top["n"] = 200
    top["delta_lo"], top["delta_hi"] = top.delta - 0.05, top.delta + 0.05
    top["tentative"] = False  # the synthetic rows are small; pretend they are not tentative
    got = takeaways(top, "X", s)
    assert 1 <= len(got) <= 4 and got[0][1].key == top.iloc[0].key
    nodigits = lambda t: not re.search(r"\d", re.sub(r"^(In game \d|At \d+\+ in a game), ", "", t))  # noqa: E731
    for text, _ in got:
        assert text.endswith(".") and nodigits(text), text  # digits only in a split prefix
    assert got[0][0].startswith("Pushes and rushes to X's rear backhand win more points")
    # a tentative or unstable row is skipped
    top.loc[0, "tentative"] = True
    assert takeaways(top, "X", s)[0][1].key != top.iloc[0].key
    top["tentative"] = False
    top["selected_folds"] = 1
    assert takeaways(top, "X", s) == []
    # every shape reads without numbers or doubled spaces
    row = top.iloc[0].copy()
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
            text = takeaway(row, "X", s)
            assert nodigits(text) and "  " not in text and text.endswith("."), text
    assert takeaway(row, "X", s).startswith("In game 3, ")


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


def test_stability_ranking_and_tentative_flag(rep):
    from tactics.report import rank_with_stability, tentative, top_insights_table

    s = AnalysisSettings()
    pool = top_insights(rep, k=10)
    planted = pool.iloc[0]
    # the planted pattern is stable, everything else in the pool was selected in 1 of 4 folds
    stab = pool[["analysis", "key"]].copy()
    stab["selected_folds"] = [4] + [1] * (len(pool) - 1)
    stab["folds"] = 4
    top, unstable = rank_with_stability(rep, stab, k=5)
    assert len(top) == 1 and top.iloc[0].key == planted.key
    assert int(top.iloc[0].selected_folds) == 4
    assert len(unstable) == min(5, len(pool)) - 1  # the plain top-5 minus the stable one
    assert (unstable.selected_folds == 1).all()
    table = top_insights_table(top, "X", s)
    assert "4 of 4 folds" in table and "stable in" in table
    # without a stability table the plain ranking comes back
    plain, rest = rank_with_stability(rep, None, k=5)
    assert len(plain) == min(5, len(pool)) and rest.empty
    # tentative: wide interval on the difference or n under 60
    row = planted.copy()
    row["n"], row["delta_lo"], row["delta_hi"] = 100, 0.02, 0.10
    assert not tentative(row)
    row["n"] = 59
    assert tentative(row)
    row["n"], row["delta_hi"] = 100, 0.25
    assert tentative(row)
