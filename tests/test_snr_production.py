from __future__ import annotations

import json

import pandas as pd
import pytest

from snr import (
    SNRError,
    add_snr_production_context,
    snr_market_state_snapshot,
)


def _config() -> dict:
    return {
        "snr": {
            "production_role": {
                "role":
                    "confidence_quality_modifier",
                "standalone_direction_predictor":
                    False,
                "morning_confidence": {
                    "enabled":
                        True,
                    "maximum_bonus_points":
                        5.0,
                    "maximum_penalty_points":
                        5.0,
                    "weak_quality_maximum":
                        0.35,
                    "strong_quality_minimum":
                        0.70,
                    "developing_modifier_points":
                        0.0,
                },
                "expose_raw_components":
                    True,
            }
        }
    }


def _frame(
    quality: float,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "snr_1m": [1.2],
            "snr_direction_1m":
                ["bullish"],
            "snr_delta_1m": [0.10],
            "snr_slope_1m": [0.05],
            "efficiency_1m": [0.70],
            "atr_1m": [2.0],

            "snr_5m": [1.1],
            "snr_direction_5m":
                ["bullish"],
            "snr_delta_5m": [0.08],
            "snr_slope_5m": [0.04],
            "efficiency_5m": [0.65],
            "atr_5m": [4.0],

            "snr_15m": [1.0],
            "snr_direction_15m":
                ["bullish"],
            "snr_delta_15m": [0.05],
            "snr_slope_15m": [0.02],
            "efficiency_15m": [0.60],
            "atr_15m": [8.0],

            "snr_alignment":
                ["strong_bullish"],

            "snr_composite_quality":
                [quality],
        }
    )


def test_strong_snr_quality_adds_bounded_confidence_bonus():
    result = (
        add_snr_production_context(
            _frame(0.80),
            _config(),
        )
    )

    assert (
        result.loc[
            0,
            "snr_quality_class",
        ]
        == "strong"
    )

    assert (
        result.loc[
            0,
            "snr_confidence_modifier_points",
        ]
        == pytest.approx(
            5.0
        )
    )


def test_weak_snr_quality_adds_bounded_confidence_penalty():
    result = (
        add_snr_production_context(
            _frame(0.20),
            _config(),
        )
    )

    assert (
        result.loc[
            0,
            "snr_quality_class",
        ]
        == "weak"
    )

    assert (
        result.loc[
            0,
            "snr_confidence_modifier_points",
        ]
        == pytest.approx(
            -5.0
        )
    )


def test_developing_snr_quality_is_neutral():
    result = (
        add_snr_production_context(
            _frame(0.50),
            _config(),
        )
    )

    assert (
        result.loc[
            0,
            "snr_quality_class",
        ]
        == "developing"
    )

    assert (
        result.loc[
            0,
            "snr_confidence_modifier_points",
        ]
        == pytest.approx(
            0.0
        )
    )


def test_snr_cannot_be_configured_as_standalone_direction_predictor():
    config = _config()

    config[
        "snr"
    ][
        "production_role"
    ][
        "standalone_direction_predictor"
    ] = True

    with pytest.raises(
        SNRError,
        match="standalone direction predictor",
    ):
        add_snr_production_context(
            _frame(0.80),
            config,
        )


def test_modifier_does_not_depend_on_bullish_vs_bearish_direction():
    bullish = _frame(
        0.80
    )

    bearish = _frame(
        0.80
    )

    for timeframe in (
        "1m",
        "5m",
        "15m",
    ):
        bearish.loc[
            0,
            f"snr_direction_{timeframe}",
        ] = "bearish"

    bearish.loc[
        0,
        "snr_alignment",
    ] = "strong_bearish"

    bullish_result = (
        add_snr_production_context(
            bullish,
            _config(),
        )
    )

    bearish_result = (
        add_snr_production_context(
            bearish,
            _config(),
        )
    )

    assert (
        bullish_result.loc[
            0,
            "snr_confidence_modifier_points",
        ]
        == bearish_result.loc[
            0,
            "snr_confidence_modifier_points",
        ]
        == pytest.approx(
            5.0
        )
    )

    assert not bool(
        bullish_result.loc[
            0,
            "snr_standalone_direction_predictor",
        ]
    )

    assert not bool(
        bearish_result.loc[
            0,
            "snr_standalone_direction_predictor",
        ]
    )


def test_market_state_snapshot_preserves_all_raw_timeframes():
    result = (
        add_snr_production_context(
            _frame(0.80),
            _config(),
        )
    )

    snapshot = (
        snr_market_state_snapshot(
            result.iloc[0]
        )
    )

    assert (
        snapshot[
            "role"
        ]
        == "confidence_quality_modifier"
    )

    assert (
        snapshot[
            "standalone_direction_predictor"
        ]
        is False
    )

    assert set(
        snapshot[
            "raw_components"
        ]
    ) == {
        "1m",
        "5m",
        "15m",
    }

    assert (
        snapshot[
            "raw_components"
        ][
            "1m"
        ][
            "snr"
        ]
        == pytest.approx(
            1.2
        )
    )


def test_serialized_market_state_contains_raw_components():
    result = (
        add_snr_production_context(
            _frame(0.80),
            _config(),
        )
    )

    raw = json.loads(
        result.loc[
            0,
            "snr_raw_components_json",
        ]
    )

    state = json.loads(
        result.loc[
            0,
            "snr_market_state_json",
        ]
    )

    assert set(
        raw
    ) == {
        "1m",
        "5m",
        "15m",
    }

    assert (
        state[
            "quality_class"
        ]
        == "strong"
    )

    assert (
        state[
            "confidence_modifier_points"
        ]
        == pytest.approx(
            5.0
        )
    )
