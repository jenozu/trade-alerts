from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from swings import SwingError, enrich_swings


def _config() -> dict:
    return {
        "swings": {
            "internal": {"left_bars": 2, "right_bars": 2},
            "external": {"left_bars": 5, "right_bars": 5},
        }
    }


def _bars(highs: list[float], lows: list[float] | None = None) -> pd.DataFrame:
    if lows is None:
        lows = [value - 2.0 for value in highs]
    timestamps = pd.date_range(
        "2026-08-31 13:30:00",
        periods=len(highs),
        freq="1min",
        tz="UTC",
    )
    opens = [(high + low) / 2.0 for high, low in zip(highs, lows)]
    closes = opens.copy()
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
        }
    )


def test_swings_reject_naive_timestamps():
    df = _bars([100, 101, 105, 104, 103])
    df["timestamp"] = df["timestamp"].dt.tz_localize(None)

    with pytest.raises(SwingError, match="timezone-aware"):
        enrich_swings(df, _config())


def test_internal_swing_high_is_confirmed_only_after_two_right_bars_close():
    df = _bars([100, 101, 105, 104, 103])
    enriched = enrich_swings(df, _config())

    # Pivot is index 2, but with right_bars=2 it is not usable until index 4.
    assert not enriched.loc[:3, "internal_swing_high_confirmed"].any()
    assert bool(enriched.loc[4, "internal_swing_high_confirmed"])
    assert enriched.loc[4, "internal_swing_high_price"] == 105.0
    assert enriched.loc[4, "internal_swing_high_pivot_index"] == 2.0
    assert enriched.loc[4, "internal_swing_high_pivot_time"] == df.loc[2, "timestamp"]

    assert enriched.loc[:3, "active_internal_swing_high"].isna().all()
    assert enriched.loc[4, "active_internal_swing_high"] == 105.0


def test_internal_swing_low_is_confirmed_only_after_two_right_bars_close():
    highs = [102, 101, 100, 101, 102]
    lows = [100, 99, 95, 96, 97]
    df = _bars(highs, lows)
    enriched = enrich_swings(df, _config())

    assert not enriched.loc[:3, "internal_swing_low_confirmed"].any()
    assert bool(enriched.loc[4, "internal_swing_low_confirmed"])
    assert enriched.loc[4, "internal_swing_low_price"] == 95.0
    assert enriched.loc[4, "internal_swing_low_pivot_index"] == 2.0
    assert enriched.loc[4, "internal_swing_low_pivot_time"] == df.loc[2, "timestamp"]

    assert enriched.loc[:3, "active_internal_swing_low"].isna().all()
    assert enriched.loc[4, "active_internal_swing_low"] == 95.0


def test_external_swing_high_waits_for_five_right_bars():
    highs = [100, 101, 102, 103, 104, 120, 110, 109, 108, 107, 106]
    df = _bars(highs)
    enriched = enrich_swings(df, _config())

    # Pivot is index 5. External right_bars=5 means confirmation is index 10.
    assert not enriched.loc[:9, "external_swing_high_confirmed"].any()
    assert bool(enriched.loc[10, "external_swing_high_confirmed"])
    assert enriched.loc[10, "external_swing_high_price"] == 120.0
    assert enriched.loc[10, "external_swing_high_pivot_index"] == 5.0
    assert enriched.loc[:9, "active_external_swing_high"].isna().all()
    assert enriched.loc[10, "active_external_swing_high"] == 120.0


def test_active_swing_persists_and_age_starts_at_confirmation_bar():
    # First internal high confirms at index 4; later bars do not create a new high.
    df = _bars([100, 101, 105, 104, 103, 102, 101])
    enriched = enrich_swings(df, _config())

    assert enriched.loc[4, "active_internal_swing_high"] == 105.0
    assert enriched.loc[5, "active_internal_swing_high"] == 105.0
    assert enriched.loc[6, "active_internal_swing_high"] == 105.0

    assert enriched.loc[4, "internal_swing_high_age_bars"] == 0.0
    assert enriched.loc[5, "internal_swing_high_age_bars"] == 1.0
    assert enriched.loc[6, "internal_swing_high_age_bars"] == 2.0


def test_future_price_changes_do_not_rewrite_already_confirmed_swing_state():
    highs = [
        100, 101, 105, 104, 103, 102, 106, 103, 101, 100,
        104, 102, 101, 103, 102, 101, 100, 99, 98, 97,
    ]
    lows = [value - 3.0 for value in highs]
    original = _bars(highs, lows)
    changed = original.copy()

    # Change only bars strictly after the comparison cutoff.
    cutoff = 12
    changed.loc[cutoff + 1 :, "high"] = changed.loc[cutoff + 1 :, "high"] + 500.0
    changed.loc[cutoff + 1 :, "low"] = changed.loc[cutoff + 1 :, "low"] - 500.0
    changed.loc[cutoff + 1 :, "open"] = (
        changed.loc[cutoff + 1 :, "high"] + changed.loc[cutoff + 1 :, "low"]
    ) / 2.0
    changed.loc[cutoff + 1 :, "close"] = changed.loc[cutoff + 1 :, "open"]

    first = enrich_swings(original, _config())
    second = enrich_swings(changed, _config())

    causal_columns = [
        "internal_swing_high_confirmed",
        "internal_swing_low_confirmed",
        "external_swing_high_confirmed",
        "external_swing_low_confirmed",
        "active_internal_swing_high",
        "active_internal_swing_low",
        "active_external_swing_high",
        "active_external_swing_low",
        "internal_swing_high_age_bars",
        "internal_swing_low_age_bars",
        "external_swing_high_age_bars",
        "external_swing_low_age_bars",
    ]

    pd.testing.assert_frame_equal(
        first.loc[:cutoff, causal_columns].reset_index(drop=True),
        second.loc[:cutoff, causal_columns].reset_index(drop=True),
        check_dtype=True,
    )


def test_premium_discount_stays_unknown_until_both_confirmed_range_sides_exist():
    # A confirmed swing high exists by index 4, but no confirmed swing low yet.
    df = _bars([100, 101, 105, 104, 103])
    enriched = enrich_swings(df, _config())

    assert enriched.loc[4, "active_internal_swing_high"] == 105.0
    assert pd.isna(enriched.loc[4, "active_internal_swing_low"])
    assert pd.isna(enriched.loc[4, "internal_equilibrium"])
    assert enriched.loc[4, "internal_premium_discount"] == "unknown"


def test_input_is_sorted_before_swing_confirmation_is_calculated():
    ordered = _bars([100, 101, 105, 104, 103])
    shuffled = ordered.iloc[[4, 0, 2, 1, 3]].reset_index(drop=True)

    enriched = enrich_swings(shuffled, _config())

    assert enriched["timestamp"].is_monotonic_increasing
    assert bool(enriched.loc[4, "internal_swing_high_confirmed"])
    assert enriched.loc[4, "internal_swing_high_pivot_index"] == 2.0
    assert enriched.loc[4, "internal_swing_high_price"] == 105.0
