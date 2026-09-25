#!/usr/bin/env python3
"""Isolated, read-only main-versus-candidate scorer parity and peak RSS test.

No full pipeline or ProjectX requests. Use --input to select an existing
feature artifact; --rows limits memory by reading an Arrow row batch only.
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
WORKER = r'''
import json
from pathlib import Path
import resource
import sys
from time import perf_counter

import pandas as pd
import pyarrow.parquet as pq
import yaml

project, data_path, config_path, model, rows, result_path = sys.argv[1:]
sys.path.insert(0, str(Path(project) / "src"))
from score_candidate_models import CANDIDATE_WEIGHTS
from scorer import enrich_scores

batch = next(pq.ParquetFile(data_path).iter_batches(batch_size=int(rows)))
features = batch.to_pandas()
features["timestamp"] = pd.to_datetime(features["timestamp"], utc=True, errors="coerce")
if features["timestamp"].isna().any():
    raise ValueError("Invalid input timestamps")
config = yaml.safe_load(Path(config_path).read_text())
config["scoring"]["positive_weights"] = {
    key: float(value) for key, value in CANDIDATE_WEIGHTS[model].items()
}
start = perf_counter()
scored = enrich_scores(features, config)
seconds = perf_counter() - start
columns = sorted([
    col for col in scored.columns
    if col.startswith(("long_", "short_")) or col in (
        "score_edge", "score_edge_abs", "preferred_score_direction", "candidate_any",
    )
])
scored[columns].to_pickle(result_path)
print(json.dumps({
    "seconds": round(seconds, 3),
    "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
    "bars": len(scored),
    "columns": len(columns),
}), flush=True)
'''


def run(project: Path, input_file: Path, config: Path, model: str, rows: int, output: Path):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project / "src") + os.pathsep + str(project)
    run = subprocess.run(
        [
            sys.executable, "-u", "-c", WORKER, str(project), str(input_file),
            str(config), model, str(rows), str(output),
        ],
        cwd=project, env=env, text=True, capture_output=True,
    )
    if run.returncode != 0:
        raise RuntimeError(
            f"Scoring worker failed in {project} (exit {run.returncode}):\n"
            + run.stderr[-3500:] + "\n" + run.stdout[-1000:]
        )
    return json.loads(run.stdout.splitlines()[-1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production-root", type=Path, default=Path("/docker/trade-alerts"))
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--model", choices=[
        "baseline", "candidate_conservative", "candidate_evidence_tilt",
        "candidate_redundancy_reduced",
    ], default="candidate_conservative")
    parser.add_argument("--rows", type=int, default=5000)
    args = parser.parse_args()
    if args.rows < 1:
        parser.error("--rows must be positive")
    production = args.production_root.resolve()
    if production == ROOT.resolve():
        parser.error("Use isolated perf/scoring-streaming-memory worktree")
    cfg = args.config or production / "config/strategy.yaml"
    if not args.input.is_file() or not cfg.is_file():
        parser.error("Existing input and config required; no data will be rebuilt")
    with tempfile.TemporaryDirectory(prefix="score-streaming-parity-") as tmp:
        directory = Path(tmp)
        print("Running original scoring on an existing input batch...", flush=True)
        old = run(production, args.input, cfg, args.model, args.rows, directory / "old.pkl")
        print(f"Original: {old}", flush=True)
        print("Running streaming scoring on the identical input batch...", flush=True)
        new = run(ROOT, args.input, cfg, args.model, args.rows, directory / "new.pkl")
        print(f"Streaming: {new}", flush=True)
        pd.testing.assert_frame_equal(
            pd.read_pickle(directory / "old.pkl"),
            pd.read_pickle(directory / "new.pkl"),
            check_exact=True, check_dtype=True, check_like=False,
        )
        print("EXACT STREAMING SCORING PARITY PASSED", flush=True)
        print("Compare peak RSS values above; neither is an estimate of full-year peak RAM.", flush=True)


if __name__ == "__main__":
    main()
