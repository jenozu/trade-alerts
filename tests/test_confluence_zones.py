from __future__ import annotations

import json

import pandas as pd
import pytest

from confluence_zones import (
    ConfluenceZoneError,
    build_confluence_zones,
    confluence_summary,
)


def _config() -> dict:
    return {
        "confluence_zones": {
            "cluster_tolerance_points": 1.0,
            "reaction_tolerance_points": 0.5,
            "pivot_tolerance_points": 0.25,
            "source_score_cap": 60.0,
            "component_weights": {
                "htf_swing": 18.0,
                "session_level": 14.0,
                "equal_liquidity": 14.0,
                "fvg_boundary": 14.0,
                "vwap": 10.0,
                "equilibrium": 8.0,
            },
        },
        "displacement": {
            "component_model": {
                "categories": {
                    "moderate": 50.0,
                    "strong": 75.0,
                }
            }
        },
    }


def _frame(
    periods: int = 8,
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
            "volume": [100.0] * periods,
        }
    )

    df["available_at"] = (
        df["timestamp"]
        + pd.Timedelta(minutes=1)
    )

    df["volume_context"] = "neutral"
    df["volume_spike_any"] = False
    df["rvol_time_of_day"] = 1.0

    df["displacement_direction"] = "neutral"
    df["bullish_displacement_score"] = 0.0
    df["bearish_displacement_score"] = 0.0

    df["htf_bias"] = "neutral"

    return df


def _find_zone(
    zones: pd.DataFrame,
    *,
    level: float,
) -> pd.Series:
    index = (
        zones[
            "zone_midpoint"
        ]
        .sub(level)
        .abs()
        .idxmin()
    )

    return zones.loc[
        index
    ]


def test_rejects_naive_timestamp():
    df = _frame()

    df["timestamp"] = (
        df["timestamp"]
        .dt.tz_localize(None)
    )

    with pytest.raises(
        ConfluenceZoneError,
        match="timezone-aware",
    ):
        build_confluence_zones(
            df,
            _config(),
        )


def test_htf_swing_component_is_preserved():
    df = _frame()

    df[
        "active_external_swing_low"
    ] = 98.0

    zones = build_confluence_zones(
        df,
        _config(),
    )

    zone = _find_zone(
        zones,
        level=98.0,
    )

    assert bool(
        zone[
            "component_htf_swing"
        ]
    )

    assert zone[
        "zone_side"
    ] == "support"


def test_prior_session_levels_cluster_together():
    df = _frame()

    df["pdl"] = 98.00
    df["pml"] = 98.50

    zones = build_confluence_zones(
        df,
        _config(),
    )

    zone = _find_zone(
        zones,
        level=98.25,
    )

    assert bool(
        zone[
            "component_session_level"
        ]
    )

    assert (
        zone[
            "source_count"
        ]
        >= 2
    )


def test_equal_high_component_is_supported():
    df = _frame()

    df[
        "external_swing_high_equal_cluster_level"
    ] = float("nan")

    df.loc[
        6,
        "external_swing_high_equal_cluster_level",
    ] = 102.0

    zones = build_confluence_zones(
        df,
        _config(),
    )

    zone = _find_zone(
        zones,
        level=102.0,
    )

    assert bool(
        zone[
            "component_equal_liquidity"
        ]
    )

    assert zone[
        "zone_side"
    ] == "resistance"


def test_active_fvg_boundaries_expose_mitigation_state():
    df = _frame()

    df[
        "nearest_active_bullish_fvg_lower"
    ] = 97.75

    df[
        "nearest_active_bullish_fvg_upper"
    ] = 98.25

    zones = build_confluence_zones(
        df,
        _config(),
    )

    zone = _find_zone(
        zones,
        level=98.0,
    )

    assert bool(
        zone[
            "component_fvg_boundary"
        ]
    )

    assert (
        zone[
            "mitigation_state"
        ]
        == "active_fvg"
    )

    assert (
        zone[
            "mitigation_component_score"
        ]
        == pytest.approx(
            4.0
        )
    )


def test_vwap_and_equilibrium_are_separate_components():
    df = _frame()

    df["vwap"] = 98.25

    df[
        "internal_dealing_equilibrium"
    ] = 98.50

    zones = build_confluence_zones(
        df,
        _config(),
    )

    zone = _find_zone(
        zones,
        level=98.375,
    )

    assert bool(
        zone[
            "component_vwap"
        ]
    )

    assert bool(
        zone[
            "component_equilibrium"
        ]
    )


def test_reaction_count_and_recency_are_explicit():
    df = _frame()

    df["pdl"] = 98.5

    # Only some historical bars actually react near the level.
    df["low"] = [
        99.5,
        98.4,
        99.3,
        98.6,
        99.4,
        99.2,
        98.5,
        99.0,
    ]

    zones = build_confluence_zones(
        df,
        _config(),
    )

    zone = _find_zone(
        zones,
        level=98.5,
    )

    assert (
        zone[
            "reaction_count"
        ]
        >= 3
    )

    assert pd.notna(
        zone[
            "reaction_recency_bars"
        ]
    )

    assert (
        zone[
            "reaction_component_score"
        ]
        > 0
    )


