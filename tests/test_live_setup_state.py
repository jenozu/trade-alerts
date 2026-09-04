from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from live_setup_state import (
    LiveStateError,
    POLL_INTERVAL_SECONDS,
    advance_scenario,
    arm_scenario,
    load_scenario,
    process_live_update,
    replay_updates,
    save_scenario,
)
from trade_planner import build_trade_plan
from test_trade_planner import _config, _state


def _candidate(direction="long", family="reversal"):
    plan = build_trade_plan(_state(), _config())
    candidate = deepcopy(plan["preferred"] if direction == "long" else plan["alternate"])
    candidate["setup"]["family"] = family
    return candidate


def _observation(direction="long", minute=30, price=None, **evidence):
    state = deepcopy(_state())
    as_of = f"2026-09-04T13:{minute:02d}:00+00:00"
    trigger_price = 100.0 if direction == "long" else 111.0
    state["as_of"] = as_of
    state["generated_at"] = as_of
    state["instrument"]["latest_price"] = trigger_price if price is None else price
    state["instrument"]["latest_bar_available_at"] = as_of
    state["timeframes"] = {"1m": {"bar_complete": True, "available_at": as_of}}
    state["status"] = {"code": "ready", "message": "ANALYSIS READY"}
    state["data_quality"] = {"freshness": {"status": "fresh", "latest_bar_age_seconds": 0}}
    state["structure"] = {}
    state["liquidity"] = {}
    state["displacement"] = {}
    state["fvgs"] = {}
    state["bias"] = {"htf_bias": "bullish" if direction == "long" else "bearish"}
    for section, values in evidence.items():
        state[section].update(values)
    return state


def _reversal_replay(direction):
    d = "bullish" if direction == "long" else "bearish"
    sweep = "sell_side" if direction == "long" else "buy_side"
    return [
        _observation(direction, 30),
        _observation(direction, 31, liquidity={f"recent_{sweep}_sweep": True}),
        _observation(direction, 32, displacement={f"{d}_displacement": True}),
        _observation(direction, 33, structure={f"{d}_mss": True}),
        _observation(direction, 34),
        _observation(direction, 35, fvgs={f"{d}_fvg_retest_hold": True}),
        _observation(direction, 36, structure={f"{d}_reversal_sequence": True}),
    ]


def _continuation_replay(direction):
    d = "bullish" if direction == "long" else "bearish"
    return [
        _observation(direction, 30),
        _observation(direction, 31, structure={f"{d}_displacement_structure_break_event": True}),
        _observation(direction, 32, structure={f"{d}_structure_close_break": True}),
        _observation(direction, 33),
        _observation(direction, 34, fvgs={f"{d}_fvg_retest_hold": True}),
        _observation(direction, 35, structure={f"{d}_bos": True}),
        _observation(direction, 36, structure={f"{d}_continuation_sequence": True}),
    ]


@pytest.mark.parametrize(
    ("direction", "family", "observations"),
    [
        ("long", "reversal", _reversal_replay("long")),
        ("short", "reversal", _reversal_replay("short")),
        ("long", "continuation", _continuation_replay("long")),
        ("short", "continuation", _continuation_replay("short")),
    ],
)
def test_full_directional_replays(direction, family, observations):
    candidate = _candidate(direction, family)
    record, armed = arm_scenario(candidate, _state())
    expected = (
        ["LIQUIDITY_REACHED", "SWEEP_CONFIRMED", "DISPLACEMENT_CONFIRMED", "MSS_CONFIRMED", "WAIT_RETEST", "RETEST_HOLDS", "ENTRY_VALID"]
        if family == "reversal"
        else ["LEVEL_REACHED", "DISPLACEMENT_BREAK", "ACCEPTANCE", "WAIT_RETEST", "RETEST_HOLDS", "MICRO_BOS", "ENTRY_VALID"]
    )
    observed = []
    manual = deepcopy(record)
    for observation in observations:
        manual, _ = advance_scenario(manual, candidate, observation)
        observed.append(manual["current_state"])
    result, alerts = replay_updates(record, candidate, observations)
    assert result["current_state"] == "ENTRY_VALID"
    assert observed == expected
    assert result == manual
    assert len(armed) == 1 and armed[0]["type"] == "PREMARKET PLAN READY"
    assert alerts[-1]["type"] == "ENTRY VALID"


