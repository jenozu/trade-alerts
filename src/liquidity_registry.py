from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd


class LiquidityRegistryError(RuntimeError):
    """Raised when causal liquidity-pool state cannot be built safely."""


REQUIRED_COLUMNS = {
    "timestamp",
    "high",
    "low",
    "close",
}


DEFAULT_IMPORTANCE = {
    "pdh": 5.0,
    "pdl": 5.0,
    "pmh": 4.0,
    "pml": 4.0,
    "onh": 4.0,
    "onl": 4.0,
    "loh": 3.0,
    "lol": 3.0,
    "ash": 3.0,
    "asl": 3.0,
    "week_high": 5.0,
    "week_low": 5.0,
    "internal_swing_high": 2.5,
    "internal_swing_low": 2.5,
    "external_swing_high": 4.0,
    "external_swing_low": 4.0,
    "internal_equal_high": 4.0,
    "internal_equal_low": 4.0,
    "external_equal_high": 5.0,
    "external_equal_low": 5.0,
}


STATIC_SOURCES = (
    ("pdh", "buy", "1d"),
    ("pdl", "sell", "1d"),
    ("pmh", "buy", "session"),
    ("pml", "sell", "session"),
    ("onh", "buy", "session"),
    ("onl", "sell", "session"),
    ("loh", "buy", "session"),
    ("lol", "sell", "session"),
    ("ash", "buy", "session"),
    ("asl", "sell", "session"),
    ("week_high", "buy", "1w"),
    ("week_low", "sell", "1w"),
)


@dataclass
class LiquidityPool:
    pool_id: str
    source: str
    side: str
    level: float
    timeframe: str
    session_key: str
    created_at: pd.Timestamp
    importance_score: float
    importance_components: str

    state: str = "untouched"

    approached_at: pd.Timestamp | None = None
    swept_at: pd.Timestamp | None = None
    broken_at: pd.Timestamp | None = None
    reclaimed_at: pd.Timestamp | None = None
    invalidated_at: pd.Timestamp | None = None


