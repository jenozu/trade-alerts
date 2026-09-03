from __future__ import annotations

import pandas as pd

from swing_lifecycle import (
    enrich_swing_lifecycle,
)


def _frame(
    trend: str,
) -> pd.DataFrame:
    timestamps = pd.date_range(
        "2026-09-01 13:30:00",
        periods=4,
        freq="1min",
        tz="UTC",
    )

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "active_internal_swing_high": [
                105.0
            ] * 4,
            "active_internal_swing_low": [
                95.0
            ] * 4,
            "internal_structure_trend": [
                trend
            ] * 4,
            "bullish_displacement_structure_break_event": [
                False
            ] * 4,
            "bearish_displacement_structure_break_event": [
                False
            ] * 4,
        }
    )


def test_bullish_structure_protects_low_and_marks_high_weak():
    result = enrich_swing_lifecycle(
        _frame("bullish"),
        {},
    )

    assert bool(
        result.loc[
            0,
            "active_internal_swing_low_protected_strong",
        ]
    )

    assert bool(
        result.loc[
            0,
            "active_internal_swing_high_weak_liquidity",
        ]
    )

    assert (
        result.loc[
            0,
            "active_internal_swing_low_classification",
        ]
        == "protected_strong"
    )

    assert (
        "bullish_structure_protects"
        in result.loc[
            0,
            "active_internal_swing_low_classification_reason",
        ]
    )


def test_bearish_structure_protects_high_and_marks_low_weak():
    result = enrich_swing_lifecycle(
        _frame("bearish"),
        {},
    )

    assert bool(
        result.loc[
            0,
            "active_internal_swing_high_protected_strong",
        ]
    )

    assert bool(
        result.loc[
            0,
            "active_internal_swing_low_weak_liquidity",
        ]
    )


def test_broken_with_displacement_persists_for_active_swing():
    dataframe = _frame(
        "bullish"
    )

    dataframe.loc[
        1,
        "bullish_displacement_structure_break_event",
    ] = True

    result = enrich_swing_lifecycle(
        dataframe,
        {},
    )

    assert not bool(
        result.loc[
            0,
            "active_internal_swing_high_broken_with_displacement",
        ]
    )

    assert bool(
        result.loc[
            1,
            "active_internal_swing_high_broken_with_displacement",
        ]
    )

    assert bool(
        result.loc[
            3,
            "active_internal_swing_high_broken_with_displacement",
        ]
    )

    assert (
        result.loc[
            3,
            "active_internal_swing_high_classification",
        ]
        == "broken_with_displacement"
    )


def test_new_active_swing_resets_broken_state():
    dataframe = _frame(
        "bullish"
    )

    dataframe.loc[
        1,
        "bullish_displacement_structure_break_event",
    ] = True

    dataframe.loc[
        3,
        "active_internal_swing_high",
    ] = 110.0

    result = enrich_swing_lifecycle(
        dataframe,
        {},
    )

    assert bool(
        result.loc[
            2,
            "active_internal_swing_high_broken_with_displacement",
        ]
    )

    assert not bool(
        result.loc[
            3,
            "active_internal_swing_high_broken_with_displacement",
        ]
    )

    assert bool(
        result.loc[
            3,
            "active_internal_swing_high_weak_liquidity",
        ]
    )
