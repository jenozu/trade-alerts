#!/usr/bin/env python3
"""Compare original-main and optimized scoring across the same existing 1m data.

Run from isolated scoring worktree; no market-data requests, trading activity,
or production state changes. Exits nonzero on any score/feature mismatch.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = Path("/docker/trade-alerts")

WORKER = r'''
import json
import sys
import time
from pathlib import Path
import pandas as pd
import yaml

project, data_path, config_path, out_path = map(Path, sys.argv[1:])
sys.path.insert(0, str(project / "src"))
from scorer import enrich_scores
data = pd.read_parquet(data_path)
config = yaml.safe_load(config_path.read_text())
started = time.perf_counter()
scored = enrich_scores(data, config)
duration = time.perf_counter() - started
columns = sorted(
    col for col in scored.columns
    if col.startswith(("long_", "short_", "score_"))
    or col in ("preferred_score_direction", "candidate_any")
)
scored[columns].to_parquet(out_path, index=False)
print(json.dumps({"seconds": duration, "rows": len(scored), "columns": columns}))
'''


def execute(project: Path, data: Path, cfg: Path, output: Path) -> dict:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(project / "src") + os.pathsep + str(project)
    completed = subprocess.run(
        [sys.executable, "-c", WORKER, str(project), str(data), str(cfg), str(output)],
        cwd=project,
        env=environment,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout.strip().splitlines()[-1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production-root", type=Path, default=PRODUCTION)
    parser.add_argument("--input", type=Path)
    arguments = parser.parse_args()
    production = arguments.production_root.resolve()
    if production == ROOT.resolve():
        parser.error("Run from isolated scoring worktree, not production main")
    path = arguments.input or production / "data/processed/pd_arrays/nq_1m_pd_arrays.parquet"
    if not path.is_file():
        parser.error(f"Existing input missing; refusing pipeline rerun: {path}")
    cfg = production / "config/strategy.yaml"
    if not cfg.is_file():
        parser.error(f"Strategy configuration unavailable: {cfg}")
    with tempfile.TemporaryDirectory(prefix="scoring-confluence-parity-") as work:
        work = Path(work)
        print(f"Input: {path}", flush=True)
        print("Running original scoring...", flush=True)
        old = execute(production, path, cfg, work / "original.parquet")
        print(f"Original: {old['seconds']:.2f}s", flush=True)
        print("Running shared-confluence scoring...", flush=True)
        new = execute(ROOT, path, cfg, work / "optimized.parquet")
        print(f"Optimized: {new['seconds']:.2f}s", flush=True)
        original = pd.read_parquet(work / "original.parquet")
        optimized = pd.read_parquet(work / "optimized.parquet")
        pd.testing.assert_frame_equal(
            original, optimized, check_dtype=True, check_exact=True,
        )
        print(f"EXACT SCORING PARITY: PASSED ({len(original):,} bars; {len(original.columns)} scoring columns)")
        print(f"Speedup: {old['seconds'] / new['seconds']:.2f}x")
        print("SCORING REAL-DATA BENCHMARK COMPLETE")


if __name__ == "__main__":
    main()
