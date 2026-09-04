"""Deterministic trade hypotheses built exclusively from market state.

The planner never inspects bars or recalculates signals.  It converts the
versioned, completed-bar market-state contract into at most one preferred and
one alternate scenario while preserving the structure, DOL, and score
semantics that produced that state.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping


PLANNER_SCHEMA_VERSION = "1.0.0"
DECISION_PLAN = "TRADE PLAN"
DECISION_NO_TRADE = "NO TRADE"


class TradePlannerError(RuntimeError):
    """Raised when the market-state contract is invalid."""


@dataclass(frozen=True)
class PlannerSettings:
    structural_buffer_points: float
    preferred_risk_minimum: float
    preferred_risk_maximum: float
    maximum_structural_risk: float
    minimum_room_points: float


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _truth(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return bool(value) if value is not None else False


def _directional_name(direction: str) -> str:
    return "bullish" if direction == "long" else "bearish"


def _target_direction(target: Mapping[str, Any]) -> str | None:
    raw = str(target.get("direction", "")).strip().lower()
    if raw in {"long", "bullish", "above", "buy"}:
        return "long"
    if raw in {"short", "bearish", "below", "sell"}:
        return "short"
    side = str(target.get("side", "")).strip().lower()
    if side == "above":
        return "long"
    if side == "below":
        return "short"
    return None


def _settings(config: Mapping[str, Any]) -> PlannerSettings:
    stop_loss = _mapping(config.get("stop_loss"))
    structural = _mapping(stop_loss.get("structural"))
    preferred = _mapping(stop_loss.get("preferred_initial_range_points"))
    fixed_values = [
        value
        for item in stop_loss.get("fixed_research_values_points", [])
        if (value := _number(item)) is not None
    ]
    preferred_minimum = _number(preferred.get("minimum")) or 20.0
    preferred_maximum = _number(preferred.get("maximum")) or 25.0
    maximum_risk = max(fixed_values, default=max(35.0, preferred_maximum))
    room = _mapping(config.get("room_to_target"))
    result = PlannerSettings(
        structural_buffer_points=_number(structural.get("buffer_points")) or 0.0,
        preferred_risk_minimum=preferred_minimum,
        preferred_risk_maximum=preferred_maximum,
        maximum_structural_risk=maximum_risk,
        minimum_room_points=_number(room.get("minimum_points")) or 25.0,
    )
    if result.structural_buffer_points < 0:
        raise TradePlannerError("Structural stop buffer cannot be negative.")
    if not 0 < result.preferred_risk_minimum <= result.preferred_risk_maximum:
        raise TradePlannerError("Preferred structural-risk range is invalid.")
    if result.maximum_structural_risk < result.preferred_risk_maximum:
        raise TradePlannerError("Maximum structural risk cannot be below preferred risk.")
    if result.minimum_room_points < 0:
        raise TradePlannerError("Minimum room to target cannot be negative.")
    return result


def _price_ahead(price: float, entry: float, direction: str) -> bool:
    return price > entry if direction == "long" else price < entry


def _distance(price: float, entry: float, direction: str) -> float:
    return price - entry if direction == "long" else entry - price


def _source_reason(source: str) -> str:
    reasons = {
        "nearest_important_swing_high": "nearest active internal/external swing high",
        "nearest_important_swing_low": "nearest active internal/external swing low",
        "nearest_equal_high": "equal-high liquidity objective",
        "nearest_equal_low": "equal-low liquidity objective",
        "important_5m_fvg_above": "important 5m fair-value-gap boundary",
        "important_5m_fvg_below": "important 5m fair-value-gap boundary",
        "important_htf_fvg_above": "opposing higher-timeframe FVG boundary",
        "important_htf_fvg_below": "opposing higher-timeframe FVG boundary",
        "important_support_resistance_zone": "deterministic confluence zone",
        "pdh": "prior-day high liquidity",
        "pdl": "prior-day low liquidity",
        "pmh": "premarket high liquidity",
        "pml": "premarket low liquidity",
        "asia_high": "Asia-session high liquidity",
        "asia_low": "Asia-session low liquidity",
        "london_high": "London-session high liquidity",
        "london_low": "London-session low liquidity",
        "overnight_high": "overnight high liquidity",
        "overnight_low": "overnight low liquidity",
        "week_high": "weekly external liquidity",
        "week_low": "weekly external liquidity",
        "vwap": "session VWAP objective",
        "previous_close": "previous-close objective",
        "prior_day_half_back": "prior-day equilibrium objective",
    }
    return reasons.get(source, f"market-state objective: {source}")


def _trigger_zone(
    state: Mapping[str, Any],
    direction: str,
    latest_price: float,
) -> dict[str, Any] | None:
    confluence = _mapping(state.get("support_resistance"))
    key = "strongest_support" if direction == "long" else "strongest_resistance"
    zone = _mapping(confluence.get(key))
    lower = _number(zone.get("zone_lower"))
    upper = _number(zone.get("zone_upper"))
    midpoint = _number(zone.get("zone_midpoint"))
    if lower is not None and upper is not None:
        return {
            "source": zone.get("zone_id") or key,
            "sources": str(zone.get("sources", "")).split("|") if zone.get("sources") else [],
            "level": midpoint if midpoint is not None else (lower + upper) / 2.0,
            "zone": {"lower": min(lower, upper), "upper": max(lower, upper)},
            "reason": f"strongest deterministic {key.replace('_', ' ')}",
        }

    levels = _mapping(state.get("levels"))
    fallback = (
        ("important_5m_fvg_below", "nearest_important_swing_low", "vwap", "pml")
        if direction == "long"
        else ("important_5m_fvg_above", "nearest_important_swing_high", "vwap", "pmh")
    )
    for source in fallback:
        price = _number(levels.get(source))
        if price is None:
            continue
        if direction == "long" and price > latest_price:
            continue
        if direction == "short" and price < latest_price:
            continue
        return {
            "source": source,
            "sources": [source],
            "level": price,
            "zone": {"lower": price, "upper": price},
            "reason": _source_reason(source),
        }
    return None


def _dol_target(
    state: Mapping[str, Any],
    direction: str,
    entry: float,
) -> dict[str, Any] | None:
    dol = _mapping(state.get("draw_on_liquidity"))
    records = [dol.get("primary"), dol.get("alternate")]
    records.extend(dol.get("ranked_candidates", []) or [])
    for raw in records:
        target = _mapping(raw)
        price = _number(target.get("price"))
        if price is None or not _price_ahead(price, entry, direction):
            continue
        inferred = _target_direction(target)
        if inferred is not None and inferred != direction:
            continue
        source = str(target.get("target_type") or target.get("source") or "primary_dol")
        return {
            "price": price,
            "source": source,
            "category": target.get("target_category") or target.get("category"),
            "reason": f"ranked draw on liquidity: {_source_reason(source)}",
            "distance_points": _distance(price, entry, direction),
            "confidence": _number(target.get("confidence")),
        }
    return None


def _objective_specs(direction: str) -> tuple[tuple[str, str, bool, bool], ...]:
    if direction == "long":
        return (
            ("nearest_important_swing_high", "internal", False, False),
            ("nearest_equal_high", "internal", False, False),
            ("important_5m_fvg_above", "internal", False, False),
            ("important_htf_fvg_above", "major", True, False),
            ("previous_close", "internal", False, False),
            ("prior_day_half_back", "internal", False, False),
            ("vwap", "internal", False, False),
            ("pdh", "external", False, True),
            ("pmh", "external", False, True),
            ("asia_high", "external", False, True),
            ("london_high", "external", False, True),
            ("overnight_high", "external", False, True),
            ("week_high", "external", False, True),
        )
    return (
        ("nearest_important_swing_low", "internal", False, False),
        ("nearest_equal_low", "internal", False, False),
        ("important_5m_fvg_below", "internal", False, False),
        ("important_htf_fvg_below", "major", True, False),
        ("previous_close", "internal", False, False),
        ("prior_day_half_back", "internal", False, False),
        ("vwap", "internal", False, False),
        ("pdl", "external", False, True),
        ("pml", "external", False, True),
        ("asia_low", "external", False, True),
        ("london_low", "external", False, True),
        ("overnight_low", "external", False, True),
        ("week_low", "external", False, True),
    )


def _objectives(
    state: Mapping[str, Any],
    direction: str,
    entry: float,
) -> list[dict[str, Any]]:
    levels = _mapping(state.get("levels"))
    result: list[dict[str, Any]] = []
    for source, category, htf, external in _objective_specs(direction):
        price = _number(levels.get(source))
        if price is None or not _price_ahead(price, entry, direction):
            continue
        result.append(
            {
                "price": price,
                "source": source,
                "category": category,
                "reason": _source_reason(source),
                "distance_points": _distance(price, entry, direction),
                "is_htf_obstacle": htf,
                "is_external_liquidity": external,
            }
        )

    confluence = _mapping(state.get("support_resistance"))
    expected_side = "resistance" if direction == "long" else "support"
    for raw in confluence.get("zones", []) or []:
        zone = _mapping(raw)
        if str(zone.get("zone_side", "")) != expected_side:
            continue
        price = _number(zone.get("zone_midpoint"))
        if price is None or not _price_ahead(price, entry, direction):
            continue
        result.append(
            {
                "price": price,
                "source": zone.get("zone_id") or "important_support_resistance_zone",
                "category": "confluence_zone",
                "reason": "opposing deterministic support/resistance confluence zone",
                "distance_points": _distance(price, entry, direction),
                "is_htf_obstacle": "htf" in str(zone.get("sources", "")).lower(),
                "is_external_liquidity": False,
            }
        )

    ordered = sorted(result, key=lambda item: (item["distance_points"], str(item["source"])))
    unique: list[dict[str, Any]] = []
    for item in ordered:
        if any(math.isclose(item["price"], prior["price"], abs_tol=1e-9) for prior in unique):
            continue
        unique.append(item)
    return unique


def _target_record(
    name: str,
    objective: Mapping[str, Any] | None,
    *,
    entry: float,
    risk: float,
    direction: str,
) -> dict[str, Any] | None:
    if not objective:
        return None
    price = float(objective["price"])
    distance = _distance(price, entry, direction)
    return {
        "name": name,
        "price": price,
        "source": objective.get("source"),
        "reason": objective.get("reason"),
        "distance_points": distance,
        "reward_risk": distance / risk,
    }


def _confirmation_criteria(
    state: Mapping[str, Any],
    direction: str,
    family: str,
    trigger_exists: bool,
) -> tuple[list[dict[str, Any]], bool]:
    directional = _directional_name(direction)
    opposite_sweep = "sell_side" if direction == "long" else "buy_side"
    structure = _mapping(state.get("structure"))
    liquidity = _mapping(state.get("liquidity"))
    displacement = _mapping(state.get("displacement"))
    fvgs = _mapping(state.get("fvgs"))

    if family == "reversal":
        sequence = _truth(structure.get(f"{directional}_reversal_sequence"))
        core = sequence or _truth(structure.get(f"{directional}_core_sequence"))
        sweep = core or _truth(liquidity.get(f"recent_{opposite_sweep}_sweep")) or _truth(
            liquidity.get(f"{opposite_sweep}_liquidity_sweep")
        )
        displaced = core or _truth(displacement.get(f"{directional}_displacement"))
        shifted = core or _truth(structure.get(f"{directional}_mss")) or _truth(
            structure.get(f"{directional}_choch")
        )
        retest = sequence or _truth(fvgs.get(f"{directional}_fvg_retest_hold"))
        criteria = [
            ("important_liquidity", trigger_exists, "directional trigger level/zone exists"),
            ("liquidity_sweep", sweep, f"existing {opposite_sweep.replace('_', ' ')} sweep"),
            ("failure_to_accept_beyond_level", sweep, "sweep semantics require close/reclaim through level"),
            ("opposite_displacement", displaced, f"{directional} displacement"),
            ("mss_or_choch", shifted, f"{directional} MSS/CHoCH"),
            ("retest_hold", retest, f"{directional} FVG/retest hold"),
            ("entry_confirmation", sequence, "ordered production reversal sequence"),
        ]
        entry_valid = sequence
    else:
        sequence = _truth(structure.get(f"{directional}_continuation_sequence"))
        break_event = sequence or _truth(
            structure.get(f"{directional}_displacement_structure_break_event")
        )
        close_break = sequence or _truth(structure.get(f"{directional}_structure_close_break"))
        hold = sequence or _truth(fvgs.get(f"{directional}_fvg_retest_hold"))
        bos = sequence or _truth(structure.get(f"{directional}_bos")) or _truth(
            structure.get(f"recent_{directional}_bos")
        )
        criteria = [
            ("important_level", trigger_exists, "directional trigger level/zone exists"),
            ("displacement_break", break_event, "displacement-confirmed structure break"),
            ("body_close_beyond_level", close_break, "production close-break flag"),
            ("acceptance_follow_through", sequence, "later-bar continuation sequence"),
            ("pullback", hold, "later-bar FVG/level retest"),
            ("level_or_fvg_hold", hold, f"{directional} FVG/retest hold"),
            ("micro_bos", bos, f"{directional} BOS/continuation break"),
            ("entry_confirmation", sequence, "ordered production continuation sequence"),
        ]
        entry_valid = sequence

    return (
        [
            {"criterion": name, "satisfied": satisfied, "evidence": evidence}
            for name, satisfied, evidence in criteria
        ],
        entry_valid,
    )


def _attempt_candidate(
    state: Mapping[str, Any],
    direction: str,
    settings: PlannerSettings,
) -> tuple[dict[str, Any] | None, list[str]]:
    rejections: list[str] = []
    latest_price = _number(_mapping(state.get("instrument")).get("latest_price"))
    if latest_price is None:
        return None, ["latest_price_unavailable"]

    score = _mapping(_mapping(state.get("scores")).get(direction))
    if _truth(score.get("disabled")):
        rejections.append(f"score_disabled:{score.get('disable_reason') or 'unspecified'}")
    if str(score.get("band", "")).strip().lower() == "no_trade":
        rejections.append("score_band_no_trade")

    trigger = _trigger_zone(state, direction, latest_price)
    if trigger is None:
        rejections.append("important_trigger_level_unavailable")
        return None, rejections
    entry_zone = _mapping(trigger["zone"])
    entry = (
        float(entry_zone["upper"])
        if direction == "long"
        else float(entry_zone["lower"])
    )

    levels = _mapping(state.get("levels"))
    structure_source = (
        "nearest_important_swing_low" if direction == "long" else "nearest_important_swing_high"
    )
    structure_price = _number(levels.get(structure_source))
    if structure_price is None:
        rejections.append("protected_structure_unavailable")
        return None, rejections
    if direction == "long" and structure_price >= entry:
        rejections.append("protected_structure_not_below_entry")
        return None, rejections
    if direction == "short" and structure_price <= entry:
        rejections.append("protected_structure_not_above_entry")
        return None, rejections

    stop = (
        structure_price - settings.structural_buffer_points
        if direction == "long"
        else structure_price + settings.structural_buffer_points
    )
    risk = abs(entry - stop)
    if risk > settings.maximum_structural_risk:
        rejections.append(
            f"structural_risk_too_large:{risk:.2f}>{settings.maximum_structural_risk:.2f}"
        )

    primary = _dol_target(state, direction, entry)
    if primary is None:
        rejections.append("directional_primary_dol_unavailable")
        return None, rejections
    primary_distance = float(primary["distance_points"])
    if primary_distance < settings.minimum_room_points:
        rejections.append(
            f"insufficient_room_to_primary_dol:{primary_distance:.2f}<{settings.minimum_room_points:.2f}"
        )

    objectives = _objectives(state, direction, entry)
    first_obstacle = objectives[0] if objectives else primary
    first_distance = float(first_obstacle["distance_points"])
    if first_distance < settings.minimum_room_points:
        label = "immediate_opposing_htf_obstacle" if first_obstacle.get("is_htf_obstacle") else "insufficient_room_to_first_obstacle"
        rejections.append(
            f"{label}:{first_distance:.2f}<{settings.minimum_room_points:.2f}"
        )

    before_primary = [
        objective
        for objective in objectives
        if objective["distance_points"] < primary_distance
    ]
    internal = [item for item in before_primary if item["category"] == "internal"]
    tp1_objective = internal[0] if internal else (before_primary[0] if before_primary else None)
    if tp1_objective is None:
        rejections.append("tp1_market_objective_unavailable_before_primary_dol")
        return None, rejections
    tp2_objective = next(
        (
            item
            for item in before_primary
            if item["distance_points"] > tp1_objective["distance_points"]
        ),
        None,
    )
    runner = next(
        (
            item
            for item in objectives
            if item["distance_points"] > primary_distance
            and item["is_external_liquidity"]
        ),
        None,
    )

    tp1_rr = float(tp1_objective["distance_points"]) / risk
    primary_rr = primary_distance / risk
    if tp1_rr < 1.0:
        rejections.append(f"poor_asymmetry_to_tp1:{tp1_rr:.2f}<1.00")
    if primary_rr < 1.0:
        rejections.append(f"poor_asymmetry_to_primary_dol:{primary_rr:.2f}<1.00")
    if rejections:
        return None, rejections

    structure = _mapping(state.get("structure"))
    liquidity = _mapping(state.get("liquidity"))
    directional = _directional_name(direction)
    opposite_sweep = "sell_side" if direction == "long" else "buy_side"
    reversal_context = (
        _truth(structure.get(f"{directional}_reversal_sequence"))
        or _truth(liquidity.get(f"recent_{opposite_sweep}_sweep"))
        or _truth(liquidity.get(f"{opposite_sweep}_liquidity_sweep"))
    )
    family = "reversal" if reversal_context else "continuation"
    criteria, entry_valid = _confirmation_criteria(
        state, direction, family, trigger_exists=True
    )

    targets = {
        "tp1": _target_record("TP1", tp1_objective, entry=entry, risk=risk, direction=direction),
        "tp2": _target_record("TP2", tp2_objective, entry=entry, risk=risk, direction=direction),
        "tp3": _target_record("TP3", primary, entry=entry, risk=risk, direction=direction),
        "tp4": _target_record("TP4", runner, entry=entry, risk=risk, direction=direction),
    }
    preferred_range = (
        settings.preferred_risk_minimum <= risk <= settings.preferred_risk_maximum
    )
    downgrade_reasons = [] if preferred_range else ["structural_risk_outside_preferred_20_25_range"]
    dol = _mapping(state.get("draw_on_liquidity"))
    dol_direction = str(dol.get("direction", "neutral")).strip().lower()
    bias = _mapping(state.get("bias"))
    htf_bias = str(bias.get("htf_bias", "unknown")).strip().lower()
    expected_bias = directional
    candidate = {
        "direction": direction,
        "setup": {
            "family": family,
            "subtype": (
                "liquidity_sweep_reversal"
                if family == "reversal"
                else "displacement_break_retest_continuation"
            ),
        },
        "scenario_status": "ENTRY VALID" if entry_valid else "HYPOTHESIS",
        "trigger": trigger,
        "entry_zone": {
            "lower": float(entry_zone["lower"]),
            "upper": float(entry_zone["upper"]),
            "risk_entry_price": entry,
            "basis": "conservative edge of deterministic trigger zone",
        },
        "structural_invalidation": {
            "source": structure_source,
            "level": structure_price,
            "reason": "protected active swing structure from market state",
        },
        "stop_loss": {
            "price": stop,
            "buffer_points": settings.structural_buffer_points,
            "risk_points": risk,
            "preferred_minimum_points": settings.preferred_risk_minimum,
            "preferred_maximum_points": settings.preferred_risk_maximum,
            "maximum_allowed_points": settings.maximum_structural_risk,
            "within_preferred_range": preferred_range,
        },
        "targets": targets,
        "confirmation_criteria": criteria,
        "invalidation_criteria": [
            {
                "criterion": "structural_stop_breached",
                "level": stop,
                "reason": "price accepts beyond protected structure plus buffer",
            },
            {
                "criterion": "trigger_retest_fails",
                "level": trigger["level"],
                "reason": "deterministic level/FVG hold fails",
            },
            {
                "criterion": "directional_thesis_flips",
                "level": None,
                "reason": "DOL/structure state invalidates the planned direction",
            },
        ],
        "nearby_obstacles": objectives[:6],
        "distance_to_first_obstacle_points": first_distance,
        "distance_to_primary_target_points": primary_distance,
        "reward_risk": {
            "tp1": targets["tp1"]["reward_risk"],
            "tp2": targets["tp2"]["reward_risk"] if targets["tp2"] else None,
            "tp3": targets["tp3"]["reward_risk"],
            "tp4": targets["tp4"]["reward_risk"] if targets["tp4"] else None,
        },
        "scores": {
            "raw_score": _number(score.get("raw_score")),
            "band": score.get("band"),
            "positive_points": _number(score.get("positive_points")),
            "penalty_points": _number(score.get("penalty_points")),
            "components": dict(_mapping(score.get("components"))),
        },
        "alignment": {
            "dol_direction": dol_direction,
            "dol_aligned": dol_direction in {direction, directional},
            "directional_target_aligned": True,
            "htf_bias": htf_bias,
            "bias_aligned": htf_bias == expected_bias,
        },
        "quality": {
            "classification": "downgraded" if downgrade_reasons else "qualified",
            "room_to_run": True,
            "poor_asymmetry": False,
            "downgrade_reasons": downgrade_reasons,
        },
    }
    return candidate, []


def build_trade_plan(
    market_state: Mapping[str, Any],
    strategy_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build preferred/alternate hypotheses from one market-state snapshot."""
    if not isinstance(market_state, Mapping):
        raise TradePlannerError("Trade planner requires a market-state mapping.")
    for required in ("schema_version", "as_of", "status", "instrument"):
        if required not in market_state:
            raise TradePlannerError(f"Market state is missing required field: {required}")

    plan: dict[str, Any] = {
        "schema_version": PLANNER_SCHEMA_VERSION,
        "market_state_schema_version": market_state["schema_version"],
        "generated_at": market_state.get("generated_at"),
        "as_of": market_state["as_of"],
        "instrument": dict(_mapping(market_state.get("instrument"))),
        "decision": DECISION_NO_TRADE,
        "preferred": None,
        "alternate": None,
        "rejections": [],
    }
    status = _mapping(market_state.get("status"))
    if str(status.get("code", "")).lower() == "no_analysis":
        plan["rejections"] = [
            {
                "direction": "all",
                "reasons": [f"market_state:{status.get('message', 'NO ANALYSIS')}"],
            }
        ]
        return plan

    settings = _settings(strategy_config or {})
    accepted: list[dict[str, Any]] = []
    for direction in ("long", "short"):
        candidate, reasons = _attempt_candidate(market_state, direction, settings)
        if candidate is not None:
            accepted.append(candidate)
        if reasons:
            plan["rejections"].append({"direction": direction, "reasons": reasons})

    preferred_hint = str(
        _mapping(market_state.get("scores")).get("preferred_direction", "neutral")
    ).lower()
    accepted.sort(
        key=lambda candidate: (
            candidate["quality"]["classification"] != "qualified",
            candidate["direction"] != preferred_hint,
            -(_number(candidate["scores"].get("raw_score")) or 0.0),
            candidate["direction"],
        )
    )
    if accepted:
        plan["decision"] = DECISION_PLAN
        plan["preferred"] = accepted[0]
        plan["alternate"] = accepted[1] if len(accepted) > 1 else None
    return plan
