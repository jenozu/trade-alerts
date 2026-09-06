from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS = PROJECT_ROOT / "data" / "results" / "backtest"
DEFAULT_ARCHIVES = PROJECT_ROOT / "data" / "results" / "research_runs"
DEFAULT_PIPELINE_AUDIT = PROJECT_ROOT / "data" / "results" / "pipeline" / "latest_run.json"
DEFAULT_STRATEGY = PROJECT_ROOT / "config" / "strategy.yaml"
DEFAULT_SESSIONS = PROJECT_ROOT / "config" / "sessions.yaml"


class ArchiveError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        text=True,
    ).strip()


def git_status() -> str:
    return subprocess.check_output(
        ["git", "status", "--short"],
        cwd=PROJECT_ROOT,
        text=True,
    )


def safe_label(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    value = re.sub(r"-+", "-", value).strip("-")
    if not value:
        raise ArchiveError("Archive label is empty after sanitization")
    return value


def copy_if_exists(source: Path | None, destination: Path) -> Path | None:
    if source is None or not source.exists():
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preserve a deterministic research/backtest run in an immutable archive directory."
    )
    parser.add_argument("--label", required=True, help="Human-readable run label, e.g. 2025_baseline")
    parser.add_argument("--input", required=True, type=Path, help="Exact market-data input used")
    parser.add_argument("--result-dir", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--archive-root", type=Path, default=DEFAULT_ARCHIVES)
    parser.add_argument("--pipeline-audit", type=Path, default=DEFAULT_PIPELINE_AUDIT)
    parser.add_argument("--input-audit", type=Path, default=None)
    parser.add_argument("--strategy-config", type=Path, default=DEFAULT_STRATEGY)
    parser.add_argument("--sessions-config", type=Path, default=DEFAULT_SESSIONS)
    parser.add_argument("--notes", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_file = args.input.resolve()
    result_dir = args.result_dir.resolve()

    if not input_file.exists():
        raise ArchiveError(f"Input file not found: {input_file}")
    if not result_dir.exists():
        raise ArchiveError(f"Result directory not found: {result_dir}")

    trades = result_dir / "trades.csv"
    metrics = result_dir / "backtest_metrics.json"
    if not trades.exists():
        raise ArchiveError(f"Required trade ledger not found: {trades}")
    if not metrics.exists():
        raise ArchiveError(f"Required metrics file not found: {metrics}")

    now = datetime.now(timezone.utc)
    input_sha = sha256_file(input_file)
    current_git_sha = git_sha()
    run_id = f"{now.strftime('%Y%m%dT%H%M%SZ')}_{safe_label(args.label)}_{input_sha[:8]}"
    archive_dir = args.archive_root.resolve() / run_id
    if archive_dir.exists():
        raise ArchiveError(f"Archive already exists: {archive_dir}")
    archive_dir.mkdir(parents=True)

    copied: dict[str, str] = {}

    def preserve(name: str, source: Path | None) -> None:
        if source is None or not source.exists():
            return
        target = archive_dir / name
        copy_if_exists(source, target)
        copied[name] = sha256_file(target)

    preserve("trades.csv", trades)
    preserve("backtest_metrics.json", metrics)
    preserve("cached_backtest_summary.json", result_dir / "cached_backtest_summary.json")
    preserve("pipeline_audit.json", args.pipeline_audit.resolve() if args.pipeline_audit else None)
    preserve("input_audit.json", args.input_audit.resolve() if args.input_audit else None)
    preserve("strategy.yaml", args.strategy_config.resolve())
    preserve("sessions.yaml", args.sessions_config.resolve())

    status_text = git_status()
    (archive_dir / "git_status.txt").write_text(status_text, encoding="utf-8")
    copied["git_status.txt"] = sha256_file(archive_dir / "git_status.txt")

    manifest: dict[str, Any] = {
        "archive_schema_version": 1,
        "run_id": run_id,
        "label": args.label,
        "archived_at_utc": now.isoformat(),
        "input": {
            "path": str(input_file),
            "sha256": input_sha,
            "size_bytes": input_file.stat().st_size,
        },
        "result_directory": str(result_dir),
        "git_sha": current_git_sha,
        "git_worktree_clean": not bool(status_text.strip()),
        "strategy_config_sha256": sha256_file(args.strategy_config.resolve()),
        "sessions_config_sha256": sha256_file(args.sessions_config.resolve()),
        "notes": args.notes,
        "files": copied,
    }
    (archive_dir / "archive_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str),
        encoding="utf-8",
    )

    print("=== RESEARCH RUN ARCHIVED ===")
    print(f"run_id: {run_id}")
    print(f"archive: {archive_dir}")
    print(f"input_sha256: {input_sha}")
    print(f"git_sha: {current_git_sha}")
    print(f"worktree_clean: {manifest['git_worktree_clean']}")
    print("files:")
    for name in sorted(copied):
        print(f"  - {name}")


if __name__ == "__main__":
    main()
