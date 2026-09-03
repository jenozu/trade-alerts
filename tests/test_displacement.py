from __future__ import annotations

import pandas as pd
import pytest

from displacement import (
    DisplacementError,
    enrich_displacement_components,
)


def _config() -> dict:
    return {
        "displacement": {
            "enabled": True,
            "atr_period": 2,
            "close_extreme_fraction": 0.25,
            "require_directional_close": True,
            "component_model": {
                "minimum_coverage_fraction": 0.50,
                "normalization": {
                    "body_atr_target": 1.20,
                    "range_atr_target": 1.50,
                    "consecutive_candles_target": 3,
                    "break_distance_atr_target": 0.50,
                    "rvol_target": 1.50,
                },
                "weights": {
                    "body_atr": 20,
                    "range_atr": 15,
                    "close_location": 15,
                    "consecutive": 10,
                    "structure_break_distance": 15,
                    "rvol": 10,
                    "fvg_generation": 10,
                    "follow_through": 5,
                },
                "categories": {
                    "weak": 40,
                    "moderate": 60,
                    "strong": 75,
                },
            },
        }
    }


def _bars() -> pd.DataFrame:
    timestamps = pd.date_range(
        "2026-09-01 13:30:00",
        periods=5,
        freq="1min",
        tz="UTC",
    )

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [
                100.0,
                100.1,
                100.2,
                100.3,
                101.7,
            ],
            "high": [
                100.4,
                100.5,
                100.6,
                102.1,
                102.0,
            ],
            "low": [
                99.9,
                100.0,
                100.1,
                100.2,
                100.6,
            ],
            "close": [
                100.1,
                100.2,
                100.3,
                101.9,
                100.8,
            ],
            "atr_1m": [1.0] * 5,
            "active_internal_swing_high": [101.0] * 5,
            "active_internal_swing_low": [99.0] * 5,
            "rvol_time_of_day": [
                1.0,
                1.0,
                1.0,
                1.8,
                1.6,
            ],
            "bullish_fvg_created": [
                False,
                False,
                False,
                True,
                False,
            ],
            "bearish_fvg_created": [
                False,
                False,
                False,
                False,
                True,
            ],
        }
    )


def test_rejects_naive_timestamps():
    dataframe = _bars()
    dataframe["timestamp"] = (
        dataframe["timestamp"].dt.tz_localize(None)
    )

    with pytest.raises(
        DisplacementError,
        match="timezone-aware",
    ):
        enrich_displacement_components(
            dataframe,
            _config(),
        )


def test_exposes_all_raw_component_columns():
    result = enrich_displacement_components(
        _bars(),
        _config(),
    )

    components = [
        "body_atr",
        "range_atr",
        "close_location",
        "consecutive",
        "structure_break_distance",
        "rvol",
        "fvg_generation",
        "follow_through",
    ]

    for direction in ("bullish", "bearish"):
        for component in components:
            assert (
                f"{direction}_displacement_component_{component}"
                in result.columns
            )


def test_body_and_range_atr_components_are_explainable():
    result = enrich_displacement_components(
        _bars(),
        _config(),
    )

    assert (
        result.loc[3, "displacement_body_atr_ratio"]
        == pytest.approx(1.6)
    )

    assert (
        result.loc[3, "displacement_range_atr_ratio"]
        == pytest.approx(1.9)
    )

    assert (
        result.loc[
            3,
            "bullish_displacement_component_body_atr",
        ]
        == pytest.approx(1.0)
    )

    assert (
        result.loc[
            3,
            "bullish_displacement_component_range_atr",
        ]
        == pytest.approx(1.0)
    )


def test_structure_break_distance_is_directional():
    result = enrich_displacement_components(
        _bars(),
        _config(),
    )

    assert (
        result.loc[3, "bullish_break_distance_points"]
        == pytest.approx(0.9)
    )

    assert (
        result.loc[3, "bullish_break_distance_atr"]
        == pytest.approx(0.9)
    )

    assert (
        result.loc[3, "bearish_break_distance_points"]
        == pytest.approx(0.0)
    )


def test_rvol_and_fvg_components_are_preserved():
    result = enrich_displacement_components(
        _bars(),
        _config(),
    )

    assert (
        result.loc[
            3,
            "bullish_displacement_component_rvol",
        ]
        == pytest.approx(1.0)
    )

    assert (
        result.loc[
            3,
            "bullish_displacement_component_fvg_generation",
        ]
        == pytest.approx(1.0)
    )

    assert (
        result.loc[
            3,
            "bearish_displacement_component_fvg_generation",
        ]
        == pytest.approx(0.0)
    )


def test_follow_through_uses_only_current_and_previous_bar():
    result = enrich_displacement_components(
        _bars(),
        _config(),
    )

    # Bar 3 closes above the previous bar's high.
    assert bool(
        result.loc[3, "bullish_follow_through"]
    )

    # No future bar is needed to establish this state.
    assert (
        result.loc[
            3,
            "bullish_displacement_component_follow_through",
        ]
        == pytest.approx(1.0)
    )


def test_strong_bullish_displacement_scores_high():
    result = enrich_displacement_components(
        _bars(),
        _config(),
    )

    assert (
        result.loc[3, "bullish_displacement_score"]
        >= 75.0
    )

    assert (
        result.loc[3, "bullish_displacement_category"]
        == "strong"
    )

    assert (
        result.loc[3, "displacement_direction"]
        == "bullish"
    )


def test_bearish_candle_cannot_be_selected_as_bullish_when_direction_required():
    result = enrich_displacement_components(
        _bars(),
        _config(),
    )

    assert (
        result.loc[4, "bullish_displacement_score"]
        == pytest.approx(0.0)
    )


def test_score_is_bounded_and_coverage_is_exposed():
    result = enrich_displacement_components(
        _bars(),
        _config(),
    )

    assert (
        result["bullish_displacement_score"]
        .between(0.0, 100.0)
        .all()
    )

    assert (
        result["bearish_displacement_score"]
        .between(0.0, 100.0)
        .all()
    )

    assert (
        result["bullish_displacement_coverage"]
        .between(0.0, 1.0)
        .all()
    )


def test_optional_components_can_be_missing_without_inventing_values():
    dataframe = _bars().drop(
        columns=[
            "rvol_time_of_day",
            "bullish_fvg_created",
            "bearish_fvg_created",
            "active_internal_swing_high",
            "active_internal_swing_low",
        ]
    )

    result = enrich_displacement_components(
        dataframe,
        _config(),
    )

    assert result[
        "displacement_rvol"
    ].isna().all()

    assert result[
        "bullish_break_distance_points"
    ].isna().all()

    assert (
        result["bullish_displacement_coverage"] < 1.0
    ).all()


def test_future_mutation_does_not_rewrite_past_components():
    original = _bars()

    changed = original.copy()

    changed.loc[4, "open"] = 500.0
    changed.loc[4, "high"] = 900.0
    changed.loc[4, "low"] = 100.0
    changed.loc[4, "close"] = 850.0
    changed.loc[4, "rvol_time_of_day"] = 10.0

    before = enrich_displacement_components(
        original,
        _config(),
    )

    after = enrich_displacement_components(
        changed,
        _config(),
    )

    columns = [
        "displacement_body_atr_ratio",
        "displacement_range_atr_ratio",
        "displacement_close_location",
        "bullish_directional_streak",
        "bullish_break_distance_atr",
        "bullish_displacement_score",
        "bullish_displacement_category",
        "displacement_direction",
    ]

    pd.testing.assert_frame_equal(
        before.loc[:3, columns],
        after.loc[:3, columns],
        check_dtype=True,
    )
