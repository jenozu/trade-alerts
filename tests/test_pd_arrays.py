from __future__ import annotations

import pandas as pd
import pytest

from dol import (
    _directional_score,
    build_dol_settings,
)

from pd_arrays import (
    PDArrayError,
    attach_pd_array_context,
    build_pd_array_event_table,
    build_pd_array_lifecycle,
    enrich_pd_array_features,
)

from run_pipeline import (
    PIPELINE_STAGES,
)

from scorer import (
    fvg_alignment,
)


def _config() -> dict:
    return {
        "pd_arrays": {
            "enabled": True,
            "recent_context_bars": 3,
            "maximum_tracking_bars": 20,
        },
        "draw_on_liquidity": {
            "evidence_weights": {
                "target_available": 1.0,
                "higher_timeframe_bias": 2.0,
                "opposing_liquidity_sweep": 1.5,
                "premium_discount": 1.0,
                "fvg_context": 0.5,
            }
        },
        "room_to_target": {
            "minimum_points": 25.0,
        },
    }


def _frame(
    periods: int = 6,
) -> pd.DataFrame:
    timestamp = pd.date_range(
        "2026-09-01 13:30:00",
        periods=periods,
        freq="1min",
        tz="UTC",
    )

    df = pd.DataFrame(
        {
            "timestamp": timestamp,
            "open": [102.0] * periods,
            "high": [102.5] * periods,
            "low": [101.5] * periods,
            "close": [102.0] * periods,
        }
    )

    df["available_at"] = (
        df["timestamp"]
        + pd.Timedelta(minutes=1)
    )

    df["bullish_fvg_created"] = False
    df["bearish_fvg_created"] = False

    df["bullish_fvg_lower"] = float("nan")
    df["bullish_fvg_upper"] = float("nan")

    df["bearish_fvg_lower"] = float("nan")
    df["bearish_fvg_upper"] = float("nan")

    return df


def _bullish_fvg_frame() -> pd.DataFrame:
    df = _frame()

    # Create bullish FVG [100, 101] at index 0.
    df.loc[
        0,
        "bullish_fvg_created",
    ] = True

    df.loc[
        0,
        "bullish_fvg_lower",
    ] = 100.0

    df.loc[
        0,
        "bullish_fvg_upper",
    ] = 101.0

    # Index 1: touch and hold -> bullish respect.
    df.loc[
        1,
        [
            "high",
            "low",
            "close",
        ],
    ] = [
        101.25,
        100.50,
        100.75,
    ]

    # Index 2: close through lower bound -> disrespect / bearish IFVG.
    df.loc[
        2,
        [
            "high",
            "low",
            "close",
        ],
    ] = [
        100.50,
        99.25,
        99.75,
    ]

    # Index 3: retest inverse zone and hold below upper -> bearish IFVG respect.
    df.loc[
        3,
        [
            "high",
            "low",
            "close",
        ],
    ] = [
        100.60,
        99.50,
        99.80,
    ]

    # Later bars remain below the bearish IFVG upper boundary so this
    # base fixture represents a respected IFVG that stays respected.
    # Tests that need a later disrespect explicitly mutate those bars.
    df.loc[
        4:,
        [
            "high",
            "low",
            "close",
        ],
    ] = [
        [
            100.50,
            99.25,
            99.75,
        ],
        [
            100.40,
            99.20,
            99.70,
        ],
    ]

    return df


def test_rejects_naive_timestamp():
    df = _frame()

    df["timestamp"] = (
        df["timestamp"]
        .dt.tz_localize(None)
    )

    with pytest.raises(
        PDArrayError,
        match="timezone-aware",
    ):
        build_pd_array_lifecycle(
            df,
            _config(),
        )


def test_bullish_fvg_tracks_respect_then_disrespect():
    df = _bullish_fvg_frame()

    lifecycle = (
        build_pd_array_lifecycle(
            df,
            _config(),
        )
    )

    assert len(lifecycle) == 1

    row = lifecycle.iloc[0]

    assert (
        row["original_direction"]
        == "bullish"
    )

    assert pd.notna(
        row["respect_at"]
    )

    assert pd.notna(
        row["disrespect_at"]
    )

    assert (
        row["original_state"]
        == "disrespected"
    )


def test_bullish_fvg_disrespect_creates_bearish_ifvg():
    lifecycle = (
        build_pd_array_lifecycle(
            _bullish_fvg_frame(),
            _config(),
        )
    )

    row = lifecycle.iloc[0]

    assert (
        row["ifvg_direction"]
        == "bearish"
    )

    assert pd.notna(
        row["ifvg_created_at"]
    )


def test_bearish_ifvg_can_be_respected():
    lifecycle = (
        build_pd_array_lifecycle(
            _bullish_fvg_frame(),
            _config(),
        )
    )

    row = lifecycle.iloc[0]

    assert pd.notna(
        row["ifvg_respect_at"]
    )

    assert (
        row["ifvg_state"]
        == "respected"
    )

    assert (
        row["current_state"]
        == "ifvg_respected"
    )


def test_bearish_original_disrespect_creates_bullish_ifvg():
    df = _frame()

    df.loc[
        0,
        "bearish_fvg_created",
    ] = True

    df.loc[
        0,
        "bearish_fvg_lower",
    ] = 99.0

    df.loc[
        0,
        "bearish_fvg_upper",
    ] = 100.0

    # Close above upper bound.
    df.loc[
        1,
        [
            "high",
            "low",
            "close",
        ],
    ] = [
        101.0,
        99.5,
        100.50,
    ]

    lifecycle = (
        build_pd_array_lifecycle(
            df,
            _config(),
        )
    )

    row = lifecycle.iloc[0]

    assert (
        row["ifvg_direction"]
        == "bullish"
    )

    assert pd.notna(
        row["ifvg_created_at"]
    )


