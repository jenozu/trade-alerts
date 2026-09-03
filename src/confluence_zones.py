from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd


class ConfluenceZoneError(RuntimeError):
    """Raised when causal confluence zones cannot be built safely."""


REQUIRED_COLUMNS = {
    "timestamp",
    "high",
    "low",
    "close",
}


DEFAULT_WEIGHTS = {
    "htf_swing": 18.0,
    "session_level": 14.0,
    "equal_liquidity": 14.0,
    "fvg_boundary": 14.0,
    "vwap": 10.0,
    "equilibrium": 8.0,
}


SESSION_LEVELS = (
    "pdh",
    "pdl",
    "pmh",
    "pml",
    "onh",
    "onl",
    "loh",
    "lol",
    "ash",
    "asl",
    "week_high",
    "week_low",
)


HTF_SWING_COLUMNS = (
    "active_external_swing_high",
    "active_external_swing_low",
    "confirmed_swing_high_1h",
    "confirmed_swing_low_1h",
    "confirmed_swing_high_4h",
    "confirmed_swing_low_4h",
    "confirmed_swing_high_1d",
    "confirmed_swing_low_1d",
)


FVG_BOUNDARY_COLUMNS = (
    "nearest_active_bullish_fvg_lower",
    "nearest_active_bullish_fvg_upper",
    "nearest_active_bearish_fvg_lower",
    "nearest_active_bearish_fvg_upper",
    "nearest_5m_fvg_above",
    "nearest_5m_fvg_below",
    "nearest_htf_fvg_above",
    "nearest_htf_fvg_below",
)


@dataclass(frozen=True)
class ConfluenceSummary:
    zones: int
    support_zones: int
    resistance_zones: int
    pivot_zones: int
    maximum_score: float


def _validate(
    dataframe: pd.DataFrame,
) -> None:
    missing = (
        REQUIRED_COLUMNS
        - set(dataframe.columns)
    )

    if missing:
        raise ConfluenceZoneError(
            f"Missing required columns: {sorted(missing)}"
        )

    if dataframe.empty:
        raise ConfluenceZoneError(
            "Cannot build confluence zones from an empty dataframe."
        )

    if not pd.api.types.is_datetime64_any_dtype(
        dataframe["timestamp"]
    ):
        raise ConfluenceZoneError(
            "'timestamp' must be datetime."
        )

    if getattr(
        dataframe["timestamp"].dt,
        "tz",
        None,
    ) is None:
        raise ConfluenceZoneError(
            "'timestamp' must be timezone-aware."
        )


def _known_times(
    dataframe: pd.DataFrame,
) -> pd.Series:
    if "available_at" in dataframe.columns:
        available = pd.to_datetime(
            dataframe["available_at"],
            utc=True,
            errors="coerce",
        )

        fallback = (
            pd.to_datetime(
                dataframe["timestamp"],
                utc=True,
            )
            + pd.Timedelta(minutes=1)
        )

        return available.fillna(
            fallback
        )

    return (
        pd.to_datetime(
            dataframe["timestamp"],
            utc=True,
        )
        + pd.Timedelta(minutes=1)
    )


def _normalize_as_of(
    dataframe: pd.DataFrame,
    as_of: pd.Timestamp | str | None,
) -> pd.Timestamp:
    known = _known_times(
        dataframe
    )

    if as_of is None:
        return pd.Timestamp(
            known.max()
        )

    timestamp = pd.Timestamp(
        as_of
    )

    if timestamp.tzinfo is None:
        raise ConfluenceZoneError(
            "as_of must be timezone-aware."
        )

    return timestamp.tz_convert(
        "UTC"
    )


def _visible_frame(
    dataframe: pd.DataFrame,
    as_of: pd.Timestamp,
) -> pd.DataFrame:
    result = (
        dataframe
        .sort_values(
            "timestamp",
            kind="stable",
        )
        .copy()
        .reset_index(drop=True)
    )

    result["_confluence_known_at"] = (
        _known_times(result)
    )

    result = (
        result.loc[
            result[
                "_confluence_known_at"
            ]
            <= as_of
        ]
        .copy()
        .reset_index(drop=True)
    )

    if result.empty:
        raise ConfluenceZoneError(
            "No market data is available at requested as_of."
        )

    return result


