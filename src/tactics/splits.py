"""Train / holdout split by MATCH.

Rallies from the same match share players, venue, form and annotator, so any split that
puts strokes of one match on both sides leaks. We reuse the match-level validation and test
ids that ShuttleSet22 ships in its own `preprocess_data.py` (VAL_ID + TEST_ID), so our
holdout is the published one and nothing about it was chosen after seeing results.
"""

from __future__ import annotations

import pandas as pd

SHUTTLESET22_VAL_IDS = (38, 46, 47, 48, 49)
SHUTTLESET22_TEST_IDS = (39, 40, 50, 52, 53, 54, 55, 56, 57)

HOLDOUT_MATCH_IDS: frozenset[str] = frozenset(
    f"ShuttleSet22:{i}" for i in SHUTTLESET22_VAL_IDS + SHUTTLESET22_TEST_IDS
)


def is_holdout(match_id: pd.Series) -> pd.Series:
    return match_id.astype(str).isin(HOLDOUT_MATCH_IDS)


def split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(development, holdout) stroke tables."""
    mask = is_holdout(df.match_id)
    return df[~mask], df[mask]
