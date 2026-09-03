from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from fvg import (
    build_fvg_settings,
    build_fvg_table,
    detect_fvg_creation,
    track_fvg_lifecycle,
)

from fvg_state import (
    FVGStateError,
    build_fvg_objects,
    build_multitimeframe_fvg_objects,
    materialize_fvg_state_as_of,
    nearest_fvg_snapshot,
    track_fvg_lifecycle_fast,
)


def _config() -> dict:
    return {
        "market": {
            "tick_size": 0.25,
        },
        "fvg": {
            "enabled": True,
            "detection": {
                "minimum_gap_ticks": 1,
                "minimum_gap_atr_fraction": 0.0,
                "require_displacement_candle": False,
            },
            "mitigation": {
                "track_first_touch": True,
                "track_fill_percentage": True,
                "full_fill_percentage": 1.0,
                "invalidate_on_full_fill": False,
            },
            "retest": {
                "enabled": True,
                "require_close_hold": True,
                "maximum_bars_after_creation": 20,
            },
            "inverse_fvg": {
                "enabled": True,
                "require_close_through_original_fvg": True,
            },
            "production": {
                "atr_period": 14,
            },
        },
    }


def _bullish_gap_frame(
    *,
    timeframe: str = "5m",
) -> pd.DataFrame:
    minutes = {
        "5m": 5,
        "15m": 15,
    }[timeframe]

    timestamps = pd.date_range(
        "2026-09-01 13:30:00",
        periods=5,
        freq=f"{minutes}min",
        tz="UTC",
    )

    dataframe = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [
                99.5,
                100.0,
                101.2,
                101.5,
                100.5,
            ],
            "high": [
                100.0,
                100.5,
                102.0,
                102.0,
                102.0,
            ],
            "low": [
                99.0,
                99.5,
                101.0,
                100.5,
                99.5,
            ],
            "close": [
                99.5,
                100.0,
                101.5,
                101.0,
                99.75,
            ],
            "volume": [
                10.0,
                10.0,
                20.0,
                15.0,
                25.0,
            ],
            f"atr_{timeframe}": [
                2.0,
                2.0,
                2.0,
                2.0,
                2.0,
            ],
            "bar_complete": [
                True,
                True,
                True,
                True,
                True,
            ],
        }
    )

    dataframe["available_at"] = (
        dataframe["timestamp"]
        + pd.Timedelta(
            minutes=minutes
        )
    )

    return dataframe


def test_fvg_state_rejects_naive_timestamp():
    dataframe = _bullish_gap_frame()

    dataframe["timestamp"] = (
        dataframe["timestamp"]
        .dt.tz_localize(None)
    )

    with pytest.raises(
        Exception,
        match="timezone-aware",
    ):
        build_fvg_objects(
            dataframe,
            _config(),
            timeframe="5m",
        )


def test_objects_expose_timeframe_and_atr_relative_size():
    objects = build_fvg_objects(
        _bullish_gap_frame(),
        _config(),
        timeframe="5m",
    )

    assert len(objects) == 1

    row = objects.iloc[0]

    assert row["timeframe"] == "5m"
    assert row["size_points"] == pytest.approx(
        1.0
    )

    assert row["size_atr"] == pytest.approx(
        0.5
    )

    assert pd.notna(
        row["available_at"]
    )


def test_mitigation_and_full_fill_are_exposed():
    objects = build_fvg_objects(
        _bullish_gap_frame(),
        _config(),
        timeframe="5m",
    )

    row = objects.iloc[0]

    assert row[
        "maximum_fill_percentage"
    ] == pytest.approx(
        1.0
    )

    assert row[
        "mitigation_percentage"
    ] == pytest.approx(
        100.0
    )

    assert bool(
        row["fully_filled"]
    )


def test_ifvg_conversion_invalidates_original_gap():
    objects = build_fvg_objects(
        _bullish_gap_frame(),
        _config(),
        timeframe="5m",
    )

    row = objects.iloc[0]

    assert bool(
        row["inverse_fvg_created"]
    )

    assert bool(
        row["invalidated"]
    )

    assert pd.notna(
        row["inverse_fvg_time"]
    )


def test_gap_preserves_sweep_displacement_structure_associations():
    dataframe = _bullish_gap_frame()

    dataframe[
        "liquidity_sweep_any"
    ] = False

    dataframe[
        "displacement_score"
    ] = 0.0

    dataframe[
        "displacement_category"
    ] = "none"

    dataframe[
        "displacement_direction"
    ] = "neutral"

    dataframe[
        "bullish_mss"
    ] = False

    dataframe.loc[
        2,
        "liquidity_sweep_any",
    ] = True

    dataframe.loc[
        2,
        "displacement_score",
    ] = 82.0

    dataframe.loc[
        2,
        "displacement_category",
    ] = "strong"

    dataframe.loc[
        2,
        "displacement_direction",
    ] = "bullish"

    dataframe.loc[
        2,
        "bullish_mss",
    ] = True

    objects = build_fvg_objects(
        dataframe,
        _config(),
        timeframe="5m",
    )

    row = objects.iloc[0]

    assert bool(
        row["sweep_context"]
    )

    assert row[
        "displacement_score"
    ] == pytest.approx(
        82.0
    )

    assert (
        row[
            "displacement_category"
        ]
        == "strong"
    )

    assert (
        row[
            "structure_context"
        ]
        == "bullish_mss"
    )


def test_multitimeframe_objects_exclude_incomplete_bars():
    five = _bullish_gap_frame(
        timeframe="5m"
    )

    fifteen = _bullish_gap_frame(
        timeframe="15m"
    )

    fifteen.loc[
        2:,
        "bar_complete",
    ] = False

    objects = (
        build_multitimeframe_fvg_objects(
            {
                "5m": five,
                "15m": fifteen,
            },
            _config(),
        )
    )

    assert (
        objects["timeframe"]
        == "5m"
    ).all()


