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


def _validate_symbol_scope(df: pd.DataFrame) -> None:
    """Never calculate one volume baseline across NQ and MNQ."""

    if "symbol" not in df.columns:
        return

    symbols = {
        str(value).strip().upper()
        for value in df["symbol"].dropna()
        if str(value).strip()
    }

    if len(symbols) > 1:
        raise VolumeError(
            "Volume baselines cannot mix multiple symbols: "
            f"{sorted(symbols)}"
        )


def _causal_volume_percentile(
    volumes: pd.Series,
    *,
    lookback_bars: int,
    minimum_periods: int,
) -> pd.Series:
    """Percentile of current volume against prior bars only."""

    values = pd.to_numeric(
        volumes,
        errors="coerce",
    ).to_numpy(dtype=float)

    output = np.full(
        len(values),
        np.nan,
        dtype=float,
    )

    for index, current in enumerate(values):
        if np.isnan(current):
            continue

        start = max(
            0,
            index - lookback_bars,
        )

        history = values[start:index]
        history = history[
            ~np.isnan(history)
        ]

        if len(history) < minimum_periods:
            continue

        output[index] = float(
            np.mean(history <= current)
            * 100.0
        )

    return pd.Series(
        output,
        index=volumes.index,
        dtype=float,
    )


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


def enrich_volume_features(
    df: pd.DataFrame,
    config: dict[str, Any],
    *,
    timeframe: str = "1m",
) -> pd.DataFrame:
    _validate(df)
    _validate_symbol_scope(df)

    timeframe = str(timeframe).strip()
    if not timeframe:
        raise VolumeError("timeframe cannot be blank.")

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

    percentile = section.get("percentile", {})
    percentile_window = int(
        percentile.get("lookback_bars", rolling_window)
    )
    percentile_min = int(
        percentile.get("minimum_periods", rolling_min)
    )

    context = section.get("context", {})
    context_lookback = int(
        context.get("lookback_bars", 5)
    )
    pullback_trend_bars = int(
        context.get("pullback_trend_bars", 3)
    )
    pullback_low_volume_ratio = float(
        context.get("pullback_low_volume_ratio", 1.0)
    )

    if percentile_window < 1 or percentile_min < 1:
        raise VolumeError(
            "Volume percentile lookback/minimum periods must be >= 1."
        )

    if context_lookback < 1 or pullback_trend_bars < 1:
        raise VolumeError(
            "Volume context lookbacks must be >= 1."
        )

    history = result["volume"].astype(float).shift(1)
    result["volume_mean_rolling"] = history.rolling(rolling_window, min_periods=rolling_min).mean()
    result["volume_std_rolling"] = history.rolling(rolling_window, min_periods=rolling_min).std(ddof=0)
    result["volume_median_rolling"] = history.rolling(rolling_window, min_periods=rolling_min).median()

    result["volume_percentile_rolling"] = _causal_volume_percentile(
        result["volume"],
        lookback_bars=percentile_window,
        minimum_periods=percentile_min,
    )

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
    result["bullish_volume_context"] = (
        (result["close"] > result["open"])
        & result["volume_spike_any"]
    )

    result["bearish_volume_context"] = (
        (result["close"] < result["open"])
        & result["volume_spike_any"]
    )

    prior_high = (
        result["high"]
        .shift(1)
        .rolling(
            context_lookback,
            min_periods=context_lookback,
        )
        .max()
    )

    prior_low = (
        result["low"]
        .shift(1)
        .rolling(
            context_lookback,
            min_periods=context_lookback,
        )
        .min()
    )

    result["bullish_volume_breakout"] = (
        (result["close"] > prior_high)
        & result["volume_spike_any"]
    ).fillna(False)

    result["bearish_volume_breakout"] = (
        (result["close"] < prior_low)
        & result["volume_spike_any"]
    ).fillna(False)

    result["bearish_volume_rejection"] = (
        (result["high"] > prior_high)
        & (result["close"] <= prior_high)
        & result["volume_spike_any"]
    ).fillna(False)

    result["bullish_volume_rejection"] = (
        (result["low"] < prior_low)
        & (result["close"] >= prior_low)
        & result["volume_spike_any"]
    ).fillna(False)

    prior_trend = (
        result["close"].shift(1)
        - result["close"].shift(
            1 + pullback_trend_bars
        )
    )

    low_volume = (
        result["volume"]
        <= (
            result["volume_mean_rolling"]
            * pullback_low_volume_ratio
        )
    ).fillna(False)

    result["bullish_pullback_low_volume"] = (
        (prior_trend > 0)
        & (result["close"] < result["open"])
        & low_volume
    ).fillna(False)

    result["bearish_pullback_low_volume"] = (
        (prior_trend < 0)
        & (result["close"] > result["open"])
        & low_volume
    ).fillna(False)

    result["volume_context"] = np.select(
        [
            result["bullish_volume_breakout"],
            result["bearish_volume_breakout"],
            result["bullish_volume_rejection"],
            result["bearish_volume_rejection"],
            result["bullish_pullback_low_volume"],
            result["bearish_pullback_low_volume"],
        ],
        [
            "bullish_breakout_high_volume",
            "bearish_breakout_high_volume",
            "bullish_rejection_high_volume",
            "bearish_rejection_high_volume",
            "bullish_pullback_low_volume",
            "bearish_pullback_low_volume",
        ],
        default="neutral",
    )

    # Explicit timeframe-labelled outputs for market-state serialization.
    result[f"volume_{timeframe}"] = result["volume"]
    result[f"volume_{timeframe}_mean_rolling"] = result[
        "volume_mean_rolling"
    ]
    result[f"volume_{timeframe}_median_rolling"] = result[
        "volume_median_rolling"
    ]
    result[f"volume_{timeframe}_percentile"] = result[
        "volume_percentile_rolling"
    ]

    return result


