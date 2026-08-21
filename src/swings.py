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


def _pivot_flags(df: pd.DataFrame, left: int, right: int, kind: str) -> list[tuple[int, int, float, pd.Timestamp]]:
    """Return (confirmation_index, pivot_index, price, pivot_time).

    The future-right bars are used only to *confirm* a past pivot; the event is
    emitted at confirmation_index, never at pivot_index. This preserves causality.
    """
    values = df["high"].to_numpy() if kind == "high" else df["low"].to_numpy()
    events: list[tuple[int, int, float, pd.Timestamp]] = []
    n = len(df)
    for pivot in range(left, n - right):
        value = values[pivot]
        left_values = values[pivot - left : pivot]
        right_values = values[pivot + 1 : pivot + 1 + right]
        if kind == "high":
            valid = bool(np.all(value > left_values) and np.all(value >= right_values))
        else:
            valid = bool(np.all(value < left_values) and np.all(value <= right_values))
        if valid:
            confirmation = pivot + right
            events.append((confirmation, pivot, float(value), df.at[pivot, "timestamp"]))
    return events


def _add_scope(df: pd.DataFrame, scope: str, left: int, right: int) -> pd.DataFrame:
    result = df.copy()
    high_events = _pivot_flags(result, left, right, "high")
    low_events = _pivot_flags(result, left, right, "low")

    high_confirmed = np.zeros(len(result), dtype=bool)
    low_confirmed = np.zeros(len(result), dtype=bool)
    high_price = np.full(len(result), np.nan)
    low_price = np.full(len(result), np.nan)
    high_pivot_time: list[Any] = [pd.NaT] * len(result)
    low_pivot_time: list[Any] = [pd.NaT] * len(result)
    high_pivot_index = np.full(len(result), np.nan)
    low_pivot_index = np.full(len(result), np.nan)

    for confirmation, pivot, price, pivot_time in high_events:
        high_confirmed[confirmation] = True
        high_price[confirmation] = price
        high_pivot_time[confirmation] = pivot_time
        high_pivot_index[confirmation] = pivot
    for confirmation, pivot, price, pivot_time in low_events:
        low_confirmed[confirmation] = True
        low_price[confirmation] = price
        low_pivot_time[confirmation] = pivot_time
        low_pivot_index[confirmation] = pivot

    result[f"{scope}_swing_high_confirmed"] = high_confirmed
    result[f"{scope}_swing_low_confirmed"] = low_confirmed
    result[f"{scope}_swing_high_price"] = high_price
    result[f"{scope}_swing_low_price"] = low_price
    result[f"{scope}_swing_high_pivot_time"] = pd.to_datetime(high_pivot_time, utc=True)
    result[f"{scope}_swing_low_pivot_time"] = pd.to_datetime(low_pivot_time, utc=True)
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

    for i in range(len(result)):
        if high_confirmed[i]:
            latest_high = high_price[i]
            latest_high_confirmation = i
        if low_confirmed[i]:
            latest_low = low_price[i]
            latest_low_confirmation = i
        active_high.append(latest_high)
        active_low.append(latest_low)
        high_age.append(np.nan if latest_high_confirmation is None else i - latest_high_confirmation)
        low_age.append(np.nan if latest_low_confirmation is None else i - latest_low_confirmation)

    result[f"active_{scope}_swing_high"] = active_high
    result[f"active_{scope}_swing_low"] = active_low
    result[f"{scope}_swing_high_age_bars"] = high_age
    result[f"{scope}_swing_low_age_bars"] = low_age
    return result


def _premium_discount(close: pd.Series, high: pd.Series, low: pd.Series) -> tuple[pd.Series, pd.Series]:
    valid = high.notna() & low.notna() & (high > low)
    equilibrium = ((high + low) / 2.0).where(valid)
    location = pd.Series("unknown", index=close.index, dtype=object)
    location.loc[valid & (close > equilibrium)] = "premium"
    location.loc[valid & (close < equilibrium)] = "discount"
    location.loc[valid & np.isclose(close, equilibrium, atol=1e-9)] = "equilibrium"
    return equilibrium, location


def enrich_swings(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    _validate(df)
    result = df.sort_values("timestamp").copy().reset_index(drop=True)
    section = config.get("swings", {})
    internal = section.get("internal", {})
    external = section.get("external", {})
    internal_left = int(internal.get("left_bars", 2))
    internal_right = int(internal.get("right_bars", 2))
    external_left = int(external.get("left_bars", 5))
    external_right = int(external.get("right_bars", 5))

    result = _add_scope(result, "internal", internal_left, internal_right)
    result = _add_scope(result, "external", external_left, external_right)

    result["internal_equilibrium"], result["internal_premium_discount"] = _premium_discount(
        result["close"], result["active_internal_swing_high"], result["active_internal_swing_low"]
    )
    result["external_equilibrium"], result["external_premium_discount"] = _premium_discount(
        result["close"], result["active_external_swing_high"], result["active_external_swing_low"]
    )
    result["internal_structure_range_high"] = result["active_internal_swing_high"]
    result["internal_structure_range_low"] = result["active_internal_swing_low"]
    result["external_structure_range_high"] = result["active_external_swing_high"]
    result["external_structure_range_low"] = result["active_external_swing_low"]
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
