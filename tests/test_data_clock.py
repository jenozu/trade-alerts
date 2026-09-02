from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pytest

from src.data_clock import (
    DataClockError,
    filter_as_of,
    filter_resampled_results_as_of,
    normalize_as_of,
    summarize_as_of,
)


def _bars(start: str, periods: int) -> pd.DataFrame:
    timestamps = pd.date_range(start, periods=periods, freq="1min", tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": range(periods),
            "high": [value + 1 for value in range(periods)],
            "low": range(periods),
            "close": [value + 0.5 for value in range(periods)],
            "volume": [10] * periods,
        }
    )


def test_normalize_as_of_requires_explicit_timezone() -> None:
    with pytest.raises(DataClockError, match="timezone-aware"):
        normalize_as_of("2026-09-02 09:00:00")


def test_normalize_as_of_converts_eastern_to_utc() -> None:
    result = normalize_as_of("2026-09-02T09:00:00-04:00")

    assert result == pd.Timestamp("2026-09-02T13:00:00Z")


def test_one_minute_bar_is_visible_only_after_it_completes() -> None:
    dataframe = _bars("2026-09-02T12:58:00Z", 4)

    visible = filter_as_of(
        dataframe,
        as_of="2026-09-02T13:00:00Z",
    )

    assert visible["timestamp"].tolist() == [
        pd.Timestamp("2026-09-02T12:58:00Z"),
        pd.Timestamp("2026-09-02T12:59:00Z"),
    ]
    assert pd.Timestamp("2026-09-02T13:00:00Z") not in set(visible["timestamp"])


def test_explicit_available_at_controls_visibility() -> None:
    dataframe = _bars("2026-09-02T12:55:00Z", 2)
    dataframe["available_at"] = pd.to_datetime(
        ["2026-09-02T13:00:00Z", "2026-09-02T13:05:00Z"], utc=True
    )

    visible = filter_as_of(
        dataframe,
        as_of="2026-09-02T13:00:00Z",
    )

    assert len(visible) == 1
    assert visible.loc[0, "timestamp"] == pd.Timestamp("2026-09-02T12:55:00Z")
    assert visible.loc[0, "available_at"] == pd.Timestamp("2026-09-02T13:00:00Z")


def test_incomplete_resampled_bar_is_hidden_even_if_available_at_has_arrived() -> None:
    dataframe = _bars("2026-09-02T12:55:00Z", 2)
    dataframe["available_at"] = pd.to_datetime(
        ["2026-09-02T13:00:00Z", "2026-09-02T13:00:00Z"], utc=True
    )
    dataframe["bar_complete"] = [True, False]

    visible = filter_as_of(
        dataframe,
        as_of="2026-09-02T13:00:00Z",
    )

    assert len(visible) == 1
    assert bool(visible.loc[0, "bar_complete"]) is True


def test_future_rows_cannot_change_historical_as_of_prefix() -> None:
    prefix = _bars("2026-09-02T12:50:00Z", 11)
    future = _bars("2026-09-02T13:01:00Z", 20)
    full = pd.concat([prefix, future], ignore_index=True)

    cutoff = "2026-09-02T13:00:00Z"
    from_prefix = filter_as_of(prefix, as_of=cutoff)
    from_full = filter_as_of(full, as_of=cutoff)

    pd.testing.assert_frame_equal(from_prefix, from_full)


def test_summary_reports_visible_and_hidden_rows() -> None:
    dataframe = _bars("2026-09-02T12:58:00Z", 4)

    summary = summarize_as_of(
        dataframe,
        as_of="2026-09-02T13:00:00Z",
    )

    assert summary.rows_in == 4
    assert summary.rows_visible == 2
    assert summary.rows_hidden == 2
    assert summary.last_visible_timestamp == pd.Timestamp("2026-09-02T12:59:00Z")
    assert summary.last_visible_available_at == pd.Timestamp("2026-09-02T13:00:00Z")


@dataclass(frozen=True)
class FakeResampleResult:
    timeframe: str
    dataframe: pd.DataFrame
    rows_in: int
    rows_out: int
    incomplete_bars: int


def test_resampled_results_use_explicit_available_at_and_preserve_result_type() -> None:
    dataframe = _bars("2026-09-02T12:50:00Z", 2)
    dataframe["available_at"] = pd.to_datetime(
        ["2026-09-02T13:00:00Z", "2026-09-02T13:05:00Z"], utc=True
    )
    dataframe["bar_complete"] = True

    original = FakeResampleResult(
        timeframe="5m",
        dataframe=dataframe,
        rows_in=10,
        rows_out=2,
        incomplete_bars=0,
    )

    filtered = filter_resampled_results_as_of(
        {"5m": original},
        as_of="2026-09-02T13:00:00Z",
    )["5m"]

    assert isinstance(filtered, FakeResampleResult)
    assert filtered.timeframe == "5m"
    assert filtered.rows_in == 10
    assert filtered.rows_out == 1
    assert filtered.incomplete_bars == 0
    assert filtered.dataframe.loc[0, "timestamp"] == pd.Timestamp(
        "2026-09-02T12:50:00Z"
    )
