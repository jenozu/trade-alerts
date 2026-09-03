from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd


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

    @property
    def maximum_directional_score(self) -> float:
        return (
            self.target_weight
            + self.htf_bias_weight
            + self.opposing_sweep_weight
            + self.premium_discount_weight
            + self.fvg_context_weight
        )


@dataclass(frozen=True)
class DOLTarget:
    side: str
    source: str
    category: str
    price: float
    distance_points: float


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
    ("onh", "onh_onl"),
    ("loh", "loh_lol"),
)

_DOWNSIDE_TARGET_COLUMNS: tuple[tuple[str, str], ...] = (
    ("active_external_swing_low", "external_swings"),
    ("pdl", "pdh_pdl"),
    ("pml", "pmh_pml"),
    ("onl", "onh_onl"),
    ("lol", "loh_lol"),
)


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
    )

    if settings.minimum_target_distance_points < 0:
        raise DOLError("minimum_target_distance_points cannot be negative.")
    if settings.decision_threshold < 0:
        raise DOLError("decision_threshold cannot be negative.")
    if settings.minimum_score_edge < 0:
        raise DOLError("minimum_score_edge cannot be negative.")
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
            "onh_onl",
            "loh_lol",
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

    htf_bias = _string(row, "htf_bias") or _string(row, "higher_timeframe_bias")
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

    return float(score), reasons


def calculate_dol_row(
    row: pd.Series,
    config: Mapping[str, Any],
    *,
    settings: DOLSettings | None = None,
) -> dict[str, Any]:
    if settings is None:
        settings = build_dol_settings(config)

    bullish_target = select_unswept_target(
        row,
        side="above",
        config=config,
        settings=settings,
    )
    bearish_target = select_unswept_target(
        row,
        side="below",
        config=config,
        settings=settings,
    )

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

    maximum = settings.maximum_directional_score
    if direction == "bullish":
        winner = bullish_score
        margin = max(0.0, edge)
    elif direction == "bearish":
        winner = bearish_score
        margin = max(0.0, -edge)
    else:
        winner = max(bullish_score, bearish_score)
        margin = abs(edge)

    confidence = float(
        np.clip(
            0.5 * (winner / maximum) + 0.5 * (margin / maximum),
            0.0,
            1.0,
        )
    )
    if direction == "neutral":
        confidence = 0.0

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
            }:
                result[column] = 0.0
            else:
                result[column] = np.nan
        return result

    settings = build_dol_settings(config)
    records = [
        calculate_dol_row(row, config, settings=settings)
        for _, row in result.iterrows()
    ]
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
