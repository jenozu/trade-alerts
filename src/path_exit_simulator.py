from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd


class PathExitSimulationError(RuntimeError):
    """Raised when path-aware exit research cannot be completed safely."""


@dataclass(frozen=True)
class ExitLeg:
    fraction: float
    target_number: int


@dataclass(frozen=True)
class ExitModel:
    name: str
    legs: tuple[ExitLeg, ...]
    breakeven_after_target: int | None = None


def default_exit_models() -> tuple[ExitModel, ...]:
    return (
        ExitModel("current_baseline", (ExitLeg(1.0, 4),)),
        ExitModel("half_tp1_half_tp4", (ExitLeg(0.5, 1), ExitLeg(0.5, 4))),
        ExitModel(
            "half_tp1_be_half_tp4",
            (ExitLeg(0.5, 1), ExitLeg(0.5, 4)),
            breakeven_after_target=1,
        ),
        ExitModel(
            "quarter_tp1_tp2_tp3_tp4",
            (
                ExitLeg(0.25, 1),
                ExitLeg(0.25, 2),
                ExitLeg(0.25, 3),
                ExitLeg(0.25, 4),
            ),
        ),
        ExitModel("half_tp2_half_tp4", (ExitLeg(0.5, 2), ExitLeg(0.5, 4))),
    )


def _validate_models(models: Iterable[ExitModel]) -> tuple[ExitModel, ...]:
    validated = tuple(models)
    if not validated:
        raise PathExitSimulationError("At least one exit model is required.")
    for model in validated:
        total = sum(leg.fraction for leg in model.legs)
        if not np.isclose(total, 1.0):
            raise PathExitSimulationError(
                f"Exit model {model.name!r} fractions sum to {total}, not 1.0."
            )
        if any(leg.fraction <= 0 for leg in model.legs):
            raise PathExitSimulationError(
                f"Exit model {model.name!r} has a non-positive leg fraction."
            )
        if any(leg.target_number not in {1, 2, 3, 4} for leg in model.legs):
            raise PathExitSimulationError(
                f"Exit model {model.name!r} references an invalid target."
            )
    return validated


def _target_price(trade: pd.Series, target_number: int) -> float:
    return float(trade[f"tp{target_number}"])


def _stop_touched(direction: str, stop_price: float, high: float, low: float) -> bool:
    return low <= stop_price if direction == "long" else high >= stop_price


def _target_touched(direction: str, target: float, high: float, low: float) -> bool:
    return high >= target if direction == "long" else low <= target


def _net_points(
    *,
    direction: str,
    entry_price: float,
    raw_exit: float,
    exit_slippage_points: float,
) -> float:
    executed_exit = (
        raw_exit - exit_slippage_points
        if direction == "long"
        else raw_exit + exit_slippage_points
    )
    return (
        executed_exit - entry_price
        if direction == "long"
        else entry_price - executed_exit
    )


def _trade_window(bars: pd.DataFrame, trade: pd.Series) -> pd.DataFrame:
    entry_index = int(trade["entry_index"])
    exit_index = int(trade["exit_index"])
    if entry_index < 0 or exit_index < entry_index or exit_index >= len(bars):
        raise PathExitSimulationError(
            f"Invalid baseline trade window: entry={entry_index}, exit={exit_index}, bars={len(bars)}"
        )
    return bars.iloc[entry_index : exit_index + 1]


