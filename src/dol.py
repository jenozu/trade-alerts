from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from liquidity_registry import build_liquidity_registry


REQUIRED_COLUMNS = {"timestamp", "close"}


class DOLError(RuntimeError):
    """Raised when Draw on Liquidity cannot be calculated safely."""


@dataclass(frozen=True)
class DOLSettings:
    minimum_target_distance_points: float
    decision_threshold: float
    minimum_score_edge: float
    target_weight: float
    htf_bias_weight: float
    opposing_sweep_weight: float
    premium_discount_weight: float
    fvg_context_weight: float
    structure_context_weight: float
    displacement_weight: float

    @property
    def maximum_directional_score(self) -> float:
        return (
            self.target_weight
            + self.htf_bias_weight
            + self.opposing_sweep_weight
            + self.premium_discount_weight
            + self.fvg_context_weight
            + self.structure_context_weight
            + self.displacement_weight
        )


@dataclass(frozen=True)
class DOLTarget:
    side: str
    source: str
    category: str
    price: float
    distance_points: float
    importance_score: float = 0.0
    state: str = "untouched"
    timeframe: str | None = None
    pool_id: str | None = None
    obstacle_count: int = 0
    direction_score: float = 0.0
    confidence: float = 0.0
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class DOLSummary:
    rows: int
    bullish: int
    bearish: int
    neutral: int
    bullish_targets_available: int
    bearish_targets_available: int


_UPSIDE_TARGET_COLUMNS: tuple[tuple[str, str], ...] = (
    ("active_external_swing_high", "external_swings"),
    ("pdh", "pdh_pdl"),
    ("pmh", "pmh_pml"),
    ("ash", "asia_high_low"),
    ("onh", "onh_onl"),
    ("loh", "loh_lol"),
    ("week_high", "weekly_high_low"),
    ("external_swing_high_equal_cluster_level", "equal_highs_lows"),
    ("internal_swing_high_equal_cluster_level", "equal_highs_lows"),
    ("nearest_htf_fvg_above", "fair_value_gaps"),
)

_DOWNSIDE_TARGET_COLUMNS: tuple[tuple[str, str], ...] = (
    ("active_external_swing_low", "external_swings"),
    ("pdl", "pdh_pdl"),
    ("pml", "pmh_pml"),
    ("asl", "asia_high_low"),
    ("onl", "onh_onl"),
    ("lol", "loh_lol"),
    ("week_low", "weekly_high_low"),
    ("external_swing_low_equal_cluster_level", "equal_highs_lows"),
    ("internal_swing_low_equal_cluster_level", "equal_highs_lows"),
    ("nearest_htf_fvg_below", "fair_value_gaps"),
)


_SOURCE_CATEGORIES = {
    "pdh": "pdh_pdl",
    "pdl": "pdh_pdl",
    "pmh": "pmh_pml",
    "pml": "pmh_pml",
    "onh": "onh_onl",
    "onl": "onh_onl",
    "loh": "loh_lol",
    "lol": "loh_lol",
    "ash": "asia_high_low",
    "asl": "asia_high_low",
    "week_high": "weekly_high_low",
    "week_low": "weekly_high_low",
    "external_swing_high": "external_swings",
    "external_swing_low": "external_swings",
    "internal_equal_high": "equal_highs_lows",
    "internal_equal_low": "equal_highs_lows",
    "external_equal_high": "equal_highs_lows",
    "external_equal_low": "equal_highs_lows",
    "nearest_htf_fvg_above": "fair_value_gaps",
    "nearest_htf_fvg_below": "fair_value_gaps",
}

# -----------------------------------------------------------------------------
# Validation / settings
# -----------------------------------------------------------------------------


