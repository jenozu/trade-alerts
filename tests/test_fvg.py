from __future__ import annotations

import pandas as pd
import pytest

from fvg import (
    FVGError,
    FVGSettings,
    add_nearest_active_fvg,
    attach_fvg_events_to_bars,
    build_fvg_table,
    detect_fvg_creation,
    enrich_fvg_features,
    track_fvg_lifecycle,
)


def _settings(*, maximum_bars_after_creation: int = 20) -> FVGSettings:
    return FVGSettings(
        tick_size=0.25,
        minimum_gap_ticks=1,
        minimum_gap_atr_fraction=0.0,
        require_displacement_candle=False,
        track_first_touch=True,
        track_fill_percentage=True,
        full_fill_percentage=1.0,
        invalidate_on_full_fill=False,
        retest_enabled=True,
        require_close_hold=True,
        maximum_bars_after_creation=maximum_bars_after_creation,
        inverse_fvg_enabled=True,
        require_close_through_original_fvg=True,
    )


def _config(*, maximum_bars_after_creation: int = 20) -> dict:
    return {
        "market": {"tick_size": 0.25},
        "fvg": {
            "enabled": True,
            "detection": {
                "minimum_gap_ticks": 1,
                "minimum_gap_atr_fraction": 0.0,
                "require_displacement_candle": False,
            },
            "mitigation": {
                "track_first_touch": True,
                "track_fill_percentage": True,
                "full_fill_percentage": 1.0,
                "invalidate_on_full_fill": False,
            },
            "retest": {
                "enabled": True,
                "require_close_hold": True,
                "maximum_bars_after_creation": maximum_bars_after_creation,
            },
            "inverse_fvg": {
                "enabled": True,
                "require_close_through_original_fvg": True,
            },
        },
    }


def _bullish_fixture() -> pd.DataFrame:
    """Create one clean bullish FVG, then touch, fill, and invert it.

    Bar 2 creates a bullish FVG from 100.00 to 101.00.
    Bar 3 partially touches/retests it.
    Bar 4 fully fills it but closes back above the lower boundary.
    Bar 5 closes below the lower boundary and creates the inverse FVG event.
    """
    timestamps = pd.date_range(
        "2026-08-31 13:30:00",
        periods=7,
        freq="1min",
        tz="UTC",
    )
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [99.50, 100.25, 101.25, 101.50, 100.75, 100.10, 99.80],
            "high": [100.00, 101.00, 102.50, 102.00, 101.25, 100.40, 100.00],
            "low": [99.00, 100.00, 101.00, 100.75, 99.50, 99.60, 99.40],
            "close": [99.75, 100.75, 102.00, 101.25, 100.25, 99.75, 99.60],
        }
    )


def test_fvg_rejects_naive_timestamps():
    bars = _bullish_fixture().copy()
    bars["timestamp"] = bars["timestamp"].dt.tz_localize(None)

    with pytest.raises(FVGError, match="timezone-aware"):
        detect_fvg_creation(bars, settings=_settings())


def test_three_candle_fvg_is_not_created_before_third_bar():
    created = detect_fvg_creation(_bullish_fixture(), settings=_settings())

    assert not bool(created.loc[0, "bullish_fvg_created"])
    assert not bool(created.loc[1, "bullish_fvg_created"])
    assert bool(created.loc[2, "bullish_fvg_created"])
    assert created.loc[2, "bullish_fvg_lower"] == pytest.approx(100.0)
    assert created.loc[2, "bullish_fvg_upper"] == pytest.approx(101.0)


def test_fvg_table_uses_creation_bar_timestamp_not_an_earlier_bar():
    bars = _bullish_fixture()
    created = detect_fvg_creation(bars, settings=_settings())
    table = build_fvg_table(created)
    bullish = table.loc[table["direction"] == "bullish"].iloc[0]

    assert int(bullish["creation_index"]) == 2
    assert bullish["creation_time"] == bars.loc[2, "timestamp"]


