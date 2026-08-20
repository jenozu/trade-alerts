from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

DEFAULT_STRATEGY_CONFIG = Path("config/strategy.yaml")
REQUIRED_COLUMNS = {
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "long_raw_score",
    "short_raw_score",
    "long_score_band",
    "short_score_band",
}
VALID_DIRECTIONS = {"long", "short"}


class BacktestError(RuntimeError):
    """Raised when a backtest cannot be completed safely."""


@dataclass(frozen=True)
class BacktestSettings:
    use_completed_bars_only: bool
    entry_on_next_bar_open: bool
    conservative_same_bar_resolution: bool
    same_bar_stop_and_target_behavior: str
    commission_enabled: bool
    commission_round_trip: float
    slippage_enabled: bool
    entry_slippage_points: float
    exit_slippage_points: float
    maximum_holding_minutes: int
    maximum_one_open_trade: bool
    stop_method: str
    structural_stop_buffer_points: float
    fixed_stop_values: tuple[float, ...]
    preferred_fixed_stop_min: float
    preferred_fixed_stop_max: float
    tp1_points: float
    tp2_points: float
    tp3_points: float
    tp4_points: float
    number_of_targets: int


@dataclass
class TradeResult:
    trade_id: int
    signal_index: int
    entry_index: int
    exit_index: int | None
    signal_time: Any
    entry_time: Any
    exit_time: Any | None
    direction: str
    signal_close: float
    entry_price_raw: float
    entry_price: float
    stop_price: float
    tp1: float
    tp2: float
    tp3: float
    tp4: float
    raw_score: float
    score_band: str
    score_edge: float | None
    stop_distance_points: float
    tp1_hit: bool
    tp2_hit: bool
    tp3_hit: bool
    tp4_hit: bool
    stop_hit: bool
    exit_reason: str
    exit_price_raw: float
    exit_price: float
    gross_result_points: float
    commission_cost: float
    net_result_points: float
    net_result_r: float | None
    mfe_points: float
    mae_points: float
    mfe_r: float | None
    mae_r: float | None
    bars_held: int
    minutes_held: float | None
    maximum_target_reached: int
    session_date: Any | None
    snr_1m: float | None
    snr_5m: float | None
    snr_15m: float | None
    snr_alignment: str | None
    rvol_rolling: float | None
    rvol_time_of_day: float | None
    htf_bias: str | None
    dol_direction: str | None
    liquidity_sweep: bool
    displacement: bool
    structure_shift: bool
    fvg_context: bool


def load_strategy_config(filepath: str | Path = DEFAULT_STRATEGY_CONFIG) -> dict[str, Any]:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Strategy configuration file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
    except Exception as exc:
        raise BacktestError(f"Could not load strategy configuration: {path}") from exc
    if not isinstance(config, dict):
        raise BacktestError("strategy.yaml did not produce a dictionary.")
    return config


