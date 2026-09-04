from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from structure import (
    DisplacementSettings,
    StructureError,
    StructureSettings,
    add_core_sequence_flags,
    add_displacement,
    add_fvg_structure_sequences,
    add_production_setup_sequences,
    add_recent_structure_context,
    classify_structure_events,
    deduplicate_breaks,
    detect_structure_breaks,
    validate_input_dataframe,
)


def _bars(periods: int = 6) -> pd.DataFrame:
    timestamps = pd.date_range(
        "2026-08-31 13:30:00",
        periods=periods,
        freq="1min",
        tz="UTC",
    )
    close = 100.0 + np.arange(periods, dtype=float) * 0.25
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": close - 0.10,
            "high": close + 0.30,
            "low": close - 0.30,
            "close": close,
        }
    )


def _structure_settings() -> StructureSettings:
    return StructureSettings(
        break_method="close",
        break_buffer_points=0.25,
        bos_enabled=True,
        bos_require_confirmed_swing=True,
        mss_enabled=True,
        mss_require_confirmed_swing=True,
        mss_require_prior_liquidity_event=False,
        mss_require_displacement=False,
        choch_enabled=True,
        choch_structure_scope="internal",
        record_wick_breaks=True,
        wick_breaks_count_as_confirmation=False,
    )


def _displacement_settings() -> DisplacementSettings:
    return DisplacementSettings(
        atr_period=1,
        body_lookback=2,
        minimum_body_atr_multiple=0.50,
        minimum_body_median_multiple=1.20,
        close_extreme_fraction=0.25,
        require_directional_close=True,
        relative_volume_confirmation_enabled=False,
        minimum_rvol=1.25,
    )


def test_structure_rejects_naive_timestamps():
    df = _bars(3)
    df["timestamp"] = df["timestamp"].dt.tz_localize(None)

    with pytest.raises(StructureError, match="timezone-aware"):
        validate_input_dataframe(df)


def test_close_break_method_does_not_promote_wick_only_break():
    df = _bars(2)
    df["active_internal_swing_high"] = 101.0
    df["active_internal_swing_low"] = 99.0

    # Wick trades above 101.25, but the close remains below the buffered level.
    df.loc[0, "high"] = 101.50
    df.loc[0, "close"] = 101.00

    result = detect_structure_breaks(df, settings=_structure_settings())

    assert bool(result.loc[0, "bullish_structure_wick_break"])
    assert not bool(result.loc[0, "bullish_structure_close_break"])
    assert not bool(result.loc[0, "bullish_structure_break"])


def test_break_is_emitted_once_per_active_swing_level():
    df = _bars(5)
    df["active_internal_swing_high"] = [101.0, 101.0, 101.0, 102.0, 102.0]
    df["active_internal_swing_low"] = [99.0] * 5
    df["bullish_structure_break"] = [True, True, True, True, True]
    df["bearish_structure_break"] = [False] * 5

    result = deduplicate_breaks(df)

    event_indices = result.index[result["bullish_structure_break_event"]].tolist()
    assert event_indices == [0, 3]


def test_with_trend_break_is_bos_not_mss():
    df = _bars(1)
    df["internal_structure_trend"] = ["bullish"]
    df["bullish_structure_break_event"] = [True]
    df["bearish_structure_break_event"] = [False]
    df["bullish_displacement"] = [False]
    df["bearish_displacement"] = [False]

    result = classify_structure_events(df, settings=_structure_settings())

    assert bool(result.loc[0, "bullish_bos"])
    assert not bool(result.loc[0, "bullish_mss"])
    assert not bool(result.loc[0, "bullish_choch"])


def test_countertrend_break_is_mss_and_choch_not_bos():
    df = _bars(1)
    df["internal_structure_trend"] = ["bearish"]
    df["bullish_structure_break_event"] = [True]
    df["bearish_structure_break_event"] = [False]
    df["bullish_displacement"] = [False]
    df["bearish_displacement"] = [False]

    result = classify_structure_events(df, settings=_structure_settings())

    assert not bool(result.loc[0, "bullish_bos"])
    assert bool(result.loc[0, "bullish_mss"])
    assert bool(result.loc[0, "bullish_choch"])


