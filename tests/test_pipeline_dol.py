from __future__ import annotations

import sys

import pandas as pd

import run_pipeline as pipeline


def _strategy_config() -> dict:
    return {
        "market": {"tick_size": 0.25},
        "room_to_target": {"minimum_points": 25.0},
        "draw_on_liquidity": {
            "enabled": True,
            "candidate_sources": ["pdh_pdl"],
            "minimum_target_distance_points": 25.0,
            "decision_threshold": 3.0,
            "minimum_score_edge": 1.0,
        },
    }


def test_pipeline_places_dol_between_structure_and_scoring() -> None:
    stages = pipeline.PIPELINE_STAGES

    assert "dol" in stages
    assert stages.index("structure") < stages.index("dol")
    assert stages.index("dol") < stages.index("scoring")


def test_stage_dol_enriches_dataframe_and_saves_outputs(tmp_path) -> None:
    dataframe = pd.DataFrame(
        {
            "timestamp": [pd.Timestamp("2026-06-01T14:00:00Z")],
            "close": [100.0],
            "htf_bias": ["bullish"],
            "pdh": [130.0],
            "nearest_unswept_liquidity_above": [130.0],
            "distance_to_unswept_liquidity_above": [30.0],
            "recent_sell_side_sweep": [True],
            "external_premium_discount": ["discount"],
        }
    )

    enriched = pipeline.stage_dol(
        dataframe,
        strategy_config=_strategy_config(),
        processed_directory=tmp_path,
    )

    assert enriched.loc[0, "dol_direction"] == "bullish"
    assert enriched.loc[0, "draw_on_liquidity_direction"] == "bullish"
    assert enriched.loc[0, "dol_target_type"] == "pdh"
    assert enriched.loc[0, "dol_target_price"] == 130.0
    assert enriched.loc[0, "dol_distance_points"] == 30.0

    assert (tmp_path / "dol" / "nq_1m_dol.parquet").exists()
    assert (tmp_path / "dol" / "dol_distribution.csv").exists()


def test_stop_after_accepts_dol(monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_pipeline.py", "--input", "sample.csv", "--stop-after", "dol"],
    )

    args = pipeline.parse_arguments()

    assert args.stop_after == "dol"
