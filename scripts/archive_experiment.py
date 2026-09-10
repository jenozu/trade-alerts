#!/usr/bin/env python3
"""Archive durable experiment evidence into a Git-tracked research directory.

Working experiment outputs normally live under gitignored ``data/reports`` paths.
This helper copies only approved, reasonably sized text/research artifacts into
``research-archive/EXP-XXX`` and records a SHA-256 manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ALLOWED_SUFFIXES = {
    ".md",
    ".json",
    ".csv",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".txt",
}

DENY_NAME_FRAGMENTS = {
    "secret",
    "credential",
    "password",
    "passwd",
    "token",
    "private_key",
    "api_key",
}

DEFAULT_MAX_BYTES = 10 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def looks_sensitive(path: Path) -> bool:
    name = path.name.lower()
    return any(fragment in name for fragment in DENY_NAME_FRAGMENTS)


def collect_files(source: Path, max_bytes: int) -> tuple[list[Path], list[dict[str, object]]]:
    accepted: list[Path] = []
    skipped: list[dict[str, object]] = []

    for path in sorted(p for p in source.rglob("*") if p.is_file()):
        rel = path.relative_to(source)
        reason: str | None = None

        if path.suffix.lower() not in ALLOWED_SUFFIXES:
            reason = "unsupported_suffix"
        elif looks_sensitive(path):
            reason = "sensitive_filename"
        elif path.stat().st_size > max_bytes:
            reason = "over_size_limit"

        if reason:
            skipped.append(
                {
                    "path": rel.as_posix(),
                    "reason": reason,
                    "bytes": path.stat().st_size,
                }
            )
        else:
            accepted.append(path)

    return accepted, skipped


def archive_experiment(
    experiment: str,
    source: Path,
    destination_root: Path,
    max_bytes: int = DEFAULT_MAX_BYTES,
    dry_run: bool = False,
) -> dict[str, object]:
    experiment = experiment.strip().upper()
    if not experiment.startswith("EXP-"):
        raise ValueError("experiment must look like EXP-003")
    if not source.is_dir():
        raise FileNotFoundError(f"source directory does not exist: {source}")

    destination = destination_root / experiment
    accepted, skipped = collect_files(source, max_bytes)

    manifest_files: list[dict[str, object]] = []
    for src in accepted:
        rel = src.relative_to(source)
        dest = destination / rel
        entry = {
            "path": rel.as_posix(),
            "bytes": src.stat().st_size,
            "sha256": sha256_file(src),
        }
        manifest_files.append(entry)

        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    manifest: dict[str, object] = {
        "experiment": experiment,
        "source": str(source),
        "destination": str(destination),
        "max_file_bytes": max_bytes,
        "archived_file_count": len(manifest_files),
        "files": manifest_files,
        "skipped": skipped,
    }

    if not dry_run:
        destination.mkdir(parents=True, exist_ok=True)
        manifest_path = destination / "ARCHIVE_MANIFEST.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, help="Experiment ID, e.g. EXP-003")
    parser.add_argument("--source", required=True, type=Path, help="Working report directory")
    parser.add_argument(
        "--destination-root",
        type=Path,
        default=Path("research-archive"),
        help="Git-tracked archive root (default: research-archive)",
    )
    parser.add_argument(
        "--max-file-mb",
        type=float,
        default=10.0,
        help="Maximum individual artifact size to archive (default: 10 MB)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without copying files")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    max_bytes = int(args.max_file_mb * 1024 * 1024)
    manifest = archive_experiment(
        experiment=args.experiment,
        source=args.source,
        destination_root=args.destination_root,
        max_bytes=max_bytes,
        dry_run=args.dry_run,
    )

    print(json.dumps(manifest, indent=2, sort_keys=True))
    if manifest["archived_file_count"] == 0:
        print("WARNING: no eligible artifacts were archived")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