def test_ordered_sweep_displacement_mss_sequence_becomes_valid_after_mss():
    df = _bars(4)
    # Liquidity sweep occurs first and remains recent while the later events occur.
    df["recent_sell_side_sweep"] = [True, True, True, True]
    df["recent_buy_side_sweep"] = [False, False, False, False]
    df["bullish_displacement"] = [False, True, False, False]
    df["bearish_displacement"] = [False, False, False, False]
    df["bullish_mss"] = [False, False, True, False]
    df["bearish_mss"] = [False, False, False, False]
    df["bullish_bos"] = [False, False, False, False]
    df["bearish_bos"] = [False, False, False, False]
    df["bullish_choch"] = [False, False, False, False]
    df["bearish_choch"] = [False, False, False, False]

    recent = add_recent_structure_context(df, lookback_bars=10)
    result = add_core_sequence_flags(recent)

    assert not bool(result.loc[0, "bullish_core_sequence"])
    assert not bool(result.loc[1, "bullish_core_sequence"])
    assert bool(result.loc[2, "bullish_core_sequence"])


def test_out_of_order_mss_displacement_then_sweep_is_not_a_valid_core_sequence():
    df = _bars(4)
    # Wrong order: MSS -> displacement -> sweep. A rolling-window coincidence is
    # not a causal sweep -> displacement -> MSS sequence.
    df["recent_sell_side_sweep"] = [False, False, True, True]
    df["recent_buy_side_sweep"] = [False, False, False, False]
    df["bullish_displacement"] = [False, True, False, False]
    df["bearish_displacement"] = [False, False, False, False]
    df["bullish_mss"] = [True, False, False, False]
    df["bearish_mss"] = [False, False, False, False]
    df["bullish_bos"] = [False, False, False, False]
    df["bearish_bos"] = [False, False, False, False]
    df["bullish_choch"] = [False, False, False, False]
    df["bearish_choch"] = [False, False, False, False]

    recent = add_recent_structure_context(df, lookback_bars=10)
    result = add_core_sequence_flags(recent)

    assert not result["bullish_core_sequence"].any(), (
        "Out-of-order MSS/displacement/sweep events were incorrectly accepted "
        "as a bullish core sequence"
    )


def test_fvg_that_happened_before_core_sequence_does_not_complete_core_plus_fvg():
    df = _bars(4)
    # FVG exists first, core sequence completes later. The desired sequence is
    # core context first, then FVG/retest confirmation; an older FVG must not be
    # pulled forward by a generic rolling window.
    df["bullish_core_sequence"] = [False, False, True, True]
    df["bearish_core_sequence"] = [False, False, False, False]
    df["bullish_fvg_created"] = [True, False, False, False]
    df["bearish_fvg_created"] = [False, False, False, False]
    df["bullish_fvg_retest_hold"] = [False, False, False, False]
    df["bearish_fvg_retest_hold"] = [False, False, False, False]

    result = add_fvg_structure_sequences(df)

    assert not result["bullish_core_plus_fvg"].any(), (
        "An FVG created before the core sequence was incorrectly treated as a "
        "post-structure confirmation"
    )


def test_reversal_entry_valid_only_after_full_ordered_confirmation():
    df = _bars(6)
    df["bullish_core_plus_fvg_retest"] = [False, False, False, False, True, True]
    df["bearish_core_plus_fvg_retest"] = False

    result = add_production_setup_sequences(df)

    assert result.index[result["bullish_reversal_entry_valid_event"]].tolist() == [4]
    assert result.loc[4:, "bullish_reversal_sequence"].all()
    assert result.loc[4, "entry_valid_direction"] == "bullish"


def test_continuation_requires_displacement_break_then_later_retest_hold():
    df = _bars(5)
    df["bullish_displacement_structure_break_event"] = [False, True, False, False, False]
    df["bearish_displacement_structure_break_event"] = False
    df["bullish_body_close_break_event"] = [False, True, False, False, False]
    df["bullish_fvg_retest_hold"] = [False, False, True, False, False]
    df["bearish_fvg_retest_hold"] = False

    result = add_production_setup_sequences(df)

    assert result.index[result["bullish_continuation_entry_valid_event"]].tolist() == [2]
    assert result.loc[2:, "bullish_continuation_sequence"].all()
    assert result.loc[2, "entry_valid_direction"] == "bullish"


