import json
import subprocess

import pandas as pd
import pytest
import yaml

from scripts.run_isolated_cache_replay import historical_timing, replay, verify_producer
from feature_cache import sha256_file
from experiment_identity import verify_input_lock
from tests.test_confirmed_entry_execution import bars, config


def test_timing_preserves_late_availability_and_incomplete_flags():
    frame = bars()
    frame.loc[1, "available_at"] += pd.Timedelta(minutes=2)
    frame.loc[0, "bar_complete"] = False
    original = frame.copy(deep=True)
    derived = historical_timing(frame, frame.timestamp.iloc[2])
    assert not derived.bar_complete.iloc[0]
    assert not derived.bar_complete.iloc[1]
    assert derived.available_at.iloc[1] == frame.available_at.iloc[1]
    pd.testing.assert_frame_equal(frame, original)


def test_missing_flags_derived_at_exact_close_without_changing_features():
    frame = bars().drop(columns=["available_at", "bar_complete"])
    frame["volume"] = 100
    derived = historical_timing(frame, frame.timestamp.iloc[2])
    assert derived.bar_complete.tolist() == [True, True, False, False, False]
    assert derived.available_at.iloc[1] == frame.timestamp.iloc[2]
    pd.testing.assert_frame_equal(derived[frame.columns], frame)


@pytest.mark.parametrize("change", ["naive", "null", "duplicate", "unordered", "off_minute", "bad_flag", "null_availability"])
def test_malformed_historical_time_fails_closed(change):
    frame = bars()
    if change == "naive":
        frame["timestamp"] = frame.timestamp.dt.tz_localize(None)
    elif change == "null":
        frame.loc[1, "timestamp"] = pd.NaT
    elif change == "duplicate":
        frame.loc[1, "timestamp"] = frame.timestamp.iloc[0]
    elif change == "unordered":
        frame = frame.iloc[::-1]
    elif change == "off_minute":
        frame["timestamp"] += pd.Timedelta(seconds=1)
    elif change == "bad_flag":
        frame["bar_complete"] = 1
    else:
        frame.loc[1, "available_at"] = pd.NaT
    with pytest.raises(ValueError):
        historical_timing(frame, "2027-01-01T00:00:00Z")


def test_naive_cutoff_rejected():
    with pytest.raises(ValueError, match="timezone"):
        historical_timing(bars(), "2027-01-01")


@pytest.fixture
def frozen(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    for key, value in (("user.email", "test@example.test"), ("user.name", "Fixture")):
        subprocess.run(["git", "-C", str(repo), "config", key, value], check=True)
    (repo / "src").mkdir()
    (repo / "src/feature.py").write_text("# frozen producer\n")
    (repo / "config").mkdir()
    (repo / "config/research_policy.yaml").write_text("periods:\n  2026: pseudo_out_of_sample_validation\n")
    (repo / "requirements.txt").write_text("pandas\n")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "producer"], check=True)
    producer = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    expected = sha256_file(repo / "src/feature.py")
    (repo / "src/feature.py").write_text("# later feature code\n")
    subprocess.run(["git", "-C", str(repo), "commit", "-qam", "later"], check=True)
    source = tmp_path / "source"
    cache = source / "cache"
    cache.mkdir(parents=True)
    frame = bars().drop(columns=["available_at", "bar_complete"])
    frame["volume"] = 100
    frame.to_parquet(cache / "scored.parquet", index=False)
    frame[["timestamp", "open", "high", "low", "close", "volume"]].to_parquet(source / "raw.parquet", index=False)
    (source / "strategy.yaml").write_text(yaml.safe_dump(config()))
    (source / "sessions.yaml").write_text("timezone: America/New_York\n")
    def artifact(name):
        return {"path": name, "sha256": sha256_file(source / name)}
    metadata = {"git_sha": producer, "feature_code_manifest": {"files": {"src/feature.py": expected}},
                "input": artifact("raw.parquet"), "scored_cache": {**artifact("cache/scored.parquet"), "rows": len(frame)},
                "strategy_config": artifact("strategy.yaml"), "sessions_config": artifact("sessions.yaml")}
    (cache / "cache_metadata.json").write_text(json.dumps(metadata))
    return dict(source_root=source, cache_dir=cache, output_dir=tmp_path / "outputs",
                completed_through="2027-01-01T00:00:00Z", year=2026, repository=repo)


def test_actual_two_mode_replay_locks_inputs_and_preserves_originals(frozen):
    source = frozen["source_root"]
    before = {str(p): sha256_file(p) for p in source.rglob("*") if p.is_file()}
    result = replay(**frozen)
    assert result["inputs_unchanged"]
    assert all(item["trades"] == 1 for item in result["results"].values())
    output = frozen["output_dir"]
    provenance = json.loads((output / "REPLAY_PROVENANCE.json").read_text())
    assert provenance["current_feature_files_differing_from_producer"] == ["src/feature.py"]
    lock = json.loads((output / "EXPERIMENT_INPUT_LOCK.json").read_text())
    verify_input_lock(lock, root=frozen["repository"])
    assert before == {str(p): sha256_file(p) for p in source.rglob("*") if p.is_file()}
    trades = pd.read_csv(output / "market_after_retest_confirmation_v1/trades.csv")
    assert trades.setup_family.tolist() == ["reversal"]
    with pytest.raises(FileExistsError):
        replay(**frozen)


@pytest.mark.parametrize("change", ["source_drift", "producer_blob", "output_in_source", "late_cutoff", "missing_manifest"])
def test_replay_rejects_drift_unsafe_output_and_unproved_producer(frozen, change):
    metadata_path = frozen["cache_dir"] / "cache_metadata.json"
    metadata = json.loads(metadata_path.read_text())
    if change == "source_drift":
        (frozen["source_root"] / "raw.parquet").write_bytes(b"drift")
    elif change == "producer_blob":
        metadata["feature_code_manifest"]["files"]["src/feature.py"] = "0" * 64
        metadata_path.write_text(json.dumps(metadata))
    elif change == "missing_manifest":
        metadata["feature_code_manifest"] = {}
        metadata_path.write_text(json.dumps(metadata))
    elif change == "output_in_source":
        frozen["output_dir"] = frozen["source_root"] / "outputs"
    else:
        frozen["completed_through"] = "2026-08-31T13:31:00Z"
    with pytest.raises(ValueError):
        replay(**frozen)
    assert not frozen["output_dir"].exists()


def test_date_bounded_replay_reads_only_selected_bars(frozen):
    frozen.update(evaluation_start="2026-08-31T13:30:00Z", evaluation_end="2026-08-31T13:34:00Z")
    replay(**frozen)
    derived = pd.read_parquet(frozen["output_dir"] / "derived_scored.parquet")
    assert len(derived) == 4
    provenance = json.loads((frozen["output_dir"] / "REPLAY_PROVENANCE.json").read_text())
    assert provenance["source_cache_rows"] == 5


@pytest.mark.parametrize("start,end", [("2026-08-31", "2026-09-01T00:00:00Z"),
                                       ("2025-01-01T00:00:00Z", "2026-09-01T00:00:00Z")])
def test_invalid_sample_bounds_rejected(frozen, start, end):
    frozen.update(evaluation_start=start, evaluation_end=end)
    with pytest.raises(ValueError):
        replay(**frozen)
    assert not frozen["output_dir"].exists()
