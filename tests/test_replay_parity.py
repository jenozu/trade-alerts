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

from datetime import timedelta

import numpy as np
import pandas as pd

from data_clock import filter_as_of, filter_resampled_results_as_of
from dol import enrich_draw_on_liquidity
from resample import TIMEFRAME_RULES, generate_standard_timeframes
from sessions import enrich_with_sessions, load_sessions_config
from structure import enrich_structure_features

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


def _phase4_config() -> dict:
    """Small deterministic production configuration for parity coverage."""
    return {
        "market": {"tick_size": 0.25},
        "swings": {"timeframe": "1m"},
        "liquidity": {
            "sweep": {
                "minimum_penetration_ticks": 1,
                "require_close_back_through_level": True,
            },
            "registry": {"approach_ticks": 4, "break_ticks": 1},
        },
        "displacement": {
            "enabled": True,
            "atr_period": 1,
            "body_lookback": 1,
            "minimum_body_atr_multiple": 0.25,
            "minimum_body_median_multiple": 1.0,
            "close_extreme_fraction": 0.25,
            "require_directional_close": True,
            "relative_volume_confirmation": {"enabled": False},
            "component_model": {
                "minimum_coverage_fraction": 0.0,
                "categories": {"weak": 0.0, "moderate": 0.0, "strong": 0.0},
            },
        },
        "structure": {
            "enabled": True,
            "break_method": "close",
            "break_buffer_points": 0.25,
            "bos": {"enabled": True, "require_confirmed_swing": True},
            "mss": {
                "enabled": True,
                "require_confirmed_swing": True,
                "require_prior_liquidity_event": False,
                "require_displacement": {"enabled": False},
            },
            "choch": {"enabled": True, "structure_scope": "internal"},
            "wick_breaks": {"record": True, "count_as_confirmation": False},
        },
        "room_to_target": {"minimum_points": 25.0},
        "draw_on_liquidity": {
            "enabled": True,
            "candidate_sources": ["pdh_pdl"],
            "minimum_target_distance_points": 25.0,
            "decision_threshold": 3.0,
            "minimum_score_edge": 1.0,
            "evidence_weights": {
                "target_available": 1.0,
                "higher_timeframe_bias": 2.0,
                "opposing_liquidity_sweep": 1.5,
                "premium_discount": 1.0,
                "fvg_context": 0.5,
                "structure_context": 1.0,
                "displacement": 1.0,
            },
        },
    }


def _phase4_dataset() -> pd.DataFrame:
    timestamps = pd.date_range(
        "2026-09-01 14:00", periods=12, freq="1min", tz="UTC"
    )
    close = np.array(
        [100.0, 102.0, 101.75, 102.0, 102.25, 102.5, 102.75, 103.0,
         139.0, 141.0, 138.0, 137.0]
    )
    open_price = np.array(
        [99.75, 100.0, 102.0, 101.75, 102.0, 102.25, 102.5, 102.75,
         103.0, 139.0, 141.0, 138.0]
    )
    dataframe = pd.DataFrame(
        {
            "timestamp": timestamps,
            "available_at": timestamps + timedelta(minutes=1),
            "bar_complete": True,
            "open": open_price,
            "high": np.maximum(open_price, close) + 0.25,
            "low": np.minimum(open_price, close) - 0.25,
            "close": close,
            "volume": 100.0,
            "internal_swing_high_confirmed": False,
            "internal_swing_low_confirmed": False,
            "internal_swing_high_price": np.nan,
            "internal_swing_low_price": np.nan,
            "active_internal_swing_high": 101.0,
            "active_internal_swing_low": 95.0,
            "pdh": 140.0,
            "pdl": 60.0,
            "nearest_unswept_liquidity_above": 140.0,
            "nearest_unswept_liquidity_below": 60.0,
            "distance_to_unswept_liquidity_above": 40.0,
            "distance_to_unswept_liquidity_below": 40.0,
            "htf_bias": "bullish",
            "recent_sell_side_sweep": True,
            "recent_buy_side_sweep": False,
            "sell_side_liquidity_sweep": False,
            "buy_side_liquidity_sweep": False,
            "external_premium_discount": "discount",
            "bullish_fvg_created": False,
            "bearish_fvg_created": False,
            "bullish_fvg_retest_hold": False,
            "bearish_fvg_retest_hold": False,
        }
    )
    # The displacement break on 14:01 can become continuation-entry-valid only
    # after this later completed-bar retest hold.
    dataframe.loc[2, "bullish_fvg_retest_hold"] = True

    # A nominally available but explicitly incomplete bar must remain hidden.
    dataframe.loc[7, "bar_complete"] = False

    # Hostile post-cutoff bars sweep the prior-day high and reverse violently.
    # They must not rewrite the already-visible structure sequence or DOL.
    dataframe.loc[8, "high"] = 141.0
    dataframe.loc[8, "low"] = 102.75
    dataframe.loc[9, "high"] = 142.0
    dataframe.loc[10, "low"] = 90.0
    return dataframe


def _phase4_features(dataframe: pd.DataFrame) -> pd.DataFrame:
    structured = enrich_structure_features(dataframe, _phase4_config())
    return enrich_draw_on_liquidity(structured, _phase4_config())


def test_phase4_replay_matches_live_completed_prefix_at_as_of() -> None:
    """Replay and live use identical Phase 4 semantics on visible bars.

    The live representation is the completed prefix available at ``as_of``.
    The replay representation processes the full history causally and is then
    observed at the same cutoff. Both paths deliberately call the same
    production structure/sequence and DOL functions.
    """
    full = _phase4_dataset()
    as_of = pd.Timestamp("2026-09-01 14:08:00", tz="UTC")

    live_input = filter_as_of(full, as_of=as_of)
    live = _phase4_features(live_input)

    replay_full = _phase4_features(full)
    replay_visible = filter_as_of(replay_full, as_of=as_of)

    assert live["available_at"].le(as_of).all()
    assert live["bar_complete"].all()
    assert live["timestamp"].max() == pd.Timestamp("2026-09-01 14:06:00Z")
    assert live["bullish_continuation_entry_valid_event"].any()
    assert (live["dol_primary_target_type"] == "pdh").any()

    input_columns = set(full.columns)
    phase4_columns = [
        column for column in live.columns if column not in input_columns
    ]
    pd.testing.assert_frame_equal(
        live[["timestamp", *phase4_columns]].reset_index(drop=True),
        replay_visible[["timestamp", *phase4_columns]].reset_index(drop=True),
        check_dtype=False,
        obj="Phase 4 historical replay/live completed-prefix mismatch",
    )
