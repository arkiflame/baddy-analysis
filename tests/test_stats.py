import numpy as np
import pandas as pd
import pytest

from tactics import stats


def test_wilson_matches_known_values():
    # 0/10 and 10/10 are the classic cases where a normal interval collapses to zero width.
    lo, hi = stats.wilson_ci(0, 10)
    assert lo == pytest.approx(0.0, abs=1e-12) and hi == pytest.approx(0.2775, abs=1e-3)
    lo, hi = stats.wilson_ci(10, 10)
    assert lo == pytest.approx(0.7225, abs=1e-3) and hi == pytest.approx(1.0, abs=1e-12)
    lo, hi = stats.wilson_ci(50, 100)
    assert lo == pytest.approx(0.4038, abs=1e-3) and hi == pytest.approx(0.5962, abs=1e-3)


def test_wilson_handles_zero_n():
    lo, hi = stats.wilson_ci(0, 0)
    assert np.isnan(lo) and np.isnan(hi)


def test_shrinkage_pulls_small_samples_harder():
    small = stats.shrink(5, 6, baseline=0.5, prior_strength=20)  # raw 83%
    large = stats.shrink(50, 60, baseline=0.5, prior_strength=20)  # raw 83%
    assert small == pytest.approx(15 / 26)
    assert large == pytest.approx(60 / 80)
    assert small < large


def test_rate_table_flags_rare_and_significant_groups():
    df = pd.DataFrame(
        {
            "zone": ["a"] * 100 + ["b"] * 5,
            "won": [1] * 70 + [0] * 30 + [1] * 5,
        }
    )
    t = stats.rate_table(df, "zone", "won", baseline=0.5, settings=stats.RateSettings(min_n=30))
    a = t.set_index("zone").loc["a"]
    b = t.set_index("zone").loc["b"]
    assert a.reliable and a.ci_excludes_baseline and a.rate == pytest.approx(0.7)
    assert not b.reliable and b.rate == 1.0 and b.shrunk < 0.8
    assert t.zone.iloc[0] == "a"  # reliable rows rank first


def test_two_proportion_z():
    assert stats.two_proportion_z(50, 100, 50, 100) == pytest.approx(1.0)
    assert stats.two_proportion_z(80, 100, 50, 100) < 0.001


def test_newcombe_matches_published_example():
    # Newcombe (1998), example (a): 56/70 vs 48/80, hybrid score method -> (0.0524, 0.3339)
    lo, hi = stats.newcombe_diff_ci(56, 70, 48, 80)
    assert lo == pytest.approx(0.0524, abs=5e-4) and hi == pytest.approx(0.3339, abs=5e-4)
    lo, hi = stats.newcombe_diff_ci(9, 10, 3, 10)
    assert lo == pytest.approx(0.1705, abs=5e-4) and hi == pytest.approx(0.8090, abs=5e-4)


def test_compare_to_reference_scores_by_bound_nearest_zero():
    t = pd.DataFrame({"key": ["a", "b", "c"], "n": [100, 100, 10], "wins": [70, 50, 9]})
    t["rate"] = t.wins / t.n
    ref = pd.DataFrame({"key": ["a", "b"], "n": [1000, 1000], "wins": [500, 500]})
    out = stats.compare_to_reference(t, ref).set_index("key")
    assert out.loc["a", "delta"] == pytest.approx(0.2)
    assert out.loc["a", "delta_excludes_zero"] and out.loc["a", "score"] > 0
    assert out.loc["a", "score"] == pytest.approx(out.loc["a", "delta_lo"])
    assert not out.loc["b", "delta_excludes_zero"] and out.loc["b", "score"] == 0
    assert out.loc["c", "ref_n"] == 0 and np.isnan(out.loc["c", "delta"])
    assert not out.loc["c", "ref_reliable"]
