from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd


class PDArrayError(RuntimeError):
    """Raised when PD-array state cannot be constructed safely."""


REQUIRED_COLUMNS = {
    "timestamp",
    "open",
    "high",
    "low",
    "close",
}


@dataclass(frozen=True)
class PDArraySummary:
    rows: int
    objects: int
    original_respects: int
    original_disrespects: int
    ifvgs_created: int
    ifvg_respects: int
    ifvg_disrespects: int


def _validate(dataframe: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(dataframe.columns)

    if missing:
        raise PDArrayError(
            f"Missing required PD-array columns: {sorted(missing)}"
        )

    if dataframe.empty:
        raise PDArrayError(
            "Cannot calculate PD arrays on an empty dataframe."
        )

    if not pd.api.types.is_datetime64_any_dtype(
        dataframe["timestamp"]
    ):
        raise PDArrayError(
            "'timestamp' must be datetime."
        )

    if getattr(
        dataframe["timestamp"].dt,
        "tz",
        None,
    ) is None:
        raise PDArrayError(
            "'timestamp' must be timezone-aware."
        )


def _known_at(
    dataframe: pd.DataFrame,
    index: int,
) -> pd.Timestamp:
    if "available_at" in dataframe.columns:
        value = dataframe.at[
            index,
            "available_at",
        ]

        if pd.notna(value):
            return pd.Timestamp(value)

    return (
        pd.Timestamp(
            dataframe.at[
                index,
                "timestamp",
            ]
        )
        + pd.Timedelta(minutes=1)
    )


def _opposite(
    direction: str,
) -> str:
    if direction == "bullish":
        return "bearish"

    if direction == "bearish":
        return "bullish"

    raise PDArrayError(
        f"Invalid PD-array direction: {direction}"
    )


def _creation_objects(
    dataframe: pd.DataFrame,
) -> list[dict[str, Any]]:
    objects: list[
        dict[str, Any]
    ] = []

    definitions = (
        (
            "bullish",
            "bullish_fvg_created",
            "bullish_fvg_lower",
            "bullish_fvg_upper",
        ),
        (
            "bearish",
            "bearish_fvg_created",
            "bearish_fvg_lower",
            "bearish_fvg_upper",
        ),
    )

    for i in range(
        len(dataframe)
    ):
        row = dataframe.iloc[i]

        for (
            direction,
            created_column,
            lower_column,
            upper_column,
        ) in definitions:
            if not bool(
                row.get(
                    created_column,
                    False,
                )
            ):
                continue

            lower = row.get(
                lower_column,
                np.nan,
            )

            upper = row.get(
                upper_column,
                np.nan,
            )

            if (
                pd.isna(lower)
                or pd.isna(upper)
            ):
                raise PDArrayError(
                    f"{direction} FVG created without valid bounds."
                )

            lower = float(lower)
            upper = float(upper)

            if upper <= lower:
                raise PDArrayError(
                    "PD-array upper bound must be greater than lower bound."
                )

            created_at = _known_at(
                dataframe,
                i,
            )

            identifier = (
                f"pdarr:{direction}:"
                f"{created_at.isoformat()}:"
                f"{lower:.8f}:"
                f"{upper:.8f}"
            )

            objects.append(
                {
                    "pd_array_id": identifier,
                    "creation_index": i,
                    "original_direction": direction,
                    "lower_bound": lower,
                    "upper_bound": upper,
                    "midpoint": (
                        lower + upper
                    ) / 2.0,
                    "created_at": created_at,
                    "session_date": row.get(
                        "session_date"
                    ),
                }
            )

    return objects


def _touches_zone(
    *,
    high: float,
    low: float,
    lower: float,
    upper: float,
) -> bool:
    return (
        high >= lower
        and low <= upper
    )


def build_pd_array_lifecycle(
    dataframe: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build causal FVG/IFVG respect-disrespect lifecycle objects."""

    _validate(dataframe)

    frame = (
        dataframe
        .sort_values(
            "timestamp",
            kind="stable",
        )
        .copy()
        .reset_index(drop=True)
    )

    section = config.get(
        "pd_arrays",
        {},
    )

    maximum_tracking_bars = int(
        section.get(
            "maximum_tracking_bars",
            50,
        )
    )

    if maximum_tracking_bars <= 0:
        raise PDArrayError(
            "pd_arrays.maximum_tracking_bars must be > 0."
        )

    objects = _creation_objects(
        frame
    )

    rows: list[
        dict[str, Any]
    ] = []

    for item in objects:
        creation_index = int(
            item["creation_index"]
        )

        direction = str(
            item[
                "original_direction"
            ]
        )

        lower = float(
            item["lower_bound"]
        )

        upper = float(
            item["upper_bound"]
        )

        respect_at = pd.NaT
        disrespect_at = pd.NaT

        ifvg_created_at = pd.NaT
        ifvg_direction: str | None = None

        ifvg_respect_at = pd.NaT
        ifvg_disrespect_at = pd.NaT

        end_index = min(
            len(frame) - 1,
            creation_index
            + maximum_tracking_bars,
        )

        inversion_index: int | None = None

        # ----------------------------------------------------
        # ORIGINAL FVG
        # ----------------------------------------------------

        for i in range(
            creation_index + 1,
            end_index + 1,
        ):
            row = frame.iloc[i]

            high = float(
                row["high"]
            )

            low = float(
                row["low"]
            )

            close = float(
                row["close"]
            )

            touches = _touches_zone(
                high=high,
                low=low,
                lower=lower,
                upper=upper,
            )

            if direction == "bullish":
                disrespected = (
                    close < lower
                )

                respected = (
                    touches
                    and close > lower
                )
            else:
                disrespected = (
                    close > upper
                )

                respected = (
                    touches
                    and close < upper
                )

            # A close through the far side has priority.
            if disrespected:
                disrespect_at = (
                    _known_at(
                        frame,
                        i,
                    )
                )

                ifvg_created_at = (
                    disrespect_at
                )

                ifvg_direction = (
                    _opposite(
                        direction
                    )
                )

                inversion_index = i
                break

            if (
                respected
                and pd.isna(
                    respect_at
                )
            ):
                respect_at = (
                    _known_at(
                        frame,
                        i,
                    )
                )

        # ----------------------------------------------------
        # INVERSE FVG
        # ----------------------------------------------------

        if (
            inversion_index
            is not None
            and ifvg_direction
            is not None
        ):
            for i in range(
                inversion_index + 1,
                end_index + 1,
            ):
                row = frame.iloc[i]

                high = float(
                    row["high"]
                )

                low = float(
                    row["low"]
                )

                close = float(
                    row["close"]
                )

                touches = (
                    _touches_zone(
                        high=high,
                        low=low,
                        lower=lower,
                        upper=upper,
                    )
                )

                if (
                    ifvg_direction
                    == "bullish"
                ):
                    disrespected = (
                        close < lower
                    )

                    respected = (
                        touches
                        and close > lower
                    )
                else:
                    disrespected = (
                        close > upper
                    )

                    respected = (
                        touches
                        and close < upper
                    )

                if disrespected:
                    ifvg_disrespect_at = (
                        _known_at(
                            frame,
                            i,
                        )
                    )
                    break

                if (
                    respected
                    and pd.isna(
                        ifvg_respect_at
                    )
                ):
                    ifvg_respect_at = (
                        _known_at(
                            frame,
                            i,
                        )
                    )

        if pd.notna(
            disrespect_at
        ):
            original_state = (
                "disrespected"
            )
        elif pd.notna(
            respect_at
        ):
            original_state = (
                "respected"
            )
        else:
            original_state = (
                "active"
            )

        if (
            ifvg_direction
            is None
        ):
            ifvg_state = "none"

        elif pd.notna(
            ifvg_disrespect_at
        ):
            ifvg_state = (
                "disrespected"
            )

        elif pd.notna(
            ifvg_respect_at
        ):
            ifvg_state = (
                "respected"
            )

        else:
            ifvg_state = "active"

        if ifvg_state != "none":
            current_state = (
                f"ifvg_{ifvg_state}"
            )
        else:
            current_state = (
                f"fvg_{original_state}"
            )

        rows.append(
            {
                **item,
                "original_state": original_state,
                "respect_at": respect_at,
                "disrespect_at": disrespect_at,
                "ifvg_created_at": ifvg_created_at,
                "ifvg_direction": ifvg_direction,
                "ifvg_state": ifvg_state,
                "ifvg_respect_at": ifvg_respect_at,
                "ifvg_disrespect_at": ifvg_disrespect_at,
                "current_state": current_state,
            }
        )

    columns = [
        "pd_array_id",
        "creation_index",
        "original_direction",
        "lower_bound",
        "upper_bound",
        "midpoint",
        "created_at",
        "session_date",
        "original_state",
        "respect_at",
        "disrespect_at",
        "ifvg_created_at",
        "ifvg_direction",
        "ifvg_state",
        "ifvg_respect_at",
        "ifvg_disrespect_at",
        "current_state",
    ]

    if not rows:
        return pd.DataFrame(
            columns=columns
        )

    result = pd.DataFrame(
        rows
    )

    timestamp_columns = [
        "created_at",
        "respect_at",
        "disrespect_at",
        "ifvg_created_at",
        "ifvg_respect_at",
        "ifvg_disrespect_at",
    ]

    for column in timestamp_columns:
        result[column] = (
            pd.to_datetime(
                result[column],
                utc=True,
            )
        )

    return (
        result[
            columns
        ]
        .sort_values(
            [
                "created_at",
                "pd_array_id",
            ],
            kind="stable",
        )
        .reset_index(drop=True)
    )


def build_pd_array_event_table(
    lifecycle: pd.DataFrame,
) -> pd.DataFrame:
    """Convert lifecycle objects to an explicit state-change event stream."""

    columns = [
        "event_at",
        "pd_array_id",
        "event_type",
        "original_direction",
        "evidence_direction",
        "lower_bound",
        "upper_bound",
        "midpoint",
        "session_date",
    ]

    if lifecycle.empty:
        return pd.DataFrame(
            columns=columns
        )

    events: list[
        dict[str, Any]
    ] = []

    for _, row in (
        lifecycle.iterrows()
    ):
        original_direction = str(
            row[
                "original_direction"
            ]
        )

        inverse_direction = (
            row.get(
                "ifvg_direction"
            )
        )

        base = {
            "pd_array_id": row[
                "pd_array_id"
            ],
            "original_direction": original_direction,
            "lower_bound": float(
                row[
                    "lower_bound"
                ]
            ),
            "upper_bound": float(
                row[
                    "upper_bound"
                ]
            ),
            "midpoint": float(
                row["midpoint"]
            ),
            "session_date": row.get(
                "session_date"
            ),
        }

        def add(
            *,
            event_at: Any,
            event_type: str,
            evidence_direction: str,
        ) -> None:
            if pd.isna(event_at):
                return

            events.append(
                {
                    **base,
                    "event_at": pd.Timestamp(
                        event_at
                    ),
                    "event_type": event_type,
                    "evidence_direction": evidence_direction,
                }
            )

        add(
            event_at=row["created_at"],
            event_type="fvg_created",
            evidence_direction=original_direction,
        )

        add(
            event_at=row["respect_at"],
            event_type="fvg_respected",
            evidence_direction=original_direction,
        )

        add(
            event_at=row[
                "disrespect_at"
            ],
            event_type="fvg_disrespected",
            evidence_direction=_opposite(
                original_direction
            ),
        )

        if (
            inverse_direction
            is not None
            and not pd.isna(
                inverse_direction
            )
        ):
            inverse_direction = str(
                inverse_direction
            )

            add(
                event_at=row[
                    "ifvg_created_at"
                ],
                event_type="ifvg_created",
                evidence_direction=inverse_direction,
            )

            add(
                event_at=row[
                    "ifvg_respect_at"
                ],
                event_type="ifvg_respected",
                evidence_direction=inverse_direction,
            )

            add(
                event_at=row[
                    "ifvg_disrespect_at"
                ],
                event_type="ifvg_disrespected",
                evidence_direction=original_direction,
            )

    if not events:
        return pd.DataFrame(
            columns=columns
        )

    result = pd.DataFrame(
        events
    )

    result[
        "event_at"
    ] = pd.to_datetime(
        result["event_at"],
        utc=True,
    )

    return (
        result[
            columns
        ]
        .sort_values(
            [
                "event_at",
                "pd_array_id",
                "event_type",
            ],
            kind="stable",
        )
        .reset_index(drop=True)
    )


def attach_pd_array_context(
    dataframe: pd.DataFrame,
    lifecycle: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Attach causal PD-array state-change context to completed bars."""

    _validate(dataframe)

    result = (
        dataframe
        .sort_values(
            "timestamp",
            kind="stable",
        )
        .copy()
        .reset_index(drop=True)
    )

    section = config.get(
        "pd_arrays",
        {},
    )

    lookback = int(
        section.get(
            "recent_context_bars",
            10,
        )
    )

    if lookback <= 0:
        raise PDArrayError(
            "pd_arrays.recent_context_bars must be > 0."
        )

    event_columns = [
        "bullish_pd_array_respect_event",
        "bearish_pd_array_respect_event",
        "bullish_pd_array_disrespect_event",
        "bearish_pd_array_disrespect_event",
        "bullish_ifvg_created_event",
        "bearish_ifvg_created_event",
        "bullish_ifvg_respect_event",
        "bearish_ifvg_respect_event",
        "bullish_ifvg_disrespect_event",
        "bearish_ifvg_disrespect_event",
    ]

    for column in event_columns:
        result[column] = False

    result[
        "pd_array_last_event"
    ] = None

    result[
        "pd_array_last_event_at"
    ] = pd.NaT

    result[
        "pd_array_last_evidence_direction"
    ] = None

    events = (
        build_pd_array_event_table(
            lifecycle
        )
    )

    if "available_at" in result.columns:
        known_times = pd.to_datetime(
            result["available_at"],
            utc=True,
        )
    else:
        known_times = (
            pd.to_datetime(
                result["timestamp"],
                utc=True,
            )
            + pd.Timedelta(minutes=1)
        )

    lookup: dict[
        pd.Timestamp,
        list[int],
    ] = {}

    for i, value in enumerate(
        known_times
    ):
        lookup.setdefault(
            pd.Timestamp(value),
            [],
        ).append(i)

    for _, event in (
        events.iterrows()
    ):
        event_at = pd.Timestamp(
            event["event_at"]
        )

        indices = lookup.get(
            event_at,
            [],
        )

        if not indices:
            continue

        event_type = str(
            event["event_type"]
        )

        original = str(
            event[
                "original_direction"
            ]
        )

        evidence = str(
            event[
                "evidence_direction"
            ]
        )

        for index in indices:
            if (
                event_type
                == "fvg_respected"
            ):
                result.at[
                    index,
                    f"{original}_pd_array_respect_event",
                ] = True

            elif (
                event_type
                == "fvg_disrespected"
            ):
                result.at[
                    index,
                    f"{original}_pd_array_disrespect_event",
                ] = True

            elif (
                event_type
                == "ifvg_created"
            ):
                result.at[
                    index,
                    f"{evidence}_ifvg_created_event",
                ] = True

            elif (
                event_type
                == "ifvg_respected"
            ):
                result.at[
                    index,
                    f"{evidence}_ifvg_respect_event",
                ] = True

            elif (
                event_type
                == "ifvg_disrespected"
            ):
                inverse_direction = (
                    _opposite(
                        evidence
                    )
                )

                result.at[
                    index,
                    f"{inverse_direction}_ifvg_disrespect_event",
                ] = True

            result.at[
                index,
                "pd_array_last_event",
            ] = event_type

            result.at[
                index,
                "pd_array_last_event_at",
            ] = event_at

            result.at[
                index,
                "pd_array_last_evidence_direction",
            ] = evidence

    recent_definitions = {
        "bullish_pd_array_respected_recent":
            "bullish_pd_array_respect_event",
        "bearish_pd_array_respected_recent":
            "bearish_pd_array_respect_event",
        "bullish_pd_array_disrespected_recent":
            "bullish_pd_array_disrespect_event",
        "bearish_pd_array_disrespected_recent":
            "bearish_pd_array_disrespect_event",
        "bullish_ifvg_created_recent":
            "bullish_ifvg_created_event",
        "bearish_ifvg_created_recent":
            "bearish_ifvg_created_event",
        "bullish_ifvg_respected_recent":
            "bullish_ifvg_respect_event",
        "bearish_ifvg_respected_recent":
            "bearish_ifvg_respect_event",
        "bullish_ifvg_disrespected_recent":
            "bullish_ifvg_disrespect_event",
        "bearish_ifvg_disrespected_recent":
            "bearish_ifvg_disrespect_event",
    }

    for target, source in (
        recent_definitions.items()
    ):
        result[target] = (
            result[source]
            .astype(int)
            .rolling(
                window=lookback,
                min_periods=1,
            )
            .max()
            .astype(bool)
        )

    bullish_support = (
        result[
            "bullish_pd_array_respected_recent"
        ]
        | result[
            "bullish_ifvg_respected_recent"
        ]
    )

    bearish_support = (
        result[
            "bearish_pd_array_respected_recent"
        ]
        | result[
            "bearish_ifvg_respected_recent"
        ]
    )

    context = np.full(
        len(result),
        "neutral",
        dtype=object,
    )

    context[
        bullish_support
        & ~bearish_support
    ] = "bullish"

    context[
        bearish_support
        & ~bullish_support
    ] = "bearish"

    context[
        bullish_support
        & bearish_support
    ] = "conflict"

    result[
        "pd_array_directional_context"
    ] = context

    result[
        "pd_array_last_event"
    ] = result[
        "pd_array_last_event"
    ].ffill()

    result[
        "pd_array_last_event_at"
    ] = pd.to_datetime(
        result[
            "pd_array_last_event_at"
        ],
        utc=True,
    ).ffill()

    result[
        "pd_array_last_evidence_direction"
    ] = result[
        "pd_array_last_evidence_direction"
    ].ffill()

    return result


def enrich_pd_array_features(
    dataframe: pd.DataFrame,
    config: Mapping[str, Any],
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    """Production entry point."""

    section = config.get(
        "pd_arrays",
        {},
    )

    if not bool(
        section.get(
            "enabled",
            True,
        )
    ):
        return (
            dataframe.copy(),
            pd.DataFrame(),
        )

    lifecycle = (
        build_pd_array_lifecycle(
            dataframe,
            config,
        )
    )

    enriched = (
        attach_pd_array_context(
            dataframe,
            lifecycle,
            config,
        )
    )

    return enriched, lifecycle


def pd_array_summary(
    dataframe: pd.DataFrame,
    lifecycle: pd.DataFrame,
) -> PDArraySummary:
    def count(
        column: str,
    ) -> int:
        if (
            lifecycle.empty
            or column
            not in lifecycle.columns
        ):
            return 0

        return int(
            lifecycle[
                column
            ].notna().sum()
        )

    return PDArraySummary(
        rows=len(dataframe),
        objects=len(lifecycle),
        original_respects=count(
            "respect_at"
        ),
        original_disrespects=count(
            "disrespect_at"
        ),
        ifvgs_created=count(
            "ifvg_created_at"
        ),
        ifvg_respects=count(
            "ifvg_respect_at"
        ),
        ifvg_disrespects=count(
            "ifvg_disrespect_at"
        ),
    )


def save_pd_array_outputs(
    dataframe: pd.DataFrame,
    lifecycle: pd.DataFrame,
    output_directory: str | Path,
) -> dict[str, Path]:
    directory = Path(
        output_directory
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    feature_path = (
        directory
        / "nq_1m_pd_arrays.parquet"
    )

    lifecycle_path = (
        directory
        / "pd_array_lifecycle.csv"
    )

    event_path = (
        directory
        / "pd_array_events.csv"
    )

    dataframe.to_parquet(
        feature_path,
        index=False,
    )

    lifecycle.to_csv(
        lifecycle_path,
        index=False,
    )

    build_pd_array_event_table(
        lifecycle
    ).to_csv(
        event_path,
        index=False,
    )

    return {
        "pd_array_features":
            feature_path,
        "pd_array_lifecycle":
            lifecycle_path,
        "pd_array_events":
            event_path,
    }
