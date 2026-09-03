from __future__ import annotations

import pandas as pd
import pytest

from liquidity_registry import (
    LiquidityRegistryError,
    build_liquidity_registry,
)


def _config() -> dict:
    return {
        "market": {
            "tick_size": 0.25,
        },
        "liquidity": {
            "sweep": {
                "minimum_penetration_ticks": 1,
                "require_close_back_through_level": True,
            },
            "registry": {
                "approach_ticks": 4,
                "break_ticks": 1,
            },
        },
    }


def _bars(
    *,
    highs=None,
    lows=None,
    closes=None,
    sessions=None,
) -> pd.DataFrame:
    timestamps = pd.date_range(
        "2026-09-01 13:30:00",
        periods=5,
        freq="1min",
        tz="UTC",
    )

    n = len(timestamps)

    highs = highs or [101.0] * n
    lows = lows or [99.0] * n
    closes = closes or [100.0] * n

    if sessions is None:
        sessions = [
            pd.Timestamp(
                "2026-09-01"
            ).date()
        ] * n

    dataframe = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [100.0] * n,
            "high": highs,
            "low": lows,
            "close": closes,
            "session_date": sessions,
        }
    )

    dataframe["timestamp_et"] = (
        dataframe["timestamp"]
        .dt.tz_convert(
            "America/New_York"
        )
    )

    return dataframe


def test_registry_rejects_naive_timestamps():
    dataframe = _bars()

    dataframe["timestamp"] = (
        dataframe["timestamp"]
        .dt.tz_localize(None)
    )

    with pytest.raises(
        LiquidityRegistryError,
        match="timezone-aware",
    ):
        build_liquidity_registry(
            dataframe,
            _config(),
        )


def test_registry_includes_asia_and_weekly_levels():
    dataframe = _bars()

    dataframe["ash"] = 105.0
    dataframe["asl"] = 95.0
    dataframe["week_high"] = 110.0
    dataframe["week_low"] = 90.0

    registry = build_liquidity_registry(
        dataframe,
        _config(),
    )

    sources = set(
        registry["source"]
    )

    assert "ash" in sources
    assert "asl" in sources
    assert "week_high" in sources
    assert "week_low" in sources

    weekly = registry.loc[
        registry["source"]
        == "week_high"
    ].iloc[0]

    assert weekly["timeframe"] == "1w"
    assert weekly["side"] == "buy"


def test_registry_adds_equal_high_and_low_pools():
    dataframe = _bars()

    dataframe[
        "internal_swing_high_equal"
    ] = False

    dataframe[
        "internal_swing_low_equal"
    ] = False

    dataframe[
        "internal_swing_high_equal_cluster_level"
    ] = float("nan")

    dataframe[
        "internal_swing_low_equal_cluster_level"
    ] = float("nan")

    dataframe[
        "internal_swing_high_equal_cluster_id"
    ] = None

    dataframe[
        "internal_swing_low_equal_cluster_id"
    ] = None

    dataframe[
        "internal_swing_high_equal_cluster_count"
    ] = 0

    dataframe[
        "internal_swing_low_equal_cluster_count"
    ] = 0

    dataframe[
        "internal_swing_high_timeframe"
    ] = "1m"

    dataframe[
        "internal_swing_low_timeframe"
    ] = "1m"

    dataframe.loc[
        2,
        "internal_swing_high_equal",
    ] = True

    dataframe.loc[
        2,
        "internal_swing_high_equal_cluster_level",
    ] = 104.0

    dataframe.loc[
        2,
        "internal_swing_high_equal_cluster_id",
    ] = "eqh_1"

    dataframe.loc[
        2,
        "internal_swing_high_equal_cluster_count",
    ] = 2

    dataframe.loc[
        3,
        "internal_swing_low_equal",
    ] = True

    dataframe.loc[
        3,
        "internal_swing_low_equal_cluster_level",
    ] = 96.0

    dataframe.loc[
        3,
        "internal_swing_low_equal_cluster_id",
    ] = "eql_1"

    dataframe.loc[
        3,
        "internal_swing_low_equal_cluster_count",
    ] = 2

    registry = build_liquidity_registry(
        dataframe,
        _config(),
    )

    assert (
        registry["source"]
        == "internal_equal_high"
    ).any()

    assert (
        registry["source"]
        == "internal_equal_low"
    ).any()


def test_same_price_on_different_sessions_has_distinct_identity():
    sessions = [
        pd.Timestamp(
            "2026-09-01"
        ).date(),
        pd.Timestamp(
            "2026-09-01"
        ).date(),
        pd.Timestamp(
            "2026-09-02"
        ).date(),
        pd.Timestamp(
            "2026-09-02"
        ).date(),
        pd.Timestamp(
            "2026-09-02"
        ).date(),
    ]

    dataframe = _bars(
        sessions=sessions,
    )

    dataframe["pdh"] = 105.0

    registry = build_liquidity_registry(
        dataframe,
        _config(),
    )

    pdh = registry.loc[
        registry["source"] == "pdh"
    ]

    assert len(pdh) == 2
    assert pdh["pool_id"].nunique() == 2
    assert pdh["level"].tolist() == [
        105.0,
        105.0,
    ]


