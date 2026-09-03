"""Integrated replay/live MTF parity and append-invariance snapshots.

Phase 2 requires that historical replay reproduces the same multi-timeframe
bars and the same session levels a live run would have produced at a given
``as_of``. This test builds a continuous 1m dataset that extends past every
checkpoint, then verifies at each checkpoint (08:00/09:00/09:25/09:29/09:35/
10:00 ET):

1. MTF parity: resampling the ``as_of``-cut prefix equals filtering the full
   resample at the same cutoff, for every timeframe.
2. No incomplete HTF bar is ever visible at a checkpoint.
3. Session enrichment is append-invariant: enriching the prefix yields exactly
   the same rows as enriching the full dataset and cutting at the prefix
   boundary, so future bars never rewrite past session levels.
4. Future session extrema are not visible at an earlier checkpoint.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from data_clock import filter_as_of, filter_resampled_results_as_of
from resample import TIMEFRAME_RULES, generate_standard_timeframes
from sessions import enrich_with_sessions, load_sessions_config

TRADING_TZ = "America/New_York"

CHECKPOINTS = ["08:00", "09:00", "09:25", "09:29", "09:35", "10:00"]


def _full_dataset() -> pd.DataFrame:
    """Continuous 1m bars spanning a prior RTH session and the next Globex
    session through 10:30 ET (past every checkpoint)."""
    prior = pd.date_range("2026-08-31 09:30", "2026-08-31 15:59", freq="1min", tz=TRADING_TZ)
    current = pd.date_range("2026-08-31 18:00", "2026-09-01 10:30", freq="1min", tz=TRADING_TZ)
    timestamps_et = prior.append(current)
    n = len(timestamps_et)
    base = 100.0 + 0.01 * np.arange(n)
    return pd.DataFrame(
        {
            "timestamp": timestamps_et.tz_convert("UTC"),
            "open": base,
            "high": base + 0.5,
            "low": base - 0.5,
            "close": base + 0.25,
            "volume": 100.0,
        }
    )


def _config() -> dict:
    return load_sessions_config("config/sessions.yaml")


def _checkpoint(hhmm: str) -> pd.Timestamp:
    return pd.Timestamp(f"2026-09-01 {hhmm}", tz=TRADING_TZ)


def test_replay_matches_live_mtf_at_every_checkpoint() -> None:
    full = _full_dataset()

    for hhmm in CHECKPOINTS:
        as_of = _checkpoint(hhmm)
        prefix = filter_as_of(full, as_of=as_of)
        resampled_prefix = generate_standard_timeframes(prefix)
        resampled_full_filtered = filter_resampled_results_as_of(
            generate_standard_timeframes(full), as_of=as_of
        )

        for timeframe in TIMEFRAME_RULES:
            left = resampled_prefix[timeframe].dataframe
            left = left[left["bar_complete"]].reset_index(drop=True)
            right = resampled_full_filtered[timeframe].dataframe.reset_index(drop=True)
            pd.testing.assert_frame_equal(
                left,
                right,
                check_like=True,
                obj=f"{timeframe} replay/live mismatch at {hhmm} ET",
            )
            # No incomplete HTF bar is ever visible at a checkpoint.
            assert right["bar_complete"].all(), (
                f"{timeframe} exposed an incomplete bar at {hhmm} ET"
            )


def test_session_enrichment_is_append_invariant() -> None:
    full = _full_dataset()
    config = _config()
    as_of = _checkpoint("09:29")
    prefix = filter_as_of(full, as_of=as_of)

    enriched_prefix, _ = enrich_with_sessions(prefix, config, causal=True)
    enriched_full, _ = enrich_with_sessions(full, config, causal=True)

    last_visible = prefix["timestamp"].max()
    full_cut = enriched_full[
        enriched_full["timestamp"] <= last_visible
    ].reset_index(drop=True)
    enriched_prefix = enriched_prefix.reset_index(drop=True)

    # Appending future bars must not change any column of any prefix row.
    pd.testing.assert_frame_equal(enriched_prefix, full_cut)


def test_no_future_session_extrema_visible_at_0929() -> None:
    full = _full_dataset()
    config = _config()

    # A bar opening exactly at the 09:29 checkpoint completes at 09:30 and is
    # therefore not yet visible at 09:29; its extreme spike must not leak into
    # the 09:29 snapshot.
    spike = pd.Timestamp("2026-09-01 09:29", tz=TRADING_TZ).tz_convert("UTC")
    full.loc[full["timestamp"] == spike, "high"] = 99999.0

    prefix = filter_as_of(full, as_of=_checkpoint("09:29"))
    enriched, _ = enrich_with_sessions(prefix, config, causal=True)

    # The 09:29 bar is excluded from the 09:29 prefix, so its spike never
    # reaches the developing overnight extreme.
    assert not (enriched["developing_onh"] >= 99999.0).any()
    # Same-session finalized levels are not available yet at 09:29.
    for column in ["pmh", "pml", "onh", "onl"]:
        assert enriched[column].isna().all(), f"{column} leaked at 09:29 ET"
