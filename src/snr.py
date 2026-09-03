from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close"}
TIMEFRAME_MINUTES = {"1m": 1, "5m": 5, "15m": 15}


class SNRError(RuntimeError):
    """Raised when signal-to-noise features cannot be calculated safely."""


@dataclass(frozen=True)
class SNRSummary:
    timeframe: str
    rows: int
    available: int
    median_snr: float | None
    median_efficiency: float | None
    bullish: int
    bearish: int


def _validate(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise SNRError(f"Missing required columns: {sorted(missing)}")
    if df.empty:
        raise SNRError("Cannot calculate SNR on an empty dataframe.")
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        raise SNRError("'timestamp' must be datetime.")
    if getattr(df["timestamp"].dt, "tz", None) is None:
        raise SNRError("'timestamp' must be timezone-aware.")


def _atr(df: pd.DataFrame, period: int) -> pd.Series:
    previous_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period, min_periods=period).mean()


def calculate_snr_features(
    df: pd.DataFrame,
    *,
    timeframe: str,
    config: dict[str, Any],
) -> pd.DataFrame:
    _validate(df)
    result = df.sort_values("timestamp").copy().reset_index(drop=True)
    section = config.get("snr", {})
    per_tf = section.get("timeframes", {}).get(timeframe, {})
    lookback = int(per_tf.get("lookback_bars", section.get("lookback_bars", 5)))
    atr_period = int(per_tf.get("atr_period", section.get("atr_period", 14)))
    slope_period = int(per_tf.get("slope_bars", section.get("slope_bars", 3)))

    atr = _atr(result, atr_period)
    net = result["close"] - result["close"].shift(lookback)
    travel = result["close"].diff().abs().rolling(lookback, min_periods=lookback).sum()
    snr = net.abs() / atr.replace(0, np.nan)
    efficiency = net.abs() / travel.replace(0, np.nan)
    direction = np.select([net > 0, net < 0], ["bullish", "bearish"], default="neutral")

    prefix = timeframe
    result[f"atr_{prefix}"] = atr
    result[f"snr_{prefix}"] = snr
    result[f"snr_direction_{prefix}"] = direction
    result[f"snr_delta_{prefix}"] = snr.diff()
    result[f"snr_slope_{prefix}"] = snr.diff(slope_period) / max(slope_period, 1)
    result[f"efficiency_{prefix}"] = efficiency
    return result


def _available_at(df: pd.DataFrame, timeframe: str) -> pd.Series:
    if "available_at" in df.columns:
        return pd.to_datetime(df["available_at"], utc=True)
    minutes = TIMEFRAME_MINUTES[timeframe]
    return df["timestamp"] + pd.Timedelta(minutes=minutes)


def _merge_completed_features(
    base: pd.DataFrame,
    higher: pd.DataFrame,
    timeframe: str,
) -> pd.DataFrame:
    feature_columns = [
        f"snr_{timeframe}",
        f"snr_direction_{timeframe}",
        f"snr_delta_{timeframe}",
        f"snr_slope_{timeframe}",
        f"efficiency_{timeframe}",
        f"atr_{timeframe}",
    ]
    right = higher.copy()
    if "bar_complete" in right.columns:
        right = right.loc[right["bar_complete"].fillna(False)].copy()
    right["feature_available_at"] = _available_at(right, timeframe)
    right = right[["feature_available_at", *[c for c in feature_columns if c in right.columns]]]
    right = right.sort_values("feature_available_at")
    left = base.sort_values("timestamp").copy()
    return pd.merge_asof(
        left,
        right,
        left_on="timestamp",
        right_on="feature_available_at",
        direction="backward",
        allow_exact_matches=True,
    ).drop(columns=["feature_available_at"], errors="ignore")


def _alignment(row: pd.Series) -> str:
    directions = [row.get(f"snr_direction_{tf}") for tf in ("1m", "5m", "15m")]
    available = [d for d in directions if isinstance(d, str) and d in {"bullish", "bearish"}]
    if len(available) == 3 and all(d == "bullish" for d in available):
        return "strong_bullish"
    if len(available) == 3 and all(d == "bearish" for d in available):
        return "strong_bearish"
    if available.count("bullish") >= 2:
        return "partial_bullish"
    if available.count("bearish") >= 2:
        return "partial_bearish"
    return "mixed"


