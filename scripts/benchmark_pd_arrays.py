#!/usr/bin/env python3
"""Read-only baseline-versus-optimized PD-array parity/performance benchmark.

Run from an isolated perf/pd-array-lifecycle worktree, *not* production.
Reads existing FVG artifacts; never rebuilds a historical pipeline.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import sys
from time import perf_counter

import pandas as pd
import yaml

BRANCH_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCTION_ROOT = Path("/docker/trade-alerts")


def load_pd_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load PD-array module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production-root", type=Path, default=DEFAULT_PRODUCTION_ROOT)
    parser.add_argument("--input", type=Path, default=None)
    args = parser.parse_args()
    if BRANCH_ROOT.resolve() == args.production_root.resolve():
        parser.error("Benchmark must run from an isolated worktree")
    path = args.input or (args.production_root / "data/processed/fvg/nq_1m_fvg.parquet")
    if not path.is_file():
        parser.error(f"Existing FVG artifact not found (do not rebuild): {path}")
    original_path = args.production_root / "src/pd_arrays.py"
    optimized_path = BRANCH_ROOT / "src/pd_arrays.py"
    if not original_path.exists() or not optimized_path.exists():
        parser.error("Cannot find both PD-array versions")
    config_file = args.production_root / "config/strategy.yaml"
    config = yaml.safe_load(config_file.read_text())
    original = load_pd_module("pd_arrays_original_benchmark", original_path)
    candidate = load_pd_module("pd_arrays_candidate_benchmark", optimized_path)
    data = pd.read_parquet(path)
    print(f"Existing input: {path}\nRows: {len(data):,}", flush=True)

    start = perf_counter()
    original_features, original_lifecycle = original.enrich_pd_array_features(data.copy(), config)
    before = perf_counter() - start
    print(f"Original full PD-array stage: {before:.2f}s", flush=True)

    start = perf_counter()
    candidate_features, candidate_lifecycle = candidate.enrich_pd_array_features(data.copy(), config)
    after = perf_counter() - start
    print(f"Optimized full PD-array stage: {after:.2f}s", flush=True)

    pd.testing.assert_frame_equal(
        original_lifecycle, candidate_lifecycle,
        check_exact=True, check_dtype=True,
    )
    pd.testing.assert_frame_equal(
        original_features, candidate_features,
        check_exact=True, check_dtype=True,
    )
    print("EXACT FULL PD-ARRAY PARITY: PASSED", flush=True)
    print(f"Speedup: {before / after:.2f}x", flush=True)
    print("REAL-DATA PD-ARRAY BENCHMARK COMPLETE", flush=True)


if __name__ == "__main__":
    main()