def _validate(dataframe: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(dataframe.columns)

    if missing:
        raise LiquidityRegistryError(
            f"Missing required columns: {sorted(missing)}"
        )

    if dataframe.empty:
        raise LiquidityRegistryError(
            "Cannot build liquidity registry from an empty dataframe."
        )

    if not pd.api.types.is_datetime64_any_dtype(
        dataframe["timestamp"]
    ):
        raise LiquidityRegistryError(
            "'timestamp' must be datetime."
        )

    if getattr(dataframe["timestamp"].dt, "tz", None) is None:
        raise LiquidityRegistryError(
            "'timestamp' must be timezone-aware."
        )


def _known_at(row: pd.Series) -> pd.Timestamp:
    value = row.get("available_at")

    if pd.notna(value):
        return pd.Timestamp(value)

    return pd.Timestamp(row["timestamp"]) + pd.Timedelta(minutes=1)


def _session_key(
    row: pd.Series,
    *,
    source: str,
) -> str:
    if source in {"week_high", "week_low"}:
        timestamp = pd.Timestamp(row["timestamp"])

        if "timestamp_et" in row and pd.notna(row.get("timestamp_et")):
            timestamp = pd.Timestamp(row["timestamp_et"])
        else:
            timestamp = timestamp.tz_convert(
                "America/New_York"
            )

        iso = timestamp.isocalendar()

        return f"{int(iso.year)}-W{int(iso.week):02d}"

    session_date = row.get("session_date")

    if pd.notna(session_date):
        return str(session_date)

    return str(
        pd.Timestamp(row["timestamp"])
        .tz_convert("America/New_York")
        .date()
    )


def _pool_id(
    *,
    source: str,
    side: str,
    timeframe: str,
    session_key: str,
    identity_key: str,
    level: float,
) -> str:
    raw = (
        f"{source}|{side}|{timeframe}|"
        f"{session_key}|{identity_key}|{level:.8f}"
    )

    digest = hashlib.sha1(
        raw.encode("utf-8")
    ).hexdigest()[:16]

    return f"liq_{digest}"


def _importance(
    *,
    source: str,
    strength_ticks: float | None,
    equal_count: int | None,
    config: Mapping[str, Any],
) -> tuple[float, str]:
    registry = (
        config.get("liquidity", {})
        .get("registry", {})
    )

    importance_config = registry.get(
        "importance",
        {},
    )

    base = float(
        importance_config.get(
            source,
            DEFAULT_IMPORTANCE.get(
                source,
                2.0,
            ),
        )
    )

    strength_bonus = 0.0

    if (
        strength_ticks is not None
        and not pd.isna(strength_ticks)
    ):
        strength_bonus = min(
            2.0,
            max(
                0.0,
                float(strength_ticks) / 8.0,
            ),
        )

    equal_bonus = 0.0

    if equal_count is not None and equal_count >= 2:
        equal_bonus = min(
            2.0,
            0.5 * float(equal_count - 1),
        )

    score = min(
        10.0,
        base + strength_bonus + equal_bonus,
    )

    components = {
        "base": base,
        "strength_bonus": strength_bonus,
        "equal_bonus": equal_bonus,
    }

    return (
        score,
        json.dumps(
            components,
            sort_keys=True,
        ),
    )


def _static_candidates(
    row: pd.Series,
    config: Mapping[str, Any],
) -> Iterable[dict[str, Any]]:
    for source, side, timeframe in STATIC_SOURCES:
        value = row.get(source)

        if pd.isna(value):
            continue

        session_key = _session_key(
            row,
            source=source,
        )

        score, components = _importance(
            source=source,
            strength_ticks=None,
            equal_count=None,
            config=config,
        )

        yield {
            "source": source,
            "side": side,
            "timeframe": timeframe,
            "level": float(value),
            "session_key": session_key,
            "identity_key": session_key,
            "replacement_group": (
                source,
                side,
                timeframe,
            ),
            "importance_score": score,
            "importance_components": components,
        }


def _swing_candidates(
    row: pd.Series,
    config: Mapping[str, Any],
) -> Iterable[dict[str, Any]]:
    for scope in ("internal", "external"):
        for kind, side in (
            ("high", "buy"),
            ("low", "sell"),
        ):
            confirmed_column = (
                f"{scope}_swing_{kind}_confirmed"
            )

            price_column = (
                f"{scope}_swing_{kind}_price"
            )

            timeframe_column = (
                f"{scope}_swing_{kind}_timeframe"
            )

            pivot_time_column = (
                f"{scope}_swing_{kind}_pivot_time"
            )

            strength_column = (
                f"{scope}_swing_{kind}_strength_ticks"
            )

            if bool(
                row.get(
                    confirmed_column,
                    False,
                )
            ):
                price = row.get(price_column)

                if pd.notna(price):
                    timeframe = str(
                        row.get(
                            timeframe_column,
                            "1m",
                        )
                        or "1m"
                    )

                    pivot_time = row.get(
                        pivot_time_column
                    )

                    identity_key = (
                        str(pivot_time)
                        if pd.notna(pivot_time)
                        else str(row["timestamp"])
                    )

                    source = (
                        f"{scope}_swing_{kind}"
                    )

                    score, components = _importance(
                        source=source,
                        strength_ticks=row.get(
                            strength_column
                        ),
                        equal_count=None,
                        config=config,
                    )

                    yield {
                        "source": source,
                        "side": side,
                        "timeframe": timeframe,
                        "level": float(price),
                        "session_key": str(
                            row.get(
                                "session_date",
                                "",
                            )
                        ),
                        "identity_key": identity_key,
                        "replacement_group": (
                            source,
                            side,
                            timeframe,
                        ),
                        "importance_score": score,
                        "importance_components": components,
                    }

            equal_column = (
                f"{scope}_swing_{kind}_equal"
            )

            equal_level_column = (
                f"{scope}_swing_{kind}_equal_cluster_level"
            )

            equal_id_column = (
                f"{scope}_swing_{kind}_equal_cluster_id"
            )

            equal_count_column = (
                f"{scope}_swing_{kind}_equal_cluster_count"
            )

            if bool(
                row.get(
                    equal_column,
                    False,
                )
            ):
                level = row.get(
                    equal_level_column
                )

                cluster_id = row.get(
                    equal_id_column
                )

                if (
                    pd.notna(level)
                    and cluster_id is not None
                ):
                    timeframe = str(
                        row.get(
                            timeframe_column,
                            "1m",
                        )
                        or "1m"
                    )

                    source = (
                        f"{scope}_equal_{kind}"
                    )

                    count_value = row.get(
                        equal_count_column,
                        2,
                    )

                    equal_count = (
                        int(count_value)
                        if pd.notna(count_value)
                        else 2
                    )

                    score, components = _importance(
                        source=source,
                        strength_ticks=row.get(
                            strength_column
                        ),
                        equal_count=equal_count,
                        config=config,
                    )

                    yield {
                        "source": source,
                        "side": side,
                        "timeframe": timeframe,
                        "level": float(level),
                        "session_key": str(
                            row.get(
                                "session_date",
                                "",
                            )
                        ),
                        "identity_key": str(
                            cluster_id
                        ),
                        # Multiple equal-H/L pools can coexist.
                        "replacement_group": None,
                        "importance_score": score,
                        "importance_components": components,
                    }


def _state(pool: LiquidityPool) -> str:
    if pool.invalidated_at is not None:
        return "invalidated"

    if pool.reclaimed_at is not None:
        return "reclaimed"

    if pool.broken_at is not None:
        return "broken"

    if pool.swept_at is not None:
        return "swept"

    if pool.approached_at is not None:
        return "approached"

    return "untouched"


def build_liquidity_registry(
    dataframe: pd.DataFrame,
    config: Mapping[str, Any],
) -> pd.DataFrame:
    """Build deterministic explicit liquidity-pool lifecycle state."""

    _validate(dataframe)

    result = (
        dataframe
        .sort_values("timestamp")
        .copy()
        .reset_index(drop=True)
    )

    liquidity_config = config.get(
        "liquidity",
        {},
    )

    sweep_config = liquidity_config.get(
        "sweep",
        {},
    )

    registry_config = liquidity_config.get(
        "registry",
        {},
    )

    tick_size = float(
        config.get(
            "market",
            {},
        ).get(
            "tick_size",
            0.25,
        )
    )

    if tick_size <= 0:
        raise LiquidityRegistryError(
            "market.tick_size must be > 0."
        )

    penetration_ticks = float(
        sweep_config.get(
            "minimum_penetration_ticks",
            1.0,
        )
    )

    penetration = (
        penetration_ticks
        * tick_size
    )

    require_close_back = bool(
        sweep_config.get(
            "require_close_back_through_level",
            True,
        )
    )

    approach_ticks = float(
        registry_config.get(
            "approach_ticks",
            4.0,
        )
    )

    break_ticks = float(
        registry_config.get(
            "break_ticks",
            1.0,
        )
    )

    approach_distance = (
        approach_ticks * tick_size
    )

    break_distance = (
        break_ticks * tick_size
    )

    pools: dict[
        str,
        LiquidityPool,
    ] = {}

    active_ids: set[str] = set()

    active_replacement_groups: dict[
        tuple[str, str, str],
        str,
    ] = {}

    for _, row in result.iterrows():
        event_at = _known_at(row)

        candidates = list(
            _static_candidates(
                row,
                config,
            )
        )

        candidates.extend(
            _swing_candidates(
                row,
                config,
            )
        )

        for candidate in candidates:
            pool_id = _pool_id(
                source=candidate["source"],
                side=candidate["side"],
                timeframe=candidate["timeframe"],
                session_key=candidate["session_key"],
                identity_key=candidate[
                    "identity_key"
                ],
                level=candidate["level"],
            )

            if pool_id in pools:
                continue

            replacement_group = candidate[
                "replacement_group"
            ]

            if replacement_group is not None:
                previous_id = (
                    active_replacement_groups.get(
                        replacement_group
                    )
                )

                if (
                    previous_id is not None
                    and previous_id in active_ids
                ):
                    previous = pools[
                        previous_id
                    ]

                    previous.invalidated_at = (
                        event_at
                    )

                    previous.state = _state(
                        previous
                    )

                    active_ids.discard(
                        previous_id
                    )

                active_replacement_groups[
                    replacement_group
                ] = pool_id

            pool = LiquidityPool(
                pool_id=pool_id,
                source=candidate["source"],
                side=candidate["side"],
                level=candidate["level"],
                timeframe=candidate[
                    "timeframe"
                ],
                session_key=candidate[
                    "session_key"
                ],
                created_at=event_at,
                importance_score=candidate[
                    "importance_score"
                ],
                importance_components=candidate[
                    "importance_components"
                ],
            )

            pools[pool_id] = pool
            active_ids.add(pool_id)

        high = float(row["high"])
        low = float(row["low"])
        close = float(row["close"])

        for pool_id in list(active_ids):
            pool = pools[pool_id]
            level = pool.level

            if pool.approached_at is None:
                if pool.side == "buy":
                    approached = (
                        high
                        >= level
                        - approach_distance
                    )
                else:
                    approached = (
                        low
                        <= level
                        + approach_distance
                    )

                if approached:
                    pool.approached_at = (
                        event_at
                    )

            if pool.swept_at is None:
                if pool.side == "buy":
                    penetrated = (
                        high
                        >= level
                        + penetration
                    )

                    rejected = (
                        close < level
                        if require_close_back
                        else penetrated
                    )
                else:
                    penetrated = (
                        low
                        <= level
                        - penetration
                    )

                    rejected = (
                        close > level
                        if require_close_back
                        else penetrated
                    )

                if penetrated and rejected:
                    pool.swept_at = (
                        event_at
                    )

            if pool.broken_at is None:
                if pool.side == "buy":
                    broken = (
                        close
                        >= level
                        + break_distance
                    )
                else:
                    broken = (
                        close
                        <= level
                        - break_distance
                    )

                if broken:
                    pool.broken_at = (
                        event_at
                    )

            elif (
                pool.reclaimed_at is None
                and event_at > pool.broken_at
            ):
                if pool.side == "buy":
                    reclaimed = (
                        close < level
                    )
                else:
                    reclaimed = (
                        close > level
                    )

                if reclaimed:
                    pool.reclaimed_at = (
                        event_at
                    )

            pool.state = _state(pool)

    rows: list[dict[str, Any]] = []

    for pool in pools.values():
        pool.state = _state(pool)

        row = asdict(pool)

        rows.append(row)

    columns = [
        "pool_id",
        "source",
        "side",
        "level",
        "timeframe",
        "session_key",
        "created_at",
        "importance_score",
        "importance_components",
        "state",
        "approached_at",
        "swept_at",
        "broken_at",
        "reclaimed_at",
        "invalidated_at",
    ]

    if not rows:
        return pd.DataFrame(
            columns=columns
        )

    registry = pd.DataFrame(rows)

    return (
        registry
        .sort_values(
            [
                "created_at",
                "pool_id",
            ],
            kind="stable",
        )
        .reset_index(drop=True)
    )