def validate_input_dataframe(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise BacktestError(f"Missing required columns for backtesting: {sorted(missing)}")
    if df.empty:
        raise BacktestError("Cannot backtest an empty dataframe.")
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        raise BacktestError("'timestamp' must be a pandas datetime column.")
    if getattr(df["timestamp"].dt, "tz", None) is None:
        raise BacktestError("'timestamp' must be timezone-aware.")


def build_backtest_settings(config: dict[str, Any]) -> BacktestSettings:
    backtest = config.get("backtest", {})
    trade_management = config.get("trade_management", {})
    stop_loss = config.get("stop_loss", {})
    structural_stop = stop_loss.get("structural", {})
    preferred_stop = stop_loss.get("preferred_initial_range_points", {})
    take_profit = config.get("take_profit", {})
    preferred_tp = take_profit.get("preferred_initial", {})
    commission = backtest.get("commission", {})
    slippage = backtest.get("slippage", {})

    return BacktestSettings(
        use_completed_bars_only=bool(backtest.get("use_completed_bars_only", True)),
        entry_on_next_bar_open=bool(backtest.get("entry_on_next_bar_open", True)),
        conservative_same_bar_resolution=bool(backtest.get("conservative_same_bar_resolution", True)),
        same_bar_stop_and_target_behavior=str(backtest.get("same_bar_stop_and_target_behavior", "stop_first")),
        commission_enabled=bool(commission.get("enabled", False)),
        commission_round_trip=float(commission.get("per_contract_round_trip", 0.0)),
        slippage_enabled=bool(slippage.get("enabled", True)),
        entry_slippage_points=float(slippage.get("points_per_entry", 0.25)),
        exit_slippage_points=float(slippage.get("points_per_exit", 0.25)),
        maximum_holding_minutes=int(trade_management.get("maximum_holding_minutes", 60)),
        maximum_one_open_trade=bool(trade_management.get("maximum_one_open_trade", True)),
        stop_method=str(stop_loss.get("primary_method", "structural")),
        structural_stop_buffer_points=float(structural_stop.get("buffer_points", 2.0)),
        fixed_stop_values=tuple(float(x) for x in stop_loss.get("fixed_research_values_points", [15, 20, 25, 30])),
        preferred_fixed_stop_min=float(preferred_stop.get("minimum", 20)),
        preferred_fixed_stop_max=float(preferred_stop.get("maximum", 25)),
        tp1_points=float(preferred_tp.get("tp1_points", 25)),
        tp2_points=float(preferred_tp.get("tp2_points", 50)),
        tp3_points=float(preferred_tp.get("tp3_points", 75)),
        tp4_points=float(preferred_tp.get("tp4_points", 100)),
        number_of_targets=int(take_profit.get("number_of_targets", 4)),
    )


def safe_float(row: pd.Series, column: str) -> float | None:
    if column not in row.index:
        return None
    value = row[column]
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_bool(row: pd.Series, column: str) -> bool:
    if column not in row.index:
        return False
    value = row[column]
    if pd.isna(value):
        return False
    return bool(value)


def safe_string(row: pd.Series, column: str) -> str | None:
    if column not in row.index:
        return None
    value = row[column]
    if pd.isna(value):
        return None
    return str(value)


def directional_candidate(row: pd.Series, direction: str) -> bool:
    if direction not in VALID_DIRECTIONS:
        raise ValueError(f"Invalid direction: {direction}")
    candidate_column = f"{direction}_candidate"
    if candidate_column in row.index:
        return safe_bool(row, candidate_column)
    band = safe_string(row, f"{direction}_score_band")
    return band in {"near_trigger", "high_probability", "a_plus_plus"}


def determine_structural_stop(
    signal_row: pd.Series,
    *,
    direction: str,
    buffer_points: float,
) -> float | None:
    if direction == "long":
        candidates = [
            safe_float(signal_row, "active_internal_swing_low"),
            safe_float(signal_row, "active_external_swing_low"),
        ]
        for value in candidates:
            if value is not None:
                return value - buffer_points
    elif direction == "short":
        candidates = [
            safe_float(signal_row, "active_internal_swing_high"),
            safe_float(signal_row, "active_external_swing_high"),
        ]
        for value in candidates:
            if value is not None:
                return value + buffer_points
    return None


def fixed_stop_price(*, entry_price: float, direction: str, stop_points: float) -> float:
    if direction == "long":
        return entry_price - stop_points
    return entry_price + stop_points


def determine_stop_price(
    signal_row: pd.Series,
    *,
    entry_price: float,
    direction: str,
    settings: BacktestSettings,
) -> float:
    structural = determine_structural_stop(
        signal_row,
        direction=direction,
        buffer_points=settings.structural_stop_buffer_points,
    )
    fallback_points = settings.preferred_fixed_stop_max
    fallback = fixed_stop_price(
        entry_price=entry_price,
        direction=direction,
        stop_points=fallback_points,
    )

    if settings.stop_method != "structural":
        return fallback
    if structural is None:
        return fallback

    risk = entry_price - structural if direction == "long" else structural - entry_price
    if risk <= 0:
        return fallback
    if risk < settings.preferred_fixed_stop_min or risk > settings.preferred_fixed_stop_max:
        return fallback
    return structural


def determine_targets(
    *,
    entry_price: float,
    direction: str,
    settings: BacktestSettings,
) -> tuple[float, float, float, float]:
    distances = [settings.tp1_points, settings.tp2_points, settings.tp3_points, settings.tp4_points]
    if direction == "long":
        targets = [entry_price + distance for distance in distances]
    else:
        targets = [entry_price - distance for distance in distances]
    return tuple(float(x) for x in targets)  # type: ignore[return-value]


def apply_entry_slippage(raw_entry: float, *, direction: str, settings: BacktestSettings) -> float:
    if not settings.slippage_enabled:
        return raw_entry
    slip = settings.entry_slippage_points
    return raw_entry + slip if direction == "long" else raw_entry - slip


def apply_exit_slippage(raw_exit: float, *, direction: str, settings: BacktestSettings) -> float:
    if not settings.slippage_enabled:
        return raw_exit
    slip = settings.exit_slippage_points
    return raw_exit - slip if direction == "long" else raw_exit + slip


def directional_excursions(
    *,
    direction: str,
    entry_price: float,
    bar_high: float,
    bar_low: float,
) -> tuple[float, float]:
    if direction == "long":
        favorable = max(0.0, bar_high - entry_price)
        adverse = max(0.0, entry_price - bar_low)
    else:
        favorable = max(0.0, entry_price - bar_low)
        adverse = max(0.0, bar_high - entry_price)
    return favorable, adverse


def stop_touched(*, direction: str, stop_price: float, bar_high: float, bar_low: float) -> bool:
    if direction == "long":
        return bar_low <= stop_price
    return bar_high >= stop_price


def target_touched(*, direction: str, target_price: float, bar_high: float, bar_low: float) -> bool:
    if direction == "long":
        return bar_high >= target_price
    return bar_low <= target_price


def resolve_same_bar_stop_target(
    *,
    stop_hit: bool,
    target_hits: list[bool],
    settings: BacktestSettings,
) -> str:
    any_target = any(target_hits)
    if stop_hit and any_target:
        behavior = settings.same_bar_stop_and_target_behavior
        if behavior == "stop_first":
            return "stop"
        if behavior == "target_first":
            return "target"
        raise BacktestError(f"Unknown same-bar behavior: {behavior}")
    if stop_hit:
        return "stop"
    if any_target:
        return "target"
    return "none"


def simulate_trade(
    df: pd.DataFrame,
    *,
    signal_index: int,
    direction: str,
    trade_id: int,
    config: dict[str, Any],
    settings: BacktestSettings,
) -> TradeResult | None:
    if direction not in VALID_DIRECTIONS:
        raise ValueError(f"Invalid direction: {direction}")
    if signal_index >= len(df) - 1:
        return None

    signal_row = df.iloc[signal_index]

    if settings.entry_on_next_bar_open:
        entry_index = signal_index + 1
        entry_row = df.iloc[entry_index]
        raw_entry = float(entry_row["open"])
    else:
        entry_index = signal_index
        entry_row = signal_row
        raw_entry = float(signal_row["close"])

    entry_price = apply_entry_slippage(raw_entry, direction=direction, settings=settings)
    stop_price = determine_stop_price(
        signal_row,
        entry_price=entry_price,
        direction=direction,
        settings=settings,
    )
    stop_distance = abs(entry_price - stop_price)
    if stop_distance <= 0:
        return None

    tp1, tp2, tp3, tp4 = determine_targets(
        entry_price=entry_price,
        direction=direction,
        settings=settings,
    )
    targets = [tp1, tp2, tp3, tp4]

    raw_score = float(signal_row[f"{direction}_raw_score"])
    score_band = str(signal_row[f"{direction}_score_band"])
    score_edge = safe_float(signal_row, "score_edge")

    max_favorable = 0.0
    max_adverse = 0.0
    tp_hits = [False, False, False, False]
    stop_hit_flag = False
    exit_index: int | None = None
    raw_exit: float | None = None
    exit_reason = "timeout"

    entry_time = df.iloc[entry_index]["timestamp"]
    maximum_end_time = entry_time + pd.Timedelta(minutes=settings.maximum_holding_minutes)

    for i in range(entry_index, len(df)):
        row = df.iloc[i]
        timestamp = row["timestamp"]
        if timestamp > maximum_end_time:
            previous_index = max(entry_index, i - 1)
            exit_index = previous_index
            raw_exit = float(df.iloc[previous_index]["close"])
            exit_reason = "max_holding_time"
            break

        bar_high = float(row["high"])
        bar_low = float(row["low"])
        favorable, adverse = directional_excursions(
            direction=direction,
            entry_price=entry_price,
            bar_high=bar_high,
            bar_low=bar_low,
        )
        max_favorable = max(max_favorable, favorable)
        max_adverse = max(max_adverse, adverse)

        this_stop_hit = stop_touched(
            direction=direction,
            stop_price=stop_price,
            bar_high=bar_high,
            bar_low=bar_low,
        )
        this_target_hits = [
            target_touched(
                direction=direction,
                target_price=target,
                bar_high=bar_high,
                bar_low=bar_low,
            )
            for target in targets
        ]

        resolution = resolve_same_bar_stop_target(
            stop_hit=this_stop_hit,
            target_hits=this_target_hits,
            settings=settings,
        )

        if resolution == "stop":
            stop_hit_flag = True
            exit_index = i
            raw_exit = stop_price
            exit_reason = "stop"
            break

        for target_index, hit in enumerate(this_target_hits):
            if hit:
                tp_hits[target_index] = True

        if tp_hits[3]:
            exit_index = i
            raw_exit = tp4
            exit_reason = "tp4"
            break

    if exit_index is None:
        exit_index = len(df) - 1
        raw_exit = float(df.iloc[exit_index]["close"])
        exit_reason = "end_of_data"

    if raw_exit is None:
        raise BacktestError("Trade simulation finished without an exit price.")

    exit_price = apply_exit_slippage(raw_exit, direction=direction, settings=settings)
    gross_points = exit_price - entry_price if direction == "long" else entry_price - exit_price
    commission_cost = settings.commission_round_trip if settings.commission_enabled else 0.0
    net_points = gross_points
    net_result_r = net_points / stop_distance if stop_distance > 0 else None
    mfe_r = max_favorable / stop_distance if stop_distance > 0 else None
    mae_r = max_adverse / stop_distance if stop_distance > 0 else None

    maximum_target_reached = 0
    for number, hit in enumerate(tp_hits, start=1):
        if hit:
            maximum_target_reached = number

    exit_time = df.iloc[exit_index]["timestamp"]
    bars_held = exit_index - entry_index + 1
    minutes_held = (exit_time - entry_time).total_seconds() / 60.0

    liquidity_ok = safe_bool(
        signal_row,
        "recent_sell_side_sweep" if direction == "long" else "recent_buy_side_sweep",
    )
    displacement_ok = safe_bool(
        signal_row,
        "recent_bullish_displacement" if direction == "long" else "recent_bearish_displacement",
    )
    structure_ok = safe_bool(
        signal_row,
        "recent_bullish_mss" if direction == "long" else "recent_bearish_mss",
    ) or safe_bool(
        signal_row,
        "recent_bullish_bos" if direction == "long" else "recent_bearish_bos",
    )
    fvg_ok = safe_bool(
        signal_row,
        "bullish_fvg_retest_hold" if direction == "long" else "bearish_fvg_retest_hold",
    ) or safe_bool(
        signal_row,
        "bullish_core_plus_fvg" if direction == "long" else "bearish_core_plus_fvg",
    )

    return TradeResult(
        trade_id=trade_id,
        signal_index=signal_index,
        entry_index=entry_index,
        exit_index=exit_index,
        signal_time=signal_row["timestamp"],
        entry_time=entry_time,
        exit_time=exit_time,
        direction=direction,
        signal_close=float(signal_row["close"]),
        entry_price_raw=raw_entry,
        entry_price=entry_price,
        stop_price=stop_price,
        tp1=tp1,
        tp2=tp2,
        tp3=tp3,
        tp4=tp4,
        raw_score=raw_score,
        score_band=score_band,
        score_edge=score_edge,
        stop_distance_points=stop_distance,
        tp1_hit=tp_hits[0],
        tp2_hit=tp_hits[1],
        tp3_hit=tp_hits[2],
        tp4_hit=tp_hits[3],
        stop_hit=stop_hit_flag,
        exit_reason=exit_reason,
        exit_price_raw=raw_exit,
        exit_price=exit_price,
        gross_result_points=gross_points,
        commission_cost=commission_cost,
        net_result_points=net_points,
        net_result_r=net_result_r,
        mfe_points=max_favorable,
        mae_points=max_adverse,
        mfe_r=mfe_r,
        mae_r=mae_r,
        bars_held=bars_held,
        minutes_held=minutes_held,
        maximum_target_reached=maximum_target_reached,
        session_date=signal_row.get("session_date"),
        snr_1m=safe_float(signal_row, "snr_1m"),
        snr_5m=safe_float(signal_row, "snr_5m"),
        snr_15m=safe_float(signal_row, "snr_15m"),
        snr_alignment=safe_string(signal_row, "snr_alignment"),
        rvol_rolling=safe_float(signal_row, "rvol_rolling"),
        rvol_time_of_day=safe_float(signal_row, "rvol_time_of_day"),
        htf_bias=safe_string(signal_row, "htf_bias"),
        dol_direction=safe_string(signal_row, "dol_direction"),
        liquidity_sweep=liquidity_ok,
        displacement=displacement_ok,
        structure_shift=structure_ok,
        fvg_context=fvg_ok,
    )


def run_backtest(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    validate_input_dataframe(df)
    settings = build_backtest_settings(config)
    data = df.sort_values("timestamp").copy().reset_index(drop=True)

    trades: list[TradeResult] = []
    next_trade_id = 1
    blocked_until_index = -1

    for i in range(len(data) - 1):
        if settings.maximum_one_open_trade and i <= blocked_until_index:
            continue

        row = data.iloc[i]
        candidates = []
        for direction in ["long", "short"]:
            if directional_candidate(row, direction):
                candidates.append(direction)

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

        direction = candidates[0]
        trade = simulate_trade(
            data,
            signal_index=i,
            direction=direction,
            trade_id=next_trade_id,
            config=config,
            settings=settings,
        )
        if trade is None:
            continue

        trades.append(trade)
        next_trade_id += 1
        if settings.maximum_one_open_trade:
            blocked_until_index = int(trade.exit_index if trade.exit_index is not None else i)

    if not trades:
        return pd.DataFrame()
    return pd.DataFrame([asdict(trade) for trade in trades])


def calculate_backtest_metrics(trades: pd.DataFrame) -> dict[str, Any]:
    if trades.empty:
        return {"trades": 0}

    results = trades["net_result_points"]
    winners = trades.loc[results > 0]
    losers = trades.loc[results < 0]
    gross_profit = winners["net_result_points"].sum()
    gross_loss = abs(losers["net_result_points"].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
    win_rate = len(winners) / len(trades)
    expectancy_points = float(results.mean())
    expectancy_r = float(trades["net_result_r"].mean()) if trades["net_result_r"].notna().any() else None

    return {
        "trades": int(len(trades)),
        "wins": int(len(winners)),
        "losses": int(len(losers)),
        "win_rate": float(win_rate),
        "expectancy_points": expectancy_points,
        "expectancy_r": expectancy_r,
        "profit_factor": float(profit_factor),
        "average_mfe_points": float(trades["mfe_points"].mean()),
        "average_mae_points": float(trades["mae_points"].mean()),
        "median_mfe_points": float(trades["mfe_points"].median()),
        "median_mae_points": float(trades["mae_points"].median()),
        "tp1_hit_rate": float(trades["tp1_hit"].mean()),
        "tp2_hit_rate": float(trades["tp2_hit"].mean()),
        "tp3_hit_rate": float(trades["tp3_hit"].mean()),
        "tp4_hit_rate": float(trades["tp4_hit"].mean()),
        "stop_hit_rate": float(trades["stop_hit"].mean()),
        "average_score": float(trades["raw_score"].mean()),
        "average_hold_minutes": float(trades["minutes_held"].mean()),
    }


def performance_by_score_band(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()
    records = []
    for (direction, score_band), group in trades.groupby(["direction", "score_band"]):
        result = group["net_result_points"]
        records.append(
            {
                "direction": direction,
                "score_band": score_band,
                "trades": int(len(group)),
                "win_rate": float((result > 0).mean()),
                "expectancy_points": float(result.mean()),
                "expectancy_r": float(group["net_result_r"].mean()),
                "tp1_hit_rate": float(group["tp1_hit"].mean()),
                "tp2_hit_rate": float(group["tp2_hit"].mean()),
                "tp3_hit_rate": float(group["tp3_hit"].mean()),
                "tp4_hit_rate": float(group["tp4_hit"].mean()),
                "average_mfe": float(group["mfe_points"].mean()),
                "average_mae": float(group["mae_points"].mean()),
            }
        )
    return pd.DataFrame(records).sort_values(["direction", "score_band"]).reset_index(drop=True)


def performance_by_snr_bucket(trades: pd.DataFrame, *, column: str = "snr_5m") -> pd.DataFrame:
    if trades.empty or column not in trades.columns:
        return pd.DataFrame()
    result = trades.copy()
    bins = [-np.inf, 0.50, 0.80, 1.10, 1.40, 1.70, 2.00, 2.50, np.inf]
    labels = ["<0.50", "0.50-0.79", "0.80-1.09", "1.10-1.39", "1.40-1.69", "1.70-1.99", "2.00-2.49", "2.50+"]
    result["snr_bucket"] = pd.cut(result[column], bins=bins, labels=labels, right=False)

    records = []
    for bucket, group in result.groupby("snr_bucket", observed=True):
        if group.empty:
            continue
        records.append(
            {
                "snr_bucket": str(bucket),
                "trades": int(len(group)),
                "win_rate": float((group["net_result_points"] > 0).mean()),
                "expectancy_points": float(group["net_result_points"].mean()),
                "expectancy_r": float(group["net_result_r"].mean()),
                "tp1_hit_rate": float(group["tp1_hit"].mean()),
                "tp2_hit_rate": float(group["tp2_hit"].mean()),
                "tp3_hit_rate": float(group["tp3_hit"].mean()),
                "tp4_hit_rate": float(group["tp4_hit"].mean()),
                "average_mfe": float(group["mfe_points"].mean()),
                "average_mae": float(group["mae_points"].mean()),
            }
        )
    return pd.DataFrame(records)


def add_equity_curve(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    result = trades.sort_values("entry_time").copy().reset_index(drop=True)
    result["cumulative_points"] = result["net_result_points"].cumsum()
    result["equity_peak_points"] = result["cumulative_points"].cummax()
    result["drawdown_points"] = result["cumulative_points"] - result["equity_peak_points"]
    return result


def save_backtest_outputs(trades: pd.DataFrame, output_directory: str | Path) -> dict[str, Path]:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)

    trades_path = directory / "trades.csv"
    equity_path = directory / "equity_curve.csv"
    score_path = directory / "score_band_performance.csv"
    snr_path = directory / "snr_performance.csv"
    metrics_path = directory / "backtest_metrics.json"

    trades.to_csv(trades_path, index=False)
    add_equity_curve(trades).to_csv(equity_path, index=False)
    performance_by_score_band(trades).to_csv(score_path, index=False)
    performance_by_snr_bucket(trades).to_csv(snr_path, index=False)

    metrics = calculate_backtest_metrics(trades)
    import json
    with metrics_path.open("w", encoding="utf-8") as file:
        json.dump(metrics, file, indent=2, default=str)

    return {
        "trades": trades_path,
        "equity_curve": equity_path,
        "score_performance": score_path,
        "snr_performance": snr_path,
        "metrics": metrics_path,
    }


if __name__ == "__main__":
    input_file = Path("data/processed/scoring/nq_1m_scored.parquet")
    config_file = Path("config/strategy.yaml")
    output_directory = Path("data/results/backtest")

    if not input_file.exists():
        print("\nScored dataset not found.")
        print(f"Expected:\n{input_file}\n")
    else:
        print("\nLoading strategy configuration...")
        strategy_config = load_strategy_config(config_file)
        print("Loading scored market data...")
        data = pd.read_parquet(input_file)
        data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True)
        if "timestamp_et" in data.columns:
            data["timestamp_et"] = data["timestamp"].dt.tz_convert("America/New_York")

        print(f"Loaded {len(data):,} bars.")
        print("Running causal trade simulation...")
        trades = run_backtest(data, strategy_config)

        if trades.empty:
            print("\nNo trades were generated.")
        else:
            metrics = calculate_backtest_metrics(trades)
            print("\n============================================================")
            print("BACKTEST SUMMARY")
            print("============================================================")
            for key, value in metrics.items():
                print(f"{key}: {value}")
            print("\nSCORE BAND PERFORMANCE\n")
            print(performance_by_score_band(trades))
            print("\nSNR PERFORMANCE\n")
            print(performance_by_snr_bucket(trades))
            saved = save_backtest_outputs(trades, output_directory)
            print("\nSaved files:")
            for name, filepath in saved.items():
                print(f"  {name}: {filepath}")
        print("\nDone.\n")
