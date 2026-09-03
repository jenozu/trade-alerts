from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd


REQUIRED_OHLC_COLUMNS = {"timestamp", "open", "high", "low", "close"}
DEFAULT_TIMEFRAMES = ("15m", "30m", "1h", "4h", "1d")
TIMEFRAME_DURATIONS = {
    "15m": pd.Timedelta(minutes=15),
    "30m": pd.Timedelta(minutes=30),
    "1h": pd.Timedelta(hours=1),
    "4h": pd.Timedelta(hours=4),
    "1d": pd.Timedelta(days=1),
}


class BiasError(RuntimeError):
    """Raised when higher-timeframe bias cannot be calculated safely."""


@dataclass(frozen=True)
class BiasSummary:
    rows: int
    bullish: int
    bearish: int
    neutral: int
    conflicts: int
    known: int
    unknown: int


def _validate_timestamp_column(df: pd.DataFrame, *, name: str) -> None:
    if "timestamp" not in df.columns:
        raise BiasError(f"{name} is missing required column: timestamp")
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        raise BiasError(f"{name} 'timestamp' must be datetime.")
    if getattr(df["timestamp"].dt, "tz", None) is None:
        raise BiasError(f"{name} 'timestamp' must be timezone-aware.")


def validate_base_dataframe(df: pd.DataFrame) -> None:
    missing = REQUIRED_OHLC_COLUMNS - set(df.columns)
    if missing:
        raise BiasError(f"Base dataframe missing columns: {sorted(missing)}")
    if df.empty:
        raise BiasError("Cannot enrich HTF bias onto an empty dataframe.")
    _validate_timestamp_column(df, name="Base dataframe")


def validate_higher_timeframe_dataframe(df: pd.DataFrame, timeframe: str) -> None:
    missing = REQUIRED_OHLC_COLUMNS - set(df.columns)
    if missing:
        raise BiasError(f"{timeframe} dataframe missing columns: {sorted(missing)}")
    if df.empty:
        raise BiasError(f"{timeframe} dataframe is empty.")
    _validate_timestamp_column(df, name=f"{timeframe} dataframe")


def _bias_config(config: Mapping[str, Any]) -> Mapping[str, Any]:
    section = config.get("higher_timeframe_bias", {})
    if not isinstance(section, Mapping):
        raise BiasError("higher_timeframe_bias configuration must be a mapping.")
    return section


def configured_timeframes(config: Mapping[str, Any]) -> list[str]:
    section = _bias_config(config)
    raw = section.get("timeframes", list(DEFAULT_TIMEFRAMES))
    if isinstance(raw, str):
        raw = [raw]
    timeframes = [str(value).strip() for value in raw if str(value).strip()]
    if not timeframes:
        raise BiasError("At least one higher-timeframe bias timeframe is required.")
    unsupported = [tf for tf in timeframes if tf not in TIMEFRAME_DURATIONS]
    if unsupported:
        raise BiasError(f"Unsupported higher-timeframe bias timeframes: {unsupported}")
    return timeframes


def _structure_parameters(config: Mapping[str, Any]) -> tuple[int, int, float]:
    section = _bias_config(config)
    structure = section.get("structure", {})
    if structure is None:
        structure = {}
    if not isinstance(structure, Mapping):
        raise BiasError("higher_timeframe_bias.structure must be a mapping.")

    left = int(structure.get("left_bars", 2))
    right = int(structure.get("right_bars", 2))

    default_buffer = 0.25
    strategy_structure = config.get("structure", {})
    if isinstance(strategy_structure, Mapping):
        default_buffer = float(strategy_structure.get("break_buffer_points", default_buffer))
    buffer_points = float(structure.get("break_buffer_points", default_buffer))

    if left < 1 or right < 1:
        raise BiasError("HTF bias swing left_bars/right_bars must be >= 1.")
    if buffer_points < 0:
        raise BiasError("HTF bias break_buffer_points cannot be negative.")

    return left, right, buffer_points


def _strict_pivot_high(values: np.ndarray, index: int, left: int, right: int) -> bool:
    value = values[index]
    if np.isnan(value):
        return False
    left_values = values[index - left:index]
    right_values = values[index + 1:index + right + 1]
    if np.isnan(left_values).any() or np.isnan(right_values).any():
        return False
    return bool((value > left_values).all() and (value > right_values).all())


def _strict_pivot_low(values: np.ndarray, index: int, left: int, right: int) -> bool:
    value = values[index]
    if np.isnan(value):
        return False
    left_values = values[index - left:index]
    right_values = values[index + 1:index + right + 1]
    if np.isnan(left_values).any() or np.isnan(right_values).any():
        return False
    return bool((value < left_values).all() and (value < right_values).all())


