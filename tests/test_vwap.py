from __future__ import annotations

import pandas as pd
import pytest

from vwap import (
    VWAPError,
    enrich_vwap,
)


def _config() -> dict:
    return {
        "vwap": {
            "enabled": True,
            "timezone": "America/New_York",
            "reset_time_et": "18:00",
            "slope_bars": 2,
        }
    }


def _bars(
    *,
    timestamps=None,
    opens=None,
    highs=None,
    lows=None,
    closes=None,
    volumes=None,
) -> pd.DataFrame:
    if timestamps is None:
        timestamps = pd.date_range(
            "2026-09-01 22:00:00",
            periods=5,
            freq="1min",
            tz="UTC",
        )

    n = len(timestamps)

    opens = opens or [100.0] * n
    highs = highs or [101.0] * n
    lows = lows or [99.0] * n
    closes = closes or [100.0] * n
    volumes = volumes or [10.0] * n

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        }
    )


def test_vwap_rejects_naive_timestamps():
    dataframe = _bars()
    dataframe["timestamp"] = (
        dataframe["timestamp"]
        .dt.tz_localize(None)
    )

    with pytest.raises(
        VWAPError,
        match="timezone-aware",
    ):
        enrich_vwap(
            dataframe,
            _config(),
        )


def test_vwap_uses_typical_price_and_volume_weighting():
    dataframe = _bars(
        timestamps=pd.date_range(
            "2026-09-01 22:00",
            periods=2,
            freq="1min",
            tz="UTC",
        ),
        highs=[102.0, 106.0],
        lows=[98.0, 100.0],
        closes=[101.0, 105.0],
        volumes=[10.0, 30.0],
    )

    result = enrich_vwap(
        dataframe,
        _config(),
    )

    typical_1 = (
        102.0 + 98.0 + 101.0
    ) / 3.0

    typical_2 = (
        106.0 + 100.0 + 105.0
    ) / 3.0

    expected = (
        typical_1 * 10.0
        + typical_2 * 30.0
    ) / 40.0

    assert (
        result.loc[1, "vwap"]
        == pytest.approx(expected)
    )


def test_vwap_resets_at_configured_et_session_boundary():
    timestamps_et = pd.DatetimeIndex(
        [
            "2026-09-01 16:59:00",
            "2026-09-01 18:00:00",
        ]
    ).tz_localize(
        "America/New_York"
    )

    timestamps = timestamps_et.tz_convert(
        "UTC"
    )

    dataframe = _bars(
        timestamps=timestamps,
        highs=[102.0, 202.0],
        lows=[98.0, 198.0],
        closes=[100.0, 200.0],
        volumes=[100.0, 100.0],
    )

    result = enrich_vwap(
        dataframe,
        _config(),
    )

    assert (
        result.loc[
            0,
            "vwap_session_anchor",
        ]
        != result.loc[
            1,
            "vwap_session_anchor",
        ]
    )

    assert (
        result.loc[0, "vwap"]
        == pytest.approx(100.0)
    )

    assert (
        result.loc[1, "vwap"]
        == pytest.approx(200.0)
    )


def test_vwap_exposes_distance_and_position():
    dataframe = _bars(
        highs=[102.0] * 5,
        lows=[98.0] * 5,
        closes=[101.0] * 5,
    )

    result = enrich_vwap(
        dataframe,
        _config(),
    )

    assert result.loc[
        0,
        "vwap_position",
    ] == "above"

    assert (
        result.loc[
            0,
            "vwap_distance_points",
        ]
        > 0
    )


def test_vwap_detects_recent_cross_causally():
    dataframe = _bars(
        timestamps=pd.date_range(
            "2026-09-01 22:00",
            periods=2,
            freq="1min",
            tz="UTC",
        ),
        opens=[100.0, 99.0],
        highs=[102.0, 103.0],
        lows=[98.0, 99.0],
        closes=[99.0, 103.0],
        volumes=[10.0, 10.0],
    )

    result = enrich_vwap(
        dataframe,
        _config(),
    )

    assert (
        result.loc[
            0,
            "vwap_position",
        ]
        == "below"
    )

    assert bool(
        result.loc[
            1,
            "vwap_bullish_cross",
        ]
    )


def test_vwap_slope_uses_only_prior_vwap_values():
    dataframe = _bars(
        closes=[
            100.0,
            101.0,
            102.0,
            103.0,
            104.0,
        ],
        highs=[
            101.0,
            102.0,
            103.0,
            104.0,
            105.0,
        ],
        lows=[
            99.0,
            100.0,
            101.0,
            102.0,
            103.0,
        ],
    )

    result = enrich_vwap(
        dataframe,
        _config(),
    )

    assert (
        result.loc[
            2,
            "vwap_slope_points_per_bar",
        ]
        > 0
    )

    assert (
        result.loc[
            2,
            "vwap_slope_direction",
        ]
        == "rising"
    )


def test_zero_volume_does_not_create_invalid_vwap():
    dataframe = _bars(
        timestamps=pd.date_range(
            "2026-09-01 22:00",
            periods=2,
            freq="1min",
            tz="UTC",
        ),
        highs=[101.0, 102.0],
        lows=[99.0, 100.0],
        closes=[100.0, 101.0],
        volumes=[0.0, 10.0],
    )

    result = enrich_vwap(
        dataframe,
        _config(),
    )

    assert pd.isna(
        result.loc[0, "vwap"]
    )

    assert pd.notna(
        result.loc[1, "vwap"]
    )


def test_future_mutation_does_not_rewrite_past_vwap():
    original = _bars()

    changed = original.copy()

    changed.loc[4, "high"] = 1000.0
    changed.loc[4, "low"] = 1.0
    changed.loc[4, "close"] = 900.0
    changed.loc[4, "volume"] = 999999.0

    before = enrich_vwap(
        original,
        _config(),
    )

    after = enrich_vwap(
        changed,
        _config(),
    )

    columns = [
        "vwap",
        "vwap_distance_points",
        "vwap_position",
        "vwap_bullish_cross",
        "vwap_bearish_cross",
        "vwap_slope_points_per_bar",
    ]

    pd.testing.assert_frame_equal(
        before.loc[:3, columns],
        after.loc[:3, columns],
        check_dtype=True,
    )
