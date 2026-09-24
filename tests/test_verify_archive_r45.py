"""Small synthetic checks for the guarded R4.5 archival audit."""
import json
from pathlib import Path

import pandas as pd
import pytest

from scripts import verify_archive_r45 as mod


def test_trade_fingerprint_normalizes_utc_and_order():
    old = pd.DataFrame({
        "signal_time": ["2025-01-02T14:32:00Z", "2025-01-02T14:33:00+00:00"],
        "direction": ["LONG", "short"],
        "net_result_points": [25.0, -25.0],
    })
    new = pd.DataFrame({
        "signal_time": ["2025-01-02T09:33:00-05:00", "2025-01-02T09:32:00-05:00"],
        "direction": ["Short", "long"],
        "net_result_points": [-25.0, 25.0],
    })
    assert mod.trade_fingerprint(old) == mod.trade_fingerprint(new)


def test_r45_archive_audit_detects_baseline_drift(monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "BASELINE_COUNTS", {year: 1 for year in mod.YEARS})
    out = tmp_path / "out"
    ledgers = {}
    years = {}
    for year in mod.YEARS:
        ledgers[year] = tmp_path / f"{year}_frozen.csv"
        trade = pd.DataFrame([{
            "signal_time": f"{year}-02-01T14:31:00Z",
            "direction": "long", "net_result_points": 25.0,
        }])
        trade.to_csv(ledgers[year], index=False)
        years[str(year)] = {}
        for model in mod.MODELS:
            folder = out / str(year) / model
            folder.mkdir(parents=True)
            trade.to_csv(folder / "trades.csv", index=False)
            (folder / "metrics.json").write_text(json.dumps({"trades": 1}))
            years[str(year)][model] = {"metrics": {"trades": 1}}
    aggregates = {}
    for model in mod.MODELS:
        combined = pd.concat([pd.read_csv(ledgers[y]) for y in mod.YEARS])
        combined.to_csv(out / f"{model}_all_years_trades.csv", index=False)
        aggregates[model] = {"trades": 3}
    pd.DataFrame([{"model": m, "trades": 3} for m in mod.MODELS]).to_csv(
        out / "model_summary.csv", index=False
    )
    (out / "r45_results.json").write_text(json.dumps({
        "years": years, "aggregate": aggregates,
    }))
    assert mod.audit(out, ledgers)["aggregate"]["baseline"] == {
        "trades": 3, "net_points": 75.0,
    }
    wrong = out / "2024" / "baseline" / "trades.csv"
    altered = pd.read_csv(wrong)
    altered.loc[0, "net_result_points"] = -25.0
    altered.to_csv(wrong, index=False)
    with pytest.raises(ValueError, match="baseline replay"):
        mod.audit(out, ledgers)
