"""Shared deterministic replay/live setup-state transitions for Phase 9."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from data_clock import normalize_as_of

POLL_INTERVAL_SECONDS = 60
MONITOR_START = (9, 30)
MONITOR_END = (10, 30)

REVERSAL_STATES = (
    "ARMED", "LIQUIDITY_REACHED", "SWEEP_CONFIRMED",
    "DISPLACEMENT_CONFIRMED", "MSS_CONFIRMED", "WAIT_RETEST",
    "RETEST_HOLDS", "ENTRY_VALID", "INVALIDATED",
)
CONTINUATION_STATES = (
    "ARMED", "LEVEL_REACHED", "DISPLACEMENT_BREAK", "ACCEPTANCE",
    "WAIT_RETEST", "RETEST_HOLDS", "MICRO_BOS", "ENTRY_VALID",
    "INVALIDATED",
)
TERMINAL_STATES = {"ENTRY_VALID", "INVALIDATED"}


class LiveStateError(RuntimeError):
    """Raised when an update violates the live-monitor contract."""


def _m(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _truth(value: Any) -> bool:
    return bool(value) if value is not None else False


def _directional(direction: str) -> str:
    return "bullish" if direction == "long" else "bearish"


def _opposite(direction: str) -> str:
    return "bearish" if direction == "long" else "bullish"


def scenario_id(candidate: Mapping[str, Any], as_of: Any, symbol: str) -> str:
    local = normalize_as_of(as_of).tz_convert("America/New_York")
    setup = _m(candidate.get("setup"))
    trigger = _m(candidate.get("trigger"))
    identity = {
        "session_date": str(local.date()),
        "symbol": symbol,
        "direction": candidate.get("direction"),
        "family": setup.get("family"),
        "subtype": setup.get("subtype"),
        "trigger_source": trigger.get("source"),
        "trigger_level": trigger.get("level"),
        "trigger_lower": trigger.get("lower"),
        "trigger_upper": trigger.get("upper"),
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    return f"{local:%Y%m%d}-{digest}"


def _alert(record: dict[str, Any], alert_type: str, as_of: str, state: str) -> dict[str, Any] | None:
    key = f"{alert_type}:{state}"
    if key in record["emitted_alert_keys"]:
        return None
    record["emitted_alert_keys"].append(key)
    record["last_alert"] = alert_type
    record["last_alert_at"] = as_of
    return {
        "scenario_id": record["scenario_id"],
        "type": alert_type,
        "state": state,
        "as_of": as_of,
    }


def arm_scenario(candidate: Mapping[str, Any], market_state: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    family = str(_m(candidate.get("setup")).get("family", ""))
    if family not in {"reversal", "continuation"}:
        raise LiveStateError("Scenario setup family must be reversal or continuation.")
    direction = str(candidate.get("direction", ""))
    if direction not in {"long", "short"}:
        raise LiveStateError("Scenario direction must be long or short.")
    as_of = str(market_state["as_of"])
    symbol = str(_m(market_state.get("instrument")).get("symbol", "UNKNOWN"))
    bias = _m(market_state.get("bias")).get("htf_bias")
    record = {
        "schema_version": "1.0.0",
        "scenario_id": scenario_id(candidate, as_of, symbol),
        "setup_family": family,
        "direction": direction,
        "current_state": "ARMED",
        "previous_state": None,
        "last_transition_at": as_of,
        "last_alert": None,
        "last_alert_at": None,
        "last_bias": bias,
        "emitted_alert_keys": [],
        "targets_hit": [],
    }
    alert = _alert(record, "PREMARKET PLAN READY", as_of, "ARMED")
    return record, [alert] if alert else []


def _validate_update(market_state: Mapping[str, Any]) -> tuple[str, bool, bool]:
    as_of = normalize_as_of(market_state["as_of"])
    local = as_of.tz_convert("America/New_York")
    one_minute = _m(_m(market_state.get("timeframes")).get("1m"))
    if one_minute.get("bar_complete") is False:
        raise LiveStateError("Incomplete bars cannot advance a setup state machine.")
    available_at = one_minute.get("available_at") or _m(market_state.get("instrument")).get("latest_bar_available_at")
    if available_at is not None and normalize_as_of(available_at) > as_of:
        raise LiveStateError("A bar is not visible at the explicit as_of cutoff.")
    status = _m(market_state.get("status"))
    freshness = _m(_m(market_state.get("data_quality")).get("freshness"))
    stale = (
        status.get("code") == "no_analysis"
        or str(freshness.get("status", "")).lower() in {"stale", "unavailable"}
        or float(freshness.get("latest_bar_age_seconds", 0) or 0) > 90.0
    )
    in_window = MONITOR_START <= (local.hour, local.minute) < MONITOR_END
    closed = (local.hour, local.minute) >= MONITOR_END
    return as_of.isoformat(), stale, closed or not in_window


def _trigger_reached(candidate: Mapping[str, Any], price: float) -> bool:
    trigger = _m(candidate.get("trigger"))
    zone = _m(trigger.get("zone"))
    lower = zone.get("lower", trigger.get("lower", trigger.get("level")))
    upper = zone.get("upper", trigger.get("upper", trigger.get("level")))
    return lower is not None and upper is not None and float(lower) <= price <= float(upper)


def _invalidated(record: Mapping[str, Any], candidate: Mapping[str, Any], market_state: Mapping[str, Any]) -> bool:
    price = _m(market_state.get("instrument")).get("latest_price")
    stop = _m(candidate.get("stop_loss")).get("price")
    if price is not None and stop is not None:
        if record["direction"] == "long" and float(price) <= float(stop):
            return True
        if record["direction"] == "short" and float(price) >= float(stop):
            return True
    structure = _m(market_state.get("structure"))
    return _truth(structure.get("thesis_invalidated")) or _truth(
        structure.get(f"{_directional(record['direction'])}_thesis_invalidated")
    )


def _next_state(record: Mapping[str, Any], candidate: Mapping[str, Any], state: Mapping[str, Any]) -> str | None:
    current = str(record["current_state"])
    direction = str(record["direction"])
    directional = _directional(direction)
    price = _m(state.get("instrument")).get("latest_price")
    structure, liquidity = _m(state.get("structure")), _m(state.get("liquidity"))
    displacement, fvgs = _m(state.get("displacement")), _m(state.get("fvgs"))
    if _invalidated(record, candidate, state):
        return "INVALIDATED"
    if current in TERMINAL_STATES or price is None:
        return None
    reached = _trigger_reached(candidate, float(price))
    displaced = _truth(displacement.get(f"{directional}_displacement"))
    retest = _truth(fvgs.get(f"{directional}_fvg_retest_hold"))
    bos = _truth(structure.get(f"{directional}_bos")) or _truth(structure.get(f"recent_{directional}_bos"))

    if record["setup_family"] == "reversal":
        sweep_side = "sell_side" if direction == "long" else "buy_side"
        swept = _truth(liquidity.get(f"{sweep_side}_liquidity_sweep")) or _truth(liquidity.get(f"recent_{sweep_side}_sweep"))
        shifted = _truth(structure.get(f"{directional}_mss")) or _truth(structure.get(f"{directional}_choch")) or _truth(structure.get(f"{directional}_core_sequence"))
        sequence = _truth(structure.get(f"{directional}_reversal_sequence"))
        rules = {
            "ARMED": ("LIQUIDITY_REACHED", reached),
            "LIQUIDITY_REACHED": ("SWEEP_CONFIRMED", swept),
            "SWEEP_CONFIRMED": ("DISPLACEMENT_CONFIRMED", displaced),
            "DISPLACEMENT_CONFIRMED": ("MSS_CONFIRMED", shifted),
            "MSS_CONFIRMED": ("WAIT_RETEST", True),
            "WAIT_RETEST": ("RETEST_HOLDS", retest or sequence),
            "RETEST_HOLDS": ("ENTRY_VALID", sequence),
        }
    else:
        break_event = _truth(structure.get(f"{directional}_displacement_structure_break_event"))
        accepted = _truth(structure.get(f"{directional}_structure_close_break"))
        sequence = _truth(structure.get(f"{directional}_continuation_sequence"))
        rules = {
            "ARMED": ("LEVEL_REACHED", reached),
            "LEVEL_REACHED": ("DISPLACEMENT_BREAK", break_event),
            "DISPLACEMENT_BREAK": ("ACCEPTANCE", accepted or sequence),
            "ACCEPTANCE": ("WAIT_RETEST", True),
            "WAIT_RETEST": ("RETEST_HOLDS", retest or sequence),
            "RETEST_HOLDS": ("MICRO_BOS", bos or sequence),
            "MICRO_BOS": ("ENTRY_VALID", sequence),
        }
    target, satisfied = rules.get(current, (None, False))
    return target if satisfied else None


TRANSITION_ALERTS = {
    "LIQUIDITY_REACHED": "TRIGGER ZONE REACHED",
    "LEVEL_REACHED": "TRIGGER ZONE REACHED",
    "SWEEP_CONFIRMED": "LIQUIDITY SWEPT",
    "DISPLACEMENT_CONFIRMED": "DISPLACEMENT CONFIRMED",
    "DISPLACEMENT_BREAK": "DISPLACEMENT CONFIRMED",
    "MSS_CONFIRMED": "MSS/CHOCH CONFIRMED",
    "WAIT_RETEST": "RETEST IN PROGRESS",
    "ENTRY_VALID": "ENTRY VALID",
    "INVALIDATED": "SETUP INVALIDATED",
}


def advance_scenario(record: Mapping[str, Any], candidate: Mapping[str, Any], market_state: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Advance at most one state from one completed observation."""
    updated = json.loads(json.dumps(record))
    as_of, stale, outside_window = _validate_update(market_state)
    alerts: list[dict[str, Any]] = []
    if stale:
        alert = _alert(updated, "STALE FEED", as_of, str(updated["current_state"]))
        return updated, [alert] if alert else []
    if outside_window:
        return updated, []

    bias = _m(market_state.get("bias")).get("htf_bias")
    if updated.get("last_bias") is not None and bias is not None and bias != updated["last_bias"]:
        alert = _alert(updated, "BIAS CHANGED", as_of, str(updated["current_state"]))
        if alert:
            alerts.append(alert)
    updated["last_bias"] = bias

    next_state = _next_state(updated, candidate, market_state)
    if next_state is not None and next_state != updated["current_state"]:
        updated["previous_state"] = updated["current_state"]
        updated["current_state"] = next_state
        updated["last_transition_at"] = as_of
        alert_type = TRANSITION_ALERTS.get(next_state)
        if alert_type:
            alert = _alert(updated, alert_type, as_of, next_state)
            if alert:
                alerts.append(alert)

    if updated["current_state"] == "ENTRY_VALID":
        price = _m(market_state.get("instrument")).get("latest_price")
        if price is not None:
            for name in ("tp1", "tp2", "tp3", "tp4"):
                target = _m(_m(candidate.get("targets")).get(name))
                target_price = target.get("price")
                hit = target_price is not None and (
                    (updated["direction"] == "long" and float(price) >= float(target_price))
                    or (updated["direction"] == "short" and float(price) <= float(target_price))
                )
                if hit and name not in updated["targets_hit"]:
                    updated["targets_hit"].append(name)
                    alert = _alert(updated, f"{name.upper()} HIT", as_of, "ENTRY_VALID")
                    if alert:
                        alerts.append(alert)
    return updated, alerts


def process_live_update(record: Mapping[str, Any], candidate: Mapping[str, Any], market_state: Mapping[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    return advance_scenario(record, candidate, market_state)


def replay_updates(record: Mapping[str, Any], candidate: Mapping[str, Any], observations: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    current = dict(record)
    alerts: list[dict[str, Any]] = []
    for observation in observations:
        current, emitted = advance_scenario(current, candidate, observation)
        alerts.extend(emitted)
    return current, alerts


def save_scenario(record: Mapping[str, Any], path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(destination)
    return destination


def load_scenario(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"scenario_id", "setup_family", "current_state", "emitted_alert_keys"}
    if not required.issubset(payload):
        raise LiveStateError("Persisted scenario is missing required state fields.")
    return payload
