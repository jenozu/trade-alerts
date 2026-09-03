from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from run_pipeline import (
    PIPELINE_STAGES,
)

from scorer import (
    score_setup,
)

from scorer_harmonization import (
    positive_weight_total,
    validate_positive_weight_total,
)


def _config() -> dict:
    path = Path(
        "config/strategy.yaml"
    )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return yaml.safe_load(
            file
        )


def _row() -> pd.Series:
    return pd.Series(
        {
            "timestamp":
                pd.Timestamp(
                    "2026-09-01 13:30:00",
                    tz="UTC",
                ),
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,

            "data_healthy": True,
            "new_entry_allowed": True,
            "bullish_thesis_valid": True,
            "bearish_thesis_valid": True,

            "distance_to_unswept_liquidity_above":
                100.0,
            "distance_to_unswept_liquidity_below":
                100.0,

            "htf_bias": "neutral",
            "dol_direction": "neutral",

            "recent_sell_side_sweep": False,
            "recent_buy_side_sweep": False,
            "sell_side_liquidity_sweep": False,
            "buy_side_liquidity_sweep": False,

            "bullish_displacement": False,
            "bearish_displacement": False,
            "recent_bullish_displacement": False,
            "recent_bearish_displacement": False,

            "bullish_mss": False,
            "bearish_mss": False,
            "bullish_bos": False,
            "bearish_bos": False,

            "bullish_fvg_created": False,
            "bearish_fvg_created": False,

            "volume_spike_any": False,
            "rvol_time_of_day": 1.0,

            "external_premium_discount":
                "equilibrium",

            "external_dealing_location":
                "equilibrium",
            "internal_dealing_location":
                "equilibrium",

            "vwap": 100.0,
            "vwap_position": "at",
            "vwap_slope_direction": "flat",
            "vwap_bullish_cross": False,
            "vwap_bearish_cross": False,

            "snr_confidence_modifier_points":
                0.0,

            "bullish_displacement_score":
                0.0,
            "bearish_displacement_score":
                0.0,
        }
    )


def test_production_positive_weights_total_exactly_100():
    config = _config()

    assert (
        positive_weight_total(
            config
        )
        == pytest.approx(
            100.0
        )
    )

    assert (
        validate_positive_weight_total(
            config
        )
        == pytest.approx(
            100.0
        )
    )


def test_vwap_can_supply_existing_key_location_bucket():
    row = _row()

    row["close"] = 101.0
    row["vwap"] = 100.0
    row["vwap_position"] = "above"
    row[
        "vwap_slope_direction"
    ] = "rising"

    result = score_setup(
        row,
        direction="long",
        config=_config(),
    )

    assert (
        result.contributions[
            "key_location"
        ]
        == pytest.approx(
            8.0
        )
    )

    assert (
        result.contributions[
            "detail_key_location_vwap"
        ]
        == pytest.approx(
            1.0
        )
    )


def test_dealing_range_supplies_premium_discount_bucket():
    row = _row()

    row[
        "external_dealing_location"
    ] = "discount"

    result = score_setup(
        row,
        direction="long",
        config=_config(),
    )

    assert (
        result.contributions[
            "premium_discount"
        ]
        == pytest.approx(
            4.0
        )
    )

    assert (
        result.contributions[
            "detail_dealing_range_alignment"
        ]
        == pytest.approx(
            1.0
        )
    )


def test_confluence_can_supply_key_location_without_double_counting():
    row = _row()

    row["close"] = 100.0

    # Two distinct source categories clustered below price.
    row[
        "active_external_swing_low"
    ] = 98.0

    row["pdl"] = 98.5

    result = score_setup(
        row,
        direction="long",
        config=_config(),
    )

    assert (
        result.contributions[
            "detail_key_location_confluence_score"
        ]
        >= 40.0
    )

    assert (
        result.contributions[
            "key_location"
        ]
        == pytest.approx(
            8.0
        )
    )

    # detail_* values are explanatory and not part of positive_points.
    counted = sum(
        value
        for key, value
        in result.contributions.items()
        if not key.startswith(
            (
                "detail_",
                "penalty_",
            )
        )
    )

    assert (
        result.positive_points
        == pytest.approx(
            counted
        )
    )