def test_state_as_of_does_not_leak_future_invalidation():
    objects = build_fvg_objects(
        _bullish_gap_frame(),
        _config(),
        timeframe="5m",
    )

    creation_available = pd.Timestamp(
        objects.iloc[
            0
        ]["available_at"]
    )

    early = materialize_fvg_state_as_of(
        objects,
        as_of=creation_available,
    )

    assert len(early) == 1

    assert early.iloc[
        0
    ]["state_as_of"] == "active"

    assert early.iloc[
        0
    ][
        "mitigation_percentage_as_of"
    ] == pytest.approx(
        0.0
    )

    late = materialize_fvg_state_as_of(
        objects,
        as_of=pd.Timestamp(
            "2026-09-01 14:00:00+00:00"
        ),
    )

    assert late.iloc[
        0
    ]["state_as_of"] == "ifvg"


def test_nearest_5m_fvg_above():
    dataframe = (
        _bullish_gap_frame()
        .iloc[:3]
        .copy()
    )

    objects = build_fvg_objects(
        dataframe,
        _config(),
        timeframe="5m",
    )

    snapshot = nearest_fvg_snapshot(
        objects,
        price=99.5,
        as_of=pd.Timestamp(
            "2026-09-01 13:45:00+00:00"
        ),
    )

    assert snapshot[
        "nearest_5m_fvg_above"
    ] == pytest.approx(
        100.0
    )

    assert snapshot[
        "distance_to_nearest_5m_fvg_above"
    ] == pytest.approx(
        0.5
    )


def test_nearest_htf_fvg_above():
    fifteen = (
        _bullish_gap_frame(
            timeframe="15m"
        )
        .iloc[:3]
        .copy()
    )

    fifteen[
        "high"
    ] = [
        110.0,
        110.5,
        113.0,
    ]

    fifteen[
        "low"
    ] = [
        109.0,
        109.5,
        112.0,
    ]

    fifteen[
        "open"
    ] = [
        109.5,
        110.0,
        112.2,
    ]

    fifteen[
        "close"
    ] = [
        109.5,
        110.0,
        112.5,
    ]

    objects = build_fvg_objects(
        fifteen,
        _config(),
        timeframe="15m",
    )

    snapshot = nearest_fvg_snapshot(
        objects,
        price=100.0,
        as_of=pd.Timestamp(
            "2026-09-01 14:15:00+00:00"
        ),
    )

    assert snapshot[
        "nearest_htf_fvg_above"
    ] == pytest.approx(
        110.0
    )

    assert snapshot[
        "distance_to_nearest_htf_fvg_above"
    ] == pytest.approx(
        10.0
    )


def test_future_mutation_does_not_rewrite_creation_metadata():
    original = _bullish_gap_frame()

    prefix = (
        original
        .iloc[:3]
        .copy()
    )

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

    first = build_fvg_objects(
        prefix,
        _config(),
        timeframe="5m",
    )

    second = build_fvg_objects(
        changed,
        _config(),
        timeframe="5m",
    )

    columns = [
        "direction",
        "timeframe",
        "creation_time",
        "available_at",
        "lower_bound",
        "upper_bound",
        "midpoint",
        "size_points",
        "size_atr",
    ]

    pd.testing.assert_series_equal(
        first.iloc[0][columns],
        second.iloc[0][columns],
        check_names=False,
    )


def test_fast_lifecycle_preserves_legacy_terminal_behavior():
    dataframe = _bullish_gap_frame()

    settings = build_fvg_settings(
        _config()
    )

    created = detect_fvg_creation(
        dataframe,
        settings=settings,
        atr_column="atr_5m",
    )

    table = build_fvg_table(
        created
    )

    legacy = track_fvg_lifecycle(
        created,
        table,
        settings=settings,
    )

    fast = track_fvg_lifecycle_fast(
        created,
        table,
        settings=settings,
        timeframe="5m",
    )

    assert fast[
        "maximum_fill_percentage"
    ].tolist() == pytest.approx(
        legacy[
            "maximum_fill_percentage"
        ].tolist()
    )

    assert fast[
        "invalidated"
    ].tolist() == legacy[
        "invalidated"
    ].tolist()

    assert fast[
        "inverse_fvg_created"
    ].tolist() == legacy[
        "inverse_fvg_created"
    ].tolist()


def test_exact_output_regression_fixture():
    fixture_path = Path(
        "tests/fixtures/fvg_state_expected.json"
    )

    expected = json.loads(
        fixture_path.read_text()
    )

    objects = build_fvg_objects(
        _bullish_gap_frame(),
        _config(),
        timeframe="5m",
    )

    row = objects.iloc[0]

    actual = {
        "direction": row[
            "direction"
        ],
        "timeframe": row[
            "timeframe"
        ],
        "lower_bound": float(
            row["lower_bound"]
        ),
        "upper_bound": float(
            row["upper_bound"]
        ),
        "size_points": float(
            row["size_points"]
        ),
        "size_atr": float(
            row["size_atr"]
        ),
        "maximum_fill_percentage": float(
            row[
                "maximum_fill_percentage"
            ]
        ),
        "mitigation_percentage": float(
            row[
                "mitigation_percentage"
            ]
        ),
        "fully_filled": bool(
            row["fully_filled"]
        ),
        "inverse_fvg_created": bool(
            row[
                "inverse_fvg_created"
            ]
        ),
        "invalidated": bool(
            row["invalidated"]
        ),
    }

    assert actual == expected
