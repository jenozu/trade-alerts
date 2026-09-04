from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

import run_pipeline as pipeline
from trade_planner import (
    DECISION_NO_TRADE,
    DECISION_PLAN,
    TradePlannerError,
    build_trade_plan,
)


def _zone(zone_id: str, side: str, lower: float, upper: float) -> dict:
    return {
        "zone_id": zone_id,
        "zone_side": side,
        "zone_lower": lower,
        "zone_upper": upper,
        "zone_midpoint": (lower + upper) / 2.0,
        "sources": "deterministic_fixture",
    }


def _state() -> dict:
    support = _zone("support:100", "support", 99.0, 100.0)
    resistance = _zone("resistance:111", "resistance", 110.0, 112.0)
    return {
        "schema_version": "1.0.0",
        "generated_at": "2026-09-04T13:00:00+00:00",
        "as_of": "2026-09-04T13:00:00+00:00",
        "status": {"code": "ready", "message": "ANALYSIS READY"},
        "instrument": {"symbol": "MNQ", "contract": "MNQU6", "latest_price": 100.0},
        "levels": {
            "nearest_important_swing_high": 130.0,
            "nearest_important_swing_low": 80.0,
            "nearest_equal_high": 140.0,
            "nearest_equal_low": 70.0,
            "important_5m_fvg_above": 135.0,
            "important_5m_fvg_below": 75.0,
            "important_htf_fvg_above": 150.0,
            "important_htf_fvg_below": 50.0,
            "pdh": 160.0,
            "pdl": 40.0,
            "pmh": None,
            "pml": None,
            "asia_high": None,
            "asia_low": None,
            "london_high": None,
            "london_low": None,
            "overnight_high": None,
            "overnight_low": None,
            "week_high": 180.0,
            "week_low": 20.0,
            "previous_close": None,
            "prior_day_half_back": None,
            "vwap": None,
        },
        "support_resistance": {
            "strongest_support": support,
            "strongest_resistance": resistance,
            # Trigger zones are not automatically target obstacles.  The
            # roadmap's room test adds an explicit opposing objective below.
            "zones": [],
        },
        "draw_on_liquidity": {
            "direction": "bullish",
            "primary": {
                "direction": "bullish",
                "target_type": "pdh",
                "target_category": "pdh_pdl",
                "price": 160.0,
                "confidence": 0.8,
            },
            "alternate": {
                "direction": "bearish",
                "target_type": "pdl",
                "target_category": "pdh_pdl",
                "price": 40.0,
                "confidence": 0.5,
            },
            "ranked_candidates": [],
        },
        "scores": {
            "preferred_direction": "long",
            "long": {
                "raw_score": 82.0,
                "band": "high_probability",
                "positive_points": 82.0,
                "penalty_points": 0.0,
                "disabled": False,
                "components": {"long_score_draw_on_liquidity": 10.0},
            },
            "short": {
                "raw_score": 76.0,
                "band": "near_trigger",
                "positive_points": 76.0,
                "penalty_points": 0.0,
                "disabled": False,
                "components": {"short_score_draw_on_liquidity": 8.0},
            },
        },
        "structure": {
            "bullish_continuation_sequence": False,
            "bearish_continuation_sequence": False,
            "bullish_reversal_sequence": False,
            "bearish_reversal_sequence": False,
        },
        "liquidity": {},
        "displacement": {},
        "fvgs": {},
        "bias": {"htf_bias": "bullish"},
    }


def _config() -> dict:
    return {
        "room_to_target": {"minimum_points": 25.0},
        "stop_loss": {
            "structural": {"buffer_points": 2.0},
            "preferred_initial_range_points": {"minimum": 20.0, "maximum": 25.0},
            "fixed_research_values_points": [15.0, 20.0, 25.0, 30.0, 35.0],
        },
    }


