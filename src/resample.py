from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime as _datetime
from datetime import time, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}
TIMEFRAME_RULES = {
    "1m": ("1min", 1),
    "2m": ("2min", 2),
    "3m": ("3min", 3),
    "5m": ("5min", 5),
    "15m": ("15min", 15),
    "30m": ("30min", 30),
    "1h": ("1h", 60),
    "4h": ("4h", 240),
    "1d": ("1D", None),
}

# CME equity-index futures Globex session boundary, fixed ET wall-clock times.
# The daily research bar must follow this session rather than a UTC-midnight
# calendar day: the session opens at 18:00 ET and closes at 17:00 ET the next
# calendar day, and the session date rolls at 18:00 ET. These values must stay
# consistent with config/sessions.yaml `sessions.globex` (start 18:00 / end
# 17:00) and `sessions._session_date`.
TRADING_TIMEZONE = "America/New_York"
GLOBEX_SESSION_START = time(18, 0)
GLOBEX_SESSION_CLOSE = time(17, 0)


class ResampleError(RuntimeError):
    """Raised when timeframe reconstruction cannot be completed safely."""


@dataclass(frozen=True)
class ResampleResult:
    timeframe: str
    dataframe: pd.DataFrame
    rows_in: int
    rows_out: int
    incomplete_bars: int


