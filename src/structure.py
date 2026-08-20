from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

DEFAULT_STRATEGY_CONFIG = Path("config/strategy.yaml")
REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close"}
DEFAULT_ATR_PERIOD = 14
DEFAULT_BODY_LOOKBACK = 20


class StructureError(RuntimeError):
    """Raised when structure calculations cannot be completed safely."""


@dataclass(frozen=True)
class DisplacementSettings:
    atr_period: int
    body_lookback: int
    minimum_body_atr_multiple: float
    minimum_body_median_multiple: float
    close_extreme_fraction: float
    require_directional_close: bool
    relative_volume_confirmation_enabled: bool
    minimum_rvol: float


@dataclass(frozen=True)
class StructureSettings:
    break_method: str
    break_buffer_points: float
    bos_enabled: bool
    bos_require_confirmed_swing: bool
    mss_enabled: bool
    mss_require_confirmed_swing: bool
    mss_require_prior_liquidity_event: bool
    mss_require_displacement: bool
    choch_enabled: bool
    choch_structure_scope: str
    record_wick_breaks: bool
    wick_breaks_count_as_confirmation: bool


@dataclass(frozen=True)
class StructureSummary:
    rows: int
    bullish_displacement: int
    bearish_displacement: int
    bullish_bos: int
    bearish_bos: int
    bullish_mss: int
    bearish_mss: int
    bullish_choch: int
    bearish_choch: int


def load_strategy_config(filepath: str | Path = DEFAULT_STRATEGY_CONFIG) -> dict[str, Any]:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Strategy configuration file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
    except Exception as exc:
        raise StructureError(f"Could not load strategy configuration: {path}") from exc
    if not isinstance(config, dict):
        raise StructureError("strategy.yaml did not produce a dictionary.")
    return config


