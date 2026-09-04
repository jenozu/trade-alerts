"""Versioned deterministic market-state snapshots.

The builder consumes the already-enriched production dataframe and applies the
canonical completed-bar ``as_of`` filter itself.  It does not recalculate any
trading signal, so replay, premarket, and future live callers share the same
feature semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd

from confluence_zones import build_confluence_zones
from data_clock import filter_as_of, normalize_as_of, visibility_times


SCHEMA_VERSION = "1.0.0"
STATUS_READY = "ANALYSIS READY"
STATUS_PROJECTX_UNAVAILABLE = "NO ANALYSIS — PROJECTX DATA UNAVAILABLE"
STATUS_STALE = "NO ANALYSIS — STALE MARKET DATA"
STATUS_DEGRADED_HISTORY = "ANALYSIS DEGRADED — REQUIRED HISTORY INCOMPLETE"
STATUS_DATA_QUALITY_FAILURE = "NO ANALYSIS — DATA QUALITY FAILURE"


class MarketStateError(RuntimeError):
    """Raised when a market-state snapshot cannot be built safely."""


@dataclass(frozen=True)
class MarketStatePaths:
    snapshot: Path
    latest: Path


LEVEL_COLUMNS: dict[str, tuple[str, ...]] = {
    "pdh": ("pdh",),
    "pdl": ("pdl",),
    "previous_close": ("pdc", "previous_close"),
    "prior_day_half_back": ("half_back",),
    "pmh": ("pmh",),
    "pml": ("pml",),
    "asia_high": ("ash",),
    "asia_low": ("asl",),
    "london_high": ("loh",),
    "london_low": ("lol",),
    "overnight_high": ("onh",),
    "overnight_low": ("onl",),
    "week_high": ("week_high",),
    "week_low": ("week_low",),
    "vwap": ("vwap",),
    "important_htf_fvg_above": ("nearest_htf_fvg_above",),
    "important_htf_fvg_below": ("nearest_htf_fvg_below",),
    "important_5m_fvg_above": ("nearest_5m_fvg_above",),
    "important_5m_fvg_below": ("nearest_5m_fvg_below",),
    "cash_open": ("rth_open",),
    "or5_high": ("or5_high", "orh_5"),
    "or5_low": ("or5_low", "orl_5"),
    "or15_high": ("or15_high", "orh_15"),
    "or15_low": ("or15_low", "orl_15"),
}


def _json_value(value: Any) -> Any:
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp,)):
        if value.tzinfo is None:
            import traceback
            print("\n=== NAIVE TIMESTAMP DETECTED ===")
            print("VALUE:", repr(value))
            print("TYPE:", type(value))
            print("CALL STACK:")
            traceback.print_stack(limit=8)
            raise MarketStateError("Market-state timestamps must be timezone-aware.")
        return value.tz_convert("UTC").isoformat()
    if isinstance(value, datetime):
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is None:
            raise MarketStateError("Market-state timestamps must be timezone-aware.")
        return timestamp.tz_convert("UTC").isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.datetime64):
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is None:
            return timestamp.isoformat()
        return timestamp.tz_convert("UTC").isoformat()
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, set):
        return [_json_value(item) for item in sorted(value, key=str)]
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _first_value(row: pd.Series, columns: Iterable[str]) -> Any:
    for column in columns:
        if column not in row.index:
            continue
        value = row[column]
        try:
            missing = bool(pd.isna(value))
        except (TypeError, ValueError):
            missing = False
        if not missing:
            return _json_value(value)
    return None


def _selected(row: pd.Series, predicate: Any) -> dict[str, Any]:
    return {
        str(column): _json_value(value)
        for column, value in row.items()
        if predicate(str(column))
    }


def _decode_json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return _json_value(value)


def _nearest_equal_level(
    visible: pd.DataFrame,
    *,
    price: float,
    side: str,
) -> float | None:
    suffix = "_high_equal_cluster_level" if side == "above" else "_low_equal_cluster_level"
    values: list[float] = []
    for column in visible.columns:
        if not str(column).endswith(suffix):
            continue
        numeric = pd.to_numeric(visible[column], errors="coerce").dropna()
        values.extend(float(value) for value in numeric.unique())
    if side == "above":
        eligible = [value for value in values if value > price]
    else:
        eligible = [value for value in values if value < price]
    if not eligible:
        return None
    return min(eligible, key=lambda value: abs(value - price))


def _nearest_active_swing(
    row: pd.Series,
    *,
    price: float,
    kind: str,
) -> float | None:
    columns = (
        f"active_internal_swing_{kind}",
        f"active_external_swing_{kind}",
    )
    values = [
        float(value)
        for column in columns
        if (value := _first_value(row, (column,))) is not None
    ]
    if kind == "high":
        directional = [value for value in values if value >= price]
    else:
        directional = [value for value in values if value <= price]
    candidates = directional or values
    return min(candidates, key=lambda value: abs(value - price)) if candidates else None


def _confluence_snapshot(
    visible: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    as_of: pd.Timestamp,
) -> dict[str, Any]:
    zones = build_confluence_zones(visible, config, as_of=as_of)
    records = [
        {str(key): _json_value(value) for key, value in row.items()}
        for row in zones.head(10).to_dict(orient="records")
    ]
    strongest_support = next(
        (record for record in records if record.get("zone_side") == "support"),
        None,
    )
    strongest_resistance = next(
        (record for record in records if record.get("zone_side") == "resistance"),
        None,
    )
    return {
        "important_zone": records[0] if records else None,
        "strongest_support": strongest_support,
        "strongest_resistance": strongest_resistance,
        "zones": records,
    }


def _status(
    *,
    visible: pd.DataFrame,
    data_quality: Mapping[str, Any],
    freshness: Mapping[str, Any],
) -> tuple[str, str, list[str]]:
    quality_status = str(
        data_quality.get("analysis_status", data_quality.get("status", "pass"))
    ).strip().lower()
    quality_reasons = [str(reason) for reason in data_quality.get("reasons", [])]
    failure_code = str(data_quality.get("failure_code", "")).strip().lower()
    freshness_status = str(freshness.get("status", "fresh")).strip().lower()
    freshness_reason = str(freshness.get("reason", "")).strip().lower()
    stale = (
        freshness.get("fresh") is False
        or bool(freshness.get("stale", False))
        or freshness_status == "stale"
        or freshness_reason == "latest_bar_is_stale"
    )

    if visible.empty or failure_code == "projectx_data_unavailable":
        reasons = quality_reasons or ["No completed ProjectX bars are available at as_of."]
        return "no_analysis", STATUS_PROJECTX_UNAVAILABLE, reasons
    if stale or failure_code == "stale_market_data":
        reasons = quality_reasons or ["The latest completed market bar is stale."]
        return "no_analysis", STATUS_STALE, reasons

    coverage = data_quality.get("session_coverage", {})
    incomplete_coverage = isinstance(coverage, Mapping) and not bool(
        coverage.get("all_due_covered", True)
    )
    if quality_status == "degraded" or incomplete_coverage:
        reasons = quality_reasons or ["Required historical/session coverage is incomplete."]
        return "degraded", STATUS_DEGRADED_HISTORY, reasons
    if quality_status in {"no_analysis", "failed", "error"}:
        reasons = quality_reasons or ["Market-data quality validation failed."]
        return "no_analysis", STATUS_DATA_QUALITY_FAILURE, reasons
    return "ready", STATUS_READY, quality_reasons


def _empty_sections() -> dict[str, Any]:
    return {
        "sessions": {},
        "timeframes": {},
        "bias": {},
        "levels": {name: None for name in LEVEL_COLUMNS} | {
            "nearest_equal_high": None,
            "nearest_equal_low": None,
            "important_support_resistance_zone": None,
        },
        "swings": {},
        "liquidity": {},
        "dealing_ranges": {},
        "pd_arrays": {},
        "fvgs": {},
        "structure": {},
        "displacement": {},
        "volume": {},
        "signal_to_noise": {},
        "support_resistance": {
            "important_zone": None,
            "strongest_support": None,
            "strongest_resistance": None,
            "zones": [],
        },
        "draw_on_liquidity": {
            "direction": "neutral",
            "primary": None,
            "alternate": None,
            "ranked_candidates": [],
        },
        "scores": {"long": {}, "short": {}, "preferred_direction": "neutral"},
        "trade_candidates": {"long": False, "short": False, "any": False},
    }


def build_market_state(
    dataframe: pd.DataFrame | None,
    *,
    as_of: Any,
    symbol: str,
    contract: str | None,
    strategy_config: Mapping[str, Any] | None = None,
    data_quality: Mapping[str, Any] | None = None,
    freshness: Mapping[str, Any] | None = None,
    source_snapshots: Iterable[str] | None = None,
    generated_at: Any | None = None,
    news_event_risk: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one JSON-safe market-state snapshot from completed visible bars."""
    cutoff = normalize_as_of(as_of)
    generated = normalize_as_of(generated_at if generated_at is not None else cutoff)
    config = dict(strategy_config or {})
    quality = dict(data_quality or {})
    freshness_state = dict(freshness or {})

    if dataframe is None or dataframe.empty:
        visible = pd.DataFrame()
    else:
        visible = filter_as_of(dataframe, as_of=cutoff)

    if visible.empty:
        freshness_state.setdefault("status", "unavailable")
    else:
        latest_available = pd.Timestamp(visibility_times(visible).iloc[-1])
        freshness_state.setdefault(
            "latest_completed_bar_available_at",
            latest_available.tz_convert("UTC").isoformat(),
        )
        freshness_state.setdefault(
            "latest_bar_age_seconds",
            max(0.0, float((cutoff - latest_available).total_seconds())),
        )
        freshness_state.setdefault("status", "not_evaluated")

    status_code, status_message, reasons = _status(
        visible=visible,
        data_quality=quality,
        freshness=freshness_state,
    )
    state: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated.isoformat(),
        "as_of": cutoff.isoformat(),
        "status": {
            "code": status_code,
            "message": status_message,
            "reasons": reasons,
        },
        "instrument": {
            "symbol": symbol,
            "contract": contract,
            "source": None,
            "latest_price": None,
            "latest_bar_timestamp": None,
            "latest_bar_available_at": None,
        },
        "data_quality": {
            "analysis_status": quality.get("analysis_status", quality.get("status")),
            "reasons": _json_value(quality.get("reasons", [])),
            "freshness": _json_value(freshness_state),
            "session_coverage": _json_value(quality.get("session_coverage")),
            "details": _json_value(quality),
        },
        "source_snapshots": sorted(str(path) for path in (source_snapshots or [])),
        "news_event_risk": _json_value(
            news_event_risk
            or {"status": "unavailable", "source": "manual", "events": []}
        ),
        **_empty_sections(),
    }

    if visible.empty:
        return state

    row = visible.iloc[-1]
    available_at = visibility_times(visible).iloc[-1]
    price = float(row["close"])
    state["instrument"] = {
        "symbol": symbol,
        "contract": contract,
        "source": _first_value(row, ("source",)),
        "latest_price": price,
        "latest_bar_timestamp": _json_value(pd.Timestamp(row["timestamp"])),
        "latest_bar_available_at": _json_value(pd.Timestamp(available_at)),
    }

    confluence = _confluence_snapshot(visible, config, as_of=cutoff)
    levels = {
        name: _first_value(row, columns)
        for name, columns in LEVEL_COLUMNS.items()
    }
    levels["nearest_important_swing_high"] = _nearest_active_swing(
        row, price=price, kind="high"
    )
    levels["nearest_important_swing_low"] = _nearest_active_swing(
        row, price=price, kind="low"
    )
    levels["nearest_equal_high"] = _nearest_equal_level(
        visible, price=price, side="above"
    )
    levels["nearest_equal_low"] = _nearest_equal_level(
        visible, price=price, side="below"
    )
    important_zone = confluence["important_zone"]
    levels["important_support_resistance_zone"] = (
        important_zone.get("zone_midpoint") if important_zone else None
    )
    state["levels"] = levels
    state["support_resistance"] = confluence

    state["sessions"] = _selected(
        row,
        lambda column: column in {
            "timestamp_et", "session_date", "is_rth", "is_premarket",
            "is_overnight", "is_london", "is_asia", "strategy_entry_window",
        } or column.startswith("developing_"),
    )
    state["timeframes"] = {
        timeframe: {
            "bias": _first_value(row, (f"bias_{timeframe}",)),
            "snr": _first_value(row, (f"snr_{timeframe}",)),
            "volume": _first_value(row, (f"volume_{timeframe}",)),
        }
        for timeframe in ("1m", "5m", "15m", "30m", "1h", "4h", "1d")
    }
    state["timeframes"]["1m"].update(
        {
            "timestamp": state["instrument"]["latest_bar_timestamp"],
            "available_at": state["instrument"]["latest_bar_available_at"],
            "bar_complete": (
                bool(_first_value(row, ("bar_complete",)))
                if _first_value(row, ("bar_complete",)) is not None
                else True
            ),
            "open": _first_value(row, ("open",)),
            "high": _first_value(row, ("high",)),
            "low": _first_value(row, ("low",)),
            "close": price,
        }
    )
    state["bias"] = _selected(
        row,
        lambda column: column.startswith(("htf_", "macro_", "intraday_", "higher_timeframe_")),
    )
    state["swings"] = _selected(row, lambda column: "swing" in column)
    state["liquidity"] = _selected(
        row,
        lambda column: "liquidity" in column or "sweep" in column,
    )
    state["dealing_ranges"] = _selected(
        row,
        lambda column: column.startswith(("internal_dealing_", "external_dealing_")),
    )
    state["pd_arrays"] = _selected(
        row,
        lambda column: "pd_array" in column or "ifvg" in column,
    )
    state["fvgs"] = _selected(row, lambda column: "fvg" in column)
    state["structure"] = _selected(
        row,
        lambda column: (
            "structure" in column
            or column.endswith(("_bos", "_mss", "_choch"))
            or "entry_valid" in column
            or "reversal_sequence" in column
            or "continuation_sequence" in column
            or "core_sequence" in column
            or "thesis_invalidated" in column
        ),
    )
    state["displacement"] = _selected(row, lambda column: "displacement" in column)
    state["volume"] = _selected(
        row,
        lambda column: column == "volume" or column.startswith(("volume_", "rvol_")),
    )
    state["signal_to_noise"] = _selected(
        row,
        lambda column: column.startswith(("snr_", "efficiency_")),
    )

    primary = None
    if _first_value(row, ("dol_primary_target_type",)) is not None:
        primary = {
            "direction": _first_value(row, ("dol_primary_direction",)),
            "target_type": _first_value(row, ("dol_primary_target_type",)),
            "target_category": _first_value(row, ("dol_primary_target_category",)),
            "price": _first_value(row, ("dol_primary_target_price",)),
            "distance_points": _first_value(row, ("dol_primary_distance_points",)),
            "confidence": _first_value(row, ("dol_primary_confidence",)),
            "components": _decode_json(row.get("dol_primary_components"), {}),
        }
    alternate = None
    if _first_value(row, ("dol_alternate_target_type",)) is not None:
        alternate = {
            "direction": _first_value(row, ("dol_alternate_direction",)),
            "target_type": _first_value(row, ("dol_alternate_target_type",)),
            "target_category": _first_value(row, ("dol_alternate_target_category",)),
            "price": _first_value(row, ("dol_alternate_target_price",)),
            "distance_points": _first_value(row, ("dol_alternate_distance_points",)),
            "confidence": _first_value(row, ("dol_alternate_confidence",)),
            "components": _decode_json(row.get("dol_alternate_components"), {}),
        }
    state["draw_on_liquidity"] = {
        "direction": _first_value(row, ("dol_direction",)) or "neutral",
        "primary": primary,
        "alternate": alternate,
        "ranked_candidates": _decode_json(row.get("dol_ranked_candidates"), []),
    }

    def score(direction: str) -> dict[str, Any]:
        return {
            "raw_score": _first_value(row, (f"{direction}_raw_score",)),
            "band": _first_value(row, (f"{direction}_score_band",)),
            "positive_points": _first_value(row, (f"{direction}_positive_points",)),
            "penalty_points": _first_value(row, (f"{direction}_penalty_points",)),
            "disabled": _first_value(row, (f"{direction}_disabled",)),
            "disable_reason": _first_value(row, (f"{direction}_disable_reason",)),
            "components": _selected(
                row,
                lambda column: column.startswith(f"{direction}_score_")
                and column != f"{direction}_score_band",
            ),
        }

    state["scores"] = {
        "long": score("long"),
        "short": score("short"),
        "score_edge": _first_value(row, ("score_edge",)),
        "preferred_direction": _first_value(row, ("preferred_score_direction",))
        or "neutral",
    }
    state["trade_candidates"] = {
        "long": bool(_first_value(row, ("long_candidate",)) or False),
        "short": bool(_first_value(row, ("short_candidate",)) or False),
        "any": bool(_first_value(row, ("candidate_any",)) or False),
    }
    return state


def save_market_state_snapshot(
    state: Mapping[str, Any],
    output_directory: str | Path,
    *,
    timezone: str = "America/New_York",
) -> MarketStatePaths:
    """Persist an immutable timestamped snapshot and refresh ``latest.json``."""
    if "as_of" not in state or "schema_version" not in state:
        raise MarketStateError("State must include as_of and schema_version.")
    as_of = normalize_as_of(state["as_of"]).tz_convert(timezone)
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)

    stem = f"{as_of:%Y-%m-%d_%H%M}_market_state"
    snapshot = directory / f"{stem}.json"
    suffix = 2
    while snapshot.exists():
        snapshot = directory / f"{stem}_v{suffix}.json"
        suffix += 1

    payload = json.dumps(_json_value(dict(state)), indent=2, sort_keys=True) + "\n"

    def atomic_write(path: Path) -> None:
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(path)

    atomic_write(snapshot)
    latest = directory / "latest.json"
    atomic_write(latest)
    return MarketStatePaths(snapshot=snapshot, latest=latest)