def test_richer_displacement_scales_existing_bucket():
    row = _row()

    row[
        "bullish_displacement_score"
    ] = 50.0

    result = score_setup(
        row,
        direction="long",
        config=_config(),
    )

    assert (
        result.contributions[
            "displacement"
        ]
        == pytest.approx(
            6.0
        )
    )

    assert (
        result.contributions[
            "detail_displacement_fraction"
        ]
        == pytest.approx(
            0.5
        )
    )


def test_strong_snr_quality_is_direction_neutral():
    bullish = _row()
    bearish = _row()

    bullish[
        "snr_confidence_modifier_points"
    ] = 5.0

    bearish[
        "snr_confidence_modifier_points"
    ] = 5.0

    bullish[
        "snr_direction_5m"
    ] = "bullish"

    bearish[
        "snr_direction_5m"
    ] = "bearish"

    long_a = score_setup(
        bullish,
        direction="long",
        config=_config(),
    )

    long_b = score_setup(
        bearish,
        direction="long",
        config=_config(),
    )

    assert (
        long_a.contributions[
            "signal_to_noise"
        ]
        == pytest.approx(
            10.0
        )
    )

    assert (
        long_b.contributions[
            "signal_to_noise"
        ]
        == pytest.approx(
            10.0
        )
    )

    assert (
        long_a.contributions[
            "penalty_snr_conflict"
        ]
        == pytest.approx(
            0.0
        )
    )

    assert (
        long_b.contributions[
            "penalty_snr_conflict"
        ]
        == pytest.approx(
            0.0
        )
    )


def test_weak_snr_quality_applies_small_non_directional_penalty():
    row = _row()

    row[
        "snr_confidence_modifier_points"
    ] = -5.0

    row[
        "snr_direction_5m"
    ] = "bullish"

    long_result = score_setup(
        row,
        direction="long",
        config=_config(),
    )

    short_result = score_setup(
        row,
        direction="short",
        config=_config(),
    )

    assert (
        long_result.contributions[
            "penalty_snr_conflict"
        ]
        == pytest.approx(
            -5.0
        )
    )

    assert (
        short_result.contributions[
            "penalty_snr_conflict"
        ]
        == pytest.approx(
            -5.0
        )
    )


def test_htf_conflict_penalty_is_preserved():
    row = _row()

    row["htf_bias"] = "bearish"

    result = score_setup(
        row,
        direction="long",
        config=_config(),
    )

    assert (
        result.contributions[
            "penalty_htf_conflict"
        ]
        == pytest.approx(
            -20.0
        )
    )


def test_score_remains_clamped_to_100():
    row = _row()

    row["htf_bias"] = "bullish"
    row["dol_direction"] = "bullish"

    row[
        "recent_sell_side_sweep"
    ] = True

    row[
        "sell_side_liquidity_sweep"
    ] = True

    row[
        "bullish_displacement"
    ] = True

    row[
        "bullish_displacement_score"
    ] = 100.0

    row["bullish_mss"] = True
    row["bullish_fvg_created"] = True

    row["volume_spike_any"] = True

    row[
        "external_dealing_location"
    ] = "discount"

    row[
        "external_premium_discount"
    ] = "discount"

    row[
        "snr_confidence_modifier_points"
    ] = 5.0

    row["close"] = 101.0
    row["vwap"] = 100.0
    row["vwap_position"] = "above"
    row[
        "vwap_slope_direction"
    ] = "rising"

    result = score_setup(
        row,
        direction="long",
        config=_config(),
    )

    assert (
        result.raw_score
        <= 100.0
    )

    assert (
        result.positive_points
        <= 100.0
    )


def test_pipeline_runs_vwap_before_volume():
    assert (
        PIPELINE_STAGES.index(
            "sessions"
        )
        < PIPELINE_STAGES.index(
            "vwap"
        )
        < PIPELINE_STAGES.index(
            "volume"
        )
    )


def test_pipeline_runs_dealing_range_after_structure_before_dol():
    assert (
        PIPELINE_STAGES.index(
            "structure"
        )
        < PIPELINE_STAGES.index(
            "dealing_range"
        )
        < PIPELINE_STAGES.index(
            "dol"
        )
    )


def test_calibration_remains_disabled():
    config = _config()

    calibration = (
        config[
            "scoring"
        ][
            "harmonization"
        ][
            "calibration"
        ]
    )

    assert (
        calibration[
            "enabled"
        ]
        is False
    )
