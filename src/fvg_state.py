from __future__ import annotations

import json
from typing import Any, Mapping

import numpy as np
import pandas as pd

from fvg import (
    FVGSettings,
    build_fvg_settings,
    build_fvg_table,
    calculate_fill_percentage,
    detect_fvg_creation,
    validate_input_dataframe,
)


class FVGStateError(RuntimeError):
    """Raised when production FVG state cannot be built safely."""


_TIMEFRAME_MINUTES = {
    "1m": 1,
    "2m": 2,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 1440,
}

_HTF_TIMEFRAMES = {
    "15m",
    "30m",
    "1h",
    "4h",
    "1d",
}


def _duration(timeframe: str) -> pd.Timedelta:
    if timeframe not in _TIMEFRAME_MINUTES:
        raise FVGStateError(
            f"Unsupported timeframe: {timeframe}"
        )

    return pd.Timedelta(
        minutes=_TIMEFRAME_MINUTES[timeframe]
    )


def _prepare(
    dataframe: pd.DataFrame,
    timeframe: str,
) -> pd.DataFrame:
    validate_input_dataframe(dataframe)

    result = (
        dataframe
        .sort_values("timestamp")
        .copy()
        .reset_index(drop=True)
    )

    if "bar_complete" in result.columns:
        result = (
            result.loc[
                result["bar_complete"]
                .fillna(False)
                .astype(bool)
            ]
            .copy()
            .reset_index(drop=True)
        )

    if result.empty:
        return result

    if "available_at" in result.columns:
        result["available_at"] = pd.to_datetime(
            result["available_at"],
            utc=True,
        )
    else:
        result["available_at"] = (
            result["timestamp"]
            + _duration(timeframe)
        )

    return result


