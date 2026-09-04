from copy import deepcopy
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from premarket_refresh import FLIPPED, STRENGTHENED, UNCHANGED, WEAKENED, build_0925_refresh, compare_premarket_refresh
from trade_planner import build_trade_plan
from test_trade_planner import _config, _state

def _snapshots():
    state = _state(); state["as_of"]="2026-09-04T13:00:00+00:00"; state["source_snapshots"]=["0900.json"]
    return state, build_trade_plan(state,_config())
def test_identical_is_unchanged_and_deterministic():
    state, plan=_snapshots(); after=deepcopy(state); after["as_of"]="2026-09-04T13:25:00+00:00"; after["source_snapshots"]=["0925.json"]
    result=compare_premarket_refresh(state,plan,after,deepcopy(plan)); assert result["classification"]==UNCHANGED and result["changes"]==[]
def test_support_loss_and_added_entry_evidence_classify():
    state,plan=_snapshots(); weak=deepcopy(state); weak["as_of"]="2026-09-04T13:25:00+00:00"; weak["scores"]["long"]["disabled"]=True; weak["scores"]["short"]["disabled"]=True
    assert compare_premarket_refresh(state,plan,weak,build_trade_plan(weak,_config()))["classification"]==WEAKENED
    strong=deepcopy(state); strong["as_of"]="2026-09-04T13:25:00+00:00"; strong["structure"]["bullish_reversal_sequence"]=True; strong["liquidity"]["recent_sell_side_sweep"]=True; strong["displacement"]["bullish_displacement"]=True; strong["fvgs"]["bullish_fvg_retest_hold"]=True
    result = compare_premarket_refresh(state,plan,strong,build_trade_plan(strong,_config()))
    assert result["classification"]==STRENGTHENED
    assert {change["category"] for change in result["changes"]} >= {"structure", "liquidity/sweep", "entry"}
    assert all(change["reason"] for change in result["changes"])
def test_direction_flip_and_post_0925_are_rejected():
    state,plan=_snapshots(); flip=deepcopy(state); flip["as_of"]="2026-09-04T13:25:00+00:00"; flip["scores"]["preferred_direction"]="short"; flip["draw_on_liquidity"]["direction"]="bearish"; flip["draw_on_liquidity"]["primary"]=deepcopy(flip["draw_on_liquidity"]["alternate"])
    assert compare_premarket_refresh(state,plan,flip,build_trade_plan(flip,_config()))["classification"]==FLIPPED
    flip["as_of"]="2026-09-04T13:30:00+00:00"
    try: compare_premarket_refresh(state,plan,flip,plan)
    except ValueError: pass
    else: raise AssertionError("09:30 data was accepted")

def test_refresh_builds_separate_causal_snapshot(monkeypatch, tmp_path):
    state, plan = _snapshots()
    fake = deepcopy(state); fake["as_of"] = "2026-09-04T13:25:00+00:00"
    monkeypatch.setattr("premarket_refresh.build_market_state", lambda *_args, **kwargs: fake)
    refreshed, refreshed_plan, paths = build_0925_refresh(
        object(), as_of=fake["as_of"], symbol="MNQ", contract="MNQU6", strategy_config=_config(),
        data_quality={}, freshness={}, source_snapshots=["raw-0925.parquet"], state_directory=str(tmp_path),
    )
    assert refreshed["as_of"] != state["as_of"] and refreshed_plan["as_of"] == refreshed["as_of"]
    assert Path(paths["snapshot"]).name == "2026-09-04_0925_market_state.json"
    assert compare_premarket_refresh(state, plan, refreshed, refreshed_plan)["refreshed_as_of"].startswith("2026-09-04T09:25")
