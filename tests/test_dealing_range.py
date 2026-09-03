from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from dealing_range import (
    DealingRangeError,
    add_dealing_range,
    enrich_dealing_ranges,
)


def _frame() -> pd.DataFrame:
    timestamps = pd.date_range(
        "2026-09-01 13:30:00",
        periods=5,
        freq="1min",
        tz="UTC",
    )

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "close": [100.0, 102.5, 105.0, 107.5, 110.0],
            "internal_structure_range_high": [110.0] * 5,
            "internal_structure_range_low": [100.0] * 5,
            "external_structure_range_high": [120.0] * 5,
            "external_structure_range_low": [90.0] * 5,
        }
    )


def test_dealing_range_rejects_naive_timestamps():
    dataframe = _frame()
    dataframe["timestamp"] = (
        dataframe["timestamp"].dt.tz_localize(None)
    )

    with pytest.raises(
        DealingRangeError,
        match="timezone-aware",
    ):
        enrich_dealing_ranges(dataframe)


def test_internal_dealing_range_computes_midpoint_and_percentile():
    result = enrich_dealing_ranges(
        _frame(),
        scopes=["internal"],
    )

    assert result.loc[0, "internal_dealing_range_high"] == 110.0
    assert result.loc[0, "internal_dealing_range_low"] == 100.0
    assert result.loc[0, "internal_dealing_range_width"] == 10.0
    assert result.loc[0, "internal_dealing_equilibrium"] == 105.0

    assert result.loc[0, "internal_dealing_percentile"] == pytest.approx(0.0)
    assert result.loc[2, "internal_dealing_percentile"] == pytest.approx(0.5)
    assert result.loc[4, "internal_dealing_percentile"] == pytest.approx(1.0)


def test_premium_discount_equilibrium_classification():
    result = enrich_dealing_ranges(
        _frame(),
        scopes=["internal"],
    )

    assert result.loc[0, "internal_dealing_location"] == "discount"
    assert result.loc[1, "internal_dealing_location"] == "discount"
    assert result.loc[2, "internal_dealing_location"] == "equilibrium"
    assert result.loc[3, "internal_dealing_location"] == "premium"
    assert result.loc[4, "internal_dealing_location"] == "premium"


def test_multiple_ranges_are_exposed_independently():
    result = enrich_dealing_ranges(_frame())

    assert "internal_dealing_percentile" in result.columns
    assert "external_dealing_percentile" in result.columns

    # Close=105 in external 90-120 range is exactly equilibrium.
    assert result.loc[2, "external_dealing_percentile"] == pytest.approx(0.5)
    assert result.loc[2, "external_dealing_location"] == "equilibrium"


def test_invalid_range_remains_unknown():
    dataframe = _frame()

    dataframe.loc[0, "internal_structure_range_high"] = np.nan
    dataframe.loc[1, "internal_structure_range_high"] = 100.0
    dataframe.loc[1, "internal_structure_range_low"] = 100.0

    result = enrich_dealing_ranges(
        dataframe,
        scopes=["internal"],
    )

    assert not bool(result.loc[0, "internal_dealing_valid"])
    assert not bool(result.loc[1, "internal_dealing_valid"])

    assert pd.isna(result.loc[0, "internal_dealing_percentile"])
    assert pd.isna(result.loc[1, "internal_dealing_percentile"])

    assert result.loc[0, "internal_dealing_location"] == "unknown"
    assert result.loc[1, "internal_dealing_location"] == "unknown"


def test_price_outside_range_is_clipped_for_location_percentile():
    dataframe = _frame()
    dataframe.loc[0, "close"] = 95.0
    dataframe.loc[4, "close"] = 115.0

    result = enrich_dealing_ranges(
        dataframe,
        scopes=["internal"],
    )

    assert result.loc[0, "internal_dealing_percentile"] == pytest.approx(0.0)
    assert result.loc[4, "internal_dealing_percentile"] == pytest.approx(1.0)

    assert result.loc[0, "internal_dealing_location"] == "discount"
    assert result.loc[4, "internal_dealing_location"] == "premium"


def test_equilibrium_tolerance_creates_neutral_band():
    dataframe = _frame()
    dataframe.loc[0, "close"] = 104.6
    dataframe.loc[1, "close"] = 105.4

    result = enrich_dealing_ranges(
        dataframe,
        scopes=["internal"],
        equilibrium_tolerance=0.05,
    )

    assert result.loc[0, "internal_dealing_location"] == "equilibrium"
    assert result.loc[1, "internal_dealing_location"] == "equilibrium"


def test_future_changes_do_not_rewrite_past_dealing_range_features():
    original = _frame()
    changed = original.copy()

    changed.loc[3:, "close"] += 500.0
    changed.loc[3:, "internal_structure_range_high"] += 500.0
    changed.loc[3:, "internal_structure_range_low"] += 500.0

    before = enrich_dealing_ranges(
        original,
        scopes=["internal"],
    )
    after = enrich_dealing_ranges(
        changed,
        scopes=["internal"],
    )

    columns = [
        "internal_dealing_range_high",
        "internal_dealing_range_low",
        "internal_dealing_equilibrium",
        "internal_dealing_percentile",
        "internal_dealing_location",
    ]

    pd.testing.assert_frame_equal(
        before.loc[:2, columns],
        after.loc[:2, columns],
        check_dtype=True,
    )


def test_add_dealing_range_does_not_infer_directional_bias():
    result = add_dealing_range(
        _frame(),
        range_high_column="internal_structure_range_high",
        range_low_column="internal_structure_range_low",
        prefix="test",
    )

    # Premium/discount is objective location only.
    # The component must not invent long/short bias.
    forbidden = {
        "test_bias",
        "test_signal",
        "test_direction",
        "test_long",
        "test_short",
    }

    assert forbidden.isdisjoint(result.columns)


def test_multiple_timeframe_named_ranges_are_supported():
    dataframe = _frame().rename(
        columns={
            "internal_structure_range_high": "5m_structure_range_high",
            "internal_structure_range_low": "5m_structure_range_low",
            "external_structure_range_high": "1h_structure_range_high",
            "external_structure_range_low": "1h_structure_range_low",
        }
    )

    result = enrich_dealing_ranges(
        dataframe,
        scopes=["5m", "1h"],
    )

    assert "5m_dealing_percentile" in result.columns
    assert "1h_dealing_percentile" in result.columns

    assert result.loc[2, "5m_dealing_percentile"] == pytest.approx(0.5)
    assert result.loc[2, "1h_dealing_percentile"] == pytest.approx(0.5)
