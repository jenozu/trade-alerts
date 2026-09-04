from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from dol import DOLError, enrich_draw_on_liquidity, select_unswept_target
from scorer import score_setup


def _config() -> dict:
    return {
        "market": {"tick_size": 0.25},
        "room_to_target": {"minimum_points": 25.0},
        "draw_on_liquidity": {
            "enabled": True,
            "candidate_sources": [
                "external_swings",
                "pdh_pdl",
                "pmh_pml",
                "onh_onl",
                "loh_lol",
                "fair_value_gaps",
            ],
            "minimum_target_distance_points": 25.0,
            "decision_threshold": 3.0,
            "minimum_score_edge": 1.0,
            "evidence_weights": {
                "target_available": 1.0,
                "higher_timeframe_bias": 2.0,
                "opposing_liquidity_sweep": 1.5,
                "premium_discount": 1.0,
                "fvg_context": 0.5,
            },
        },
    }


def _row(**overrides) -> dict:
    base = {
        "timestamp": pd.Timestamp("2026-08-31 14:00:00", tz="UTC"),
        "open": 100.0,
        "high": 101.0,
        "low": 99.0,
        "close": 100.0,
        "pdh": 130.0,
        "pdl": 70.0,
        "nearest_unswept_liquidity_above": 130.0,
        "nearest_unswept_liquidity_below": 70.0,
        "distance_to_unswept_liquidity_above": 30.0,
        "distance_to_unswept_liquidity_below": 30.0,
        "htf_bias": "neutral",
        "recent_sell_side_sweep": False,
        "recent_buy_side_sweep": False,
        "external_premium_discount": "equilibrium",
        "bullish_fvg_retest_hold": False,
        "bearish_fvg_retest_hold": False,
    }
    base.update(overrides)
    return base


def _frame(*rows: dict) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


def test_dol_rejects_naive_timestamps():
    df = _frame(_row())
    df["timestamp"] = df["timestamp"].dt.tz_localize(None)

    with pytest.raises(DOLError, match="timezone-aware"):
        enrich_draw_on_liquidity(df, _config())


def test_bullish_dol_selects_unswept_upside_target():
    df = _frame(
        _row(
            htf_bias="bullish",
            recent_sell_side_sweep=True,
            external_premium_discount="discount",
        )
    )

    result = enrich_draw_on_liquidity(df, _config())

    assert result.loc[0, "dol_direction"] == "bullish"
    assert result.loc[0, "draw_on_liquidity_direction"] == "bullish"
    assert result.loc[0, "dol_target_type"] == "pdh"
    assert result.loc[0, "dol_target_category"] == "pdh_pdl"
    assert result.loc[0, "dol_target_price"] == pytest.approx(130.0)
    assert result.loc[0, "dol_distance_points"] == pytest.approx(30.0)
    assert result.loc[0, "dol_bullish_score"] > result.loc[0, "dol_bearish_score"]
    assert result.loc[0, "dol_confidence"] > 0.0


def test_bearish_dol_selects_unswept_downside_target():
    df = _frame(
        _row(
            htf_bias="bearish",
            recent_buy_side_sweep=True,
            external_premium_discount="premium",
        )
    )

    result = enrich_draw_on_liquidity(df, _config())

    assert result.loc[0, "dol_direction"] == "bearish"
    assert result.loc[0, "dol_target_type"] == "pdl"
    assert result.loc[0, "dol_target_price"] == pytest.approx(70.0)
    assert result.loc[0, "dol_bearish_score"] > result.loc[0, "dol_bullish_score"]


def test_internal_nearest_level_is_not_silently_promoted_to_external_target():
    row = pd.Series(
        _row(
            nearest_unswept_liquidity_above=110.0,
            distance_to_unswept_liquidity_above=30.0,
            active_internal_swing_high=110.0,
            htf_bias="bullish",
            recent_sell_side_sweep=True,
            external_premium_discount="discount",
            nearest_unswept_liquidity_below=np.nan,
            distance_to_unswept_liquidity_below=np.nan,
        )
    )

    target = select_unswept_target(row, side="above", config=_config())
    assert target is None

    result = enrich_draw_on_liquidity(_frame(row.to_dict()), _config())
    assert result.loc[0, "dol_direction"] == "neutral"
    assert pd.isna(result.loc[0, "dol_target_price"])


def test_conflicting_directional_context_returns_neutral():
    df = _frame(
        _row(
            htf_bias="bullish",
            recent_buy_side_sweep=True,
            external_premium_discount="premium",
        )
    )

    result = enrich_draw_on_liquidity(df, _config())

    # Bullish side: target + HTF = 3.0.
    # Bearish side: target + sweep + premium = 3.5.
    # The 0.5 edge is below the configured 1.0 decision margin.
    assert result.loc[0, "dol_direction"] == "neutral"
    assert result.loc[0, "dol_confidence"] == pytest.approx(0.0)