def _atr(
    dataframe: pd.DataFrame,
    *,
    timeframe: str,
    period: int,
) -> pd.Series:
    preferred = [
        f"atr_{timeframe}",
        "atr_1m",
        "atr",
    ]

    for column in preferred:
        if column in dataframe.columns:
            values = pd.to_numeric(
                dataframe[column],
                errors="coerce",
            )

            if values.notna().any():
                return values

    previous_close = dataframe[
        "close"
    ].shift(1)

    true_range = pd.concat(
        [
            dataframe["high"]
            - dataframe["low"],
            (
                dataframe["high"]
                - previous_close
            ).abs(),
            (
                dataframe["low"]
                - previous_close
            ).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return true_range.rolling(
        period,
        min_periods=period,
    ).mean()


def _structure_context(
    row: pd.Series,
) -> str:
    checks = [
        (
            "bullish_mss",
            "bullish_mss",
        ),
        (
            "bearish_mss",
            "bearish_mss",
        ),
        (
            "bullish_bos",
            "bullish_bos",
        ),
        (
            "bearish_bos",
            "bearish_bos",
        ),
        (
            "bullish_choch",
            "bullish_choch",
        ),
        (
            "bearish_choch",
            "bearish_choch",
        ),
    ]

    for column, label in checks:
        if bool(
            row.get(
                column,
                False,
            )
        ):
            return label

    return "none"


def _displacement_context(
    row: pd.Series,
) -> tuple[float, str, str]:
    score = row.get(
        "displacement_score",
        np.nan,
    )

    category = row.get(
        "displacement_category",
        "unknown",
    )

    direction = row.get(
        "displacement_direction",
        "neutral",
    )

    if pd.isna(score):
        bullish = row.get(
            "bullish_displacement_score",
            np.nan,
        )

        bearish = row.get(
            "bearish_displacement_score",
            np.nan,
        )

        candidates = [
            value
            for value in (
                bullish,
                bearish,
            )
            if pd.notna(value)
        ]

        score = (
            max(candidates)
            if candidates
            else np.nan
        )

    return (
        float(score)
        if pd.notna(score)
        else np.nan,
        str(category),
        str(direction),
    )


def track_fvg_lifecycle_fast(
    dataframe: pd.DataFrame,
    fvg_table: pd.DataFrame,
    *,
    settings: FVGSettings,
    timeframe: str,
) -> pd.DataFrame:
    """Array-backed lifecycle tracker.

    This preserves legacy lifecycle semantics while avoiding repeated
    DataFrame iloc/at access inside the inner loop.

    Event timestamps use bar availability, not bar-open time.
    """

    if fvg_table.empty:
        return fvg_table.copy()

    tracked = fvg_table.copy()

    n_objects = len(tracked)

    tracked["first_touch_time"] = pd.NaT
    tracked["first_touch_index"] = np.nan
    tracked["maximum_fill_percentage"] = 0.0
    tracked["full_fill_time"] = pd.NaT
    tracked["retest_hold_time"] = pd.NaT
    tracked["invalidated"] = False
    tracked["invalidation_time"] = pd.NaT
    tracked["inverse_fvg_created"] = False
    tracked["inverse_fvg_time"] = pd.NaT
    tracked["fill_history_json"] = "[]"

    highs = dataframe[
        "high"
    ].to_numpy(
        dtype=float,
    )

    lows = dataframe[
        "low"
    ].to_numpy(
        dtype=float,
    )

    closes = dataframe[
        "close"
    ].to_numpy(
        dtype=float,
    )

    if "available_at" in dataframe.columns:
        known_times = pd.to_datetime(
            dataframe["available_at"],
            utc=True,
        ).tolist()
    else:
        known_times = (
            dataframe["timestamp"]
            + _duration(timeframe)
        ).tolist()

    for object_index in range(n_objects):
        fvg = tracked.iloc[
            object_index
        ]

        direction = str(
            fvg["direction"]
        )

        creation_index = int(
            fvg["creation_index"]
        )

        lower = float(
            fvg["lower_bound"]
        )

        upper = float(
            fvg["upper_bound"]
        )

        max_fill = 0.0
        first_touch_recorded = False
        history: list[
            dict[str, Any]
        ] = []

        end_index = min(
            len(dataframe) - 1,
            creation_index
            + settings.maximum_bars_after_creation,
        )

        for i in range(
            creation_index + 1,
            end_index + 1,
        ):
            fill = calculate_fill_percentage(
                direction=direction,
                lower_bound=lower,
                upper_bound=upper,
                bar_high=highs[i],
                bar_low=lows[i],
            )

            event_time = pd.Timestamp(
                known_times[i]
            )

            if fill > 0:
                history.append(
                    {
                        "available_at": (
                            event_time.isoformat()
                        ),
                        "fill": float(fill),
                    }
                )

            if fill > max_fill:
                max_fill = fill

            if (
                fill > 0
                and not first_touch_recorded
            ):
                tracked.at[
                    tracked.index[
                        object_index
                    ],
                    "first_touch_time",
                ] = event_time

                tracked.at[
                    tracked.index[
                        object_index
                    ],
                    "first_touch_index",
                ] = i

                first_touch_recorded = True

            if (
                settings.retest_enabled
                and fill > 0
                and pd.isna(
                    tracked.at[
                        tracked.index[
                            object_index
                        ],
                        "retest_hold_time",
                    ]
                )
            ):
                if direction == "bullish":
                    held = (
                        closes[i] > lower
                        if settings.require_close_hold
                        else True
                    )
                else:
                    held = (
                        closes[i] < upper
                        if settings.require_close_hold
                        else True
                    )

                if held:
                    tracked.at[
                        tracked.index[
                            object_index
                        ],
                        "retest_hold_time",
                    ] = event_time

            if (
                fill
                >= settings.full_fill_percentage
                and pd.isna(
                    tracked.at[
                        tracked.index[
                            object_index
                        ],
                        "full_fill_time",
                    ]
                )
            ):
                tracked.at[
                    tracked.index[
                        object_index
                    ],
                    "full_fill_time",
                ] = event_time

                if (
                    settings.invalidate_on_full_fill
                ):
                    tracked.at[
                        tracked.index[
                            object_index
                        ],
                        "invalidated",
                    ] = True

                    tracked.at[
                        tracked.index[
                            object_index
                        ],
                        "invalidation_time",
                    ] = event_time

            if settings.inverse_fvg_enabled:
                if direction == "bullish":
                    inverse = (
                        closes[i] < lower
                        if settings.require_close_through_original_fvg
                        else lows[i] < lower
                    )
                else:
                    inverse = (
                        closes[i] > upper
                        if settings.require_close_through_original_fvg
                        else highs[i] > upper
                    )

                if (
                    inverse
                    and not bool(
                        tracked.at[
                            tracked.index[
                                object_index
                            ],
                            "inverse_fvg_created",
                        ]
                    )
                ):
                    tracked.at[
                        tracked.index[
                            object_index
                        ],
                        "inverse_fvg_created",
                    ] = True

                    tracked.at[
                        tracked.index[
                            object_index
                        ],
                        "inverse_fvg_time",
                    ] = event_time

                    tracked.at[
                        tracked.index[
                            object_index
                        ],
                        "invalidated",
                    ] = True

                    tracked.at[
                        tracked.index[
                            object_index
                        ],
                        "invalidation_time",
                    ] = event_time

                    break

        tracked.at[
            tracked.index[
                object_index
            ],
            "maximum_fill_percentage",
        ] = max_fill

        tracked.at[
            tracked.index[
                object_index
            ],
            "fill_history_json",
        ] = json.dumps(
            history,
            separators=(",", ":"),
        )

    for column in [
        "first_touch_time",
        "full_fill_time",
        "retest_hold_time",
        "invalidation_time",
        "inverse_fvg_time",
    ]:
        tracked[column] = pd.to_datetime(
            tracked[column],
            utc=True,
        )

    return tracked


def build_fvg_objects(
    dataframe: pd.DataFrame,
    config: Mapping[str, Any],
    *,
    timeframe: str,
) -> pd.DataFrame:
    frame = _prepare(
        dataframe,
        timeframe,
    )

    columns = [
        "fvg_id",
        "direction",
        "timeframe",
        "creation_index",
        "creation_time",
        "available_at",
        "lower_bound",
        "upper_bound",
        "midpoint",
        "size_points",
        "size_atr",
        "session_date",
        "first_touch_time",
        "maximum_fill_percentage",
        "mitigation_percentage",
        "full_fill_time",
        "fully_filled",
        "retest_hold_time",
        "invalidated",
        "invalidation_time",
        "inverse_fvg_created",
        "inverse_fvg_time",
        "fill_history_json",
        "sweep_context",
        "displacement_score",
        "displacement_category",
        "displacement_direction",
        "structure_context",
    ]

    if frame.empty:
        return pd.DataFrame(
            columns=columns
        )

    settings = build_fvg_settings(
        dict(config)
    )

    atr_period = int(
        config.get(
            "fvg",
            {},
        ).get(
            "production",
            {},
        ).get(
            "atr_period",
            14,
        )
    )

    frame[
        "_fvg_production_atr"
    ] = _atr(
        frame,
        timeframe=timeframe,
        period=atr_period,
    )

    created = detect_fvg_creation(
        frame,
        settings=settings,
        atr_column="_fvg_production_atr",
    )

    table = build_fvg_table(
        created
    )

    if table.empty:
        return pd.DataFrame(
            columns=columns
        )

    tracked = track_fvg_lifecycle_fast(
        created,
        table,
        settings=settings,
        timeframe=timeframe,
    )

    tracked["timeframe"] = timeframe

    available_values = []
    atr_values = []
    sweep_values = []
    displacement_scores = []
    displacement_categories = []
    displacement_directions = []
    structure_values = []

    for _, fvg in tracked.iterrows():
        creation_index = int(
            fvg["creation_index"]
        )

        creation_row = created.iloc[
            creation_index
        ]

        available_values.append(
            pd.Timestamp(
                creation_row[
                    "available_at"
                ]
            )
        )

        atr_value = creation_row.get(
            "_fvg_production_atr",
            np.nan,
        )

        atr_values.append(
            float(atr_value)
            if pd.notna(atr_value)
            and float(atr_value) > 0
            else np.nan
        )

        sweep_values.append(
            bool(
                creation_row.get(
                    "liquidity_sweep_any",
                    False,
                )
            )
            or bool(
                creation_row.get(
                    "recent_buy_side_sweep",
                    False,
                )
            )
            or bool(
                creation_row.get(
                    "recent_sell_side_sweep",
                    False,
                )
            )
        )

        (
            displacement_score,
            displacement_category,
            displacement_direction,
        ) = _displacement_context(
            creation_row
        )

        displacement_scores.append(
            displacement_score
        )

        displacement_categories.append(
            displacement_category
        )

        displacement_directions.append(
            displacement_direction
        )

        structure_values.append(
            _structure_context(
                creation_row
            )
        )

    tracked["available_at"] = pd.to_datetime(
        available_values,
        utc=True,
    )

    atr_series = pd.Series(
        atr_values,
        index=tracked.index,
        dtype=float,
    )

    tracked["size_atr"] = (
        tracked["size_points"]
        / atr_series.replace(
            0.0,
            np.nan,
        )
    )

    tracked[
        "mitigation_percentage"
    ] = (
        tracked[
            "maximum_fill_percentage"
        ]
        * 100.0
    )

    tracked["fully_filled"] = (
        tracked[
            "full_fill_time"
        ].notna()
    )

    tracked["sweep_context"] = (
        sweep_values
    )

    tracked[
        "displacement_score"
    ] = displacement_scores

    tracked[
        "displacement_category"
    ] = displacement_categories

    tracked[
        "displacement_direction"
    ] = displacement_directions

    tracked[
        "structure_context"
    ] = structure_values

    tracked["fvg_id"] = [
        (
            f"{timeframe}:"
            f"{direction}:"
            f"{pd.Timestamp(time).isoformat()}:"
            f"{index}"
        )
        for index, (
            direction,
            time,
        ) in enumerate(
            zip(
                tracked["direction"],
                tracked["creation_time"],
            ),
            start=1,
        )
    ]

    return tracked[
        columns
    ].copy()


def build_multitimeframe_fvg_objects(
    frames: Mapping[
        str,
        pd.DataFrame,
    ],
    config: Mapping[str, Any],
) -> pd.DataFrame:
    tables = []

    for timeframe, dataframe in (
        frames.items()
    ):
        table = build_fvg_objects(
            dataframe,
            config,
            timeframe=timeframe,
        )

        if not table.empty:
            tables.append(
                table
            )

    if not tables:
        return pd.DataFrame()

    return (
        pd.concat(
            tables,
            ignore_index=True,
            sort=False,
        )
        .sort_values(
            [
                "available_at",
                "timeframe",
                "fvg_id",
            ],
            kind="stable",
        )
        .reset_index(drop=True)
    )


def materialize_fvg_state_as_of(
    objects: pd.DataFrame,
    *,
    as_of: pd.Timestamp,
) -> pd.DataFrame:
    if objects.empty:
        result = objects.copy()
        result["state_as_of"] = pd.Series(
            dtype=object
        )
        result[
            "mitigation_percentage_as_of"
        ] = pd.Series(
            dtype=float
        )
        return result

    as_of = pd.Timestamp(
        as_of
    )

    if as_of.tzinfo is None:
        raise FVGStateError(
            "as_of must be timezone-aware."
        )

    as_of = as_of.tz_convert(
        "UTC"
    )

    visible = objects.loc[
        pd.to_datetime(
            objects["available_at"],
            utc=True,
        )
        <= as_of
    ].copy()

    states = []
    mitigation_values = []

    for _, row in visible.iterrows():
        maximum_fill = 0.0

        history_raw = row.get(
            "fill_history_json",
            "[]",
        )

        try:
            history = json.loads(
                history_raw
            )
        except Exception as exc:
            raise FVGStateError(
                "Invalid FVG fill history."
            ) from exc

        for event in history:
            event_time = pd.Timestamp(
                event["available_at"]
            )

            if (
                event_time.tzinfo is None
            ):
                event_time = (
                    event_time.tz_localize(
                        "UTC"
                    )
                )
            else:
                event_time = (
                    event_time.tz_convert(
                        "UTC"
                    )
                )

            if event_time <= as_of:
                maximum_fill = max(
                    maximum_fill,
                    float(
                        event["fill"]
                    ),
                )

        mitigation_values.append(
            maximum_fill
            * 100.0
        )

        inverse_time = row.get(
            "inverse_fvg_time"
        )

        invalidation_time = row.get(
            "invalidation_time"
        )

        full_fill_time = row.get(
            "full_fill_time"
        )

        inverse_known = (
            pd.notna(inverse_time)
            and pd.Timestamp(
                inverse_time
            )
            <= as_of
        )

        invalidated_known = (
            pd.notna(
                invalidation_time
            )
            and pd.Timestamp(
                invalidation_time
            )
            <= as_of
        )

        filled_known = (
            pd.notna(
                full_fill_time
            )
            and pd.Timestamp(
                full_fill_time
            )
            <= as_of
        )

        if inverse_known:
            state = "ifvg"
        elif invalidated_known:
            state = "invalidated"
        elif filled_known:
            state = "filled"
        elif maximum_fill > 0:
            state = "mitigated"
        else:
            state = "active"

        states.append(
            state
        )

    visible[
        "state_as_of"
    ] = states

    visible[
        "mitigation_percentage_as_of"
    ] = mitigation_values

    return visible.reset_index(
        drop=True
    )


def nearest_fvg_snapshot(
    objects: pd.DataFrame,
    *,
    price: float,
    as_of: pd.Timestamp,
) -> dict[str, Any]:
    state = materialize_fvg_state_as_of(
        objects,
        as_of=as_of,
    )

    active = state.loc[
        state["state_as_of"].isin(
            [
                "active",
                "mitigated",
            ]
        )
    ].copy()

    result: dict[
        str,
        Any,
    ] = {
        "nearest_5m_fvg_above": None,
        "distance_to_nearest_5m_fvg_above": None,
        "nearest_5m_fvg_below": None,
        "distance_to_nearest_5m_fvg_below": None,
        "nearest_htf_fvg_above": None,
        "distance_to_nearest_htf_fvg_above": None,
        "nearest_htf_fvg_below": None,
        "distance_to_nearest_htf_fvg_below": None,
    }

    groups = {
        "5m": active.loc[
            active["timeframe"]
            == "5m"
        ],
        "htf": active.loc[
            active["timeframe"].isin(
                _HTF_TIMEFRAMES
            )
        ],
    }

    for name, frame in groups.items():
        if frame.empty:
            continue

        above = frame.loc[
            frame["lower_bound"]
            > price
        ].copy()

        if not above.empty:
            above["distance"] = (
                above["lower_bound"]
                - price
            )

            row = above.sort_values(
                [
                    "distance",
                    "available_at",
                ],
                kind="stable",
            ).iloc[0]

            result[
                f"nearest_{name}_fvg_above"
            ] = float(
                row["lower_bound"]
            )

            result[
                f"distance_to_nearest_{name}_fvg_above"
            ] = float(
                row["distance"]
            )

        below = frame.loc[
            frame["upper_bound"]
            < price
        ].copy()

        if not below.empty:
            below["distance"] = (
                price
                - below["upper_bound"]
            )

            row = below.sort_values(
                [
                    "distance",
                    "available_at",
                ],
                kind="stable",
            ).iloc[0]

            result[
                f"nearest_{name}_fvg_below"
            ] = float(
                row["upper_bound"]
            )

            result[
                f"distance_to_nearest_{name}_fvg_below"
            ] = float(
                row["distance"]
            )

    return result
