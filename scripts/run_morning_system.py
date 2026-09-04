#!/usr/bin/env python3
"""Thin production orchestrator for the independently scheduled Phase 10 modes."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from time import perf_counter
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import run_pipeline as pipeline  # noqa: E402
from scripts import collect_projectx, healthcheck  # noqa: E402
from live_setup_state import arm_scenario, load_scenario, process_live_update, save_scenario  # noqa: E402
from premarket_refresh import compare_premarket_refresh  # noqa: E402
from production_logging import configure_production_logger, log_event  # noqa: E402
from production_paths import ProductionPaths, production_paths  # noqa: E402
from projectx_client import ProjectXAuthenticationError  # noqa: E402
from telegram_transport import send_telegram_alert  # noqa: E402

MODES = ("health", "collect", "premarket", "refresh", "arm", "live", "recap")


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def dispatch_mode(mode: str, handlers: Mapping[str, Callable[[], int]]) -> int:
    if mode not in MODES:
        raise ValueError(f"Unsupported production mode: {mode}")
    if mode not in handlers:
        raise RuntimeError(f"No handler configured for mode: {mode}")
    return int(handlers[mode]())


class MorningSystem:
    def __init__(self, *, project_root: Path = PROJECT_ROOT, environment: Mapping[str, str] | None = None, now_func: Callable[[], datetime] | None = None) -> None:
        self.project_root = project_root
        self.environment = dict(os.environ if environment is None else environment)
        self.now_func = now_func or (lambda: datetime.now(timezone.utc))
        self.paths: ProductionPaths = production_paths(project_root, self.environment.get("DATA_DIR"))
        secrets = [self.environment.get(name, "") for name in ("PROJECTX_API_KEY", "TOPSTEP_API_KEY", "TELEGRAM_BOT_TOKEN")]
        self.logger = configure_production_logger(self.paths.logs, component="orchestrator", sensitive_values=secrets)

    def _now(self) -> datetime:
        value = self.now_func()
        if value.tzinfo is None:
            raise ValueError("Production clock must be timezone-aware.")
        return value

    def _latest_raw(self) -> Path:
        candidates = sorted(self.paths.raw.glob("*.parquet"))
        if not candidates:
            raise FileNotFoundError("No ProjectX raw snapshot is available.")
        return candidates[-1]

    def _collect(self) -> Any:
        old = os.environ.copy()
        os.environ.update(self.environment)
        try:
            args = collect_projectx.parse_arguments(["--output-directory", str(self.paths.raw)])
            try:
                artifact = collect_projectx.collect(args, now_func=self._now)
            except ProjectXAuthenticationError:
                log_event(self.logger, "projectx_authentication_failed")
                raise
        finally:
            os.environ.clear()
            os.environ.update(old)
        metadata = json.loads(artifact.metadata_path.read_text(encoding="utf-8"))
        log_event(self.logger, "projectx_authentication_succeeded")
        log_event(
            self.logger,
            "projectx_collection_completed",
            contract=(metadata.get("contract") or {}).get("name"),
            request_count=metadata.get("history_request_count"),
            bar_count=artifact.rows,
            latest_timestamp=artifact.last_bar.isoformat(),
            snapshot=str(artifact.parquet_path),
            validation=metadata.get("validation"),
            freshness=metadata.get("freshness"),
        )
        return artifact

    def _analysis(self, *, as_of: datetime, stop_after: str) -> dict[str, Any]:
        pipeline.DEFAULT_STATE_DIRECTORY = self.paths.state
        pipeline.DEFAULT_REPORT_DIRECTORY = self.paths.reports
        pipeline.DEFAULT_RESULTS_DIRECTORY = self.paths.root / "results"
        pipeline.DEFAULT_PROCESSED_DIRECTORY = self.paths.root / "processed"
        pipeline.DEFAULT_NORMALIZED_DIRECTORY = self.paths.root / "normalized"
        started = perf_counter()
        artifacts = pipeline.run_pipeline(
            input_file=self._latest_raw(), source="PROJECTX",
            symbol=self.environment.get("PROJECTX_SYMBOL", "MNQ"),
            contract=self.environment.get("PROJECTX_CONTRACT_NAME"), source_timezone="UTC",
            sessions_config_path=self.project_root / "config" / "sessions.yaml",
            strategy_config_path=self.project_root / "config" / "strategy.yaml",
            stop_after=stop_after, as_of=as_of,
        )
        state = artifacts.get("market_state", {})
        plan = artifacts.get("trade_plan", {})
        log_event(self.logger, "market_state_built", duration_seconds=perf_counter() - started, as_of=state.get("as_of"), status=state.get("status"))
        log_event(self.logger, "planner_completed", decision=plan.get("decision"), preferred_scores=(plan.get("preferred") or {}).get("scores"))
        return artifacts

    def _deliver(self, alerts: list[dict[str, Any]]) -> None:
        if self.environment.get("TELEGRAM_ENABLED", "false").lower() not in {"1", "true", "yes"}:
            return
        for alert in alerts:
            send_telegram_alert(alert, token=self.environment.get("TELEGRAM_BOT_TOKEN"), chat_id=self.environment.get("TELEGRAM_CHAT_ID"))
            log_event(self.logger, "alert_delivered", alert=alert)

    def health(self) -> int:
        report = healthcheck.run_health_checks(project_root=self.project_root, environment=self.environment, now=self._now())
        log_event(self.logger, "health_check_completed", status=report["status"], checks=report["checks"])
        _atomic_json(self.paths.root / "production" / "health-latest.json", report)
        return int(report["exit_code"])

    def collect(self) -> int:
        self._collect()
        return 0

    def premarket(self) -> int:
        artifacts = self._analysis(as_of=self._now(), stop_after="morning_report")
        _atomic_json(self.paths.plans / "morning-state.json", artifacts["market_state"])
        _atomic_json(self.paths.plans / "morning-plan.json", artifacts["trade_plan"])
        log_event(self.logger, "morning_report_generated", decision=artifacts["morning_report"]["decision"])
        return 0

    def refresh(self) -> int:
        self._collect()
        artifacts = self._analysis(as_of=self._now(), stop_after="trade_plan")
        morning_state = json.loads((self.paths.plans / "morning-state.json").read_text(encoding="utf-8"))
        morning_plan = json.loads((self.paths.plans / "morning-plan.json").read_text(encoding="utf-8"))
        comparison = compare_premarket_refresh(morning_state, morning_plan, artifacts["market_state"], artifacts["trade_plan"])
        _atomic_json(self.paths.plans / "refresh-state.json", artifacts["market_state"])
        _atomic_json(self.paths.plans / "refresh-plan.json", artifacts["trade_plan"])
        _atomic_json(self.paths.comparisons / "latest.json", comparison)
        log_event(self.logger, "premarket_refresh_completed", classification=comparison["classification"], changes=comparison["changes"])
        return 0

    def arm(self) -> int:
        state_path = self.paths.plans / "refresh-state.json"
        plan_path = self.paths.plans / "refresh-plan.json"
        if not state_path.exists():
            state_path, plan_path = self.paths.plans / "morning-state.json", self.paths.plans / "morning-plan.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        for candidate in (plan.get("preferred"), plan.get("alternate")):
            if not candidate:
                continue
            record, alerts = arm_scenario(candidate, state)
            record["candidate"] = candidate
            destination = self.paths.live / f"{record['scenario_id']}.json"
            if destination.exists():
                record = load_scenario(destination)
                alerts = []
            else:
                save_scenario(record, destination)
            self._deliver(alerts)
            log_event(self.logger, "scenario_armed", scenario_id=record["scenario_id"], state=record["current_state"])
        return 0

    def live(self) -> int:
        self._collect()
        artifacts = self._analysis(as_of=self._now(), stop_after="trade_plan")
        for path in sorted(self.paths.live.glob("*.json")):
            record = load_scenario(path)
            candidate = record.get("candidate")
            if not candidate:
                raise RuntimeError(f"Scenario file lacks candidate: {path.name}")
            updated, alerts = process_live_update(record, candidate, artifacts["market_state"])
            save_scenario(updated, path)
            self._deliver(alerts)
            log_event(self.logger, "live_state_updated", scenario_id=updated["scenario_id"], previous_state=updated.get("previous_state"), current_state=updated["current_state"], alerts=alerts)
        return 0

    def recap(self) -> int:
        scenarios = [load_scenario(path) for path in sorted(self.paths.live.glob("*.json"))]
        local = self._now().astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d_%H%M")
        _atomic_json(self.paths.recaps / f"{local}_recap.json", {"generated_at": self._now().isoformat(), "scenarios": scenarios})
        log_event(self.logger, "monitoring_shutdown", scenario_count=len(scenarios))
        return 0

    def handlers(self) -> dict[str, Callable[[], int]]:
        return {name: getattr(self, name) for name in MODES}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one deterministic morning-system production mode.")
    parser.add_argument("mode", choices=MODES)
    args = parser.parse_args(argv)
    try:
        system = MorningSystem()
        log_event(system.logger, "startup", mode=args.mode)
        code = dispatch_mode(args.mode, system.handlers())
        log_event(system.logger, "shutdown", mode=args.mode, exit_code=code)
        return code
    except Exception:
        if "system" in locals():
            system.logger.exception("production_mode_failed", extra={"event": "production_mode_failed", "details": {"mode": args.mode}})
        else:
            print(f"FAIL: production mode {args.mode} could not initialize", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