def build_multitimeframe_snr(
    dataframe_1m: pd.DataFrame,
    bars_5m: pd.DataFrame,
    bars_15m: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    one = calculate_snr_features(dataframe_1m, timeframe="1m", config=config)
    five = calculate_snr_features(bars_5m, timeframe="5m", config=config)
    fifteen = calculate_snr_features(bars_15m, timeframe="15m", config=config)
    merged = _merge_completed_features(one, five, "5m")
    merged = _merge_completed_features(merged, fifteen, "15m")
    merged["snr_alignment"] = merged.apply(_alignment, axis=1)

    magnitudes = pd.concat(
        [merged.get(f"snr_{tf}", pd.Series(np.nan, index=merged.index)) for tf in ("1m", "5m", "15m")],
        axis=1,
    )
    efficiencies = pd.concat(
        [merged.get(f"efficiency_{tf}", pd.Series(np.nan, index=merged.index)) for tf in ("1m", "5m", "15m")],
        axis=1,
    )
    # Research-quality metric only; no claim of probability calibration.
    merged["snr_composite_quality"] = (
        magnitudes.clip(upper=3).mean(axis=1) / 3.0
        + efficiencies.mean(axis=1)
    ) / 2.0

    # Production SNR is a bounded quality/confidence modifier only.
    # It does not create a directional trading signal.
    merged = add_snr_production_context(
        merged,
        config,
    )

    return merged



def _production_role_settings(
    config: dict[str, Any],
) -> dict[str, Any]:
    section = (
        config
        .get("snr", {})
        .get("production_role", {})
    )

    role = str(
        section.get(
            "role",
            "confidence_quality_modifier",
        )
    )

    standalone_direction_predictor = bool(
        section.get(
            "standalone_direction_predictor",
            False,
        )
    )

    if standalone_direction_predictor:
        raise SNRError(
            "Production SNR cannot be configured as a standalone "
            "direction predictor."
        )

    morning = section.get(
        "morning_confidence",
        {},
    )

    enabled = bool(
        morning.get(
            "enabled",
            True,
        )
    )

    maximum_bonus = float(
        morning.get(
            "maximum_bonus_points",
            5.0,
        )
    )

    maximum_penalty = float(
        morning.get(
            "maximum_penalty_points",
            5.0,
        )
    )

    weak_maximum = float(
        morning.get(
            "weak_quality_maximum",
            0.35,
        )
    )

    strong_minimum = float(
        morning.get(
            "strong_quality_minimum",
            0.70,
        )
    )

    developing_modifier = float(
        morning.get(
            "developing_modifier_points",
            0.0,
        )
    )

    expose_raw_components = bool(
        section.get(
            "expose_raw_components",
            True,
        )
    )

    if not (
        0.0
        <= weak_maximum
        < strong_minimum
        <= 1.0
    ):
        raise SNRError(
            "Production SNR quality thresholds must satisfy "
            "0 <= weak < strong <= 1."
        )

    if (
        maximum_bonus < 0
        or maximum_penalty < 0
    ):
        raise SNRError(
            "SNR bonus/penalty magnitudes cannot be negative."
        )

    return {
        "role": role,
        "enabled": enabled,
        "maximum_bonus_points": maximum_bonus,
        "maximum_penalty_points": maximum_penalty,
        "weak_quality_maximum": weak_maximum,
        "strong_quality_minimum": strong_minimum,
        "developing_modifier_points": developing_modifier,
        "expose_raw_components": expose_raw_components,
    }


def _json_number(
    value: Any,
) -> float | None:
    if pd.isna(value):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def snr_market_state_snapshot(
    row: pd.Series,
) -> dict[str, Any]:
    """Return explicit SNR state for later market-state serialization."""

    raw_components: dict[
        str,
        dict[str, Any],
    ] = {}

    for timeframe in (
        "1m",
        "5m",
        "15m",
    ):
        direction = row.get(
            f"snr_direction_{timeframe}"
        )

        if pd.isna(direction):
            direction = None

        raw_components[
            timeframe
        ] = {
            "snr": _json_number(
                row.get(
                    f"snr_{timeframe}"
                )
            ),
            "direction": (
                str(direction)
                if direction is not None
                else None
            ),
            "delta": _json_number(
                row.get(
                    f"snr_delta_{timeframe}"
                )
            ),
            "slope": _json_number(
                row.get(
                    f"snr_slope_{timeframe}"
                )
            ),
            "efficiency": _json_number(
                row.get(
                    f"efficiency_{timeframe}"
                )
            ),
            "atr": _json_number(
                row.get(
                    f"atr_{timeframe}"
                )
            ),
        }

    alignment = row.get(
        "snr_alignment"
    )

    if pd.isna(alignment):
        alignment = None

    quality_class = row.get(
        "snr_quality_class"
    )

    if pd.isna(quality_class):
        quality_class = None

    return {
        "role": row.get(
            "snr_production_role",
            "confidence_quality_modifier",
        ),
        "standalone_direction_predictor": False,
        "alignment": (
            str(alignment)
            if alignment is not None
            else None
        ),
        "composite_quality": _json_number(
            row.get(
                "snr_composite_quality"
            )
        ),
        "quality_class": (
            str(quality_class)
            if quality_class is not None
            else None
        ),
        "confidence_modifier_points": _json_number(
            row.get(
                "snr_confidence_modifier_points",
                0.0,
            )
        ),
        "raw_components": raw_components,
    }


def add_snr_production_context(
    dataframe: pd.DataFrame,
    config: dict[str, Any],
) -> pd.DataFrame:
    """Convert raw SNR into a bounded non-directional confidence modifier."""

    result = dataframe.copy()

    settings = (
        _production_role_settings(
            config
        )
    )

    quality = pd.to_numeric(
        result.get(
            "snr_composite_quality",
            pd.Series(
                np.nan,
                index=result.index,
            ),
        ),
        errors="coerce",
    ).clip(
        lower=0.0,
        upper=1.0,
    )

    available = (
        quality.notna()
    )

    weak = (
        available
        & (
            quality
            <= settings[
                "weak_quality_maximum"
            ]
        )
    )

    strong = (
        available
        & (
            quality
            >= settings[
                "strong_quality_minimum"
            ]
        )
    )

    developing = (
        available
        & ~weak
        & ~strong
    )

    quality_class = np.full(
        len(result),
        "unavailable",
        dtype=object,
    )

    quality_class[
        weak
    ] = "weak"

    quality_class[
        developing
    ] = "developing"

    quality_class[
        strong
    ] = "strong"

    modifier = np.zeros(
        len(result),
        dtype=float,
    )

    if settings["enabled"]:
        modifier[
            weak
        ] = -float(
            settings[
                "maximum_penalty_points"
            ]
        )

        modifier[
            developing
        ] = float(
            settings[
                "developing_modifier_points"
            ]
        )

        modifier[
            strong
        ] = float(
            settings[
                "maximum_bonus_points"
            ]
        )

    result[
        "snr_production_role"
    ] = settings[
        "role"
    ]

    # This column is intentionally always false.
    # Direction comes from structure/bias/liquidity/DOL, not SNR.
    result[
        "snr_standalone_direction_predictor"
    ] = False

    result[
        "snr_quality_class"
    ] = quality_class

    result[
        "snr_confidence_modifier_points"
    ] = modifier

    result[
        "snr_confidence_modifier_enabled"
    ] = bool(
        settings[
            "enabled"
        ]
    )

    if settings[
        "expose_raw_components"
    ]:
        snapshots = result.apply(
            snr_market_state_snapshot,
            axis=1,
        )

        result[
            "snr_raw_components_json"
        ] = snapshots.map(
            lambda snapshot: json.dumps(
                snapshot[
                    "raw_components"
                ],
                sort_keys=True,
            )
        )

        result[
            "snr_market_state_json"
        ] = snapshots.map(
            lambda snapshot: json.dumps(
                snapshot,
                sort_keys=True,
            )
        )

    return result


def snr_summary(df: pd.DataFrame, *, timeframe: str) -> SNRSummary:
    snr_col = f"snr_{timeframe}"
    eff_col = f"efficiency_{timeframe}"
    dir_col = f"snr_direction_{timeframe}"
    snr = df[snr_col] if snr_col in df.columns else pd.Series(dtype=float)
    efficiency = df[eff_col] if eff_col in df.columns else pd.Series(dtype=float)
    direction = df[dir_col] if dir_col in df.columns else pd.Series(dtype=object)
    return SNRSummary(
        timeframe=timeframe,
        rows=len(df),
        available=int(snr.notna().sum()),
        median_snr=float(snr.median()) if snr.notna().any() else None,
        median_efficiency=float(efficiency.median()) if efficiency.notna().any() else None,
        bullish=int((direction == "bullish").sum()),
        bearish=int((direction == "bearish").sum()),
    )


def save_snr_outputs(df: pd.DataFrame, output_directory: str | Path) -> dict[str, Path]:
    directory = Path(output_directory)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "nq_1m_snr.parquet"
    try:
        df.to_parquet(path, index=False)
    except ImportError as exc:
        raise SNRError("Saving Parquet requires pyarrow.") from exc
    return {"snr_features": path}
