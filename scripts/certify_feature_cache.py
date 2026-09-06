from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import pandas as pd


FEATURE_FILES = [
    "src/resample.py",
    "src/bias.py",
    "src/sessions.py",
    "src/vwap.py",
    "src/volume.py",
    "src/snr.py",
    "src/swings.py",
    "src/liquidity.py",
    "src/fvg.py",
    "src/pd_arrays.py",
    "src/structure.py",
    "src/dealing_range.py",
    "src/dol.py",
    "src/scorer.py",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect(path: Path) -> dict:
    df = pd.read_parquet(path)
    if "timestamp" not in df.columns:
        raise SystemExit(f"Missing timestamp column: {path}")
    ts = pd.to_datetime(df["timestamp"], utc=True)
    return {
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "first_timestamp": str(ts.min()),
        "last_timestamp": str(ts.max()),
        "duplicate_timestamps": int(ts.duplicated().sum()),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Certify a preserved feature cache.")
    p.add_argument("--cache-dir", required=True, type=Path)
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--label", required=True)
    p.add_argument("--strategy", type=Path, default=Path("config/strategy.yaml"))
    p.add_argument("--sessions", type=Path, default=Path("config/sessions.yaml"))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cache_dir = args.cache_dir
    pre = cache_dir / "features_pre_scoring.parquet"
    scored = cache_dir / "features_scored.parquet"

    required = [args.input, args.strategy, args.sessions, pre, scored]
    for path in required:
        if not path.exists():
            raise SystemExit(f"MISSING: {path}")

    pre_info = inspect(pre)
    scored_info = inspect(scored)
    if pre_info["rows"] != scored_info["rows"]:
        raise SystemExit(
            f"Row mismatch: pre={pre_info['rows']} scored={scored_info['rows']}"
        )
    if pre_info["duplicate_timestamps"] or scored_info["duplicate_timestamps"]:
        raise SystemExit("Duplicate timestamps detected in cache")

    manifest = {}
    for filename in FEATURE_FILES:
        path = Path(filename)
        if not path.exists():
            raise SystemExit(f"MISSING FEATURE FILE: {filename}")
        manifest[filename] = sha256(path)

    manifest_path = cache_dir / "feature_code_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    git_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()

    metadata = {
        "cache_schema_version": 1,
        "dataset": args.label,
        "git_sha": git_sha,
        "input": {"path": str(args.input), "sha256": sha256(args.input)},
        "strategy_config": {
            "path": str(args.strategy),
            "sha256": sha256(args.strategy),
        },
        "sessions_config": {
            "path": str(args.sessions),
            "sha256": sha256(args.sessions),
        },
        "feature_code_manifest": {
            "path": str(manifest_path),
            "files": manifest,
        },
        "pre_scoring_cache": {
            "path": str(pre),
            "sha256": sha256(pre),
            **pre_info,
        },
        "scored_cache": {
            "path": str(scored),
            "sha256": sha256(scored),
            **scored_info,
        },
    }

    meta_path = cache_dir / "cache_metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print("=== FEATURE CACHE CERTIFIED ===")
    print("label:", args.label)
    print("git_sha:", git_sha)
    print("input_sha256:", metadata["input"]["sha256"])
    print("rows:", scored_info["rows"])
    print("pre_scoring_sha256:", metadata["pre_scoring_cache"]["sha256"])
    print("scored_sha256:", metadata["scored_cache"]["sha256"])
    print("metadata:", meta_path)


if __name__ == "__main__":
    main()
