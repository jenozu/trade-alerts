from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

import run_pipeline as pipeline
from data_clock import DataClockError
from sessions import load_sessions_config


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


def test_validate_stage_records_pass_status_for_clean_data(monkeypatch, tmp_path) -> None:
    _stub_startup(monkeypatch, _bars())
    monkeypatch.setattr(
        pipeline, "DEFAULT_RESULTS_DIRECTORY", tmp_path / "results"
    )
    monkeypatch.setattr(
        pipeline, "DEFAULT_NORMALIZED_DIRECTORY", tmp_path / "normalized"
    )

    result = pipeline.run_pipeline(
        **_run_kwargs(tmp_path),
        stop_after="validate",
    )

    details = result["metadata"]["stages"]["validate"]["details"]
    assert details["analysis_status"] == "pass"
    assert details["analysis_status_reasons"] == []


def test_validate_stage_records_degraded_status_for_material_warning(
    monkeypatch, tmp_path
) -> None:
    dataframe = _bars()
    # Off-tick price: structurally valid OHLC but a material warning.
    dataframe.loc[3, "open"] = 103.13
    _stub_startup(monkeypatch, dataframe)
    # allow_zero_volume_bars is honored from the validation config block; the
    # off-tick warning is not allowed, so the run is degraded, not failed.
    monkeypatch.setattr(
        pipeline,
        "load_sessions_config",
        lambda _: {"validation": {"allow_zero_volume_bars": True}},
    )
    monkeypatch.setattr(
        pipeline, "DEFAULT_RESULTS_DIRECTORY", tmp_path / "results"
    )
    monkeypatch.setattr(
        pipeline, "DEFAULT_NORMALIZED_DIRECTORY", tmp_path / "normalized"
    )

    result = pipeline.run_pipeline(
        **_run_kwargs(tmp_path),
        stop_after="validate",
    )

    details = result["metadata"]["stages"]["validate"]["details"]
    assert details["analysis_status"] == "degraded"
    assert any(
        "off_tick_prices" in reason
        for reason in details["analysis_status_reasons"]
    )


def _morning_records(dense: bool) -> pd.DataFrame:
    """1m bars for the Globex session dated Mon 2026-06-01.

    Dense: every minute from May 31 18:00 ET (session open) through Jun 1
    08:59 ET (900 completed bars; the last completes at 09:00 ET). Sparse:
    the same session with only a handful of isolated representative bars.
    """
    if dense:
        timestamps = pd.date_range(
            "2026-05-31T22:00:00Z", periods=900, freq="1min"
        )
    else:
        timestamps = pd.to_datetime(
            [
                "2026-05-31T22:00:00Z",   # May31 18:00 ET: overnight open
                "2026-06-01T00:30:00Z",   # May31 20:30 ET: asia
                "2026-06-01T06:30:00Z",   # Jun1 02:30 ET: london
                "2026-06-01T10:00:00Z",   # Jun1 06:00 ET: premarket
                "2026-06-01T13:00:00Z",   # Jun1 09:00 ET: premarket
                "2026-06-01T13:02:00Z",   # Jun1 09:02 ET: premarket
            ],
            utc=True,
        )
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": [10.0] * len(timestamps),
            "source": ["TEST"] * len(timestamps),
            "symbol": ["MNQ"] * len(timestamps),
            "contract": ["MNQM6"] * len(timestamps),
        }
    )


def _dense_morning_dataframe() -> pd.DataFrame:
    """Completed 1m bars covering every required morning session of the
    Globex session dated Mon 2026-06-01 with no gaps at all."""
    return _morning_records(dense=True)


def _sparse_morning_dataframe() -> pd.DataFrame:
    """Isolated 1m bars, one per required session window (no full minute
    coverage): presence without completeness."""
    return _morning_records(dense=False)


def test_validate_stage_aborts_when_required_sessions_missing(monkeypatch, tmp_path) -> None:
    real_config = load_sessions_config("config/sessions.yaml")
    _stub_startup(monkeypatch, _bars())
    monkeypatch.setattr(pipeline, "load_sessions_config", lambda _: real_config)
    monkeypatch.setattr(
        pipeline, "DEFAULT_RESULTS_DIRECTORY", tmp_path / "results"
    )
    monkeypatch.setattr(
        pipeline, "DEFAULT_NORMALIZED_DIRECTORY", tmp_path / "normalized"
    )
    captured: list[dict] = []
    monkeypatch.setattr(
        pipeline, "save_run_metadata", lambda metadata, filepath: captured.append(metadata)
    )

    # The 08:55-09:02 ET morning-only fixture has no overnight/Asia bars and
    # only a fragment of the premarket/overnight windows; every required
    # window is due and incomplete by the data's end, so validation must
    # refuse analysis instead of continuing into resampling.
    with pytest.raises(pipeline.PipelineError, match="required-session coverage"):
        pipeline.run_pipeline(
            **_run_kwargs(tmp_path),
            stop_after="validate",
        )

    assert captured, "run metadata was never saved"
    validate = captured[-1]["stages"]["validate"]
    assert validate["status"] == "no_analysis"
    details = validate["details"]
    assert details["analysis_status"] == "no_analysis"
    assert details["session_coverage"]["all_covered"] is False
    assert set(details["session_coverage"]["missing"]) == {
        "overnight",
        "london",
        "asia",
        "premarket",
    }
    assert details["session_coverage"]["all_due_covered"] is False


