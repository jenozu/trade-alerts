"""R6.3 equal-partials unit tests."""
import pandas as pd

from scripts.run_r63_equal_partials import run_equal_partials


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


def test_all_targets_hit_realizes_weighted_62_5_points():
    trade = run_equal_partials(
        _frame([
            (100, 101, 99, 100),
            (100, 201, 99, 200),
            (200, 201, 199, 200),
        ]),
        _config(),
    ).iloc[0]
    assert all(bool(trade[c]) for c in ("tp1_hit", "tp2_hit", "tp3_hit", "tp4_hit"))
    assert trade.net_result_points == 62.5


def test_tp1_then_stop():
    trade = run_equal_partials(
        _frame([
            (100, 101, 99, 100),
            (100, 126, 99, 125),
            (125, 126, 74, 75),
        ]),
        _config(),
    ).iloc[0]
    # 25% * +25, then 75% * -25.
    assert trade.net_result_points == -12.5
    assert bool(trade.tp1_hit)
    assert not bool(trade.tp2_hit)


def test_tp1_tp2_then_stop():
    trade = run_equal_partials(
        _frame([
            (100, 101, 99, 100),
            (100, 151, 99, 150),
            (150, 151, 74, 75),
        ]),
        _config(),
    ).iloc[0]
    # 25%*25 + 25%*50 + 50%*-25 = 6.25
    assert trade.net_result_points == 6.25


def test_same_bar_stop_precedes_targets():
    trade = run_equal_partials(
        _frame([
            (100, 101, 99, 100),
            (100, 201, 74, 200),
            (200, 201, 199, 200),
        ]),
        _config(),
    ).iloc[0]
    assert trade.net_result_points == -25.0
    assert not bool(trade.tp1_hit)
