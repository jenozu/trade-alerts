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


# ---------------------------------------------------------------------------
# Canonical as_of contract boundary tests (Phase 2 C1)
# ---------------------------------------------------------------------------


def test_row_is_visible_when_available_at_equals_as_of() -> None:
    dataframe = _bars("2026-09-02T12:58:00Z", 2)
    cutoff = "2026-09-02T13:00:00Z"

    at_cutoff = filter_as_of(dataframe, as_of=cutoff)
    # One microsecond before the cutoff the 12:59 bar (available_at 13:00:00)
    # must still be hidden.
    just_before = filter_as_of(
        dataframe, as_of="2026-09-02T12:59:59.999999Z"
    )

    assert at_cutoff["timestamp"].tolist() == [
        pd.Timestamp("2026-09-02T12:58:00Z"),
        pd.Timestamp("2026-09-02T12:59:00Z"),
    ]
    assert just_before["timestamp"].tolist() == [
        pd.Timestamp("2026-09-02T12:58:00Z")
    ]


def test_filter_as_of_requires_an_as_of_value() -> None:
    dataframe = _bars("2026-09-02T12:58:00Z", 2)

    with pytest.raises(DataClockError, match="as_of is required"):
        filter_as_of(dataframe, as_of=None)


def test_filter_as_of_accepts_an_empty_dataframe() -> None:
    empty = pd.DataFrame(
        columns=["timestamp", "open", "high", "low", "close", "volume"]
    )

    visible = filter_as_of(empty, as_of="2026-09-02T13:00:00Z")

    assert visible.empty


def test_summarize_as_of_reports_all_rows_hidden_before_first_bar() -> None:
    dataframe = _bars("2026-09-02T12:58:00Z", 4)

    summary = summarize_as_of(dataframe, as_of="2026-09-02T12:57:00Z")

    assert summary.rows_in == 4
    assert summary.rows_visible == 0
    assert summary.rows_hidden == 4
    assert summary.first_visible_timestamp is None
    assert summary.last_visible_timestamp is None
    assert summary.last_visible_available_at is None


def test_filtered_frame_records_canonical_utc_cutoff_in_attrs() -> None:
    dataframe = _bars("2026-09-02T12:58:00Z", 2)

    visible = filter_as_of(dataframe, as_of="2026-09-02T09:00:00-04:00")

    assert visible.attrs["as_of"] == "2026-09-02T13:00:00+00:00"


def test_normalize_as_of_honors_dst_offsets() -> None:
    # 2026-03-08 09:30 EDT (after spring-forward) and
    # 2026-11-01 09:30 EST (after fall-back) map to different UTC instants.
    assert normalize_as_of("2026-03-08T09:30:00-04:00") == pd.Timestamp(
        "2026-03-08T13:30:00Z"
    )
    assert normalize_as_of("2026-11-01T09:30:00-05:00") == pd.Timestamp(
        "2026-11-01T14:30:00Z"
    )
