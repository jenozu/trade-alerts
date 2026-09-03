from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np
import pandas as pd


class DisplacementError(RuntimeError):
    """Raised when displacement components cannot be computed safely."""


REQUIRED_COLUMNS = {
    "timestamp",
    "open",
    "high",
    "low",
    "close",
}


@dataclass(frozen=True)
class DisplacementComponentSettings:
    atr_period: int
    body_atr_target: float
    range_atr_target: float
    close_extreme_fraction: float
    consecutive_candles_target: int
    break_distance_atr_target: float
    rvol_target: float
    minimum_coverage_fraction: float
    weak_threshold: float
    moderate_threshold: float
    strong_threshold: float
    require_directional_close: bool
    weights: Mapping[str, float]


DEFAULT_WEIGHTS = {
    "body_atr": 20.0,
    "range_atr": 15.0,
    "close_location": 15.0,
    "consecutive": 10.0,
    "structure_break_distance": 15.0,
    "rvol": 10.0,
    "fvg_generation": 10.0,
    "follow_through": 5.0,
}


def _validate(dataframe: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(dataframe.columns)

    if missing:
        raise DisplacementError(
            f"Missing required columns: {sorted(missing)}"
        )

    if dataframe.empty:
        raise DisplacementError(
            "Cannot calculate displacement on an empty dataframe."
        )

    if not pd.api.types.is_datetime64_any_dtype(
        dataframe["timestamp"]
    ):
        raise DisplacementError(
            "'timestamp' must be datetime."
        )

    if getattr(dataframe["timestamp"].dt, "tz", None) is None:
        raise DisplacementError(
            "'timestamp' must be timezone-aware."
        )


def build_component_settings(
    config: Mapping[str, Any],
) -> DisplacementComponentSettings:
    section = config.get("displacement", {})
    model = section.get("component_model", {})
    normalization = model.get("normalization", {})
    categories = model.get("categories", {})
    weights = model.get("weights", DEFAULT_WEIGHTS)

    if not isinstance(weights, Mapping):
        raise DisplacementError(
            "displacement.component_model.weights must be a mapping."
        )

    parsed_weights = {
        name: float(weights.get(name, default))
        for name, default in DEFAULT_WEIGHTS.items()
    }

    if any(weight < 0 for weight in parsed_weights.values()):
        raise DisplacementError(
            "Displacement component weights cannot be negative."
        )

    if sum(parsed_weights.values()) <= 0:
        raise DisplacementError(
            "At least one displacement component weight must be positive."
        )

    settings = DisplacementComponentSettings(
        atr_period=int(section.get("atr_period", 14)),
        body_atr_target=float(
            normalization.get("body_atr_target", 1.20)
        ),
        range_atr_target=float(
            normalization.get("range_atr_target", 1.50)
        ),
        close_extreme_fraction=float(
            section.get("close_extreme_fraction", 0.25)
        ),
        consecutive_candles_target=int(
            normalization.get(
                "consecutive_candles_target",
                3,
            )
        ),
        break_distance_atr_target=float(
            normalization.get(
                "break_distance_atr_target",
                0.50,
            )
        ),
        rvol_target=float(
            normalization.get("rvol_target", 1.50)
        ),
        minimum_coverage_fraction=float(
            model.get("minimum_coverage_fraction", 0.50)
        ),
        weak_threshold=float(
            categories.get("weak", 40.0)
        ),
        moderate_threshold=float(
            categories.get("moderate", 60.0)
        ),
        strong_threshold=float(
            categories.get("strong", 75.0)
        ),
        require_directional_close=bool(
            section.get("require_directional_close", True)
        ),
        weights=parsed_weights,
    )

    if not (
        0
        <= settings.weak_threshold
        <= settings.moderate_threshold
        <= settings.strong_threshold
        <= 100
    ):
        raise DisplacementError(
            "Displacement category thresholds must satisfy "
            "0 <= weak <= moderate <= strong <= 100."
        )

    if not 0 <= settings.minimum_coverage_fraction <= 1:
        raise DisplacementError(
            "minimum_coverage_fraction must be between 0 and 1."
        )

    return settings


def _add_atr(
    dataframe: pd.DataFrame,
    *,
    period: int,
) -> pd.DataFrame:
    result = dataframe.copy()

    if "atr_1m" in result.columns:
        result["displacement_atr"] = pd.to_numeric(
            result["atr_1m"],
            errors="coerce",
        )
        return result

    previous_close = result["close"].shift(1)

    true_range = pd.concat(
        [
            result["high"] - result["low"],
            (result["high"] - previous_close).abs(),
            (result["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    result["displacement_atr"] = true_range.rolling(
        window=period,
        min_periods=period,
    ).mean()

    return result


def _directional_streaks(
    dataframe: pd.DataFrame,
) -> tuple[pd.Series, pd.Series]:
    bullish_values: list[int] = []
    bearish_values: list[int] = []

    bullish_streak = 0
    bearish_streak = 0

    for open_price, close_price in zip(
        dataframe["open"],
        dataframe["close"],
    ):
        if close_price > open_price:
            bullish_streak += 1
            bearish_streak = 0
        elif close_price < open_price:
            bearish_streak += 1
            bullish_streak = 0
        else:
            bullish_streak = 0
            bearish_streak = 0

        bullish_values.append(bullish_streak)
        bearish_values.append(bearish_streak)

    return (
        pd.Series(bullish_values, index=dataframe.index, dtype=int),
        pd.Series(bearish_values, index=dataframe.index, dtype=int),
    )


def _ratio_score(
    values: pd.Series,
    target: float,
) -> pd.Series:
    if target <= 0:
        raise DisplacementError(
            "Displacement normalization targets must be > 0."
        )

    return (
        pd.to_numeric(values, errors="coerce")
        .div(target)
        .clip(lower=0.0, upper=1.0)
    )


def _category(
    score: pd.Series,
    coverage: pd.Series,
    *,
    settings: DisplacementComponentSettings,
) -> pd.Series:
    result = pd.Series(
        "none",
        index=score.index,
        dtype=object,
    )

    eligible = (
        coverage >= settings.minimum_coverage_fraction
    )

    result.loc[
        eligible & (score >= settings.weak_threshold)
    ] = "weak"

    result.loc[
        eligible & (score >= settings.moderate_threshold)
    ] = "moderate"

    result.loc[
        eligible & (score >= settings.strong_threshold)
    ] = "strong"

    return result


def _weighted_score(
    components: Mapping[
        str,
        tuple[pd.Series, pd.Series],
    ],
    *,
    weights: Mapping[str, float],
) -> tuple[pd.Series, pd.Series]:
    index = next(iter(components.values()))[0].index

    numerator = pd.Series(0.0, index=index)
    available_weight = pd.Series(0.0, index=index)

    total_weight = float(sum(weights.values()))

    for name, (component, available) in components.items():
        weight = float(weights[name])

        availability = available.fillna(False).astype(bool)

        numerator = numerator + (
            component.fillna(0.0)
            * weight
            * availability.astype(float)
        )

        available_weight = available_weight + (
            weight * availability.astype(float)
        )

    score = (
        numerator
        .div(available_weight.replace(0.0, np.nan))
        .mul(100.0)
        .fillna(0.0)
        .clip(lower=0.0, upper=100.0)
    )

    coverage = (
        available_weight / total_weight
        if total_weight > 0
        else pd.Series(0.0, index=index)
    )

    return score, coverage


def enrich_displacement_components(
    dataframe: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Add explainable, causal displacement components.

    The model uses only information available on the current or prior
    completed bars. It never inspects future follow-through.
    """

    _validate(dataframe)

    settings = build_component_settings(config)

    result = (
        dataframe
        .sort_values("timestamp")
        .copy()
        .reset_index(drop=True)
    )

    result = _add_atr(
        result,
        period=settings.atr_period,
    )

    atr = result["displacement_atr"].replace(0, np.nan)

    result["displacement_body"] = (
        result["close"] - result["open"]
    ).abs()

    result["displacement_range"] = (
        result["high"] - result["low"]
    )

    result["displacement_body_atr_ratio"] = (
        result["displacement_body"] / atr
    )

    result["displacement_range_atr_ratio"] = (
        result["displacement_range"] / atr
    )

    candle_range = (
        result["high"] - result["low"]
    ).replace(0, np.nan)

    result["displacement_close_location"] = (
        result["close"] - result["low"]
    ) / candle_range

    bullish_direction = (
        result["close"] > result["open"]
    )

    bearish_direction = (
        result["close"] < result["open"]
    )

    bullish_streak, bearish_streak = (
        _directional_streaks(result)
    )

    result["bullish_directional_streak"] = bullish_streak
    result["bearish_directional_streak"] = bearish_streak

    body_component = _ratio_score(
        result["displacement_body_atr_ratio"],
        settings.body_atr_target,
    )

    range_component = _ratio_score(
        result["displacement_range_atr_ratio"],
        settings.range_atr_target,
    )

    bullish_close_target = (
        1.0 - settings.close_extreme_fraction
    )

    bearish_close_target = (
        settings.close_extreme_fraction
    )

    bullish_close_component = (
        (
            result["displacement_close_location"] - 0.5
        )
        / max(bullish_close_target - 0.5, 1e-9)
    ).clip(lower=0.0, upper=1.0)

    bearish_close_component = (
        (
            0.5 - result["displacement_close_location"]
        )
        / max(0.5 - bearish_close_target, 1e-9)
    ).clip(lower=0.0, upper=1.0)

    bullish_consecutive_component = _ratio_score(
        bullish_streak.astype(float),
        float(settings.consecutive_candles_target),
    )

    bearish_consecutive_component = _ratio_score(
        bearish_streak.astype(float),
        float(settings.consecutive_candles_target),
    )

    if "active_internal_swing_high" in result.columns:
        result["bullish_break_distance_points"] = (
            result["close"]
            - result["active_internal_swing_high"]
        ).clip(lower=0.0)

        bullish_break_available = (
            result["active_internal_swing_high"].notna()
            & atr.notna()
        )
    else:
        result["bullish_break_distance_points"] = np.nan
        bullish_break_available = pd.Series(
            False,
            index=result.index,
        )

    if "active_internal_swing_low" in result.columns:
        result["bearish_break_distance_points"] = (
            result["active_internal_swing_low"]
            - result["close"]
        ).clip(lower=0.0)

        bearish_break_available = (
            result["active_internal_swing_low"].notna()
            & atr.notna()
        )
    else:
        result["bearish_break_distance_points"] = np.nan
        bearish_break_available = pd.Series(
            False,
            index=result.index,
        )

    result["bullish_break_distance_atr"] = (
        result["bullish_break_distance_points"] / atr
    )

    result["bearish_break_distance_atr"] = (
        result["bearish_break_distance_points"] / atr
    )

    bullish_break_component = _ratio_score(
        result["bullish_break_distance_atr"],
        settings.break_distance_atr_target,
    )

    bearish_break_component = _ratio_score(
        result["bearish_break_distance_atr"],
        settings.break_distance_atr_target,
    )

    rvol_column: str | None = None

    if "rvol_time_of_day" in result.columns:
        rvol_column = "rvol_time_of_day"
    elif "rvol_rolling" in result.columns:
        rvol_column = "rvol_rolling"

    if rvol_column is None:
        result["displacement_rvol"] = np.nan
        rvol_available = pd.Series(
            False,
            index=result.index,
        )
    else:
        result["displacement_rvol"] = pd.to_numeric(
            result[rvol_column],
            errors="coerce",
        )

        rvol_available = result[
            "displacement_rvol"
        ].notna()

    rvol_component = _ratio_score(
        result["displacement_rvol"],
        settings.rvol_target,
    )

    if "bullish_fvg_created" in result.columns:
        bullish_fvg_component = result[
            "bullish_fvg_created"
        ].fillna(False).astype(float)

        bullish_fvg_available = pd.Series(
            True,
            index=result.index,
        )
    else:
        bullish_fvg_component = pd.Series(
            np.nan,
            index=result.index,
        )

        bullish_fvg_available = pd.Series(
            False,
            index=result.index,
        )

    if "bearish_fvg_created" in result.columns:
        bearish_fvg_component = result[
            "bearish_fvg_created"
        ].fillna(False).astype(float)

        bearish_fvg_available = pd.Series(
            True,
            index=result.index,
        )
    else:
        bearish_fvg_component = pd.Series(
            np.nan,
            index=result.index,
        )

        bearish_fvg_available = pd.Series(
            False,
            index=result.index,
        )

    previous_high = result["high"].shift(1)
    previous_low = result["low"].shift(1)

    bullish_follow_through = (
        result["close"] > previous_high
    )

    bearish_follow_through = (
        result["close"] < previous_low
    )

    follow_through_available = previous_high.notna()

    result["bullish_follow_through"] = (
        bullish_follow_through.fillna(False)
    )

    result["bearish_follow_through"] = (
        bearish_follow_through.fillna(False)
    )

    base_available = atr.notna()

    bullish_components = {
        "body_atr": (
            body_component,
            base_available,
        ),
        "range_atr": (
            range_component,
            base_available,
        ),
        "close_location": (
            bullish_close_component,
            result["displacement_close_location"].notna(),
        ),
        "consecutive": (
            bullish_consecutive_component,
            pd.Series(True, index=result.index),
        ),
        "structure_break_distance": (
            bullish_break_component,
            bullish_break_available,
        ),
        "rvol": (
            rvol_component,
            rvol_available,
        ),
        "fvg_generation": (
            bullish_fvg_component,
            bullish_fvg_available,
        ),
        "follow_through": (
            bullish_follow_through.astype(float),
            follow_through_available,
        ),
    }

    bearish_components = {
        "body_atr": (
            body_component,
            base_available,
        ),
        "range_atr": (
            range_component,
            base_available,
        ),
        "close_location": (
            bearish_close_component,
            result["displacement_close_location"].notna(),
        ),
        "consecutive": (
            bearish_consecutive_component,
            pd.Series(True, index=result.index),
        ),
        "structure_break_distance": (
            bearish_break_component,
            bearish_break_available,
        ),
        "rvol": (
            rvol_component,
            rvol_available,
        ),
        "fvg_generation": (
            bearish_fvg_component,
            bearish_fvg_available,
        ),
        "follow_through": (
            bearish_follow_through.astype(float),
            follow_through_available,
        ),
    }

    for direction, components in (
        ("bullish", bullish_components),
        ("bearish", bearish_components),
    ):
        for name, (component, _) in components.items():
            result[
                f"{direction}_displacement_component_{name}"
            ] = component

    bullish_score, bullish_coverage = _weighted_score(
        bullish_components,
        weights=settings.weights,
    )

    bearish_score, bearish_coverage = _weighted_score(
        bearish_components,
        weights=settings.weights,
    )

    if settings.require_directional_close:
        bullish_score = bullish_score.where(
            bullish_direction,
            0.0,
        )

        bearish_score = bearish_score.where(
            bearish_direction,
            0.0,
        )

    result["bullish_displacement_score"] = bullish_score
    result["bearish_displacement_score"] = bearish_score

    result["bullish_displacement_coverage"] = bullish_coverage
    result["bearish_displacement_coverage"] = bearish_coverage

    result["bullish_displacement_category"] = _category(
        bullish_score,
        bullish_coverage,
        settings=settings,
    )

    result["bearish_displacement_category"] = _category(
        bearish_score,
        bearish_coverage,
        settings=settings,
    )

    bullish_wins = bullish_score > bearish_score
    bearish_wins = bearish_score > bullish_score

    result["displacement_direction"] = "neutral"

    result.loc[
        bullish_wins
        & (
            result["bullish_displacement_category"]
            != "none"
        ),
        "displacement_direction",
    ] = "bullish"

    result.loc[
        bearish_wins
        & (
            result["bearish_displacement_category"]
            != "none"
        ),
        "displacement_direction",
    ] = "bearish"

    result["displacement_score"] = pd.concat(
        [
            bullish_score,
            bearish_score,
        ],
        axis=1,
    ).max(axis=1)

    result["displacement_category"] = "none"

    bullish_selected = (
        result["displacement_direction"] == "bullish"
    )

    bearish_selected = (
        result["displacement_direction"] == "bearish"
    )

    result.loc[
        bullish_selected,
        "displacement_category",
    ] = result.loc[
        bullish_selected,
        "bullish_displacement_category",
    ]

    result.loc[
        bearish_selected,
        "displacement_category",
    ] = result.loc[
        bearish_selected,
        "bearish_displacement_category",
    ]

    return result