def _candidate_from_column(
    dataframe: pd.DataFrame,
    *,
    column: str,
    category: str,
    source: str | None = None,
    mitigation_state: str = "not_applicable",
) -> dict[str, Any] | None:
    if column not in dataframe.columns:
        return None

    values = pd.to_numeric(
        dataframe[column],
        errors="coerce",
    )

    valid = values.notna()

    if not valid.any():
        return None

    latest_index = int(
        values[valid].index[-1]
    )

    level = float(
        values.loc[
            latest_index
        ]
    )

    matching = (
        valid
        & np.isclose(
            values,
            level,
            atol=1e-9,
            rtol=0.0,
        )
    )

    first_index = int(
        values[
            matching
        ].index[0]
    )

    return {
        "level": level,
        "category": category,
        "source": (
            source
            if source is not None
            else column
        ),
        "available_at": pd.Timestamp(
            dataframe.at[
                first_index,
                "_confluence_known_at",
            ]
        ),
        "mitigation_state": mitigation_state,
    }


def _collect_candidates(
    dataframe: pd.DataFrame,
) -> list[dict[str, Any]]:
    candidates: list[
        dict[str, Any]
    ] = []

    for column in HTF_SWING_COLUMNS:
        candidate = _candidate_from_column(
            dataframe,
            column=column,
            category="htf_swing",
        )

        if candidate is not None:
            candidates.append(
                candidate
            )

    for column in SESSION_LEVELS:
        candidate = _candidate_from_column(
            dataframe,
            column=column,
            category="session_level",
        )

        if candidate is not None:
            candidates.append(
                candidate
            )

    # Equal-high/low cluster levels are event-driven, so inspect every
    # available equal-cluster column and retain its latest known value.
    for column in dataframe.columns:
        if not column.endswith(
            "_equal_cluster_level"
        ):
            continue

        candidate = _candidate_from_column(
            dataframe,
            column=column,
            category="equal_liquidity",
        )

        if candidate is not None:
            candidates.append(
                candidate
            )

    for column in FVG_BOUNDARY_COLUMNS:
        candidate = _candidate_from_column(
            dataframe,
            column=column,
            category="fvg_boundary",
            mitigation_state="active",
        )

        if candidate is not None:
            candidates.append(
                candidate
            )

    candidate = _candidate_from_column(
        dataframe,
        column="vwap",
        category="vwap",
    )

    if candidate is not None:
        candidates.append(
            candidate
        )

    for column in dataframe.columns:
        if not column.endswith(
            "_equilibrium"
        ):
            continue

        candidate = _candidate_from_column(
            dataframe,
            column=column,
            category="equilibrium",
        )

        if candidate is not None:
            candidates.append(
                candidate
            )

    return candidates


def _cluster_candidates(
    candidates: list[dict[str, Any]],
    *,
    tolerance_points: float,
) -> list[list[dict[str, Any]]]:
    if tolerance_points < 0:
        raise ConfluenceZoneError(
            "cluster_tolerance_points cannot be negative."
        )

    if not candidates:
        return []

    ordered = sorted(
        candidates,
        key=lambda item: (
            float(
                item["level"]
            ),
            str(
                item["category"]
            ),
            str(
                item["source"]
            ),
        ),
    )

    clusters: list[
        list[dict[str, Any]]
    ] = []

    current: list[
        dict[str, Any]
    ] = [
        ordered[0]
    ]

    for candidate in ordered[1:]:
        current_center = float(
            np.mean(
                [
                    item["level"]
                    for item in current
                ]
            )
        )

        if (
            float(
                candidate["level"]
            )
            - current_center
            <= tolerance_points
        ):
            current.append(
                candidate
            )
        else:
            clusters.append(
                current
            )

            current = [
                candidate
            ]

    clusters.append(
        current
    )

    return clusters


def _zone_side(
    *,
    midpoint: float,
    price: float,
    pivot_tolerance: float,
) -> str:
    if abs(
        midpoint - price
    ) <= pivot_tolerance:
        return "pivot"

    if midpoint < price:
        return "support"

    return "resistance"


def _reaction_metrics(
    dataframe: pd.DataFrame,
    *,
    lower: float,
    upper: float,
    available_at: pd.Timestamp,
    tolerance: float,
) -> tuple[
    int,
    int | None,
    pd.Series | None,
]:
    eligible = dataframe.loc[
        dataframe[
            "_confluence_known_at"
        ]
        >= available_at
    ].copy()

    if eligible.empty:
        return 0, None, None

    touch = (
        pd.to_numeric(
            eligible["high"],
            errors="coerce",
        )
        >= lower - tolerance
    ) & (
        pd.to_numeric(
            eligible["low"],
            errors="coerce",
        )
        <= upper + tolerance
    )

    touched = eligible.loc[
        touch
    ]

    if touched.empty:
        return 0, None, None

    last_touch_index = int(
        touched.index[-1]
    )

    last_visible_index = int(
        eligible.index[-1]
    )

    recency = (
        last_visible_index
        - last_touch_index
    )

    return (
        int(touch.sum()),
        int(recency),
        dataframe.loc[
            last_touch_index
        ],
    )


