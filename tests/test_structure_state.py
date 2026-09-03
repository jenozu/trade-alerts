from __future__ import annotations

import pandas as pd
import pytest

from structure_state import (
    StructureStateError,
    enrich_structure_state,
)


def _config() -> dict:
    return {
        "structure": {
            "break_buffer_points": 0.25,
        },
        "displacement": {
            "component_model": {
                "categories": {
                    "strong": 75.0,
                }
            }
        },
    }


def _frame(
    periods: int = 5,
) -> pd.DataFrame:
    timestamps = pd.date_range(
        "2026-09-01 13:30:00",
        periods=periods,
        freq="1min",
        tz="UTC",
    )

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [100.0] * periods,
            "high": [101.0] * periods,
            "low": [99.0] * periods,
            "close": [100.0] * periods,
            "active_internal_swing_high": [
                105.0
            ] * periods,
            "active_internal_swing_low": [
                95.0
            ] * periods,
            "internal_structure_trend": [
                "bullish"
            ] * periods,
            "bullish_displacement_score": [
                0.0
            ] * periods,
            "bearish_displacement_score": [
                0.0
            ] * periods,
            "bullish_displacement_category": [
                "none"
            ] * periods,
            "bearish_displacement_category": [
                "none"
            ] * periods,
            "displacement_direction": [
                "neutral"
            ] * periods,
            "volume_context": [
                "neutral"
            ] * periods,
            "rvol_time_of_day": [
                1.0
            ] * periods,
        }
    )

    df["available_at"] = (
        df["timestamp"]
        + pd.Timedelta(minutes=1)
    )

    return df


def test_rejects_naive_timestamp():
    df = _frame()

    df["timestamp"] = (
        df["timestamp"]
        .dt.tz_localize(None)
    )

    with pytest.raises(
        StructureStateError,
        match="timezone-aware",
    ):
        enrich_structure_state(
            df,
            _config(),
        )


def test_wick_sweep_is_not_body_close_break():
    df = _frame()

    df.loc[1, "high"] = 105.50
    df.loc[1, "close"] = 104.75

    result = enrich_structure_state(
        df,
        _config(),
    )

    assert bool(
        result.loc[
            1,
            "bullish_structure_wick_sweep_event",
        ]
    )

    assert not bool(
        result.loc[
            1,
            "bullish_body_close_break_event",
        ]
    )


def test_body_close_break_is_distinct_from_displacement_break():
    df = _frame()

    df.loc[1, "high"] = 106.0
    df.loc[1, "close"] = 105.50

    result = enrich_structure_state(
        df,
        _config(),
    )

    assert bool(
        result.loc[
            1,
            "bullish_body_close_break_event",
        ]
    )

    assert not bool(
        result.loc[
            1,
            "bullish_displacement_structure_break_event",
        ]
    )

    assert (
        result.loc[
            1,
            "structure_break_confirmation",
        ]
        == "body_close"
    )


def test_strong_same_direction_displacement_confirms_break():
    df = _frame()

    df.loc[1, "high"] = 106.0
    df.loc[1, "close"] = 105.75

    df.loc[
        1,
        "bullish_displacement_score",
    ] = 82.0

    df.loc[
        1,
        "bullish_displacement_category",
    ] = "strong"

    df.loc[
        1,
        "displacement_direction",
    ] = "bullish"

    result = enrich_structure_state(
        df,
        _config(),
    )

    assert bool(
        result.loc[
            1,
            "bullish_displacement_structure_break_event",
        ]
    )

    assert (
        result.loc[
            1,
            "structure_break_confirmation",
        ]
        == "displacement"
    )


def test_with_trend_break_is_continuation_break():
    df = _frame()

    df.loc[1, "high"] = 106.0
    df.loc[1, "close"] = 105.50

    result = enrich_structure_state(
        df,
        _config(),
    )

    assert bool(
        result.loc[
            1,
            "bullish_continuation_break_event",
        ]
    )