def test_lifecycle_events_begin_only_after_creation_bar():
    bars = _bullish_fixture()
    created = detect_fvg_creation(bars, settings=_settings())
    table = build_fvg_table(created)
    tracked = track_fvg_lifecycle(created, table, settings=_settings())
    bullish = tracked.loc[tracked["direction"] == "bullish"].iloc[0]

    assert bullish["first_touch_time"] == bars.loc[3, "timestamp"]
    assert int(bullish["first_touch_index"]) == 3
    assert bullish["retest_hold_time"] == bars.loc[3, "timestamp"]
    assert bullish["full_fill_time"] == bars.loc[4, "timestamp"]
    assert bullish["inverse_fvg_time"] == bars.loc[5, "timestamp"]
    assert bool(bullish["inverse_fvg_created"])
    assert bool(bullish["invalidated"])


def test_attached_fvg_events_exist_only_on_the_bar_where_the_event_occurs():
    bars = _bullish_fixture()
    created = detect_fvg_creation(bars, settings=_settings())
    table = build_fvg_table(created)
    tracked = track_fvg_lifecycle(created, table, settings=_settings())
    enriched = attach_fvg_events_to_bars(created, tracked)

    assert not enriched.loc[:2, "bullish_fvg_first_touch"].any()
    assert bool(enriched.loc[3, "bullish_fvg_first_touch"])
    assert bool(enriched.loc[3, "bullish_fvg_retest_hold"])

    assert not enriched.loc[:3, "bullish_fvg_full_fill"].any()
    assert bool(enriched.loc[4, "bullish_fvg_full_fill"])

    assert not enriched.loc[:4, "bearish_ifvg_created"].any()
    assert bool(enriched.loc[5, "bearish_ifvg_created"])


def test_original_fvg_is_active_before_invalidation_and_hidden_at_invalidation_bar():
    bars = _bullish_fixture()
    created = detect_fvg_creation(bars, settings=_settings())
    table = build_fvg_table(created)
    tracked = track_fvg_lifecycle(created, table, settings=_settings())
    enriched = add_nearest_active_fvg(created, tracked)

    assert enriched.loc[2, "nearest_active_bullish_fvg_lower"] == pytest.approx(100.0)
    assert enriched.loc[4, "nearest_active_bullish_fvg_lower"] == pytest.approx(100.0)
    assert pd.isna(enriched.loc[5, "nearest_active_bullish_fvg_lower"])


def test_future_bars_do_not_rewrite_past_fvg_features():
    bars = _bullish_fixture()
    prefix = bars.iloc[:4].copy()

    prefix_enriched, _ = enrich_fvg_features(prefix, _config())
    full_enriched, _ = enrich_fvg_features(bars, _config())

    columns = [
        "bullish_fvg_created",
        "bearish_fvg_created",
        "bullish_fvg_lower",
        "bullish_fvg_upper",
        "bullish_fvg_first_touch",
        "bullish_fvg_retest_hold",
        "bullish_fvg_full_fill",
        "bearish_ifvg_created",
        "nearest_active_bullish_fvg_lower",
        "nearest_active_bullish_fvg_upper",
    ]

    pd.testing.assert_frame_equal(
        prefix_enriched[columns].reset_index(drop=True),
        full_enriched.loc[: len(prefix) - 1, columns].reset_index(drop=True),
        check_dtype=False,
    )


def test_lifecycle_tracking_stops_after_configured_maximum_bars():
    bars = _bullish_fixture().copy()

    # Keep bars 3 and 4 completely above the FVG so the first possible touch is
    # bar 5, three bars after creation. With a two-bar lifecycle window it must
    # remain unseen.
    bars.loc[3, ["open", "high", "low", "close"]] = [102.0, 102.5, 101.5, 102.25]
    bars.loc[4, ["open", "high", "low", "close"]] = [102.0, 102.5, 101.5, 102.25]
    bars.loc[5, ["open", "high", "low", "close"]] = [100.75, 101.25, 100.50, 100.75]

    created = detect_fvg_creation(bars, settings=_settings(maximum_bars_after_creation=2))
    table = build_fvg_table(created)
    tracked = track_fvg_lifecycle(
        created,
        table,
        settings=_settings(maximum_bars_after_creation=2),
    )
    bullish = tracked.loc[tracked["direction"] == "bullish"].iloc[0]

    assert pd.isna(bullish["first_touch_time"])
    assert pd.isna(bullish["retest_hold_time"])
    assert pd.isna(bullish["full_fill_time"])
    assert not bool(bullish["inverse_fvg_created"])
