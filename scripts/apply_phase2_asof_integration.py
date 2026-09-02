from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "run_pipeline.py"
TEST_FILE = ROOT / "tests" / "test_pipeline_as_of.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match, found {count}.")
    return text.replace(old, new, 1)


def main() -> None:
    text = PIPELINE.read_text(encoding="utf-8")

    if "from data_clock import" in text or "--as-of" in text:
        raise RuntimeError("run_pipeline.py already appears to contain as-of integration.")

    text = replace_once(
        text,
        'from data_loader import DatasetMetadata, load_csv, save_parquet  # noqa: E402\n',
        'from data_loader import DatasetMetadata, load_csv, save_parquet  # noqa: E402\n'
        'from data_clock import (  # noqa: E402\n'
        '    filter_as_of,\n'
        '    filter_resampled_results_as_of,\n'
        '    normalize_as_of,\n'
        '    summarize_as_of,\n'
        ')\n',
        "data_clock import insertion",
    )

    text = replace_once(
        text,
        '''def create_run_metadata(\n    *,\n    input_file: Path,\n    source: str,\n    symbol: str,\n    contract: str | None,\n    source_timezone: str,\n    sessions_config: dict[str, Any],\n    strategy_config: dict[str, Any],\n) -> dict[str, Any]:\n''',
        '''def create_run_metadata(\n    *,\n    input_file: Path,\n    source: str,\n    symbol: str,\n    contract: str | None,\n    source_timezone: str,\n    sessions_config: dict[str, Any],\n    strategy_config: dict[str, Any],\n    as_of: pd.Timestamp | None = None,\n) -> dict[str, Any]:\n''',
        "create_run_metadata signature",
    )

    text = replace_once(
        text,
        '''        "source_timezone": source_timezone,\n        "session_config_version": sessions_config.get("metadata", {}).get("config_version"),\n''',
        '''        "source_timezone": source_timezone,\n        "as_of": as_of.isoformat() if as_of is not None else None,\n        "session_config_version": sessions_config.get("metadata", {}).get("config_version"),\n''',
        "metadata as_of field",
    )

    text = replace_once(
        text,
        '''def stage_resample(\n    dataframe: pd.DataFrame,\n    *,\n    processed_directory: Path,\n) -> dict[str, Any]:\n    output_directory = processed_directory / "timeframes"\n    results = generate_standard_timeframes(dataframe)\n''',
        '''def stage_resample(\n    dataframe: pd.DataFrame,\n    *,\n    processed_directory: Path,\n    as_of: Any | None = None,\n) -> dict[str, Any]:\n    output_directory = processed_directory / "timeframes"\n    results = generate_standard_timeframes(dataframe)\n    if as_of is not None:\n        results = filter_resampled_results_as_of(results, as_of=as_of)\n''',
        "stage_resample as_of integration",
    )

    text = replace_once(
        text,
        '''def run_pipeline(\n    *,\n    input_file: Path,\n    source: str,\n    symbol: str,\n    contract: str | None,\n    source_timezone: str,\n    sessions_config_path: Path,\n    strategy_config_path: Path,\n    stop_after: str | None = None,\n) -> dict[str, Any]:\n''',
        '''def run_pipeline(\n    *,\n    input_file: Path,\n    source: str,\n    symbol: str,\n    contract: str | None,\n    source_timezone: str,\n    sessions_config_path: Path,\n    strategy_config_path: Path,\n    stop_after: str | None = None,\n    as_of: Any | None = None,\n) -> dict[str, Any]:\n''',
        "run_pipeline signature",
    )

    text = replace_once(
        text,
        '''    print(f"Contract:  {contract}")\n    print(f"Timezone:  {source_timezone}")\n\n    sessions_config = load_sessions_config(sessions_config_path)\n''',
        '''    print(f"Contract:  {contract}")\n    print(f"Timezone:  {source_timezone}")\n    as_of_utc = normalize_as_of(as_of) if as_of is not None else None\n    print(f"As of:     {as_of_utc.isoformat() if as_of_utc is not None else 'FULL DATASET'}")\n\n    sessions_config = load_sessions_config(sessions_config_path)\n''',
        "run_pipeline as_of normalization",
    )

    text = replace_once(
        text,
        '''        source_timezone=source_timezone,\n        sessions_config=sessions_config,\n        strategy_config=strategy_config,\n    )\n''',
        '''        source_timezone=source_timezone,\n        sessions_config=sessions_config,\n        strategy_config=strategy_config,\n        as_of=as_of_utc,\n    )\n''',
        "create_run_metadata call",
    )

    text = replace_once(
        text,
        '''        data = stage_load(\n            input_file=input_file,\n            source=source,\n            symbol=symbol,\n            contract=contract,\n            source_timezone=source_timezone,\n        )\n        record_stage(run_metadata, "load", status="passed", details=dataframe_health_summary(data))\n        if stop_after == "load":\n            return {"data": data, "metadata": run_metadata}\n''',
        '''        data = stage_load(\n            input_file=input_file,\n            source=source,\n            symbol=symbol,\n            contract=contract,\n            source_timezone=source_timezone,\n        )\n        load_details = dataframe_health_summary(data)\n        if as_of_utc is not None:\n            clock_summary = summarize_as_of(data, as_of=as_of_utc)\n            data = filter_as_of(data, as_of=as_of_utc)\n            if data.empty:\n                raise PipelineError(\n                    f"No completed one-minute bars are available by as_of={as_of_utc.isoformat()}."\n                )\n            run_metadata["data_clock"] = {\n                "as_of": as_of_utc.isoformat(),\n                "rows_in": clock_summary.rows_in,\n                "rows_visible": clock_summary.rows_visible,\n                "rows_hidden": clock_summary.rows_hidden,\n                "first_visible_timestamp": str(clock_summary.first_visible_timestamp),\n                "last_visible_timestamp": str(clock_summary.last_visible_timestamp),\n                "last_visible_available_at": str(clock_summary.last_visible_available_at),\n            }\n            load_details = dataframe_health_summary(data)\n            load_details.update(\n                {\n                    "as_of": as_of_utc.isoformat(),\n                    "rows_before_as_of": clock_summary.rows_in,\n                    "rows_hidden_by_as_of": clock_summary.rows_hidden,\n                }\n            )\n            print(\n                f"As-of cutoff: {clock_summary.rows_visible:,}/{clock_summary.rows_in:,} "\n                f"completed 1m bars visible; {clock_summary.rows_hidden:,} hidden."\n            )\n        record_stage(run_metadata, "load", status="passed", details=load_details)\n        if stop_after == "load":\n            save_run_metadata(run_metadata, audit_file)\n            return {"data": data, "metadata": run_metadata}\n''',
        "load-stage as_of cutoff",
    )

    text = replace_once(
        text,
        '''        resampled = stage_resample(data, processed_directory=processed_directory)\n''',
        '''        resampled = stage_resample(\n            data,\n            processed_directory=processed_directory,\n            as_of=as_of_utc,\n        )\n''',
        "resample call",
    )

    text = replace_once(
        text,
        '''    parser.add_argument(\n        "--stop-after",\n        choices=PIPELINE_STAGES,\n        default=None,\n        help="Stop pipeline after a specific stage. Useful while debugging.",\n    )\n''',
        '''    parser.add_argument(\n        "--as-of",\n        default=None,\n        help=(\n            "Optional timezone-aware replay cutoff. Example: "\n            "2026-08-10T09:00:00-04:00. Only completed data available by this "\n            "timestamp may influence the pipeline."\n        ),\n    )\n    parser.add_argument(\n        "--stop-after",\n        choices=PIPELINE_STAGES,\n        default=None,\n        help="Stop pipeline after a specific stage. Useful while debugging.",\n    )\n''',
        "--as-of CLI argument",
    )

    text = replace_once(
        text,
        '''        strategy_config_path=Path(args.strategy_config),\n        stop_after=args.stop_after,\n    )\n''',
        '''        strategy_config_path=Path(args.strategy_config),\n        stop_after=args.stop_after,\n        as_of=args.as_of,\n    )\n''',
        "main as_of forwarding",
    )

    PIPELINE.write_text(text, encoding="utf-8")

    TEST_FILE.write_text(
        '''from __future__ import annotations\n\nimport sys\nfrom pathlib import Path\n\nimport pandas as pd\nimport pytest\n\nimport run_pipeline as pipeline\nfrom data_clock import DataClockError\n\n\ndef _bars() -> pd.DataFrame:\n    timestamps = pd.date_range(\n        "2026-06-01T12:55:00Z",\n        periods=8,\n        freq="1min",\n    )\n    base = pd.Series(range(len(timestamps)), dtype=float)\n    return pd.DataFrame(\n        {\n            "timestamp": timestamps,\n            "open": 100.0 + base,\n            "high": 101.0 + base,\n            "low": 99.0 + base,\n            "close": 100.5 + base,\n            "volume": 10 + base,\n            "source": "TEST",\n            "symbol": "MNQ",\n            "contract": "MNQM6",\n        }\n    )\n\n\ndef _run_kwargs(tmp_path: Path) -> dict:\n    return {\n        "input_file": tmp_path / "ignored.csv",\n        "source": "TEST",\n        "symbol": "MNQ",\n        "contract": "MNQM6",\n        "source_timezone": "UTC",\n        "sessions_config_path": tmp_path / "sessions.yaml",\n        "strategy_config_path": tmp_path / "strategy.yaml",\n    }\n\n\ndef _stub_startup(monkeypatch, dataframe: pd.DataFrame) -> None:\n    monkeypatch.setattr(pipeline, "load_sessions_config", lambda _: {})\n    monkeypatch.setattr(pipeline, "load_yaml", lambda _: {})\n    monkeypatch.setattr(pipeline, "save_run_metadata", lambda *args, **kwargs: None)\n    monkeypatch.setattr(pipeline, "stage_load", lambda **kwargs: dataframe.copy())\n\n\ndef test_parse_arguments_accepts_timezone_aware_as_of(monkeypatch) -> None:\n    monkeypatch.setattr(\n        sys,\n        "argv",\n        [\n            "run_pipeline.py",\n            "--input",\n            "sample.csv",\n            "--as-of",\n            "2026-06-01T09:00:00-04:00",\n        ],\n    )\n    args = pipeline.parse_arguments()\n    assert args.as_of == "2026-06-01T09:00:00-04:00"\n\n\ndef test_pipeline_stop_after_load_applies_one_minute_as_of(monkeypatch, tmp_path) -> None:\n    dataframe = _bars()\n    _stub_startup(monkeypatch, dataframe)\n\n    result = pipeline.run_pipeline(\n        **_run_kwargs(tmp_path),\n        stop_after="load",\n        as_of="2026-06-01T09:00:00-04:00",\n    )\n\n    visible = result["data"]\n    assert len(visible) == 5\n    assert visible["timestamp"].iloc[-1] == pd.Timestamp("2026-06-01T12:59:00Z")\n    assert result["metadata"]["as_of"] == "2026-06-01T13:00:00+00:00"\n    assert result["metadata"]["data_clock"]["rows_visible"] == 5\n    assert result["metadata"]["data_clock"]["rows_hidden"] == 3\n\n\ndef test_pipeline_without_as_of_preserves_existing_full_dataset_behavior(\n    monkeypatch, tmp_path\n) -> None:\n    dataframe = _bars()\n    _stub_startup(monkeypatch, dataframe)\n\n    result = pipeline.run_pipeline(\n        **_run_kwargs(tmp_path),\n        stop_after="load",\n        as_of=None,\n    )\n\n    assert len(result["data"]) == len(dataframe)\n    assert result["metadata"]["as_of"] is None\n    assert "data_clock" not in result["metadata"]\n\n\ndef test_pipeline_rejects_naive_as_of_before_processing(monkeypatch, tmp_path) -> None:\n    _stub_startup(monkeypatch, _bars())\n\n    with pytest.raises(DataClockError, match="timezone-aware"):\n        pipeline.run_pipeline(\n            **_run_kwargs(tmp_path),\n            stop_after="load",\n            as_of="2026-06-01 09:00:00",\n        )\n\n\ndef test_stage_resample_hides_partial_higher_timeframe_bar(tmp_path) -> None:\n    results = pipeline.stage_resample(\n        _bars(),\n        processed_directory=tmp_path,\n        as_of="2026-06-01T09:03:00-04:00",\n    )\n\n    one_minute = results["1m"].dataframe\n    five_minute = results["5m"].dataframe\n\n    assert len(one_minute) == 8\n    assert len(five_minute) == 1\n    assert five_minute.loc[0, "timestamp"] == pd.Timestamp("2026-06-01T12:55:00Z")\n    assert five_minute.loc[0, "available_at"] == pd.Timestamp("2026-06-01T13:00:00Z")\n    assert five_minute["bar_complete"].all()\n''',
        encoding="utf-8",
    )

    print("Updated run_pipeline.py with canonical --as-of integration.")
    print(f"Created {TEST_FILE.relative_to(ROOT)} with 5 integration tests.")
    print("This helper will now remove itself; commit the resulting run_pipeline/test changes after tests pass.")

    Path(__file__).unlink()


if __name__ == "__main__":
    main()
