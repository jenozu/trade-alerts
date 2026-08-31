from __future__ import annotations

import argparse
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIRECTORY = PROJECT_ROOT / "src"
if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))

import run_pipeline as pipeline  # noqa: E402
from backtest import calculate_backtest_metrics, save_backtest_outputs  # noqa: E402
from rollover import RolloverError, prepare_contract_frame, split_rollover_segments  # noqa: E402

DEFAULT_SESSION_CONFIG = PROJECT_ROOT / "config" / "sessions.yaml"
DEFAULT_STRATEGY_CONFIG = PROJECT_ROOT / "config" / "strategy.yaml"
DEFAULT_ROLLOVER_PROCESSED = PROJECT_ROOT / "data" / "processed" / "rollover"
DEFAULT_ROLLOVER_RESULTS = PROJECT_ROOT / "data" / "results" / "rollover"
DEFAULT_COMBINED_BACKTEST = PROJECT_ROOT / "data" / "results" / "backtest"


class RolloverPipelineError(RuntimeError):
    """Raised when a stitched rollover research run cannot be completed safely."""


def load_stitched_csv(filepath: str | Path) -> pd.DataFrame:
    """Load and validate a stitched, non-adjusted contract series."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise RolloverPipelineError(f"Not a file: {path}")

    try:
        raw = pd.read_csv(path)
    except Exception as exc:
        raise RolloverPipelineError(f"Could not read stitched rollover CSV: {path}") from exc

    prepared = prepare_contract_frame(raw)
    validate_stitched_frame(prepared)
    return prepared


def validate_stitched_frame(df: pd.DataFrame) -> None:
    required = {"contract", "rollover_segment", "rollover_boundary"}
    missing = required - set(df.columns)
    if missing:
        raise RolloverPipelineError(
            f"Stitched rollover data is missing columns: {sorted(missing)}"
        )

    if df.empty:
        raise RolloverPipelineError("Stitched rollover data is empty.")

    ordered = df.sort_values("timestamp", kind="stable").reset_index(drop=True)
    if ordered["timestamp"].duplicated().any():
        raise RolloverPipelineError("Duplicate timestamps exist in stitched rollover data.")

    segment_ids = ordered["rollover_segment"].dropna().astype(int).unique().tolist()
    if segment_ids != list(range(len(segment_ids))):
        raise RolloverPipelineError(
            f"Rollover segments must be contiguous starting at zero; found {segment_ids}."
        )

    contract_change = ordered["contract"].astype(str).ne(
        ordered["contract"].astype(str).shift(1)
    )
    expected_boundary = contract_change & ordered.index.to_series().ne(0)
    actual_boundary = ordered["rollover_boundary"].fillna(False).astype(bool)
    if not expected_boundary.equals(actual_boundary):
        raise RolloverPipelineError(
            "Contract changes do not match rollover_boundary markers."
        )

    segment_change = ordered["rollover_segment"].ne(ordered["rollover_segment"].shift(1))
    expected_segment_boundary = segment_change & ordered.index.to_series().ne(0)
    if not expected_segment_boundary.equals(actual_boundary):
        raise RolloverPipelineError(
            "Rollover segment changes do not match rollover_boundary markers."
        )

    try:
        split_rollover_segments(ordered)
    except RolloverError as exc:
        raise RolloverPipelineError(str(exc)) from exc


def write_segment_input(segment: pd.DataFrame, filepath: str | Path) -> Path:
    """Write one isolated contract segment for the existing single-contract pipeline."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    result = segment.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True).dt.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    # The normal loader regenerates timestamp_et from timestamp.
    if "timestamp_et" in result.columns:
        result = result.drop(columns=["timestamp_et"])
    result.to_csv(path, index=False)
    return path


@contextmanager
def isolated_pipeline_directories(
    *,
    processed_directory: Path,
    results_directory: Path,
    normalized_directory: Path,
) -> Iterator[None]:
    """Temporarily redirect run_pipeline outputs for one contract segment."""
    old_processed = pipeline.DEFAULT_PROCESSED_DIRECTORY
    old_results = pipeline.DEFAULT_RESULTS_DIRECTORY
    old_normalized = pipeline.DEFAULT_NORMALIZED_DIRECTORY

    pipeline.DEFAULT_PROCESSED_DIRECTORY = processed_directory
    pipeline.DEFAULT_RESULTS_DIRECTORY = results_directory
    pipeline.DEFAULT_NORMALIZED_DIRECTORY = normalized_directory
    try:
        yield
    finally:
        pipeline.DEFAULT_PROCESSED_DIRECTORY = old_processed
        pipeline.DEFAULT_RESULTS_DIRECTORY = old_results
        pipeline.DEFAULT_NORMALIZED_DIRECTORY = old_normalized


