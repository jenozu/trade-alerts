from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


class FeatureCacheError(RuntimeError):
    """Raised when a feature cache is missing, stale, or incompatible."""


@dataclass(frozen=True)
class FeatureCacheValidation:
    cache_directory: Path
    metadata_path: Path
    scored_path: Path
    pre_scoring_path: Path | None
    rows: int
    valid: bool
    reasons: tuple[str, ...]


def sha256_file(path: str | Path) -> str:
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_cache_metadata(cache_directory: str | Path) -> dict[str, Any]:
    cache_directory = Path(cache_directory)
    metadata_path = cache_directory / "cache_metadata.json"
    if not metadata_path.exists():
        raise FeatureCacheError(f"Cache metadata not found: {metadata_path}")
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FeatureCacheError(f"Invalid cache metadata JSON: {metadata_path}") from exc
    if not isinstance(payload, dict):
        raise FeatureCacheError(f"Invalid cache metadata object: {metadata_path}")
    return payload


def _resolve_artifact_path(cache_directory: Path, declared: str | None, fallback: str) -> Path:
    if declared:
        candidate = Path(declared)
        if candidate.is_absolute():
            return candidate
        # Historical metadata may store a repository-relative path such as
        # data/cache/<name>/features_scored.parquet. Prefer that path if it
        # exists; otherwise fall back to the cache directory itself.
        if candidate.exists():
            return candidate
        return cache_directory / candidate.name
    return cache_directory / fallback


def validate_feature_cache(
    cache_directory: str | Path,
    *,
    input_file: str | Path | None = None,
    strategy_config: str | Path | None = None,
    sessions_config: str | Path | None = None,
    verify_feature_code: bool = True,
) -> FeatureCacheValidation:
    cache_directory = Path(cache_directory)
    metadata_path = cache_directory / "cache_metadata.json"
    metadata = load_cache_metadata(cache_directory)
    reasons: list[str] = []

    scored_meta = metadata.get("scored_cache") or {}
    pre_meta = metadata.get("pre_scoring_cache") or {}

    scored_path = _resolve_artifact_path(
        cache_directory,
        scored_meta.get("path"),
        "features_scored.parquet",
    )
    pre_scoring_path = _resolve_artifact_path(
        cache_directory,
        pre_meta.get("path"),
        "features_pre_scoring.parquet",
    )
    if not pre_scoring_path.exists():
        pre_scoring_path = None

    if not scored_path.exists():
        reasons.append(f"missing scored cache: {scored_path}")
    else:
        expected_sha = scored_meta.get("sha256")
        if expected_sha and sha256_file(scored_path) != expected_sha:
            reasons.append("scored cache SHA-256 mismatch")

    checks = (
        (input_file, metadata.get("input", {}), "input dataset"),
        (strategy_config, metadata.get("strategy_config", {}), "strategy config"),
        (sessions_config, metadata.get("sessions_config", {}), "sessions config"),
    )
    for current_path, recorded, label in checks:
        if current_path is None:
            continue
        current_path = Path(current_path)
        if not current_path.exists():
            reasons.append(f"missing {label}: {current_path}")
            continue
        expected_sha = recorded.get("sha256")
        if expected_sha and sha256_file(current_path) != expected_sha:
            reasons.append(f"{label} SHA-256 mismatch")

    if verify_feature_code:
        manifest = metadata.get("feature_code_manifest", {}).get("files", {})
        if not manifest:
            reasons.append("feature code manifest missing")
        else:
            for filename, expected_sha in sorted(manifest.items()):
                path = Path(filename)
                if not path.exists():
                    reasons.append(f"feature code file missing: {filename}")
                    continue
                if sha256_file(path) != expected_sha:
                    reasons.append(f"feature code changed: {filename}")

    rows = int(scored_meta.get("rows") or 0)
    return FeatureCacheValidation(
        cache_directory=cache_directory,
        metadata_path=metadata_path,
        scored_path=scored_path,
        pre_scoring_path=pre_scoring_path,
        rows=rows,
        valid=not reasons,
        reasons=tuple(reasons),
    )


def load_scored_cache(validation: FeatureCacheValidation) -> pd.DataFrame:
    if not validation.valid:
        raise FeatureCacheError(
            "Feature cache is not valid: " + "; ".join(validation.reasons)
        )
    dataframe = pd.read_parquet(validation.scored_path)
    if "timestamp" not in dataframe.columns:
        raise FeatureCacheError("Scored cache is missing timestamp column")
    dataframe["timestamp"] = pd.to_datetime(dataframe["timestamp"], utc=True)
    if validation.rows and len(dataframe) != validation.rows:
        raise FeatureCacheError(
            f"Scored cache row mismatch: {len(dataframe)} != {validation.rows}"
        )
    if dataframe["timestamp"].duplicated().any():
        raise FeatureCacheError("Scored cache contains duplicate timestamps")
    return dataframe
