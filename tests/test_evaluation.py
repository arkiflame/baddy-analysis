"""Replication schemes on the synthetic table: verdict rule and leave-one-out pooling."""

import pytest

from tactics import evaluation
from tactics.analyses import AnalysisSettings
from tests.synthetic import synthetic_strokes


def test_verdict_rule():
    # same direction and the Newcombe interval excludes zero -> REPLICATES
    v = evaluation.verdict(+1, 40, 100, 200, 1000, min_test_n=10)
    assert v["verdict"] == "REPLICATES" and v["test_delta"] == pytest.approx(0.2)
    # same direction, interval includes zero -> SAME DIRECTION
    assert evaluation.verdict(+1, 12, 50, 200, 1000, 10)["verdict"] == "SAME DIRECTION"
    # opposite direction -> FAILS
    assert evaluation.verdict(+1, 5, 100, 200, 1000, 10)["verdict"] == "FAILS"
    # too few -> UNTESTABLE
    assert evaluation.verdict(+1, 4, 5, 200, 1000, 10)["verdict"] == "UNTESTABLE"


def test_leave_one_out_pools_only_selected_folds():
    df = synthetic_strokes()
    s = AnalysisSettings()
    res = evaluation.leave_one_out(df, "X", s, k=5, by="match")
    assert res.scheme == "lomo" and res.folds == 2  # X plays two synthetic matches
    t = res.table
    planted = t[t.key == "faced push_rush -> rear_bh"].iloc[0]
    assert planted.selected_folds == 2 and planted.verdict == "REPLICATES"
    assert planted.test_n > 0 and planted.test_n <= planted.dev_n
    res_o = evaluation.leave_one_out(df, "X", s, k=5, by="opponent")
    assert res_o.scheme == "looo" and res_o.folds == 2
    text = evaluation.result_markdown(res_o)
    assert "selected in" in text and "Verdicts:" in text
    summary = evaluation.summary_table([res, res_o])
    assert list(summary.scheme) == ["lomo", "looo"]


def test_selection_frequency_counts_every_fold():
    df = synthetic_strokes()
    freq = evaluation.selection_frequency(df, "X", AnalysisSettings(), k=5)
    assert list(freq.columns) == ["analysis", "key", "selected_folds", "folds"]
    assert (freq.folds == 2).all() and freq.selected_folds.between(1, 2).all()
    planted = freq[freq.key == "faced push_rush -> rear_bh"]
    assert len(planted) == 1 and int(planted.selected_folds.iloc[0]) == 2
