"""R6.2 25%-partial runner tests."""
import pandas as pd

from scripts.run_r62_p25_tp50_runner import run_managed_backtest


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
    t0 = pd.Timestamp("2025-01-02T14:30:00Z")
    rows = []
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


def test_25_percent_at_50_and_75_percent_at_100():
    trade = run_managed_backtest(
        _frame([
            (100, 101, 99, 100),
            (100, 151, 99, 150),
            (150, 201, 149, 200),
        ]),
        _config(),
        move_runner_to_be=False,
    ).iloc[0]
    assert bool(trade.partial_50_hit)
    assert bool(trade.runner_100_hit)
    # 25% * 50 + 75% * 100 = 87.5
    assert trade.net_result_points == 87.5


def test_original_stop_after_partial():
    trade = run_managed_backtest(
        _frame([
            (100, 101, 99, 100),
            (100, 151, 99, 150),
            (150, 151, 74, 75),
        ]),
        _config(),
        move_runner_to_be=False,
    ).iloc[0]
    # 25% * 50 + 75% * -25 = -6.25
    assert trade.net_result_points == -6.25
    assert trade.exit_reason == "runner_initial_stop"


def test_next_bar_break_even_after_partial():
    trade = run_managed_backtest(
        _frame([
            (100, 101, 99, 100),
            (100, 151, 99, 150),
            (150, 151, 99, 100),
        ]),
        _config(),
        move_runner_to_be=True,
    ).iloc[0]
    assert bool(trade.break_even_exit)
    # Locked 25% * 50; runner exits at BE.
    assert trade.net_result_points == 12.5


def test_same_bar_stop_remains_conservative():
    trade = run_managed_backtest(
        _frame([
            (100, 101, 99, 100),
            (100, 151, 74, 150),
            (150, 151, 149, 150),
        ]),
        _config(),
        move_runner_to_be=True,
    ).iloc[0]
    assert not bool(trade.partial_50_hit)
    assert trade.net_result_points == -25.0
