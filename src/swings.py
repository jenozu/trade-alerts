from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close"}


class SwingError(RuntimeError):
    """Raised when causal swing detection cannot be completed safely."""


@dataclass(frozen=True)
class SwingSummary:
    rows: int
    internal_swing_highs: int
    internal_swing_lows: int
    external_swing_highs: int
    external_swing_lows: int


def _validate(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise SwingError(f"Missing required columns: {sorted(missing)}")
    if df.empty:
        raise SwingError("Cannot detect swings on an empty dataframe.")
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        raise SwingError("'timestamp' must be datetime.")
    if getattr(df["timestamp"].dt, "tz", None) is None:
        raise SwingError("'timestamp' must be timezone-aware.")


def _pivot_flags(
    df: pd.DataFrame,
    left: int,
    right: int,
    kind: str,
) -> list[tuple[int, int, float, pd.Timestamp, float]]:
    """Return confirmation/pivot metadata plus causal prominence.

    Right-side bars are used only to confirm a historical pivot.
    Nothing is emitted before the confirmation bar.
    """
    values = (
        df["high"].to_numpy()
        if kind == "high"
        else df["low"].to_numpy()
    )

    events: list[
        tuple[int, int, float, pd.Timestamp, float]
    ] = []

    n = len(df)

    for pivot in range(left, n - right):
        value = values[pivot]
        left_values = values[pivot - left:pivot]
        right_values = values[pivot + 1:pivot + 1 + right]

        if kind == "high":
            valid = bool(
                np.all(value > left_values)
                and np.all(value >= right_values)
            )
            prominence = (
                float(value)
                - float(max(left_values.max(), right_values.max()))
            )
        else:
            valid = bool(
                np.all(value < left_values)
                and np.all(value <= right_values)
            )
            prominence = (
                float(min(left_values.min(), right_values.min()))
                - float(value)
            )

        if valid:
            confirmation = pivot + right
            events.append(
                (
                    confirmation,
                    pivot,
                    float(value),
                    df.at[pivot, "timestamp"],
                    max(0.0, prominence),
                )
            )

    return events

def _add_scope(
    df: pd.DataFrame,
    scope: str,
    left: int,
    right: int,
    *,
    timeframe: str,
    tick_size: float,
) -> pd.DataFrame:
    result = df.copy()

    high_events = _pivot_flags(
        result, left, right, "high"
    )
    low_events = _pivot_flags(
        result, left, right, "low"
    )

    n = len(result)

    high_confirmed = np.zeros(n, dtype=bool)
    low_confirmed = np.zeros(n, dtype=bool)

    high_price = np.full(n, np.nan)
    low_price = np.full(n, np.nan)

    high_strength = np.full(n, np.nan)
    low_strength = np.full(n, np.nan)

    high_pivot_time: list[Any] = [pd.NaT] * n
    low_pivot_time: list[Any] = [pd.NaT] * n

    high_pivot_index = np.full(n, np.nan)
    low_pivot_index = np.full(n, np.nan)

    high_timeframe: list[str | None] = [None] * n
    low_timeframe: list[str | None] = [None] * n

    for (
        confirmation,
        pivot,
        price,
        pivot_time,
        strength,
    ) in high_events:
        high_confirmed[confirmation] = True
        high_price[confirmation] = price
        high_strength[confirmation] = strength
        high_pivot_time[confirmation] = pivot_time
        high_pivot_index[confirmation] = pivot
        high_timeframe[confirmation] = timeframe

    for (
        confirmation,
        pivot,
        price,
        pivot_time,
        strength,
    ) in low_events:
        low_confirmed[confirmation] = True
        low_price[confirmation] = price
        low_strength[confirmation] = strength
        low_pivot_time[confirmation] = pivot_time
        low_pivot_index[confirmation] = pivot
        low_timeframe[confirmation] = timeframe

    result[f"{scope}_swing_high_confirmed"] = high_confirmed
    result[f"{scope}_swing_low_confirmed"] = low_confirmed

    result[f"{scope}_swing_high_price"] = high_price
    result[f"{scope}_swing_low_price"] = low_price

    result[f"{scope}_swing_high_strength_points"] = high_strength
    result[f"{scope}_swing_low_strength_points"] = low_strength

    result[f"{scope}_swing_high_strength_ticks"] = (
        high_strength / tick_size
    )
    result[f"{scope}_swing_low_strength_ticks"] = (
        low_strength / tick_size
    )

    result[f"{scope}_swing_high_timeframe"] = high_timeframe
    result[f"{scope}_swing_low_timeframe"] = low_timeframe

    result[f"{scope}_swing_high_pivot_time"] = pd.to_datetime(
        high_pivot_time, utc=True
    )
    result[f"{scope}_swing_low_pivot_time"] = pd.to_datetime(
        low_pivot_time, utc=True
    )

    result[f"{scope}_swing_high_pivot_index"] = high_pivot_index
    result[f"{scope}_swing_low_pivot_index"] = low_pivot_index

    active_high: list[float] = []
    active_low: list[float] = []

    high_age: list[float] = []
    low_age: list[float] = []

    latest_high = np.nan
    latest_low = np.nan

    latest_high_confirmation: int | None = None
    latest_low_confirmation: int | None = None

    for i in range(n):
        if high_confirmed[i]:
            latest_high = high_price[i]
            latest_high_confirmation = i

        if low_confirmed[i]:
            latest_low = low_price[i]
            latest_low_confirmation = i

        active_high.append(latest_high)
        active_low.append(latest_low)

        high_age.append(
            np.nan
            if latest_high_confirmation is None
            else i - latest_high_confirmation
        )

        low_age.append(
            np.nan
            if latest_low_confirmation is None
            else i - latest_low_confirmation
        )

    result[f"active_{scope}_swing_high"] = active_high
    result[f"active_{scope}_swing_low"] = active_low

    result[f"{scope}_swing_high_age_bars"] = high_age
    result[f"{scope}_swing_low_age_bars"] = low_age

    return result


def _add_equal_clusters(
    df: pd.DataFrame,
    *,
    scope: str,
    kind: str,
    tolerance_points: float,
) -> pd.DataFrame:
    """Cluster successive confirmed swings near the same price."""

    result = df.copy()

    confirmed_col = f"{scope}_swing_{kind}_confirmed"
    price_col = f"{scope}_swing_{kind}_price"

    cluster_ids: list[str | None] = [None] * len(result)
    cluster_counts = np.zeros(len(result), dtype=int)
    cluster_levels = np.full(len(result), np.nan)
    equal_flags = np.zeros(len(result), dtype=bool)

    cluster_number = 0
    cluster_count = 0
    cluster_center: float | None = None

    for i in range(len(result)):
        if not bool(result.at[i, confirmed_col]):
            continue

        price = float(result.at[i, price_col])

        if (
            cluster_center is not None
            and abs(price - cluster_center) <= tolerance_points
        ):
            cluster_count += 1
            cluster_center = (
                (
                    cluster_center * (cluster_count - 1)
                )
                + price
            ) / cluster_count
        else:
            cluster_number += 1
            cluster_count = 1
            cluster_center = price

        cluster_ids[i] = (
            f"{scope}_{kind}_cluster_{cluster_number}"
        )
        cluster_counts[i] = cluster_count
        cluster_levels[i] = cluster_center
        equal_flags[i] = cluster_count >= 2

    result[f"{scope}_swing_{kind}_equal"] = equal_flags
    result[f"{scope}_swing_{kind}_equal_cluster_id"] = cluster_ids
    result[f"{scope}_swing_{kind}_equal_cluster_count"] = cluster_counts
    result[f"{scope}_swing_{kind}_equal_cluster_level"] = cluster_levels

    return result


def _add_swept_state(
    df: pd.DataFrame,
    *,
    scope: str,
    penetration_points: float,
    require_close_back: bool,
) -> pd.DataFrame:
    """Track causal sweep state for the currently active swing."""

    result = df.copy()
    n = len(result)

    high_event = np.zeros(n, dtype=bool)
    low_event = np.zeros(n, dtype=bool)

    high_state = np.zeros(n, dtype=bool)
    low_state = np.zeros(n, dtype=bool)

    active_high = np.nan
    active_low = np.nan

    high_swept = False
    low_swept = False

    for i in range(n):
        if bool(result.at[i, f"{scope}_swing_high_confirmed"]):
            active_high = float(
                result.at[i, f"{scope}_swing_high_price"]
            )
            high_swept = False

        if bool(result.at[i, f"{scope}_swing_low_confirmed"]):
            active_low = float(
                result.at[i, f"{scope}_swing_low_price"]
            )
            low_swept = False

        if pd.notna(active_high) and not high_swept:
            penetrated = (
                float(result.at[i, "high"])
                >= active_high + penetration_points
            )
            rejected = (
                float(result.at[i, "close"]) < active_high
                if require_close_back
                else penetrated
            )

            if penetrated and rejected:
                high_event[i] = True
                high_swept = True

        if pd.notna(active_low) and not low_swept:
            penetrated = (
                float(result.at[i, "low"])
                <= active_low - penetration_points
            )
            rejected = (
                float(result.at[i, "close"]) > active_low
                if require_close_back
                else penetrated
            )

            if penetrated and rejected:
                low_event[i] = True
                low_swept = True

        high_state[i] = high_swept
        low_state[i] = low_swept

    result[f"{scope}_swing_high_sweep_event"] = high_event
    result[f"{scope}_swing_low_sweep_event"] = low_event

    result[f"active_{scope}_swing_high_swept"] = high_state
    result[f"active_{scope}_swing_low_swept"] = low_state

    return result

def _premium_discount(close: pd.Series, high: pd.Series, low: pd.Series) -> tuple[pd.Series, pd.Series]:
    valid = high.notna() & low.notna() & (high > low)
    equilibrium = ((high + low) / 2.0).where(valid)
    location = pd.Series("unknown", index=close.index, dtype=object)
    location.loc[valid & (close > equilibrium)] = "premium"
    location.loc[valid & (close < equilibrium)] = "discount"
    location.loc[valid & np.isclose(close, equilibrium, atol=1e-9)] = "equilibrium"
    return equilibrium, location


def enrich_swings(
    df: pd.DataFrame,
    config: dict[str, Any],
    *,
    timeframe: str | None = None,
) -> pd.DataFrame:
    _validate(df)

    result = (
        df.sort_values("timestamp")
        .copy()
        .reset_index(drop=True)
    )

    section = config.get("swings", {})

    internal = section.get("internal", {})
    external = section.get("external", {})

    internal_left = int(internal.get("left_bars", 2))
    internal_right = int(internal.get("right_bars", 2))

    external_left = int(external.get("left_bars", 5))
    external_right = int(external.get("right_bars", 5))

    if timeframe is None:
        timeframe = str(section.get("timeframe", "1m"))

    tick_size = float(
        config.get("market", {}).get("tick_size", 0.25)
    )

    if tick_size <= 0:
        raise SwingError("market.tick_size must be > 0.")

    equal_section = section.get("equal_levels", {})
    tolerance_ticks = float(
        equal_section.get("tolerance_ticks", 2.0)
    )

    if tolerance_ticks < 0:
        raise SwingError(
            "swings.equal_levels.tolerance_ticks must be >= 0."
        )

    tolerance_points = tolerance_ticks * tick_size

    sweep = config.get("liquidity", {}).get("sweep", {})

    minimum_penetration_ticks = float(
        sweep.get("minimum_penetration_ticks", 1.0)
    )

    penetration_points = (
        minimum_penetration_ticks * tick_size
    )

    require_close_back = bool(
        sweep.get("require_close_back_through_level", True)
    )

    result = _add_scope(
        result,
        "internal",
        internal_left,
        internal_right,
        timeframe=timeframe,
        tick_size=tick_size,
    )

    result = _add_scope(
        result,
        "external",
        external_left,
        external_right,
        timeframe=timeframe,
        tick_size=tick_size,
    )

    for scope in ("internal", "external"):
        for kind in ("high", "low"):
            result = _add_equal_clusters(
                result,
                scope=scope,
                kind=kind,
                tolerance_points=tolerance_points,
            )

        result = _add_swept_state(
            result,
            scope=scope,
            penetration_points=penetration_points,
            require_close_back=require_close_back,
        )

    result[
        "internal_equilibrium"
    ], result[
        "internal_premium_discount"
    ] = _premium_discount(
        result["close"],
        result["active_internal_swing_high"],
        result["active_internal_swing_low"],
    )

    result[
        "external_equilibrium"
    ], result[
        "external_premium_discount"
    ] = _premium_discount(
        result["close"],
        result["active_external_swing_high"],
        result["active_external_swing_low"],
    )

    result["internal_structure_range_high"] = (
        result["active_internal_swing_high"]
    )
    result["internal_structure_range_low"] = (
        result["active_internal_swing_low"]
    )

    result["external_structure_range_high"] = (
        result["active_external_swing_high"]
    )
    result["external_structure_range_low"] = (
        result["active_external_swing_low"]
    )

    return result

def swing_summary(df: pd.DataFrame) -> SwingSummary:
    def count(column: str) -> int:
        return int(df[column].fillna(False).sum()) if column in df.columns else 0
    return SwingSummary(
        rows=len(df),
        internal_swing_highs=count("internal_swing_high_confirmed"),
        internal_swing_lows=count("internal_swing_low_confirmed"),
        external_swing_highs=count("external_swing_high_confirmed"),
        external_swing_lows=count("external_swing_low_confirmed"),
    )


def _event_table(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for scope in ("internal", "external"):
        for kind in ("high", "low"):
            confirmed = f"{scope}_swing_{kind}_confirmed"
            price = f"{scope}_swing_{kind}_price"
            pivot_time = f"{scope}_swing_{kind}_pivot_time"
            if confirmed not in df.columns:
                continue
            for _, row in df.loc[df[confirmed]].iterrows():
                rows.append(
                    {
                        "confirmation_time": row["timestamp"],
                        "pivot_time": row[pivot_time],
                        "scope": scope,
                        "kind": kind,
                        "price": row[price],
                        "session_date": row.get("session_date"),
                    }
                )
    table = pd.DataFrame(rows)
    if not table.empty:
        table = table.sort_values("confirmation_time").reset_index(drop=True)
    return table


def save_swing_outputs(df: pd.DataFrame, output_directory: str | Path) -> dict[str, Path]:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "nq_1m_swings.parquet"
    events = directory / "swing_events.csv"
    try:
        df.to_parquet(path, index=False)
    except ImportError as exc:
        raise SwingError("Saving Parquet requires pyarrow.") from exc
    _event_table(df).to_csv(events, index=False)
    return {"swing_features": path, "swing_events": events}
