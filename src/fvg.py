from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


# ============================================================
# CONSTANTS
# ============================================================

DEFAULT_STRATEGY_CONFIG = Path("config/strategy.yaml")

REQUIRED_COLUMNS = {
    "timestamp",
    "open",
    "high",
    "low",
    "close",
}

DEFAULT_TICK_SIZE = 0.25


# ============================================================
# EXCEPTIONS
# ============================================================

class FVGError(RuntimeError):
    """Raised when FVG calculations cannot be completed safely."""


# ============================================================
# DATA MODELS
# ============================================================

@dataclass(frozen=True)
class FVGSettings:
    tick_size: float
    minimum_gap_ticks: int
    minimum_gap_atr_fraction: float
    require_displacement_candle: bool
    track_first_touch: bool
    track_fill_percentage: bool
    full_fill_percentage: float
    invalidate_on_full_fill: bool
    retest_enabled: bool
    require_close_hold: bool
    maximum_bars_after_creation: int
    inverse_fvg_enabled: bool
    require_close_through_original_fvg: bool


@dataclass(frozen=True)
class FVGSummary:
    rows: int
    bullish_created: int
    bearish_created: int
    bullish_first_touches: int
    bearish_first_touches: int
    bullish_full_fills: int
    bearish_full_fills: int
    bullish_retest_holds: int
    bearish_retest_holds: int
    bullish_ifvgs: int
    bearish_ifvgs: int


# ============================================================
# CONFIG LOADING
# ============================================================

def load_strategy_config(filepath: str | Path = DEFAULT_STRATEGY_CONFIG) -> dict[str, Any]:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Strategy configuration file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
    except Exception as exc:
        raise FVGError(f"Could not load strategy configuration: {path}") from exc
    if not isinstance(config, dict):
        raise FVGError("strategy.yaml did not produce a dictionary.")
    return config


# ============================================================
# VALIDATION / PREPARATION
# ============================================================

