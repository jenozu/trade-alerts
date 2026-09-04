from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib import error

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent))

import run_pipeline
from production_logging import configure_production_logger, log_event
from production_paths import production_paths
from scripts.healthcheck import run_health_checks
from scripts.run_morning_system import MorningSystem, dispatch_mode, main
from telegram_transport import TelegramTransportError, render_telegram_alert, send_telegram_alert
from test_live_setup_state import _observation
from test_trade_planner import _config, _state
from trade_planner import build_trade_plan


def _probe(*, fresh=True):
    return lambda _env, _now: {
        "contract": "MNQU6", "bar_count": 10,
        "last_bar": "2026-09-04T12:55:00+00:00", "fresh": fresh,
    }


def _environment(tmp_path):
    return {
        "DATA_DIR": str(tmp_path / "data"),
        "PROJECTX_USERNAME": "configured-user",
        "PROJECTX_API_KEY": "configured-key",
        "TELEGRAM_ENABLED": "false",
    }


def test_health_check_pass_is_machine_readable(tmp_path):
    report = run_health_checks(
        environment=_environment(tmp_path), probe=_probe(),
        now=datetime(2026, 9, 4, 12, 55, tzinfo=timezone.utc),
    )
    assert report["status"] == "PASS" and report["exit_code"] == 0
    assert {item["name"] for item in report["checks"]} >= {
        "credentials", "projectx_auth", "current_contract", "market_freshness",
    }


def test_health_check_missing_credentials_is_critical(tmp_path):
    report = run_health_checks(environment={"DATA_DIR": str(tmp_path)}, probe=_probe())
    assert report["status"] == "FAIL" and report["exit_code"] != 0
    credentials = next(item for item in report["checks"] if item["name"] == "credentials")
    assert "PROJECTX_API_KEY" in credentials["message"]


def test_health_check_accepts_existing_legacy_credential_names(tmp_path):
    environment = {
        "DATA_DIR": str(tmp_path / "data"),
        "TOPSTEP_USERNAME": "configured-user",
        "TOPSTEP_API_KEY": "configured-key",
    }
    report = run_health_checks(environment=environment, probe=_probe())
    assert report["status"] == "PASS"


def test_health_check_stale_data_fails(tmp_path):
    report = run_health_checks(environment=_environment(tmp_path), probe=_probe(fresh=False))
    freshness = next(item for item in report["checks"] if item["name"] == "market_freshness")
    assert report["status"] == "FAIL" and freshness["status"] == "FAIL"


def test_structured_logs_never_contain_secret_values(tmp_path):
    secret = "ultra-private-key"
    logger = configure_production_logger(tmp_path, component="test", sensitive_values=[secret])
    log_event(logger, "authentication_failed", api_key=secret, message=f"failed {secret}")
    for handler in logger.handlers:
        handler.flush()
    content = (tmp_path / "production.jsonl").read_text(encoding="utf-8")
    payload = json.loads(content)
    assert secret not in content and payload["details"]["api_key"] == "[REDACTED]"


def test_orchestrator_dispatch_and_safe_failure(monkeypatch):
    called = []
    assert dispatch_mode("health", {"health": lambda: called.append("health") or 0}) == 0
    assert called == ["health"]
    monkeypatch.setattr(MorningSystem, "handlers", lambda self: {"health": lambda: (_ for _ in ()).throw(RuntimeError("boom"))})
    assert main(["health"]) == 1


def test_premarket_mode_persists_state_and_plan_from_existing_pipeline(monkeypatch, tmp_path):
    system = MorningSystem(environment=_environment(tmp_path), now_func=lambda: datetime(2026, 9, 4, 13, 0, tzinfo=timezone.utc))
    state = _state(); plan = build_trade_plan(state, _config())
    report = {"decision": plan["decision"]}
    monkeypatch.setattr(system, "_analysis", lambda **_kwargs: {"market_state": state, "trade_plan": plan, "morning_report": report})
    assert system.premarket() == 0
    assert json.loads((system.paths.plans / "morning-plan.json").read_text())["decision"] == plan["decision"]


def test_refresh_mode_collects_compares_and_persists(monkeypatch, tmp_path):
    system = MorningSystem(environment=_environment(tmp_path), now_func=lambda: datetime(2026, 9, 4, 13, 25, tzinfo=timezone.utc))
    morning = _state(); morning["as_of"] = "2026-09-04T13:00:00+00:00"
    morning_plan = build_trade_plan(morning, _config())
    refreshed = deepcopy(morning); refreshed["as_of"] = "2026-09-04T13:25:00+00:00"
    refreshed_plan = build_trade_plan(refreshed, _config())
    system.paths.plans.mkdir(parents=True, exist_ok=True)
    (system.paths.plans / "morning-state.json").write_text(json.dumps(morning))
    (system.paths.plans / "morning-plan.json").write_text(json.dumps(morning_plan))
    monkeypatch.setattr(system, "_collect", lambda: None)
    monkeypatch.setattr(system, "_analysis", lambda **_kwargs: {"market_state": refreshed, "trade_plan": refreshed_plan})
    assert system.refresh() == 0
    assert json.loads((system.paths.comparisons / "latest.json").read_text())["classification"] == "UNCHANGED"


