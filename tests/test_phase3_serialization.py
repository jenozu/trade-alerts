from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from confluence_zones import (
    build_confluence_zones,
)

from scorer import (
    enrich_scores,
)


def _config() -> dict:
    with Path(
        "config/strategy.yaml"
    ).open(
        "r",
        encoding="utf-8",
    ) as file:
        return yaml.safe_load(
            file
        )


def _json_payload(
    dataframe: pd.DataFrame,
) -> str:
    return dataframe.to_json(
        orient="records",
        date_format="iso",
        date_unit="ms",
    )


def test_confluence_zone_output_is_deterministically_json_serializable():
    timestamp = pd.date_range(
        "2026-09-01 13:30:00",
        periods=5,
        freq="1min",
        tz="UTC",
    )

    dataframe = pd.DataFrame(
        {
            "timestamp": timestamp,
            "available_at":
                timestamp
                + pd.Timedelta(
                    minutes=1
                ),
            "open": [100.0] * 5,
            "high": [101.0] * 5,
            "low": [99.0] * 5,
            "close": [100.0] * 5,
            "volume": [100.0] * 5,
            "pdl": [98.0] * 5,
            "pdh": [102.0] * 5,
            "vwap": [100.0] * 5,
            "htf_bias":
                ["neutral"] * 5,
            "volume_context":
                ["neutral"] * 5,
            "volume_spike_any":
                [False] * 5,
            "rvol_time_of_day":
                [1.0] * 5,
            "displacement_direction":
                ["neutral"] * 5,
            "bullish_displacement_score":
                [0.0] * 5,
            "bearish_displacement_score":
                [0.0] * 5,
        }
    )

    first = build_confluence_zones(
        dataframe,
        _config(),
    )

    second = build_confluence_zones(
        dataframe,
        _config(),
    )

    first_payload = _json_payload(
        first
    )

    second_payload = _json_payload(
        second
    )

    assert (
        first_payload
        == second_payload
    )

    parsed = json.loads(
        first_payload
    )

    assert isinstance(
        parsed,
        list,
    )

    assert len(parsed) == len(
        first
    )


def test_scorer_output_is_deterministically_json_serializable():
    timestamp = pd.Series(
        [
            pd.Timestamp(
                "2026-09-01 13:30:00",
                tz="UTC",
            )
        ]
    )

    dataframe = pd.DataFrame(
        {
            "timestamp": timestamp,
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.0],

            "data_healthy": [True],
            "new_entry_allowed": [True],
            "bullish_thesis_valid":
                [True],
            "bearish_thesis_valid":
                [True],

            "htf_bias": ["neutral"],
            "dol_direction":
                ["neutral"],

            "distance_to_unswept_liquidity_above":
                [50.0],
            "distance_to_unswept_liquidity_below":
                [50.0],

            "vwap": [100.0],
            "vwap_position": ["at"],
            "vwap_slope_direction":
                ["flat"],
            "vwap_bullish_cross":
                [False],
            "vwap_bearish_cross":
                [False],

            "external_dealing_location":
                ["equilibrium"],
            "internal_dealing_location":
                ["equilibrium"],

            "bullish_displacement_score":
                [0.0],
            "bearish_displacement_score":
                [0.0],

            "snr_confidence_modifier_points":
                [0.0],
        }
    )

    first = enrich_scores(
        dataframe,
        _config(),
    )

    second = enrich_scores(
        dataframe,
        _config(),
    )

    first_payload = _json_payload(
        first
    )

    second_payload = _json_payload(
        second
    )

    assert (
        first_payload
        == second_payload
    )

    parsed = json.loads(
        first_payload
    )

    assert len(parsed) == 1

    assert (
        parsed[0][
            "long_raw_score"
        ]
        is not None
    )

    assert (
        parsed[0][
            "short_raw_score"
        ]
        is not None
    )


def test_score_component_column_names_are_stable():
    dataframe = pd.DataFrame(
        {
            "timestamp": [
                pd.Timestamp(
                    "2026-09-01 13:30:00",
                    tz="UTC",
                )
            ],
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.0],
            "data_healthy": [True],
            "new_entry_allowed":
                [True],
            "distance_to_unswept_liquidity_above":
                [50.0],
            "distance_to_unswept_liquidity_below":
                [50.0],
            "snr_confidence_modifier_points":
                [0.0],
            "bullish_displacement_score":
                [0.0],
            "bearish_displacement_score":
                [0.0],
        }
    )

    result = enrich_scores(
        dataframe,
        _config(),
    )

    expected = {
        "long_raw_score",
        "short_raw_score",
        "long_score_band",
        "short_score_band",
        "long_positive_points",
        "short_positive_points",
        "long_penalty_points",
        "short_penalty_points",
        "score_edge",
        "preferred_score_direction",
    }

    assert expected.issubset(
        result.columns
    )
