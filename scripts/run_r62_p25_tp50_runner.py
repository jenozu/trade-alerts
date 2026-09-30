#!/usr/bin/env python3
"""R6.2 — 25% at TP50 with 75% TP100 runner.

R6.1 showed that realizing 50% at +50 reduced drawdown but sacrificed too much
of the TP100 upside. R6.2 changes only the partial size:

  P25_RUNNER: 25% exits at +50; 75% remains for +100; original stop remains.
  P25_BE_RUNNER: 25% exits at +50; 75% remains for +100; runner stop moves to
                 break-even beginning on the next bar.

The TP100 baseline remains the exact parity control. No production settings
are modified.
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

PARTIAL_FRACTION = 0.25
RUNNER_FRACTION = 0.75


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
    partial_50_hit: bool
    runner_100_hit: bool
    break_even_exit: bool
    exit_reason: str
    net_result_points: float
    net_result_r: float
    mfe_points: float
    mae_points: float
    bars_held: int
    minutes_held: float


def _target(entry: float, direction: str, points: float) -> float:
    return entry + points if direction == "long" else entry - points


def _target_hit(direction: str, target: float, high: float, low: float) -> bool:
    return high >= target if direction == "long" else low <= target


def _stop_hit(direction: str, stop: float, high: float, low: float) -> bool:
    return low <= stop if direction == "long" else high >= stop


def _directional_points(direction: str, entry: float, exit_price: float) -> float:
    return exit_price - entry if direction == "long" else entry - exit_price


def _excursions(direction: str, entry: float, high: float, low: float) -> tuple[float, float]:
    if direction == "long":
        return max(0.0, high - entry), max(0.0, entry - low)
    return max(0.0, entry - low), max(0.0, high - entry)


def simulate_managed_trade(
    data: pd.DataFrame,
    *,
    signal_index: int,
    direction: str,
    trade_id: int,
    config: dict,
    move_runner_to_be: bool,
) -> ManagedTrade | None:
    settings = build_backtest_settings(config)
    if signal_index >= len(data) - 1:
        return None

    signal = data.iloc[signal_index]
    entry_index = signal_index + 1 if settings.entry_on_next_bar_open else signal_index
    entry_row = data.iloc[entry_index]
    raw_entry = float(entry_row["open"] if settings.entry_on_next_bar_open else signal["close"])
    entry = apply_entry_slippage(raw_entry, direction=direction, settings=settings)

    initial_stop = determine_stop_price(
        signal, entry_price=entry, direction=direction, settings=settings
    )
    stop_distance = abs(entry - initial_stop)
    if stop_distance <= 0:
        return None

    tp50 = _target(entry, direction, 50.0)
    tp100 = _target(entry, direction, 100.0)

    entry_time = data.iloc[entry_index]["timestamp"]
    max_end = entry_time + pd.Timedelta(
        minutes=int(settings.maximum_holding_minutes)
    )

    partial_hit = False
    runner_hit = False
    be_exit = False
    realized = 0.0
    max_favorable = 0.0
    max_adverse = 0.0
    exit_index = entry_index
    exit_reason = "end_of_data"
    be_active_from_index: int | None = None

    for i in range(entry_index, len(data)):
        row = data.iloc[i]
        ts = row["timestamp"]

        if ts >= max_end:
            j = max(entry_index, i - 1)
            close_raw = float(data.iloc[j]["close"])
            close_exit = apply_exit_slippage(
                close_raw, direction=direction, settings=settings
            )
            remaining = RUNNER_FRACTION if partial_hit else 1.0
            realized += remaining * _directional_points(direction, entry, close_exit)
            exit_index = j
            exit_reason = "timeout_after_partial" if partial_hit else "timeout"
            break

        high = float(row["high"])
        low = float(row["low"])
        fav, adv = _excursions(direction, entry, high, low)
        max_favorable = max(max_favorable, fav)
        max_adverse = max(max_adverse, adv)

        active_stop = initial_stop
        if (
            partial_hit
            and move_runner_to_be
            and be_active_from_index is not None
            and i >= be_active_from_index
        ):
            active_stop = entry

        stop_now = _stop_hit(direction, active_stop, high, low)
        tp50_now = (not partial_hit) and _target_hit(direction, tp50, high, low)
        tp100_now = _target_hit(direction, tp100, high, low)

        # Keep the frozen simulator's conservative stop-first convention.
        if stop_now:
            stop_exit = apply_exit_slippage(
                active_stop, direction=direction, settings=settings
            )
            remaining = RUNNER_FRACTION if partial_hit else 1.0
            realized += remaining * _directional_points(direction, entry, stop_exit)
            exit_index = i
            if partial_hit and move_runner_to_be and active_stop == entry:
                be_exit = True
                exit_reason = "break_even_runner_stop"
            elif partial_hit:
                exit_reason = "runner_initial_stop"
            else:
                exit_reason = "initial_stop"
            break

        if tp50_now:
            partial_exit = apply_exit_slippage(
                tp50, direction=direction, settings=settings
            )
            realized += PARTIAL_FRACTION * _directional_points(
                direction, entry, partial_exit
            )
            partial_hit = True
            if move_runner_to_be:
                # OHLC cannot establish post-TP50 intrabar path, so BE begins
                # on the following bar.
                be_active_from_index = i + 1

        if tp100_now:
            if not partial_hit:
                partial_exit = apply_exit_slippage(
                    tp50, direction=direction, settings=settings
                )
                realized += PARTIAL_FRACTION * _directional_points(
                    direction, entry, partial_exit
                )
                partial_hit = True

            runner_exit = apply_exit_slippage(
                tp100, direction=direction, settings=settings
            )
            realized += RUNNER_FRACTION * _directional_points(
                direction, entry, runner_exit
            )
            runner_hit = True
            exit_index = i
            exit_reason = "runner_tp100"
            break
    else:
        close_raw = float(data.iloc[-1]["close"])
        close_exit = apply_exit_slippage(
            close_raw, direction=direction, settings=settings
        )
        remaining = RUNNER_FRACTION if partial_hit else 1.0
        realized += remaining * _directional_points(direction, entry, close_exit)
        exit_index = len(data) - 1
        exit_reason = "end_of_data_after_partial" if partial_hit else "end_of_data"

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
        initial_stop_price=initial_stop,
        stop_distance_points=stop_distance,
        raw_score=float(signal[f"{direction}_raw_score"]),
        partial_50_hit=partial_hit,
        runner_100_hit=runner_hit,
        break_even_exit=be_exit,
        exit_reason=exit_reason,
        net_result_points=realized,
        net_result_r=realized / stop_distance,
        mfe_points=max_favorable,
        mae_points=max_adverse,
        bars_held=exit_index - entry_index + 1,
        minutes_held=(exit_time - entry_time).total_seconds() / 60.0,
    )


def run_managed_backtest(
    data: pd.DataFrame, config: dict, *, move_runner_to_be: bool
) -> pd.DataFrame:
    settings = build_backtest_settings(config)
    ordered = data.sort_values("timestamp").copy().reset_index(drop=True)
    trades: list[ManagedTrade] = []
    blocked_until = -1
    trade_id = 1

    for i in range(len(ordered) - 1):
        if settings.maximum_one_open_trade and i <= blocked_until:
            continue

        row = ordered.iloc[i]
        candidates = [
            d for d in ("long", "short") if directional_candidate(row, d)
        ]
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

        trade = simulate_managed_trade(
            ordered,
            signal_index=i,
            direction=candidates[0],
            trade_id=trade_id,
            config=config,
            move_runner_to_be=move_runner_to_be,
        )
        if trade is None:
            continue

        trades.append(trade)
        trade_id += 1
        if settings.maximum_one_open_trade:
            blocked_until = trade.exit_index

    return pd.DataFrame([asdict(x) for x in trades])


def metrics(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {"trades": 0}
    pnl = pd.to_numeric(trades["net_result_points"], errors="raise")
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = float(-pnl[pnl < 0].sum())
    equity = pnl.cumsum()
    drawdown = equity.cummax() - equity

    return {
        "trades": int(len(trades)),
        "wins": int((pnl > 0).sum()),
        "win_rate": float((pnl > 0).mean()),
        "net_points": float(pnl.sum()),
        "expectancy_points": float(pnl.mean()),
        "expectancy_r": float(trades["net_result_r"].mean()),
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else None,
        "max_drawdown_points": float(drawdown.max()),
        "partial_50_hit_rate": float(trades["partial_50_hit"].mean()),
        "runner_100_hit_rate": float(trades["runner_100_hit"].mean()),
        "break_even_exit_rate": float(trades["break_even_exit"].mean()),
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

    print(f"===== R6.2 PARITY GATE: {year} / CONTROL TP100 =====", flush=True)
    control = run_backtest(scored, config)
    assert_frozen_70(control, frozen)
    print(f"EXACT CONTROL PARITY PASSED: {len(frozen)} trades", flush=True)

    summaries = []
    for name, use_be in (("p25_runner", False), ("p25_be_runner", True)):
        trades = run_managed_backtest(
            scored, config, move_runner_to_be=use_be
        )
        outdir = output / str(year) / name
        outdir.mkdir(parents=True, exist_ok=True)
        trades.to_csv(outdir / "trades.csv", index=False)

        row = {"research_year": year, "model": name, **metrics(trades)}
        (outdir / "metrics.json").write_text(
            json.dumps(row, indent=2) + "\n", encoding="utf-8"
        )
        summaries.append(row)

        print(
            f"R6.2 {year} {name}: trades={row['trades']}, "
            f"net={row['net_points']:.2f}, "
            f"exp={row['expectancy_points']:.4f}, "
            f"PF={row['profit_factor']:.4f}, "
            f"DD={row['max_drawdown_points']:.2f}",
            flush=True,
        )

    pd.DataFrame(summaries).to_csv(
        output / f"summary_{year}.csv", index=False
    )
    del scored
    gc.collect()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--year", required=True, type=int, choices=YEARS)
    p.add_argument("--batch-rows", type=int, default=5000)
    p.add_argument(
        "--archive", type=Path, default=Path("research-archive/R4-05")
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data/reports/R6_2_p25_tp50_runner",
    )
    args = p.parse_args()
    if not 100 <= args.batch_rows <= 20000:
        p.error("--batch-rows must be 100–20000")

    replay_year(
        args.year,
        batch_rows=args.batch_rows,
        archive=args.archive,
        output=args.output_dir,
    )


if __name__ == "__main__":
    main()
