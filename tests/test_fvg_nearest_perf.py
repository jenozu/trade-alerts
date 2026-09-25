"""Parity and causality regression tests for the fast full-history FVG lookup."""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
import pytest

from fvg import add_nearest_active_fvg


OUTPUT_COLUMNS = [
    "nearest_active_bullish_fvg_lower",
    "nearest_active_bullish_fvg_upper",
    "nearest_active_bullish_fvg_midpoint",
    "distance_to_bullish_fvg",
    "nearest_active_bearish_fvg_lower",
    "nearest_active_bearish_fvg_upper",
    "nearest_active_bearish_fvg_midpoint",
    "distance_to_bearish_fvg",
]


def reference_nearest(df: pd.DataFrame, tracked: pd.DataFrame) -> pd.DataFrame:
    """Frozen original pandas implementation; independent parity oracle."""
    result = df.copy()
    for col in OUTPUT_COLUMNS:
        result[col] = np.nan
    if tracked.empty:
        return result
    for i, bar in result.iterrows():
        timestamp = bar["timestamp"]
        close = float(bar["close"])
        active = tracked.loc[tracked["creation_time"] <= timestamp].copy()
        if active.empty:
            continue
        active = active.loc[
            active["invalidation_time"].isna()
            | (active["invalidation_time"] > timestamp)
        ]
        for direction, anchor, offset in (
            ("bullish", "upper_bound", 0),
            ("bearish", "lower_bound", 4),
        ):
            group = active.loc[active["direction"] == direction]
            if group.empty:
                continue
            group = group.copy()
            group["distance"] = (close - group[anchor]).abs()
            nearest = group.loc[group["distance"].idxmin()]
            result.at[i, OUTPUT_COLUMNS[offset]] = nearest["lower_bound"]
            result.at[i, OUTPUT_COLUMNS[offset + 1]] = nearest["upper_bound"]
            result.at[i, OUTPUT_COLUMNS[offset + 2]] = nearest["midpoint"]
            result.at[i, OUTPUT_COLUMNS[offset + 3]] = nearest["distance"]
    return result


def sample_tables(seed=123, bars=130, gaps=42, *, timezone="UTC"):
    rng = np.random.default_rng(seed)
    times = pd.date_range("2026-03-08 05:30", periods=bars, freq="1min", tz="UTC")
    if timezone != "UTC":
        times = times.tz_convert(timezone)
    prices = 100.0 + rng.normal(0, 2, bars)
    df = pd.DataFrame({"timestamp": times, "close": prices})
    created = rng.integers(0, bars - 2, gaps)
    invalidated = [
        pd.NaT if j % 5 == 0 else times[min(bars - 1, x + int(rng.integers(1, 30)))]
        for j, x in enumerate(created)
    ]
    lows = rng.normal(99, 4, gaps)
    highs = lows + rng.uniform(.25, 3, gaps)
    tracked = pd.DataFrame({
        "creation_time": times[created],
        "invalidation_time": invalidated,
        "direction": np.where(np.arange(gaps) % 2, "bullish", "bearish"),
        "lower_bound": lows,
        "upper_bound": highs,
        "midpoint": (lows + highs) / 2,
    })
    return df, tracked


@pytest.mark.parametrize("timezone", ["UTC", "America/New_York"])
@pytest.mark.parametrize("seed", [5, 20])
def test_optimized_lookup_matches_original(seed, timezone):
    bars, gaps = sample_tables(seed, timezone=timezone)
    optimized = add_nearest_active_fvg(bars, gaps)
    reference = reference_nearest(bars, gaps)
    pd.testing.assert_frame_equal(optimized, reference, check_dtype=False)


def test_invalidation_is_exclusive_and_ties_keep_first_table_row():
    times = pd.date_range("2026-09-01 13:30", periods=4, freq="min", tz="UTC")
    bars = pd.DataFrame({"timestamp": times, "close": [100., 100., 100., 100.]})
    gaps = pd.DataFrame({
        "creation_time": [times[0]] * 3,
        "invalidation_time": [times[2], pd.NaT, pd.NaT],
        "direction": ["bullish", "bullish", "bearish"],
        "lower_bound": [98., 97., 99.],
        "upper_bound": [101., 101., 102.],
        "midpoint": [99.5, 99., 100.5],
    })
    actual = add_nearest_active_fvg(bars, gaps)
    assert actual.loc[0, "nearest_active_bullish_fvg_lower"] == 98.
    assert actual.loc[2, "nearest_active_bullish_fvg_lower"] == 97.
    assert actual.loc[0, "nearest_active_bearish_fvg_lower"] == 99.


def test_future_fvgs_and_future_invalidations_do_not_change_past():
    bars, gaps = sample_tables(55)
    prefix = bars.iloc[:60].copy()
    # Future-created gaps have no visibility in the prefix; future
    # invalidations must not remove currently active gaps early.
    full = add_nearest_active_fvg(bars, gaps)
    early = add_nearest_active_fvg(prefix, gaps)
    pd.testing.assert_frame_equal(
        full.iloc[:len(prefix)].reset_index(drop=True),
        early.reset_index(drop=True),
        check_dtype=False,
    )


def test_empty_table_preserves_output_contract():
    bars, gaps = sample_tables()
    optimized = add_nearest_active_fvg(bars, gaps.iloc[0:0].copy())
    assert all(col in optimized for col in OUTPUT_COLUMNS)
    assert optimized[OUTPUT_COLUMNS].isna().all().all()


@pytest.mark.slow
def test_large_synthetic_fvg_nearest_benchmark():
    """Opt-in local performance test: pytest -q -m slow this file."""
    bars, gaps = sample_tables(77, bars=1500, gaps=300)
    start = time.perf_counter()
    expected = reference_nearest(bars, gaps)
    reference_seconds = time.perf_counter() - start
    start = time.perf_counter()
    actual = add_nearest_active_fvg(bars, gaps)
    optimized_seconds = time.perf_counter() - start
    pd.testing.assert_frame_equal(actual, expected, check_dtype=False)
    print(f"reference={reference_seconds:.2f}s optimized={optimized_seconds:.2f}s")
