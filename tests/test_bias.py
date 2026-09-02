from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from bias import (
    BiasError,
    _merge_completed_bias_features,
    calculate_timeframe_bias,
    combine_htf_bias,
    enrich_htf_bias,
)


def _config(*, timeframes=None, left=1, right=1, buffer=0.0) -> dict:
    return {
        "higher_timeframe_bias": {
            "enabled": True,
            "timeframes": timeframes or ["1h"],
            "structure": {
                "left_bars": left,
                "right_bars": right,
                "break_buffer_points": buffer,
            },
        },
        "structure": {
            "break_buffer_points": buffer,
        },
    }


def _bars(
    highs,
    lows,
    closes,
    *,
    start="2026-08-31 13:00:00",
    freq="1h",
    complete=True,
) -> pd.DataFrame:
    timestamps = pd.date_range(start, periods=len(closes), freq=freq, tz="UTC")
    closes = np.asarray(closes, dtype=float)
    highs = np.asarray(highs, dtype=float)
    lows = np.asarray(lows, dtype=float)
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": closes,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": 100.0,
            "bar_complete": complete,
            "available_at": timestamps + pd.Timedelta(hours=1),
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


def test_timeframe_bias_rejects_naive_timestamps():
    bars = _bars(
        [10, 12, 11],
        [8, 9, 8.5],
        [9, 11, 10],
    )
    bars["timestamp"] = bars["timestamp"].dt.tz_localize(None)

    with pytest.raises(BiasError, match="timezone-aware"):
        calculate_timeframe_bias(
            bars,
            timeframe="1h",
            config=_config(),
        )


def test_bullish_break_uses_confirmed_swing_and_then_carries_state():
    bars = _bars(
        highs=[10, 12, 11, 13, 13.5],
        lows=[8, 9, 8.5, 9.5, 10],
        closes=[9, 11, 10, 12.5, 13],
    )

    result = calculate_timeframe_bias(
        bars,
        timeframe="1h",
        config=_config(),
    )

    assert result.loc[2, "bias_1h"] == "neutral"
    assert result.loc[3, "bias_event_1h"] == "bullish_break"
    assert result.loc[3, "bias_1h"] == "bullish"
    assert result.loc[4, "bias_1h"] == "bullish"
    assert result.loc[3, "confirmed_swing_high_1h"] == pytest.approx(12.0)


def test_bearish_break_can_change_existing_bullish_state():
    bars = _bars(
        highs=[10, 12, 11, 13, 12, 11, 10, 9],
        lows=[8, 9, 8.5, 9.5, 8, 9, 7, 6],
        closes=[9, 11, 10, 12.5, 10, 9.5, 7.5, 6.5],
    )

    result = calculate_timeframe_bias(
        bars,
        timeframe="1h",
        config=_config(),
    )

    assert "bullish" in result["bias_1h"].tolist()
    assert result.iloc[-1]["bias_1h"] == "bearish"
    assert "bearish_break" in result["bias_event_1h"].tolist()


def test_bias_is_hidden_before_available_at_and_visible_exactly_at_close():
    base = _base_at(
        "2026-08-31 13:59:00+00:00",
        "2026-08-31 14:00:00+00:00",
    )
    higher = pd.DataFrame(
        {
            "available_at": pd.to_datetime(
                ["2026-08-31 14:00:00+00:00"], utc=True
            ),
            "bar_complete": [True],
            "bias_1h": ["bullish"],
            "bias_event_1h": ["bullish_break"],
            "confirmed_swing_high_1h": [101.0],
            "confirmed_swing_low_1h": [95.0],
        }
    )

    merged = _merge_completed_bias_features(base, higher, "1h")

    assert pd.isna(merged.loc[0, "bias_1h"])
    assert merged.loc[1, "bias_1h"] == "bullish"


def test_incomplete_higher_timeframe_bias_is_never_merged():
    base = _base_at(
        "2026-08-31 14:00:00+00:00",
        "2026-08-31 14:01:00+00:00",
    )
    higher = pd.DataFrame(
        {
            "available_at": pd.to_datetime(
                ["2026-08-31 14:00:00+00:00"], utc=True
            ),
            "bar_complete": [False],
            "bias_1h": ["bullish"],
        }
    )

    merged = _merge_completed_bias_features(base, higher, "1h")

    assert merged["bias_1h"].isna().all()


def test_conflicting_directional_timeframes_produce_neutral_bias():
    df = pd.DataFrame(
        {
            "bias_1h": ["bullish", "bullish", "neutral"],
            "bias_4h": ["bullish", "bearish", "neutral"],
            "bias_1d": ["neutral", "neutral", "neutral"],
        }
    )

    result = combine_htf_bias(
        df,
        timeframes=["1h", "4h", "1d"],
    )

    assert result.loc[0, "htf_bias"] == "bullish"
    assert result.loc[0, "htf_bias_confidence"] == pytest.approx(2 / 3)
    assert bool(result.loc[0, "htf_bias_conflict"]) is False

    assert result.loc[1, "htf_bias"] == "neutral"
    assert result.loc[1, "htf_bias_confidence"] == pytest.approx(0.0)
    assert bool(result.loc[1, "htf_bias_conflict"]) is True

    assert result.loc[2, "htf_bias"] == "neutral"
    assert result.loc[2, "htf_bias_known_count"] == 3


def test_future_bars_do_not_rewrite_past_timeframe_bias():
    original = _bars(
        highs=[10, 12, 11, 13, 12, 14, 13, 15, 14, 16],
        lows=[8, 9, 8.5, 9.5, 9, 10, 9.5, 11, 10, 12],
        closes=[9, 11, 10, 12.5, 11, 13.5, 12, 14.5, 13, 15.5],
    )
    mutated = original.copy()

    mutated.loc[8:, ["open", "high", "low", "close"]] += 500.0

    before = calculate_timeframe_bias(
        original,
        timeframe="1h",
        config=_config(),
    )
    after = calculate_timeframe_bias(
        mutated,
        timeframe="1h",
        config=_config(),
    )

    feature_columns = [
        "bias_1h",
        "bias_event_1h",
        "confirmed_swing_high_1h",
        "confirmed_swing_low_1h",
    ]

    pd.testing.assert_frame_equal(
        before.loc[:7, feature_columns],
        after.loc[:7, feature_columns],
        check_dtype=True,
    )


def test_enrich_htf_bias_creates_raw_bias_fields_for_scorer():
    one_minute = _base_at(
        "2026-08-31 15:59:00+00:00",
        "2026-08-31 16:00:00+00:00",
        "2026-08-31 16:01:00+00:00",
        "2026-08-31 16:02:00+00:00",
    )

    hourly = _bars(
        highs=[10, 12, 11],
        lows=[8, 9, 8.5],
        closes=[9, 11, 10],
        start="2026-08-31 13:00:00",
    )

    enriched = enrich_htf_bias(
        one_minute,
        {"1h": SimpleNamespace(dataframe=hourly)},
        _config(timeframes=["1h"]),
    )

    assert "bias_1h" in enriched.columns
    assert "htf_bias" in enriched.columns
    assert "higher_timeframe_bias" in enriched.columns
    assert "htf_bias_confidence" in enriched.columns
    assert enriched["higher_timeframe_bias"].equals(enriched["htf_bias"])