def test_target_inside_minimum_room_is_not_selected():
    df = _frame(
        _row(
            pdh=120.0,
            nearest_unswept_liquidity_above=120.0,
            distance_to_unswept_liquidity_above=20.0,
            nearest_unswept_liquidity_below=np.nan,
            distance_to_unswept_liquidity_below=np.nan,
            htf_bias="bullish",
            recent_sell_side_sweep=True,
            external_premium_discount="discount",
        )
    )

    result = enrich_draw_on_liquidity(df, _config())
    assert result.loc[0, "dol_direction"] == "neutral"
    assert pd.isna(result.loc[0, "dol_bullish_target_price"])


def test_future_rows_do_not_rewrite_past_dol():
    first = _row(
        timestamp=pd.Timestamp("2026-08-31 14:00:00", tz="UTC"),
        htf_bias="bullish",
        recent_sell_side_sweep=True,
        external_premium_discount="discount",
    )
    second = _row(
        timestamp=pd.Timestamp("2026-08-31 14:01:00", tz="UTC"),
        htf_bias="bearish",
        recent_buy_side_sweep=True,
        external_premium_discount="premium",
    )

    before = enrich_draw_on_liquidity(_frame(first, second), _config())

    future = _row(
        timestamp=pd.Timestamp("2026-08-31 14:02:00", tz="UTC"),
        close=999.0,
        pdh=1100.0,
        pdl=900.0,
        nearest_unswept_liquidity_above=1100.0,
        nearest_unswept_liquidity_below=900.0,
        distance_to_unswept_liquidity_above=101.0,
        distance_to_unswept_liquidity_below=99.0,
        htf_bias="bearish",
        recent_buy_side_sweep=True,
        external_premium_discount="premium",
    )
    after = enrich_draw_on_liquidity(_frame(first, second, future), _config())

    columns = [
        "dol_direction",
        "dol_target_type",
        "dol_target_price",
        "dol_distance_points",
        "dol_bullish_score",
        "dol_bearish_score",
        "dol_score_edge",
    ]
    pd.testing.assert_frame_equal(
        before[columns],
        after.loc[:1, columns].reset_index(drop=True),
        check_dtype=True,
    )


def test_scorer_awards_dol_points_only_to_aligned_direction():
    config = {
        "scoring": {
            "enabled": True,
            "positive_weights": {"draw_on_liquidity": 10},
            "penalties": {},
            "hard_disable": {
                "unhealthy_data": True,
                "invalidated_thesis": True,
                "outside_entry_window": True,
            },
            "clamp": {"minimum": 0, "maximum": 100},
        },
        "score_bands": {
            "no_trade": {"minimum": 0, "maximum": 39},
            "watch": {"minimum": 40, "maximum": 54},
            "developing": {"minimum": 55, "maximum": 69},
            "near_trigger": {"minimum": 70, "maximum": 79},
            "high_probability": {"minimum": 80, "maximum": 89},
            "a_plus_plus": {"minimum": 90, "maximum": 100},
        },
    }
    row = pd.Series(
        {
            "timestamp": pd.Timestamp("2026-08-31 14:00:00", tz="UTC"),
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "dol_direction": "bullish",
        }
    )

    long_score = score_setup(row, direction="long", config=config)
    short_score = score_setup(row, direction="short", config=config)

    assert long_score.contributions["draw_on_liquidity"] == pytest.approx(10.0)
    assert short_score.contributions["draw_on_liquidity"] == pytest.approx(0.0)
    assert long_score.raw_score == pytest.approx(10.0)
    assert short_score.raw_score == pytest.approx(0.0)