def test_bearish_continuation_uses_the_symmetric_sequence():
    df = _bars(5)
    df["bullish_displacement_structure_break_event"] = False
    df["bearish_displacement_structure_break_event"] = [False, True, False, False, False]
    df["bullish_fvg_retest_hold"] = False
    df["bearish_fvg_retest_hold"] = [False, False, True, False, False]

    result = add_production_setup_sequences(df)

    assert result.index[result["bearish_continuation_entry_valid_event"]].tolist() == [2]
    assert result.loc[2, "entry_valid_direction"] == "bearish"


def test_body_close_only_break_never_becomes_continuation_entry_valid():
    df = _bars(4)
    df["bullish_body_close_break_event"] = [False, True, False, False]
    df["bullish_displacement_structure_break_event"] = False
    df["bearish_displacement_structure_break_event"] = False
    df["bullish_fvg_retest_hold"] = [False, False, True, False]
    df["bearish_fvg_retest_hold"] = False

    result = add_production_setup_sequences(df)

    assert not result["bullish_continuation_sequence"].any()
    assert not result["bullish_continuation_entry_valid_event"].any()
    assert (result["entry_valid_direction"] == "none").all()


def test_same_bar_break_and_retest_is_not_assigned_an_intrabar_order():
    df = _bars(3)
    df["bullish_displacement_structure_break_event"] = [False, True, False]
    df["bearish_displacement_structure_break_event"] = False
    df["bullish_fvg_retest_hold"] = [False, True, False]
    df["bearish_fvg_retest_hold"] = False

    result = add_production_setup_sequences(df)

    assert not result["bullish_continuation_entry_valid_event"].any()


def test_future_rows_do_not_rewrite_production_setup_sequences():
    prefix = _bars(4)
    prefix["bullish_displacement_structure_break_event"] = [False, True, False, False]
    prefix["bearish_displacement_structure_break_event"] = False
    prefix["bullish_fvg_retest_hold"] = [False, False, True, False]
    prefix["bearish_fvg_retest_hold"] = False
    before = add_production_setup_sequences(prefix)

    future = _bars(2)
    future["timestamp"] = pd.date_range(
        prefix["timestamp"].iloc[-1] + pd.Timedelta(minutes=1),
        periods=2,
        freq="1min",
        tz="UTC",
    )
    future["bullish_displacement_structure_break_event"] = [True, False]
    future["bearish_displacement_structure_break_event"] = [False, True]
    future["bullish_fvg_retest_hold"] = [False, True]
    future["bearish_fvg_retest_hold"] = [False, False]
    after = add_production_setup_sequences(
        pd.concat([prefix, future], ignore_index=True)
    )

    columns = [
        "bullish_continuation_sequence",
        "bullish_continuation_entry_valid_event",
        "bearish_continuation_sequence",
        "bearish_continuation_entry_valid_event",
        "entry_valid_direction",
    ]
    pd.testing.assert_frame_equal(
        before[columns],
        after.loc[: len(prefix) - 1, columns].reset_index(drop=True),
    )


def test_future_bars_do_not_rewrite_past_displacement_features():
    prefix = _bars(5)
    prefix["atr_1m"] = 1.0
    prefix.loc[:, "open"] = [100.0, 100.1, 100.2, 100.3, 100.4]
    prefix.loc[:, "close"] = [100.1, 100.2, 100.3, 101.2, 100.5]
    prefix["high"] = prefix[["open", "close"]].max(axis=1) + 0.05
    prefix["low"] = prefix[["open", "close"]].min(axis=1) - 0.05

    future = _bars(2)
    future["timestamp"] = pd.date_range(
        prefix["timestamp"].iloc[-1] + pd.Timedelta(minutes=1),
        periods=2,
        freq="1min",
        tz="UTC",
    )
    future["atr_1m"] = 1.0
    future.loc[:, "open"] = [100.5, 100.6]
    future.loc[:, "close"] = [110.0, 90.0]
    future["high"] = future[["open", "close"]].max(axis=1) + 0.05
    future["low"] = future[["open", "close"]].min(axis=1) - 0.05

    extended = pd.concat([prefix, future], ignore_index=True)

    settings = _displacement_settings()
    prefix_result = add_displacement(prefix, settings=settings)
    extended_result = add_displacement(extended, settings=settings).iloc[: len(prefix)]

    columns = [
        "bullish_displacement",
        "bearish_displacement",
        "body_atr_ratio",
        "body_median_ratio",
        "median_body_previous",
    ]
    pd.testing.assert_frame_equal(
        prefix_result[columns].reset_index(drop=True),
        extended_result[columns].reset_index(drop=True),
        check_dtype=False,
    )