def _reaction_score(
    count: int,
    recency_bars: int | None,
) -> float:
    if count <= 0:
        return 0.0

    count_score = min(
        6.0,
        (
            min(
                count,
                3,
            )
            / 3.0
        )
        * 6.0,
    )

    if recency_bars is None:
        recency_score = 0.0

    elif recency_bars <= 3:
        recency_score = 4.0

    elif recency_bars <= 10:
        recency_score = 2.0

    else:
        recency_score = 0.0

    return min(
        10.0,
        count_score
        + recency_score,
    )


def _volume_reaction(
    touch_row: pd.Series | None,
) -> tuple[float, str]:
    if touch_row is None:
        return 0.0, "none"

    context = str(
        touch_row.get(
            "volume_context",
            "neutral",
        )
    )

    spike = bool(
        touch_row.get(
            "volume_spike_any",
            False,
        )
    )

    raw_rvol = touch_row.get(
        "rvol_time_of_day",
        touch_row.get(
            "rvol_rolling",
            np.nan,
        ),
    )

    rvol = (
        float(raw_rvol)
        if pd.notna(raw_rvol)
        else np.nan
    )

    if (
        spike
        or "high_volume"
        in context
        or "breakout"
        in context
        or "rejection"
        in context
    ):
        return 8.0, context

    if (
        pd.notna(rvol)
        and rvol >= 1.5
    ):
        return 6.0, (
            f"rvol_{rvol:.2f}"
        )

    if (
        pd.notna(rvol)
        and rvol >= 1.1
    ):
        return 3.0, (
            f"rvol_{rvol:.2f}"
        )

    return 0.0, context


def _displacement_away(
    touch_row: pd.Series | None,
    *,
    side: str,
    moderate_threshold: float,
    strong_threshold: float,
) -> tuple[
    float,
    float | None,
    str,
]:
    if touch_row is None:
        return 0.0, None, "none"

    direction = str(
        touch_row.get(
            "displacement_direction",
            "neutral",
        )
    )

    expected = (
        "bullish"
        if side == "support"
        else (
            "bearish"
            if side == "resistance"
            else "neutral"
        )
    )

    if direction != expected:
        return 0.0, None, direction

    directional_column = (
        "bullish_displacement_score"
        if expected == "bullish"
        else "bearish_displacement_score"
    )

    raw_score = touch_row.get(
        directional_column,
        touch_row.get(
            "displacement_score",
            np.nan,
        ),
    )

    if pd.isna(
        raw_score
    ):
        return 0.0, None, direction

    raw_score = float(
        raw_score
    )

    if raw_score >= strong_threshold:
        return 10.0, raw_score, direction

    if raw_score >= moderate_threshold:
        return 6.0, raw_score, direction

    if raw_score > 0:
        return 2.0, raw_score, direction

    return 0.0, raw_score, direction


def _htf_alignment(
    latest: pd.Series,
    *,
    side: str,
) -> tuple[
    float,
    str,
]:
    bias = str(
        latest.get(
            "htf_bias",
            latest.get(
                "intraday_bias",
                "neutral",
            ),
        )
    ).lower()

    if (
        side == "support"
        and bias == "bullish"
    ):
        return 8.0, "aligned_bullish"

    if (
        side == "resistance"
        and bias == "bearish"
    ):
        return 8.0, "aligned_bearish"

    if bias in {
        "bullish",
        "bearish",
    }:
        return 0.0, (
            f"opposed_{bias}"
        )

    return 0.0, (
        f"neutral_{bias}"
    )


