from __future__ import annotations

from dataclasses import dataclass
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
    if timeframe == "1d":
        return timestamp + pd.Timedelta(days=1)
    minutes = TIMEFRAME_RULES[timeframe][1]
    assert minutes is not None
    return timestamp + pd.to_timedelta(minutes, unit="m")


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

    rule, expected_count = TIMEFRAME_RULES[timeframe]
    indexed = ordered.set_index("timestamp")
    aggregation = _metadata_aggregation(ordered)
    bars = indexed.resample(rule, label="left", closed="left", origin="start_day").agg(aggregation)
    counts = indexed["close"].resample(rule, label="left", closed="left", origin="start_day").count()
    bars["bar_count"] = counts
    bars = bars.loc[bars["bar_count"] > 0].copy()
    bars = bars.reset_index()

    if expected_count is not None:
        bars["bar_complete"] = bars["bar_count"] >= expected_count
    else:
        # A complete futures daily-session definition belongs in sessions.py. Until
        # then, a daily bucket is only considered final after a later bucket exists.
        bars["bar_complete"] = True
        if len(bars):
            bars.loc[bars.index[-1], "bar_complete"] = False

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
