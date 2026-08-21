from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")
PRICE_COLUMNS = ("open", "high", "low", "close")


class DataValidationError(RuntimeError):
    """Raised when a dataset cannot be validated structurally."""


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    category: str
    count: int
    message: str


@dataclass
class ValidationReport:
    rows: int
    passed: bool = True
    duplicate_timestamps: int = 0
    out_of_order_rows: int = 0
    missing_values: int = 0
    invalid_prices: int = 0
    invalid_ohlc_relationships: int = 0
    negative_volume_rows: int = 0
    zero_volume_rows: int = 0
    off_tick_price_rows: int = 0
    timestamp_gaps: int = 0
    continuous_missing_timestamps: int = 0
    large_price_jumps: int = 0
    extreme_bar_ranges: int = 0
    issues: list[ValidationIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["issues"] = [asdict(issue) for issue in self.issues]
        return result


def _validate_structure(df: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise DataValidationError(f"Missing required columns: {missing}")
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        raise DataValidationError("'timestamp' must be a pandas datetime column.")
    if getattr(df["timestamp"].dt, "tz", None) is None:
        raise DataValidationError("'timestamp' must be timezone-aware.")


def find_duplicate_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[df["timestamp"].duplicated(keep=False)].copy()


def find_out_of_order_rows(df: pd.DataFrame) -> pd.DataFrame:
    mask = df["timestamp"].diff().dt.total_seconds().lt(0).fillna(False)
    return df.loc[mask].copy()


def find_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    columns = [column for column in REQUIRED_COLUMNS if column in df.columns]
    return df.loc[df[columns].isna().any(axis=1)].copy()


def find_invalid_prices(df: pd.DataFrame) -> pd.DataFrame:
    columns = [column for column in PRICE_COLUMNS if column in df.columns]
    if not columns:
        return df.iloc[0:0].copy()
    mask = (df[columns] <= 0).any(axis=1)
    return df.loc[mask].copy()


def find_invalid_ohlc_relationships(df: pd.DataFrame) -> pd.DataFrame:
    high_max = df[["open", "close", "low"]].max(axis=1)
    low_min = df[["open", "close", "high"]].min(axis=1)
    mask = (df["high"] < high_max) | (df["low"] > low_min) | (df["high"] < df["low"])
    return df.loc[mask].copy()


def find_negative_volume(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[df["volume"] < 0].copy()


def find_zero_volume(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[df["volume"] == 0].copy()


def find_off_tick_prices(df: pd.DataFrame, *, tick_size: float = 0.25) -> pd.DataFrame:
    if tick_size <= 0:
        raise ValueError("tick_size must be positive")
    row_mask = pd.Series(False, index=df.index)
    for column in PRICE_COLUMNS:
        if column not in df.columns:
            continue
        scaled = df[column].astype(float) / tick_size
        aligned = np.isclose(scaled, np.round(scaled), atol=1e-8, rtol=0)
        row_mask |= ~pd.Series(aligned, index=df.index)
    return df.loc[row_mask].copy()


def find_timestamp_gaps(
    df: pd.DataFrame,
    *,
    expected_interval_minutes: int = 1,
) -> pd.DataFrame:
    if expected_interval_minutes <= 0:
        raise ValueError("expected_interval_minutes must be positive")
    ordered = df.sort_values("timestamp")
    gaps = ordered["timestamp"].diff().dt.total_seconds().div(60.0)
    mask = gaps > expected_interval_minutes
    if not mask.any():
        return pd.DataFrame(columns=["previous_timestamp", "timestamp", "gap_minutes"])
    rows = []
    indices = list(ordered.index)
    for position, (idx, gap) in enumerate(gaps.items()):
        if pd.isna(gap) or gap <= expected_interval_minutes:
            continue
        previous_idx = indices[position - 1]
        rows.append(
            {
                "previous_timestamp": ordered.loc[previous_idx, "timestamp"],
                "timestamp": ordered.loc[idx, "timestamp"],
                "gap_minutes": float(gap),
            }
        )
    return pd.DataFrame(rows)


def find_continuous_missing_timestamps(
    df: pd.DataFrame,
    *,
    expected_interval_minutes: int = 1,
) -> list[pd.Timestamp]:
    if df.empty:
        return []
    ordered = pd.DatetimeIndex(df["timestamp"].sort_values().drop_duplicates())
    expected = pd.date_range(
        start=ordered.min(),
        end=ordered.max(),
        freq=f"{expected_interval_minutes}min",
        tz=ordered.tz,
    )
    missing = expected.difference(ordered)
    return [pd.Timestamp(value) for value in missing]


def find_large_price_jumps(df: pd.DataFrame, *, threshold_points: float = 100.0) -> pd.DataFrame:
    previous_close = df["close"].shift(1)
    open_gap = (df["open"] - previous_close).abs()

    # Record the start of each discontinuity rather than double-counting an
    # isolated bad/spike bar on both the jump into it and the immediate
    # reversion out of it.
    raw_mask = open_gap > threshold_points
    mask = raw_mask & ~raw_mask.shift(1, fill_value=False)

    result = df.loc[mask, [column for column in ["timestamp", "open", "high", "low", "close"] if column in df.columns]].copy()
    result["previous_close"] = previous_close.loc[mask]
    result["open_gap_points"] = open_gap.loc[mask]
    return result


def find_extreme_bar_ranges(
    df: pd.DataFrame,
    *,
    rolling_window: int = 20,
    multiplier: float = 10.0,
) -> pd.DataFrame:
    bar_range = df["high"] - df["low"]
    baseline = bar_range.shift(1).rolling(rolling_window, min_periods=max(3, rolling_window // 2)).median()
    mask = baseline.notna() & (bar_range > baseline * multiplier)
    result = df.loc[mask].copy()
    if not result.empty:
        result["bar_range"] = bar_range.loc[mask]
        result["rolling_median_range"] = baseline.loc[mask]
    return result


def session_hour_summary(df: pd.DataFrame) -> pd.DataFrame:
    if "timestamp_et" in df.columns:
        et = pd.to_datetime(df["timestamp_et"])
    else:
        et = df["timestamp"].dt.tz_convert("America/New_York")
    temp = df.copy()
    temp["et_hour"] = et.dt.hour
    grouped = temp.groupby("et_hour", sort=True)
    return grouped.agg(
        bars=("timestamp", "size"),
        total_volume=("volume", "sum"),
    ).reset_index()


def daily_coverage_summary(df: pd.DataFrame) -> pd.DataFrame:
    if "timestamp_et" in df.columns:
        et = pd.to_datetime(df["timestamp_et"])
    else:
        et = df["timestamp"].dt.tz_convert("America/New_York")
    temp = df.copy()
    temp["session_day"] = et.dt.date
    return (
        temp.groupby("session_day", sort=True)
        .agg(
            bars=("timestamp", "size"),
            first_timestamp=("timestamp", "min"),
            last_timestamp=("timestamp", "max"),
            day_high=("high", "max"),
            day_low=("low", "min"),
            total_volume=("volume", "sum"),
        )
        .reset_index()
    )


def _add_issue(report: ValidationReport, severity: str, category: str, count: int, message: str) -> None:
    if count <= 0:
        return
    report.issues.append(ValidationIssue(severity, category, int(count), message))
    if severity == "ERROR":
        report.passed = False


def validate_market_data(
    df: pd.DataFrame,
    *,
    tick_size: float = 0.25,
    expected_interval_minutes: int = 1,
    large_gap_points: float = 100.0,
    extreme_range_window: int = 20,
    extreme_range_multiplier: float = 10.0,
) -> ValidationReport:
    _validate_structure(df)
    report = ValidationReport(rows=int(len(df)))

    duplicates = find_duplicate_timestamps(df)
    out_of_order = find_out_of_order_rows(df)
    missing_values = find_missing_values(df)
    invalid_prices = find_invalid_prices(df)
    invalid_ohlc = find_invalid_ohlc_relationships(df)
    negative_volume = find_negative_volume(df)
    zero_volume = find_zero_volume(df)
    off_tick = find_off_tick_prices(df, tick_size=tick_size)
    gaps = find_timestamp_gaps(df, expected_interval_minutes=expected_interval_minutes)
    missing_timestamps = find_continuous_missing_timestamps(
        df, expected_interval_minutes=expected_interval_minutes
    )
    jumps = find_large_price_jumps(df, threshold_points=large_gap_points)
    extreme = find_extreme_bar_ranges(
        df,
        rolling_window=extreme_range_window,
        multiplier=extreme_range_multiplier,
    )

    report.duplicate_timestamps = len(duplicates)
    report.out_of_order_rows = len(out_of_order)
    report.missing_values = len(missing_values)
    report.invalid_prices = len(invalid_prices)
    report.invalid_ohlc_relationships = len(invalid_ohlc)
    report.negative_volume_rows = len(negative_volume)
    report.zero_volume_rows = len(zero_volume)
    report.off_tick_price_rows = len(off_tick)
    report.timestamp_gaps = len(gaps)
    report.continuous_missing_timestamps = len(missing_timestamps)
    report.large_price_jumps = len(jumps)
    report.extreme_bar_ranges = len(extreme)

    _add_issue(report, "ERROR", "duplicate_timestamps", len(duplicates), "Duplicate timestamps detected.")
    _add_issue(report, "ERROR", "out_of_order_rows", len(out_of_order), "Timestamps are out of order.")
    _add_issue(report, "ERROR", "missing_values", len(missing_values), "Missing required OHLCV values detected.")
    _add_issue(report, "ERROR", "invalid_prices", len(invalid_prices), "Zero or negative prices detected.")
    _add_issue(report, "ERROR", "invalid_ohlc_relationships", len(invalid_ohlc), "Invalid OHLC relationships detected.")
    _add_issue(report, "ERROR", "negative_volume", len(negative_volume), "Negative volume detected.")
    _add_issue(report, "WARNING", "zero_volume", len(zero_volume), "Zero-volume bars detected.")
    _add_issue(report, "WARNING", "off_tick_prices", len(off_tick), "Prices not aligned to NQ tick size detected.")
    _add_issue(report, "WARNING", "timestamp_gaps", len(gaps), "Timestamp gaps detected; exchange closures are not session-aware yet.")
    _add_issue(report, "WARNING", "large_price_jumps", len(jumps), "Large open-to-prior-close jumps detected.")
    _add_issue(report, "WARNING", "extreme_bar_ranges", len(extreme), "Extreme candle ranges detected.")
    return report


def print_validation_report(report: ValidationReport) -> None:
    print("\n============================================================")
    print("MARKET DATA VALIDATION")
    print("============================================================")
    print(f"Rows: {report.rows:,}")
    print(f"Status: {'PASS' if report.passed else 'FAIL'}")
    if not report.issues:
        print("No validation issues detected.")
        return
    for issue in report.issues:
        print(f"{issue.severity:<7} {issue.category}: {issue.count:,} - {issue.message}")


def save_validation_report_json(report: ValidationReport, filepath: str | Path) -> Path:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(report.to_dict(), file, indent=2, default=str)
    return path


def save_coverage_reports(df: pd.DataFrame, output_directory: str | Path) -> dict[str, Path]:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    hourly_path = directory / "session_hour_summary.csv"
    daily_path = directory / "daily_coverage_summary.csv"
    gaps_path = directory / "timestamp_gaps.csv"
    session_hour_summary(df).to_csv(hourly_path, index=False)
    daily_coverage_summary(df).to_csv(daily_path, index=False)
    find_timestamp_gaps(df).to_csv(gaps_path, index=False)
    return {"hourly": hourly_path, "daily": daily_path, "gaps": gaps_path}