def run_single_contract_segment(
    segment: pd.DataFrame,
    *,
    segment_id: int,
    contract: str,
    source: str,
    symbol: str,
    source_timezone: str,
    sessions_config_path: Path,
    strategy_config_path: Path,
    rollover_processed_root: Path,
    rollover_results_root: Path,
) -> dict[str, Any]:
    safe_contract = contract.replace("/", "_").replace(" ", "_")
    segment_name = f"{segment_id:02d}_{safe_contract}"

    segment_input = rollover_processed_root / "segment_inputs" / f"{segment_name}.csv"
    write_segment_input(segment, segment_input)

    processed_directory = rollover_processed_root / "segments" / segment_name
    results_directory = rollover_results_root / "segments" / segment_name
    normalized_directory = rollover_processed_root / "normalized" / segment_name

    print("\n" + "#" * 60)
    print(f"ROLLOVER SEGMENT {segment_id}: {contract}")
    print(f"Rows: {len(segment):,}")
    print("#" * 60)

    with isolated_pipeline_directories(
        processed_directory=processed_directory,
        results_directory=results_directory,
        normalized_directory=normalized_directory,
    ):
        artifacts = pipeline.run_pipeline(
            input_file=segment_input,
            source=source,
            symbol=symbol,
            contract=contract,
            source_timezone=source_timezone,
            sessions_config_path=sessions_config_path,
            strategy_config_path=strategy_config_path,
        )

    return artifacts


def combine_enriched_segments(segments: list[pd.DataFrame]) -> pd.DataFrame:
    if not segments:
        return pd.DataFrame()
    combined = pd.concat(segments, ignore_index=True, sort=False)
    combined = combined.sort_values("timestamp", kind="stable").reset_index(drop=True)
    validate_stitched_frame(combined)
    return combined


def combine_segment_trades(
    trade_frames: list[pd.DataFrame],
    *,
    segment_lengths: list[int],
    contracts: list[str],
) -> pd.DataFrame:
    """Combine isolated trade logs while translating indexes to stitched-row indexes."""
    if not (len(trade_frames) == len(segment_lengths) == len(contracts)):
        raise RolloverPipelineError("Trade frames, segment lengths, and contracts must align.")

    pieces: list[pd.DataFrame] = []
    row_offset = 0

    for segment_id, (trades, segment_length, contract) in enumerate(
        zip(trade_frames, segment_lengths, contracts)
    ):
        if segment_length <= 0:
            raise RolloverPipelineError("Segment lengths must be positive.")

        if trades is not None and not trades.empty:
            piece = trades.copy()
            piece["contract"] = contract
            piece["rollover_segment"] = segment_id
            piece["segment_trade_id"] = piece.get("trade_id")

            for column in ["signal_index", "entry_index", "exit_index"]:
                if column in piece.columns:
                    numeric = pd.to_numeric(piece[column], errors="coerce")
                    piece[column] = numeric.where(numeric.isna(), numeric + row_offset)

            pieces.append(piece)

        row_offset += segment_length

    if not pieces:
        return pd.DataFrame()

    combined = pd.concat(pieces, ignore_index=True, sort=False)
    if "entry_time" in combined.columns:
        combined = combined.sort_values("entry_time", kind="stable").reset_index(drop=True)
    else:
        combined = combined.reset_index(drop=True)
    combined["trade_id"] = range(1, len(combined) + 1)
    return combined