def test_ifvg_disrespect_is_timestamped():
    df = _bullish_fvg_frame()

    # After bearish IFVG respect, close above original upper bound.
    df.loc[
        4,
        [
            "high",
            "low",
            "close",
        ],
    ] = [
        101.50,
        100.25,
        101.25,
    ]

    lifecycle = (
        build_pd_array_lifecycle(
            df,
            _config(),
        )
    )

    row = lifecycle.iloc[0]

    assert pd.notna(
        row["ifvg_respect_at"]
    )

    assert pd.notna(
        row["ifvg_disrespect_at"]
    )

    assert (
        row["ifvg_state"]
        == "disrespected"
    )


def test_state_changes_use_bar_available_at():
    df = _bullish_fvg_frame()

    lifecycle = (
        build_pd_array_lifecycle(
            df,
            _config(),
        )
    )

    row = lifecycle.iloc[0]

    assert (
        row["created_at"]
        == df.loc[
            0,
            "available_at",
        ]
    )

    assert (
        row["respect_at"]
        == df.loc[
            1,
            "available_at",
        ]
    )

    assert (
        row["disrespect_at"]
        == df.loc[
            2,
            "available_at",
        ]
    )

    assert (
        row["ifvg_respect_at"]
        == df.loc[
            3,
            "available_at",
        ]
    )


def test_event_table_records_every_lifecycle_transition():
    lifecycle = (
        build_pd_array_lifecycle(
            _bullish_fvg_frame(),
            _config(),
        )
    )

    events = (
        build_pd_array_event_table(
            lifecycle
        )
    )

    types = set(
        events["event_type"]
    )

    assert "fvg_created" in types
    assert "fvg_respected" in types
    assert "fvg_disrespected" in types
    assert "ifvg_created" in types
    assert "ifvg_respected" in types


def test_bar_context_exposes_recent_bullish_pd_array_respect():
    df = _bullish_fvg_frame()

    lifecycle = (
        build_pd_array_lifecycle(
            df,
            _config(),
        )
    )

    enriched = (
        attach_pd_array_context(
            df,
            lifecycle,
            _config(),
        )
    )

    assert bool(
        enriched.loc[
            1,
            "bullish_pd_array_respect_event",
        ]
    )

    assert bool(
        enriched.loc[
            1,
            "bullish_pd_array_respected_recent",
        ]
    )


def test_bar_context_exposes_bearish_ifvg_respect():
    df = _bullish_fvg_frame()

    enriched, _ = (
        enrich_pd_array_features(
            df,
            _config(),
        )
    )

    assert bool(
        enriched.loc[
            3,
            "bearish_ifvg_respect_event",
        ]
    )

    assert (
        enriched.loc[
            3,
            "pd_array_directional_context",
        ]
        in {
            "bearish",
            "conflict",
        }
    )


def test_future_events_do_not_rewrite_past_pd_array_context():
    original = _bullish_fvg_frame()

    prefix = (
        original
        .iloc[:2]
        .copy()
        .reset_index(drop=True)
    )

    prefix_result, _ = (
        enrich_pd_array_features(
            prefix,
            _config(),
        )
    )

    full_result, _ = (
        enrich_pd_array_features(
            original,
            _config(),
        )
    )

    columns = [
        "bullish_pd_array_respect_event",
        "bearish_pd_array_respect_event",
        "bullish_ifvg_respect_event",
        "bearish_ifvg_respect_event",
        "bullish_pd_array_respected_recent",
        "bearish_pd_array_respected_recent",
        "pd_array_directional_context",
        "pd_array_last_event",
        "pd_array_last_event_at",
    ]

    pd.testing.assert_frame_equal(
        prefix_result[
            columns
        ].reset_index(drop=True),
        full_result.loc[
            :1,
            columns,
        ].reset_index(drop=True),
        check_dtype=False,
    )


def test_dol_uses_pd_array_respect_via_existing_fvg_weight():
    settings = (
        build_dol_settings(
            _config()
        )
    )

    row = pd.Series(
        {
            "bullish_pd_array_respected_recent": True,
            "bullish_ifvg_respected_recent": False,
        }
    )

    score, reasons = (
        _directional_score(
            row,
            direction="bullish",
            target=None,
            settings=settings,
        )
    )

    assert score == pytest.approx(
        settings.fvg_context_weight
    )

    assert (
        "bullish_pd_array_respect"
        in reasons
    )


def test_scorer_fvg_component_accepts_pd_array_respect():
    row = pd.Series(
        {
            "bullish_pd_array_respected_recent": True,
        }
    )

    assert fvg_alignment(
        row,
        "long",
    )


def test_pd_arrays_are_between_fvg_and_structure_in_pipeline():
    fvg_index = (
        PIPELINE_STAGES.index(
            "fvg"
        )
    )

    pd_index = (
        PIPELINE_STAGES.index(
            "pd_arrays"
        )
    )

    structure_index = (
        PIPELINE_STAGES.index(
            "structure"
        )
    )

    assert (
        fvg_index
        < pd_index
        < structure_index
    )
