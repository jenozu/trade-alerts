#!/usr/bin/env python3
"""R6.3 — Equal partials across TP1/TP2/TP3/TP4.

This is the roadmap's distinct EXIT-C model:
  25% at +25
  25% at +50
  25% at +75
  25% at +100

The original stop remains in force for whatever position remains.
No break-even or trailing logic is added in this experiment.

The frozen TP100 baseline is replayed first as an exact parity gate.
No production settings are modified.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import gc
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.resume_r45 import (
    CANDIDATE_WEIGHTS,
    FEATURES,
    YEARS,
    load_config,
    model_config,
    read_trades,
)
from scripts.run_r45_chunked import parquet_replay
from scripts.run_r46_threshold_replay import assert_frozen_70
from backtest import (
    apply_entry_slippage,
    apply_exit_slippage,
    build_backtest_settings,
    determine_stop_price,
    directional_candidate,
    run_backtest,
)

TARGETS = (25.0, 50.0, 75.0, 100.0)
FRACTIONS = (0.25, 0.25, 0.25, 0.25)


@dataclass
class ManagedTrade:
    trade_id: int
    signal_index: int
    entry_index: int
    exit_index: int
    signal_time: Any
    entry_time: Any
    exit_time: Any
    direction: str
    entry_price: float
    initial_stop_price: float
    stop_distance_points: float
    raw_score: float
    tp1_hit: bool
    tp2_hit: bool
    tp3_hit: bool
    tp4_hit: bool
    exit_reason: str
    net_result_points: float
    net_result_r: float
    mfe_points: float
    mae_points: float
    bars_held: int
    minutes_held: float


def _price(entry: float, direction: str, points: float) -> float:
    return entry + points if direction == "long" else entry - points


def _target_hit(direction: str, target: float, high: float, low: float) -> bool:
    return high >= target if direction == "long" else low <= target


def _stop_hit(direction: str, stop: float, high: float, low: float) -> bool:
    return low <= stop if direction == "long" else high >= stop


def _points(direction: str, entry: float, exit_price: float) -> float:
    return exit_price - entry if direction == "long" else entry - exit_price


def _excursions(direction: str, entry: float, high: float, low: float) -> tuple[float, float]:
    if direction == "long":
        return max(0.0, high - entry), max(0.0, entry - low)
    return max(0.0, entry - low), max(0.0, high - entry)


def simulate_equal_partials(
    data: pd.DataFrame,
    *,
    signal_index: int,
    direction: str,
    trade_id: int,
    config: dict,
) -> ManagedTrade | None:
    settings = build_backtest_settings(config)
    if signal_index >= len(data) - 1:
        return None

    signal = data.iloc[signal_index]
    entry_index = signal_index + 1 if settings.entry_on_next_bar_open else signal_index
    entry_row = data.iloc[entry_index]
    raw_entry = float(entry_row["open"] if settings.entry_on_next_bar_open else signal["close"])
    entry = apply_entry_slippage(raw_entry, direction=direction, settings=settings)

    stop = determine_stop_price(
        signal, entry_price=entry, direction=direction, settings=settings
    )
    stop_distance = abs(entry - stop)
    if stop_distance <= 0:
        return None

    target_prices = [_price(entry, direction, points) for points in TARGETS]
    hit = [False, False, False, False]
    realized = 0.0
    remaining = 1.0

    entry_time = data.iloc[entry_index]["timestamp"]
    max_end = entry_time + pd.Timedelta(seconds=int(settings.maximum_holding_minutes) * 60)

    max_favorable = 0.0
    max_adverse = 0.0
    exit_index = entry_index
    exit_reason = "end_of_data"

    for i in range(entry_index, len(data)):
        row = data.iloc[i]
        ts = row["timestamp"]

        if ts >= max_end:
            j = max(entry_index, i - 1)
            raw_exit = float(data.iloc[j]["close"])
            exit_price = apply_exit_slippage(raw_exit, direction=direction, settings=settings)
            realized += remaining * _points(direction, entry, exit_price)
            exit_index = j
            exit_reason = "timeout"
            break

        high = float(row["high"])
        low = float(row["low"])
        fav, adv = _excursions(direction, entry, high, low)
        max_favorable = max(max_favorable, fav)
        max_adverse = max(max_adverse, adv)

        # Preserve conservative stop-first same-bar semantics.
        if _stop_hit(direction, stop, high, low):
            stop_exit = apply_exit_slippage(stop, direction=direction, settings=settings)
            realized += remaining * _points(direction, entry, stop_exit)
            exit_index = i
            exit_reason = "stop"
            break

        for idx, target in enumerate(target_prices):
            if hit[idx]:
                continue
            if _target_hit(direction, target, high, low):
                target_exit = apply_exit_slippage(
                    target, direction=direction, settings=settings
                )
                realized += FRACTIONS[idx] * _points(direction, entry, target_exit)
                remaining -= FRACTIONS[idx]
                hit[idx] = True

        if hit[3]:
            exit_index = i
            exit_reason = "tp4"
            break
    else:
        raw_exit = float(data.iloc[-1]["close"])
        exit_price = apply_exit_slippage(raw_exit, direction=direction, settings=settings)
        realized += remaining * _points(direction, entry, exit_price)
        exit_index = len(data) - 1
        exit_reason = "end_of_data"

    exit_time = data.iloc[exit_index]["timestamp"]
    return ManagedTrade(
        trade_id=trade_id,
        signal_index=signal_index,
        entry_index=entry_index,
        exit_index=exit_index,
        signal_time=signal["timestamp"],
        entry_time=entry_time,
        exit_time=exit_time,
        direction=direction,
        entry_price=entry,
        initial_stop_price=stop,
        stop_distance_points=stop_distance,
        raw_score=float(signal[f"{direction}_raw_score"]),
        tp1_hit=hit[0],
        tp2_hit=hit[1],
        tp3_hit=hit[2],
        tp4_hit=hit[3],
        exit_reason=exit_reason,
        net_result_points=realized,
        net_result_r=realized / stop_distance,
        mfe_points=max_favorable,
        mae_points=max_adverse,
        bars_held=exit_index - entry_index + 1,
        minutes_held=(exit_time - entry_time).total_seconds() / 60.0,
    )


def run_equal_partials(data: pd.DataFrame, config: dict) -> pd.DataFrame:
    settings = build_backtest_settings(config)
    ordered = data.sort_values("timestamp").copy().reset_index(drop=True)
    trades: list[ManagedTrade] = []
    blocked_until = -1
    trade_id = 1

    for i in range(len(ordered) - 1):
        if settings.maximum_one_open_trade and i <= blocked_until:
            continue

        row = ordered.iloc[i]
        candidates = [d for d in ("long", "short") if directional_candidate(row, d)]
        if not candidates:
            continue

        if len(candidates) == 2:
            long_score = float(row["long_raw_score"])
            short_score = float(row["short_raw_score"])
            if long_score > short_score:
                candidates = ["long"]
            elif short_score > long_score:
                candidates = ["short"]
            else:
                continue

        trade = simulate_equal_partials(
            ordered,
            signal_index=i,
            direction=candidates[0],
            trade_id=trade_id,
            config=config,
        )
        if trade is None:
            continue

        trades.append(trade)
        trade_id += 1
        if settings.maximum_one_open_trade:
            blocked_until = trade.exit_index

    return pd.DataFrame([asdict(t) for t in trades])


def metrics(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {"trades": 0}

    pnl = pd.to_numeric(trades["net_result_points"], errors="raise")
    gp = float(pnl[pnl > 0].sum())
    gl = float(-pnl[pnl < 0].sum())
    equity = pnl.cumsum()
    dd = equity.cummax() - equity

    return {
        "trades": int(len(trades)),
        "wins": int((pnl > 0).sum()),
        "win_rate": float((pnl > 0).mean()),
        "net_points": float(pnl.sum()),
        "expectancy_points": float(pnl.mean()),
        "expectancy_r": float(trades["net_result_r"].mean()),
        "profit_factor": gp / gl if gl > 0 else None,
        "max_drawdown_points": float(dd.max()),
        "tp1_hit_rate": float(trades["tp1_hit"].mean()),
        "tp2_hit_rate": float(trades["tp2_hit"].mean()),
        "tp3_hit_rate": float(trades["tp3_hit"].mean()),
        "tp4_hit_rate": float(trades["tp4_hit"].mean()),
        "average_mfe_points": float(trades["mfe_points"].mean()),
        "average_mae_points": float(trades["mae_points"].mean()),
        "average_hold_minutes": float(trades["minutes_held"].mean()),
    }


def replay_year(year: int, *, batch_rows: int, archive: Path, output: Path) -> None:
    frozen_path = archive / str(year) / "baseline" / "trades.csv"
    if not frozen_path.is_file():
        raise FileNotFoundError(frozen_path)

    config = model_config(
        load_config(Path("config/strategy.yaml")),
        CANDIDATE_WEIGHTS["baseline"],
    )
    scored = parquet_replay(FEATURES[year], config, batch_rows)
    frozen = read_trades(frozen_path)

    print(f"===== R6.3 PARITY GATE: {year} / CONTROL TP100 =====", flush=True)
    control = run_backtest(scored, config)
    assert_frozen_70(control, frozen)
    print(f"EXACT CONTROL PARITY PASSED: {len(frozen)} trades", flush=True)

    trades = run_equal_partials(scored, config)
    outdir = output / str(year) / "equal_partials"
    outdir.mkdir(parents=True, exist_ok=True)
    trades.to_csv(outdir / "trades.csv", index=False)

    row = {"research_year": year, "model": "equal_partials", **metrics(trades)}
    (outdir / "metrics.json").write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    pd.DataFrame([row]).to_csv(output / f"summary_{year}.csv", index=False)

    print(
        f"R6.3 {year} equal_partials: trades={row['trades']}, "
        f"net={row['net_points']:.2f}, exp={row['expectancy_points']:.4f}, "
        f"PF={row['profit_factor']:.4f}, DD={row['max_drawdown_points']:.2f}",
        flush=True,
    )

    del scored
    gc.collect()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--year", required=True, type=int, choices=YEARS)
    p.add_argument("--batch-rows", type=int, default=5000)
    p.add_argument("--archive", type=Path, default=Path("research-archive/R4-05"))
    p.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data/reports/R6_3_equal_partials",
    )
    a = p.parse_args()

    if not 100 <= a.batch_rows <= 20000:
        p.error("--batch-rows must be 100–20000")

    replay_year(a.year, batch_rows=a.batch_rows, archive=a.archive, output=a.output_dir)


if __name__ == "__main__":
    main()
