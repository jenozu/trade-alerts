from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

import run_pipeline as pipeline
from data_clock import DataClockError


def _bars() -> pd.DataFrame:
    timestamps = pd.date_range(
        "2026-06-01T12:55:00Z",
        periods=8,
        freq="1min",
    )
    base = pd.Series(range(len(timestamps)), dtype=float)
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": 100.0 + base,
            "high": 101.0 + base,
            "low": 99.0 + base,
            "close": 100.5 + base,
            "volume": 10 + base,
            "source": "TEST",
            "symbol": "MNQ",
            "contract": "MNQM6",
        }
    )


def _run_kwargs(tmp_path: Path) -> dict:
    return {
        "input_file": tmp_path / "ignored.csv",
        "source": "TEST",
        "symbol": "MNQ",
        "contract": "MNQM6",
        "source_timezone": "UTC",
        "sessions_config_path": tmp_path / "sessions.yaml",
        "strategy_config_path": tmp_path / "strategy.yaml",
    }


def _stub_startup(monkeypatch, dataframe: pd.DataFrame) -> None:
    monkeypatch.setattr(pipeline, "load_sessions_config", lambda _: {})
    monkeypatch.setattr(pipeline, "load_yaml", lambda _: {})
    monkeypatch.setattr(pipeline, "save_run_metadata", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline, "stage_load", lambda **kwargs: dataframe.copy())


def test_parse_arguments_accepts_timezone_aware_as_of(monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_pipeline.py",
            "--input",
            "sample.csv",
            "--as-of",
            "2026-06-01T09:00:00-04:00",
        ],
    )
    args = pipeline.parse_arguments()
    assert args.as_of == "2026-06-01T09:00:00-04:00"


def test_pipeline_stop_after_load_applies_one_minute_as_of(monkeypatch, tmp_path) -> None:
    dataframe = _bars()
    _stub_startup(monkeypatch, dataframe)

    result = pipeline.run_pipeline(
        **_run_kwargs(tmp_path),
        stop_after="load",
        as_of="2026-06-01T09:00:00-04:00",
    )

    visible = result["data"]
    assert len(visible) == 5
    assert visible["timestamp"].iloc[-1] == pd.Timestamp("2026-06-01T12:59:00Z")
    assert result["metadata"]["as_of"] == "2026-06-01T13:00:00+00:00"
    assert result["metadata"]["data_clock"]["rows_visible"] == 5
    assert result["metadata"]["data_clock"]["rows_hidden"] == 3


def test_pipeline_without_as_of_preserves_existing_full_dataset_behavior(
    monkeypatch, tmp_path
) -> None:
    dataframe = _bars()
    _stub_startup(monkeypatch, dataframe)

    result = pipeline.run_pipeline(
        **_run_kwargs(tmp_path),
        stop_after="load",
        as_of=None,
    )

    assert len(result["data"]) == len(dataframe)
    assert result["metadata"]["as_of"] is None
    assert "data_clock" not in result["metadata"]


def test_pipeline_rejects_naive_as_of_before_processing(monkeypatch, tmp_path) -> None:
    _stub_startup(monkeypatch, _bars())

    with pytest.raises(DataClockError, match="timezone-aware"):
        pipeline.run_pipeline(
            **_run_kwargs(tmp_path),
            stop_after="load",
            as_of="2026-06-01 09:00:00",
        )


def test_stage_resample_hides_partial_higher_timeframe_bar(tmp_path) -> None:
    results = pipeline.stage_resample(
        _bars(),
        processed_directory=tmp_path,
        as_of="2026-06-01T09:03:00-04:00",
    )

    one_minute = results["1m"].dataframe
    five_minute = results["5m"].dataframe

    assert len(one_minute) == 8
    assert len(five_minute) == 1
    assert five_minute.loc[0, "timestamp"] == pd.Timestamp("2026-06-01T12:55:00Z")
    assert five_minute.loc[0, "available_at"] == pd.Timestamp("2026-06-01T13:00:00Z")
    assert five_minute["bar_complete"].all()
