"""R4.5 checkpoint resume guard tests: no historical pipeline required."""
import json
from pathlib import Path

import pandas as pd
import pytest

from scripts import resume_r45 as mod


def test_checkpoint_missing_and_partial_never_overwritten(tmp_path):
    folder = tmp_path / "2024" / "baseline"
    assert mod.verified_checkpoint(folder) is None
    folder.mkdir(parents=True)
    (folder / "metrics.json").write_text(json.dumps({"trades": 1}))
    with pytest.raises(ValueError, match="Partial checkpoint"):
        mod.verified_checkpoint(folder)


def test_checkpoint_counts_and_points_are_checked(tmp_path):
    folder = tmp_path / "2024" / "candidate_conservative"
    folder.mkdir(parents=True)
    pd.DataFrame({"net_result_points": [25.0]}).to_csv(folder / "trades.csv", index=False)
    (folder / "metrics.json").write_text(json.dumps({"trades": 2, "net_points": 25.0}))
    with pytest.raises(ValueError, match="Count mismatch"):
        mod.verified_checkpoint(folder)
    (folder / "metrics.json").write_text(json.dumps({"trades": 1, "net_points": 30.0}))
    with pytest.raises(ValueError, match="Net points mismatch"):
        mod.verified_checkpoint(folder)
    (folder / "metrics.json").write_text(json.dumps({"trades": 1, "net_points": 25.0}))
    frame, metrics = mod.verified_checkpoint(folder)
    assert len(frame) == 1 and metrics["trades"] == 1


def test_worker_skips_existing_checkpoint_without_loading_features(monkeypatch, tmp_path):
    folder = tmp_path / "out/2024/candidate_conservative"
    folder.mkdir(parents=True)
    pd.DataFrame({"net_result_points": [25.0]}).to_csv(folder / "trades.csv", index=False)
    (folder / "metrics.json").write_text(json.dumps({"trades": 1, "net_points": 25.0}))
    monkeypatch.setattr(mod.pd, "read_parquet", lambda *a, **kw: pytest.fail("Recomputed complete checkpoint"))
    mod.worker(
        2024, "candidate_conservative", tmp_path / "out",
        tmp_path / "missing-config.yaml", tmp_path / "missing.parquet",
    )


def test_baseline_comparison_checks_exact_trade_fingerprint(monkeypatch, tmp_path):
    original = pd.DataFrame({
        "signal_time": ["2023-03-01T14:30:00Z"],
        "direction": ["long"],
        "net_result_points": [25.0],
    })
    changed = original.copy()
    changed.loc[0, "net_result_points"] = -25.0
    original.to_csv(tmp_path / "frozen.csv", index=False)
    monkeypatch.setattr(mod, "DEFAULT_LEDGERS", {2023: tmp_path / "frozen.csv"})
    monkeypatch.setattr(mod, "BASELINE_COUNTS", {2023: 1})
    mod.check_baseline(2023, original)
    with pytest.raises(ValueError, match="differ"):
        mod.check_baseline(2023, changed)


def test_finalize_refuses_missing_models_before_writing(tmp_path):
    with pytest.raises(ValueError, match="Missing checkpoint"):
        mod.finalize(tmp_path)
    assert not (tmp_path / "model_summary.csv").exists()
    assert not (tmp_path / "r45_results.json").exists()


def test_selective_loader_excludes_only_known_diagnostic_payloads(tmp_path):
    path = tmp_path / "features.parquet"
    pd.DataFrame({
        "timestamp": pd.to_datetime(["2024-01-01T00:00:00Z"]),
        "open": [100.0],
        "close": [101.0],
        "dol_ranked_candidates": ["large-json"],
        "snr_market_state_json": ["large-json"],
        "snr_raw_components_json": ["large-json"],
        "dol_primary_components": ["large-json"],
        "dol_alternate_components": ["large-json"],
        "dol_direction": ["bullish"],
        "snr_5m": [1.4],
    }).to_parquet(path, index=False)
    reduced = mod.load_reduced_features(path)
    assert set(reduced.columns) == {
        "timestamp", "open", "close", "dol_direction", "snr_5m",
    }
    assert reduced["dol_direction"].iloc[0] == "bullish"
