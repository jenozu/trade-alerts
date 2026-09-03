"""Production ``as_of`` data-clock contract.

Canonical semantics (Phase 2 C1; see docs/AS_OF_CONTRACT.md):

- Bar timestamps are bar OPEN times. A one-minute bar opening at 09:30 ET is
  complete and visible only at 09:31 ET.
- A raw bar's availability is ``timestamp + bar_duration`` (1 minute for the
  master 1m feed). Resampled and derived bars carry an explicit
  ``available_at`` column instead.
- A row may influence analysis at time ``as_of`` if and only if
  ``available_at <= as_of`` AND (when a ``bar_complete`` flag is present) the
  bar is complete. Incomplete bars are never production inputs.
- ``as_of`` must be timezone-aware; it is normalized to UTC. Naive inputs are
  rejected deliberately so production and replay callers state the timezone.
- Filtering is prefix-stable: appending future rows never changes the rows
  visible at an earlier ``as_of``, so replay outputs equal live prefixes.
- Downstream stages consume only the already-cut completed prefix; every
  resampled result is re-filtered with the same cutoff.

The functions in this module implement that contract and expose a summary of
what a cutoff hides. Consumers that need strategy-feature semantics beyond
this (session windows, developing vs finalized levels) build on top of it in
``sessions.py`` and must assume this completed-prefix input contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import pandas as pd


class DataClockError(RuntimeError):
    """Raised when an as-of cutoff cannot be applied safely."""


@dataclass(frozen=True)
class DataClockSummary:
    as_of: pd.Timestamp
    rows_in: int
    rows_visible: int
    rows_hidden: int
    first_visible_timestamp: pd.Timestamp | None
    last_visible_timestamp: pd.Timestamp | None
    last_visible_available_at: pd.Timestamp | None


def normalize_as_of(value: Any) -> pd.Timestamp:
    """Return a timezone-aware UTC as-of timestamp.

    Naive timestamps are rejected deliberately. Production and replay callers must
    state the timezone rather than relying on the VPS or workstation locale.
    """
    if value is None:
        raise DataClockError("as_of is required.")

    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:
        raise DataClockError(f"Invalid as_of value: {value!r}") from exc

    if timestamp.tzinfo is None:
        raise DataClockError(
            "as_of must be timezone-aware, e.g. 2026-09-02T09:00:00-04:00."
        )

    return timestamp.tz_convert("UTC")


def _validate_time_column(dataframe: pd.DataFrame, column: str) -> pd.Series:
    if column not in dataframe.columns:
        raise DataClockError(f"Missing required time column: {column}")

    series = dataframe[column]
    if not pd.api.types.is_datetime64_any_dtype(series):
        try:
            series = pd.to_datetime(series, errors="raise")
        except (TypeError, ValueError) as exc:
            raise DataClockError(f"Column {column!r} must contain datetimes.") from exc

    if getattr(series.dt, "tz", None) is None:
        raise DataClockError(f"Column {column!r} must be timezone-aware.")

    return series.dt.tz_convert("UTC")


def infer_available_at(
    dataframe: pd.DataFrame,
    *,
    bar_duration: timedelta | pd.Timedelta = timedelta(minutes=1),
    timestamp_column: str = "timestamp",
) -> pd.Series:
    """Infer when bars become usable from their opening timestamps.

    The canonical bar timestamp represents the bar *open*. A one-minute bar with
    timestamp 08:59 becomes available at 09:00. A bar timestamped 09:00 is not
    available until 09:01.
    """
    timestamps = _validate_time_column(dataframe, timestamp_column)
    duration = pd.Timedelta(bar_duration)
    if duration <= pd.Timedelta(0):
        raise DataClockError("bar_duration must be positive.")
    return timestamps + duration


def visibility_times(
    dataframe: pd.DataFrame,
    *,
    available_at_column: str = "available_at",
    timestamp_column: str = "timestamp",
    bar_duration: timedelta | pd.Timedelta = timedelta(minutes=1),
) -> pd.Series:
    """Return the timestamp at which each row is allowed to influence analysis.

    Resampled/derived data should carry an explicit ``available_at`` column. Raw
    one-minute OHLCV normally does not, so its visibility is inferred as
    ``timestamp + 1 minute`` by default.
    """
    if available_at_column in dataframe.columns:
        return _validate_time_column(dataframe, available_at_column)
    return infer_available_at(
        dataframe,
        bar_duration=bar_duration,
        timestamp_column=timestamp_column,
    )


def filter_as_of(
    dataframe: pd.DataFrame,
    *,
    as_of: Any,
    available_at_column: str = "available_at",
    timestamp_column: str = "timestamp",
    bar_duration: timedelta | pd.Timedelta = timedelta(minutes=1),
    require_bar_complete: bool = True,
    bar_complete_column: str = "bar_complete",
) -> pd.DataFrame:
    """Return only rows that were fully available at ``as_of``.

    Visibility uses ``available_at <= as_of``. When a dataframe exposes a
    ``bar_complete`` flag, incomplete bars are also excluded by default.
    """
    cutoff = normalize_as_of(as_of)
    if dataframe.empty:
        return dataframe.copy()

    timestamps = _validate_time_column(dataframe, timestamp_column)
    available = visibility_times(
        dataframe,
        available_at_column=available_at_column,
        timestamp_column=timestamp_column,
        bar_duration=bar_duration,
    )

    mask = available <= cutoff
    if require_bar_complete and bar_complete_column in dataframe.columns:
        complete = dataframe[bar_complete_column].fillna(False).astype(bool)
        mask &= complete

    result = dataframe.loc[mask].copy()
    result[timestamp_column] = timestamps.loc[result.index]
    if available_at_column in result.columns:
        result[available_at_column] = available.loc[result.index]
    result = result.sort_values(timestamp_column, kind="stable").reset_index(drop=True)
    result.attrs["as_of"] = cutoff.isoformat()
    return result


def summarize_as_of(
    dataframe: pd.DataFrame,
    *,
    as_of: Any,
    available_at_column: str = "available_at",
    timestamp_column: str = "timestamp",
    bar_duration: timedelta | pd.Timedelta = timedelta(minutes=1),
    require_bar_complete: bool = True,
    bar_complete_column: str = "bar_complete",
) -> DataClockSummary:
    cutoff = normalize_as_of(as_of)
    visible = filter_as_of(
        dataframe,
        as_of=cutoff,
        available_at_column=available_at_column,
        timestamp_column=timestamp_column,
        bar_duration=bar_duration,
        require_bar_complete=require_bar_complete,
        bar_complete_column=bar_complete_column,
    )

    if visible.empty:
        first_timestamp = None
        last_timestamp = None
        last_available = None
    else:
        first_timestamp = pd.Timestamp(visible[timestamp_column].iloc[0])
        last_timestamp = pd.Timestamp(visible[timestamp_column].iloc[-1])
        visible_available = visibility_times(
            visible,
            available_at_column=available_at_column,
            timestamp_column=timestamp_column,
            bar_duration=bar_duration,
        )
        last_available = pd.Timestamp(visible_available.iloc[-1])

    return DataClockSummary(
        as_of=cutoff,
        rows_in=int(len(dataframe)),
        rows_visible=int(len(visible)),
        rows_hidden=int(len(dataframe) - len(visible)),
        first_visible_timestamp=first_timestamp,
        last_visible_timestamp=last_timestamp,
        last_visible_available_at=last_available,
    )


def filter_resampled_results_as_of(
    results: dict[str, Any],
    *,
    as_of: Any,
) -> dict[str, Any]:
    """Apply the same as-of cutoff to ResampleResult-like objects.

    The function preserves the input object's type when it is constructible with
    the standard ``timeframe, dataframe, rows_in, rows_out, incomplete_bars``
    fields. Plain DataFrames are also accepted for lightweight callers/tests.
    """
    cutoff = normalize_as_of(as_of)
    filtered: dict[str, Any] = {}

    for timeframe, value in results.items():
        dataframe = value.dataframe if hasattr(value, "dataframe") else value
        if not isinstance(dataframe, pd.DataFrame):
            raise DataClockError(
                f"Resampled result {timeframe!r} does not contain a DataFrame."
            )

        visible = filter_as_of(dataframe, as_of=cutoff)

        if hasattr(value, "dataframe"):
            result_type = type(value)
            incomplete = (
                int((~visible["bar_complete"].astype(bool)).sum())
                if "bar_complete" in visible.columns
                else 0
            )
            try:
                filtered[timeframe] = result_type(
                    timeframe=getattr(value, "timeframe", timeframe),
                    dataframe=visible,
                    rows_in=getattr(value, "rows_in", len(dataframe)),
                    rows_out=len(visible),
                    incomplete_bars=incomplete,
                )
            except TypeError as exc:
                raise DataClockError(
                    f"Could not reconstruct resampled result for {timeframe!r}."
                ) from exc
        else:
            filtered[timeframe] = visible

    return filtered
