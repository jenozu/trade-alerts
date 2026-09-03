"""Completed-bar visibility and ``available_at`` tests for every longer
intraday timeframe (15m/30m/1h/4h), extending the 1m/2m/3m/5m evidence in
test_resample_short_timeframes.py to the full intraday matrix (Phase 2 R3/R4).

Contract under test:
- A bucket containing exactly its required constituent minutes is complete and
  available at ``bucket_open + duration``.
- A partial bucket (missing any constituent minute) is incomplete and stays
  hidden even after its nominal ``available_at`` has passed.
- ``filter_as_of`` at the exact completion instant exposes only complete bars.
"""

from __future__ import annotations

import pandas as pd
import pytest

from data_clock import filter_as_of
from resample import resample_timeframe

CASES = [
    ("15m", 15, pd.Timedelta(minutes=15)),
    ("30m", 30, pd.Timedelta(minutes=30)),
    ("1h", 60, pd.Timedelta(hours=1)),
    ("4h", 240, pd.Timedelta(hours=4)),
]


def _bars(periods: int) -> pd.DataFrame:
    # UTC-aligned so every intraday bucket below starts on a clean boundary.
    timestamps = pd.date_range(
        start="2026-06-01T08:00:00Z", periods=periods, freq="1min"
    )
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


@pytest.mark.parametrize("timeframe,expected_count,duration", CASES)
def test_full_bucket_is_complete_and_available_at_open_plus_duration(
    timeframe, expected_count, duration
) -> None:
    result = resample_timeframe(_bars(expected_count), timeframe)
    bars = result.dataframe

    assert len(bars) == 1
    first = bars.iloc[0]
    assert first["timestamp"] == pd.Timestamp("2026-06-01T08:00:00Z")
    assert first["available_at"] == pd.Timestamp("2026-06-01T08:00:00Z") + duration
    assert first["bar_count"] == expected_count
    assert bool(first["bar_complete"]) is True
    assert result.incomplete_bars == 0


@pytest.mark.parametrize("timeframe,expected_count,duration", CASES)
def test_partial_bucket_is_incomplete_and_stays_hidden_past_nominal_availability(
    timeframe, expected_count, duration
) -> None:
    result = resample_timeframe(_bars(expected_count - 1), timeframe)

    last = result.dataframe.iloc[-1]
    assert bool(last["bar_complete"]) is False
    assert result.incomplete_bars == 1

    # Even after the nominal completion time, the incomplete bucket is not a
    # production input.
    nominal_completion = pd.Timestamp("2026-06-01T08:00:00Z") + duration
    visible = filter_as_of(
        result.dataframe, as_of=nominal_completion + pd.Timedelta(minutes=1)
    )
    assert visible.empty


@pytest.mark.parametrize("timeframe,expected_count,duration", CASES)
def test_as_of_at_exact_completion_exposes_only_the_complete_bucket(
    timeframe, expected_count, duration
) -> None:
    result = resample_timeframe(_bars(expected_count + 2), timeframe)

    # The second bucket is partial (2 minutes of a new bucket) and must not be
    # visible at the first bucket's completion instant.
    visible = filter_as_of(
        result.dataframe,
        as_of=pd.Timestamp("2026-06-01T08:00:00Z") + duration,
    )

    assert len(visible) == 1
    assert visible.iloc[0]["timestamp"] == pd.Timestamp("2026-06-01T08:00:00Z")
    assert bool(visible.iloc[0]["bar_complete"]) is True
