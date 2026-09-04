from copy import deepcopy
from pathlib import Path
import sys

from report_generator import build_morning_alert, generate_optional_narrative, render_morning_markdown, save_morning_report
from trade_planner import DECISION_NO_TRADE, build_trade_plan

sys.path.insert(0, str(Path(__file__).parent))
from test_trade_planner import _config, _state


def test_morning_alert_is_linked_deterministic_and_complete(tmp_path):
    state = _state(); state["source_snapshots"] = ["data/state/2026-09-04_0900_market_state.json"]
    alert = build_morning_alert(state, build_trade_plan(state, _config()))
    assert alert["is_hypothesis"] is True and alert["preferred"]["scenario_status"] == "HYPOTHESIS"
    assert alert["source_market_state"]["snapshots"] == state["source_snapshots"]
    assert set(alert["chart_markup"]["levels"]) == {"pdh", "pdl", "pmh", "pml", "asia_high", "asia_low", "london_high", "london_low"}
    markdown = render_morning_markdown(alert)
    assert "## Scenario A — Preferred" in markdown and "hypothesis/plan" in markdown
    paths = save_morning_report(alert, tmp_path, markdown=markdown)
    assert paths["json"].name == "2026-09-04_0900_morning_report.json" and paths["markdown"].exists()


def test_no_analysis_and_optional_narrative_failure_are_safe():
    state = _state(); state["status"] = {"code": "no_analysis", "message": "fatal data failure"}
    plan = build_trade_plan(state, _config()); alert = build_morning_alert(state, plan)
    before = deepcopy(alert)
    assert plan["decision"] == DECISION_NO_TRADE and alert["decision"] == "NO ANALYSIS"
    assert generate_optional_narrative(lambda _: (_ for _ in ()).throw(RuntimeError("offline")), alert) is None
    assert alert == before


def test_report_ignores_unseen_future_payload():
    state = _state(); plan = build_trade_plan(state, _config())
    future = deepcopy(state); future["unseen_future_append"] = {"pdh": 99999}
    assert build_morning_alert(state, plan) == build_morning_alert(future, plan)
