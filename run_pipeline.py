from __future__ import annotations

import argparse
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIRECTORY = PROJECT_ROOT / "src"
if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))

from data_loader import DatasetMetadata, load_csv, save_parquet  # noqa: E402
from data_clock import (  # noqa: E402
    filter_as_of,
    filter_resampled_results_as_of,
    normalize_as_of,
    summarize_as_of,
    visibility_times,
)
from validate_data import (  # noqa: E402
    AnalysisStatus,
    STATUS_NO_ANALYSIS,
    allowed_warnings_from_validation_config,
    classify_analysis_status,
    validate_market_data,
    print_validation_report,
    save_validation_report_json,
    save_coverage_reports,
)
from resample import (  # noqa: E402
    generate_standard_timeframes,
    validate_resampled_bars,
    save_resampled_parquet,
)
from bias import (  # noqa: E402
    enrich_htf_bias,
    bias_summary,
    save_bias_outputs,
)
from sessions import (  # noqa: E402
    load_sessions_config,
    enrich_with_sessions,
    required_session_coverage,
    save_session_outputs,
)
from vwap import enrich_vwap, save_vwap_outputs  # noqa: E402
from volume import (  # noqa: E402
    enrich_volume_features,
    volume_summary,
    save_volume_outputs,
)
from snr import (  # noqa: E402
    build_multitimeframe_snr,
    snr_summary,
    save_snr_outputs,
)
from swings import (  # noqa: E402
    enrich_swings,
    swing_summary,
    save_swing_outputs,
)
from liquidity import (  # noqa: E402
    enrich_liquidity_features,
    liquidity_summary,
    save_liquidity_outputs,
)
from fvg import enrich_fvg_features, fvg_summary, save_fvg_outputs  # noqa: E402
from pd_arrays import (  # noqa: E402
    enrich_pd_array_features,
    pd_array_summary,
    save_pd_array_outputs,
)
from structure import (  # noqa: E402
    enrich_structure_features,
    structure_summary,
    save_structure_outputs,
)
from dealing_range import enrich_dealing_ranges  # noqa: E402
from dol import (  # noqa: E402
    enrich_draw_on_liquidity,
    dol_summary,
    save_dol_outputs,
)
from scorer import (  # noqa: E402
    enrich_scores,
    add_score_change_events,
    scoring_summary,
    save_scoring_outputs,
)
from market_state import (  # noqa: E402
    build_market_state,
    save_market_state_snapshot,
)
from trade_planner import build_trade_plan  # noqa: E402
from backtest import (  # noqa: E402
    run_backtest,
    calculate_backtest_metrics,
    save_backtest_outputs,
)

DEFAULT_SESSION_CONFIG = PROJECT_ROOT / "config" / "sessions.yaml"
DEFAULT_STRATEGY_CONFIG = PROJECT_ROOT / "config" / "strategy.yaml"
DEFAULT_RESULTS_DIRECTORY = PROJECT_ROOT / "data" / "results"
DEFAULT_PROCESSED_DIRECTORY = PROJECT_ROOT / "data" / "processed"
DEFAULT_NORMALIZED_DIRECTORY = PROJECT_ROOT / "data" / "normalized"
DEFAULT_STATE_DIRECTORY = PROJECT_ROOT / "data" / "state"


class PipelineError(RuntimeError):
    """Raised when the end-to-end research pipeline fails."""


PIPELINE_STAGES = [
    "load",
    "validate",
    "resample",
    "bias",
    "sessions",
    "vwap",
    "volume",
    "snr",
    "swings",
    "liquidity",
    "fvg",
    "pd_arrays",
    "structure",
    "dealing_range",
    "dol",
    "scoring",
    "market_state",
    "trade_plan",
    "backtest",
]


def print_header(text: str) -> None:
    print("\n============================================================")
    print(text)
    print("============================================================")


def print_stage(stage_number: int, total_stages: int, name: str) -> None:
    print(f"\n[{stage_number}/{total_stages}] {name.upper()}")
    print("-" * 60)


def load_yaml(filepath: Path) -> dict[str, Any]:
    if not filepath.exists():
        raise FileNotFoundError(f"Configuration file not found: {filepath}")
    with filepath.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    if not isinstance(config, dict):
        raise PipelineError(f"Invalid YAML configuration: {filepath}")
    return config


def ensure_datetime_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    if "timestamp" in result.columns:
        result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True)
    if "timestamp_et" in result.columns:
        result["timestamp_et"] = result["timestamp"].dt.tz_convert("America/New_York")
    return result


def dataframe_health_summary(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"rows": 0}
    result: dict[str, Any] = {"rows": int(len(df))}
    if "timestamp" in df.columns:
        result["start"] = str(df["timestamp"].min())
        result["end"] = str(df["timestamp"].max())
    return result