def test_volume_reaction_is_scored_at_latest_touch():
    df = _frame()

    df["pdl"] = 98.5
    df["low"] = 99.5

    df.loc[
        6,
        "low",
    ] = 98.5

    df.loc[
        6,
        "volume_context",
    ] = "bullish_rejection_high_volume"

    df.loc[
        6,
        "volume_spike_any",
    ] = True

    zones = build_confluence_zones(
        df,
        _config(),
    )

    zone = _find_zone(
        zones,
        level=98.5,
    )

    assert (
        zone[
            "volume_component_score"
        ]
        == pytest.approx(
            8.0
        )
    )

    assert (
        "rejection"
        in zone[
            "volume_reaction_context"
        ]
    )


def test_bullish_displacement_away_scores_support():
    df = _frame()

    df["pdl"] = 98.5
    df["low"] = 99.5

    df.loc[
        6,
        "low",
    ] = 98.5

    df.loc[
        6,
        "displacement_direction",
    ] = "bullish"

    df.loc[
        6,
        "bullish_displacement_score",
    ] = 85.0

    zones = build_confluence_zones(
        df,
        _config(),
    )

    zone = _find_zone(
        zones,
        level=98.5,
    )

    assert (
        zone[
            "displacement_component_score"
        ]
        == pytest.approx(
            10.0
        )
    )

    assert (
        zone[
            "displacement_away_raw_score"
        ]
        == pytest.approx(
            85.0
        )
    )


def test_htf_alignment_scores_directionally():
    df = _frame()

    df["pdl"] = 98.5
    df["htf_bias"] = "bullish"

    zones = build_confluence_zones(
        df,
        _config(),
    )

    zone = _find_zone(
        zones,
        level=98.5,
    )

    assert (
        zone[
            "htf_alignment_state"
        ]
        == "aligned_bullish"
    )

    assert (
        zone[
            "htf_alignment_component_score"
        ]
        == pytest.approx(
            8.0
        )
    )


def test_transparent_score_matches_preserved_components():
    df = _frame()

    df["active_external_swing_low"] = 98.0
    df["pdl"] = 98.25
    df["vwap"] = 98.50

    zones = build_confluence_zones(
        df,
        _config(),
    )

    zone = _find_zone(
        zones,
        level=98.25,
    )

    expected = min(
        100.0,
        float(
            zone[
                "source_component_score"
            ]
        )
        + float(
            zone[
                "reaction_component_score"
            ]
        )
        + float(
            zone[
                "volume_component_score"
            ]
        )
        + float(
            zone[
                "displacement_component_score"
            ]
        )
        + float(
            zone[
                "mitigation_component_score"
            ]
        )
        + float(
            zone[
                "htf_alignment_component_score"
            ]
        ),
    )

    assert (
        zone[
            "combined_zone_score"
        ]
        == pytest.approx(
            expected
        )
    )

    components = json.loads(
        zone[
            "components_json"
        ]
    )

    assert (
        components[
            "source_component_score"
        ]
        == pytest.approx(
            zone[
                "source_component_score"
            ]
        )
    )


def test_summary_reports_support_and_resistance():
    df = _frame()

    df["pdl"] = 98.0
    df["pdh"] = 102.0

    zones = build_confluence_zones(
        df,
        _config(),
    )

    summary = confluence_summary(
        zones
    )

    assert (
        summary.support_zones
        >= 1
    )

    assert (
        summary.resistance_zones
        >= 1
    )


def test_future_mutation_does_not_rewrite_snapshot():
    df = _frame()

    df["pdl"] = 98.5
    df["pdh"] = 102.0

    as_of = df.loc[
        4,
        "available_at",
    ]

    before = build_confluence_zones(
        df,
        _config(),
        as_of=as_of,
    )

    changed = df.copy()

    changed.loc[
        5:,
        [
            "high",
            "low",
            "close",
        ],
    ] = [
        [1000.0, 1.0, 900.0],
        [1000.0, 1.0, 900.0],
        [1000.0, 1.0, 900.0],
    ]

    changed.loc[
        5:,
        "pdl",
    ] = 500.0

    after = build_confluence_zones(
        changed,
        _config(),
        as_of=as_of,
    )

    comparable = [
        "zone_side",
        "zone_lower",
        "zone_upper",
        "zone_midpoint",
        "source_count",
        "component_count",
        "source_component_score",
        "reaction_count",
        "combined_zone_score",
    ]

    pd.testing.assert_frame_equal(
        before[
            comparable
        ].reset_index(
            drop=True
        ),
        after[
            comparable
        ].reset_index(
            drop=True
        ),
        check_dtype=True,
    )
