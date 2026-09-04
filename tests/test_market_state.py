from __future__ import annotations

from datetime import timedelta
import json

import numpy as np
import pandas as pd

import run_pipeline as pipeline
from market_state import (
    SCHEMA_VERSION,
    STATUS_DEGRADED_HISTORY,
    STATUS_PROJECTX_UNAVAILABLE,
    STATUS_READY,
    STATUS_STALE,
    build_market_state,
    save_market_state_snapshot,
)


def _config() -> dict:
    return {
        "confluence_zones": {
            "cluster_tolerance_points": 2.0,
            "reaction_tolerance_points": 1.0,
            "pivot_tolerance_points": 0.5,
            "source_score_cap": 60.0,
        }
    }


def _frame() -> pd.DataFrame:
    timestamps = pd.date_range("2026-09-01 13:00", periods=3, freq="1min", tz="UTC")
    dataframe = pd.DataFrame(
        {
            "timestamp": timestamps,
            "available_at": timestamps + timedelta(minutes=1),
            "bar_complete": True,
            "open": [99.5, 100.0, 100.25],
            "high": [100.25, 100.75, 101.0],
            "low": [99.25, 99.75, 100.0],
            "close": [100.0, 100.5, 100.75],
            "volume": [100.0, 125.0, 150.0],
            "source": "PROJECTX",
            "session_date": pd.Timestamp("2026-09-01").date(),
            "pdh": 130.0,
            "pdl": 70.0,
            "pdc": 98.0,
            "half_back": 100.0,
            "pmh": 125.0,
            "pml": 75.0,
            "ash": 120.0,
            "asl": 80.0,
            "loh": 122.0,
            "lol": 78.0,
            "onh": 126.0,
            "onl": 74.0,
            "week_high": 140.0,
            "week_low": 60.0,
            "vwap": [99.8, 100.0, 100.25],
            "rth_open": np.nan,
            "or5_high": np.nan,
            "or5_low": np.nan,
            "or15_high": np.nan,
            "or15_low": np.nan,
            "active_external_swing_high": 128.0,
            "active_external_swing_low": 72.0,
            "active_internal_swing_high": 110.0,
            "active_internal_swing_low": 90.0,
            "external_swing_high_equal_cluster_level": [130.0, np.nan, np.nan],
            "external_swing_low_equal_cluster_level": [70.0, np.nan, np.nan],
            "nearest_htf_fvg_above": 132.0,
            "nearest_htf_fvg_below": 68.0,
            "nearest_5m_fvg_above": 115.0,
            "nearest_5m_fvg_below": 85.0,
            "htf_bias": "bullish",
            "htf_bias_confidence": 0.75,
            "macro_bias": "bullish",
            "intraday_bias": "bullish",
            "bias_15m": "bullish",
            "bias_1h": "bullish",
            "external_dealing_range_high": 128.0,
            "external_dealing_range_low": 72.0,
            "external_dealing_equilibrium": 100.0,
            "external_dealing_location": "premium",
            "pd_array_directional_context": "bullish",
            "bullish_fvg_retest_hold": [False, True, True],
            "bullish_displacement": [False, True, False],
            "displacement_direction": ["none", "bullish", "none"],
            "displacement_category": ["none", "strong", "none"],
            "bullish_continuation_sequence": [False, True, True],
            "bullish_continuation_entry_valid_event": [False, True, False],
            "entry_valid_direction": ["none", "bullish", "none"],
            "rvol_rolling": [1.0, 1.5, 1.25],
            "rvol_time_of_day": [1.0, 1.4, 1.2],
            "volume_context": ["normal", "bullish_breakout", "normal"],
            "snr_1m": [0.4, 0.7, 0.6],
            "snr_5m": [0.5, 0.6, 0.65],
            "snr_15m": [0.45, 0.55, 0.6],
            "snr_quality_class": "strong",
            "dol_direction": "bullish",
            "dol_primary_direction": "bullish",
            "dol_primary_target_type": "pdh",
            "dol_primary_target_category": "pdh_pdl",
            "dol_primary_target_price": 130.0,
            "dol_primary_distance_points": [30.0, 29.5, 29.25],
            "dol_primary_confidence": 0.8,
            "dol_primary_components": json.dumps({"source": "pdh"}),
            "dol_alternate_direction": "bearish",
            "dol_alternate_target_type": "pdl",
            "dol_alternate_target_category": "pdh_pdl",
            "dol_alternate_target_price": 70.0,
            "dol_alternate_distance_points": [30.0, 30.5, 30.75],
            "dol_alternate_confidence": 0.25,
            "dol_alternate_components": json.dumps({"source": "pdl"}),
            "dol_ranked_candidates": json.dumps(
                [{"source": "pdh", "price": 130.0}]
            ),
            "long_raw_score": [60.0, 72.0, 74.0],
            "short_raw_score": [35.0, 30.0, 28.0],
            "long_score_band": "near_trigger",
            "short_score_band": "no_trade",
            "long_positive_points": 74.0,
            "short_positive_points": 28.0,
            "long_penalty_points": 0.0,
            "short_penalty_points": 0.0,
            "long_disabled": False,
            "short_disabled": False,
            "long_disable_reason": None,
            "short_disable_reason": None,
            "long_score_draw_on_liquidity": 10.0,
            "short_score_draw_on_liquidity": 0.0,
            "score_edge": [25.0, 42.0, 46.0],
            "preferred_score_direction": "long",
            "long_candidate": True,
            "short_candidate": False,
            "candidate_any": True,
        }
    )
    return dataframe