def _default_available_at(timestamps: pd.Series, timeframe: str) -> pd.Series:
    if timeframe == "1d":
        raise BiasError(
            "1d bias requires explicit session-aware available_at; "
            "calendar-day inference is not allowed."
        )
    return timestamps + TIMEFRAME_DURATIONS[timeframe]


def calculate_timeframe_bias(
    bars: pd.DataFrame,
    *,
    timeframe: str,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Calculate a causal structural bias for one higher timeframe.

    A swing becomes usable only after its configured right-side confirmation
    bars have closed. Bias changes only when a completed bar closes beyond the
    latest confirmed swing high/low by the configured break buffer.

    The function intentionally produces ``neutral`` until a confirmed
    structural break exists rather than inferring direction from future bars
    or from a moving-average shortcut.
    """
    if timeframe not in TIMEFRAME_DURATIONS:
        raise BiasError(f"Unsupported higher timeframe: {timeframe}")

    validate_higher_timeframe_dataframe(bars, timeframe)
    left, right, buffer_points = _structure_parameters(config)

    ordered = bars.sort_values("timestamp", kind="stable").reset_index(drop=True).copy()

    if "bar_complete" in ordered.columns:
        ordered = ordered.loc[
            ordered["bar_complete"].fillna(False).astype(bool)
        ].copy().reset_index(drop=True)

    if ordered.empty:
        columns = [
            "timestamp",
            "available_at",
            "bar_complete",
            f"bias_{timeframe}",
            f"bias_event_{timeframe}",
            f"confirmed_swing_high_{timeframe}",
            f"confirmed_swing_low_{timeframe}",
        ]
        return pd.DataFrame(columns=columns)

    if "available_at" not in ordered.columns:
        ordered["available_at"] = _default_available_at(ordered["timestamp"], timeframe)
    else:
        ordered["available_at"] = pd.to_datetime(ordered["available_at"], utc=True)

    highs = pd.to_numeric(ordered["high"], errors="coerce").to_numpy(dtype=float)
    lows = pd.to_numeric(ordered["low"], errors="coerce").to_numpy(dtype=float)
    closes = pd.to_numeric(ordered["close"], errors="coerce").to_numpy(dtype=float)
    n = len(ordered)

    confirmed_high_value = np.full(n, np.nan, dtype=float)
    confirmed_low_value = np.full(n, np.nan, dtype=float)
    confirmed_high_id = np.full(n, -1, dtype=int)
    confirmed_low_id = np.full(n, -1, dtype=int)

    for pivot_index in range(left, n - right):
        confirmation_index = pivot_index + right
        if _strict_pivot_high(highs, pivot_index, left, right):
            confirmed_high_value[confirmation_index] = highs[pivot_index]
            confirmed_high_id[confirmation_index] = pivot_index
        if _strict_pivot_low(lows, pivot_index, left, right):
            confirmed_low_value[confirmation_index] = lows[pivot_index]
            confirmed_low_id[confirmation_index] = pivot_index

    bias_values: list[str] = []
    bias_events: list[str] = []
    active_high_values = np.full(n, np.nan, dtype=float)
    active_low_values = np.full(n, np.nan, dtype=float)

    active_high = np.nan
    active_low = np.nan
    active_high_id = -1
    active_low_id = -1
    broken_high_id = -1
    broken_low_id = -1
    state = "neutral"

    for index in range(n):
        if confirmed_high_id[index] >= 0:
            active_high = confirmed_high_value[index]
            active_high_id = int(confirmed_high_id[index])

        if confirmed_low_id[index] >= 0:
            active_low = confirmed_low_value[index]
            active_low_id = int(confirmed_low_id[index])

        active_high_values[index] = active_high
        active_low_values[index] = active_low

        event = "none"
        close = closes[index]

        bullish_break = (
            active_high_id >= 0
            and active_high_id != broken_high_id
            and not np.isnan(close)
            and close > active_high + buffer_points
        )
        bearish_break = (
            active_low_id >= 0
            and active_low_id != broken_low_id
            and not np.isnan(close)
            and close < active_low - buffer_points
        )

        if bullish_break and bearish_break:
            raise BiasError(
                "Impossible simultaneous bullish/bearish HTF break at "
                f"{ordered.loc[index, 'timestamp']}."
            )
        if bullish_break:
            state = "bullish"
            event = "bullish_break"
            broken_high_id = active_high_id
        elif bearish_break:
            state = "bearish"
            event = "bearish_break"
            broken_low_id = active_low_id

        bias_values.append(state)
        bias_events.append(event)

    result = ordered.copy()
    result[f"bias_{timeframe}"] = bias_values
    result[f"bias_event_{timeframe}"] = bias_events
    result[f"confirmed_swing_high_{timeframe}"] = active_high_values
    result[f"confirmed_swing_low_{timeframe}"] = active_low_values
    result["bar_complete"] = True
    return result


def _merge_completed_bias_features(
    base: pd.DataFrame,
    higher: pd.DataFrame,
    timeframe: str,
) -> pd.DataFrame:
    """As-of merge one HTF bias onto lower-timeframe bars using available_at."""
    validate_base_dataframe(base)

    bias_column = f"bias_{timeframe}"
    event_column = f"bias_event_{timeframe}"
    high_column = f"confirmed_swing_high_{timeframe}"
    low_column = f"confirmed_swing_low_{timeframe}"

    required = {"available_at", bias_column}
    missing = required - set(higher.columns)
    if missing:
        raise BiasError(f"{timeframe} bias dataframe missing columns: {sorted(missing)}")

    right = higher.copy()
    if "bar_complete" in right.columns:
        right = right.loc[right["bar_complete"].fillna(False).astype(bool)].copy()

    columns = ["available_at", bias_column, event_column, high_column, low_column]
    columns = [column for column in columns if column in right.columns]

    right = right[columns].copy()
    right["available_at"] = pd.to_datetime(right["available_at"], utc=True)
    right = (
        right.dropna(subset=["available_at"])
        .sort_values("available_at", kind="stable")
        .drop_duplicates("available_at", keep="last")
    )

    left = base.copy()
    left["_bias_original_order"] = np.arange(len(left))
    left = left.sort_values("timestamp", kind="stable")

    if right.empty:
        for column in columns:
            if column != "available_at":
                left[column] = np.nan
        left[f"bias_available_at_{timeframe}"] = pd.NaT
        return (
            left.sort_values("_bias_original_order")
            .drop(columns=["_bias_original_order"])
            .reset_index(drop=True)
        )

    right = right.rename(columns={"available_at": f"bias_available_at_{timeframe}"})

    merged = pd.merge_asof(
        left,
        right,
        left_on="timestamp",
        right_on=f"bias_available_at_{timeframe}",
        direction="backward",
        allow_exact_matches=True,
    )

    return (
        merged.sort_values("_bias_original_order")
        .drop(columns=["_bias_original_order"])
        .reset_index(drop=True)
    )



def _bias_layer_settings(
    config: Mapping[str, Any],
    name: str,
    *,
    default_timeframes: tuple[str, ...],
    default_weights: Mapping[str, float],
) -> tuple[list[str], dict[str, float]]:
    section = _bias_config(config)
    layer = section.get(name, {})

    if not isinstance(layer, Mapping):
        raise BiasError(f"higher_timeframe_bias.{name} must be a mapping.")

    raw_timeframes = layer.get("timeframes", list(default_timeframes))
    if isinstance(raw_timeframes, str):
        raw_timeframes = [raw_timeframes]

    timeframes = [
        str(value).strip()
        for value in raw_timeframes
        if str(value).strip()
    ]

    if not timeframes:
        raise BiasError(f"{name} bias requires at least one timeframe.")

    unsupported = [
        timeframe
        for timeframe in timeframes
        if timeframe not in TIMEFRAME_DURATIONS
    ]
    if unsupported:
        raise BiasError(
            f"Unsupported {name} bias timeframes: {unsupported}"
        )

    raw_weights = layer.get("weights", default_weights)
    if not isinstance(raw_weights, Mapping):
        raise BiasError(
            f"higher_timeframe_bias.{name}.weights must be a mapping."
        )

    weights: dict[str, float] = {}
    for timeframe in timeframes:
        if timeframe not in raw_weights:
            raise BiasError(
                f"Missing {name} bias weight for timeframe '{timeframe}'."
            )

        weight = float(raw_weights[timeframe])
        if weight <= 0:
            raise BiasError(
                f"{name} bias weight for '{timeframe}' must be > 0."
            )
        weights[timeframe] = weight

    return timeframes, weights


def combine_weighted_bias(
    dataframe: pd.DataFrame,
    *,
    timeframes: list[str],
    weights: Mapping[str, float],
    prefix: str,
) -> pd.DataFrame:
    """Combine causal timeframe states using explicit deterministic weights."""

    result = dataframe.copy()

    columns = [f"bias_{timeframe}" for timeframe in timeframes]
    missing = [column for column in columns if column not in result.columns]
    if missing:
        raise BiasError(
            f"Cannot combine {prefix} bias; missing columns: {missing}"
        )

    def combine_row(row: pd.Series):
        known_count = 0
        total_weight = 0.0
        net_score = 0.0
        bullish_seen = False
        bearish_seen = False
        components: list[str] = []

        for timeframe in timeframes:
            column = f"bias_{timeframe}"
            raw = row[column]

            if pd.isna(raw):
                components.append(f"{timeframe}=unknown")
                continue

            state = str(raw).strip().lower()
            if state not in {"bullish", "bearish", "neutral"}:
                components.append(f"{timeframe}=unknown")
                continue

            weight = float(weights[timeframe])

            components.append(f"{timeframe}={state}")
            known_count += 1
            total_weight += weight

            if state == "bullish":
                net_score += weight
                bullish_seen = True
            elif state == "bearish":
                net_score -= weight
                bearish_seen = True

        conflict = bullish_seen and bearish_seen

        if net_score > 0:
            state = "bullish"
        elif net_score < 0:
            state = "bearish"
        else:
            state = "neutral"

        confidence = (
            abs(net_score) / total_weight
            if total_weight > 0
            else 0.0
        )

        return (
            state,
            confidence,
            known_count,
            conflict,
            net_score,
            "|".join(components),
        )

    combined = result.apply(combine_row, axis=1, result_type="expand")
    combined.columns = [
        f"{prefix}_bias",
        f"{prefix}_bias_confidence",
        f"{prefix}_bias_known_count",
        f"{prefix}_bias_conflict",
        f"{prefix}_bias_score",
        f"{prefix}_bias_components",
    ]

    result[combined.columns] = combined
    return result


def combine_hierarchical_bias(
    dataframe: pd.DataFrame,
    *,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Separate intraday trading bias from macro Daily/4H context."""

    intraday_timeframes, intraday_weights = _bias_layer_settings(
        config,
        "intraday",
        default_timeframes=("1h", "30m", "15m"),
        default_weights={"1h": 3.0, "30m": 2.0, "15m": 1.0},
    )

    macro_timeframes, macro_weights = _bias_layer_settings(
        config,
        "macro",
        default_timeframes=("4h", "1d"),
        default_weights={"4h": 2.0, "1d": 1.0},
    )

    configured = set(configured_timeframes(config))
    required = set(intraday_timeframes) | set(macro_timeframes)

    missing_configuration = sorted(required - configured)
    if missing_configuration:
        raise BiasError(
            "Bias hierarchy references timeframes not present in "
            f"higher_timeframe_bias.timeframes: {missing_configuration}"
        )

    result = combine_weighted_bias(
        dataframe,
        timeframes=intraday_timeframes,
        weights=intraday_weights,
        prefix="intraday",
    )

    result = combine_weighted_bias(
        result,
        timeframes=macro_timeframes,
        weights=macro_weights,
        prefix="macro",
    )

    # Compatibility aliases used by the current scorer.
    # Scorer harmonization happens later in Phase 3.
    result["htf_bias"] = result["intraday_bias"]
    result["higher_timeframe_bias"] = result["intraday_bias"]
    result["htf_bias_confidence"] = result["intraday_bias_confidence"]
    result["htf_bias_known_count"] = result["intraday_bias_known_count"]
    result["htf_bias_conflict"] = result["intraday_bias_conflict"]

    result["macro_intraday_conflict"] = (
        result["intraday_bias"].isin({"bullish", "bearish"})
        & result["macro_bias"].isin({"bullish", "bearish"})
        & (result["intraday_bias"] != result["macro_bias"])
    )

    return result


def combine_htf_bias(
    dataframe: pd.DataFrame,
    *,
    timeframes: list[str],
) -> pd.DataFrame:
    """Combine individual timeframe states with a conservative conflict policy."""
    result = dataframe.copy()
    bias_columns = [f"bias_{tf}" for tf in timeframes]

    missing = [column for column in bias_columns if column not in result.columns]
    if missing:
        raise BiasError(f"Cannot combine HTF bias; missing columns: {missing}")

    def combine_row(row: pd.Series) -> tuple[str, float, int, bool]:
        values = []
        for column in bias_columns:
            value = row[column]
            if pd.isna(value):
                continue
            normalized = str(value).strip().lower()
            if normalized in {"bullish", "bearish", "neutral"}:
                values.append(normalized)

        known = len(values)
        if known == 0:
            return "neutral", 0.0, 0, False

        bullish = sum(value == "bullish" for value in values)
        bearish = sum(value == "bearish" for value in values)
        conflict = bullish > 0 and bearish > 0

        if conflict:
            return "neutral", 0.0, known, True
        if bullish > 0:
            return "bullish", bullish / known, known, False
        if bearish > 0:
            return "bearish", bearish / known, known, False
        return "neutral", 0.0, known, False

    combined = result.apply(combine_row, axis=1, result_type="expand")
    combined.columns = [
        "htf_bias",
        "htf_bias_confidence",
        "htf_bias_known_count",
        "htf_bias_conflict",
    ]

    result[combined.columns] = combined
    result["higher_timeframe_bias"] = result["htf_bias"]
    return result


def enrich_htf_bias(
    dataframe_1m: pd.DataFrame,
    resampled_results: Mapping[str, Any],
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build and causally merge configured HTF structural biases onto 1m bars."""
    validate_base_dataframe(dataframe_1m)
    section = _bias_config(config)

    if not bool(section.get("enabled", True)):
        result = dataframe_1m.copy()
        result["intraday_bias"] = "neutral"
        result["intraday_bias_confidence"] = 0.0
        result["intraday_bias_known_count"] = 0
        result["intraday_bias_conflict"] = False
        result["intraday_bias_score"] = 0.0
        result["intraday_bias_components"] = ""

        result["macro_bias"] = "neutral"
        result["macro_bias_confidence"] = 0.0
        result["macro_bias_known_count"] = 0
        result["macro_bias_conflict"] = False
        result["macro_bias_score"] = 0.0
        result["macro_bias_components"] = ""

        result["macro_intraday_conflict"] = False

        result["htf_bias"] = "neutral"
        result["higher_timeframe_bias"] = "neutral"
        result["htf_bias_confidence"] = 0.0
        result["htf_bias_known_count"] = 0
        result["htf_bias_conflict"] = False
        return result

    timeframes = configured_timeframes(config)
    enriched = dataframe_1m.copy()

    for timeframe in timeframes:
        if timeframe not in resampled_results:
            raise BiasError(
                f"Configured HTF bias timeframe '{timeframe}' is missing from resampled results."
            )

        source = resampled_results[timeframe]
        bars = source.dataframe if hasattr(source, "dataframe") else source
        bias_frame = calculate_timeframe_bias(
            bars,
            timeframe=timeframe,
            config=config,
        )
        enriched = _merge_completed_bias_features(enriched, bias_frame, timeframe)

    # Use the production hierarchy when explicitly configured.
    # Minimal/legacy configurations continue to combine only their
    # requested timeframes, preserving backwards compatibility.
    if "intraday" in section or "macro" in section:
        return combine_hierarchical_bias(
            enriched,
            config=config,
        )

    return combine_htf_bias(
        enriched,
        timeframes=timeframes,
    )


def bias_summary(dataframe: pd.DataFrame) -> BiasSummary:
    if "htf_bias" not in dataframe.columns:
        raise BiasError("Cannot summarize bias: htf_bias column is missing.")

    values = dataframe["htf_bias"].astype("string")
    known_count = (
        pd.to_numeric(
            dataframe.get("htf_bias_known_count", pd.Series(0, index=dataframe.index)),
            errors="coerce",
        )
        .fillna(0)
        .astype(int)
    )
    conflicts = (
        dataframe.get("htf_bias_conflict", pd.Series(False, index=dataframe.index))
        .fillna(False)
        .astype(bool)
    )

    return BiasSummary(
        rows=int(len(dataframe)),
        bullish=int((values == "bullish").sum()),
        bearish=int((values == "bearish").sum()),
        neutral=int((values == "neutral").sum()),
        conflicts=int(conflicts.sum()),
        known=int((known_count > 0).sum()),
        unknown=int((known_count == 0).sum()),
    )


def save_bias_outputs(
    dataframe: pd.DataFrame,
    output_directory: str | Path,
) -> tuple[Path, Path]:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)

    parquet_path = directory / "nq_1m_bias.parquet"
    summary_path = directory / "bias_distribution.csv"

    dataframe.to_parquet(parquet_path, index=False)

    if "htf_bias" in dataframe.columns:
        distribution = (
            dataframe["htf_bias"]
            .value_counts(dropna=False)
            .rename_axis("htf_bias")
            .reset_index(name="bars")
        )
    else:
        distribution = pd.DataFrame(columns=["htf_bias", "bars"])

    distribution.to_csv(summary_path, index=False)
    return parquet_path, summary_path