def validate_input_dataframe(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise FVGError(
            "Missing required columns for FVG calculations: "
            f"{sorted(missing)}"
        )
    if df.empty:
        raise FVGError("Cannot calculate FVGs on an empty dataframe.")
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        raise FVGError("'timestamp' must be a pandas datetime column.")
    timezone = getattr(df["timestamp"].dt, "tz", None)
    if timezone is None:
        raise FVGError("'timestamp' must be timezone-aware.")
    for column in ["open", "high", "low", "close"]:
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise FVGError(f"'{column}' must be numeric.")


def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    validate_input_dataframe(df)
    return df.sort_values("timestamp").copy().reset_index(drop=True)


# ============================================================
# SETTINGS
# ============================================================

def build_fvg_settings(config: dict[str, Any]) -> FVGSettings:
    market = config.get("market", {})
    fvg = config.get("fvg", {})
    detection = fvg.get("detection", {})
    mitigation = fvg.get("mitigation", {})
    retest = fvg.get("retest", {})
    inverse = fvg.get("inverse_fvg", {})

    return FVGSettings(
        tick_size=float(market.get("tick_size", DEFAULT_TICK_SIZE)),
        minimum_gap_ticks=int(detection.get("minimum_gap_ticks", 1)),
        minimum_gap_atr_fraction=float(detection.get("minimum_gap_atr_fraction", 0.0)),
        require_displacement_candle=bool(detection.get("require_displacement_candle", False)),
        track_first_touch=bool(mitigation.get("track_first_touch", True)),
        track_fill_percentage=bool(mitigation.get("track_fill_percentage", True)),
        full_fill_percentage=float(mitigation.get("full_fill_percentage", 1.0)),
        invalidate_on_full_fill=bool(mitigation.get("invalidate_on_full_fill", False)),
        retest_enabled=bool(retest.get("enabled", True)),
        require_close_hold=bool(retest.get("require_close_hold", True)),
        maximum_bars_after_creation=int(retest.get("maximum_bars_after_creation", 20)),
        inverse_fvg_enabled=bool(inverse.get("enabled", True)),
        require_close_through_original_fvg=bool(inverse.get("require_close_through_original_fvg", True)),
    )


# ============================================================
# BASIC 3-CANDLE FVG DETECTION
# ============================================================

def detect_fvg_creation(
    df: pd.DataFrame,
    *,
    settings: FVGSettings,
    atr_column: str | None = None,
) -> pd.DataFrame:
    result = prepare_dataframe(df)

    prior_2_high = result["high"].shift(2)
    prior_2_low = result["low"].shift(2)

    bullish_gap = result["low"] - prior_2_high
    bearish_gap = prior_2_low - result["high"]

    minimum_gap_points = settings.tick_size * settings.minimum_gap_ticks

    bullish = bullish_gap >= minimum_gap_points
    bearish = bearish_gap >= minimum_gap_points

    if (
        settings.minimum_gap_atr_fraction > 0
        and atr_column is not None
        and atr_column in result.columns
    ):
        required_gap = result[atr_column] * settings.minimum_gap_atr_fraction
        bullish &= bullish_gap >= required_gap
        bearish &= bearish_gap >= required_gap

    if settings.require_displacement_candle:
        bullish_displacement = result.get(
            "bullish_displacement",
            pd.Series(False, index=result.index),
        )
        bearish_displacement = result.get(
            "bearish_displacement",
            pd.Series(False, index=result.index),
        )
        bullish &= bullish_displacement
        bearish &= bearish_displacement

    result["bullish_fvg_created"] = bullish.fillna(False)
    result["bearish_fvg_created"] = bearish.fillna(False)

    result["bullish_fvg_lower"] = np.where(
        result["bullish_fvg_created"], prior_2_high, np.nan
    )
    result["bullish_fvg_upper"] = np.where(
        result["bullish_fvg_created"], result["low"], np.nan
    )
    result["bearish_fvg_lower"] = np.where(
        result["bearish_fvg_created"], result["high"], np.nan
    )
    result["bearish_fvg_upper"] = np.where(
        result["bearish_fvg_created"], prior_2_low, np.nan
    )

    result["bullish_fvg_size_points"] = np.where(
        result["bullish_fvg_created"], bullish_gap, np.nan
    )
    result["bearish_fvg_size_points"] = np.where(
        result["bearish_fvg_created"], bearish_gap, np.nan
    )

    result["bullish_fvg_midpoint"] = (
        result["bullish_fvg_lower"] + result["bullish_fvg_upper"]
    ) / 2.0
    result["bearish_fvg_midpoint"] = (
        result["bearish_fvg_lower"] + result["bearish_fvg_upper"]
    ) / 2.0

    return result


# ============================================================
# FVG OBJECT TABLE
# ============================================================

def build_fvg_table(df: pd.DataFrame) -> pd.DataFrame:
    fvgs: list[dict[str, Any]] = []
    next_id = 1

    for index, row in df.iterrows():
        if bool(row.get("bullish_fvg_created", False)):
            fvgs.append(
                {
                    "fvg_id": next_id,
                    "direction": "bullish",
                    "creation_index": index,
                    "creation_time": row["timestamp"],
                    "lower_bound": float(row["bullish_fvg_lower"]),
                    "upper_bound": float(row["bullish_fvg_upper"]),
                    "midpoint": float(row["bullish_fvg_midpoint"]),
                    "size_points": float(row["bullish_fvg_size_points"]),
                    "session_date": row.get("session_date"),
                }
            )
            next_id += 1

        if bool(row.get("bearish_fvg_created", False)):
            fvgs.append(
                {
                    "fvg_id": next_id,
                    "direction": "bearish",
                    "creation_index": index,
                    "creation_time": row["timestamp"],
                    "lower_bound": float(row["bearish_fvg_lower"]),
                    "upper_bound": float(row["bearish_fvg_upper"]),
                    "midpoint": float(row["bearish_fvg_midpoint"]),
                    "size_points": float(row["bearish_fvg_size_points"]),
                    "session_date": row.get("session_date"),
                }
            )
            next_id += 1

    return pd.DataFrame(fvgs)


# ============================================================
# FILL PERCENTAGE
# ============================================================

def calculate_fill_percentage(
    *,
    direction: str,
    lower_bound: float,
    upper_bound: float,
    bar_high: float,
    bar_low: float,
) -> float:
    size = upper_bound - lower_bound
    if size <= 0:
        return 0.0

    if direction == "bullish":
        if bar_low >= upper_bound:
            return 0.0
        fill = (upper_bound - bar_low) / size
    elif direction == "bearish":
        if bar_high <= lower_bound:
            return 0.0
        fill = (bar_high - lower_bound) / size
    else:
        raise ValueError("direction must be 'bullish' or 'bearish'.")

    return float(np.clip(fill, 0.0, 1.0))


# ============================================================
# TRACK FVG LIFECYCLE
# ============================================================

def track_fvg_lifecycle(
    df: pd.DataFrame,
    fvg_table: pd.DataFrame,
    *,
    settings: FVGSettings,
) -> pd.DataFrame:
    if fvg_table.empty:
        return fvg_table.copy()

    tracked = fvg_table.copy()
    tracked["first_touch_time"] = pd.NaT
    tracked["first_touch_index"] = np.nan
    tracked["maximum_fill_percentage"] = 0.0
    tracked["full_fill_time"] = pd.NaT
    tracked["retest_hold_time"] = pd.NaT
    tracked["invalidated"] = False
    tracked["invalidation_time"] = pd.NaT
    tracked["inverse_fvg_created"] = False
    tracked["inverse_fvg_time"] = pd.NaT

    for fvg_row_index, fvg in tracked.iterrows():
        direction = fvg["direction"]
        creation_index = int(fvg["creation_index"])
        lower = float(fvg["lower_bound"])
        upper = float(fvg["upper_bound"])

        max_fill = 0.0
        first_touch_recorded = False
        end_index = min(
            len(df) - 1,
            creation_index + settings.maximum_bars_after_creation,
        )

        for i in range(creation_index + 1, end_index + 1):
            row = df.iloc[i]
            fill = calculate_fill_percentage(
                direction=direction,
                lower_bound=lower,
                upper_bound=upper,
                bar_high=float(row["high"]),
                bar_low=float(row["low"]),
            )

            if fill > max_fill:
                max_fill = fill

            if fill > 0 and not first_touch_recorded:
                tracked.at[fvg_row_index, "first_touch_time"] = row["timestamp"]
                tracked.at[fvg_row_index, "first_touch_index"] = i
                first_touch_recorded = True

            if (
                settings.retest_enabled
                and fill > 0
                and pd.isna(tracked.at[fvg_row_index, "retest_hold_time"])
            ):
                if direction == "bullish":
                    held = float(row["close"]) > lower if settings.require_close_hold else True
                else:
                    held = float(row["close"]) < upper if settings.require_close_hold else True
                if held:
                    tracked.at[fvg_row_index, "retest_hold_time"] = row["timestamp"]

            if (
                fill >= settings.full_fill_percentage
                and pd.isna(tracked.at[fvg_row_index, "full_fill_time"])
            ):
                tracked.at[fvg_row_index, "full_fill_time"] = row["timestamp"]
                if settings.invalidate_on_full_fill:
                    tracked.at[fvg_row_index, "invalidated"] = True
                    tracked.at[fvg_row_index, "invalidation_time"] = row["timestamp"]

            if settings.inverse_fvg_enabled:
                if direction == "bullish":
                    if settings.require_close_through_original_fvg:
                        inverse = float(row["close"]) < lower
                    else:
                        inverse = float(row["low"]) < lower
                else:
                    if settings.require_close_through_original_fvg:
                        inverse = float(row["close"]) > upper
                    else:
                        inverse = float(row["high"]) > upper

                if inverse and not bool(tracked.at[fvg_row_index, "inverse_fvg_created"]):
                    tracked.at[fvg_row_index, "inverse_fvg_created"] = True
                    tracked.at[fvg_row_index, "inverse_fvg_time"] = row["timestamp"]
                    tracked.at[fvg_row_index, "invalidated"] = True
                    tracked.at[fvg_row_index, "invalidation_time"] = row["timestamp"]
                    break

        tracked.at[fvg_row_index, "maximum_fill_percentage"] = max_fill

    return tracked


# ============================================================
# EVENT FLAGS BACK ONTO BARS
# ============================================================

def attach_fvg_events_to_bars(df: pd.DataFrame, tracked_fvgs: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    event_columns = [
        "bullish_fvg_first_touch",
        "bearish_fvg_first_touch",
        "bullish_fvg_retest_hold",
        "bearish_fvg_retest_hold",
        "bullish_fvg_full_fill",
        "bearish_fvg_full_fill",
        "bullish_ifvg_created",
        "bearish_ifvg_created",
    ]
    for column in event_columns:
        result[column] = False

    if tracked_fvgs.empty:
        return result

    timestamp_lookup = {
        timestamp: index for index, timestamp in enumerate(result["timestamp"])
    }

    for _, fvg in tracked_fvgs.iterrows():
        direction = fvg["direction"]

        touch_time = fvg["first_touch_time"]
        if pd.notna(touch_time) and touch_time in timestamp_lookup:
            index = timestamp_lookup[touch_time]
            result.at[
                index,
                "bullish_fvg_first_touch" if direction == "bullish" else "bearish_fvg_first_touch",
            ] = True

        retest_time = fvg["retest_hold_time"]
        if pd.notna(retest_time) and retest_time in timestamp_lookup:
            index = timestamp_lookup[retest_time]
            result.at[
                index,
                "bullish_fvg_retest_hold" if direction == "bullish" else "bearish_fvg_retest_hold",
            ] = True

        full_fill_time = fvg["full_fill_time"]
        if pd.notna(full_fill_time) and full_fill_time in timestamp_lookup:
            index = timestamp_lookup[full_fill_time]
            result.at[
                index,
                "bullish_fvg_full_fill" if direction == "bullish" else "bearish_fvg_full_fill",
            ] = True

        inverse_time = fvg["inverse_fvg_time"]
        if pd.notna(inverse_time) and inverse_time in timestamp_lookup:
            index = timestamp_lookup[inverse_time]
            if direction == "bullish":
                result.at[index, "bearish_ifvg_created"] = True
            else:
                result.at[index, "bullish_ifvg_created"] = True

    return result


# ============================================================
# ACTIVE FVG STATE
# ============================================================

def add_nearest_active_fvg(df: pd.DataFrame, tracked_fvgs: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    output_columns = [
        "nearest_active_bullish_fvg_lower",
        "nearest_active_bullish_fvg_upper",
        "nearest_active_bullish_fvg_midpoint",
        "distance_to_bullish_fvg",
        "nearest_active_bearish_fvg_lower",
        "nearest_active_bearish_fvg_upper",
        "nearest_active_bearish_fvg_midpoint",
        "distance_to_bearish_fvg",
    ]
    for column in output_columns:
        result[column] = np.nan

    if tracked_fvgs.empty:
        return result

    for i, bar in result.iterrows():
        timestamp = bar["timestamp"]
        close = float(bar["close"])

        active = tracked_fvgs.loc[
            tracked_fvgs["creation_time"] <= timestamp
        ].copy()
        if active.empty:
            continue

        active = active.loc[
            active["invalidation_time"].isna()
            | (active["invalidation_time"] > timestamp)
        ]
        if active.empty:
            continue

        bullish = active.loc[active["direction"] == "bullish"]
        bearish = active.loc[active["direction"] == "bearish"]

        if not bullish.empty:
            bullish = bullish.copy()
            bullish["distance"] = (close - bullish["upper_bound"]).abs()
            nearest = bullish.loc[bullish["distance"].idxmin()]
            result.at[i, "nearest_active_bullish_fvg_lower"] = nearest["lower_bound"]
            result.at[i, "nearest_active_bullish_fvg_upper"] = nearest["upper_bound"]
            result.at[i, "nearest_active_bullish_fvg_midpoint"] = nearest["midpoint"]
            result.at[i, "distance_to_bullish_fvg"] = nearest["distance"]

        if not bearish.empty:
            bearish = bearish.copy()
            bearish["distance"] = (close - bearish["lower_bound"]).abs()
            nearest = bearish.loc[bearish["distance"].idxmin()]
            result.at[i, "nearest_active_bearish_fvg_lower"] = nearest["lower_bound"]
            result.at[i, "nearest_active_bearish_fvg_upper"] = nearest["upper_bound"]
            result.at[i, "nearest_active_bearish_fvg_midpoint"] = nearest["midpoint"]
            result.at[i, "distance_to_bearish_fvg"] = nearest["distance"]

    return result


# ============================================================
# GENERIC AGGREGATE EVENTS
# ============================================================

def add_aggregate_fvg_events(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["fvg_created_any"] = (
        result["bullish_fvg_created"] | result["bearish_fvg_created"]
    )
    result["fvg_retest_any"] = (
        result["bullish_fvg_retest_hold"] | result["bearish_fvg_retest_hold"]
    )
    result["ifvg_created_any"] = (
        result["bullish_ifvg_created"] | result["bearish_ifvg_created"]
    )
    return result


# ============================================================
# FULL PIPELINE
# ============================================================

def enrich_fvg_features(
    df: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    fvg_config = config.get("fvg", {})
    if not fvg_config.get("enabled", True):
        return df.copy(), pd.DataFrame()

    settings = build_fvg_settings(config)

    atr_column = None
    for candidate in ["atr_1m", "atr"]:
        if candidate in df.columns:
            atr_column = candidate
            break

    created = detect_fvg_creation(
        df,
        settings=settings,
        atr_column=atr_column,
    )
    fvg_table = build_fvg_table(created)
    tracked = track_fvg_lifecycle(
        created,
        fvg_table,
        settings=settings,
    )
    result = attach_fvg_events_to_bars(created, tracked)
    result = add_nearest_active_fvg(result, tracked)
    result = add_aggregate_fvg_events(result)
    return result, tracked


# ============================================================
# SUMMARY
# ============================================================

def fvg_summary(df: pd.DataFrame) -> FVGSummary:
    def count(column: str) -> int:
        if column not in df.columns:
            return 0
        return int(df[column].fillna(False).sum())

    return FVGSummary(
        rows=len(df),
        bullish_created=count("bullish_fvg_created"),
        bearish_created=count("bearish_fvg_created"),
        bullish_first_touches=count("bullish_fvg_first_touch"),
        bearish_first_touches=count("bearish_fvg_first_touch"),
        bullish_full_fills=count("bullish_fvg_full_fill"),
        bearish_full_fills=count("bearish_fvg_full_fill"),
        bullish_retest_holds=count("bullish_fvg_retest_hold"),
        bearish_retest_holds=count("bearish_fvg_retest_hold"),
        bullish_ifvgs=count("bullish_ifvg_created"),
        bearish_ifvgs=count("bearish_ifvg_created"),
    )


# ============================================================
# SAVE OUTPUTS
# ============================================================

def save_fvg_outputs(
    df: pd.DataFrame,
    fvg_table: pd.DataFrame,
    output_directory: str | Path,
) -> dict[str, Path]:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)

    parquet_path = directory / "nq_1m_fvg.parquet"
    lifecycle_path = directory / "fvg_lifecycle.csv"
    event_path = directory / "fvg_events.csv"

    df.to_parquet(parquet_path, index=False)
    fvg_table.to_csv(lifecycle_path, index=False)

    event_columns = [
        "timestamp",
        "timestamp_et",
        "session_date",
        "open",
        "high",
        "low",
        "close",
        "bullish_fvg_created",
        "bearish_fvg_created",
        "bullish_fvg_first_touch",
        "bearish_fvg_first_touch",
        "bullish_fvg_retest_hold",
        "bearish_fvg_retest_hold",
        "bullish_fvg_full_fill",
        "bearish_fvg_full_fill",
        "bullish_ifvg_created",
        "bearish_ifvg_created",
    ]
    available = [column for column in event_columns if column in df.columns]

    mask = pd.Series(False, index=df.index)
    for column in [
        "bullish_fvg_created",
        "bearish_fvg_created",
        "bullish_fvg_first_touch",
        "bearish_fvg_first_touch",
        "bullish_fvg_retest_hold",
        "bearish_fvg_retest_hold",
        "bullish_ifvg_created",
        "bearish_ifvg_created",
    ]:
        if column in df.columns:
            mask |= df[column].fillna(False)

    df.loc[mask, available].to_csv(event_path, index=False)

    return {
        "fvg_features": parquet_path,
        "fvg_lifecycle": lifecycle_path,
        "fvg_events": event_path,
    }


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    input_file = Path("data/processed/liquidity/nq_1m_liquidity.parquet")
    config_file = Path("config/strategy.yaml")
    output_directory = Path("data/processed/fvg")

    if not input_file.exists():
        print("\nLiquidity-enriched dataset not found.")
        print(f"Expected:\n{input_file}\n")
    else:
        print("\nLoading strategy configuration...")
        strategy_config = load_strategy_config(config_file)

        print("Loading market data...")
        data = pd.read_parquet(input_file)
        data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)

        if "timestamp_et" in data.columns:
            data["timestamp_et"] = data["timestamp"].dt.tz_convert(
                "America/New_York"
            )

        print(f"Loaded {len(data):,} bars.")
        print("Calculating FVG features...")

        enriched, lifecycle = enrich_fvg_features(data, strategy_config)
        summary = fvg_summary(enriched)

        print("\n============================================================")
        print("FVG SUMMARY")
        print("============================================================")
        print(f"Rows: {summary.rows:,}")
        print(f"Bullish FVGs created: {summary.bullish_created:,}")
        print(f"Bearish FVGs created: {summary.bearish_created:,}")
        print(f"Bullish first touches: {summary.bullish_first_touches:,}")
        print(f"Bearish first touches: {summary.bearish_first_touches:,}")
        print(f"Bullish retest holds: {summary.bullish_retest_holds:,}")
        print(f"Bearish retest holds: {summary.bearish_retest_holds:,}")
        print(f"Bullish full fills: {summary.bullish_full_fills:,}")
        print(f"Bearish full fills: {summary.bearish_full_fills:,}")
        print(f"Bullish IFVGs: {summary.bullish_ifvgs:,}")
        print(f"Bearish IFVGs: {summary.bearish_ifvgs:,}")

        print("\nRecent FVG lifecycle rows:\n")
        if lifecycle.empty:
            print("No FVGs found.")
        else:
            display_columns = [
                "fvg_id",
                "direction",
                "creation_time",
                "lower_bound",
                "upper_bound",
                "size_points",
                "first_touch_time",
                "maximum_fill_percentage",
                "retest_hold_time",
                "full_fill_time",
                "inverse_fvg_created",
                "inverse_fvg_time",
            ]
            available = [
                column for column in display_columns if column in lifecycle.columns
            ]
            print(lifecycle[available].tail(20))

        saved = save_fvg_outputs(enriched, lifecycle, output_directory)

        print("\nSaved files:")
        for name, filepath in saved.items():
            print(f"  {name}: {filepath}")

        print("\nDone.\n")
