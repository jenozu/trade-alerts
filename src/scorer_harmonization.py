from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd

from confluence_zones import (
    directional_confluence_strength,
)


class ScorerHarmonizationError(
    RuntimeError
):
    """Raised when harmonized scoring configuration is unsafe."""


def _text(
    row: pd.Series,
    column: str,
) -> str:
    if column not in row.index:
        return ""

    value = row.get(
        column
    )

    if pd.isna(value):
        return ""

    return str(
        value
    ).strip().lower()


def _number(
    row: pd.Series,
    column: str,
) -> float | None:
    if column not in row.index:
        return None

    value = row.get(
        column
    )

    if pd.isna(value):
        return None

    try:
        return float(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


def positive_weight_total(
    config: Mapping[
        str,
        Any,
    ],
) -> float:
    weights = (
        config
        .get(
            "scoring",
            {},
        )
        .get(
            "positive_weights",
            {},
        )
    )

    return float(
        sum(
            float(
                value
            )
            for value
            in weights.values()
        )
    )


def validate_positive_weight_total(
    config: Mapping[
        str,
        Any,
    ],
) -> float:
    scoring = config.get(
        "scoring",
        {},
    )

    harmonization = scoring.get(
        "harmonization",
        {},
    )

    required = harmonization.get(
        "required_positive_weight_total"
    )

    total = positive_weight_total(
        config
    )

    # Backward-compatible for isolated legacy/unit configs that do not
    # declare the production harmonization contract.
    if required is None:
        return total

    required = float(
        required
    )

    if not np.isclose(
        total,
        required,
        atol=1e-9,
        rtol=0.0,
    ):
        raise ScorerHarmonizationError(
            "Production positive scoring weights "
            f"must total {required:g}; found {total:g}."
        )

    return total


def vwap_alignment(
    row: pd.Series,
    direction: str,
) -> bool:
    position = _text(
        row,
        "vwap_position",
    )

    slope = _text(
        row,
        "vwap_slope_direction",
    )

    if direction == "long":
        if bool(
            row.get(
                "vwap_bullish_cross",
                False,
            )
        ):
            return True

        return (
            position == "above"
            and slope
            not in {
                "falling",
            }
        )

    if bool(
        row.get(
            "vwap_bearish_cross",
            False,
        )
    ):
        return True

    return (
        position == "below"
        and slope
        not in {
            "rising",
        }
    )


def dealing_range_alignment(
    row: pd.Series,
    direction: str,
) -> bool:
    locations = [
        _text(
            row,
            "external_dealing_location",
        ),
        _text(
            row,
            "internal_dealing_location",
        ),
    ]

    locations = [
        value
        for value
        in locations
        if value
        and value != "unknown"
    ]

    if not locations:
        return False

    desired = (
        "discount"
        if direction == "long"
        else "premium"
    )

    return (
        desired
        in locations
    )


def harmonized_key_location(
    row: pd.Series,
    direction: str,
    config: Mapping[
        str,
        Any,
    ],
    *,
    legacy_aligned: bool,
) -> tuple[
    bool,
    dict[str, float],
]:
    vwap_ok = vwap_alignment(
        row,
        direction,
    )

    confluence = (
        directional_confluence_strength(
            row,
            config,
            direction=direction,
        )
    )

    threshold = float(
        config.get(
            "scoring",
            {},
        )
        .get(
            "harmonization",
            {},
        )
        .get(
            "minimum_directional_confluence_score",
            40.0,
        )
    )

    confluence_score = float(
        confluence.get(
            "score",
            0.0,
        )
    )

    confluence_ok = (
        confluence_score
        >= threshold
    )

    aligned = bool(
        legacy_aligned
        or vwap_ok
        or confluence_ok
    )

    return (
        aligned,
        {
            "legacy":
                float(
                    bool(
                        legacy_aligned
                    )
                ),
            "vwap":
                float(
                    bool(
                        vwap_ok
                    )
                ),
            "confluence_aligned":
                float(
                    bool(
                        confluence_ok
                    )
                ),
            "confluence_score":
                confluence_score,
        },
    )


def richer_displacement_fraction(
    row: pd.Series,
    direction: str,
    *,
    legacy_aligned: bool,
) -> tuple[
    float,
    float | None,
]:
    score_column = (
        "bullish_displacement_score"
        if direction == "long"
        else "bearish_displacement_score"
    )

    raw = _number(
        row,
        score_column,
    )

    if raw is None:
        return (
            1.0
            if legacy_aligned
            else 0.0,
            None,
        )

    raw = float(
        np.clip(
            raw,
            0.0,
            100.0,
        )
    )

    return (
        raw / 100.0,
        raw,
    )


def snr_quality_adjustment(
    row: pd.Series,
    config: Mapping[
        str,
        Any,
    ],
) -> tuple[
    float,
    float,
    bool,
]:
    """Return positive fraction, penalty points, production-context-used.

    Direction is intentionally absent from this function.
    """

    modifier = _number(
        row,
        "snr_confidence_modifier_points",
    )

    if modifier is None:
        return (
            0.0,
            0.0,
            False,
        )

    morning = (
        config
        .get(
            "snr",
            {},
        )
        .get(
            "production_role",
            {},
        )
        .get(
            "morning_confidence",
            {},
        )
    )

    maximum_bonus = float(
        morning.get(
            "maximum_bonus_points",
            5.0,
        )
    )

    if modifier > 0:
        if maximum_bonus <= 0:
            return (
                0.0,
                0.0,
                True,
            )

        fraction = float(
            np.clip(
                modifier
                / maximum_bonus,
                0.0,
                1.0,
            )
        )

        return (
            fraction,
            0.0,
            True,
        )

    if modifier < 0:
        return (
            0.0,
            float(
                modifier
            ),
            True,
        )

    return (
        0.0,
        0.0,
        True,
    )
