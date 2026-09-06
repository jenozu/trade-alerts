from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from feature_cache import load_scored_cache, validate_feature_cache


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _write_cache(tmp_path: Path):
    cache = tmp_path / "cache"
    cache.mkdir()

    input_file = tmp_path / "input.parquet"
    strategy = tmp_path / "strategy.yaml"
    sessions = tmp_path / "sessions.yaml"
    feature_code = tmp_path / "feature.py"
    scored = cache / "features_scored.parquet"

    pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2026-01-01", periods=2, freq="1min", tz="UTC"
            ),
            "close": [100.0, 101.0],
        }
    ).to_parquet(input_file, index=False)

    strategy.write_text("scoring:\n  enabled: true\n", encoding="utf-8")
    sessions.write_text("sessions: {}\n", encoding="utf-8")
    feature_code.write_text("VALUE = 1\n", encoding="utf-8")

    pd.DataFrame(
        {
            "timestamp": pd.date_range(
                "2026-01-01", periods=2, freq="1min", tz="UTC"
            ),
            "close": [100.0, 101.0],
            "long_candidate": [False, True],
        }
    ).to_parquet(scored, index=False)

    metadata = {
        "input": {"path": str(input_file), "sha256": _sha(input_file)},
        "strategy_config": {"path": str(strategy), "sha256": _sha(strategy)},
        "sessions_config": {"path": str(sessions), "sha256": _sha(sessions)},
        "scored_cache": {
            "path": str(scored),
            "sha256": _sha(scored),
            "rows": 2,
        },
        "feature_code_manifest": {
            "files": {str(feature_code): _sha(feature_code)}
        },
    }
    (cache / "cache_metadata.json").write_text(
        json.dumps(metadata), encoding="utf-8"
    )
    return cache, input_file, strategy, sessions, feature_code


def test_valid_feature_cache_loads_scored_dataframe(tmp_path):
    cache, input_file, strategy, sessions, _ = _write_cache(tmp_path)

    validation = validate_feature_cache(
        cache,
        input_file=input_file,
        strategy_config=strategy,
        sessions_config=sessions,
    )

    assert validation.valid is True
    assert validation.reasons == ()
    loaded = load_scored_cache(validation)
    assert len(loaded) == 2
    assert str(loaded["timestamp"].dtype) == "datetime64[ns, UTC]"


def test_feature_cache_rejects_changed_input(tmp_path):
    cache, input_file, strategy, sessions, _ = _write_cache(tmp_path)
    input_file.write_bytes(input_file.read_bytes() + b"changed")

    validation = validate_feature_cache(
        cache,
        input_file=input_file,
        strategy_config=strategy,
        sessions_config=sessions,
    )

    assert validation.valid is False
    assert "input dataset SHA-256 mismatch" in validation.reasons


def test_feature_cache_rejects_changed_feature_code(tmp_path):
    cache, input_file, strategy, sessions, feature_code = _write_cache(tmp_path)
    feature_code.write_text("VALUE = 2\n", encoding="utf-8")

    validation = validate_feature_cache(
        cache,
        input_file=input_file,
        strategy_config=strategy,
        sessions_config=sessions,
    )

    assert validation.valid is False
    assert any(reason.startswith("feature code changed:") for reason in validation.reasons)
