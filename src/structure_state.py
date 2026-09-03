from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd


class StructureStateError(RuntimeError):
    """Raised when deterministic structure state cannot be built safely."""


REQUIRED_COLUMNS = {
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "active_internal_swing_high",
    "active_internal_swing_low",
}


_TIMEFRAME_MINUTES = {
    "1m": 1,
    "2m": 2,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
}


def _validate(dataframe: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(dataframe.columns)

    if missing:
        raise StructureStateError(
            f"Missing required structure-state columns: {sorted(missing)}"
        )

    if dataframe.empty:
        raise StructureStateError(
            "Cannot build structure state from an empty dataframe."
        )

    if not pd.api.types.is_datetime64_any_dtype(
        dataframe["timestamp"]
    ):
        raise StructureStateError(
            "'timestamp' must be datetime."
        )

    if getattr(dataframe["timestamp"].dt, "tz", None) is None:
        raise StructureStateError(
            "'timestamp' must be timezone-aware."
        )


def _known_at(
    row: pd.Series,
    *,
    timeframe: str,
) -> pd.Timestamp:
    available_at = row.get("available_at")

    if pd.notna(available_at):
        return pd.Timestamp(available_at)

    minutes = _TIMEFRAME_MINUTES.get(
        timeframe,
        1,
    )

    return (
        pd.Timestamp(row["timestamp"])
        + pd.Timedelta(minutes=minutes)
    )


def _strong_displacement_threshold(
    config: Mapping[str, Any],
) -> float:
    return float(
        config.get("displacement", {})
        .get("component_model", {})
        .get("categories", {})
        .get("strong", 75.0)
    )


def enrich_structure_state(
    dataframe: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    timeframe: str = "1m",
) -> pd.DataFrame:
    """Add explicit causal sweep/break/displacement/reclaim structure state.

    Contract:
    - wick through + close back through level = sweep, not break;
    - body close beyond buffered level = structural break;
    - body close + strong same-direction displacement = displacement break;
    - reclaim = later close back through the broken level;
    - failed break = reclaim of a body-close break that lacked strong
      displacement confirmation.
    """

    _validate(dataframe)

    result = (
        dataframe
        .sort_values("timestamp")
        .copy()
        .reset_index(drop=True)
    )

    structure = config.get(
        "structure",
        {},
    )

    buffer_points = float(
        structure.get(
            "break_buffer_points",
            0.25,
        )
    )

    strong_threshold = (
        _strong_displacement_threshold(
            config
        )
    )

    n = len(result)

    bullish_wick_sweep = np.zeros(n, dtype=bool)
    bearish_wick_sweep = np.zeros(n, dtype=bool)

    bullish_body_break = np.zeros(n, dtype=bool)
    bearish_body_break = np.zeros(n, dtype=bool)

    bullish_displacement_break = np.zeros(n, dtype=bool)
    bearish_displacement_break = np.zeros(n, dtype=bool)

    bullish_continuation = np.zeros(n, dtype=bool)
    bearish_continuation = np.zeros(n, dtype=bool)

    bullish_reclaim = np.zeros(n, dtype=bool)
    bearish_reclaim = np.zeros(n, dtype=bool)

    bullish_failed = np.zeros(n, dtype=bool)
    bearish_failed = np.zeros(n, dtype=bool)

    break_direction = np.full(n, None, dtype=object)
    break_kind = np.full(n, None, dtype=object)
    broken_level = np.full(n, np.nan)
    broken_timeframe = np.full(n, None, dtype=object)
    broken_timestamp = np.full(n, pd.NaT, dtype=object)
    broken_available_at = np.full(n, pd.NaT, dtype=object)

    break_displacement_score = np.full(n, np.nan)
    break_displacement_category = np.full(n, None, dtype=object)
    break_volume_context = np.full(n, None, dtype=object)
    break_rvol = np.full(n, np.nan)

    current_high = np.nan
    current_low = np.nan

    high_broken = False
    low_broken = False

    high_break_index: int | None = None
    low_break_index: int | None = None

    high_break_had_displacement = False
    low_break_had_displacement = False

    for i in range(n):
        row = result.iloc[i]

        high_level = row[
            "active_internal_swing_high"
        ]

        low_level = row[
            "active_internal_swing_low"
        ]

        # New active swing => new structural contract.
        if pd.notna(high_level) and (
            pd.isna(current_high)
            or float(high_level) != float(current_high)
        ):
            current_high = float(high_level)
            high_broken = False
            high_break_index = None
            high_break_had_displacement = False

        if pd.notna(low_level) and (
            pd.isna(current_low)
            or float(low_level) != float(current_low)
        ):
            current_low = float(low_level)
            low_broken = False
            low_break_index = None
            low_break_had_displacement = False

        close = float(row["close"])
        high = float(row["high"])
        low = float(row["low"])

        trend = str(
            row.get(
                "internal_structure_trend",
                "unknown",
            )
        )

        bullish_score = row.get(
            "bullish_displacement_score",
            np.nan,
        )

        bearish_score = row.get(
            "bearish_displacement_score",
            np.nan,
        )

        displacement_direction = str(
            row.get(
                "displacement_direction",
                "neutral",
            )
        )

        known_at = _known_at(
            row,
            timeframe=timeframe,
        )

        # ----------------------------------------------------
        # HIGH / bullish structural interaction
        # ----------------------------------------------------

        if pd.notna(current_high):
            wick_through = (
                high
                > current_high
                + buffer_points
            )

            close_back = (
                close <= current_high
            )

            if (
                wick_through
                and close_back
                and not high_broken
            ):
                bullish_wick_sweep[i] = True

            body_break = (
                close
                > current_high
                + buffer_points
            )

            if body_break and not high_broken:
                bullish_body_break[i] = True
                high_broken = True
                high_break_index = i

                displacement_confirmed = (
                    pd.notna(bullish_score)
                    and float(bullish_score)
                    >= strong_threshold
                    and displacement_direction
                    == "bullish"
                )

                high_break_had_displacement = (
                    displacement_confirmed
                )

                if displacement_confirmed:
                    bullish_displacement_break[i] = True
                    confirmation = "displacement"
                else:
                    confirmation = "body_close"

                if trend == "bullish":
                    bullish_continuation[i] = True

                break_direction[i] = "bullish"
                break_kind[i] = confirmation
                broken_level[i] = current_high
                broken_timeframe[i] = timeframe
                broken_timestamp[i] = row[
                    "timestamp"
                ]
                broken_available_at[i] = known_at

                break_displacement_score[i] = (
                    float(bullish_score)
                    if pd.notna(bullish_score)
                    else np.nan
                )

                break_displacement_category[i] = (
                    row.get(
                        "bullish_displacement_category",
                        row.get(
                            "displacement_category",
                            "none",
                        ),
                    )
                )

                break_volume_context[i] = (
                    row.get(
                        "volume_context",
                        "unknown",
                    )
                )

                rvol = row.get(
                    "rvol_time_of_day",
                    row.get(
                        "rvol_rolling",
                        np.nan,
                    ),
                )

                break_rvol[i] = (
                    float(rvol)
                    if pd.notna(rvol)
                    else np.nan
                )

            elif (
                high_broken
                and high_break_index is not None
                and i > high_break_index
                and close < current_high
            ):
                bullish_reclaim[i] = True

                if not high_break_had_displacement:
                    bullish_failed[i] = True

                # Only emit the first reclaim for this break.
                high_break_index = None

        # ----------------------------------------------------
        # LOW / bearish structural interaction
        # ----------------------------------------------------

        if pd.notna(current_low):
            wick_through = (
                low
                < current_low
                - buffer_points
            )

            close_back = (
                close >= current_low
            )

            if (
                wick_through
                and close_back
                and not low_broken
            ):
                bearish_wick_sweep[i] = True

            body_break = (
                close
                < current_low
                - buffer_points
            )

            if body_break and not low_broken:
                bearish_body_break[i] = True
                low_broken = True
                low_break_index = i

                displacement_confirmed = (
                    pd.notna(bearish_score)
                    and float(bearish_score)
                    >= strong_threshold
                    and displacement_direction
                    == "bearish"
                )

                low_break_had_displacement = (
                    displacement_confirmed
                )

                if displacement_confirmed:
                    bearish_displacement_break[i] = True
                    confirmation = "displacement"
                else:
                    confirmation = "body_close"

                if trend == "bearish":
                    bearish_continuation[i] = True

                break_direction[i] = "bearish"
                break_kind[i] = confirmation
                broken_level[i] = current_low
                broken_timeframe[i] = timeframe
                broken_timestamp[i] = row[
                    "timestamp"
                ]
                broken_available_at[i] = known_at

                break_displacement_score[i] = (
                    float(bearish_score)
                    if pd.notna(bearish_score)
                    else np.nan
                )

                break_displacement_category[i] = (
                    row.get(
                        "bearish_displacement_category",
                        row.get(
                            "displacement_category",
                            "none",
                        ),
                    )
                )

                break_volume_context[i] = (
                    row.get(
                        "volume_context",
                        "unknown",
                    )
                )

                rvol = row.get(
                    "rvol_time_of_day",
                    row.get(
                        "rvol_rolling",
                        np.nan,
                    ),
                )

                break_rvol[i] = (
                    float(rvol)
                    if pd.notna(rvol)
                    else np.nan
                )

            elif (
                low_broken
                and low_break_index is not None
                and i > low_break_index
                and close > current_low
            ):
                bearish_reclaim[i] = True

                if not low_break_had_displacement:
                    bearish_failed[i] = True

                low_break_index = None

    result[
        "bullish_structure_wick_sweep_event"
    ] = bullish_wick_sweep

    result[
        "bearish_structure_wick_sweep_event"
    ] = bearish_wick_sweep

    result[
        "bullish_body_close_break_event"
    ] = bullish_body_break

    result[
        "bearish_body_close_break_event"
    ] = bearish_body_break

    result[
        "bullish_displacement_structure_break_event"
    ] = bullish_displacement_break

    result[
        "bearish_displacement_structure_break_event"
    ] = bearish_displacement_break

    result[
        "bullish_continuation_break_event"
    ] = bullish_continuation

    result[
        "bearish_continuation_break_event"
    ] = bearish_continuation

    result[
        "bullish_structure_reclaim_event"
    ] = bullish_reclaim

    result[
        "bearish_structure_reclaim_event"
    ] = bearish_reclaim

    result[
        "bullish_failed_break_event"
    ] = bullish_failed

    result[
        "bearish_failed_break_event"
    ] = bearish_failed

    result[
        "structure_break_direction"
    ] = break_direction

    result[
        "structure_break_confirmation"
    ] = break_kind

    result[
        "structure_broken_level"
    ] = broken_level

    result[
        "structure_broken_timeframe"
    ] = broken_timeframe

    result[
        "structure_break_timestamp"
    ] = pd.to_datetime(
        broken_timestamp,
        utc=True,
    )

    result[
        "structure_break_available_at"
    ] = pd.to_datetime(
        broken_available_at,
        utc=True,
    )

    result[
        "structure_break_displacement_score"
    ] = break_displacement_score

    result[
        "structure_break_displacement_category"
    ] = break_displacement_category

    result[
        "structure_break_volume_context"
    ] = break_volume_context

    result[
        "structure_break_rvol"
    ] = break_rvol

    return result
