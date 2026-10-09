"""Market-entry decisions use completed state and the actual entry reference."""
from copy import deepcopy

import pytest

from tests.test_trade_planner import _state, _config
from trade_planner import build_market_execution_plan, build_trade_plan, TradePlannerError


def state(direction="long", family="reversal"):
    result = _state()
    result["as_of"] = "2025-01-29T15:15:00+00:00"
    result["instrument"].update(latest_bar_timestamp="2025-01-29T15:14:00+00:00",
                                latest_bar_available_at=result["as_of"])
    result["timeframes"] = {"1m": {"bar_complete": True}}
    result["trade_candidates"] = {direction: True}
    if direction == "short":
        result["levels"] = {k: 200-v if v is not None else None for k,v in result["levels"].items()}
        for a,b in (("nearest_important_swing_high","nearest_important_swing_low"),
                    ("nearest_equal_high","nearest_equal_low"),
                    ("important_5m_fvg_above","important_5m_fvg_below"),
                    ("important_htf_fvg_above","important_htf_fvg_below"),
                    ("pdh","pdl"),("week_high","week_low")):
            result["levels"][a],result["levels"][b] = result["levels"][b],result["levels"][a]
        support = result["support_resistance"]["strongest_support"]
        result["support_resistance"]["strongest_resistance"] = {
            **support, "zone_side":"resistance", "zone_lower":100, "zone_upper":101, "zone_midpoint":100.5}
        for target in (result["draw_on_liquidity"]["primary"], result["draw_on_liquidity"]["alternate"]):
            target["price"] = 200-target["price"]
            target["direction"] = "bearish" if target["direction"]=="bullish" else "bullish"
    side = "bullish" if direction == "long" else "bearish"
    result["structure"][f"{side}_{family}_sequence"] = True
    result["structure"][f"{side}_{family}_entry_valid_event"] = True
    return result


def plan(snapshot, direction="long", entry=100, time="2025-01-29T15:15:00Z"):
    return build_market_execution_plan(snapshot, _config(), direction=direction,
                                       entry_price=entry, entry_time=time)


@pytest.mark.parametrize("direction", ["long", "short"])
@pytest.mark.parametrize("family", ["reversal", "continuation"])
def test_positive_market_plan_keeps_structure_and_market_targets(direction, family):
    snapshot = state(direction, family)
    before = deepcopy(snapshot)
    candidate = plan(snapshot, direction)["candidate"]
    assert candidate["setup"]["family"] == family
    assert candidate["entry_zone"]["risk_entry_price"] == 100
    assert candidate["stop_loss"]["price"] == (78 if direction == "long" else 122)
    assert candidate["stop_loss"]["maximum_allowed_points"] == 25
    assert candidate["targets"]["tp4"]["price"] == (180 if direction == "long" else 20)
    assert candidate["execution"]["terminal_target"] == "tp4"
    assert snapshot == before


def test_obstacle_distance_uses_market_price_not_planned_zone():
    snapshot = state("short")
    snapshot["support_resistance"]["strongest_resistance"].update(zone_lower=115, zone_upper=116)
    snapshot["levels"]["asia_low"] = 108
    assert build_trade_plan(snapshot, _config())["preferred"] is None
    accepted = plan(snapshot, "short")["candidate"]
    assert accepted is not None
    assert accepted["distance_to_first_obstacle_points"] == 30
    assert all(item["source"] != "asia_low" for item in accepted["nearby_obstacles"])


def test_real_rejection_context_does_not_fall_back_to_fixed_risk():
    snapshot = state("short")
    snapshot["instrument"]["latest_price"] = 21536
    snapshot["levels"]["nearest_important_swing_high"] = 21561
    snapshot["levels"]["asia_low"] = 21553.25
    snapshot["support_resistance"]["strongest_resistance"].update(zone_lower=21560.25, zone_upper=21562)
    result = plan(snapshot, "short", entry=21536.25)
    assert result["candidate"] is None
    assert "structural_risk_too_large:26.75>25.00" in result["rejections"]


@pytest.mark.parametrize("change,reason", [
    ("no_structure","protected_structure_unavailable"),
    ("no_runner","terminal_tp4_market_objective_unavailable"),
    ("no_event","fresh_confirmation_event_required"),
    ("not_candidate","directional_score_candidate_required"),
    ("incomplete","completed_confirmation_required"),
])
def test_missing_execution_evidence_fails_closed(change, reason):
    snapshot = state()
    if change == "no_structure": snapshot["levels"]["nearest_important_swing_low"] = None
    elif change == "no_runner": snapshot["levels"]["week_high"] = None
    elif change == "no_event": snapshot["structure"]["bullish_reversal_entry_valid_event"] = False
    elif change == "not_candidate": snapshot["trade_candidates"]["long"] = False
    else: snapshot["timeframes"]["1m"]["bar_complete"] = False
    result = plan(snapshot)
    assert result["candidate"] is None
    assert reason in result["rejections"]


@pytest.mark.parametrize("time", ["2025-01-29T15:16:00Z", "2025-01-29T15:14:00Z"])
def test_delayed_or_early_execution_is_rejected(time):
    assert plan(state(), time=time)["candidate"] is None


def test_fill_at_end_of_entry_window_is_rejected():
    snapshot = state()
    snapshot["as_of"] = "2025-01-29T15:30:00Z"
    snapshot["instrument"].update(latest_bar_timestamp="2025-01-29T15:29:00Z",
                                latest_bar_available_at=snapshot["as_of"])
    assert "outside_fill_entry_window" in plan(snapshot, time=snapshot["as_of"])["rejections"]


def test_availability_cannot_precede_confirmation_bar_close():
    snapshot = state()
    snapshot["instrument"]["latest_bar_available_at"] = "2025-01-29T15:14:00Z"
    assert plan(snapshot)["candidate"] is None


def test_naive_execution_time_or_invalid_price_is_an_error():
    with pytest.raises(TradePlannerError): plan(state(), time="2025-01-29T15:15:00")
    with pytest.raises(TradePlannerError): plan(state(), entry=float("nan"))
