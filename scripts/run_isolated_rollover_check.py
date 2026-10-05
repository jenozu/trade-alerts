"""Bounded cold-start feature diagnostic; preserve frozen source/cache controls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
import run_pipeline as pipeline
from experiment_identity import build_input_lock, verify_input_lock, write_input_lock
from rollover import prepare_contract_frame
from scripts.run_isolated_cache_replay import checked_path, historical_timing, verify_producer

RAW_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume", "contract",
               "rollover_segment", "rollover_boundary", "rollover_from_contract",
               "rollover_to_contract", "available_at", "bar_complete", "is_complete"]
RESET_LEVELS = ["active_internal_swing_high", "active_internal_swing_low",
                "nearest_active_bullish_fvg_lower", "nearest_active_bearish_fvg_lower",
                "pdh", "pdl"]
RESET_FLAGS = [f"{direction}_{name}" for direction in ("bullish", "bearish")
               for name in ("core_sequence", "reversal_sequence", "continuation_sequence")]


def select_window(frame, boundary, days_before=3, days_after=3):
    if not all(isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= 7
               for n in (days_before, days_after)):
        raise ValueError("Diagnostic bounds must be 1 to 7 days on each side")
    boundary = pd.Timestamp(boundary)
    if boundary.tzinfo is None:
        raise ValueError("Boundary must be timezone-aware")
    boundary = boundary.tz_convert("UTC")
    if "contract" not in frame or frame.contract.isna().any():
        raise ValueError("Known contract labels are required")
    if "rollover_segment" not in frame or frame.rollover_segment.isna().any():
        raise ValueError("Known rollover segments are required")
    ts = pd.to_datetime(frame.timestamp)
    if ts.dt.tz is None or ts.isna().any() or ts.duplicated().any() or not ts.is_monotonic_increasing:
        raise ValueError("Source timestamps must be aware, unique and ordered")
    changed = frame.contract.ne(frame.contract.shift())
    changed.iloc[0] = False
    if not ((ts == boundary) & changed).any():
        raise ValueError("Boundary must identify an actual contract transition")
    selected = frame.loc[(ts >= boundary - pd.Timedelta(days=days_before))
                         & (ts < boundary + pd.Timedelta(days=days_after))].copy()
    segments = [part.reset_index(drop=True) for _, part in
                selected.groupby("rollover_segment", sort=False)]
    if len(segments) != 2 or selected.contract.nunique() != 2:
        raise ValueError("Bounded check must contain exactly the adjacent two contract segments")
    for part in segments:
        pipeline.require_single_contract_input(part)
    if segments[0].timestamp.max() >= boundary or segments[1].timestamp.min() != boundary:
        raise ValueError("Segment metadata does not align with the selected transition")
    return segments


def generate_features(raw, strategy, sessions, destination):
    """Real feature stages only; no backtest, alert, state or cache certification."""
    pipeline.require_single_contract_input(raw)
    resampled = pipeline.stage_resample(raw, processed_directory=destination)
    frame = pipeline.stage_bias(raw, resampled_results=resampled,
        strategy_config=strategy, processed_directory=destination)
    frame = pipeline.stage_sessions(frame, sessions_config=sessions, processed_directory=destination)
    for stage in (pipeline.stage_vwap, pipeline.stage_volume):
        frame = stage(frame, strategy_config=strategy, processed_directory=destination)
    frame = pipeline.stage_snr(frame, resampled_results=resampled,
        strategy_config=strategy, processed_directory=destination)
    for stage in (pipeline.stage_swings, pipeline.stage_liquidity, pipeline.stage_fvg,
                  pipeline.stage_pd_arrays, pipeline.stage_structure):
        frame = stage(frame, strategy_config=strategy, processed_directory=destination)
    frame = pipeline.stage_dealing_range(frame, processed_directory=destination)
    frame = pipeline.stage_dol(frame, strategy_config=strategy, processed_directory=destination)
    return pipeline.stage_scoring(frame, strategy_config=strategy, processed_directory=destination)


def verify_features(raw, features, period):
    if len(raw) != len(features):
        raise ValueError("Feature row count changed")
    if not (pd.to_datetime(raw.timestamp).reset_index(drop=True).eq(
            pd.to_datetime(features.timestamp).reset_index(drop=True)).all()
            and raw.contract.astype(str).tolist() == features.contract.astype(str).tolist()):
        raise ValueError("Feature timestamp/contract identity changed")
    for name in ("open", "high", "low", "close", "volume"):
        if not np.array_equal(raw[name].to_numpy(), features[name].to_numpy()):
            raise ValueError(f"Raw {name} changed")
    previous = raw.close.shift()
    tr = pd.concat([raw.high - raw.low, (raw.high - previous).abs(),
                    (raw.low - previous).abs()], axis=1).max(axis=1)
    expected = tr.rolling(period, min_periods=period).mean()
    if "atr_1m" not in features or not np.allclose(
            features.atr_1m, expected, rtol=1e-10, atol=1e-10, equal_nan=True):
        raise ValueError("ATR does not match isolated same-contract rolling calculation")
    missing = set(RESET_LEVELS + RESET_FLAGS) - set(features.columns)
    if missing:
        raise ValueError(f"Missing reset evidence columns: {sorted(missing)}")
    first = features.iloc[0]
    if any(pd.notna(first[name]) for name in RESET_LEVELS):
        raise ValueError("Cold-start levels were populated before same-contract history")
    if any(pd.isna(first[name]) or bool(first[name]) for name in RESET_FLAGS):
        raise ValueError("Cold-start sequence state did not reset")
    return {"raw_identity_preserved": True, "same_contract_atr_matches": True,
            "cold_start_levels_reset": True, "cold_start_sequences_reset": True,
            "atr_warmup_bars": period - 1}


def run_check(*, source_root, cache_dir, output_dir, boundary, completed_through,
              days_before=3, days_after=3, repository=ROOT):
    source_root, cache_dir, output_dir, repository = (
        Path(p).resolve() for p in (source_root, cache_dir, output_dir, repository))
    if not cache_dir.is_relative_to(source_root):
        raise ValueError("Cache must be under the source root")
    if output_dir.is_relative_to(source_root) or source_root.is_relative_to(output_dir):
        raise ValueError("Output must be separate from the preserved source root")
    if output_dir.exists():
        raise FileExistsError("Use a fresh output directory")
    meta_path = cache_dir / "cache_metadata.json"
    metadata = json.loads(meta_path.read_text())
    differences = verify_producer(metadata, repository)
    paths = {role: checked_path(source_root, metadata[role]) for role in
             ("input", "scored_cache", "strategy_config", "sessions_config")}
    import pyarrow.parquet as pq
    schema = pq.ParquetFile(paths["input"]).schema_arrow.names
    raw = pd.read_parquet(paths["input"], columns=[c for c in RAW_COLUMNS if c in schema])
    raw = historical_timing(raw, completed_through)
    segments = select_window(raw, boundary, days_before, days_after)
    if not all(part.bar_complete.all() for part in segments):
        raise ValueError("Selected diagnostic bars must all be completed")
    # Validate actual OHLCV and reject duplicates; never adjust the raw prices.
    for part in segments:
        if part[["open", "high", "low", "close", "volume"]].isna().any().any():
            raise ValueError("Selected raw OHLCV contains missing values")
        prepare_contract_frame(part)
    strategy = yaml.safe_load(paths["strategy_config"].read_text())
    sessions = pipeline.load_sessions_config(paths["sessions_config"])
    period = int(strategy.get("displacement", {}).get("atr_period", 14))
    if any(len(part) <= period for part in segments):
        raise ValueError("Each segment needs more than one ATR period of bars")
    files = {"source_data": paths["input"], "scored_cache_control": paths["scored_cache"],
             "cache_metadata": meta_path, "strategy": paths["strategy_config"],
             "sessions": paths["sessions_config"], "research_policy": repository / "config/research_policy.yaml",
             "dependencies": repository / "requirements.txt"}
    # Include orchestration and transitive feature dependencies, not only the old
    # producer's incomplete feature manifest. Full tracked tree is commit-locked.
    for path in sorted((repository / "src").glob("*.py")):
        files[f"code:{path.relative_to(repository)}"] = path
    for path in (repository / "run_pipeline.py", repository / "scripts/run_isolated_rollover_check.py",
                 repository / "scripts/run_isolated_cache_replay.py"):
        files[f"code:{path.relative_to(repository)}"] = path
    lock = build_input_lock(experiment_id="DIAGNOSTIC-ISOLATED-ROLLOVER", root=repository,
        files=files, years=sorted({int(t.year) for part in segments for t in part.timestamp}),
        contracts=[str(part.contract.iloc[0]) for part in segments],
        counts={"bars": sum(len(p) for p in segments), "candidates": None, "trades": None},
        settings={"execution": {"mode": "feature_only", "boundary": pd.Timestamp(boundary).isoformat(),
                  "days_before": days_before, "days_after": days_after,
                  "timing": "historical_bar_open_plus_one_minute_v1",
                  "completed_through": pd.Timestamp(completed_through).isoformat(),
                  "warmup": "cold_start_each_selected_segment"}, "cost": {}, "slippage": {}},
        unavailable={"research_readiness": "Bounded cold-start diagnostic, not a research cache"})
    output_dir.mkdir(parents=True, exist_ok=False)
    write_input_lock(output_dir / "EXPERIMENT_INPUT_LOCK.json", lock)
    results = []
    for number, part in enumerate(segments):
        destination = output_dir / f"segment_{number}"
        destination.mkdir()
        part.to_parquet(destination / "raw_segment.parquet", index=False)
        features = generate_features(part.copy(), strategy, sessions, destination / "processed")
        checks = verify_features(part, features, period)
        feature_path = destination / "features_scored.parquet"
        features.to_parquet(feature_path, index=False)
        from feature_cache import sha256_file
        results.append({"contract": str(part.contract.iloc[0]), "rows": len(part),
                        "original_segment": str(part.rollover_segment.iloc[0]),
                        "first_timestamp": part.timestamp.iloc[0].isoformat(),
                        "last_timestamp": part.timestamp.iloc[-1].isoformat(),
                        "feature_sha256": sha256_file(feature_path), "checks": checks})
    verify_input_lock(lock, root=repository)
    summary = {"status": "DIAGNOSTIC_ONLY", "inputs_unchanged": True, "segments": results,
               "producer_commit": metadata["git_sha"], "feature_files_differing_from_producer": differences,
               "limitations": ["Cold-start window is not a full-year research warmup",
                   "Original cache is a preserved contaminated control",
                   "No source vendor/correction-history certification",
                   "No backtest, performance claim or sequence-object fidelity certification"]}
    (output_dir / "ROLLOVER_CHECK_SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("ROLLOVER CHECK: diagnostic checks passed; inputs unchanged", flush=True)
    for item in results:
        print(item["contract"], item["rows"], "bars:", item["checks"], flush=True)
    print("Outputs:", output_dir, flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source-root", "cache-dir", "output-dir", "boundary", "completed-through"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--days-before", type=int, default=3)
    parser.add_argument("--days-after", type=int, default=3)
    parser.add_argument("--acknowledge-historical-export-assumption", action="store_true", required=True)
    args = vars(parser.parse_args())
    args.pop("acknowledge_historical_export_assumption")
    run_check(**args)


if __name__ == "__main__":
    main()
