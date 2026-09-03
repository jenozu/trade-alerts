from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


class DealingRangeError(RuntimeError):
    """Raised when a deterministic dealing range cannot be computed safely."""


REQUIRED_COLUMNS = {
    "timestamp",
    "close",
}


def _validate(dataframe: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(dataframe.columns)
    if missing:
        raise DealingRangeError(
            f"Missing required columns: {sorted(missing)}"
        )

    if dataframe.empty:
        raise DealingRangeError(
            "Cannot compute dealing ranges on an empty dataframe."
        )

    if not pd.api.types.is_datetime64_any_dtype(
        dataframe["timestamp"]
    ):
        raise DealingRangeError("'timestamp' must be datetime.")

    if getattr(dataframe["timestamp"].dt, "tz", None) is None:
        raise DealingRangeError(
            "'timestamp' must be timezone-aware."
        )


def _classify_location(
    percentile: pd.Series,
    *,
    equilibrium_tolerance: float,
) -> pd.Series:
    result = pd.Series(
        "unknown",
        index=percentile.index,
        dtype=object,
    )

    valid = percentile.notna()

    lower = 0.5 - equilibrium_tolerance
    upper = 0.5 + equilibrium_tolerance

    result.loc[valid & (percentile < lower)] = "discount"
    result.loc[valid & (percentile > upper)] = "premium"
    result.loc[
        valid
        & (percentile >= lower)
        & (percentile <= upper)
    ] = "equilibrium"

    return result


def add_dealing_range(
    dataframe: pd.DataFrame,
    *,
    range_high_column: str,
    range_low_column: str,
    prefix: str,
    price_column: str = "close",
    equilibrium_tolerance: float = 0.0,
) -> pd.DataFrame:
    """Add deterministic premium/discount features for one structural range.

    Range boundaries must already be causal inputs. This function never
    discovers future extrema or rewrites prior structural state.
    """

    _validate(dataframe)

    if price_column not in dataframe.columns:
        raise DealingRangeError(
            f"Missing price column: {price_column}"
        )

    required_range_columns = {
        range_high_column,
        range_low_column,
    }
    missing = required_range_columns - set(dataframe.columns)
    if missing:
        raise DealingRangeError(
            f"Missing dealing-range columns: {sorted(missing)}"
        )

    if not 0.0 <= equilibrium_tolerance < 0.5:
        raise DealingRangeError(
            "equilibrium_tolerance must be >= 0 and < 0.5."
        )

    result = dataframe.copy()

    high = pd.to_numeric(
        result[range_high_column],
        errors="coerce",
    )
    low = pd.to_numeric(
        result[range_low_column],
        errors="coerce",
    )
    price = pd.to_numeric(
        result[price_column],
        errors="coerce",
    )

    valid = (
        high.notna()
        & low.notna()
        & price.notna()
        & (high > low)
    )

    width = (high - low).where(valid)
    midpoint = ((high + low) / 2.0).where(valid)

    percentile = (
        ((price - low) / width)
        .where(valid)
        .clip(lower=0.0, upper=1.0)
    )

    result[f"{prefix}_range_high"] = high.where(valid)
    result[f"{prefix}_range_low"] = low.where(valid)
    result[f"{prefix}_range_width"] = width
    result[f"{prefix}_equilibrium"] = midpoint
    result[f"{prefix}_percentile"] = percentile
    result[f"{prefix}_location"] = _classify_location(
        percentile,
        equilibrium_tolerance=equilibrium_tolerance,
    )

    result[f"{prefix}_distance_to_equilibrium"] = (
        price - midpoint
    ).where(valid)

    result[f"{prefix}_distance_to_high"] = (
        high - price
    ).where(valid)

    result[f"{prefix}_distance_to_low"] = (
        price - low
    ).where(valid)

    result[f"{prefix}_valid"] = valid.astype(bool)

    return result


def enrich_dealing_ranges(
    dataframe: pd.DataFrame,
    *,
    scopes: Iterable[str] = ("internal", "external"),
    price_column: str = "close",
    equilibrium_tolerance: float = 0.0,
) -> pd.DataFrame:
    """Enrich a dataframe with one or more confirmed structural ranges."""

    _validate(dataframe)

    result = dataframe.copy()

    for scope in scopes:
        scope = str(scope).strip()

        if not scope:
            raise DealingRangeError(
                "Dealing-range scope cannot be blank."
            )

        high_column = f"{scope}_structure_range_high"
        low_column = f"{scope}_structure_range_low"

        result = add_dealing_range(
            result,
            range_high_column=high_column,
            range_low_column=low_column,
            prefix=f"{scope}_dealing",
            price_column=price_column,
            equilibrium_tolerance=equilibrium_tolerance,
        )

    return result
