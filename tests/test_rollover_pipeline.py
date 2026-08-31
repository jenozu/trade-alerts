from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import run_pipeline as pipeline
from run_rollover_pipeline import (
    RolloverPipelineError,
    combine_enriched_segments,
    combine_segment_trades,
    isolated_pipeline_directories,
    load_stitched_csv,
    validate_stitched_frame,
    write_segment_input,
)


def _stitched_frame() -> pd.DataFrame:
    timestamps = pd.date_range(
        "2026-06-11 21:58:00",
        periods=4,
        freq="1min",
        tz="UTC",
    )
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [100.0, 101.0, 200.0, 201.0],
            "high": [101.0, 102.0, 201.0, 202.0],
            "low": [99.0, 100.0, 199.0, 200.0],
            "close": [100.5, 101.5, 200.5, 201.5],
            "volume": [10, 11, 20, 21],
            "source": ["PROJECTX"] * 4,
            "symbol": ["MNQ"] * 4,
            "contract": ["MNQM6", "MNQM6", "MNQU6", "MNQU6"],
            "rollover_segment": [0, 0, 1, 1],
            "rollover_boundary": [False, False, True, False],
            "rollover_from_contract": [pd.NA, pd.NA, "MNQM6", pd.NA],
            "rollover_to_contract": [pd.NA, pd.NA, "MNQU6", pd.NA],
        }
    )


def test_validate_stitched_frame_accepts_clean_contract_boundary():
    frame = _stitched_frame()
    validate_stitched_frame(frame)


def test_validate_stitched_frame_rejects_contract_change_without_boundary_marker():
    frame = _stitched_frame()
    frame.loc[2, "rollover_boundary"] = False

    with pytest.raises(RolloverPipelineError, match="Contract changes"):
        validate_stitched_frame(frame)


def test_load_stitched_csv_preserves_both_contracts_and_boundary(tmp_path):
    path = tmp_path / "stitched.csv"
    frame = _stitched_frame().copy()
    frame["timestamp"] = frame["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    frame.to_csv(path, index=False)

    loaded = load_stitched_csv(path)

    assert loaded["contract"].tolist() == ["MNQM6", "MNQM6", "MNQU6", "MNQU6"]
    assert loaded["rollover_segment"].astype(int).tolist() == [0, 0, 1, 1]
    assert loaded["rollover_boundary"].astype(bool).tolist() == [False, False, True, False]
    assert loaded.loc[1, "close"] == pytest.approx(101.5)
    assert loaded.loc[2, "open"] == pytest.approx(200.0)


def test_combine_enriched_segments_keeps_raw_price_jump_but_marks_boundary():
    frame = _stitched_frame()
    old_contract = frame.iloc[:2].copy().reset_index(drop=True)
    new_contract = frame.iloc[2:].copy().reset_index(drop=True)

    combined = combine_enriched_segments([old_contract, new_contract])

    assert combined.loc[1, "close"] == pytest.approx(101.5)
    assert combined.loc[2, "open"] == pytest.approx(200.0)
    assert bool(combined.loc[2, "rollover_boundary"])
    assert combined.loc[1, "contract"] == "MNQM6"
    assert combined.loc[2, "contract"] == "MNQU6"


def test_combine_segment_trades_offsets_indexes_and_preserves_contract_identity():
    first = pd.DataFrame(
        {
            "trade_id": [1],
            "signal_index": [0],
            "entry_index": [1],
            "exit_index": [1],
            "entry_time": [pd.Timestamp("2026-06-11 21:59:00", tz="UTC")],
            "net_result_points": [5.0],
        }
    )
    second = pd.DataFrame(
        {
            "trade_id": [1],
            "signal_index": [0],
            "entry_index": [1],
            "exit_index": [1],
            "entry_time": [pd.Timestamp("2026-06-11 22:01:00", tz="UTC")],
            "net_result_points": [-5.0],
        }
    )

    combined = combine_segment_trades(
        [first, second],
        segment_lengths=[2, 2],
        contracts=["MNQM6", "MNQU6"],
    )

    assert combined["trade_id"].tolist() == [1, 2]
    assert combined["segment_trade_id"].tolist() == [1, 1]
    assert combined["contract"].tolist() == ["MNQM6", "MNQU6"]
    assert combined["rollover_segment"].tolist() == [0, 1]
    assert combined["signal_index"].tolist() == [0, 2]
    assert combined["entry_index"].tolist() == [1, 3]
    assert combined["exit_index"].tolist() == [1, 3]


def test_write_segment_input_keeps_contract_and_removes_redundant_timestamp_et(tmp_path):
    segment = _stitched_frame().iloc[:2].copy().reset_index(drop=True)
    segment["timestamp_et"] = segment["timestamp"].dt.tz_convert("America/New_York")

    path = write_segment_input(segment, tmp_path / "segment.csv")
    written = pd.read_csv(path)

    assert "timestamp_et" not in written.columns
    assert written["contract"].tolist() == ["MNQM6", "MNQM6"]
    assert written["timestamp"].iloc[0].endswith("Z")
    assert written["rollover_segment"].tolist() == [0, 0]


def test_isolated_pipeline_directories_are_restored_after_context(tmp_path):
    old_processed = pipeline.DEFAULT_PROCESSED_DIRECTORY
    old_results = pipeline.DEFAULT_RESULTS_DIRECTORY
    old_normalized = pipeline.DEFAULT_NORMALIZED_DIRECTORY

    processed = tmp_path / "processed"
    results = tmp_path / "results"
    normalized = tmp_path / "normalized"

    with isolated_pipeline_directories(
        processed_directory=processed,
        results_directory=results,
        normalized_directory=normalized,
    ):
        assert pipeline.DEFAULT_PROCESSED_DIRECTORY == processed
        assert pipeline.DEFAULT_RESULTS_DIRECTORY == results
        assert pipeline.DEFAULT_NORMALIZED_DIRECTORY == normalized

    assert pipeline.DEFAULT_PROCESSED_DIRECTORY == old_processed
    assert pipeline.DEFAULT_RESULTS_DIRECTORY == old_results
    assert pipeline.DEFAULT_NORMALIZED_DIRECTORY == old_normalized