def test_body_only_break_then_close_back_is_failed_break_and_reclaim():
    df = _frame()

    df.loc[1, "high"] = 106.0
    df.loc[1, "close"] = 105.50

    df.loc[2, "close"] = 104.75

    result = enrich_structure_state(
        df,
        _config(),
    )

    assert bool(
        result.loc[
            2,
            "bullish_structure_reclaim_event",
        ]
    )

    assert bool(
        result.loc[
            2,
            "bullish_failed_break_event",
        ]
    )


def test_displacement_break_reclaim_is_not_failed_break():
    df = _frame()

    df.loc[1, "high"] = 106.0
    df.loc[1, "close"] = 105.75

    df.loc[
        1,
        "bullish_displacement_score",
    ] = 90.0

    df.loc[
        1,
        "bullish_displacement_category",
    ] = "strong"

    df.loc[
        1,
        "displacement_direction",
    ] = "bullish"

    df.loc[2, "close"] = 104.75

    result = enrich_structure_state(
        df,
        _config(),
    )

    assert bool(
        result.loc[
            2,
            "bullish_structure_reclaim_event",
        ]
    )

    assert not bool(
        result.loc[
            2,
            "bullish_failed_break_event",
        ]
    )


def test_break_metadata_exposes_level_time_and_confirmation():
    df = _frame()

    df.loc[1, "high"] = 106.0
    df.loc[1, "close"] = 105.50

    result = enrich_structure_state(
        df,
        _config(),
        timeframe="1m",
    )

    assert (
        result.loc[
            1,
            "structure_broken_level",
        ]
        == pytest.approx(105.0)
    )

    assert (
        result.loc[
            1,
            "structure_broken_timeframe",
        ]
        == "1m"
    )

    assert (
        result.loc[
            1,
            "structure_break_timestamp",
        ]
        == df.loc[
            1,
            "timestamp",
        ]
    )

    assert (
        result.loc[
            1,
            "structure_break_available_at",
        ]
        == df.loc[
            1,
            "available_at",
        ]
    )


def test_break_preserves_volume_and_displacement_context():
    df = _frame()

    df.loc[1, "high"] = 106.0
    df.loc[1, "close"] = 105.75

    df.loc[
        1,
        "bullish_displacement_score",
    ] = 85.0

    df.loc[
        1,
        "bullish_displacement_category",
    ] = "strong"

    df.loc[
        1,
        "displacement_direction",
    ] = "bullish"

    df.loc[
        1,
        "volume_context",
    ] = "bullish_breakout_high_volume"

    df.loc[
        1,
        "rvol_time_of_day",
    ] = 2.25

    result = enrich_structure_state(
        df,
        _config(),
    )

    assert (
        result.loc[
            1,
            "structure_break_displacement_score",
        ]
        == pytest.approx(85.0)
    )

    assert (
        result.loc[
            1,
            "structure_break_volume_context",
        ]
        == "bullish_breakout_high_volume"
    )

    assert (
        result.loc[
            1,
            "structure_break_rvol",
        ]
        == pytest.approx(2.25)
    )


def test_future_mutation_does_not_rewrite_past_structure_state():
    original = _frame()

    original.loc[1, "high"] = 106.0
    original.loc[1, "close"] = 105.50

    changed = original.copy()

    changed.loc[
        3:,
        "high",
    ] = 1000.0

    changed.loc[
        3:,
        "low",
    ] = 1.0

    changed.loc[
        3:,
        "close",
    ] = 900.0

    before = enrich_structure_state(
        original,
        _config(),
    )

    after = enrich_structure_state(
        changed,
        _config(),
    )

    columns = [
        "bullish_structure_wick_sweep_event",
        "bullish_body_close_break_event",
        "bullish_displacement_structure_break_event",
        "bullish_continuation_break_event",
        "structure_broken_level",
        "structure_break_confirmation",
    ]

    pd.testing.assert_frame_equal(
        before.loc[
            :2,
            columns,
        ],
        after.loc[
            :2,
            columns,
        ],
        check_dtype=True,
    )
