from __future__ import annotations

import numpy as np
import pandas as pd


class SwingLifecycleError(RuntimeError):
    """Raised when swing lifecycle state cannot be classified safely."""


def enrich_swing_lifecycle(
    dataframe: pd.DataFrame,
    config: dict,
) -> pd.DataFrame:
    """Classify active internal swings after structure/displacement state.

    Bullish structure:
      - low = protected/strong
      - high = weak-liquidity

    Bearish structure:
      - high = protected/strong
      - low = weak-liquidity

    A swing that is broken by a strong same-direction displacement break is
    explicitly marked broken-with-displacement and no longer presented as
    protected or weak.
    """

    required = {
        "timestamp",
        "active_internal_swing_high",
        "active_internal_swing_low",
        "internal_structure_trend",
    }

    missing = required - set(
        dataframe.columns
    )

    if missing:
        raise SwingLifecycleError(
            f"Missing swing lifecycle columns: {sorted(missing)}"
        )

    result = dataframe.copy()

    n = len(result)

    high_broken = np.zeros(n, dtype=bool)
    low_broken = np.zeros(n, dtype=bool)

    high_protected = np.zeros(n, dtype=bool)
    low_protected = np.zeros(n, dtype=bool)

    high_weak = np.zeros(n, dtype=bool)
    low_weak = np.zeros(n, dtype=bool)

    high_status = np.full(
        n,
        "unclassified",
        dtype=object,
    )

    low_status = np.full(
        n,
        "unclassified",
        dtype=object,
    )

    high_reason = np.full(
        n,
        "structure_trend_unavailable",
        dtype=object,
    )

    low_reason = np.full(
        n,
        "structure_trend_unavailable",
        dtype=object,
    )

    current_high = np.nan
    current_low = np.nan

    current_high_broken = False
    current_low_broken = False

    for i in range(n):
        row = result.iloc[i]

        high_level = row[
            "active_internal_swing_high"
        ]

        low_level = row[
            "active_internal_swing_low"
        ]

        if pd.notna(high_level) and (
            pd.isna(current_high)
            or float(high_level)
            != float(current_high)
        ):
            current_high = float(high_level)
            current_high_broken = False

        if pd.notna(low_level) and (
            pd.isna(current_low)
            or float(low_level)
            != float(current_low)
        ):
            current_low = float(low_level)
            current_low_broken = False

        if bool(
            row.get(
                "bullish_displacement_structure_break_event",
                False,
            )
        ):
            current_high_broken = True

        if bool(
            row.get(
                "bearish_displacement_structure_break_event",
                False,
            )
        ):
            current_low_broken = True

        trend = str(
            row.get(
                "internal_structure_trend",
                "unknown",
            )
        )

        if pd.notna(current_high):
            high_broken[i] = current_high_broken

            if current_high_broken:
                high_status[i] = (
                    "broken_with_displacement"
                )

                high_reason[i] = (
                    "active_swing_high_closed_above_"
                    "with_strong_bullish_displacement"
                )

            elif trend == "bearish":
                high_protected[i] = True
                high_status[i] = "protected_strong"

                high_reason[i] = (
                    "bearish_structure_protects_"
                    "active_swing_high"
                )

            elif trend == "bullish":
                high_weak[i] = True
                high_status[i] = "weak_liquidity"

                high_reason[i] = (
                    "bullish_structure_targets_"
                    "buy_side_swing_high"
                )

            else:
                high_status[i] = "neutral"

                high_reason[i] = (
                    "structure_not_directional"
                )

        if pd.notna(current_low):
            low_broken[i] = current_low_broken

            if current_low_broken:
                low_status[i] = (
                    "broken_with_displacement"
                )

                low_reason[i] = (
                    "active_swing_low_closed_below_"
                    "with_strong_bearish_displacement"
                )

            elif trend == "bullish":
                low_protected[i] = True
                low_status[i] = "protected_strong"

                low_reason[i] = (
                    "bullish_structure_protects_"
                    "active_swing_low"
                )

            elif trend == "bearish":
                low_weak[i] = True
                low_status[i] = "weak_liquidity"

                low_reason[i] = (
                    "bearish_structure_targets_"
                    "sell_side_swing_low"
                )

            else:
                low_status[i] = "neutral"

                low_reason[i] = (
                    "structure_not_directional"
                )

    result[
        "active_internal_swing_high_broken_with_displacement"
    ] = high_broken

    result[
        "active_internal_swing_low_broken_with_displacement"
    ] = low_broken

    result[
        "active_internal_swing_high_protected_strong"
    ] = high_protected

    result[
        "active_internal_swing_low_protected_strong"
    ] = low_protected

    result[
        "active_internal_swing_high_weak_liquidity"
    ] = high_weak

    result[
        "active_internal_swing_low_weak_liquidity"
    ] = low_weak

    result[
        "active_internal_swing_high_classification"
    ] = high_status

    result[
        "active_internal_swing_low_classification"
    ] = low_status

    result[
        "active_internal_swing_high_classification_reason"
    ] = high_reason

    result[
        "active_internal_swing_low_classification_reason"
    ] = low_reason

    return result
