from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd


class VWAPError(RuntimeError):
    """Raised when VWAP cannot be calculated safely."""


REQUIRED_COLUMNS = {
    "timestamp",
    "high",
    "low",
    "close",
    "volume",
}


def _validate(dataframe: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(dataframe.columns)

    if missing:
        raise VWAPError(
            f"Missing required columns: {sorted(missing)}"
        )

    if dataframe.empty:
        raise VWAPError(
            "Cannot calculate VWAP on an empty dataframe."
        )

    if not pd.api.types.is_datetime64_any_dtype(
        dataframe["timestamp"]
    ):
        raise VWAPError("'timestamp' must be datetime.")

    if getattr(dataframe["timestamp"].dt, "tz", None) is None:
        raise VWAPError(
            "'timestamp' must be timezone-aware."
        )

    volume = pd.to_numeric(
        dataframe["volume"],
        errors="coerce",
    )

    if volume.isna().any():
        raise VWAPError(
            "Volume contains non-numeric or missing values."
        )

    if (volume < 0).any():
        raise VWAPError("Volume cannot be negative.")


def _parse_reset_time(value: str) -> tuple[int, int]:
    try:
        hour_text, minute_text = str(value).split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    except Exception as exc:
        raise VWAPError(
            "VWAP reset_time_et must use HH:MM."
        ) from exc

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise VWAPError(
            "VWAP reset_time_et must use a valid HH:MM time."
        )

    return hour, minute


def _session_anchor(
    timestamps_et: pd.Series,
    *,
    reset_time_et: str,
) -> pd.Series:
    hour, minute = _parse_reset_time(reset_time_et)
    reset_minutes = hour * 60 + minute

    anchors: list[object] = []

    for timestamp in timestamps_et:
        current_minutes = timestamp.hour * 60 + timestamp.minute

        if current_minutes >= reset_minutes:
            anchor = timestamp.date()
        else:
            anchor = timestamp.date() - timedelta(days=1)

        anchors.append(anchor)

    return pd.Series(
        anchors,
        index=timestamps_et.index,
        dtype="object",
    )


def enrich_vwap(
    dataframe: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Calculate causal session-reset VWAP and objective derivatives."""

    _validate(dataframe)

    section = config.get("vwap", {})
    timezone = str(
        section.get(
            "timezone",
            "America/New_York",
        )
    )
    reset_time_et = str(
        section.get(
            "reset_time_et",
            "18:00",
        )
    )
    slope_bars = int(
        section.get(
            "slope_bars",
            3,
        )
    )

    if slope_bars < 1:
        raise VWAPError(
            "vwap.slope_bars must be >= 1."
        )

    result = (
        dataframe
        .sort_values("timestamp")
        .copy()
        .reset_index(drop=True)
    )

    if "timestamp_et" not in result.columns:
        result["timestamp_et"] = (
            result["timestamp"]
            .dt.tz_convert(timezone)
        )
    else:
        result["timestamp_et"] = pd.to_datetime(
            result["timestamp_et"],
            utc=True,
        ).dt.tz_convert(timezone)

    result["vwap_session_anchor"] = _session_anchor(
        result["timestamp_et"],
        reset_time_et=reset_time_et,
    )

    high = pd.to_numeric(
        result["high"],
        errors="coerce",
    )
    low = pd.to_numeric(
        result["low"],
        errors="coerce",
    )
    close = pd.to_numeric(
        result["close"],
        errors="coerce",
    )
    volume = pd.to_numeric(
        result["volume"],
        errors="coerce",
    )

    result["vwap_typical_price"] = (
        high + low + close
    ) / 3.0

    result["vwap_price_volume"] = (
        result["vwap_typical_price"] * volume
    )

    grouped = result.groupby(
        "vwap_session_anchor",
        sort=False,
    )

    result["vwap_cumulative_volume"] = (
        grouped["volume"].cumsum()
    )

    result["vwap_cumulative_price_volume"] = (
        result.groupby(
            "vwap_session_anchor",
            sort=False,
        )["vwap_price_volume"]
        .cumsum()
    )

    valid_volume = (
        result["vwap_cumulative_volume"] > 0
    )

    result["vwap"] = (
        result["vwap_cumulative_price_volume"]
        / result[
            "vwap_cumulative_volume"
        ].replace(0.0, np.nan)
    ).where(valid_volume)

    result["vwap_distance_points"] = (
        close - result["vwap"]
    )

    result["vwap_distance_pct"] = (
        result["vwap_distance_points"]
        / result["vwap"].replace(0.0, np.nan)
        * 100.0
    )

    result["vwap_position"] = np.select(
        [
            result["vwap"].isna(),
            close > result["vwap"],
            close < result["vwap"],
        ],
        [
            "unknown",
            "above",
            "below",
        ],
        default="at",
    )

    previous_position = (
        result.groupby(
            "vwap_session_anchor",
            sort=False,
        )["vwap_position"]
        .shift(1)
    )

    result["vwap_bullish_cross"] = (
        (result["vwap_position"] == "above")
        & previous_position.isin(
            ["below", "at"]
        )
    )

    result["vwap_bearish_cross"] = (
        (result["vwap_position"] == "below")
        & previous_position.isin(
            ["above", "at"]
        )
    )

    previous_vwap = (
        result.groupby(
            "vwap_session_anchor",
            sort=False,
        )["vwap"]
        .shift(slope_bars)
    )

    result["vwap_slope_points_per_bar"] = (
        result["vwap"] - previous_vwap
    ) / float(slope_bars)

    result["vwap_slope_direction"] = np.select(
        [
            result[
                "vwap_slope_points_per_bar"
            ].isna(),
            result[
                "vwap_slope_points_per_bar"
            ] > 0,
            result[
                "vwap_slope_points_per_bar"
            ] < 0,
        ],
        [
            "unknown",
            "rising",
            "falling",
        ],
        default="flat",
    )

    return result


def save_vwap_outputs(
    dataframe: pd.DataFrame,
    output_directory: str | Path,
) -> Path:
    directory = Path(output_directory)
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = directory / "vwap.parquet"

    try:
        dataframe.to_parquet(
            path,
            index=False,
        )
    except ImportError as exc:
        raise VWAPError(
            "Saving VWAP Parquet requires pyarrow."
        ) from exc

    return path
