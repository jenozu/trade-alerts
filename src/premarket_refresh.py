"""Causal 09:25 refresh comparison over independently built snapshots."""
from __future__ import annotations

from typing import Any, Mapping

import pandas as pd

from data_clock import normalize_as_of
from market_state import build_market_state, save_market_state_snapshot
from trade_planner import build_trade_plan

UNCHANGED = "UNCHANGED"
STRENGTHENED = "STRENGTHENED"
WEAKENED = "WEAKENED"
FLIPPED = "FLIPPED"


def _m(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _candidate(plan: Mapping[str, Any]) -> Mapping[str, Any]:
    return _m(plan.get("preferred"))


def _direction(plan: Mapping[str, Any]) -> str | None:
    return _candidate(plan).get("direction")

def validate_premarket_as_of(value: Any) -> pd.Timestamp:
    as_of = normalize_as_of(value).tz_convert("America/New_York")
    if (as_of.hour, as_of.minute) > (9, 25):
        raise ValueError("Premarket refresh may not use information after 09:25 ET.")
    return as_of


def build_0925_refresh(
    dataframe: pd.DataFrame,
    *,
    as_of: Any,
    symbol: str,
    contract: str | None,
    strategy_config: Mapping[str, Any],
    data_quality: Mapping[str, Any],
    freshness: Mapping[str, Any],
    source_snapshots: list[str],
    state_directory: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    """Build and preserve a fresh causal 09:25 state plus its planner output.

    ``dataframe`` is the freshly enriched pipeline output. ``build_market_state``
    applies the canonical completed-bar/as-of filter again before serialization.
    """
    cutoff = validate_premarket_as_of(as_of)
    state = build_market_state(
        dataframe,
        as_of=cutoff,
        symbol=symbol,
        contract=contract,
        strategy_config=strategy_config,
        data_quality=data_quality,
        freshness=freshness,
        source_snapshots=source_snapshots,
    )
    paths = save_market_state_snapshot(state, state_directory)
    plan = build_trade_plan(state, strategy_config)
    return state, plan, {"snapshot": str(paths.snapshot), "latest": str(paths.latest)}

def compare_premarket_refresh(
    morning_state: Mapping[str, Any],
    morning_plan: Mapping[str, Any],
    refreshed_state: Mapping[str, Any],
    refreshed_plan: Mapping[str, Any],
) -> dict[str, Any]:
    """Deterministically classify only values already present in two snapshots."""
    morning_time = normalize_as_of(morning_state["as_of"])
    refresh_time = validate_premarket_as_of(refreshed_state["as_of"])
    if refresh_time.tz_convert("UTC") < morning_time:
        raise ValueError("Refresh precedes morning snapshot.")
    before, after = _candidate(morning_plan), _candidate(refreshed_plan)
    changes: list[dict[str, Any]] = []

    def watch(category: str, path: str, left: Any, right: Any) -> None:
        if left != right:
            changes.append(
                {
                    "category": category,
                    "path": path,
                    "before": left,
                    "after": right,
                    "reason": f"{category} changed between the preserved 09:00 and 09:25 snapshots",
                }
            )

    watch("bias", "bias", _m(morning_state.get("bias")), _m(refreshed_state.get("bias")))
    watch("level", "levels", _m(morning_state.get("levels")), _m(refreshed_state.get("levels")))
    watch("liquidity/sweep", "liquidity", _m(morning_state.get("liquidity")), _m(refreshed_state.get("liquidity")))
    watch("structure", "structure", _m(morning_state.get("structure")), _m(refreshed_state.get("structure")))
    watch(
        "DOL",
        "draw_on_liquidity.primary",
        _m(_m(morning_state.get("draw_on_liquidity")).get("primary")),
        _m(_m(refreshed_state.get("draw_on_liquidity")).get("primary")),
    )
    for category, field in (
        ("entry", "entry_zone"),
        ("invalidation", "structural_invalidation"),
        ("target", "targets"),
        ("entry", "scenario_status"),
    ):
        watch(category, field, before.get(field), after.get(field))
    old_dir, new_dir = _direction(morning_plan), _direction(refreshed_plan)
    if old_dir and new_dir and old_dir != new_dir:
        classification = FLIPPED
    elif not before and after:
        classification = STRENGTHENED
    elif before and not after:
        classification = WEAKENED
    elif before.get("scenario_status") != "ENTRY VALID" and after.get("scenario_status") == "ENTRY VALID":
        classification = STRENGTHENED
    elif before.get("scenario_status") == "ENTRY VALID" and after.get("scenario_status") != "ENTRY VALID":
        classification = WEAKENED
    elif not changes:
        classification = UNCHANGED
    else:
        old_score, new_score = _m(before.get("scores")).get("raw_score"), _m(after.get("scores")).get("raw_score")
        improved = (
            isinstance(old_score, (int, float))
            and isinstance(new_score, (int, float))
            and new_score > old_score
        )
        classification = STRENGTHENED if improved else WEAKENED
    return {
        "schema_version": "1.0.0",
        "morning_as_of": morning_time.isoformat(),
        "refreshed_as_of": refresh_time.isoformat(),
        "classification": classification,
        "changes": changes,
        "source_snapshots": {
            "morning": list(morning_state.get("source_snapshots", [])),
            "refreshed": list(refreshed_state.get("source_snapshots", [])),
        },
    }
