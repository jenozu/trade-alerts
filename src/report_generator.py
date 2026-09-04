"""Deterministic 09:00 report rendering from immutable state and plan payloads."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping

import pandas as pd

from data_clock import normalize_as_of

REPORT_SCHEMA_VERSION = "1.0.0"


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _json(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def _lines(value: Mapping[str, Any] | None) -> list[str]:
    if not value:
        return ["- None available from deterministic state."]
    return [f"- `{key}`: {value[key]}" for key in sorted(value)]


def _scenario(candidate: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return _mapping(candidate)


def build_morning_alert(market_state: Mapping[str, Any], trade_plan: Mapping[str, Any]) -> dict[str, Any]:
    """Create JSON without deriving, rounding, or recalculating market levels."""
    if not isinstance(market_state, Mapping) or not isinstance(trade_plan, Mapping):
        raise TypeError("Morning output requires market-state and trade-plan mappings.")
    for required in ("schema_version", "as_of", "status", "instrument"):
        if required not in market_state:
            raise ValueError(f"market_state missing {required}")
    status = _mapping(market_state["status"])
    no_analysis = status.get("code") == "no_analysis"
    preferred, alternate = _scenario(trade_plan.get("preferred")), _scenario(trade_plan.get("alternate"))
    decision = "NO ANALYSIS" if no_analysis else str(trade_plan.get("decision", "NO TRADE"))
    levels = _mapping(market_state.get("levels"))
    markup = {
        "levels": {key: levels.get(key) for key in (
            "pdh", "pdl", "pmh", "pml", "asia_high", "asia_low", "london_high", "london_low"
        )},
        "primary_dol": _mapping(market_state.get("draw_on_liquidity")).get("primary"),
        "important_fvgs": _mapping(market_state.get("fvgs")),
        "preferred_trigger": preferred.get("trigger") if preferred else None,
        "alternate_trigger": alternate.get("trigger") if alternate else None,
        "no_trade_zone": None,
        "entries_stops_targets": [
            {"scenario": label, "entry_zone": item.get("entry_zone"), "stop_loss": item.get("stop_loss"), "targets": item.get("targets")}
            for label, item in (("preferred", preferred), ("alternate", alternate)) if item
        ],
    }
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_type": "morning_alert",
        "as_of": market_state["as_of"],
        "generated_at": market_state.get("generated_at", market_state["as_of"]),
        "source_market_state": {
            "schema_version": market_state["schema_version"], "as_of": market_state["as_of"],
            "snapshots": list(market_state.get("source_snapshots", [])),
        },
        "decision": decision,
        "is_hypothesis": not no_analysis,
        "current_market_context": {"instrument": _json(market_state["instrument"]), "status": _json(status)},
        "bias": _json(market_state.get("bias", {})),
        "draw_on_liquidity": _json(market_state.get("draw_on_liquidity", {})),
        "key_liquidity_and_structure": _json({"levels": levels, "liquidity": market_state.get("liquidity", {}), "structure": market_state.get("structure", {})}),
        "chart_markup": _json(markup),
        "preferred": _json(preferred) if preferred else None,
        "alternate": _json(alternate) if alternate else None,
        "best_play_right_now": _json(preferred) if preferred else {"decision": decision, "rejections": _json(trade_plan.get("rejections", []))},
        "no_analysis_reason": status.get("message") if no_analysis else None,
    }


def render_morning_markdown(alert: Mapping[str, Any]) -> str:
    """Render report values verbatim from ``build_morning_alert`` output."""
    lines = ["# 09:00 ET Trade Plan", "", f"As of: `{alert['as_of']}`", f"Decision: **{alert['decision']}**", "", "## Current Market Context", *_lines(_mapping(alert.get("current_market_context"))), "", "## Bias", *_lines(_mapping(alert.get("bias"))), "", "## Primary DOL", f"- {json.dumps(_mapping(alert.get('draw_on_liquidity')).get('primary'), sort_keys=True)}", "", "## Alternate DOL", f"- {json.dumps(_mapping(alert.get('draw_on_liquidity')).get('alternate'), sort_keys=True)}", "", "## Key Liquidity & Structure Levels", *_lines(_mapping(alert.get("key_liquidity_and_structure"))), "", "## Chart Markup", f"```json\n{json.dumps(alert.get('chart_markup', {}), indent=2, sort_keys=True)}\n```", "", "## Scenario A — Preferred", f"```json\n{json.dumps(alert.get('preferred'), indent=2, sort_keys=True)}\n```", "", "## Scenario B — Alternate", f"```json\n{json.dumps(alert.get('alternate'), indent=2, sort_keys=True)}\n```", "", "## Trigger Zones", f"- Preferred: {json.dumps(_mapping(alert.get('preferred')).get('trigger'), sort_keys=True)}", f"- Alternate: {json.dumps(_mapping(alert.get('alternate')).get('trigger'), sort_keys=True)}", "", "## Best Play Right Now", f"```json\n{json.dumps(alert.get('best_play_right_now'), indent=2, sort_keys=True)}\n```"]
    if alert.get("is_hypothesis"):
        lines.extend(["", "_This 09:00 output is a hypothesis/plan. A setup is confirmed only when the deterministic state marks it entry-valid._"])
    return "\n".join(lines) + "\n"


def save_morning_report(alert: Mapping[str, Any], output_directory: str | Path, *, markdown: str | None = None) -> dict[str, Path]:
    local = normalize_as_of(alert["as_of"]).tz_convert("America/New_York")
    directory = Path(output_directory); directory.mkdir(parents=True, exist_ok=True)
    stem = f"{local:%Y-%m-%d_%H%M}_morning_report"
    json_path, markdown_path = directory / f"{stem}.json", directory / f"{stem}.md"
    suffix = 2
    while json_path.exists() or markdown_path.exists():
        json_path, markdown_path = directory / f"{stem}_v{suffix}.json", directory / f"{stem}_v{suffix}.md"; suffix += 1
    json_path.write_text(json.dumps(_json(alert), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown or render_morning_markdown(alert), encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def generate_optional_narrative(generator: Callable[[dict[str, Any]], str], alert: Mapping[str, Any]) -> str | None:
    """Optional prose is isolated; any failure leaves deterministic payload unchanged."""
    try:
        return str(generator(deepcopy(_json(alert))))
    except Exception:
        return None