def create_run_metadata(
    *,
    input_file: Path,
    source: str,
    symbol: str,
    contract: str | None,
    source_timezone: str,
    sessions_config: dict[str, Any],
    strategy_config: dict[str, Any],
    as_of: pd.Timestamp | None = None,
) -> dict[str, Any]:
    return {
        "run_started_at": datetime.now().astimezone().isoformat(),
        "input_file": str(input_file.resolve()),
        "source": source,
        "symbol": symbol,
        "contract": contract,
        "source_timezone": source_timezone,
        "as_of": as_of.isoformat() if as_of is not None else None,
        "session_config_version": sessions_config.get("metadata", {}).get("config_version"),
        "strategy_config_version": strategy_config.get("metadata", {}).get("config_version"),
        "strategy_name": strategy_config.get("metadata", {}).get("strategy_name"),
        "status": "running",
        "stages": {},
    }


def record_stage(
    run_metadata: dict[str, Any],
    stage: str,
    *,
    status: str,
    details: dict[str, Any] | None = None,
) -> None:
    run_metadata["stages"][stage] = {
        "status": status,
        "completed_at": datetime.now().astimezone().isoformat(),
        "details": details or {},
    }


def save_run_metadata(metadata: dict[str, Any], filepath: Path) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with filepath.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2, default=str)


def stage_load(
    *,
    input_file: Path,
    source: str,
    symbol: str,
    contract: str | None,
    source_timezone: str,
) -> pd.DataFrame:
    metadata = DatasetMetadata(
        source=source,
        symbol=symbol,
        contract=contract,
        source_timezone=source_timezone,
        filename=input_file.name,
    )
    dataframe = load_csv(input_file, metadata=metadata)
    print(f"Loaded {len(dataframe):,} raw bars.")
    return dataframe


def stage_validate(
    dataframe: pd.DataFrame,
    *,
    results_directory: Path,
    normalized_directory: Path,
    sessions_config: dict[str, Any] | None = None,
) -> tuple[pd.DataFrame, Any]:
    validation_directory = results_directory / "validation"
    report = validate_market_data(
        dataframe,
        tick_size=0.25,
        expected_interval_minutes=1,
        large_gap_points=100.0,
    )
    analysis_status = classify_analysis_status(
        report,
        allowed_warning_categories=allowed_warnings_from_validation_config(
            sessions_config
        ),
    )
    print_validation_report(report)
    print(f"Analysis status: {analysis_status.status.upper()}")
    for reason in analysis_status.reasons:
        print(f"  reason: {reason}")
    save_validation_report_json(report, validation_directory / "validation_report.json")
    save_coverage_reports(dataframe, validation_directory / "diagnostics")
    if not report.passed:
        raise PipelineError(
            "Data validation FAILED. The pipeline will not continue into strategy research."
        )
    normalized_directory.mkdir(parents=True, exist_ok=True)
    normalized_path = normalized_directory / "nq_1m_normalized.parquet"
    save_parquet(dataframe, normalized_path)
    print(f"Validated dataset saved to:\n{normalized_path}")
    return dataframe, report


def stage_resample(
    dataframe: pd.DataFrame,
    *,
    processed_directory: Path,
    as_of: Any | None = None,
) -> dict[str, Any]:
    output_directory = processed_directory / "timeframes"
    results = generate_standard_timeframes(dataframe)
    if as_of is not None:
        results = filter_resampled_results_as_of(results, as_of=as_of)
    for timeframe, result in results.items():
        validate_resampled_bars(result.dataframe)
        output_path = output_directory / f"nq_{timeframe}.parquet"
        save_resampled_parquet(result, str(output_path))
        print(
            f"{timeframe:>4}: {result.rows_out:,} bars "
            f"({result.incomplete_bars:,} incomplete)"
        )
    return results


def stage_bias(
    dataframe_1m: pd.DataFrame,
    *,
    resampled_results: dict[str, Any],
    strategy_config: dict[str, Any],
    processed_directory: Path,
) -> pd.DataFrame:
    enriched = enrich_htf_bias(
        dataframe_1m,
        resampled_results,
        strategy_config,
    )
    summary = bias_summary(enriched)
    save_bias_outputs(enriched, processed_directory / "bias")
    print(f"Bullish HTF bias bars: {summary.bullish:,}")
    print(f"Bearish HTF bias bars: {summary.bearish:,}")
    print(f"Neutral HTF bias bars: {summary.neutral:,}")
    print(f"HTF bias conflicts: {summary.conflicts:,}")
    print(f"Known HTF bias bars: {summary.known:,}")
    print(f"Unknown HTF bias bars: {summary.unknown:,}")
    return enriched


def stage_sessions(
    dataframe: pd.DataFrame,
    *,
    sessions_config: dict[str, Any],
    processed_directory: Path,
) -> pd.DataFrame:
    enriched, levels = enrich_with_sessions(dataframe, sessions_config, causal=True)
    save_session_outputs(enriched, levels, processed_directory / "sessions")
    print(f"Session enrichment complete: {len(levels):,} sessions.")
    return enriched