def _state(dataframe: pd.DataFrame | None = None, **kwargs) -> dict:
    return build_market_state(
        _frame() if dataframe is None else dataframe,
        as_of=kwargs.pop("as_of", "2026-09-01T09:03:00-04:00"),
        symbol="MNQ",
        contract="MNQU6",
        strategy_config=_config(),
        data_quality=kwargs.pop(
            "data_quality",
            {
                "analysis_status": "pass",
                "reasons": [],
                "session_coverage": {"all_due_covered": True},
            },
        ),
        source_snapshots=["data/raw/projectx/sample.parquet"],
        **kwargs,
    )


def test_market_state_schema_contains_all_phase5_sections_and_levels() -> None:
    state = _state()

    assert state["schema_version"] == SCHEMA_VERSION
    assert state["status"]["message"] == STATUS_READY
    assert state["as_of"] == "2026-09-01T13:03:00+00:00"
    assert state["generated_at"] == state["as_of"]
    assert state["instrument"]["latest_price"] == 100.75
    assert state["instrument"]["latest_bar_available_at"] == (
        "2026-09-01T13:03:00+00:00"
    )
    assert state["data_quality"]["freshness"]["latest_bar_age_seconds"] == 0.0
    assert state["timeframes"]["1m"]["close"] == 100.75
    assert state["timeframes"]["15m"]["bias"] == "bullish"

    required_sections = {
        "data_quality", "sessions", "timeframes", "bias", "levels",
        "swings", "liquidity", "dealing_ranges", "pd_arrays", "fvgs",
        "structure", "displacement", "volume", "signal_to_noise",
        "support_resistance", "draw_on_liquidity", "scores",
        "news_event_risk", "trade_candidates", "source_snapshots",
    }
    assert required_sections.issubset(state)

    levels = state["levels"]
    assert levels["pdh"] == 130.0
    assert levels["previous_close"] == 98.0
    assert levels["prior_day_half_back"] == 100.0
    assert levels["nearest_important_swing_high"] == 110.0
    assert levels["nearest_important_swing_low"] == 90.0
    assert levels["nearest_equal_high"] == 130.0
    assert levels["nearest_equal_low"] == 70.0
    assert levels["important_htf_fvg_above"] == 132.0
    assert levels["important_5m_fvg_below"] == 85.0
    assert "cash_open" in levels and levels["cash_open"] is None
    assert levels["important_support_resistance_zone"] is not None

    assert state["draw_on_liquidity"]["primary"]["target_type"] == "pdh"
    assert state["draw_on_liquidity"]["alternate"]["target_type"] == "pdl"
    assert state["scores"]["long"]["raw_score"] == 74.0
    assert state["scores"]["long"]["components"]["long_score_draw_on_liquidity"] == 10.0
    assert state["news_event_risk"]["status"] == "unavailable"
    assert state["trade_candidates"] == {"long": True, "short": False, "any": True}
    json.dumps(state, sort_keys=True)


