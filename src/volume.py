from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}


class VolumeError(RuntimeError):
    """Raised when causal volume features cannot be calculated safely."""


@dataclass(frozen=True)
class VolumeSummary:
    rows: int
    rolling_rvol_available: int
    tod_rvol_available: int
    rolling_spikes: int
    tod_spikes: int
    combined_spikes: int


def _validate(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise VolumeError(f"Missing required columns: {sorted(missing)}")
    if df.empty:
        raise VolumeError("Cannot calculate volume features on an empty dataframe.")
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        raise VolumeError("'timestamp' must be datetime.")
    if getattr(df["timestamp"].dt, "tz", None) is None:
        raise VolumeError("'timestamp' must be timezone-aware.")


def _time_of_day_baseline(
    df: pd.DataFrame,
    *,
    lookback_sessions: int,
    minimum_sessions: int,
) -> pd.Series:
    """Mean volume for the same ET minute using previous sessions only."""
    et = df["timestamp_et"] if "timestamp_et" in df.columns else df["timestamp"].dt.tz_convert("America/New_York")
    session = df["session_date"] if "session_date" in df.columns else et.dt.date
    minute = et.dt.hour * 60 + et.dt.minute
    helper = pd.DataFrame({"session": session, "minute": minute, "volume": df["volume"].astype(float)})

    # Aggregate first so a source with duplicate same-minute records cannot leak
    # within the current session's baseline.
    per_session = (
        helper.groupby(["session", "minute"], sort=True, as_index=False)["volume"].sum()
    )
    per_session = per_session.sort_values(["minute", "session"]).reset_index(drop=True)
    baseline = pd.Series(np.nan, index=per_session.index, dtype=float)
    for _, indices in per_session.groupby("minute", sort=False).groups.items():
        idx = list(indices)
        values = per_session.loc[idx, "volume"].astype(float)
        prior = values.shift(1).rolling(
            window=lookback_sessions,
            min_periods=minimum_sessions,
        ).mean()
        baseline.loc[idx] = prior.to_numpy()

    per_session["tod_baseline"] = baseline
    lookup = {
        (row.session, int(row.minute)): row.tod_baseline
        for row in per_session.itertuples(index=False)
    }
    return pd.Series(
        [lookup.get((s, int(m)), np.nan) for s, m in zip(session, minute)],
        index=df.index,
        dtype=float,
    )


def enrich_volume_features(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    _validate(df)
    result = df.sort_values("timestamp").copy().reset_index(drop=True)
    if "timestamp_et" not in result.columns:
        result["timestamp_et"] = result["timestamp"].dt.tz_convert("America/New_York")

    section = config.get("relative_volume", {})
    rolling = section.get("rolling", {})
    tod = section.get("time_of_day", {})
    rolling_window = int(rolling.get("lookback_bars", section.get("rolling_lookback_bars", 20)))
    rolling_min = int(rolling.get("minimum_periods", rolling_window))
    tod_lookback = int(tod.get("lookback_sessions", 20))
    tod_min = int(tod.get("minimum_sessions", 5))
    threshold = float(section.get("initial_signal_threshold", 1.50))
    z_threshold = float(section.get("zscore_threshold", 2.0))

    history = result["volume"].astype(float).shift(1)
    result["volume_mean_rolling"] = history.rolling(rolling_window, min_periods=rolling_min).mean()
    result["volume_std_rolling"] = history.rolling(rolling_window, min_periods=rolling_min).std(ddof=0)
    result["volume_median_rolling"] = history.rolling(rolling_window, min_periods=rolling_min).median()
    result["rvol_rolling"] = result["volume"] / result["volume_mean_rolling"].replace(0, np.nan)
    result["volume_zscore"] = (
        (result["volume"] - result["volume_mean_rolling"])
        / result["volume_std_rolling"].replace(0, np.nan)
    )
    result["volume_change"] = result["volume"].diff()
    result["volume_change_pct"] = result["volume"].pct_change(fill_method=None)

    result["volume_tod_baseline"] = _time_of_day_baseline(
        result,
        lookback_sessions=tod_lookback,
        minimum_sessions=tod_min,
    )
    result["rvol_time_of_day"] = result["volume"] / result["volume_tod_baseline"].replace(0, np.nan)

    result["rvol_rolling_high"] = (result["rvol_rolling"] >= threshold).fillna(False)
    result["rvol_time_of_day_high"] = (result["rvol_time_of_day"] >= threshold).fillna(False)
    result["volume_zscore_high"] = (result["volume_zscore"] >= z_threshold).fillna(False)
    result["volume_spike_rolling"] = result["rvol_rolling_high"] | result["volume_zscore_high"]
    result["volume_spike_time_of_day"] = result["rvol_time_of_day_high"]
    result["volume_spike_both"] = result["volume_spike_rolling"] & result["volume_spike_time_of_day"]
    result["volume_spike_any"] = result["volume_spike_rolling"] | result["volume_spike_time_of_day"]
    result["rvol_agreement"] = np.select(
        [result["volume_spike_both"], result["volume_spike_any"]],
        ["both", "one"],
        default="none",
    )
    result["bullish_volume_context"] = (result["close"] > result["open"]) & result["volume_spike_any"]
    result["bearish_volume_context"] = (result["close"] < result["open"]) & result["volume_spike_any"]
    return result


def volume_summary(df: pd.DataFrame) -> VolumeSummary:
    def available(column: str) -> int:
        return int(df[column].notna().sum()) if column in df.columns else 0
    def count(column: str) -> int:
        return int(df[column].fillna(False).sum()) if column in df.columns else 0
    return VolumeSummary(
        rows=len(df),
        rolling_rvol_available=available("rvol_rolling"),
        tod_rvol_available=available("rvol_time_of_day"),
        rolling_spikes=count("volume_spike_rolling"),
        tod_spikes=count("volume_spike_time_of_day"),
        combined_spikes=count("volume_spike_both"),
    )


def save_volume_outputs(df: pd.DataFrame, output_directory: str | Path) -> dict[str, Path]:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    feature_path = directory / "nq_1m_volume.parquet"
    spike_path = directory / "volume_spikes.csv"
    try:
        df.to_parquet(feature_path, index=False)
    except ImportError as exc:
        raise VolumeError("Saving Parquet requires pyarrow.") from exc
    mask = df.get("volume_spike_any", pd.Series(False, index=df.index)).fillna(False)
    columns = [
        column for column in [
            "timestamp", "timestamp_et", "session_date", "open", "high", "low", "close", "volume",
            "rvol_rolling", "rvol_time_of_day", "volume_zscore", "volume_spike_rolling",
            "volume_spike_time_of_day", "volume_spike_both",
        ] if column in df.columns
    ]
    df.loc[mask, columns].to_csv(spike_path, index=False)
    return {"volume_features": feature_path, "volume_spikes": spike_path}