def stage_vwap(
    dataframe: pd.DataFrame,
    *,
    strategy_config: dict[str, Any],
    processed_directory: Path,
) -> pd.DataFrame:
    enriched = enrich_vwap(
        dataframe,
        strategy_config,
    )

    output_path = save_vwap_outputs(
        enriched,
        processed_directory / "vwap",
    )

    known = int(
        enriched["vwap"].notna().sum()
    )

    print(
        f"VWAP available: {known:,}/{len(enriched):,} bars"
    )
    print(
        f"VWAP output: {output_path}"
    )

    return enriched


def stage_volume(
    dataframe: pd.DataFrame,
    *,
    strategy_config: dict[str, Any],
    processed_directory: Path,
) -> pd.DataFrame:
    enriched = enrich_volume_features(dataframe, strategy_config)
    summary = volume_summary(enriched)
    save_volume_outputs(enriched, processed_directory / "volume")
    print(f"Rolling RVOL available: {summary.rolling_rvol_available:,}")
    print(f"Time-of-day RVOL available: {summary.tod_rvol_available:,}")
    print(
        f"Volume spikes: {summary.rolling_spikes:,} rolling / "
        f"{summary.tod_spikes:,} time-of-day"
    )
    return enriched


def stage_snr(
    dataframe_1m: pd.DataFrame,
    *,
    resampled_results: dict[str, Any],
    strategy_config: dict[str, Any],
    processed_directory: Path,
) -> pd.DataFrame:
    if "5m" not in resampled_results:
        raise PipelineError("5m resampled dataset is required for SNR.")
    if "15m" not in resampled_results:
        raise PipelineError("15m resampled dataset is required for SNR.")

    bars_5m = ensure_datetime_columns(resampled_results["5m"].dataframe)
    bars_15m = ensure_datetime_columns(resampled_results["15m"].dataframe)
    enriched = build_multitimeframe_snr(
        dataframe_1m,
        bars_5m,
        bars_15m,
        strategy_config,
    )
    save_snr_outputs(enriched, processed_directory / "snr")
    for timeframe in ["1m", "5m", "15m"]:
        summary = snr_summary(enriched, timeframe=timeframe)
        print(
            f"{timeframe}: median SNR={summary.median_snr}, "
            f"median efficiency={summary.median_efficiency}"
        )
    return enriched


def stage_swings(
    dataframe: pd.DataFrame,
    *,
    strategy_config: dict[str, Any],
    processed_directory: Path,
) -> pd.DataFrame:
    enriched = enrich_swings(dataframe, strategy_config)
    summary = swing_summary(enriched)
    save_swing_outputs(enriched, processed_directory / "swings")
    print(
        f"Internal swings: {summary.internal_swing_highs:,} highs / "
        f"{summary.internal_swing_lows:,} lows"
    )
    print(
        f"External swings: {summary.external_swing_highs:,} highs / "
        f"{summary.external_swing_lows:,} lows"
    )
    return enriched


def stage_liquidity(
    dataframe: pd.DataFrame,
    *,
    strategy_config: dict[str, Any],
    processed_directory: Path,
) -> pd.DataFrame:
    enriched = enrich_liquidity_features(dataframe, strategy_config)
    summary = liquidity_summary(enriched)
    save_liquidity_outputs(
        enriched,
        processed_directory / "liquidity",
        config=strategy_config,
    )
    print(f"Liquidity sweeps: {summary.sweep_events:,}")
    print(f"Buy-side: {summary.buy_side_sweeps:,}")
    print(f"Sell-side: {summary.sell_side_sweeps:,}")
    return enriched


def stage_fvg(
    dataframe: pd.DataFrame,
    *,
    strategy_config: dict[str, Any],
    processed_directory: Path,
) -> pd.DataFrame:
    enriched, lifecycle = enrich_fvg_features(dataframe, strategy_config)
    summary = fvg_summary(enriched)
    save_fvg_outputs(enriched, lifecycle, processed_directory / "fvg")
    print(f"Bullish FVGs: {summary.bullish_created:,}")
    print(f"Bearish FVGs: {summary.bearish_created:,}")
    print(
        f"Retest holds: {summary.bullish_retest_holds:,} bullish / "
        f"{summary.bearish_retest_holds:,} bearish"
    )
    return enriched


def stage_pd_arrays(
    dataframe: pd.DataFrame,
    *,
    strategy_config: dict[str, Any],
    processed_directory: Path,
) -> pd.DataFrame:
    enriched, lifecycle = enrich_pd_array_features(
        dataframe,
        strategy_config,
    )

    summary = pd_array_summary(
        enriched,
        lifecycle,
    )

    save_pd_array_outputs(
        enriched,
        lifecycle,
        processed_directory / "pd_arrays",
    )

    print(f"PD-array objects: {summary.objects:,}")
    print(
        f"Original FVG respect/disrespect: "
        f"{summary.original_respects:,} / "
        f"{summary.original_disrespects:,}"
    )
    print(
        f"IFVG respect/disrespect: "
        f"{summary.ifvg_respects:,} / "
        f"{summary.ifvg_disrespects:,}"
    )

    return enriched


