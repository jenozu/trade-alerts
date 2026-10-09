"""Diagnostic execution replay of frozen producer features; never recertify them."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pandas as pd
import pyarrow.parquet as pq
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from backtest import MARKET_EXECUTION_MODEL, run_backtest, calculate_backtest_metrics, save_backtest_outputs
from experiment_identity import build_input_lock, verify_input_lock, write_input_lock
from feature_cache import sha256_file

MODES = ("score_signal_v1", "market_after_retest_confirmation_v1")
VALID_MODES = (*MODES, MARKET_EXECUTION_MODEL)


def checked_path(source_root, item):
    path = (source_root / item["path"]).resolve()
    if not path.is_relative_to(source_root):
        raise ValueError("Input path escapes source root")
    if not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", "")):
        raise ValueError("Missing/invalid recorded SHA-256")
    if sha256_file(path) != item["sha256"]:
        raise ValueError(f"Input SHA-256 mismatch: {path}")
    return path


def verify_producer(metadata, repository):
    commit = metadata.get("git_sha", "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Missing/invalid producer commit")
    manifest = metadata.get("feature_code_manifest", {}).get("files", {})
    if not manifest:
        raise ValueError("Missing producer feature manifest")
    differences = []
    for name, expected in sorted(manifest.items()):
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Producer manifest paths must be repository-relative")
        content = subprocess.check_output(
            ["git", "show", f"{commit}:{name}"], cwd=repository,
        )
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError(f"Recorded producer blob mismatch: {name}")
        current = repository / name
        if not current.is_file() or sha256_file(current) != expected:
            differences.append(name)
    return differences


def historical_timing(frame, completed_through):
    cutoff = pd.Timestamp(completed_through)
    if cutoff.tzinfo is None:
        raise ValueError("completed-through must be timezone-aware")
    cutoff = cutoff.tz_convert("UTC")
    result = frame.copy()
    timestamps = pd.to_datetime(result["timestamp"])
    if timestamps.dt.tz is None or timestamps.isna().any():
        raise ValueError("Historical timestamps must be non-null and timezone-aware")
    timestamps = timestamps.dt.tz_convert("UTC")
    if timestamps.duplicated().any() or not timestamps.is_monotonic_increasing:
        raise ValueError("Historical timestamps must be unique and ordered")
    if (timestamps != timestamps.dt.floor("min")).any():
        raise ValueError("Historical timestamps must label exact one-minute opens")
    close_time = timestamps + pd.Timedelta(minutes=1)
    available = close_time.copy()
    if "available_at" in result:
        previous = pd.to_datetime(result["available_at"])
        if previous.dt.tz is None or previous.isna().any():
            raise ValueError("Existing availability must be non-null and timezone-aware")
        previous = previous.dt.tz_convert("UTC")
        available = previous.where(previous > close_time, close_time)
    complete = available <= cutoff
    for name in ("bar_complete", "is_complete"):
        if name in result:
            if not pd.api.types.is_bool_dtype(result[name]):
                raise ValueError("Existing completion flags must have boolean dtype")
            complete &= result[name].fillna(False)
    result["timestamp"] = timestamps
    result["available_at"] = available
    result["bar_complete"] = complete.astype(bool)
    return result


def replay(*, source_root, cache_dir, output_dir, completed_through, year,
           evaluation_start=None, evaluation_end=None, repository=ROOT, execution_models=None):
    modes = tuple(execution_models) if execution_models is not None else MODES
    if not modes or len(set(modes)) != len(modes) or any(mode not in VALID_MODES for mode in modes):
        raise ValueError("Select distinct supported execution models")
    source_root = Path(source_root).resolve()
    repository = Path(repository).resolve()
    cache_dir = Path(cache_dir).resolve()
    output_dir = Path(output_dir).resolve()
    if not cache_dir.is_relative_to(source_root):
        raise ValueError("Cache must be under source root")
    if output_dir.is_relative_to(source_root) or source_root.is_relative_to(output_dir):
        raise ValueError("Output and source directories must be separate")
    if output_dir.exists():
        raise FileExistsError("Use a fresh output directory for each replay")
    metadata_path = cache_dir / "cache_metadata.json"
    metadata = json.loads(metadata_path.read_text())
    differences = verify_producer(metadata, repository)
    paths = {key: checked_path(source_root, metadata[key]) for key in
             ("input", "scored_cache", "strategy_config", "sessions_config")}
    metadata_sha = sha256_file(metadata_path)
    source_rows = pq.ParquetFile(paths["scored_cache"]).metadata.num_rows
    if source_rows != metadata["scored_cache"]["rows"]:
        raise ValueError("Scored cache row count mismatch")
    year_start = pd.Timestamp(f"{year}-01-01T00:00:00Z")
    year_end = pd.Timestamp(f"{year + 1}-01-01T00:00:00Z")
    start = pd.Timestamp(evaluation_start) if evaluation_start else year_start
    end = pd.Timestamp(evaluation_end) if evaluation_end else year_end
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("Evaluation bounds must be timezone-aware")
    start, end = start.tz_convert("UTC"), end.tz_convert("UTC")
    if not year_start <= start < end <= year_end:
        raise ValueError("Evaluation bounds must lie within the declared year")
    frame = pd.read_parquet(paths["scored_cache"], filters=[
        ("timestamp", ">=", start.to_pydatetime()), ("timestamp", "<", end.to_pydatetime())])
    derived = historical_timing(frame, completed_through)
    evaluated = derived.loc[derived.timestamp.dt.year == year].copy()
    if evaluated.empty or not evaluated.bar_complete.all():
        raise ValueError("Evaluation year must contain only completed historical bars")
    config = yaml.safe_load(paths["strategy_config"].read_text())
    output_dir.mkdir(parents=True, exist_ok=False)
    derived_path = output_dir / "derived_scored.parquet"
    derived.to_parquet(derived_path, index=False)
    provenance = {
        "status": "DIAGNOSTIC_ONLY", "producer_commit": metadata["git_sha"],
        "current_feature_files_differing_from_producer": differences,
        "feature_policy": "Reuse frozen producer outputs; current feature generation is not executed",
        "timing_policy": "historical_bar_open_plus_one_minute_v1",
        "completed_through": pd.Timestamp(completed_through).isoformat(),
        "timing_evidence": "Approved AS_OF_CONTRACT plus explicit historical-export assumption; CSV vendor semantics not independently certified",
        "evaluation_year": year, "evaluation_start": start.isoformat(),
        "evaluation_end_exclusive": end.isoformat(), "source_cache_rows": source_rows,
        "bars_derived": len(derived), "bars_evaluated": len(evaluated),
        "limitations": ["No real-feed availability/correction history", "Producer manifest may omit dependencies",
                        "Frozen feature rollover isolation not certified", "No live/planner execution parity certification",
                        "Backtest closes at selected sample boundaries; features retain producer warmup"],
    }
    provenance_path = output_dir / "REPLAY_PROVENANCE.json"
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n")
    settings = {"execution": {"models": list(modes), "producer_strategy": config,
                              "timing": provenance},
                "cost": config.get("backtest", {}).get("commission", {}),
                "slippage": config.get("backtest", {}).get("slippage", {})}
    files = {"source_data": paths["input"], "scored_cache_original": paths["scored_cache"],
             "scored_cache_derived": derived_path, "cache_metadata": metadata_path,
             "strategy": paths["strategy_config"], "sessions": paths["sessions_config"],
             "research_policy": repository / "config/research_policy.yaml",
             "dependencies": repository / "requirements.txt", "replay_provenance": provenance_path}
    lock = build_input_lock(experiment_id="DIAGNOSTIC-FROZEN-CACHE-REPLAY", root=repository,
        files=files, years=sorted(set(derived.timestamp.dt.year)),
        contracts=derived.contract.dropna().astype(str).unique().tolist() if "contract" in derived else [],
        counts={"bars": len(derived), "candidates": int(sum(evaluated[c].fillna(False).astype(bool).sum()
               for c in ("long_candidate", "short_candidate") if c in evaluated)), "trades": None},
        settings=settings, unavailable={"live_data_parity": "Diagnostic replay only"})
    write_input_lock(output_dir / "EXPERIMENT_INPUT_LOCK.json", lock)
    summaries = {}
    for mode in modes:
        effective = copy.deepcopy(config)
        effective.setdefault("backtest", {})["execution_model"] = mode
        trades = run_backtest(evaluated.copy(), effective)
        destination = output_dir / mode
        destination.mkdir()
        if mode == MARKET_EXECUTION_MODEL:
            (destination / "execution_decisions.json").write_text(
                json.dumps(trades.attrs["execution_decisions"], indent=2, allow_nan=False) + "\n")
        if trades.empty:
            trades.to_csv(destination / "trades.csv", index=False)
        else:
            save_backtest_outputs(trades, destination)
        summaries[mode] = {"trades": len(trades), "metrics": calculate_backtest_metrics(trades) if not trades.empty else {"trades": 0}}
        print(f"{mode}: {len(trades)} trades", flush=True)
    verify_input_lock(lock, root=repository)
    if sha256_file(metadata_path) != metadata_sha:
        raise ValueError("Cache metadata changed during preparation")
    summary = {"status": "DIAGNOSTIC_ONLY", "input_identity_sha256": lock["input_identity_sha256"],
               "inputs_unchanged": True, "results": summaries}
    (output_dir / "REPLAY_SUMMARY.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    print(f"Inputs unchanged. Outputs: {output_dir}", flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-root", "cache-dir", "output-dir", "completed-through"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--evaluation-start")
    parser.add_argument("--evaluation-end")
    parser.add_argument("--execution-model", action="append", choices=VALID_MODES,
                        help="Repeat to compare specific versions; default preserves legacy and confirmed v1")
    parser.add_argument("--acknowledge-historical-export-assumption", action="store_true", required=True)
    args = parser.parse_args()
    replay(source_root=args.source_root, cache_dir=args.cache_dir, output_dir=args.output_dir,
           completed_through=args.completed_through, year=args.year,
           evaluation_start=args.evaluation_start, evaluation_end=args.evaluation_end,
           execution_models=args.execution_model)


if __name__ == "__main__":
    main()
