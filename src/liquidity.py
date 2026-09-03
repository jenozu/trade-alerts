from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from liquidity_registry import build_liquidity_registry

REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close"}


class LiquidityError(RuntimeError):
    """Raised when liquidity tracking cannot be completed safely."""


@dataclass(frozen=True)
class LiquiditySummary:
    rows: int
    sweep_events: int
    buy_side_sweeps: int
    sell_side_sweeps: int


_BUY_STATIC = ["pdh", "pmh", "onh", "loh", "ash", "week_high"]
_SELL_STATIC = ["pdl", "pml", "onl", "lol", "asl", "week_low"]


def _validate(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise LiquidityError(f"Missing required columns: {sorted(missing)}")
    if df.empty:
        raise LiquidityError("Cannot calculate liquidity features on an empty dataframe.")
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        raise LiquidityError("'timestamp' must be datetime.")
    if getattr(df["timestamp"].dt, "tz", None) is None:
        raise LiquidityError("'timestamp' must be timezone-aware.")


def _candidate_levels(row: pd.Series, side: str) -> list[tuple[str, float]]:
    candidates: list[tuple[str, float]] = []
    names = _BUY_STATIC if side == "buy" else _SELL_STATIC
    for name in names:
        value = row.get(name)
        if pd.notna(value):
            candidates.append((name, float(value)))
    if side == "buy":
        for name in ["active_internal_swing_high", "active_external_swing_high"]:
            value = row.get(name)
            if pd.notna(value):
                candidates.append((name, float(value)))
    else:
        for name in ["active_internal_swing_low", "active_external_swing_low"]:
            value = row.get(name)
            if pd.notna(value):
                candidates.append((name, float(value)))
    return candidates


def enrich_liquidity_features(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    _validate(df)
    result = df.sort_values("timestamp").copy().reset_index(drop=True)
    section = config.get("liquidity", {})
    sweep = section.get("sweep", {})
    tick_size = float(config.get("market", {}).get("tick_size", 0.25))
    minimum_penetration_ticks = float(sweep.get("minimum_penetration_ticks", 1.0))
    penetration = minimum_penetration_ticks * tick_size
    require_close_back = bool(sweep.get("require_close_back_through_level", True))
    recent_lookback = int(sweep.get("recent_context_bars", 10))

    buy_sweep = np.zeros(len(result), dtype=bool)
    sell_sweep = np.zeros(len(result), dtype=bool)
    buy_touch = np.zeros(len(result), dtype=bool)
    sell_touch = np.zeros(len(result), dtype=bool)
    buy_source: list[str | None] = [None] * len(result)
    sell_source: list[str | None] = [None] * len(result)
    buy_level = np.full(len(result), np.nan)
    sell_level = np.full(len(result), np.nan)
    nearest_above = np.full(len(result), np.nan)
    nearest_below = np.full(len(result), np.nan)
    dist_above = np.full(len(result), np.nan)
    dist_below = np.full(len(result), np.nan)

    swept_ids: set[tuple[str, float]] = set()
    last_session = None

    for i, row in result.iterrows():
        session = row.get("session_date")
        if last_session is not None and session != last_session:
            # Session-derived levels can repeat numerically across days; reset level
            # identities at session change while swing levels remain represented by value.
            swept_ids = {key for key in swept_ids if key[0].startswith("active_")}
        last_session = session

        price = float(row["close"])
        buys = _candidate_levels(row, "buy")
        sells = _candidate_levels(row, "sell")

        available_buys = [(name, level) for name, level in buys if (name, level) not in swept_ids and level >= price]
        available_sells = [(name, level) for name, level in sells if (name, level) not in swept_ids and level <= price]
        if available_buys:
            name, level = min(available_buys, key=lambda item: item[1])
            nearest_above[i] = level
            dist_above[i] = max(0.0, level - price)
        if available_sells:
            name, level = max(available_sells, key=lambda item: item[1])
            nearest_below[i] = level
            dist_below[i] = max(0.0, price - level)

        for name, level in buys:
            identity = (name, level)
            if identity in swept_ids:
                continue
            if float(row["high"]) >= level:
                buy_touch[i] = True
            penetrated = float(row["high"]) >= level + penetration
            rejected = float(row["close"]) < level if require_close_back else penetrated
            if penetrated and rejected:
                buy_sweep[i] = True
                buy_source[i] = name
                buy_level[i] = level
                swept_ids.add(identity)
                break

        for name, level in sells:
            identity = (name, level)
            if identity in swept_ids:
                continue
            if float(row["low"]) <= level:
                sell_touch[i] = True
            penetrated = float(row["low"]) <= level - penetration
            rejected = float(row["close"]) > level if require_close_back else penetrated
            if penetrated and rejected:
                sell_sweep[i] = True
                sell_source[i] = name
                sell_level[i] = level
                swept_ids.add(identity)
                break

    result["buy_side_liquidity_touch"] = buy_touch
    result["sell_side_liquidity_touch"] = sell_touch
    result["buy_side_liquidity_sweep"] = buy_sweep
    result["sell_side_liquidity_sweep"] = sell_sweep
    result["liquidity_sweep_any"] = buy_sweep | sell_sweep
    result["buy_side_sweep_source"] = buy_source
    result["sell_side_sweep_source"] = sell_source
    result["buy_side_sweep_level"] = buy_level
    result["sell_side_sweep_level"] = sell_level
    result["recent_buy_side_sweep"] = (
        pd.Series(buy_sweep, index=result.index).astype(int).rolling(recent_lookback, min_periods=1).max().astype(bool)
    )
    result["recent_sell_side_sweep"] = (
        pd.Series(sell_sweep, index=result.index).astype(int).rolling(recent_lookback, min_periods=1).max().astype(bool)
    )
    result["nearest_unswept_liquidity_above"] = nearest_above
    result["nearest_unswept_liquidity_below"] = nearest_below
    result["distance_to_unswept_liquidity_above"] = dist_above
    result["distance_to_unswept_liquidity_below"] = dist_below
    return result


def liquidity_summary(df: pd.DataFrame) -> LiquiditySummary:
    def count(column: str) -> int:
        return int(df[column].fillna(False).sum()) if column in df.columns else 0
    buy = count("buy_side_liquidity_sweep")
    sell = count("sell_side_liquidity_sweep")
    return LiquiditySummary(rows=len(df), sweep_events=buy + sell, buy_side_sweeps=buy, sell_side_sweeps=sell)


def _event_table(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, row in df.loc[df.get("liquidity_sweep_any", pd.Series(False, index=df.index)).fillna(False)].iterrows():
        if bool(row.get("buy_side_liquidity_sweep", False)):
            rows.append({
                "timestamp": row["timestamp"], "timestamp_et": row.get("timestamp_et"),
                "session_date": row.get("session_date"), "side": "buy_side",
                "source": row.get("buy_side_sweep_source"), "level": row.get("buy_side_sweep_level"),
                "close": row["close"],
            })
        if bool(row.get("sell_side_liquidity_sweep", False)):
            rows.append({
                "timestamp": row["timestamp"], "timestamp_et": row.get("timestamp_et"),
                "session_date": row.get("session_date"), "side": "sell_side",
                "source": row.get("sell_side_sweep_source"), "level": row.get("sell_side_sweep_level"),
                "close": row["close"],
            })
    return pd.DataFrame(rows)


def save_liquidity_outputs(
    df: pd.DataFrame,
    output_directory: str | Path,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Path]:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "nq_1m_liquidity.parquet"
    events = directory / "liquidity_sweeps.csv"
    try:
        df.to_parquet(path, index=False)
    except ImportError as exc:
        raise LiquidityError("Saving Parquet requires pyarrow.") from exc
    _event_table(df).to_csv(events, index=False)

    outputs = {
        "liquidity_features": path,
        "liquidity_sweeps": events,
    }

    if config is not None:
        registry_path = (
            directory
            / "liquidity_registry.csv"
        )

        registry = build_liquidity_registry(
            df,
            config,
        )

        registry.to_csv(
            registry_path,
            index=False,
        )

        outputs[
            "liquidity_registry"
        ] = registry_path

    return outputs