def build_multitimeframe_volume_features(
    dataframe_1m: pd.DataFrame,
    dataframe_5m: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Expose causal completed 1m and 5m volume on the 1m timeline."""

    one = enrich_volume_features(
        dataframe_1m,
        config,
        timeframe="1m",
    )

    five_source = dataframe_5m.copy()

    if "bar_complete" in five_source.columns:
        five_source = five_source.loc[
            five_source["bar_complete"].fillna(False)
        ].copy()

    if five_source.empty:
        result = one.copy()

        for column in [
            "volume_5m",
            "volume_5m_mean_rolling",
            "volume_5m_median_rolling",
            "volume_5m_percentile",
            "rvol_5m_rolling",
            "rvol_5m_time_of_day",
        ]:
            result[column] = np.nan

        result["volume_5m_spike_any"] = False
        result["volume_5m_context"] = "unavailable"
        result["volume_5m_available_at"] = pd.NaT

        return result

    _validate_symbol_scope(five_source)

    if (
        "symbol" in one.columns
        and "symbol" in five_source.columns
    ):
        one_symbols = {
            str(value).strip().upper()
            for value in one["symbol"].dropna()
            if str(value).strip()
        }

        five_symbols = {
            str(value).strip().upper()
            for value in five_source["symbol"].dropna()
            if str(value).strip()
        }

        if (
            one_symbols
            and five_symbols
            and one_symbols != five_symbols
        ):
            raise VolumeError(
                "1m and 5m volume datasets use different symbols."
            )

    five = enrich_volume_features(
        five_source,
        config,
        timeframe="5m",
    )

    if "available_at" in five.columns:
        five["volume_5m_available_at"] = pd.to_datetime(
            five["available_at"],
            utc=True,
        )
    else:
        five["volume_5m_available_at"] = (
            five["timestamp"]
            + pd.Timedelta(minutes=5)
        )

    right = five[
        [
            "volume_5m_available_at",
            "volume_5m",
            "volume_5m_mean_rolling",
            "volume_5m_median_rolling",
            "volume_5m_percentile",
            "rvol_rolling",
            "rvol_time_of_day",
            "volume_spike_any",
            "volume_context",
        ]
    ].copy()

    right = right.rename(
        columns={
            "rvol_rolling": "rvol_5m_rolling",
            "rvol_time_of_day": "rvol_5m_time_of_day",
            "volume_spike_any": "volume_5m_spike_any",
            "volume_context": "volume_5m_context",
        }
    )

    if "available_at" in one.columns:
        merge_clock = pd.to_datetime(
            one["available_at"],
            utc=True,
        )
    else:
        merge_clock = (
            one["timestamp"]
            + pd.Timedelta(minutes=1)
        )

    left = one.copy()
    left["_volume_merge_clock"] = merge_clock

    left = left.sort_values(
        "_volume_merge_clock",
        kind="stable",
    )

    right = right.sort_values(
        "volume_5m_available_at",
        kind="stable",
    )

    merged = pd.merge_asof(
        left,
        right,
        left_on="_volume_merge_clock",
        right_on="volume_5m_available_at",
        direction="backward",
        allow_exact_matches=True,
    )

    merged = (
        merged
        .sort_values(
            "timestamp",
            kind="stable",
        )
        .drop(
            columns=["_volume_merge_clock"]
        )
        .reset_index(drop=True)
    )

    return merged


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