def test_validate_stage_records_required_session_coverage(monkeypatch, tmp_path) -> None:
    real_config = load_sessions_config("config/sessions.yaml")
    _stub_startup(monkeypatch, _dense_morning_dataframe())
    monkeypatch.setattr(pipeline, "load_sessions_config", lambda _: real_config)
    monkeypatch.setattr(
        pipeline, "DEFAULT_RESULTS_DIRECTORY", tmp_path / "results"
    )
    monkeypatch.setattr(
        pipeline, "DEFAULT_NORMALIZED_DIRECTORY", tmp_path / "normalized"
    )

    result = pipeline.run_pipeline(
        **_run_kwargs(tmp_path),
        stop_after="validate",
    )

    details = result["metadata"]["stages"]["validate"]["details"]
    coverage = details["session_coverage"]
    assert coverage is not None
    assert coverage["as_of"] is None
    assert coverage["missing"] == []
    assert coverage["all_covered"] is True
    assert coverage["all_due_covered"] is True
    # Fully dense required-session coverage plus no other material warnings:
    # the clean dataset is analysis-ready.
    assert details["analysis_status"] == "pass"


def test_sparse_required_sessions_abort_before_resample(monkeypatch, tmp_path) -> None:
    """A fragment in every required window is not coverage: missing expected
    minutes must produce no_analysis and stop the pipeline before resample."""
    real_config = load_sessions_config("config/sessions.yaml")
    _stub_startup(monkeypatch, _sparse_morning_dataframe())
    monkeypatch.setattr(pipeline, "load_sessions_config", lambda _: real_config)
    monkeypatch.setattr(
        pipeline, "DEFAULT_RESULTS_DIRECTORY", tmp_path / "results"
    )
    monkeypatch.setattr(
        pipeline, "DEFAULT_NORMALIZED_DIRECTORY", tmp_path / "normalized"
    )
    monkeypatch.setattr(
        pipeline, "DEFAULT_PROCESSED_DIRECTORY", tmp_path / "processed"
    )
    captured: list[dict] = []
    monkeypatch.setattr(
        pipeline, "save_run_metadata", lambda metadata, filepath: captured.append(metadata)
    )

    with pytest.raises(pipeline.PipelineError, match="no_analysis"):
        pipeline.run_pipeline(
            **_run_kwargs(tmp_path),
            stop_after="resample",
        )
    # Resampling must never run: no processed timeframe output directory.
    assert not (tmp_path / "processed").exists()
    validate = captured[-1]["stages"]["validate"]
    assert validate["status"] == "no_analysis"
    details = validate["details"]
    assert details["analysis_status"] == "no_analysis"
    assert details["session_coverage"]["all_due_covered"] is False
    assert set(details["session_coverage"]["missing_due"]) == {
        "overnight",
        "london",
        "asia",
        "premarket",
    }


def test_missing_required_sessions_stop_before_resample(monkeypatch, tmp_path) -> None:
    real_config = load_sessions_config("config/sessions.yaml")
    _stub_startup(monkeypatch, _bars())
    monkeypatch.setattr(pipeline, "load_sessions_config", lambda _: real_config)
    monkeypatch.setattr(
        pipeline, "DEFAULT_RESULTS_DIRECTORY", tmp_path / "results"
    )
    monkeypatch.setattr(
        pipeline, "DEFAULT_NORMALIZED_DIRECTORY", tmp_path / "normalized"
    )
    monkeypatch.setattr(
        pipeline, "DEFAULT_PROCESSED_DIRECTORY", tmp_path / "processed"
    )

    with pytest.raises(pipeline.PipelineError):
        pipeline.run_pipeline(
            **_run_kwargs(tmp_path),
            stop_after="resample",
        )
    # Resampling must never run when required sessions are missing: no
    # processed timeframe output directory is created.
    assert not (tmp_path / "processed").exists()