def run_rollover_research(
    stitched: pd.DataFrame,
    *,
    source: str,
    symbol: str,
    source_timezone: str,
    sessions_config_path: Path = DEFAULT_SESSION_CONFIG,
    strategy_config_path: Path = DEFAULT_STRATEGY_CONFIG,
    rollover_processed_root: Path = DEFAULT_ROLLOVER_PROCESSED,
    rollover_results_root: Path = DEFAULT_ROLLOVER_RESULTS,
    combined_backtest_directory: Path = DEFAULT_COMBINED_BACKTEST,
) -> dict[str, Any]:
    validate_stitched_frame(stitched)
    segments = split_rollover_segments(stitched)

    enriched_segments: list[pd.DataFrame] = []
    trade_frames: list[pd.DataFrame] = []
    segment_lengths: list[int] = []
    contracts: list[str] = []
    metadata: list[dict[str, Any]] = []

    for segment_id, segment in enumerate(segments):
        contract = str(segment["contract"].iloc[0])
        artifacts = run_single_contract_segment(
            segment,
            segment_id=segment_id,
            contract=contract,
            source=source,
            symbol=symbol,
            source_timezone=source_timezone,
            sessions_config_path=sessions_config_path,
            strategy_config_path=strategy_config_path,
            rollover_processed_root=rollover_processed_root,
            rollover_results_root=rollover_results_root,
        )

        enriched = artifacts.get("enriched_data")
        trades = artifacts.get("trades")
        if not isinstance(enriched, pd.DataFrame):
            raise RolloverPipelineError(
                f"Pipeline segment {contract} did not return enriched_data."
            )
        if not isinstance(trades, pd.DataFrame):
            raise RolloverPipelineError(
                f"Pipeline segment {contract} did not return trades."
            )

        # Restore authoritative rollover metadata from the isolated input rows.
        rollover_columns = [
            "rollover_segment",
            "rollover_boundary",
            "rollover_from_contract",
            "rollover_to_contract",
        ]
        for column in rollover_columns:
            if column in segment.columns:
                enriched[column] = segment[column].reset_index(drop=True)
        enriched["contract"] = contract

        enriched_segments.append(enriched)
        trade_frames.append(trades)
        segment_lengths.append(len(segment))
        contracts.append(contract)
        metadata.append(artifacts.get("metadata", {}))

    combined_enriched = combine_enriched_segments(enriched_segments)
    combined_trades = combine_segment_trades(
        trade_frames,
        segment_lengths=segment_lengths,
        contracts=contracts,
    )

    rollover_processed_root.mkdir(parents=True, exist_ok=True)
    combined_enriched_path = rollover_processed_root / "combined_enriched.parquet"
    combined_enriched.to_parquet(combined_enriched_path, index=False)

    combined_backtest_directory.mkdir(parents=True, exist_ok=True)
    if combined_trades.empty:
        combined_trades.to_csv(combined_backtest_directory / "trades.csv", index=False)
        metrics = {"trades": 0}
    else:
        save_backtest_outputs(combined_trades, combined_backtest_directory)
        metrics = calculate_backtest_metrics(combined_trades)

    segment_summary = pd.DataFrame(
        {
            "rollover_segment": range(len(segments)),
            "contract": contracts,
            "bars": segment_lengths,
            "trades": [len(frame) for frame in trade_frames],
        }
    )
    rollover_results_root.mkdir(parents=True, exist_ok=True)
    segment_summary.to_csv(rollover_results_root / "segment_summary.csv", index=False)

    print("\n" + "=" * 60)
    print("ROLLOVER PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Contracts: {', '.join(contracts)}")
    print(f"Combined enriched bars: {len(combined_enriched):,}")
    print(f"Combined trades: {len(combined_trades):,}")
    if combined_trades.empty:
        print("No combined trades generated.")
    else:
        print(f"Win rate: {metrics.get('win_rate')}")
        print(f"Expectancy points: {metrics.get('expectancy_points')}")
        print(f"Expectancy R: {metrics.get('expectancy_r')}")
        print(f"Profit factor: {metrics.get('profit_factor')}")
    print(f"Combined enriched data: {combined_enriched_path}")
    print(f"Combined backtest results: {combined_backtest_directory}")

    return {
        "enriched_data": combined_enriched,
        "trades": combined_trades,
        "metrics": metrics,
        "segment_summary": segment_summary,
        "segment_metadata": metadata,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the existing causal research pipeline independently for every "
            "contract segment in a stitched rollover CSV, then combine results."
        )
    )
    parser.add_argument("--input", required=True, help="Stitched rollover CSV.")
    parser.add_argument("--source", default="PROJECTX", help="Source label. Default: PROJECTX")
    parser.add_argument("--symbol", default="MNQ", help="Instrument symbol. Default: MNQ")
    parser.add_argument("--timezone", default="UTC", help="Source timezone. Default: UTC")
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
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path

    stitched = load_stitched_csv(input_path)
    run_rollover_research(
        stitched,
        source=args.source,
        symbol=args.symbol,
        source_timezone=args.timezone,
        sessions_config_path=Path(args.sessions_config),
        strategy_config_path=Path(args.strategy_config),
    )


if __name__ == "__main__":
    main()