def build_confluence_zones(
    dataframe: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    as_of: pd.Timestamp | str | None = None,
) -> pd.DataFrame:
    """Build transparent causal S/R confluence zones.

    This module intentionally complements rather than replaces src/snr.py.
    """

    _validate(
        dataframe
    )

    timestamp = _normalize_as_of(
        dataframe,
        as_of,
    )

    visible = _visible_frame(
        dataframe,
        timestamp,
    )

    latest = visible.iloc[
        -1
    ]

    current_price = float(
        latest["close"]
    )

    section = config.get(
        "confluence_zones",
        {},
    )

    cluster_tolerance = float(
        section.get(
            "cluster_tolerance_points",
            2.0,
        )
    )

    reaction_tolerance = float(
        section.get(
            "reaction_tolerance_points",
            1.0,
        )
    )

    pivot_tolerance = float(
        section.get(
            "pivot_tolerance_points",
            0.5,
        )
    )

    weights = dict(
        DEFAULT_WEIGHTS
    )

    weights.update(
        {
            str(key): float(value)
            for key, value
            in section.get(
                "component_weights",
                {},
            ).items()
        }
    )

    source_score_cap = float(
        section.get(
            "source_score_cap",
            60.0,
        )
    )

    displacement_config = (
        config.get(
            "displacement",
            {},
        )
        .get(
            "component_model",
            {},
        )
        .get(
            "categories",
            {},
        )
    )

    moderate_threshold = float(
        displacement_config.get(
            "moderate",
            50.0,
        )
    )

    strong_threshold = float(
        displacement_config.get(
            "strong",
            75.0,
        )
    )

    candidates = _collect_candidates(
        visible
    )

    clusters = _cluster_candidates(
        candidates,
        tolerance_points=cluster_tolerance,
    )

    rows: list[
        dict[str, Any]
    ] = []

    for zone_number, cluster in enumerate(
        clusters,
        start=1,
    ):
        levels = [
            float(
                item["level"]
            )
            for item in cluster
        ]

        lower = min(
            levels
        )

        upper = max(
            levels
        )

        midpoint = float(
            np.mean(
                levels
            )
        )

        side = _zone_side(
            midpoint=midpoint,
            price=current_price,
            pivot_tolerance=pivot_tolerance,
        )

        zone_available_at = max(
            pd.Timestamp(
                item[
                    "available_at"
                ]
            )
            for item in cluster
        )

        (
            reaction_count,
            reaction_recency,
            touch_row,
        ) = _reaction_metrics(
            visible,
            lower=lower,
            upper=upper,
            available_at=zone_available_at,
            tolerance=reaction_tolerance,
        )

        reaction_component_score = (
            _reaction_score(
                reaction_count,
                reaction_recency,
            )
        )

        (
            volume_component_score,
            volume_context,
        ) = _volume_reaction(
            touch_row
        )

        (
            displacement_component_score,
            raw_displacement_score,
            displacement_direction,
        ) = _displacement_away(
            touch_row,
            side=side,
            moderate_threshold=moderate_threshold,
            strong_threshold=strong_threshold,
        )

        (
            htf_component_score,
            htf_state,
        ) = _htf_alignment(
            latest,
            side=side,
        )

        categories = sorted(
            {
                str(
                    item[
                        "category"
                    ]
                )
                for item
                in cluster
            }
        )

        sources = sorted(
            {
                str(
                    item[
                        "source"
                    ]
                )
                for item
                in cluster
            }
        )

        raw_source_score = sum(
            weights.get(
                category,
                0.0,
            )
            for category
            in categories
        )

        source_component_score = min(
            source_score_cap,
            raw_source_score,
        )

        mitigation_states = sorted(
            {
                str(
                    item[
                        "mitigation_state"
                    ]
                )
                for item
                in cluster
            }
        )

        fvg_active = (
            "fvg_boundary"
            in categories
            and "active"
            in mitigation_states
        )

        mitigation_component_score = (
            4.0
            if fvg_active
            else 0.0
        )

        combined = min(
            100.0,
            source_component_score
            + reaction_component_score
            + volume_component_score
            + displacement_component_score
            + mitigation_component_score
            + htf_component_score,
        )

        component_flags = {
            category: (
                category
                in categories
            )
            for category
            in DEFAULT_WEIGHTS
        }

        explanation = {
            "sources": sources,
            "categories": categories,
            "source_component_score":
                source_component_score,
            "reaction_component_score":
                reaction_component_score,
            "volume_component_score":
                volume_component_score,
            "displacement_component_score":
                displacement_component_score,
            "mitigation_component_score":
                mitigation_component_score,
            "htf_alignment_component_score":
                htf_component_score,
        }

        rows.append(
            {
                "zone_id": (
                    f"zone:{timestamp.isoformat()}:{zone_number}"
                ),
                "as_of": timestamp,
                "zone_side": side,
                "zone_lower": lower,
                "zone_upper": upper,
                "zone_midpoint": midpoint,
                "distance_points": abs(
                    current_price
                    - midpoint
                ),
                "available_at": zone_available_at,
                "source_count": len(
                    sources
                ),
                "component_count": len(
                    categories
                ),
                "sources": "|".join(
                    sources
                ),
                "component_htf_swing":
                    component_flags[
                        "htf_swing"
                    ],
                "component_session_level":
                    component_flags[
                        "session_level"
                    ],
                "component_equal_liquidity":
                    component_flags[
                        "equal_liquidity"
                    ],
                "component_fvg_boundary":
                    component_flags[
                        "fvg_boundary"
                    ],
                "component_vwap":
                    component_flags[
                        "vwap"
                    ],
                "component_equilibrium":
                    component_flags[
                        "equilibrium"
                    ],
                "source_component_score":
                    source_component_score,
                "reaction_count":
                    reaction_count,
                "reaction_recency_bars":
                    reaction_recency,
                "reaction_component_score":
                    reaction_component_score,
                "volume_reaction_context":
                    volume_context,
                "volume_component_score":
                    volume_component_score,
                "displacement_away_direction":
                    displacement_direction,
                "displacement_away_raw_score":
                    raw_displacement_score,
                "displacement_component_score":
                    displacement_component_score,
                "mitigation_state": (
                    "active_fvg"
                    if fvg_active
                    else "not_applicable"
                ),
                "mitigation_component_score":
                    mitigation_component_score,
                "htf_alignment_state":
                    htf_state,
                "htf_alignment_component_score":
                    htf_component_score,
                "combined_zone_score":
                    combined,
                "components_json":
                    json.dumps(
                        explanation,
                        sort_keys=True,
                    ),
            }
        )

    columns = [
        "zone_id",
        "as_of",
        "zone_side",
        "zone_lower",
        "zone_upper",
        "zone_midpoint",
        "distance_points",
        "available_at",
        "source_count",
        "component_count",
        "sources",
        "component_htf_swing",
        "component_session_level",
        "component_equal_liquidity",
        "component_fvg_boundary",
        "component_vwap",
        "component_equilibrium",
        "source_component_score",
        "reaction_count",
        "reaction_recency_bars",
        "reaction_component_score",
        "volume_reaction_context",
        "volume_component_score",
        "displacement_away_direction",
        "displacement_away_raw_score",
        "displacement_component_score",
        "mitigation_state",
        "mitigation_component_score",
        "htf_alignment_state",
        "htf_alignment_component_score",
        "combined_zone_score",
        "components_json",
    ]

    if not rows:
        return pd.DataFrame(
            columns=columns
        )

    result = pd.DataFrame(
        rows
    )

    result["as_of"] = pd.to_datetime(
        result["as_of"],
        utc=True,
    )

    result["available_at"] = (
        pd.to_datetime(
            result["available_at"],
            utc=True,
        )
    )

    return (
        result[
            columns
        ]
        .sort_values(
            [
                "combined_zone_score",
                "distance_points",
                "zone_midpoint",
            ],
            ascending=[
                False,
                True,
                True,
            ],
            kind="stable",
        )
        .reset_index(drop=True)
    )


