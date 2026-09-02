from __future__ import annotations

import pandas as pd

from data_clock import filter_as_of
from resample import generate_standard_timeframes, resample_timeframe


def _bars(start: str, periods: int) -> pd.DataFrame:
    timestamps = pd.date_range(start=start, periods=periods, freq="1min", tz="UTC")
    base = pd.Series(range(periods), dtype="float64")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": 100.0 + base,
            "high": 101.0 + base,
            "low": 99.0 + base,
            "close": 100.5 + base,
            "volume": 10 + base,
            "source": "TEST",
            "symbol": "MNQ",
            "contract": "MNQU6",
        }
    )


def test_standard_timeframes_include_2m_and_3m() -> None:
    results = generate_standard_timeframes(_bars("2026-06-01T08:57:00Z", 6))

    assert "2m" in results
    assert "3m" in results


def test_2m_aggregates_ohlcv_and_sets_availability() -> None:
    result = resample_timeframe(_bars("2026-06-01T08:58:00Z", 4), "2m")
    bars = result.dataframe

    assert len(bars) == 2
    first = bars.iloc[0]
    assert first["timestamp"] == pd.Timestamp("2026-06-01T08:58:00Z")
    assert first["available_at"] == pd.Timestamp("2026-06-01T09:00:00Z")
    assert first["bar_count"] == 2
    assert bool(first["bar_complete"]) is True
    assert first["open"] == 100.0
    assert first["high"] == 102.0
    assert first["low"] == 99.0
    assert first["close"] == 101.5
    assert first["volume"] == 21.0


def test_3m_aggregates_ohlcv_and_sets_availability() -> None:
    result = resample_timeframe(_bars("2026-06-01T08:57:00Z", 6), "3m")
    bars = result.dataframe

    assert len(bars) == 2
    first = bars.iloc[0]
    assert first["timestamp"] == pd.Timestamp("2026-06-01T08:57:00Z")
    assert first["available_at"] == pd.Timestamp("2026-06-01T09:00:00Z")
    assert first["bar_count"] == 3
    assert bool(first["bar_complete"]) is True
    assert first["open"] == 100.0
    assert first["high"] == 103.0
    assert first["low"] == 99.0
    assert first["close"] == 102.5
    assert first["volume"] == 33.0


def test_partial_2m_and_3m_bars_are_incomplete() -> None:
    two_minute = resample_timeframe(_bars("2026-06-01T08:58:00Z", 3), "2m")
    three_minute = resample_timeframe(_bars("2026-06-01T08:57:00Z", 5), "3m")

    assert bool(two_minute.dataframe.iloc[-1]["bar_complete"]) is False
    assert two_minute.incomplete_bars == 1
    assert bool(three_minute.dataframe.iloc[-1]["bar_complete"]) is False
    assert three_minute.incomplete_bars == 1


def test_as_of_0900_exposes_only_completed_2m_bar() -> None:
    result = resample_timeframe(_bars("2026-06-01T08:58:00Z", 4), "2m")

    visible = filter_as_of(result.dataframe, as_of="2026-06-01T09:00:00Z")

    assert visible["timestamp"].tolist() == [pd.Timestamp("2026-06-01T08:58:00Z")]
    assert visible["available_at"].tolist() == [pd.Timestamp("2026-06-01T09:00:00Z")]


def test_as_of_0900_exposes_only_completed_3m_bar() -> None:
    result = resample_timeframe(_bars("2026-06-01T08:57:00Z", 6), "3m")

    visible = filter_as_of(result.dataframe, as_of="2026-06-01T09:00:00Z")

    assert visible["timestamp"].tolist() == [pd.Timestamp("2026-06-01T08:57:00Z")]
    assert visible["available_at"].tolist() == [pd.Timestamp("2026-06-01T09:00:00Z")]


def test_incomplete_short_timeframe_bar_stays_hidden_even_after_nominal_close() -> None:
    result = resample_timeframe(_bars("2026-06-01T08:57:00Z", 2), "3m")

    visible = filter_as_of(result.dataframe, as_of="2026-06-01T09:01:00Z")

    assert visible.empty
