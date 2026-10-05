from __future__ import annotations

import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd
import pytest

import experiment_identity
from feature_cache import sha256_file
from scripts.run_isolated_rollover_check import (
    ROOT, generate_features, run_check, select_window, verify_features,
)
from scripts.run_isolated_cache_replay import historical_timing
import run_pipeline as pipeline

BOUNDARY = "2025-03-17T22:00:00Z"


def raw_bars():
    n = 180
    ts = pd.date_range(pd.Timestamp(BOUNDARY) - pd.Timedelta(minutes=90), periods=n, freq="min")
    price = 100 + np.sin(np.arange(n) / 3) * 2
    price[90:] += 200
    return pd.DataFrame({"timestamp": ts, "open": price, "high": price + 1,
        "low": price - 1, "close": price + .25, "volume": np.full(n, 10),
        "contract": ["NMH25"] * 90 + ["NMM25"] * 90,
        "rollover_segment": [12] * 90 + [13] * 90,
        "rollover_boundary": [False] * 90 + [True] + [False] * 89})


def test_window_preserves_offset_segment_ids_and_raw_prices():
    parts = select_window(raw_bars(), BOUNDARY)
    assert [p.rollover_segment.iloc[0] for p in parts] == [12, 13]
    assert [len(p) for p in parts] == [90, 90]
    assert parts[1].open.iloc[0] == raw_bars().open.iloc[90]


@pytest.mark.parametrize("boundary", ["2025-03-17T22:01:00Z", "2025-03-17 22:00"])
def test_window_requires_actual_aware_boundary(boundary):
    with pytest.raises(ValueError):
        select_window(raw_bars(), boundary)


def test_window_rejects_unbounded_duration():
    with pytest.raises(ValueError, match="1 to 7"):
        select_window(raw_bars(), BOUNDARY, days_after=365)


def test_window_rejects_incorrect_segment_metadata():
    frame = raw_bars()
    frame["rollover_segment"] = 12
    with pytest.raises(ValueError, match="two contract segments"):
        select_window(frame, BOUNDARY)


@pytest.mark.parametrize("damage", ["price", "atr", "level", "sequence"])
def test_verification_rejects_corrupted_generated_evidence(damage):
    raw = raw_bars().iloc[90:].reset_index(drop=True)
    from scripts.run_isolated_rollover_check import RESET_LEVELS, RESET_FLAGS
    features = raw.copy()
    previous = raw.close.shift()
    tr = pd.concat([raw.high - raw.low, (raw.high - previous).abs(),
                    (raw.low - previous).abs()], axis=1).max(axis=1)
    features["atr_1m"] = tr.rolling(14, min_periods=14).mean()
    for col in RESET_LEVELS:
        features[col] = np.nan
    for col in RESET_FLAGS:
        features[col] = False
    if damage == "price":
        features.loc[0, "open"] += 1
    elif damage == "atr":
        features.loc[0, "atr_1m"] = 25
    elif damage == "level":
        features.loc[0, RESET_LEVELS[0]] = 100
    else:
        features.loc[0, RESET_FLAGS[0]] = True
    with pytest.raises(ValueError):
        verify_features(raw, features, 14)


def frozen_source(tmp_path):
    source = tmp_path / "source"
    cache = source / "cache"
    cache.mkdir(parents=True)
    raw = raw_bars()
    raw["atr_1m"] = 9999.  # Must not be inherited into fresh raw feature generation.
    raw_path = source / "raw.parquet"
    raw.to_parquet(raw_path, index=False)
    scored = cache / "scored.parquet"
    raw.to_parquet(scored, index=False)
    strategy = source / "strategy.yaml"
    strategy.write_bytes((ROOT / "config/strategy.yaml").read_bytes())
    sessions = source / "sessions.yaml"
    sessions.write_bytes((ROOT / "config/sessions.yaml").read_bytes())
    metadata = {
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "feature_code_manifest": {"files": {"src/structure.py": sha256_file(ROOT / "src/structure.py")}},
    }
    for role, path in (("input", raw_path), ("scored_cache", scored),
                       ("strategy_config", strategy), ("sessions_config", sessions)):
        metadata[role] = {"path": str(path.relative_to(source)), "sha256": sha256_file(path)}
    (cache / "cache_metadata.json").write_text(json.dumps(metadata))
    return source, cache


def test_real_feature_check_preserves_sources_and_matches_standalone_new_contract(tmp_path, monkeypatch):
    source, cache = frozen_source(tmp_path)
    before = {str(p): sha256_file(p) for p in source.rglob("*") if p.is_file()}
    # Only Git cleanliness is replaced during uncommitted test development;
    # producer verification, feature stages, input hashes and locks are real.
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    monkeypatch.setattr(experiment_identity, "clean_git_commit", lambda _: commit)
    output = tmp_path / "fresh"
    kwargs = dict(source_root=source, cache_dir=cache, output_dir=output,
                  boundary=BOUNDARY, completed_through="2026-01-02T00:00:00Z")
    result = run_check(**kwargs)
    assert result["inputs_unchanged"]
    assert len(result["segments"]) == 2
    assert result["segments"][1]["checks"]["same_contract_atr_matches"]
    lock = json.loads((output / "EXPERIMENT_INPUT_LOCK.json").read_text())
    assert "code:src/swing_lifecycle.py" in lock["artifacts"]
    assert "code:run_pipeline.py" in lock["artifacts"]
    assert before == {str(p): sha256_file(p) for p in source.rglob("*") if p.is_file()}
    rebuilt = pd.read_parquet(output / "segment_1/features_scored.parquet")
    new_raw = pd.read_parquet(output / "segment_1/raw_segment.parquet")
    assert "atr_1m" not in new_raw
    assert rebuilt.atr_1m.iloc[:13].isna().all()
    standalone = generate_features(new_raw, pipeline.load_yaml(source / "strategy.yaml"),
        pipeline.load_sessions_config(source / "sessions.yaml"), tmp_path / "standalone")
    standalone.to_parquet(tmp_path / "standalone.parquet", index=False)
    pd.testing.assert_frame_equal(rebuilt, pd.read_parquet(tmp_path / "standalone.parquet"))
    with pytest.raises(FileExistsError):
        run_check(**kwargs)


def test_check_rejects_output_inside_source_before_writing(tmp_path):
    source, cache = frozen_source(tmp_path)
    with pytest.raises(ValueError, match="separate"):
        run_check(source_root=source, cache_dir=cache, output_dir=source / "output",
                  boundary=BOUNDARY, completed_through="2026-01-02T00:00:00Z")
    assert not (source / "output").exists()