def test_arm_is_idempotent_and_live_uses_phase9_transition(monkeypatch, tmp_path):
    system = MorningSystem(environment=_environment(tmp_path), now_func=lambda: datetime(2026, 9, 4, 13, 29, tzinfo=timezone.utc))
    state = _state(); state["as_of"] = "2026-09-04T13:25:00+00:00"
    plan = build_trade_plan(state, _config())
    (system.paths.plans / "refresh-state.json").write_text(json.dumps(state))
    (system.paths.plans / "refresh-plan.json").write_text(json.dumps(plan))
    delivered = []
    monkeypatch.setattr(system, "_deliver", lambda alerts: delivered.extend(alerts))
    assert system.arm() == 0 and system.arm() == 0
    files = sorted(system.paths.live.glob("*.json"))
    assert len(files) == 2 and len(delivered) == 2
    live_state = _observation("long", 30)
    monkeypatch.setattr(system, "_collect", lambda: None)
    monkeypatch.setattr(system, "_analysis", lambda **_kwargs: {"market_state": live_state, "trade_plan": plan})
    assert system.live() == 0
    long_record = next(json.loads(path.read_text()) for path in files if json.loads(path.read_text())["direction"] == "long")
    assert long_record["current_state"] == "LEVEL_REACHED"


def test_recap_uses_deterministic_artifact_path(tmp_path):
    system = MorningSystem(environment=_environment(tmp_path), now_func=lambda: datetime(2026, 9, 4, 14, 30, tzinfo=timezone.utc))
    assert system.recap() == 0
    assert (system.paths.recaps / "2026-09-04_1030_recap.json").exists()


def test_telegram_transport_renders_and_retries_without_strategy_logic():
    alert = {"type": "ENTRY VALID", "scenario_id": "abc", "state": "ENTRY_VALID", "as_of": "now"}
    calls = []
    def requester(url, payload, timeout):
        calls.append((url, payload, timeout))
        if len(calls) == 1:
            raise error.URLError("temporary")
        return {"ok": True}
    result = send_telegram_alert(alert, token="token", chat_id="chat", requester=requester, sleep_func=lambda _delay: None)
    assert result["ok"] is True and len(calls) == 2
    assert render_telegram_alert(alert).startswith("type: ENTRY VALID")


def test_telegram_missing_credentials_and_terminal_failure_are_safe():
    with pytest.raises(TelegramTransportError, match="required"):
        send_telegram_alert({}, token=None, chat_id=None)
    with pytest.raises(TelegramTransportError, match="after retries"):
        send_telegram_alert({}, token="x", chat_id="y", attempts=2, requester=lambda *_args: (_ for _ in ()).throw(TimeoutError()), sleep_func=lambda _delay: None)


def test_production_paths_create_all_ignored_runtime_directories(tmp_path):
    paths = production_paths(tmp_path)
    assert all(path.is_dir() for path in (paths.logs, paths.state, paths.reports, paths.live, paths.recaps, paths.plans, paths.comparisons))


def test_systemd_units_are_weekday_et_aware_and_complete():
    directory = Path("deploy/systemd")
    timers = {path.name: path.read_text() for path in directory.glob("*.timer")}
    assert len(timers) == 7
    assert all("Mon..Fri" in text and "America/New_York" in text for text in timers.values())
    assert "08:55:00" in timers["trade-alerts-health.timer"]
    assert "10:30:00" in timers["trade-alerts-recap.timer"]
    service = (directory / "trade-alerts@.service").read_text()
    assert "EnvironmentFile=-@PROJECT_ROOT@/.env" in service and "run_morning_system.py %i" in service


def test_deployment_scripts_are_fast_forward_only_and_secret_safe():
    deploy = Path("deploy.sh").read_text()
    install = Path("deploy/install.sh").read_text()
    assert "git merge --ff-only origin/main" in deploy
    assert "reset --hard" not in deploy and "checkout --" not in deploy
    assert ".env" in deploy and "rm .env" not in deploy
    assert "--replace" in install and "systemctl daemon-reload" in install


def test_pipeline_accepts_collector_parquet_without_reinterpreting_timezone(tmp_path):
    timestamp = pd.Timestamp("2026-09-04T13:00:00Z")
    frame = pd.DataFrame({"timestamp": [timestamp], "open": [100.0], "high": [101.0], "low": [99.0], "close": [100.5], "volume": [10.0], "source": ["PROJECTX"], "symbol": ["MNQ"], "contract": ["MNQU6"]})
    path = tmp_path / "snapshot.parquet"; frame.to_parquet(path, index=False)
    loaded = run_pipeline.stage_load(input_file=path, source="PROJECTX", symbol="MNQ", contract=None, source_timezone="UTC")
    assert str(loaded["timestamp"].dt.tz) == "UTC" and loaded.iloc[0]["source"] == "PROJECTX"