def stage_structure(
    dataframe: pd.DataFrame,
    *,
    strategy_config: dict[str, Any],
    processed_directory: Path,
) -> pd.DataFrame:
    enriched = enrich_structure_features(dataframe, strategy_config)
    summary = structure_summary(enriched)
    save_structure_outputs(enriched, processed_directory / "structure")
    print(
        f"Displacement: {summary.bullish_displacement:,} bullish / "
        f"{summary.bearish_displacement:,} bearish"
    )
    print(f"MSS: {summary.bullish_mss:,} bullish / {summary.bearish_mss:,} bearish")
    print(f"BOS: {summary.bullish_bos:,} bullish / {summary.bearish_bos:,} bearish")
    return enriched


def stage_dealing_range(
    dataframe: pd.DataFrame,
    *,
    processed_directory: Path,
) -> pd.DataFrame:
    result = dataframe.copy()

    mapping = {
        "internal": (
            "active_internal_swing_high",
            "active_internal_swing_low",
        ),
        "external": (
            "active_external_swing_high",
            "active_external_swing_low",
        ),
    }

    for scope, (
        source_high,
        source_low,
    ) in mapping.items():
        target_high = (
            f"{scope}_structure_range_high"
        )
        target_low = (
            f"{scope}_structure_range_low"
        )

        if source_high not in result.columns:
            raise PipelineError(
                f"Dealing range requires {source_high}."
            )

        if source_low not in result.columns:
            raise PipelineError(
                f"Dealing range requires {source_low}."
            )

        if target_high not in result.columns:
            result[target_high] = result[
                source_high
            ]

        if target_low not in result.columns:
            result[target_low] = result[
                source_low
            ]

    enriched = enrich_dealing_ranges(
        result,
        scopes=(
            "internal",
            "external",
        ),
    )

    output_directory = (
        processed_directory
        / "dealing_range"
    )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_directory
        / "dealing_ranges.parquet"
    )

    enriched.to_parquet(
        output_path,
        index=False,
    )

    internal_known = int(
        enriched[
            "internal_dealing_valid"
        ].sum()
    )

    external_known = int(
        enriched[
            "external_dealing_valid"
        ].sum()
    )

    print(
        "Dealing ranges available: "
        f"{internal_known:,} internal / "
        f"{external_known:,} external"
    )

    return enriched


def stage_dol(
    dataframe: pd.DataFrame,
    *,
    strategy_config: dict[str, Any],
    processed_directory: Path,
) -> pd.DataFrame:
    enriched = enrich_draw_on_liquidity(dataframe, strategy_config)
    summary = dol_summary(enriched)
    save_dol_outputs(enriched, processed_directory / "dol")
    print(f"Bullish DOL bars: {summary.bullish:,}")
    print(f"Bearish DOL bars: {summary.bearish:,}")
    print(f"Neutral DOL bars: {summary.neutral:,}")
    print(f"Bullish DOL targets available: {summary.bullish_targets_available:,}")
    print(f"Bearish DOL targets available: {summary.bearish_targets_available:,}")
    return enriched


def stage_scoring(
    dataframe: pd.DataFrame,
    *,
    strategy_config: dict[str, Any],
    processed_directory: Path,
) -> pd.DataFrame:
    scored = enrich_scores(dataframe, strategy_config)
    scored = add_score_change_events(scored, strategy_config)
    summary = scoring_summary(scored)
    save_scoring_outputs(scored, processed_directory / "scoring")
    print(f"Long candidates: {summary.long_candidates:,}")
    print(f"Short candidates: {summary.short_candidates:,}")
    print(f"Max long score: {summary.max_long_score}")
    print(f"Max short score: {summary.max_short_score}")
    return scored


def stage_market_state(
    dataframe: pd.DataFrame,
    *,
    strategy_config: dict[str, Any],
    state_directory: Path,
    as_of: Any,
    symbol: str,
    contract: str | None,
    data_quality: dict[str, Any],
    source_snapshots: list[str],
) -> tuple[dict[str, Any], dict[str, str]]:
    state = build_market_state(
        dataframe,
        as_of=as_of,
        symbol=symbol,
        contract=contract,
        strategy_config=strategy_config,
        data_quality=data_quality,
        source_snapshots=source_snapshots,
    )
    paths = save_market_state_snapshot(state, state_directory)
    print(f"Market state: {state['status']['message']}")
    print(f"Market-state snapshot: {paths.snapshot}")
    return state, {
        "snapshot": str(paths.snapshot),
        "latest": str(paths.latest),
    }