def confluence_summary(
    zones: pd.DataFrame,
) -> ConfluenceSummary:
    if zones.empty:
        return ConfluenceSummary(
            zones=0,
            support_zones=0,
            resistance_zones=0,
            pivot_zones=0,
            maximum_score=0.0,
        )

    return ConfluenceSummary(
        zones=len(zones),
        support_zones=int(
            (
                zones[
                    "zone_side"
                ]
                == "support"
            ).sum()
        ),
        resistance_zones=int(
            (
                zones[
                    "zone_side"
                ]
                == "resistance"
            ).sum()
        ),
        pivot_zones=int(
            (
                zones[
                    "zone_side"
                ]
                == "pivot"
            ).sum()
        ),
        maximum_score=float(
            zones[
                "combined_zone_score"
            ].max()
        ),
    )


def save_confluence_outputs(
    zones: pd.DataFrame,
    output_directory: str | Path,
) -> dict[str, Path]:
    directory = Path(
        output_directory
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    csv_path = (
        directory
        / "confluence_zones.csv"
    )

    parquet_path = (
        directory
        / "confluence_zones.parquet"
    )

    zones.to_csv(
        csv_path,
        index=False,
    )

    zones.to_parquet(
        parquet_path,
        index=False,
    )

    return {
        "confluence_zones_csv":
            csv_path,
        "confluence_zones_parquet":
            parquet_path,
    }


def directional_confluence_strength(
    row: pd.Series,
    config: Mapping[str, Any],
    *,
    direction: str,
) -> dict[str, Any]:
    """Return causal source-only S/R confluence for one market-state row.

    This intentionally uses only source-location evidence. Reaction,
    volume, displacement, and HTF alignment remain separate scorer
    components and therefore are not double-counted here.
    """

    direction = str(direction).strip().lower()

    if direction not in {
        "long",
        "short",
    }:
        raise ConfluenceZoneError(
            "direction must be 'long' or 'short'."
        )

    raw_price = row.get(
        "close",
        np.nan,
    )

    if pd.isna(raw_price):
        return {
            "score": 0.0,
            "source_score": 0.0,
            "midpoint": None,
            "distance_points": None,
            "sources": [],
            "categories": [],
        }

    price = float(
        raw_price
    )

    section = config.get(
        "confluence_zones",
        {},
    )

    tolerance = float(
        section.get(
            "cluster_tolerance_points",
            2.0,
        )
    )

    pivot_tolerance = float(
        section.get(
            "pivot_tolerance_points",
            0.5,
        )
    )

    source_score_cap = float(
        section.get(
            "source_score_cap",
            60.0,
        )
    )

    weights = dict(
        DEFAULT_WEIGHTS
    )

    weights.update(
        {
            str(key): float(value)
            for key, value
            in section.get(
                "component_weights",
                {},
            ).items()
        }
    )

    candidates: list[
        dict[str, Any]
    ] = []

    def add(
        column: str,
        category: str,
    ) -> None:
        if column not in row.index:
            return

        value = row.get(
            column
        )

        if pd.isna(value):
            return

        try:
            level = float(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            return

        candidates.append(
            {
                "level": level,
                "category": category,
                "source": column,
            }
        )

    for column in HTF_SWING_COLUMNS:
        add(
            column,
            "htf_swing",
        )

    for column in SESSION_LEVELS:
        add(
            column,
            "session_level",
        )

    for column in row.index:
        if str(
            column
        ).endswith(
            "_equal_cluster_level"
        ):
            add(
                str(column),
                "equal_liquidity",
            )

    for column in FVG_BOUNDARY_COLUMNS:
        add(
            column,
            "fvg_boundary",
        )

    add(
        "vwap",
        "vwap",
    )

    for column in row.index:
        if str(
            column
        ).endswith(
            "_equilibrium"
        ):
            add(
                str(column),
                "equilibrium",
            )

    if not candidates:
        return {
            "score": 0.0,
            "source_score": 0.0,
            "midpoint": None,
            "distance_points": None,
            "sources": [],
            "categories": [],
        }

    clusters = _cluster_candidates(
        candidates,
        tolerance_points=tolerance,
    )

    eligible: list[
        dict[str, Any]
    ] = []

    for cluster in clusters:
        midpoint = float(
            np.mean(
                [
                    float(
                        item["level"]
                    )
                    for item in cluster
                ]
            )
        )

        if direction == "long":
            direction_ok = (
                midpoint
                <= price
                + pivot_tolerance
            )
        else:
            direction_ok = (
                midpoint
                >= price
                - pivot_tolerance
            )

        if not direction_ok:
            continue

        categories = sorted(
            {
                str(
                    item["category"]
                )
                for item
                in cluster
            }
        )

        sources = sorted(
            {
                str(
                    item["source"]
                )
                for item
                in cluster
            }
        )

        source_score = min(
            source_score_cap,
            sum(
                float(
                    weights.get(
                        category,
                        0.0,
                    )
                )
                for category
                in categories
            ),
        )

        normalized = (
            source_score
            / source_score_cap
            * 100.0
            if source_score_cap > 0
            else 0.0
        )

        eligible.append(
            {
                "score": float(
                    np.clip(
                        normalized,
                        0.0,
                        100.0,
                    )
                ),
                "source_score":
                    source_score,
                "midpoint":
                    midpoint,
                "distance_points":
                    abs(
                        price
                        - midpoint
                    ),
                "sources":
                    sources,
                "categories":
                    categories,
            }
        )

    if not eligible:
        return {
            "score": 0.0,
            "source_score": 0.0,
            "midpoint": None,
            "distance_points": None,
            "sources": [],
            "categories": [],
        }

    eligible.sort(
        key=lambda item: (
            -float(
                item["score"]
            ),
            float(
                item[
                    "distance_points"
                ]
            ),
        )
    )

    return eligible[0]