def test_planner_uses_structural_stop_and_market_derived_target_priority() -> None:
    plan = build_trade_plan(_state(), _config())
    candidate = plan["preferred"]

    assert plan["decision"] == DECISION_PLAN
    assert candidate["direction"] == "long"
    assert candidate["scenario_status"] == "HYPOTHESIS"
    assert candidate["stop_loss"]["price"] == 78.0
    assert candidate["stop_loss"]["risk_points"] == 22.0
    assert candidate["structural_invalidation"]["source"] == "nearest_important_swing_low"
    assert candidate["targets"]["tp1"]["source"] == "nearest_important_swing_high"
    assert candidate["targets"]["tp2"]["source"] == "important_5m_fvg_above"
    assert candidate["targets"]["tp3"]["source"] == "pdh"
    assert candidate["targets"]["tp4"]["source"] == "week_high"
    assert candidate["targets"]["tp3"]["reason"].startswith("ranked draw on liquidity")
    assert candidate["reward_risk"]["tp1"] > 1.0


def test_planner_rejects_oversized_structural_risk_without_forcing_stop() -> None:
    state = _state()
    state["levels"]["nearest_important_swing_low"] = 50.0

    plan = build_trade_plan(state, _config())

    long_rejection = next(item for item in plan["rejections"] if item["direction"] == "long")
    assert any(reason.startswith("structural_risk_too_large") for reason in long_rejection["reasons"])
    assert all(
        candidate is None or candidate["direction"] != "long"
        for candidate in (plan["preferred"], plan["alternate"])
    )


def test_planner_rejects_insufficient_room_to_first_opposing_obstacle() -> None:
    state = _state()
    state["levels"]["nearest_important_swing_high"] = 115.0

    plan = build_trade_plan(state, _config())

    long_rejection = next(item for item in plan["rejections"] if item["direction"] == "long")
    assert any("insufficient_room_to_first_obstacle" in reason for reason in long_rejection["reasons"])
    assert all(
        candidate is None or candidate["direction"] != "long"
        for candidate in (plan["preferred"], plan["alternate"])
    )


def test_planner_returns_preferred_and_alternate_deterministically() -> None:
    plan = build_trade_plan(_state(), _config())

    assert plan["preferred"]["direction"] == "long"
    assert plan["alternate"]["direction"] == "short"
    assert plan["preferred"]["scores"]["raw_score"] == 82.0
    assert plan["alternate"]["alignment"]["directional_target_aligned"] is True


def test_reversal_sequence_is_entry_valid_but_unconfirmed_continuation_is_hypothesis() -> None:
    state = _state()
    state["structure"]["bullish_reversal_sequence"] = True
    state["liquidity"]["recent_sell_side_sweep"] = True
    state["displacement"]["bullish_displacement"] = True
    state["fvgs"]["bullish_fvg_retest_hold"] = True

    plan = build_trade_plan(state, _config())
    candidate = plan["preferred"]

    assert candidate["setup"]["family"] == "reversal"
    assert candidate["scenario_status"] == "ENTRY VALID"
    assert all(item["satisfied"] for item in candidate["confirmation_criteria"])


def test_planner_returns_no_trade_for_fatal_market_state() -> None:
    state = _state()
    state["status"] = {
        "code": "no_analysis",
        "message": "NO ANALYSIS — STALE MARKET DATA",
    }

    plan = build_trade_plan(state, _config())

    assert plan["decision"] == DECISION_NO_TRADE
    assert plan["preferred"] is None and plan["alternate"] is None
    assert "NO ANALYSIS" in plan["rejections"][0]["reasons"][0]


def test_planner_is_insulated_from_unseen_future_append_payload() -> None:
    visible_state = _state()
    with_unseen_future = deepcopy(visible_state)
    with_unseen_future["unseen_future_append"] = {
        "close": 9999.0,
        "pdh": 10000.0,
        "entry_valid_direction": "bearish",
    }

    assert build_trade_plan(visible_state, _config()) == build_trade_plan(
        with_unseen_future, _config()
    )


def test_planner_refuses_raw_dataframe_instead_of_recalculating_features() -> None:
    with pytest.raises(TradePlannerError, match="market-state mapping"):
        build_trade_plan(pd.DataFrame({"close": [100.0]}), _config())


def test_pipeline_places_trade_plan_after_market_state_before_backtest() -> None:
    stages = pipeline.PIPELINE_STAGES
    assert stages.index("market_state") < stages.index("trade_plan")
    assert stages.index("trade_plan") < stages.index("backtest")


def test_pipeline_trade_plan_stage_uses_market_state_contract() -> None:
    plan = pipeline.stage_trade_plan(_state(), strategy_config=_config())
    assert plan["decision"] == DECISION_PLAN
    assert plan["preferred"]["direction"] == "long"