def test_importance_records_explainable_components():
    dataframe = _bars()

    dataframe[
        "external_swing_high_confirmed"
    ] = False

    dataframe[
        "external_swing_high_price"
    ] = float("nan")

    dataframe[
        "external_swing_high_timeframe"
    ] = "5m"

    dataframe[
        "external_swing_high_pivot_time"
    ] = pd.NaT

    dataframe[
        "external_swing_high_strength_ticks"
    ] = float("nan")

    dataframe.loc[
        2,
        "external_swing_high_confirmed",
    ] = True

    dataframe.loc[
        2,
        "external_swing_high_price",
    ] = 105.0

    dataframe.loc[
        2,
        "external_swing_high_pivot_time",
    ] = dataframe.loc[
        0,
        "timestamp",
    ]

    dataframe.loc[
        2,
        "external_swing_high_strength_ticks",
    ] = 8.0

    registry = build_liquidity_registry(
        dataframe,
        _config(),
    )

    pool = registry.loc[
        registry["source"]
        == "external_swing_high"
    ].iloc[0]

    assert (
        pool["importance_score"]
        > 4.0
    )

    assert "strength_bonus" in pool[
        "importance_components"
    ]


def test_pool_moves_from_untouched_to_approached():
    dataframe = _bars(
        highs=[
            100.0,
            104.25,
            104.0,
            104.0,
            104.0,
        ],
    )

    dataframe["pdh"] = 105.0

    registry = build_liquidity_registry(
        dataframe,
        _config(),
    )

    pool = registry.loc[
        registry["source"] == "pdh"
    ].iloc[0]

    assert pool["state"] == "approached"
    assert pd.notna(
        pool["approached_at"]
    )

    assert pd.isna(
        pool["swept_at"]
    )

    assert pd.isna(
        pool["broken_at"]
    )


def test_pool_tracks_swept_state():
    dataframe = _bars(
        highs=[
            100.0,
            105.50,
            104.0,
            104.0,
            104.0,
        ],
        closes=[
            100.0,
            104.75,
            100.0,
            100.0,
            100.0,
        ],
    )

    dataframe["pdh"] = 105.0

    registry = build_liquidity_registry(
        dataframe,
        _config(),
    )

    pool = registry.loc[
        registry["source"] == "pdh"
    ].iloc[0]

    assert pool["state"] == "swept"

    assert pd.notna(
        pool["swept_at"]
    )


def test_pool_tracks_break_then_reclaim():
    dataframe = _bars(
        highs=[
            100.0,
            106.0,
            105.0,
            104.0,
            104.0,
        ],
        closes=[
            100.0,
            105.50,
            104.75,
            100.0,
            100.0,
        ],
    )

    dataframe["pdh"] = 105.0

    registry = build_liquidity_registry(
        dataframe,
        _config(),
    )

    pool = registry.loc[
        registry["source"] == "pdh"
    ].iloc[0]

    assert pool["state"] == "reclaimed"

    assert pd.notna(
        pool["broken_at"]
    )

    assert pd.notna(
        pool["reclaimed_at"]
    )

    assert (
        pool["reclaimed_at"]
        > pool["broken_at"]
    )


def test_old_session_pool_is_invalidated_when_replaced():
    sessions = [
        pd.Timestamp(
            "2026-09-01"
        ).date(),
        pd.Timestamp(
            "2026-09-01"
        ).date(),
        pd.Timestamp(
            "2026-09-02"
        ).date(),
        pd.Timestamp(
            "2026-09-02"
        ).date(),
        pd.Timestamp(
            "2026-09-02"
        ).date(),
    ]

    dataframe = _bars(
        sessions=sessions,
    )

    dataframe["pdh"] = [
        105.0,
        105.0,
        106.0,
        106.0,
        106.0,
    ]

    registry = build_liquidity_registry(
        dataframe,
        _config(),
    )

    pdh = (
        registry.loc[
            registry["source"] == "pdh"
        ]
        .sort_values("created_at")
        .reset_index(drop=True)
    )

    assert len(pdh) == 2

    assert (
        pdh.loc[
            0,
            "state",
        ]
        == "invalidated"
    )

    assert pd.notna(
        pdh.loc[
            0,
            "invalidated_at",
        ]
    )


def test_future_data_does_not_rewrite_pool_identity_or_creation():
    base = _bars()

    base["pdh"] = 105.0
    base["ash"] = 104.0

    prefix = base.iloc[:3].copy()

    future_changed = base.copy()

    future_changed.loc[
        3:,
        "high",
    ] = 1000.0

    future_changed.loc[
        3:,
        "close",
    ] = 900.0

    first = build_liquidity_registry(
        prefix,
        _config(),
    )

    second = build_liquidity_registry(
        future_changed,
        _config(),
    )

    initial_ids = set(
        first["pool_id"]
    )

    comparable = second.loc[
        second["pool_id"].isin(
            initial_ids
        ),
        [
            "pool_id",
            "source",
            "side",
            "level",
            "timeframe",
            "session_key",
            "created_at",
            "importance_score",
            "importance_components",
        ],
    ].sort_values(
        "pool_id"
    ).reset_index(
        drop=True
    )

    expected = first[
        [
            "pool_id",
            "source",
            "side",
            "level",
            "timeframe",
            "session_key",
            "created_at",
            "importance_score",
            "importance_components",
        ]
    ].sort_values(
        "pool_id"
    ).reset_index(
        drop=True
    )

    pd.testing.assert_frame_equal(
        expected,
        comparable,
        check_dtype=True,
    )