def test_dol_v2_ranks_multiple_targets_and_exposes_primary_alternate():
    config = _config()
    config["draw_on_liquidity"]["candidate_sources"] = [
        "pdh_pdl",
        "pmh_pml",
        "asia_high_low",
        "loh_lol",
        "weekly_high_low",
        "external_swings",
        "equal_highs_lows",
        "fair_value_gaps",
    ]
    row = _row(
        htf_bias="bullish",
        recent_sell_side_sweep=True,
        external_premium_discount="discount",
        pdh=130.0,
        pdl=70.0,
        pmh=140.0,
        pml=60.0,
        ash=150.0,
        asl=50.0,
        loh=160.0,
        lol=40.0,
        week_high=170.0,
        week_low=30.0,
        external_swing_high_confirmed=True,
        external_swing_high_price=180.0,
        external_swing_high_timeframe="1h",
        external_swing_high_pivot_time=pd.Timestamp("2026-08-31 13:00:00", tz="UTC"),
        external_swing_high_equal=True,
        external_swing_high_equal_cluster_level=190.0,
        external_swing_high_equal_cluster_id="eqh-1",
        external_swing_high_equal_cluster_count=3,
        nearest_htf_fvg_above=200.0,
        distance_to_nearest_htf_fvg_above=100.0,
    )

    result = enrich_draw_on_liquidity(_frame(row), config).iloc[0]
    ranked = json.loads(result["dol_ranked_candidates"])

    assert result["dol_primary_direction"] == "bullish"
    assert result["dol_primary_target_type"] == "pdh"
    assert result["dol_primary_target_price"] == pytest.approx(130.0)
    assert result["dol_alternate_direction"] == "bearish"
    assert result["dol_alternate_target_type"] == "pdl"
    assert result["dol_alternate_target_price"] == pytest.approx(70.0)
    assert [candidate["distance_points"] for candidate in ranked[:7]] == sorted(
        candidate["distance_points"] for candidate in ranked[:7]
    )
    assert {
        candidate["category"] for candidate in ranked
    } >= {
        "pdh_pdl",
        "pmh_pml",
        "asia_high_low",
        "loh_lol",
        "weekly_high_low",
        "external_swings",
        "equal_highs_lows",
        "fair_value_gaps",
    }


def test_dol_v2_excludes_pool_after_causal_sweep():
    config = _config()
    config["draw_on_liquidity"]["candidate_sources"] = ["pdh_pdl", "pmh_pml"]
    first = _row(
        timestamp=pd.Timestamp("2026-08-31 14:00:00", tz="UTC"),
        pdh=130.0,
        pmh=140.0,
        nearest_unswept_liquidity_above=130.0,
        htf_bias="bullish",
        recent_sell_side_sweep=True,
        external_premium_discount="discount",
    )
    second = _row(
        timestamp=pd.Timestamp("2026-08-31 14:01:00", tz="UTC"),
        high=131.0,
        close=120.0,
        pdh=130.0,
        pmh=150.0,
        nearest_unswept_liquidity_above=150.0,
        nearest_unswept_liquidity_below=70.0,
        distance_to_unswept_liquidity_above=30.0,
        distance_to_unswept_liquidity_below=50.0,
        htf_bias="bullish",
        recent_sell_side_sweep=True,
        external_premium_discount="discount",
    )

    result = enrich_draw_on_liquidity(_frame(first, second), config)

    assert result.loc[0, "dol_primary_target_type"] == "pdh"
    assert result.loc[1, "dol_primary_target_type"] == "pmh"
    assert result.loc[1, "dol_primary_target_price"] == pytest.approx(150.0)


def test_dol_v2_structure_and_displacement_are_explainable_evidence():
    config = _config()
    row = _row(
        htf_bias="bullish",
        active_internal_swing_high_weak_liquidity=True,
        displacement_direction="bullish",
        displacement_category="strong",
    )

    result = enrich_draw_on_liquidity(_frame(row), config).iloc[0]
    components = json.loads(result["dol_primary_components"])

    assert result["dol_bullish_score"] == pytest.approx(5.0)
    assert "bullish_protected_weak_structure" in components["reasons"]
    assert "bullish_displacement" in components["reasons"]


def test_neutral_dol_does_not_publish_primary_or_alternate_targets():
    result = enrich_draw_on_liquidity(
        _frame(
            _row(
                htf_bias="bullish",
                recent_buy_side_sweep=True,
                external_premium_discount="premium",
            )
        ),
        _config(),
    ).iloc[0]

    assert result["dol_direction"] == "neutral"
    assert pd.isna(result["dol_primary_target_price"])
    assert pd.isna(result["dol_alternate_target_price"])
    assert json.loads(result["dol_ranked_candidates"]) == []


def test_future_pool_creation_does_not_rewrite_ranked_prefix():
    first = _row(
        timestamp=pd.Timestamp("2026-08-31 14:00:00", tz="UTC"),
        htf_bias="bullish",
        recent_sell_side_sweep=True,
        external_premium_discount="discount",
    )
    future = _row(
        timestamp=pd.Timestamp("2026-08-31 14:01:00", tz="UTC"),
        pdh=135.0,
        pmh=125.0,
        nearest_unswept_liquidity_above=125.0,
        distance_to_unswept_liquidity_above=25.0,
        htf_bias="bullish",
        recent_sell_side_sweep=True,
        external_premium_discount="discount",
    )

    before = enrich_draw_on_liquidity(_frame(first), _config())
    after = enrich_draw_on_liquidity(_frame(first, future), _config())

    columns = [
        "dol_primary_target_type",
        "dol_primary_target_price",
        "dol_primary_components",
        "dol_alternate_target_type",
        "dol_alternate_target_price",
        "dol_ranked_candidates",
    ]
    pd.testing.assert_frame_equal(
        before[columns],
        after.loc[:0, columns].reset_index(drop=True),
    )
