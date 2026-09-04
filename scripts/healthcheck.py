#!/usr/bin/env python3
"""Deterministic, secret-safe production readiness checks."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Callable, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from production_paths import production_paths  # noqa: E402
from projectx_client import ProjectXClient, assess_bar_freshness  # noqa: E402

REQUIRED_ENVIRONMENT = ("PROJECTX_USERNAME", "PROJECTX_API_KEY")
REQUIRED_FILES = ("config/sessions.yaml", "config/strategy.yaml", "config/projectx.yaml.example")
REQUIRED_MODULES = (
    "projectx_client", "market_state", "trade_planner", "report_generator",
    "premarket_refresh", "live_setup_state",
)


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    message: str
    critical: bool = True


def _default_probe(environment: Mapping[str, str], now: datetime) -> dict[str, Any]:
    username = environment.get("PROJECTX_USERNAME") or environment.get("TOPSTEP_USERNAME")
    api_key = environment.get("PROJECTX_API_KEY") or environment.get("TOPSTEP_API_KEY")
    client = ProjectXClient(
        username=str(username or ""),
        api_key=str(api_key or ""),
        base_url=environment.get("PROJECTX_BASE_URL", "https://api.topstepx.com"),
        live=environment.get("PROJECTX_LIVE", "false").lower() in {"1", "true", "yes"},
    )
    client.authenticate()
    contract = client.resolve_contract(symbol=environment.get("PROJECTX_SYMBOL", "MNQ"))
    bars = client.fetch_bars(
        symbol=environment.get("PROJECTX_SYMBOL", "MNQ"), contract=contract,
        start_time=now - timedelta(minutes=15), end_time=now,
        request_delay_seconds=0,
    )
    freshness = assess_bar_freshness(bars, reference_time=now, maximum_age=timedelta(minutes=5))
    return {"contract": contract.name, "bar_count": len(bars), "last_bar": bars["timestamp"].max().isoformat(), "fresh": freshness.fresh}


def run_health_checks(
    *, project_root: Path = PROJECT_ROOT, environment: Mapping[str, str] | None = None,
    probe: Callable[[Mapping[str, str], datetime], Mapping[str, Any]] = _default_probe,
    now: datetime | None = None,
) -> dict[str, Any]:
    env = dict(os.environ if environment is None else environment)
    current = now or datetime.now(timezone.utc)
    results: list[CheckResult] = []
    results.append(CheckResult("python_runtime", "PASS" if sys.version_info >= (3, 11) else "FAIL", f"Python {sys.version_info.major}.{sys.version_info.minor}"))
    missing_files = [name for name in REQUIRED_FILES if not (project_root / name).is_file()]
    results.append(CheckResult("required_files", "FAIL" if missing_files else "PASS", f"missing={missing_files}" if missing_files else "required configuration present"))
    missing_modules = [name for name in REQUIRED_MODULES if importlib.util.find_spec(name) is None]
    results.append(CheckResult("required_modules", "FAIL" if missing_modules else "PASS", f"missing={missing_modules}" if missing_modules else "Phase 1-9 modules importable"))
    try:
        paths = production_paths(project_root, env.get("DATA_DIR"))
        with tempfile.NamedTemporaryFile(dir=paths.root, prefix=".health-", delete=True):
            pass
        results.append(CheckResult("data_directory", "PASS", "runtime directories writable"))
    except OSError as exc:
        results.append(CheckResult("data_directory", "FAIL", f"runtime directory is not writable: {exc}"))
    username = env.get("PROJECTX_USERNAME") or env.get("TOPSTEP_USERNAME")
    api_key = env.get("PROJECTX_API_KEY") or env.get("TOPSTEP_API_KEY")
    missing_env = [name for name, value in zip(REQUIRED_ENVIRONMENT, (username, api_key)) if not value]
    if missing_env:
        results.append(CheckResult("credentials", "FAIL", f"missing environment names: {missing_env}"))
    else:
        results.append(CheckResult("credentials", "PASS", "required environment names are set"))
        try:
            outcome = dict(probe(env, current))
            results.append(CheckResult("projectx_auth", "PASS", "read-only authentication succeeded"))
            results.append(CheckResult("current_contract", "PASS" if outcome.get("contract") else "FAIL", f"contract={outcome.get('contract')}"))
            results.append(CheckResult("market_freshness", "PASS" if outcome.get("fresh") else "FAIL", f"fresh={bool(outcome.get('fresh'))}; bars={outcome.get('bar_count')}; last_bar={outcome.get('last_bar')}"))
        except Exception as exc:
            results.append(CheckResult("projectx_auth", "FAIL", f"read-only ProjectX probe failed: {type(exc).__name__}"))
    failed = [item for item in results if item.status == "FAIL" and item.critical]
    return {"status": "FAIL" if failed else "PASS", "exit_code": 1 if failed else 0, "checked_at": current.isoformat(), "checks": [asdict(item) for item in results]}


def main() -> int:
    report = run_health_checks()
    print(json.dumps(report, indent=2, sort_keys=True))
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