def test_market_state_enforces_as_of_and_completed_bar_visibility() -> None:
    dataframe = _frame()
    dataframe.loc[1, "bar_complete"] = False
    state = _state(dataframe, as_of="2026-09-01T09:02:00-04:00")

    assert state["instrument"]["latest_bar_timestamp"] == (
        "2026-09-01T13:00:00+00:00"
    )
    assert state["instrument"]["latest_price"] == 100.0
    assert state["levels"]["pdh"] == 130.0


def test_market_state_safe_failure_and_degraded_statuses() -> None:
    unavailable = build_market_state(
        None,
        as_of="2026-09-01T09:00:00-04:00",
        symbol="MNQ",
        contract="MNQU6",
    )
    assert unavailable["status"]["message"] == STATUS_PROJECTX_UNAVAILABLE
    assert unavailable["instrument"]["latest_price"] is None

    stale = _state(
        freshness={
            "fresh": False,
            "reason": "latest_bar_is_stale",
            "age_seconds": 600,
        }
    )
    assert stale["status"]["message"] == STATUS_STALE

    degraded = _state(
        data_quality={
            "analysis_status": "degraded",
            "reasons": ["Required history incomplete."],
            "session_coverage": {"all_due_covered": False},
        }
    )
    assert degraded["status"]["message"] == STATUS_DEGRADED_HISTORY
    assert degraded["instrument"]["latest_price"] == 100.75


def test_market_state_storage_is_versioned_and_latest_never_substitutes_old_state(
    tmp_path,
) -> None:
    ready_frame = _frame()
    ready_frame["timestamp"] = ready_frame["timestamp"] - timedelta(minutes=5)
    ready_frame["available_at"] = ready_frame["available_at"] - timedelta(minutes=5)
    at_0900 = _state(ready_frame, as_of="2026-09-01T09:00:00-04:00")
    first = save_market_state_snapshot(at_0900, tmp_path)
    second = save_market_state_snapshot(at_0900, tmp_path)
    at_0925 = _state(ready_frame, as_of="2026-09-01T09:25:00-04:00")
    third = save_market_state_snapshot(at_0925, tmp_path)

    assert first.snapshot.name == "2026-09-01_0900_market_state.json"
    assert second.snapshot.name == "2026-09-01_0900_market_state_v2.json"
    assert third.snapshot.name == "2026-09-01_0925_market_state.json"
    assert first.snapshot.exists() and second.snapshot.exists() and third.snapshot.exists()

    failure = build_market_state(
        None,
        as_of="2026-09-01T09:26:00-04:00",
        symbol="MNQ",
        contract="MNQU6",
    )
    failure_paths = save_market_state_snapshot(failure, tmp_path)
    latest = json.loads(failure_paths.latest.read_text(encoding="utf-8"))
    assert latest["status"]["message"] == STATUS_PROJECTX_UNAVAILABLE
    assert latest["as_of"] == "2026-09-01T13:26:00+00:00"
    preserved = json.loads(first.snapshot.read_text(encoding="utf-8"))
    assert preserved["status"]["message"] == STATUS_READY


def test_market_state_historical_prefix_is_invariant_to_future_append() -> None:
    prefix = _frame().iloc[:2].copy()
    future = _frame().iloc[2:].copy()
    future.loc[:, "close"] = 9999.0
    future.loc[:, "pdh"] = 10000.0
    future.loc[:, "dol_primary_target_price"] = 10000.0
    extended = pd.concat([prefix, future], ignore_index=True)

    before = _state(prefix, as_of="2026-09-01T09:02:00-04:00")
    after = _state(extended, as_of="2026-09-01T09:02:00-04:00")
    assert before == after


def test_pipeline_places_market_state_after_scoring_before_backtest() -> None:
    stages = pipeline.PIPELINE_STAGES
    assert stages.index("scoring") < stages.index("market_state")
    assert stages.index("market_state") < stages.index("backtest")


def test_pipeline_market_state_stage_saves_snapshot(tmp_path) -> None:
    state, paths = pipeline.stage_market_state(
        _frame(),
        strategy_config=_config(),
        state_directory=tmp_path,
        as_of="2026-09-01T09:03:00-04:00",
        symbol="MNQ",
        contract="MNQU6",
        data_quality={"analysis_status": "pass", "reasons": []},
        source_snapshots=["sample.parquet"],
    )
    assert state["schema_version"] == SCHEMA_VERSION
    assert state["status"]["message"] == STATUS_READY
    assert paths["snapshot"].endswith("2026-09-01_0903_market_state.json")
    assert paths["latest"].endswith("latest.json")
