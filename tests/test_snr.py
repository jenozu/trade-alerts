from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from resample import resample_timeframe
from snr import (
    SNRError,
    _merge_completed_features,
    build_multitimeframe_snr,
    calculate_snr_features,
)


def _config() -> dict:
    # Small research windows keep the synthetic fixtures compact while testing
    # the same causal mechanics used by the production configuration.
    return {
        "snr": {
            "timeframes": {
                "1m": {"lookback_bars": 1, "atr_period": 1, "slope_bars": 1},
                "5m": {"lookback_bars": 1, "atr_period": 1, "slope_bars": 1},
                "15m": {"lookback_bars": 1, "atr_period": 1, "slope_bars": 1},
            }
        }
    }


def _minute_bars(
    start: str = "2026-08-31 13:30:00",
    periods: int = 31,
) -> pd.DataFrame:
    timestamps = pd.date_range(start, periods=periods, freq="1min", tz="UTC")
    close = 100.0 + np.arange(periods, dtype=float)
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": close - 0.25,
            "high": close + 0.50,
            "low": close - 0.50,
            "close": close,
            "volume": np.full(periods, 100.0),
        }
    )


def _base_at(*timestamps: str) -> pd.DataFrame:
    ts = pd.to_datetime(list(timestamps), utc=True)
    close = np.arange(len(ts), dtype=float) + 100.0
    return pd.DataFrame(
        {
            "timestamp": ts,
            "open": close,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 100.0,
        }
    )


def _higher_feature_row(
    *,
    timeframe: str,
    timestamp: str,
    available_at: str,
    value: float,
    complete: bool = True,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime([timestamp], utc=True),
            "available_at": pd.to_datetime([available_at], utc=True),
            "bar_complete": [complete],
            f"snr_{timeframe}": [value],
            f"snr_direction_{timeframe}": ["bullish"],
            f"snr_delta_{timeframe}": [0.1],
            f"snr_slope_{timeframe}": [0.1],
            f"efficiency_{timeframe}": [0.8],
            f"atr_{timeframe}": [2.0],
        }
    )


def test_snr_rejects_naive_timestamps():
    bars = _minute_bars(periods=5)
    bars["timestamp"] = bars["timestamp"].dt.tz_localize(None)

    with pytest.raises(SNRError, match="timezone-aware"):
        calculate_snr_features(bars, timeframe="1m", config=_config())


def test_5m_feature_is_hidden_before_bar_available_at_and_visible_exactly_at_close():
    base = _base_at(
        "2026-08-31 13:34:00+00:00",
        "2026-08-31 13:35:00+00:00",
    )
    higher = _higher_feature_row(
        timeframe="5m",
        timestamp="2026-08-31 13:30:00+00:00",
        available_at="2026-08-31 13:35:00+00:00",
        value=1.25,
    )

    merged = _merge_completed_features(base, higher, "5m")

    assert pd.isna(merged.loc[0, "snr_5m"])
    assert merged.loc[1, "snr_5m"] == pytest.approx(1.25)


def test_15m_feature_is_hidden_before_bar_available_at_and_visible_exactly_at_close():
    base = _base_at(
        "2026-08-31 13:44:00+00:00",
        "2026-08-31 13:45:00+00:00",
    )
    higher = _higher_feature_row(
        timeframe="15m",
        timestamp="2026-08-31 13:30:00+00:00",
        available_at="2026-08-31 13:45:00+00:00",
        value=1.75,
    )

    merged = _merge_completed_features(base, higher, "15m")

    assert pd.isna(merged.loc[0, "snr_15m"])
    assert merged.loc[1, "snr_15m"] == pytest.approx(1.75)


def test_incomplete_higher_timeframe_bar_is_never_merged():
    base = _base_at(
        "2026-08-31 13:35:00+00:00",
        "2026-08-31 13:36:00+00:00",
    )
    higher = _higher_feature_row(
        timeframe="5m",
        timestamp="2026-08-31 13:30:00+00:00",
        available_at="2026-08-31 13:35:00+00:00",
        value=999.0,
        complete=False,
    )

    merged = _merge_completed_features(base, higher, "5m")

    assert merged["snr_5m"].isna().all()


def test_explicit_available_at_is_respected_instead_of_assuming_nominal_close():
    base = _base_at(
        "2026-08-31 13:35:00+00:00",
        "2026-08-31 13:36:00+00:00",
        "2026-08-31 13:37:00+00:00",
    )
    higher = _higher_feature_row(
        timeframe="5m",
        timestamp="2026-08-31 13:30:00+00:00",
        available_at="2026-08-31 13:37:00+00:00",
        value=2.0,
    )

    merged = _merge_completed_features(base, higher, "5m")

    assert merged.loc[:1, "snr_5m"].isna().all()
    assert merged.loc[2, "snr_5m"] == pytest.approx(2.0)


def test_resampled_5m_snr_does_not_appear_until_the_source_bar_is_complete():
    one_minute = _minute_bars(periods=31)
    five = resample_timeframe(one_minute, "5m").dataframe
    fifteen = resample_timeframe(one_minute, "15m").dataframe

    merged = build_multitimeframe_snr(one_minute, five, fifteen, _config())
    by_time = merged.set_index("timestamp")

    # With lookback=1 the first non-null 5m SNR belongs to the 13:35 bar,
    # which spans 13:35-13:40 and therefore cannot be known at 13:39.
    assert pd.isna(by_time.loc[pd.Timestamp("2026-08-31 13:39:00+00:00"), "snr_5m"])
    assert pd.notna(by_time.loc[pd.Timestamp("2026-08-31 13:40:00+00:00"), "snr_5m"])


def test_resampled_15m_snr_does_not_appear_until_the_source_bar_is_complete():
    one_minute = _minute_bars(periods=31)
    five = resample_timeframe(one_minute, "5m").dataframe
    fifteen = resample_timeframe(one_minute, "15m").dataframe

    merged = build_multitimeframe_snr(one_minute, five, fifteen, _config())
    by_time = merged.set_index("timestamp")

    # With lookback=1 the first non-null 15m SNR belongs to the 13:45 bar,
    # which spans 13:45-14:00 and is only available at 14:00.
    assert pd.isna(by_time.loc[pd.Timestamp("2026-08-31 13:59:00+00:00"), "snr_15m"])
    assert pd.notna(by_time.loc[pd.Timestamp("2026-08-31 14:00:00+00:00"), "snr_15m"])


def test_future_price_changes_do_not_rewrite_past_snr_features():
    original = _minute_bars(periods=20)
    mutated = original.copy()

    # Change only bars that occur after the comparison cutoff.
    mutated.loc[15:, ["open", "high", "low", "close"]] += 500.0

    before = calculate_snr_features(original, timeframe="1m", config=_config())
    after = calculate_snr_features(mutated, timeframe="1m", config=_config())

    feature_columns = [
        "atr_1m",
        "snr_1m",
        "snr_direction_1m",
        "snr_delta_1m",
        "snr_slope_1m",
        "efficiency_1m",
    ]

    pd.testing.assert_frame_equal(
        before.loc[:14, feature_columns],
        after.loc[:14, feature_columns],
        check_dtype=True,
    )