def simulate_model_for_trade(
    bars: pd.DataFrame,
    trade: pd.Series,
    model: ExitModel,
    *,
    exit_slippage_points: float,
    stop_first: bool = True,
) -> dict[str, Any]:
    direction = str(trade["direction"])
    if direction not in {"long", "short"}:
        raise PathExitSimulationError(f"Unsupported direction: {direction}")

    entry_price = float(trade["entry_price"])
    original_stop = float(trade["stop_price"])
    active_stop = original_stop
    baseline_exit_index = int(trade["exit_index"])
    baseline_exit_reason = str(trade["exit_reason"])
    baseline_raw_exit = float(trade["exit_price_raw"])

    remaining = 1.0
    realized = 0.0
    filled_targets: set[int] = set()
    breakeven_pending = False
    breakeven_active = False
    exit_reason = baseline_exit_reason
    final_exit_index = baseline_exit_index

    # Group legs by target so each target can fill once even if a model happens
    # to express multiple legs at the same level.
    fractions_by_target: dict[int, float] = {}
    for leg in model.legs:
        fractions_by_target[leg.target_number] = (
            fractions_by_target.get(leg.target_number, 0.0) + leg.fraction
        )

    window = _trade_window(bars, trade)
    for absolute_index, row in window.iterrows():
        if breakeven_pending:
            active_stop = entry_price
            breakeven_pending = False
            breakeven_active = True

        high = float(row["high"])
        low = float(row["low"])
        this_stop = _stop_touched(direction, active_stop, high, low)
        touched_targets = [
            target_number
            for target_number in sorted(fractions_by_target)
            if target_number not in filled_targets
            and _target_touched(
                direction,
                _target_price(trade, target_number),
                high,
                low,
            )
        ]

        # We only have OHLC data, not intrabar sequencing. Match the production
        # backtest's conservative rule: if stop and target are both touched in
        # the same minute, the stop wins and no target is credited on that bar.
        if this_stop and (stop_first or not touched_targets):
            realized += remaining * _net_points(
                direction=direction,
                entry_price=entry_price,
                raw_exit=active_stop,
                exit_slippage_points=exit_slippage_points,
            )
            remaining = 0.0
            final_exit_index = int(absolute_index)
            exit_reason = "breakeven_stop" if breakeven_active else "stop"
            break

        for target_number in touched_targets:
            fraction = min(remaining, fractions_by_target[target_number])
            if fraction <= 0:
                continue
            realized += fraction * _net_points(
                direction=direction,
                entry_price=entry_price,
                raw_exit=_target_price(trade, target_number),
                exit_slippage_points=exit_slippage_points,
            )
            remaining -= fraction
            filled_targets.add(target_number)
            if (
                model.breakeven_after_target is not None
                and target_number >= model.breakeven_after_target
                and remaining > 0
                and not breakeven_active
            ):
                # Activate from the next one-minute bar. Doing it inside the
                # same OHLC bar would assume an unknowable intrabar sequence.
                breakeven_pending = True
            if remaining <= 1e-12:
                remaining = 0.0
                final_exit_index = int(absolute_index)
                exit_reason = f"tp{target_number}"
                break

        if remaining == 0.0:
            break

        # Preserve the original simulator's timeout/end-of-data boundary. If
        # the alternative model still has a runner at that point, close it at
        # the exact raw price used by the baseline trade.
        if int(absolute_index) == baseline_exit_index:
            realized += remaining * _net_points(
                direction=direction,
                entry_price=entry_price,
                raw_exit=baseline_raw_exit,
                exit_slippage_points=exit_slippage_points,
            )
            remaining = 0.0
            final_exit_index = baseline_exit_index
            exit_reason = baseline_exit_reason
            break

    stop_distance = float(trade["stop_distance_points"])
    return {
        "trade_id": int(trade["trade_id"]),
        "model": model.name,
        "direction": direction,
        "entry_time": trade["entry_time"],
        "exit_index": final_exit_index,
        "exit_reason": exit_reason,
        "net_result_points": float(realized),
        "net_result_r": float(realized / stop_distance) if stop_distance > 0 else np.nan,
        "targets_filled": ",".join(str(x) for x in sorted(filled_targets)),
        "breakeven_activated": bool(breakeven_active or breakeven_pending),
    }


def _longest_losing_streak(results: pd.Series) -> int:
    longest = current = 0
    for value in results:
        if value < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def summarize_results(results: pd.DataFrame) -> dict[str, Any]:
    points = pd.to_numeric(results["net_result_points"], errors="raise")
    winners = points[points > 0]
    losers = points[points < 0]
    gross_profit = float(winners.sum())
    gross_loss = abs(float(losers.sum()))
    equity = points.cumsum()
    drawdown = equity - equity.cummax()
    return {
        "trades": int(len(points)),
        "wins": int((points > 0).sum()),
        "losses": int((points < 0).sum()),
        "breakeven": int((points == 0).sum()),
        "win_rate": float((points > 0).mean()),
        "total_points": float(points.sum()),
        "expectancy_points": float(points.mean()),
        "expectancy_r": float(results["net_result_r"].mean()),
        "profit_factor": (
            gross_profit / gross_loss
            if gross_loss > 0
            else (float("inf") if gross_profit > 0 else 0.0)
        ),
        "max_drawdown_points": abs(float(drawdown.min())) if len(drawdown) else 0.0,
        "average_winner_points": float(winners.mean()) if len(winners) else 0.0,
        "average_loser_points": float(losers.mean()) if len(losers) else 0.0,
        "longest_losing_streak": _longest_losing_streak(points),
    }


def compare_path_exit_models(
    bars: pd.DataFrame,
    baseline_trades: pd.DataFrame,
    *,
    exit_slippage_points: float,
    models: Iterable[ExitModel] | None = None,
    stop_first: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if bars.empty or baseline_trades.empty:
        raise PathExitSimulationError("Bars and baseline trades are both required.")
    models = _validate_models(models or default_exit_models())
    rows: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []

    for model in models:
        model_rows = [
            simulate_model_for_trade(
                bars,
                trade,
                model,
                exit_slippage_points=exit_slippage_points,
                stop_first=stop_first,
            )
            for _, trade in baseline_trades.iterrows()
        ]
        model_df = pd.DataFrame(model_rows)
        rows.extend(model_rows)
        summary = summarize_results(model_df)
        summary["model"] = model.name
        summaries.append(summary)

    summary_df = pd.DataFrame(summaries)
    detail_df = pd.DataFrame(rows)
    baseline_expectancy = float(
        summary_df.loc[
            summary_df["model"] == "current_baseline",
            "expectancy_points",
        ].iloc[0]
    )
    summary_df["expectancy_delta_vs_baseline"] = (
        summary_df["expectancy_points"] - baseline_expectancy
    )
    return summary_df, detail_df