def stage_trade_plan(
    market_state: dict[str, Any],
    *,
    strategy_config: dict[str, Any],
) -> dict[str, Any]:
    plan = build_trade_plan(market_state, strategy_config)
    print(f"Trade plan: {plan['decision']}")
    return plan


def stage_backtest(
    dataframe: pd.DataFrame,
    *,
    strategy_config: dict[str, Any],
    results_directory: Path,
) -> pd.DataFrame:
    trades = run_backtest(dataframe, strategy_config)
    output_directory = results_directory / "backtest"
    if trades.empty:
        output_directory.mkdir(parents=True, exist_ok=True)
        empty_path = output_directory / "trades.csv"
        trades.to_csv(empty_path, index=False)
        print("No trades generated.")
        return trades

    metrics = calculate_backtest_metrics(trades)
    save_backtest_outputs(trades, output_directory)
    print(f"Trades: {metrics.get('trades', 0):,}")
    print(f"Win rate: {metrics.get('win_rate')}")
    print(f"Expectancy points: {metrics.get('expectancy_points')}")
    print(f"Expectancy R: {metrics.get('expectancy_r')}")
    print(f"Profit factor: {metrics.get('profit_factor')}")
    return trades


def run_pipeline(
    *,
    input_file: Path,
    source: str,
    symbol: str,
    contract: str | None,
    source_timezone: str,
    sessions_config_path: Path,
    strategy_config_path: Path,
    stop_after: str | None = None,
    as_of: Any | None = None,
) -> dict[str, Any]:
    print_header("NQ HISTORICAL RESEARCH PIPELINE")
    print(f"Input:     {input_file}")
    print(f"Source:    {source}")
    print(f"Symbol:    {symbol}")
    print(f"Contract:  {contract}")
    print(f"Timezone:  {source_timezone}")
    as_of_utc = normalize_as_of(as_of) if as_of is not None else None
    print(f"As of:     {as_of_utc.isoformat() if as_of_utc is not None else 'FULL DATASET'}")

    sessions_config = load_sessions_config(sessions_config_path)
    strategy_config = load_yaml(strategy_config_path)
    processed_directory = DEFAULT_PROCESSED_DIRECTORY
    results_directory = DEFAULT_RESULTS_DIRECTORY
    normalized_directory = DEFAULT_NORMALIZED_DIRECTORY
    audit_file = results_directory / "pipeline" / "latest_run.json"

    run_metadata = create_run_metadata(
        input_file=input_file,
        source=source,
        symbol=symbol,
        contract=contract,
        source_timezone=source_timezone,
        sessions_config=sessions_config,
        strategy_config=strategy_config,
        as_of=as_of_utc,
    )
    save_run_metadata(run_metadata, audit_file)

    stage_number = 0
    total_stages = len(PIPELINE_STAGES)
    artifacts: dict[str, Any] = {}

    try:
        stage_number += 1
        print_stage(stage_number, total_stages, "Load raw LSE data")
        data = stage_load(
            input_file=input_file,
            source=source,
            symbol=symbol,
            contract=contract,
            source_timezone=source_timezone,
        )
        load_details = dataframe_health_summary(data)
        if as_of_utc is not None:
            clock_summary = summarize_as_of(data, as_of=as_of_utc)
            data = filter_as_of(data, as_of=as_of_utc)
            if data.empty:
                raise PipelineError(
                    f"No completed one-minute bars are available by as_of={as_of_utc.isoformat()}."
                )
            run_metadata["data_clock"] = {
                "as_of": as_of_utc.isoformat(),
                "rows_in": clock_summary.rows_in,
                "rows_visible": clock_summary.rows_visible,
                "rows_hidden": clock_summary.rows_hidden,
                "first_visible_timestamp": str(clock_summary.first_visible_timestamp),
                "last_visible_timestamp": str(clock_summary.last_visible_timestamp),
                "last_visible_available_at": str(clock_summary.last_visible_available_at),
            }
            load_details = dataframe_health_summary(data)
            load_details.update(
                {
                    "as_of": as_of_utc.isoformat(),
                    "rows_before_as_of": clock_summary.rows_in,
                    "rows_hidden_by_as_of": clock_summary.rows_hidden,
                }
            )
            print(
                f"As-of cutoff: {clock_summary.rows_visible:,}/{clock_summary.rows_in:,} "
                f"completed 1m bars visible; {clock_summary.rows_hidden:,} hidden."
            )
        record_stage(run_metadata, "load", status="passed", details=load_details)
        if stop_after == "load":
            save_run_metadata(run_metadata, audit_file)
            return {"data": data, "metadata": run_metadata}

        stage_number += 1
        print_stage(stage_number, total_stages, "Validate market data")
        data, validation_report = stage_validate(
            data,
            results_directory=results_directory,
            normalized_directory=normalized_directory,
            sessions_config=sessions_config,
        )
        validate_analysis_status = classify_analysis_status(
            validation_report,
            allowed_warning_categories=allowed_warnings_from_validation_config(
                sessions_config
            ),
        )
        session_coverage = None
        if sessions_config.get("sessions"):
            session_coverage = required_session_coverage(
                data,
                sessions_config,
                as_of=as_of_utc,
            )
            if session_coverage.missing:
                print(
                    "Required-session coverage missing: "
                    + ", ".join(session_coverage.missing)
                )
                not_due = sorted(
                    set(session_coverage.missing) - set(session_coverage.missing_due)
                )
                if not_due:
                    print(
                        "  (not yet due; window has not started: "
                        + ", ".join(not_due)
                        + ")"
                    )
            else:
                print("Required-session coverage: all required sessions present.")
            # Missing bars that a required session window should already have
            # produced are a hard validation failure: the morning engine's
            # finalized levels cannot be computed, so analysis must not run.
            # Windows that are not yet due stay distinguished and do not block.
            if session_coverage.missing_due:
                validate_analysis_status = AnalysisStatus(
                    STATUS_NO_ANALYSIS,
                    (
                        "required_session_coverage: missing due required "
                        f"session(s): {', '.join(session_coverage.missing_due)}"
                    ),
                )
        validate_stage_status = (
            "no_analysis"
            if validate_analysis_status.status == STATUS_NO_ANALYSIS
            else "passed"
        )
        record_stage(
            run_metadata,
            "validate",
            status=validate_stage_status,
            details={
                "report_passed": validation_report.passed,
                "rows": validation_report.rows,
                "analysis_status": validate_analysis_status.status,
                "analysis_status_reasons": list(
                    validate_analysis_status.reasons
                ),
                "session_coverage": (
                    session_coverage.to_dict() if session_coverage else None
                ),
            },
        )
        if validate_analysis_status.status == STATUS_NO_ANALYSIS:
            raise PipelineError(
                "Validation refused analysis (no_analysis): required-session "
                "coverage missing for: "
                + ", ".join(session_coverage.missing_due)
            )
        if stop_after == "validate":
            return {"data": data, "metadata": run_metadata}

        stage_number += 1
        print_stage(stage_number, total_stages, "Generate higher timeframes")
        resampled = stage_resample(
            data,
            processed_directory=processed_directory,
            as_of=as_of_utc,
        )
        record_stage(
            run_metadata,
            "resample",
            status="passed",
            details={
                timeframe: {
                    "rows": result.rows_out,
                    "incomplete": result.incomplete_bars,
                }
                for timeframe, result in resampled.items()
            },
        )
        if stop_after == "resample":
            return {"data": data, "resampled": resampled, "metadata": run_metadata}

        stage_number += 1
        print_stage(stage_number, total_stages, "Calculate higher-timeframe bias")
        data = stage_bias(
            data,
            resampled_results=resampled,
            strategy_config=strategy_config,
            processed_directory=processed_directory,
        )
        bias_stats = bias_summary(data)
        record_stage(
            run_metadata,
            "bias",
            status="passed",
            details={
                "rows": bias_stats.rows,
                "bullish": bias_stats.bullish,
                "bearish": bias_stats.bearish,
                "neutral": bias_stats.neutral,
                "conflicts": bias_stats.conflicts,
                "known": bias_stats.known,
                "unknown": bias_stats.unknown,
            },
        )
        if stop_after == "bias":
            save_run_metadata(run_metadata, audit_file)
            return {"data": data, "resampled": resampled, "metadata": run_metadata}

        stage_number += 1
        print_stage(stage_number, total_stages, "Calculate session levels")
        data = stage_sessions(
            data,
            sessions_config=sessions_config,
            processed_directory=processed_directory,
        )
        record_stage(run_metadata, "sessions", status="passed", details=dataframe_health_summary(data))
        if stop_after == "sessions":
            return {"data": data, "metadata": run_metadata}

        stage_number += 1
        print_stage(stage_number, total_stages, "Calculate production VWAP")
        data = stage_vwap(
            data,
            strategy_config=strategy_config,
            processed_directory=processed_directory,
        )
        record_stage(
            run_metadata,
            "vwap",
            status="passed",
        )
        if stop_after == "vwap":
            return {"data": data, "metadata": run_metadata}

        stage_number += 1
        print_stage(stage_number, total_stages, "Calculate volume and RVOL")
        data = stage_volume(
            data,
            strategy_config=strategy_config,
            processed_directory=processed_directory,
        )
        record_stage(run_metadata, "volume", status="passed")
        if stop_after == "volume":
            return {"data": data, "metadata": run_metadata}

        stage_number += 1
        print_stage(stage_number, total_stages, "Calculate multi-timeframe SNR")
        data = stage_snr(
            data,
            resampled_results=resampled,
            strategy_config=strategy_config,
            processed_directory=processed_directory,
        )
        record_stage(run_metadata, "snr", status="passed")
        if stop_after == "snr":
            return {"data": data, "metadata": run_metadata}

        stage_number += 1
        print_stage(stage_number, total_stages, "Detect confirmed swings")
        data = stage_swings(
            data,
            strategy_config=strategy_config,
            processed_directory=processed_directory,
        )
        record_stage(run_metadata, "swings", status="passed")
        if stop_after == "swings":
            return {"data": data, "metadata": run_metadata}

        stage_number += 1
        print_stage(stage_number, total_stages, "Detect liquidity events")
        data = stage_liquidity(
            data,
            strategy_config=strategy_config,
            processed_directory=processed_directory,
        )
        record_stage(run_metadata, "liquidity", status="passed")
        if stop_after == "liquidity":
            return {"data": data, "metadata": run_metadata}

        stage_number += 1
        print_stage(stage_number, total_stages, "Detect FVG lifecycle")
        data = stage_fvg(
            data,
            strategy_config=strategy_config,
            processed_directory=processed_directory,
        )
        record_stage(run_metadata, "fvg", status="passed")
        if stop_after == "fvg":
            return {"data": data, "metadata": run_metadata}

        stage_number += 1
        print_stage(stage_number, total_stages, "Build PD-array state")
        data = stage_pd_arrays(
            data,
            strategy_config=strategy_config,
            processed_directory=processed_directory,
        )
        record_stage(run_metadata, "pd_arrays", status="passed")
        if stop_after == "pd_arrays":
            return {"data": data, "metadata": run_metadata}

        stage_number += 1
        print_stage(stage_number, total_stages, "Detect displacement and structure shifts")
        data = stage_structure(
            data,
            strategy_config=strategy_config,
            processed_directory=processed_directory,
        )
        record_stage(run_metadata, "structure", status="passed")
        if stop_after == "structure":
            return {"data": data, "metadata": run_metadata}

        stage_number += 1
        print_stage(stage_number, total_stages, "Calculate structural dealing ranges")
        data = stage_dealing_range(
            data,
            processed_directory=processed_directory,
        )
        record_stage(
            run_metadata,
            "dealing_range",
            status="passed",
        )
        if stop_after == "dealing_range":
            return {"data": data, "metadata": run_metadata}

        stage_number += 1
        print_stage(stage_number, total_stages, "Calculate draw on liquidity")
        data = stage_dol(
            data,
            strategy_config=strategy_config,
            processed_directory=processed_directory,
        )
        dol_stats = dol_summary(data)
        record_stage(
            run_metadata,
            "dol",
            status="passed",
            details={
                "rows": dol_stats.rows,
                "bullish": dol_stats.bullish,
                "bearish": dol_stats.bearish,
                "neutral": dol_stats.neutral,
                "bullish_targets_available": dol_stats.bullish_targets_available,
                "bearish_targets_available": dol_stats.bearish_targets_available,
            },
        )
        if stop_after == "dol":
            save_run_metadata(run_metadata, audit_file)
            return {"data": data, "metadata": run_metadata}

        stage_number += 1
        print_stage(stage_number, total_stages, "Score long and short setups")
        data = stage_scoring(
            data,
            strategy_config=strategy_config,
            processed_directory=processed_directory,
        )
        record_stage(run_metadata, "scoring", status="passed")
        if stop_after == "scoring":
            return {"data": data, "metadata": run_metadata}

        stage_number += 1
        print_stage(stage_number, total_stages, "Build deterministic market state")
        state_as_of = as_of_utc
        if state_as_of is None:
            state_as_of = pd.Timestamp(visibility_times(data).iloc[-1])
        market_state, market_state_paths = stage_market_state(
            data,
            strategy_config=strategy_config,
            state_directory=DEFAULT_STATE_DIRECTORY,
            as_of=state_as_of,
            symbol=symbol,
            contract=contract,
            data_quality={
                "analysis_status": validate_analysis_status.status,
                "reasons": list(validate_analysis_status.reasons),
                "session_coverage": (
                    session_coverage.to_dict() if session_coverage else None
                ),
            },
            source_snapshots=[str(input_file)],
        )
        record_stage(
            run_metadata,
            "market_state",
            status=(
                "passed"
                if market_state["status"]["code"] in {"ready", "degraded"}
                else "no_analysis"
            ),
            details={
                "schema_version": market_state["schema_version"],
                "as_of": market_state["as_of"],
                "status": market_state["status"],
                "paths": market_state_paths,
            },
        )
        if stop_after == "market_state":
            save_run_metadata(run_metadata, audit_file)
            return {
                "data": data,
                "market_state": market_state,
                "metadata": run_metadata,
            }

        stage_number += 1
        print_stage(stage_number, total_stages, "Build deterministic trade plan")
        trade_plan = stage_trade_plan(
            market_state,
            strategy_config=strategy_config,
        )
        record_stage(
            run_metadata,
            "trade_plan",
            status=(
                "passed"
                if trade_plan["decision"] == "TRADE PLAN"
                else "no_trade"
            ),
            details={
                "schema_version": trade_plan["schema_version"],
                "as_of": trade_plan["as_of"],
                "decision": trade_plan["decision"],
                "preferred_direction": (
                    trade_plan["preferred"]["direction"]
                    if trade_plan["preferred"]
                    else None
                ),
                "alternate_direction": (
                    trade_plan["alternate"]["direction"]
                    if trade_plan["alternate"]
                    else None
                ),
                "rejections": trade_plan["rejections"],
            },
        )
        if stop_after == "trade_plan":
            save_run_metadata(run_metadata, audit_file)
            return {
                "data": data,
                "market_state": market_state,
                "trade_plan": trade_plan,
                "metadata": run_metadata,
            }

        stage_number += 1
        print_stage(stage_number, total_stages, "Run backtest")
        trades = stage_backtest(
            data,
            strategy_config=strategy_config,
            results_directory=results_directory,
        )
        record_stage(
            run_metadata,
            "backtest",
            status="passed",
            details={"trades": int(len(trades))},
        )

        run_metadata["status"] = "completed"
        run_metadata["run_completed_at"] = datetime.now().astimezone().isoformat()
        save_run_metadata(run_metadata, audit_file)

        print_header("PIPELINE COMPLETE")
        print(f"Final enriched bars: {len(data):,}")
        print(f"Trades generated: {len(trades):,}")
        print("\nResults directory:")
        print(results_directory)
        print("\nPipeline audit:")
        print(audit_file)

        artifacts["enriched_data"] = data
        artifacts["market_state"] = market_state
        artifacts["trade_plan"] = trade_plan
        artifacts["trades"] = trades
        artifacts["metadata"] = run_metadata
        return artifacts

    except Exception as exc:
        run_metadata["status"] = "failed"
        run_metadata["failed_stage"] = (
            PIPELINE_STAGES[max(0, stage_number - 1)] if stage_number > 0 else "startup"
        )
        run_metadata["error"] = str(exc)
        run_metadata["traceback"] = traceback.format_exc()
        run_metadata["run_completed_at"] = datetime.now().astimezone().isoformat()
        save_run_metadata(run_metadata, audit_file)

        print_header("PIPELINE FAILED")
        print(f"Stage: {run_metadata['failed_stage']}")
        print(f"Error: {exc}")
        print("\nFull failure details saved to:")
        print(audit_file)
        raise


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the NQ historical research and backtesting pipeline."
    )
    parser.add_argument("--input", required=True, help="Path to raw LSE 1-minute CSV.")
    parser.add_argument("--source", default="LSE", help="Market-data source label. Default: LSE")
    parser.add_argument("--symbol", default="NQ", help="Instrument symbol. Default: NQ")
    parser.add_argument(
        "--contract",
        default=None,
        help="Futures contract, e.g. NQU26. Optional while investigating LSE schema.",
    )
    parser.add_argument(
        "--timezone",
        default=None,
        help=(
            "Timezone of raw timestamps, e.g. UTC or America/New_York. "
            "Required if CSV timestamps are timezone-naive."
        ),
    )
    parser.add_argument(
        "--sessions-config",
        default=str(DEFAULT_SESSION_CONFIG),
        help="Path to sessions.yaml.",
    )
    parser.add_argument(
        "--strategy-config",
        default=str(DEFAULT_STRATEGY_CONFIG),
        help="Path to strategy.yaml.",
    )
    parser.add_argument(
        "--as-of",
        default=None,
        help=(
            "Optional timezone-aware replay cutoff. Example: "
            "2026-08-10T09:00:00-04:00. Only completed data available by this "
            "timestamp may influence the pipeline."
        ),
    )
    parser.add_argument(
        "--stop-after",
        choices=PIPELINE_STAGES,
        default=None,
        help="Stop pipeline after a specific stage. Useful while debugging.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    input_file = Path(args.input)
    if not input_file.is_absolute():
        input_file = PROJECT_ROOT / input_file
    if not input_file.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_file}")

    if args.timezone is None:
        print("\nERROR:")
        print("You must currently specify the source timezone.")
        print("\nExample:")
        print(
            "python run_pipeline.py "
            "--input data/raw/lse/nq_sample.csv "
            "--timezone UTC"
        )
        print(
            "\nDo not use UTC unless we have confirmed that "
            "LSE's timestamps are actually UTC."
        )
        sys.exit(1)

    run_pipeline(
        input_file=input_file,
        source=args.source,
        symbol=args.symbol,
        contract=args.contract,
        source_timezone=args.timezone,
        sessions_config_path=Path(args.sessions_config),
        strategy_config_path=Path(args.strategy_config),
        stop_after=args.stop_after,
        as_of=args.as_of,
    )


if __name__ == "__main__":
    main()
