from __future__ import annotations

import pandas as pd
import pytest

import run_pipeline as pipeline


def bars():
    return pd.DataFrame({
        "timestamp": pd.date_range("2025-03-17T21:58:00Z", periods=4, freq="min"),
        "open": [100., 101., 300., 301.],
        "high": [102., 103., 302., 303.],
        "low": [99., 100., 299., 300.],
        "close": [101., 102., 301., 302.], "volume": [10, 10, 10, 10],
        "contract": ["NMH25", "NMH25", "NMM25", "NMM25"],
        "rollover_segment": [12, 12, 13, 13],
    })


@pytest.mark.parametrize("extension", ["parquet", "csv"])
@pytest.mark.parametrize("requested", [None, "NMH25"])
def test_loader_rejects_mixed_contracts_before_metadata_can_hide_them(tmp_path, extension, requested):
    path = tmp_path / f"bars.{extension}"
    frame = bars()
    if extension == "parquet":
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)
    before = path.read_bytes()
    with pytest.raises(pipeline.PipelineError, match="single-contract"):
        pipeline.stage_load(input_file=path, source="TEST", symbol="MNQ",
                            contract=requested, source_timezone="UTC")
    assert path.read_bytes() == before


@pytest.mark.parametrize("extension", ["parquet", "csv"])
def test_loader_preserves_single_contract_without_cli_override(tmp_path, extension):
    frame = bars().iloc[2:].copy()
    path = tmp_path / f"bars.{extension}"
    if extension == "parquet":
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)
    result = pipeline.stage_load(input_file=path, source="TEST", symbol="MNQ",
                                 contract=None, source_timezone="UTC")
    assert result.contract.tolist() == ["NMM25", "NMM25"]
    assert result.source.tolist() == ["TEST", "TEST"]


def test_loader_rejects_conflicting_explicit_contract(tmp_path):
    path = tmp_path / "bars.parquet"
    bars().iloc[2:].to_parquet(path, index=False)
    with pytest.raises(pipeline.PipelineError, match="conflicts"):
        pipeline.stage_load(input_file=path, source="TEST", symbol="MNQ",
                            contract="NMH25", source_timezone="UTC")


def test_multiple_segments_are_rejected_even_for_same_contract():
    frame = bars()
    frame["contract"] = "NMH25"
    with pytest.raises(pipeline.PipelineError, match="single-contract"):
        pipeline.require_single_contract_input(frame)


def test_partially_missing_contracts_are_rejected():
    frame = bars().iloc[:2].copy()
    frame.loc[0, "contract"] = None
    with pytest.raises(pipeline.PipelineError, match="missing"):
        pipeline.require_single_contract_input(frame)


def test_unlabelled_legacy_single_input_is_allowed():
    pipeline.require_single_contract_input(bars().drop(columns=["contract", "rollover_segment"]))


def test_resample_rejects_mixed_contracts_before_any_feature_or_output(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        pytest.fail("Mixed-contract input reached feature generation")
    monkeypatch.setattr(pipeline, "generate_standard_timeframes", forbidden)
    destination = tmp_path / "output"
    with pytest.raises(pipeline.PipelineError, match="single-contract"):
        pipeline.stage_resample(bars(), processed_directory=destination)
    assert not destination.exists()


def test_validation_rejects_mixed_contracts_without_writing_reports(tmp_path):
    with pytest.raises(pipeline.PipelineError, match="single-contract"):
        pipeline.stage_validate(bars(), results_directory=tmp_path / "results",
                                normalized_directory=tmp_path / "normalized")
    assert not (tmp_path / "results").exists()
    assert not (tmp_path / "normalized").exists()