def test_structural_invalidation_is_terminal():
    candidate = _candidate("long")
    record, _ = arm_scenario(candidate, _state())
    result, alerts = advance_scenario(record, candidate, _observation("long", price=70.0))
    assert result["current_state"] == "INVALIDATED"
    assert alerts[0]["type"] == "SETUP INVALIDATED"
    recovered, repeated = advance_scenario(result, candidate, _observation("long", 31, structure={"bullish_reversal_sequence": True}))
    assert recovered["current_state"] == "INVALIDATED" and repeated == []


def test_same_bar_evidence_advances_only_one_state():
    candidate = _candidate("long", "continuation")
    record, _ = arm_scenario(candidate, _state())
    all_evidence = _observation("long", structure={
        "bullish_displacement_structure_break_event": True,
        "bullish_structure_close_break": True,
        "bullish_bos": True,
        "bullish_continuation_sequence": True,
    }, fvgs={"bullish_fvg_retest_hold": True})
    result, _ = advance_scenario(record, candidate, all_evidence)
    assert result["current_state"] == "LEVEL_REACHED"


def test_incomplete_or_not_yet_visible_bar_is_rejected():
    candidate = _candidate()
    record, _ = arm_scenario(candidate, _state())
    incomplete = _observation(); incomplete["timeframes"]["1m"]["bar_complete"] = False
    with pytest.raises(LiveStateError, match="Incomplete"):
        advance_scenario(record, candidate, incomplete)
    future = _observation(); future["timeframes"]["1m"]["available_at"] = "2026-09-04T13:31:00+00:00"
    with pytest.raises(LiveStateError, match="not visible"):
        advance_scenario(record, candidate, future)


def test_stale_feed_alert_is_deduplicated():
    candidate = _candidate(); record, _ = arm_scenario(candidate, _state())
    stale = _observation(); stale["data_quality"]["freshness"] = {"status": "stale", "latest_bar_age_seconds": 180}
    result, first = advance_scenario(record, candidate, stale)
    result, second = advance_scenario(result, candidate, stale)
    assert [item["type"] for item in first] == ["STALE FEED"] and second == []


def test_restart_recovery_preserves_state_and_dedup(tmp_path):
    candidate = _candidate(); record, _ = arm_scenario(candidate, _state())
    reached, alerts = advance_scenario(record, candidate, _observation())
    recovered = load_scenario(save_scenario(reached, tmp_path / "scenario.json"))
    unchanged, duplicates = advance_scenario(recovered, candidate, _observation())
    assert recovered == reached and unchanged["scenario_id"] == record["scenario_id"]
    assert alerts[0]["type"] == "TRIGGER ZONE REACHED" and duplicates == []


def test_tp_alerts_progress_once_after_entry():
    candidate = _candidate("long")
    record, _ = arm_scenario(candidate, _state())
    record["current_state"] = "ENTRY_VALID"
    alerts = []
    for minute, price in enumerate((130.0, 135.0, 160.0, 180.0), start=30):
        record, emitted = advance_scenario(record, candidate, _observation("long", minute, price=price))
        alerts.extend(emitted)
    record, duplicate = advance_scenario(record, candidate, _observation("long", 34, price=180.0))
    assert [item["type"] for item in alerts] == ["TP1 HIT", "TP2 HIT", "TP3 HIT", "TP4 HIT"]
    assert duplicate == []


def test_future_append_payload_cannot_change_transition():
    candidate = _candidate(); record, _ = arm_scenario(candidate, _state())
    visible = _observation(); future = deepcopy(visible)
    future["unseen_future_append"] = {"bullish_reversal_sequence": True, "price": 99999}
    assert advance_scenario(record, candidate, visible) == advance_scenario(record, candidate, future)


def test_live_and_replay_share_exact_transition_core():
    candidate = _candidate("long", "continuation"); record, _ = arm_scenario(candidate, _state())
    observation = _observation("long")
    live = process_live_update(record, candidate, observation)
    replay = replay_updates(record, candidate, [observation])
    assert live == replay


def test_bias_change_alert_and_monitoring_end():
    assert POLL_INTERVAL_SECONDS == 60
    candidate = _candidate(); record, _ = arm_scenario(candidate, _state())
    changed = _observation(); changed["bias"]["htf_bias"] = "bearish"
    result, alerts = advance_scenario(record, candidate, changed)
    assert "BIAS CHANGED" in [item["type"] for item in alerts]
    closed = deepcopy(changed); closed["as_of"] = "2026-09-04T14:30:00+00:00"
    closed["timeframes"]["1m"]["available_at"] = closed["as_of"]
    stopped, after_close = advance_scenario(result, candidate, closed)
    assert stopped["current_state"] == result["current_state"] and after_close == []
