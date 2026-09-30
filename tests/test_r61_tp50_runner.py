"""R6.1 managed-exit unit tests."""
import pandas as pd

from scripts.run_r61_tp50_runner import run_managed_backtest


def _config():
    return {
        "backtest": {
            "use_completed_bars_only": True,
            "entry_on_next_bar_open": True,
            "conservative_same_bar_resolution": True,
            "same_bar_stop_and_target_behavior": "stop_first",
            "commission": {"enabled": False, "per_contract_round_trip": 0.0},
            "slippage": {"enabled": False, "points_per_entry": 0.0, "points_per_exit": 0.0},
        },
        "trade_management": {
            "maximum_holding_minutes": 60,
            "maximum_one_open_trade": True,
        },
        "stop_loss": {
            "primary_method": "fixed",
            "structural": {"buffer_points": 2.0},
            "preferred_initial_range_points": {"minimum": 20, "maximum": 25},
            "fixed_research_values_points": [15, 20, 25, 30, 35],
        },
        "take_profit": {
            "number_of_targets": 4,
            "preferred_initial": {
                "tp1_points": 25,
                "tp2_points": 50,
                "tp3_points": 75,
                "tp4_points": 100,
            },
        },
    }


def _frame(bars):
    rows = []
    t0 = pd.Timestamp("2025-01-02T14:30:00Z")
    for i, (o, h, l, c) in enumerate(bars):
        rows.append({
            "timestamp": t0 + pd.Timedelta(minutes=i),
            "open": o, "high": h, "low": l, "close": c,
            "long_candidate": i == 0,
            "short_candidate": False,
            "long_raw_score": 80.0,
            "short_raw_score": 0.0,
            "long_score_band": "high_probability",
            "short_score_band": "no_trade",
        })
    return pd.DataFrame(rows)


def test_half_at_50_and_runner_at_100():
    data = _frame([
        (100, 101, 99, 100),
        (100, 151, 99, 150),
        (150, 201, 149, 200),
    ])
    trades = run_managed_backtest(data, _config(), move_runner_to_be=False)
    assert len(trades) == 1
    trade = trades.iloc[0]
    assert bool(trade.partial_50_hit)
    assert bool(trade.runner_100_hit)
    assert trade.net_result_points == 75.0


def test_original_stop_remains_for_runner_without_be():
    data = _frame([
        (100, 101, 99, 100),
        (100, 151, 99, 150),
        (150, 151, 74, 75),
    ])
    trade = run_managed_backtest(data, _config(), move_runner_to_be=False).iloc[0]
    assert bool(trade.partial_50_hit)
    assert trade.exit_reason == "runner_initial_stop"
    # +25 points on first half, -12.5 on stopped half.
    assert trade.net_result_points == 12.5


def test_be_activates_on_next_bar_after_tp50():
    data = _frame([
        (100, 101, 99, 100),
        (100, 151, 99, 150),
        (150, 151, 99, 100),
    ])
    trade = run_managed_backtest(data, _config(), move_runner_to_be=True).iloc[0]
    assert bool(trade.partial_50_hit)
    assert bool(trade.break_even_exit)
    assert trade.exit_reason == "break_even_runner_stop"
    assert trade.net_result_points == 25.0


def test_same_bar_initial_stop_wins_over_tp50():
    data = _frame([
        (100, 101, 99, 100),
        (100, 151, 74, 150),
        (150, 151, 149, 150),
    ])
    trade = run_managed_backtest(data, _config(), move_runner_to_be=True).iloc[0]
    assert not bool(trade.partial_50_hit)
    assert trade.exit_reason == "initial_stop"
    assert trade.net_result_points == -25.0