def validate_input_dataframe(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ResampleError(f"Missing required columns: {sorted(missing)}")
    if df.empty:
        raise ResampleError("Cannot resample an empty dataframe.")
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        raise ResampleError("'timestamp' must be datetime.")
    if getattr(df["timestamp"].dt, "tz", None) is None:
        raise ResampleError("'timestamp' must be timezone-aware.")


def _metadata_aggregation(df: pd.DataFrame) -> dict[str, str]:
    mapping: dict[str, str] = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    for column in ["source", "symbol", "contract"]:
        if column in df.columns:
            mapping[column] = "first"
    return mapping


def _availability_time(timestamp: pd.Series, timeframe: str) -> pd.Series:
    minutes = TIMEFRAME_RULES[timeframe][1]
    assert minutes is not None
    return timestamp + pd.to_timedelta(minutes, unit="m")


def _session_aware_daily(ordered: pd.DataFrame) -> pd.DataFrame:
    """Build daily bars over the Globex futures session (18:00 ET -> 17:00 ET).

    The CME equity-index Globex session opens at 18:00 ET and closes at 17:00
    ET the next calendar day. A daily research bar must follow that session
    boundary rather than a UTC-midnight calendar day, otherwise a session that
    spans UTC midnight is split in two and the futures trading date is
    mislabeled (phases.md: "Daily does not accidentally use midnight UTC if
    futures trading date is intended").

    The daily window is half-open ``[prior-day 18:00 ET, trading-date 17:00
    ET)``. Rows opening in the daily maintenance window ``[17:00, 18:00)`` ET
    belong to no Globex session and are excluded from every daily aggregate.
    The session date rolls at 18:00 ET (see sessions._session_date): a bar at
    or after 18:00 ET belongs to the *next* session date. Each resulting daily
    bar carries:

    - ``timestamp`` = the session OPEN (18:00 ET of the prior calendar day), in
      UTC, so a bar is labelled by its open time per the as_of contract;
    - ``available_at`` = the session CLOSE (17:00 ET of the session date), in
      UTC, so the daily bar is only usable once its session has fully closed;
    - ``bar_complete`` = True only when the completed input contains every
      required constituent minute of the session window (the number of ET
      wall-clock minutes between the session open and close). A session whose
      close instant has passed with full coverage is complete even when it is
      the last session in the data; a developing session (tail minutes not yet
      present) and any earlier session with missing constituent minutes stay
      incomplete, so finalized prior daily bars are the only complete inputs
      available to the bias engine.

    Open/close instants are built from the naive ET wall-clock date/time and
    then localized (not from absolute timedelta arithmetic), so the boundaries
    stay fixed through DST transitions: a session spanning spring-forward or
    fall-back still opens at 18:00 ET and closes at 17:00 ET, and its required
    constituent count is the true ET wall-clock minute count (23 hours on a
    normal day, 22 across spring-forward, 24 across fall-back).
    """
    et = ordered["timestamp"].dt.tz_convert(TRADING_TIMEZONE)
    et_times = et.dt.time
    in_maintenance_gap = (et_times >= GLOBEX_SESSION_CLOSE) & (
        et_times < GLOBEX_SESSION_START
    )
    trading = ordered.loc[~in_maintenance_gap]
    if trading.empty:
        return _empty_daily_bars()

    trading_et = trading["timestamp"].dt.tz_convert(TRADING_TIMEZONE)
    dates = trading_et.dt.date
    after_roll = trading_et.dt.time >= GLOBEX_SESSION_START
    session_date = pd.Series(
        [
            day + timedelta(days=1) if rolled else day
            for day, rolled in zip(dates, after_roll)
        ],
        index=trading.index,
        dtype="object",
    )

    work = trading.copy()
    work["_session_date"] = session_date

    aggregation = _metadata_aggregation(trading)
    grouped = work.groupby("_session_date", sort=True)
    bars = grouped.agg(aggregation).reset_index()
    bars["bar_count"] = grouped.size().to_numpy()

    def open_instant(session_day: Any) -> pd.Timestamp:
        naive = _datetime.combine(session_day - timedelta(days=1), GLOBEX_SESSION_START)
        return pd.Timestamp(naive, tz=TRADING_TIMEZONE)

    def close_instant(session_day: Any) -> pd.Timestamp:
        naive = _datetime.combine(session_day, GLOBEX_SESSION_CLOSE)
        return pd.Timestamp(naive, tz=TRADING_TIMEZONE)

    def expected_minutes(session_day: Any) -> int:
        """ET wall-clock 1m labels in the half-open [open, close) window."""
        delta = close_instant(session_day) - open_instant(session_day)
        return int(delta.total_seconds() // 60)

    bars["timestamp_et"] = bars["_session_date"].map(open_instant)
    bars["timestamp"] = bars["timestamp_et"].dt.tz_convert("UTC")
    bars["available_at"] = bars["_session_date"].map(close_instant).dt.tz_convert("UTC")
    bars["_expected_minutes"] = bars["_session_date"].map(expected_minutes)
    bars["bar_complete"] = bars["bar_count"] >= bars["_expected_minutes"]
    bars = bars.drop(columns=["_session_date", "_expected_minutes"])
    return bars


def _empty_daily_bars() -> pd.DataFrame:
    """Return a 1d result frame with the canonical columns and no rows."""
    return pd.DataFrame(
        columns=[
            "open",
            "high",
            "low",
            "close",
            "volume",
            "bar_count",
            "timestamp_et",
            "timestamp",
            "available_at",
            "bar_complete",
        ]
    )


def resample_timeframe(df: pd.DataFrame, timeframe: str) -> ResampleResult:
    validate_input_dataframe(df)
    if timeframe not in TIMEFRAME_RULES:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    ordered = df.sort_values("timestamp").copy().reset_index(drop=True)
    if timeframe == "1m":
        result = ordered.copy()
        result["bar_count"] = 1
        result["bar_complete"] = True
        result["timeframe"] = "1m"
        result["available_at"] = result["timestamp"] + pd.Timedelta(minutes=1)
        if "timestamp_et" not in result.columns:
            result["timestamp_et"] = result["timestamp"].dt.tz_convert("America/New_York")
        return ResampleResult("1m", result, len(df), len(result), 0)

    if timeframe == "1d":
        bars = _session_aware_daily(ordered)
        bars["timeframe"] = "1d"
        incomplete = int((~bars["bar_complete"]).sum())
        return ResampleResult("1d", bars, len(df), len(bars), incomplete)

    rule, expected_count = TIMEFRAME_RULES[timeframe]
    indexed = ordered.set_index("timestamp")
    aggregation = _metadata_aggregation(ordered)
    bars = indexed.resample(rule, label="left", closed="left", origin="start_day").agg(aggregation)
    counts = indexed["close"].resample(rule, label="left", closed="left", origin="start_day").count()
    bars["bar_count"] = counts
    bars = bars.loc[bars["bar_count"] > 0].copy()
    bars = bars.reset_index()

    bars["bar_complete"] = bars["bar_count"] >= expected_count

    bars["timeframe"] = timeframe
    bars["available_at"] = _availability_time(bars["timestamp"], timeframe)
    bars["timestamp_et"] = bars["timestamp"].dt.tz_convert("America/New_York")
    incomplete = int((~bars["bar_complete"]).sum())
    return ResampleResult(timeframe, bars, len(df), len(bars), incomplete)


def generate_standard_timeframes(df: pd.DataFrame) -> dict[str, ResampleResult]:
    return {timeframe: resample_timeframe(df, timeframe) for timeframe in TIMEFRAME_RULES}


def validate_resampled_bars(df: pd.DataFrame) -> None:
    required = REQUIRED_COLUMNS | {"bar_complete"}
    missing = required - set(df.columns)
    if missing:
        raise ResampleError(f"Resampled bars missing columns: {sorted(missing)}")
    if df.empty:
        return
    invalid = (
        (df["high"] < df[["open", "close", "low"]].max(axis=1))
        | (df["low"] > df[["open", "close", "high"]].min(axis=1))
        | (df["high"] < df["low"])
    )
    if invalid.any():
        raise ResampleError("Invalid OHLC relationship in resampled output.")
    if (df["volume"] < 0).any():
        raise ResampleError("Negative volume in resampled output.")


def save_resampled_parquet(result: ResampleResult, filepath: str | Path) -> Path:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result.dataframe.to_parquet(path, index=False)
    except ImportError as exc:
        raise ResampleError("Saving Parquet requires pyarrow.") from exc
    return path