def _validate_dataframe(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise DOLError(f"Missing required columns for DOL: {sorted(missing)}")
    if df.empty:
        raise DOLError("Cannot calculate DOL on an empty dataframe.")
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        raise DOLError("'timestamp' must be a pandas datetime column.")
    if getattr(df["timestamp"].dt, "tz", None) is None:
        raise DOLError("'timestamp' must be timezone-aware.")


def _dol_config(config: Mapping[str, Any]) -> Mapping[str, Any]:
    section = config.get("draw_on_liquidity", {})
    if section is None:
        section = {}
    if not isinstance(section, Mapping):
        raise DOLError("draw_on_liquidity configuration must be a mapping.")
    return section


def build_dol_settings(config: Mapping[str, Any]) -> DOLSettings:
    section = _dol_config(config)
    room = config.get("room_to_target", {})
    if not isinstance(room, Mapping):
        room = {}

    weights = section.get("evidence_weights", {})
    if weights is None:
        weights = {}
    if not isinstance(weights, Mapping):
        raise DOLError("draw_on_liquidity.evidence_weights must be a mapping.")

    minimum_target_distance = float(
        section.get(
            "minimum_target_distance_points",
            room.get("minimum_points", 25.0),
        )
    )
    decision_threshold = float(section.get("decision_threshold", 3.0))
    minimum_score_edge = float(section.get("minimum_score_edge", 1.0))

    settings = DOLSettings(
        minimum_target_distance_points=minimum_target_distance,
        decision_threshold=decision_threshold,
        minimum_score_edge=minimum_score_edge,
        target_weight=float(weights.get("target_available", 1.0)),
        htf_bias_weight=float(weights.get("higher_timeframe_bias", 2.0)),
        opposing_sweep_weight=float(weights.get("opposing_liquidity_sweep", 1.5)),
        premium_discount_weight=float(weights.get("premium_discount", 1.0)),
        fvg_context_weight=float(weights.get("fvg_context", 0.5)),
        structure_context_weight=float(weights.get("structure_context", 1.0)),
        displacement_weight=float(weights.get("displacement", 1.0)),
    )

    if settings.minimum_target_distance_points < 0:
        raise DOLError("minimum_target_distance_points cannot be negative.")
    if settings.decision_threshold < 0:
        raise DOLError("decision_threshold cannot be negative.")
    if settings.minimum_score_edge < 0:
        raise DOLError("minimum_score_edge cannot be negative.")
    directional_weights = (
        settings.target_weight,
        settings.htf_bias_weight,
        settings.opposing_sweep_weight,
        settings.premium_discount_weight,
        settings.fvg_context_weight,
        settings.structure_context_weight,
        settings.displacement_weight,
    )
    if any(weight < 0 for weight in directional_weights):
        raise DOLError("DOL evidence weights cannot be negative.")
    if settings.maximum_directional_score <= 0:
        raise DOLError("DOL evidence weights must sum to a positive value.")

    return settings


def configured_candidate_sources(config: Mapping[str, Any]) -> list[str]:
    section = _dol_config(config)
    raw = section.get(
        "candidate_sources",
        [
            "external_swings",
            "pdh_pdl",
            "pmh_pml",
            "asia_high_low",
            "onh_onl",
            "loh_lol",
            "weekly_high_low",
            "equal_highs_lows",
            "fair_value_gaps",
        ],
    )
    if isinstance(raw, str):
        raw = [raw]
    result = [str(value).strip() for value in raw if str(value).strip()]
    return result


# -----------------------------------------------------------------------------
# Target resolution
# -----------------------------------------------------------------------------


def _numeric(row: pd.Series, column: str) -> float | None:
    if column not in row.index:
        return None
    value = row[column]
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _boolean(row: pd.Series, column: str) -> bool:
    if column not in row.index:
        return False
    value = row[column]
    if pd.isna(value):
        return False
    return bool(value)


def _string(row: pd.Series, column: str) -> str:
    if column not in row.index:
        return ""
    value = row[column]
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def _resolve_target_source(
    row: pd.Series,
    *,
    target_price: float,
    side: str,
    allowed_categories: list[str],
    tolerance: float,
) -> tuple[str, str] | None:
    candidates = _UPSIDE_TARGET_COLUMNS if side == "above" else _DOWNSIDE_TARGET_COLUMNS
    category_order = {name: index for index, name in enumerate(allowed_categories)}

    matches: list[tuple[int, str, str]] = []
    for column, category in candidates:
        if category not in category_order:
            continue
        value = _numeric(row, column)
        if value is None:
            continue
        if np.isclose(value, target_price, atol=tolerance, rtol=0.0):
            matches.append((category_order[category], column, category))

    if not matches:
        return None

    matches.sort(key=lambda item: item[0])
    _, source, category = matches[0]
    return source, category


def select_unswept_target(
    row: pd.Series,
    *,
    side: str,
    config: Mapping[str, Any],
    settings: DOLSettings | None = None,
) -> DOLTarget | None:
    """Resolve the nearest already-tracked unswept *external* target.

    The liquidity module is responsible for causally tracking which level is
    unswept. DOL deliberately consumes those existing outputs instead of
    reconstructing sweep state from future bars.

    If the nearest unswept level is an internal swing or another source that is
    not configured for DOL, this function returns ``None`` rather than silently
    skipping over it and guessing a farther target whose sweep state is unknown.
    """
    if side not in {"above", "below"}:
        raise ValueError("side must be 'above' or 'below'.")

    if settings is None:
        settings = build_dol_settings(config)

    allowed = configured_candidate_sources(config)
    market = config.get("market", {})
    tick_size = 0.25
    if isinstance(market, Mapping):
        tick_size = float(market.get("tick_size", 0.25))
    tolerance = max(1e-9, tick_size / 10.0)

    if side == "above":
        price_column = "nearest_unswept_liquidity_above"
        distance_column = "distance_to_unswept_liquidity_above"
    else:
        price_column = "nearest_unswept_liquidity_below"
        distance_column = "distance_to_unswept_liquidity_below"

    target_price = _numeric(row, price_column)
    distance = _numeric(row, distance_column)

    if target_price is None or distance is None:
        return None
    if distance < settings.minimum_target_distance_points:
        return None

    resolved = _resolve_target_source(
        row,
        target_price=target_price,
        side=side,
        allowed_categories=allowed,
        tolerance=tolerance,
    )
    if resolved is None:
        return None

    source, category = resolved
    return DOLTarget(
        side=side,
        source=source,
        category=category,
        price=float(target_price),
        distance_points=float(distance),
    )


def _as_utc(value: Any) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise DOLError("DOL lifecycle timestamps must be timezone-aware.")
    return timestamp.tz_convert("UTC")


def _decision_time(row: pd.Series) -> pd.Timestamp:
    available_at = row.get("available_at")
    if pd.notna(available_at):
        return _as_utc(available_at)
    return _as_utc(row["timestamp"]) + pd.Timedelta(minutes=1)


def _registry_candidate_snapshots(
    dataframe: pd.DataFrame,
    config: Mapping[str, Any],
    settings: DOLSettings,
) -> list[list[DOLTarget]]:
    """Materialize eligible liquidity pools at each completed-bar decision time."""
    snapshots: list[list[DOLTarget]] = [[] for _ in range(len(dataframe))]
    required = {"timestamp", "high", "low", "close"}
    if not required.issubset(dataframe.columns):
        return snapshots

    registry = build_liquidity_registry(dataframe, config)
    if registry.empty:
        return snapshots

    allowed = set(configured_candidate_sources(config))
    events: list[tuple[pd.Timestamp, int, str, str, dict[str, Any]]] = []
    for _, pool in registry.iterrows():
        payload = pool.to_dict()
        pool_id = str(payload["pool_id"])
        events.append((_as_utc(payload["created_at"]), 0, pool_id, "add", payload))

        approached_at = payload.get("approached_at")
        if pd.notna(approached_at):
            events.append((_as_utc(approached_at), 1, pool_id, "approach", payload))

        terminal_times = [
            _as_utc(payload[column])
            for column in ("swept_at", "broken_at", "reclaimed_at", "invalidated_at")
            if pd.notna(payload.get(column))
        ]
        if terminal_times:
            events.append((min(terminal_times), 2, pool_id, "remove", payload))

    events.sort(key=lambda event: (event[0], event[1], event[2]))
    active: dict[str, dict[str, Any]] = {}
    event_index = 0

    for row_index, row in dataframe.iterrows():
        as_of = _decision_time(row)
        while event_index < len(events) and events[event_index][0] <= as_of:
            _, _, pool_id, event_type, payload = events[event_index]
            if event_type == "add":
                active[pool_id] = {**payload, "state_as_of": "untouched"}
            elif event_type == "approach" and pool_id in active:
                active[pool_id]["state_as_of"] = "approached"
            elif event_type == "remove":
                active.pop(pool_id, None)
            event_index += 1

        close = float(row["close"])
        candidates: list[DOLTarget] = []
        for pool_id, pool in active.items():
            source = str(pool["source"])
            category = _SOURCE_CATEGORIES.get(source)
            if category is None or category not in allowed:
                continue

            price = float(pool["level"])
            pool_side = str(pool["side"])
            if pool_side == "buy" and price > close:
                side = "above"
                distance = price - close
            elif pool_side == "sell" and price < close:
                side = "below"
                distance = close - price
            else:
                continue

            if distance < settings.minimum_target_distance_points:
                continue

            candidates.append(
                DOLTarget(
                    side=side,
                    source=source,
                    category=category,
                    price=price,
                    distance_points=float(distance),
                    importance_score=float(pool.get("importance_score", 0.0)),
                    state=str(pool.get("state_as_of", "untouched")),
                    timeframe=str(pool.get("timeframe") or "") or None,
                    pool_id=pool_id,
                )
            )
        snapshots[row_index] = candidates

    return snapshots


def _fvg_candidates(
    row: pd.Series,
    config: Mapping[str, Any],
    settings: DOLSettings,
) -> list[DOLTarget]:
    if "fair_value_gaps" not in configured_candidate_sources(config):
        return []

    importance = float(
        config.get("liquidity", {})
        .get("registry", {})
        .get("importance", {})
        .get("htf_fvg", 0.0)
    )
    candidates: list[DOLTarget] = []
    for side, price_column, distance_column in (
        (
            "above",
            "nearest_htf_fvg_above",
            "distance_to_nearest_htf_fvg_above",
        ),
        (
            "below",
            "nearest_htf_fvg_below",
            "distance_to_nearest_htf_fvg_below",
        ),
    ):
        price = _numeric(row, price_column)
        distance = _numeric(row, distance_column)
        if price is None or distance is None:
            continue
        if distance < settings.minimum_target_distance_points:
            continue
        candidates.append(
            DOLTarget(
                side=side,
                source=price_column,
                category="fair_value_gaps",
                price=price,
                distance_points=distance,
                importance_score=importance,
                state="active",
                timeframe="htf",
            )
        )
    return candidates


def _rank_targets(targets: list[DOLTarget]) -> list[DOLTarget]:
    """Rank the closest intact draw first; importance resolves price ties."""
    ordered = sorted(
        targets,
        key=lambda target: (
            target.distance_points,
            -target.importance_score,
            target.source,
            target.pool_id or "",
        ),
    )
    return [replace(target, obstacle_count=index) for index, target in enumerate(ordered)]


def _respect_nearest_liquidity_obstacle(
    row: pd.Series,
    targets: list[DOLTarget],
    config: Mapping[str, Any],
) -> list[DOLTarget]:
    """Do not promote a farther DOL through an ineligible nearer pool."""
    close = float(row["close"])
    allowed = configured_candidate_sources(config)
    market = config.get("market", {})
    tick_size = float(market.get("tick_size", 0.25)) if isinstance(market, Mapping) else 0.25
    tolerance = max(1e-9, tick_size / 10.0)
    filtered = list(targets)

    for side, column in (
        ("above", "nearest_unswept_liquidity_above"),
        ("below", "nearest_unswept_liquidity_below"),
    ):
        nearest_price = _numeric(row, column)
        if nearest_price is None:
            continue
        resolved = _resolve_target_source(
            row,
            target_price=nearest_price,
            side=side,
            allowed_categories=allowed,
            tolerance=tolerance,
        )
        if resolved is not None:
            continue

        nearest_distance = abs(nearest_price - close)
        filtered = [
            target
            for target in filtered
            if target.side != side
            or target.distance_points + tolerance < nearest_distance
        ]

    return filtered


# -----------------------------------------------------------------------------
# Directional evidence
# -----------------------------------------------------------------------------


def _premium_discount_location(row: pd.Series) -> str:
    value = _string(row, "external_premium_discount")
    if value:
        return value
    return _string(row, "internal_premium_discount")


def _directional_score(
    row: pd.Series,
    *,
    direction: str,
    target: DOLTarget | None,
    settings: DOLSettings,
) -> tuple[float, list[str]]:
    if direction not in {"bullish", "bearish"}:
        raise ValueError("direction must be 'bullish' or 'bearish'.")

    score = 0.0
    reasons: list[str] = []

    if target is not None:
        score += settings.target_weight
        reasons.append(f"target:{target.source}")

    htf_bias = (
        _string(row, "htf_bias")
        or _string(row, "higher_timeframe_bias")
        or _string(row, "macro_bias")
    )
    if htf_bias == direction:
        score += settings.htf_bias_weight
        reasons.append("htf_bias")

    if direction == "bullish":
        if _boolean(row, "recent_sell_side_sweep"):
            score += settings.opposing_sweep_weight
            reasons.append("sell_side_sweep")
        if _premium_discount_location(row) == "discount":
            score += settings.premium_discount_weight
            reasons.append("discount")
        if (
            _boolean(row, "bullish_pd_array_respected_recent")
            or _boolean(row, "bullish_ifvg_respected_recent")
        ):
            score += settings.fvg_context_weight
            reasons.append("bullish_pd_array_respect")
        elif _boolean(row, "bullish_fvg_retest_hold"):
            score += settings.fvg_context_weight
            reasons.append("bullish_fvg_retest")

        structure_aligned = (
            _boolean(row, "active_internal_swing_high_weak_liquidity")
            or _boolean(row, "active_internal_swing_low_protected_strong")
        )
        if structure_aligned:
            score += settings.structure_context_weight
            reasons.append("bullish_protected_weak_structure")
    else:
        if _boolean(row, "recent_buy_side_sweep"):
            score += settings.opposing_sweep_weight
            reasons.append("buy_side_sweep")
        if _premium_discount_location(row) == "premium":
            score += settings.premium_discount_weight
            reasons.append("premium")
        if (
            _boolean(row, "bearish_pd_array_respected_recent")
            or _boolean(row, "bearish_ifvg_respected_recent")
        ):
            score += settings.fvg_context_weight
            reasons.append("bearish_pd_array_respect")
        elif _boolean(row, "bearish_fvg_retest_hold"):
            score += settings.fvg_context_weight
            reasons.append("bearish_fvg_retest")

        structure_aligned = (
            _boolean(row, "active_internal_swing_low_weak_liquidity")
            or _boolean(row, "active_internal_swing_high_protected_strong")
        )
        if structure_aligned:
            score += settings.structure_context_weight
            reasons.append("bearish_protected_weak_structure")

    displacement_direction = _string(row, "displacement_direction")
    displacement_category = _string(row, "displacement_category")
    if (
        displacement_direction == direction
        and displacement_category in {"moderate", "strong"}
    ):
        score += settings.displacement_weight
        reasons.append(f"{direction}_displacement")

    return float(score), reasons


def _direction_confidence(
    *,
    score: float,
    opposing_score: float,
    settings: DOLSettings,
) -> float:
    maximum = settings.maximum_directional_score
    margin = max(0.0, score - opposing_score)
    return float(
        np.clip(
            0.5 * (score / maximum) + 0.5 * (margin / maximum),
            0.0,
            1.0,
        )
    )


def _target_record(target: DOLTarget) -> dict[str, Any]:
    record = asdict(target)
    record["reasons"] = list(target.reasons)
    return record


def calculate_dol_row(
    row: pd.Series,
    config: Mapping[str, Any],
    *,
    settings: DOLSettings | None = None,
    candidates: list[DOLTarget] | None = None,
) -> dict[str, Any]:
    if settings is None:
        settings = build_dol_settings(config)

    if candidates is None:
        candidates = []
        for side in ("above", "below"):
            target = select_unswept_target(
                row,
                side=side,
                config=config,
                settings=settings,
            )
            if target is not None:
                candidates.append(target)
        candidates.extend(_fvg_candidates(row, config, settings))

    bullish_targets = _rank_targets(
        [target for target in candidates if target.side == "above"]
    )
    bearish_targets = _rank_targets(
        [target for target in candidates if target.side == "below"]
    )
    bullish_target = bullish_targets[0] if bullish_targets else None
    bearish_target = bearish_targets[0] if bearish_targets else None

    bullish_score, bullish_reasons = _directional_score(
        row,
        direction="bullish",
        target=bullish_target,
        settings=settings,
    )
    bearish_score, bearish_reasons = _directional_score(
        row,
        direction="bearish",
        target=bearish_target,
        settings=settings,
    )

    bullish_eligible = bullish_target is not None
    bearish_eligible = bearish_target is not None
    edge = bullish_score - bearish_score

    direction = "neutral"
    chosen_target: DOLTarget | None = None
    chosen_reasons: list[str] = []

    if (
        bullish_eligible
        and bullish_score >= settings.decision_threshold
        and edge >= settings.minimum_score_edge
    ):
        direction = "bullish"
        chosen_target = bullish_target
        chosen_reasons = bullish_reasons
    elif (
        bearish_eligible
        and bearish_score >= settings.decision_threshold
        and -edge >= settings.minimum_score_edge
    ):
        direction = "bearish"
        chosen_target = bearish_target
        chosen_reasons = bearish_reasons

    bullish_confidence = _direction_confidence(
        score=bullish_score,
        opposing_score=bearish_score,
        settings=settings,
    )
    bearish_confidence = _direction_confidence(
        score=bearish_score,
        opposing_score=bullish_score,
        settings=settings,
    )

    bullish_targets = [
        replace(
            target,
            direction_score=bullish_score,
            confidence=bullish_confidence,
            reasons=tuple(bullish_reasons),
        )
        for target in bullish_targets
    ]
    bearish_targets = [
        replace(
            target,
            direction_score=bearish_score,
            confidence=bearish_confidence,
            reasons=tuple(bearish_reasons),
        )
        for target in bearish_targets
    ]

    primary: DOLTarget | None = None
    alternate: DOLTarget | None = None
    if direction == "bullish":
        primary = bullish_targets[0]
        if bearish_targets:
            alternate = bearish_targets[0]
        elif len(bullish_targets) > 1:
            alternate = bullish_targets[1]
    elif direction == "bearish":
        primary = bearish_targets[0]
        if bullish_targets:
            alternate = bullish_targets[0]
        elif len(bearish_targets) > 1:
            alternate = bearish_targets[1]

    confidence = primary.confidence if primary is not None else 0.0
    chosen_target = primary
    ranked_targets = (
        bullish_targets + bearish_targets
        if direction == "bullish"
        else bearish_targets + bullish_targets
    )
    if direction == "neutral":
        ranked_targets = []

    return {
        "dol_direction": direction,
        "draw_on_liquidity_direction": direction,
        "dol_target_type": chosen_target.source if chosen_target else None,
        "dol_target_category": chosen_target.category if chosen_target else None,
        "dol_target_price": chosen_target.price if chosen_target else np.nan,
        "dol_distance_points": chosen_target.distance_points if chosen_target else np.nan,
        "dol_confidence": confidence,
        "dol_bullish_score": bullish_score,
        "dol_bearish_score": bearish_score,
        "dol_score_edge": edge,
        "dol_bullish_target_type": bullish_target.source if bullish_target else None,
        "dol_bullish_target_price": bullish_target.price if bullish_target else np.nan,
        "dol_bullish_distance_points": (
            bullish_target.distance_points if bullish_target else np.nan
        ),
        "dol_bearish_target_type": bearish_target.source if bearish_target else None,
        "dol_bearish_target_price": bearish_target.price if bearish_target else np.nan,
        "dol_bearish_distance_points": (
            bearish_target.distance_points if bearish_target else np.nan
        ),
        "dol_pd_array_context": (
            _string(row, "pd_array_directional_context") or None
        ),
        "dol_reason": ",".join(chosen_reasons) if chosen_reasons else None,
        "dol_primary_direction": direction if primary else None,
        "dol_primary_target_type": primary.source if primary else None,
        "dol_primary_target_category": primary.category if primary else None,
        "dol_primary_target_price": primary.price if primary else np.nan,
        "dol_primary_distance_points": (
            primary.distance_points if primary else np.nan
        ),
        "dol_primary_confidence": primary.confidence if primary else 0.0,
        "dol_primary_components": (
            json.dumps(_target_record(primary), sort_keys=True)
            if primary
            else None
        ),
        "dol_alternate_direction": (
            "bullish" if alternate and alternate.side == "above" else
            "bearish" if alternate else None
        ),
        "dol_alternate_target_type": alternate.source if alternate else None,
        "dol_alternate_target_category": alternate.category if alternate else None,
        "dol_alternate_target_price": alternate.price if alternate else np.nan,
        "dol_alternate_distance_points": (
            alternate.distance_points if alternate else np.nan
        ),
        "dol_alternate_confidence": alternate.confidence if alternate else 0.0,
        "dol_alternate_components": (
            json.dumps(_target_record(alternate), sort_keys=True)
            if alternate
            else None
        ),
        "dol_ranked_candidates": json.dumps(
            [_target_record(target) for target in ranked_targets],
            sort_keys=True,
        ),
    }


# -----------------------------------------------------------------------------
# Dataframe enrichment / reporting
# -----------------------------------------------------------------------------


def enrich_draw_on_liquidity(
    df: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Add a causal, deterministic Draw on Liquidity context to each bar.

    DOL consumes only columns already available on the current row. The module
    never scans forward. Therefore its causality is inherited from the session,
    swing, liquidity, FVG, and HTF-bias features that feed it.
    """
    _validate_dataframe(df)
    result = df.sort_values("timestamp", kind="stable").copy().reset_index(drop=True)
    section = _dol_config(config)

    output_columns = [
        "dol_direction",
        "draw_on_liquidity_direction",
        "dol_target_type",
        "dol_target_category",
        "dol_target_price",
        "dol_distance_points",
        "dol_confidence",
        "dol_bullish_score",
        "dol_bearish_score",
        "dol_score_edge",
        "dol_bullish_target_type",
        "dol_bullish_target_price",
        "dol_bullish_distance_points",
        "dol_bearish_target_type",
        "dol_bearish_target_price",
        "dol_bearish_distance_points",
        "dol_pd_array_context",
        "dol_reason",
        "dol_primary_direction",
        "dol_primary_target_type",
        "dol_primary_target_category",
        "dol_primary_target_price",
        "dol_primary_distance_points",
        "dol_primary_confidence",
        "dol_primary_components",
        "dol_alternate_direction",
        "dol_alternate_target_type",
        "dol_alternate_target_category",
        "dol_alternate_target_price",
        "dol_alternate_distance_points",
        "dol_alternate_confidence",
        "dol_alternate_components",
        "dol_ranked_candidates",
    ]

    if not bool(section.get("enabled", True)):
        result["dol_direction"] = "neutral"
        result["draw_on_liquidity_direction"] = "neutral"
        for column in output_columns:
            if column in {"dol_direction", "draw_on_liquidity_direction"}:
                continue
            if column in {
                "dol_confidence",
                "dol_bullish_score",
                "dol_bearish_score",
                "dol_score_edge",
                "dol_primary_confidence",
                "dol_alternate_confidence",
            }:
                result[column] = 0.0
            else:
                result[column] = np.nan
        return result

    settings = build_dol_settings(config)
    use_registry = {"high", "low"}.issubset(result.columns)
    registry_snapshots = (
        _registry_candidate_snapshots(result, config, settings)
        if use_registry
        else [None] * len(result)
    )
    records = []
    for row_index, row in result.iterrows():
        candidates = registry_snapshots[row_index]
        if candidates is not None:
            candidates = candidates + _fvg_candidates(row, config, settings)
            candidates = _respect_nearest_liquidity_obstacle(
                row,
                candidates,
                config,
            )
        records.append(
            calculate_dol_row(
                row,
                config,
                settings=settings,
                candidates=candidates,
            )
        )
    feature_frame = pd.DataFrame(records, index=result.index)
    for column in output_columns:
        result[column] = feature_frame[column]
    return result


def dol_summary(df: pd.DataFrame) -> DOLSummary:
    if "dol_direction" not in df.columns:
        raise DOLError("Cannot summarize DOL: dol_direction column is missing.")

    direction = df["dol_direction"].astype("string")
    return DOLSummary(
        rows=int(len(df)),
        bullish=int((direction == "bullish").sum()),
        bearish=int((direction == "bearish").sum()),
        neutral=int((direction == "neutral").sum()),
        bullish_targets_available=int(df.get("dol_bullish_target_price", pd.Series(index=df.index, dtype=float)).notna().sum()),
        bearish_targets_available=int(df.get("dol_bearish_target_price", pd.Series(index=df.index, dtype=float)).notna().sum()),
    )


def save_dol_outputs(
    df: pd.DataFrame,
    output_directory: str | Path,
) -> tuple[Path, Path]:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)

    parquet_path = directory / "nq_1m_dol.parquet"
    summary_path = directory / "dol_distribution.csv"

    df.to_parquet(parquet_path, index=False)

    distribution = (
        df["dol_direction"]
        .value_counts(dropna=False)
        .rename_axis("dol_direction")
        .reset_index(name="bars")
    )
    distribution.to_csv(summary_path, index=False)
    return parquet_path, summary_path
