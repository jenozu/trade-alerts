"""Actual market-state -> shared execution planner -> backtest parity."""
from copy import deepcopy
import json

import pandas as pd
import pytest

from backtest import run_backtest, BacktestError
from market_state import build_market_state
from trade_planner import build_market_execution_plan
from tests.test_confirmed_entry_execution import bars, config

MODE = "market_after_retest_confirmation_v2"


def fixture(direction="long", family="reversal"):
    frame = bars(direction, family)
    frame["volume"] = 100
    frame["active_internal_swing_low"] = 80.0
    frame["active_internal_swing_high"] = 132.0
    frame["nearest_5m_fvg_above"] = 136.0
    frame["nearest_htf_fvg_above"] = 150.0
    frame["pdh"] = 160.0
    frame["week_high"] = 180.0
    frame["dol_primary_direction"] = "bullish"
    frame["dol_primary_target_type"] = "pdh"
    frame["dol_primary_target_price"] = 160.0
    if direction == "short":
        frame["active_internal_swing_high"] = 122.0
        frame["active_internal_swing_low"] = 70.0
        frame["nearest_5m_fvg_below"] = 65.0
        frame["nearest_htf_fvg_below"] = 50.0
        frame["pdl"] = 40.0
        frame["week_low"] = 20.0
        frame["dol_primary_direction"] = "bearish"
        frame["dol_primary_target_type"] = "pdl"
        frame["dol_primary_target_price"] = 40.0
        frame = frame.drop(columns=["nearest_5m_fvg_above","nearest_htf_fvg_above","pdh","week_high"])
    cfg = config()
    cfg["backtest"]["execution_model"] = MODE
    cfg["stop_loss"]["primary_method"] = "structural"
    return frame, cfg


@pytest.mark.parametrize("direction", ["long","short"])
@pytest.mark.parametrize("family", ["reversal","continuation"])
def test_real_state_planner_and_simulation_agree_on_executable_prices(direction, family):
    frame,cfg = fixture(direction,family)
    original = frame.copy(deep=True)
    original_cfg = deepcopy(cfg)
    cutoff = frame.available_at.iloc[1]
    snapshot = build_market_state(frame.iloc[:2], as_of=cutoff, generated_at=cutoff,
                                  symbol="MNQ",contract=None,strategy_config=cfg)
    price = 102 + (0.25 if direction == "long" else -0.25)
    decision = build_market_execution_plan(snapshot,cfg,direction=direction,
                                          entry_price=price,entry_time=frame.timestamp.iloc[2])
    assert decision["candidate"] is not None, decision
    trades = run_backtest(frame,cfg)
    assert len(trades) == 1, trades.attrs
    trade = trades.iloc[0]
    candidate = decision["candidate"]
    assert trade.entry_price == price
    assert trade.stop_price == candidate["stop_loss"]["price"]
    for key in ("tp1","tp2","tp3","tp4"):
        assert trade[key] == candidate["targets"][key]["price"]
    assert trade.setup_family == family
    assert json.loads(trade.execution_plan) == decision
    assert trade.confirmation_time == cutoff
    pd.testing.assert_frame_equal(frame, original)
    assert cfg == original_cfg


def test_rejected_market_risk_is_reported_and_never_replaced_with_fixed_stop():
    frame,cfg = fixture()
    frame["active_internal_swing_low"] = 70
    trades = run_backtest(frame,cfg)
    assert trades.empty
    reasons = trades.attrs["execution_decisions"][0]["rejections"]
    assert "structural_risk_too_large:34.25>25.00" in reasons


def test_future_entry_bar_extremes_cannot_change_the_execution_decision():
    frame,cfg = fixture()
    first = run_backtest(frame,cfg).iloc[0]
    frame.loc[2:, ["high","low","close"]] = [1000,1,800]
    changed = run_backtest(frame,cfg).iloc[0]
    assert first.execution_plan == changed.execution_plan
    assert changed.exit_reason == "stop"


def test_full_position_exits_at_shared_liquidity_runner_and_deducts_costs():
    frame,cfg = fixture()
    frame.loc[2:, ["open","high","low","close"]] = [102,181,101,180]
    cfg["backtest"]["commission"].update(enabled=True, unit="points", per_contract_round_trip=1.5)
    trade = run_backtest(frame,cfg).iloc[0]
    assert trade.exit_reason == "tp4"
    assert trade.exit_price_raw == trade.tp4 == 180
    assert trade.net_result_points == pytest.approx(180-0.25-102.25-1.5)


def test_missing_optional_tp2_is_not_fabricated():
    frame,cfg = fixture()
    frame = frame.drop(columns=["nearest_5m_fvg_above","nearest_htf_fvg_above"])
    trades = run_backtest(frame,cfg)
    assert len(trades)==1
    assert pd.isna(trades.iloc[0].tp2)
    assert not trades.iloc[0].tp2_hit


def test_opening_runner_gap_does_not_mark_missing_tp2_as_hit():
    frame,cfg = fixture()
    frame = frame.drop(columns=["nearest_5m_fvg_above","nearest_htf_fvg_above"])
    frame.loc[3:, ["open","high","low","close"]] = [190,191,189,190]
    result = run_backtest(frame,cfg).iloc[0]
    assert result.exit_reason == "tp4" and result.tp4_hit
    assert not result.tp2_hit


def test_missing_runner_records_no_trade_instead_of_fixed_target():
    frame,cfg = fixture()
    frame = frame.drop(columns="week_high")
    result = run_backtest(frame,cfg)
    assert result.empty
    assert "terminal_tp4_market_objective_unavailable" in result.attrs["execution_decisions"][0]["rejections"]


def test_rejected_higher_scoring_side_does_not_block_valid_opposite_entry():
    frame,cfg = fixture("short","continuation")
    frame.loc[1,"long_candidate"] = True
    frame.loc[1,"long_raw_score"] = 99
    frame.loc[1,"long_score_band"] = "a_plus_plus"
    frame.loc[1,"bullish_continuation_sequence"] = True
    frame.loc[1,"bullish_continuation_entry_valid_event"] = True
    frame["active_internal_swing_low"] = 50
    result = run_backtest(frame,cfg)
    assert result.iloc[0].direction == "short"
    assert len(result.attrs["execution_decisions"]) == 2
    assert result.attrs["execution_decisions"][0]["candidate"] is None


def test_completed_execution_is_unchanged_when_future_bars_are_appended():
    frame,cfg = fixture()
    prefix = frame.iloc[:3].copy()
    prefix.loc[2,"low"] = 50
    extended = frame.copy()
    extended.loc[2,"low"] = 50
    extended.loc[3:, ["open","high","low","close"]] = [1000,2000,1,1500]
    assert run_backtest(prefix,cfg).iloc[0].to_dict() == run_backtest(extended,cfg).iloc[0].to_dict()


@pytest.mark.parametrize("change", ["partial","same_bar","fixed","bad_completion","duplicates"])
def test_v2_rejects_unsupported_or_malformed_inputs(change):
    frame,cfg = fixture()
    if change=="partial": cfg["trade_management"]["partial_exits_enabled"]=True
    elif change=="same_bar": cfg["backtest"]["same_bar_stop_and_target_behavior"]="target_first"
    elif change=="fixed": cfg["stop_loss"]["primary_method"]="fixed"
    elif change=="bad_completion": frame["bar_complete"]="false"
    else: frame.loc[1,"timestamp"]=frame.timestamp.iloc[0]
    with pytest.raises(BacktestError): run_backtest(frame,cfg)