def validate_input_dataframe(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise StructureError(
            "Missing required columns for structure calculations: "
            f"{sorted(missing)}"
        )
    if df.empty:
        raise StructureError("Cannot calculate structure on an empty dataframe.")
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        raise StructureError("'timestamp' must be a pandas datetime column.")
    if getattr(df["timestamp"].dt, "tz", None) is None:
        raise StructureError("'timestamp' must be timezone-aware.")
    for column in ["open", "high", "low", "close"]:
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise StructureError(f"'{column}' must be numeric.")


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    validate_input_dataframe(df)
    return df.sort_values("timestamp").copy().reset_index(drop=True)


def build_displacement_settings(config: dict[str, Any]) -> DisplacementSettings:
    section = config.get("displacement", {})
    rvol = section.get("relative_volume_confirmation", {})
    return DisplacementSettings(
        atr_period=int(section.get("atr_period", DEFAULT_ATR_PERIOD)),
        body_lookback=int(section.get("body_lookback", DEFAULT_BODY_LOOKBACK)),
        minimum_body_atr_multiple=float(section.get("minimum_body_atr_multiple", 0.80)),
        minimum_body_median_multiple=float(section.get("minimum_body_median_multiple", 1.80)),
        close_extreme_fraction=float(section.get("close_extreme_fraction", 0.25)),
        require_directional_close=bool(section.get("require_directional_close", True)),
        relative_volume_confirmation_enabled=bool(rvol.get("enabled", False)),
        minimum_rvol=float(rvol.get("minimum_rvol", 1.25)),
    )


def build_structure_settings(config: dict[str, Any]) -> StructureSettings:
    section = config.get("structure", {})
    bos = section.get("bos", {})
    mss = section.get("mss", {})
    choch = section.get("choch", {})
    wick = section.get("wick_breaks", {})
    mss_displacement = mss.get("require_displacement", {})
    return StructureSettings(
        break_method=str(section.get("break_method", "close")),
        break_buffer_points=float(section.get("break_buffer_points", 0.25)),
        bos_enabled=bool(bos.get("enabled", True)),
        bos_require_confirmed_swing=bool(bos.get("require_confirmed_swing", True)),
        mss_enabled=bool(mss.get("enabled", True)),
        mss_require_confirmed_swing=bool(mss.get("require_confirmed_swing", True)),
        mss_require_prior_liquidity_event=bool(mss.get("require_prior_liquidity_event", False)),
        mss_require_displacement=bool(mss_displacement.get("enabled", False)),
        choch_enabled=bool(choch.get("enabled", True)),
        choch_structure_scope=str(choch.get("structure_scope", "internal")),
        record_wick_breaks=bool(wick.get("record", True)),
        wick_breaks_count_as_confirmation=bool(wick.get("count_as_confirmation", False)),
    )


def add_atr_if_missing(df: pd.DataFrame, *, period: int) -> pd.DataFrame:
    result = df.copy()
    if "atr_1m" in result.columns:
        return result
    previous_close = result["close"].shift(1)
    true_range = pd.concat(
        [
            result["high"] - result["low"],
            (result["high"] - previous_close).abs(),
            (result["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    result["atr_1m"] = true_range.rolling(window=period, min_periods=period).mean()
    return result


def add_body_statistics(df: pd.DataFrame, *, lookback: int) -> pd.DataFrame:
    result = df.copy()
    result["candle_body"] = (result["close"] - result["open"]).abs()
    result["signed_body"] = result["close"] - result["open"]
    historical_body = result["candle_body"].shift(1)
    result["median_body_previous"] = historical_body.rolling(
        window=lookback, min_periods=lookback
    ).median()
    result["mean_body_previous"] = historical_body.rolling(
        window=lookback, min_periods=lookback
    ).mean()
    return result


def add_close_location(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    candle_range = (result["high"] - result["low"]).replace(0, np.nan)
    result["close_location"] = (result["close"] - result["low"]) / candle_range
    return result


def add_displacement(df: pd.DataFrame, *, settings: DisplacementSettings) -> pd.DataFrame:
    result = prepare_dataframe(df)
    result = add_atr_if_missing(result, period=settings.atr_period)
    result = add_body_statistics(result, lookback=settings.body_lookback)
    result = add_close_location(result)

    atr = result["atr_1m"].replace(0, np.nan)
    median_body = result["median_body_previous"].replace(0, np.nan)
    result["body_atr_ratio"] = result["candle_body"] / atr
    result["body_median_ratio"] = result["candle_body"] / median_body

    bullish_direction = result["close"] > result["open"]
    bearish_direction = result["close"] < result["open"]
    bullish_close_near_extreme = result["close_location"] >= (1.0 - settings.close_extreme_fraction)
    bearish_close_near_extreme = result["close_location"] <= settings.close_extreme_fraction
    body_large_vs_atr = result["body_atr_ratio"] >= settings.minimum_body_atr_multiple
    body_large_vs_history = result["body_median_ratio"] >= settings.minimum_body_median_multiple

    bullish = body_large_vs_atr & body_large_vs_history & bullish_close_near_extreme
    bearish = body_large_vs_atr & body_large_vs_history & bearish_close_near_extreme

    if settings.require_directional_close:
        bullish &= bullish_direction
        bearish &= bearish_direction

    if settings.relative_volume_confirmation_enabled:
        rvol_column = None
        if "rvol_time_of_day" in result.columns:
            rvol_column = "rvol_time_of_day"
        elif "rvol_rolling" in result.columns:
            rvol_column = "rvol_rolling"
        if rvol_column is None:
            bullish &= False
            bearish &= False
        else:
            volume_ok = result[rvol_column] >= settings.minimum_rvol
            bullish &= volume_ok
            bearish &= volume_ok

    result["bullish_displacement"] = bullish.fillna(False)
    result["bearish_displacement"] = bearish.fillna(False)
    result["displacement_any"] = result["bullish_displacement"] | result["bearish_displacement"]
    return result


def add_internal_structure_trend(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    required = {
        "internal_swing_high_confirmed",
        "internal_swing_low_confirmed",
        "internal_swing_high_price",
        "internal_swing_low_price",
    }
    missing = required - set(result.columns)
    if missing:
        raise StructureError(
            "Internal swing columns are missing. Run swings.py before structure.py. "
            f"Missing: {sorted(missing)}"
        )

    latest_high = np.nan
    previous_high = np.nan
    latest_low = np.nan
    previous_low = np.nan
    trend = []

    for _, row in result.iterrows():
        if bool(row["internal_swing_high_confirmed"]):
            previous_high = latest_high
            latest_high = float(row["internal_swing_high_price"])
        if bool(row["internal_swing_low_confirmed"]):
            previous_low = latest_low
            latest_low = float(row["internal_swing_low_price"])

        if all(pd.notna(x) for x in [latest_high, previous_high, latest_low, previous_low]):
            if latest_high > previous_high and latest_low > previous_low:
                trend.append("bullish")
            elif latest_high < previous_high and latest_low < previous_low:
                trend.append("bearish")
            else:
                trend.append("neutral")
        else:
            trend.append("unknown")

    result["internal_structure_trend"] = trend
    return result


def detect_structure_breaks(df: pd.DataFrame, *, settings: StructureSettings) -> pd.DataFrame:
    result = df.copy()
    required = {"active_internal_swing_high", "active_internal_swing_low"}
    missing = required - set(result.columns)
    if missing:
        raise StructureError(
            "Active internal swing levels are missing. Run swings.py first. "
            f"Missing: {sorted(missing)}"
        )

    high_level = result["active_internal_swing_high"]
    low_level = result["active_internal_swing_low"]
    buffer = settings.break_buffer_points

    bullish_close_break = high_level.notna() & (result["close"] > (high_level + buffer))
    bearish_close_break = low_level.notna() & (result["close"] < (low_level - buffer))
    bullish_wick_break = high_level.notna() & (result["high"] > (high_level + buffer))
    bearish_wick_break = low_level.notna() & (result["low"] < (low_level - buffer))

    result["bullish_structure_close_break"] = bullish_close_break
    result["bearish_structure_close_break"] = bearish_close_break
    result["bullish_structure_wick_break"] = bullish_wick_break
    result["bearish_structure_wick_break"] = bearish_wick_break

    if settings.break_method == "close":
        result["bullish_structure_break"] = bullish_close_break
        result["bearish_structure_break"] = bearish_close_break
    elif settings.break_method == "wick":
        result["bullish_structure_break"] = bullish_wick_break
        result["bearish_structure_break"] = bearish_wick_break
    else:
        raise StructureError("structure.break_method must be 'close' or 'wick'.")

    return result


def deduplicate_breaks(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    bullish_event = np.zeros(len(result), dtype=bool)
    bearish_event = np.zeros(len(result), dtype=bool)
    previous_high_level = np.nan
    previous_low_level = np.nan
    high_broken = False
    low_broken = False

    for i in range(len(result)):
        current_high_level = result.at[i, "active_internal_swing_high"]
        current_low_level = result.at[i, "active_internal_swing_low"]

        if pd.notna(current_high_level) and (
            pd.isna(previous_high_level) or current_high_level != previous_high_level
        ):
            previous_high_level = current_high_level
            high_broken = False

        if pd.notna(current_low_level) and (
            pd.isna(previous_low_level) or current_low_level != previous_low_level
        ):
            previous_low_level = current_low_level
            low_broken = False

        if not high_broken and bool(result.at[i, "bullish_structure_break"]):
            bullish_event[i] = True
            high_broken = True

        if not low_broken and bool(result.at[i, "bearish_structure_break"]):
            bearish_event[i] = True
            low_broken = True

    result["bullish_structure_break_event"] = bullish_event
    result["bearish_structure_break_event"] = bearish_event
    return result


def classify_structure_events(df: pd.DataFrame, *, settings: StructureSettings) -> pd.DataFrame:
    result = df.copy()
    trend = result["internal_structure_trend"]
    bullish_break = result["bullish_structure_break_event"]
    bearish_break = result["bearish_structure_break_event"]

    bullish_bos = settings.bos_enabled & bullish_break & (trend == "bullish")
    bearish_bos = settings.bos_enabled & bearish_break & (trend == "bearish")
    bullish_countertrend = bullish_break & (trend == "bearish")
    bearish_countertrend = bearish_break & (trend == "bullish")

    if settings.choch_enabled:
        bullish_choch = bullish_countertrend
        bearish_choch = bearish_countertrend
    else:
        bullish_choch = pd.Series(False, index=result.index)
        bearish_choch = pd.Series(False, index=result.index)

    bullish_mss = bullish_countertrend.copy()
    bearish_mss = bearish_countertrend.copy()

    if settings.mss_require_prior_liquidity_event:
        bullish_mss &= result.get("recent_sell_side_sweep", pd.Series(False, index=result.index))
        bearish_mss &= result.get("recent_buy_side_sweep", pd.Series(False, index=result.index))

    if settings.mss_require_displacement:
        bullish_mss &= result["bullish_displacement"]
        bearish_mss &= result["bearish_displacement"]

    if not settings.mss_enabled:
        bullish_mss[:] = False
        bearish_mss[:] = False

    result["bullish_bos"] = bullish_bos.fillna(False)
    result["bearish_bos"] = bearish_bos.fillna(False)
    result["bullish_choch"] = bullish_choch.fillna(False)
    result["bearish_choch"] = bearish_choch.fillna(False)
    result["bullish_mss"] = bullish_mss.fillna(False)
    result["bearish_mss"] = bearish_mss.fillna(False)
    return result


def add_recent_structure_context(df: pd.DataFrame, *, lookback_bars: int = 10) -> pd.DataFrame:
    result = df.copy()
    event_map = {
        "bullish_bos": "recent_bullish_bos",
        "bearish_bos": "recent_bearish_bos",
        "bullish_mss": "recent_bullish_mss",
        "bearish_mss": "recent_bearish_mss",
        "bullish_choch": "recent_bullish_choch",
        "bearish_choch": "recent_bearish_choch",
        "bullish_displacement": "recent_bullish_displacement",
        "bearish_displacement": "recent_bearish_displacement",
    }
    for source, target in event_map.items():
        if source not in result.columns:
            continue
        result[target] = (
            result[source]
            .astype(int)
            .rolling(window=lookback_bars, min_periods=1)
            .max()
            .astype(bool)
        )
    return result


def add_core_sequence_flags(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["bullish_core_sequence"] = (
        result.get("recent_sell_side_sweep", pd.Series(False, index=result.index))
        & result.get("recent_bullish_displacement", pd.Series(False, index=result.index))
        & result.get("recent_bullish_mss", pd.Series(False, index=result.index))
    )
    result["bearish_core_sequence"] = (
        result.get("recent_buy_side_sweep", pd.Series(False, index=result.index))
        & result.get("recent_bearish_displacement", pd.Series(False, index=result.index))
        & result.get("recent_bearish_mss", pd.Series(False, index=result.index))
    )
    return result


def add_fvg_structure_sequences(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    bullish_created = result.get("bullish_fvg_created", pd.Series(False, index=result.index))
    bearish_created = result.get("bearish_fvg_created", pd.Series(False, index=result.index))
    bullish_retest = result.get("bullish_fvg_retest_hold", pd.Series(False, index=result.index))
    bearish_retest = result.get("bearish_fvg_retest_hold", pd.Series(False, index=result.index))

    recent_bullish_fvg = bullish_created.astype(int).rolling(window=10, min_periods=1).max().astype(bool)
    recent_bearish_fvg = bearish_created.astype(int).rolling(window=10, min_periods=1).max().astype(bool)

    result["bullish_core_plus_fvg"] = result["bullish_core_sequence"] & recent_bullish_fvg
    result["bearish_core_plus_fvg"] = result["bearish_core_sequence"] & recent_bearish_fvg
    result["bullish_core_plus_fvg_retest"] = result["bullish_core_sequence"] & bullish_retest
    result["bearish_core_plus_fvg_retest"] = result["bearish_core_sequence"] & bearish_retest
    return result


def build_structure_event_table(df: pd.DataFrame) -> pd.DataFrame:
    event_definitions = {
        "bullish_displacement": ("displacement", "bullish"),
        "bearish_displacement": ("displacement", "bearish"),
        "bullish_bos": ("bos", "bullish"),
        "bearish_bos": ("bos", "bearish"),
        "bullish_mss": ("mss", "bullish"),
        "bearish_mss": ("mss", "bearish"),
        "bullish_choch": ("choch", "bullish"),
        "bearish_choch": ("choch", "bearish"),
    }
    events: list[dict[str, Any]] = []
    for column, (event_type, direction) in event_definitions.items():
        if column not in df.columns:
            continue
        rows = df.loc[df[column]]
        for _, row in rows.iterrows():
            events.append(
                {
                    "timestamp": row["timestamp"],
                    "timestamp_et": row.get("timestamp_et"),
                    "session_date": row.get("session_date"),
                    "event_type": event_type,
                    "direction": direction,
                    "close": float(row["close"]),
                    "internal_structure_trend": row.get("internal_structure_trend"),
                    "active_internal_swing_high": row.get("active_internal_swing_high"),
                    "active_internal_swing_low": row.get("active_internal_swing_low"),
                    "body_atr_ratio": row.get("body_atr_ratio"),
                    "body_median_ratio": row.get("body_median_ratio"),
                    "rvol_rolling": row.get("rvol_rolling"),
                    "rvol_time_of_day": row.get("rvol_time_of_day"),
                    "snr_1m": row.get("snr_1m"),
                    "snr_5m": row.get("snr_5m"),
                }
            )
    result = pd.DataFrame(events)
    if not result.empty:
        result = result.sort_values("timestamp").reset_index(drop=True)
    return result


def enrich_structure_features(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    structure_config = config.get("structure", {})
    displacement_config = config.get("displacement", {})
    if not structure_config.get("enabled", True) and not displacement_config.get("enabled", True):
        return df.copy()

    result = prepare_dataframe(df)
    if displacement_config.get("enabled", True):
        displacement_settings = build_displacement_settings(config)
        result = add_displacement(result, settings=displacement_settings)
    else:
        result["bullish_displacement"] = False
        result["bearish_displacement"] = False
        result["displacement_any"] = False

    result = add_internal_structure_trend(result)
    structure_settings = build_structure_settings(config)
    result = detect_structure_breaks(result, settings=structure_settings)
    result = deduplicate_breaks(result)
    result = classify_structure_events(result, settings=structure_settings)
    result = add_recent_structure_context(result, lookback_bars=10)
    result = add_core_sequence_flags(result)
    result = add_fvg_structure_sequences(result)
    return result


def structure_summary(df: pd.DataFrame) -> StructureSummary:
    def count(column: str) -> int:
        if column not in df.columns:
            return 0
        return int(df[column].fillna(False).sum())

    return StructureSummary(
        rows=len(df),
        bullish_displacement=count("bullish_displacement"),
        bearish_displacement=count("bearish_displacement"),
        bullish_bos=count("bullish_bos"),
        bearish_bos=count("bearish_bos"),
        bullish_mss=count("bullish_mss"),
        bearish_mss=count("bearish_mss"),
        bullish_choch=count("bullish_choch"),
        bearish_choch=count("bearish_choch"),
    )


def save_structure_outputs(df: pd.DataFrame, output_directory: str | Path) -> dict[str, Path]:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    parquet_path = directory / "nq_1m_structure.parquet"
    event_path = directory / "structure_events.csv"
    sequence_path = directory / "core_sequences.csv"

    df.to_parquet(parquet_path, index=False)
    build_structure_event_table(df).to_csv(event_path, index=False)

    sequence_columns = [
        "timestamp",
        "timestamp_et",
        "session_date",
        "open",
        "high",
        "low",
        "close",
        "internal_structure_trend",
        "recent_sell_side_sweep",
        "recent_buy_side_sweep",
        "bullish_displacement",
        "bearish_displacement",
        "bullish_mss",
        "bearish_mss",
        "bullish_core_sequence",
        "bearish_core_sequence",
        "bullish_core_plus_fvg",
        "bearish_core_plus_fvg",
        "bullish_core_plus_fvg_retest",
        "bearish_core_plus_fvg_retest",
        "rvol_rolling",
        "rvol_time_of_day",
        "snr_1m",
        "snr_5m",
        "snr_15m",
        "snr_alignment",
        "snr_composite_quality",
    ]
    available = [column for column in sequence_columns if column in df.columns]
    sequence_mask = pd.Series(False, index=df.index)
    for column in [
        "bullish_core_sequence",
        "bearish_core_sequence",
        "bullish_core_plus_fvg",
        "bearish_core_plus_fvg",
        "bullish_core_plus_fvg_retest",
        "bearish_core_plus_fvg_retest",
    ]:
        if column in df.columns:
            sequence_mask |= df[column].fillna(False)

    df.loc[sequence_mask, available].to_csv(sequence_path, index=False)
    return {
        "structure_features": parquet_path,
        "structure_events": event_path,
        "core_sequences": sequence_path,
    }


if __name__ == "__main__":
    input_file = Path("data/processed/fvg/nq_1m_fvg.parquet")
    config_file = Path("config/strategy.yaml")
    output_directory = Path("data/processed/structure")

    if not input_file.exists():
        print("\nFVG-enriched dataset not found.")
        print(f"Expected:\n{input_file}\n")
    else:
        print("\nLoading strategy configuration...")
        strategy_config = load_strategy_config(config_file)
        print("Loading market data...")
        data = pd.read_parquet(input_file)
        data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)
        if "timestamp_et" in data.columns:
            data["timestamp_et"] = data["timestamp"].dt.tz_convert("America/New_York")

        print(f"Loaded {len(data):,} bars.")
        print("Calculating displacement and structure events...")
        enriched = enrich_structure_features(data, strategy_config)
        summary = structure_summary(enriched)

        print("\n============================================================")
        print("STRUCTURE SUMMARY")
        print("============================================================")
        print(f"Rows: {summary.rows:,}")
        print(f"Bullish displacement: {summary.bullish_displacement:,}")
        print(f"Bearish displacement: {summary.bearish_displacement:,}")
        print(f"Bullish BOS: {summary.bullish_bos:,}")
        print(f"Bearish BOS: {summary.bearish_bos:,}")
        print(f"Bullish MSS: {summary.bullish_mss:,}")
        print(f"Bearish MSS: {summary.bearish_mss:,}")
        print(f"Bullish ChoCH: {summary.bullish_choch:,}")
        print(f"Bearish ChoCH: {summary.bearish_choch:,}")

        saved = save_structure_outputs(enriched, output_directory)
        print("\nSaved files:")
        for name, filepath in saved.items():
            print(f"  {name}: {filepath}")
        print("\nDone.\n")
