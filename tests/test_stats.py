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
