import pandas as pd

from tools.barchart.analyze_barchart_rollovers import analyze_pair


def _df(contract, rows):
    return pd.DataFrame({
        "timestamp": [pd.Timestamp(ts, tz="UTC") for ts, _ in rows],
        "volume": [v for _, v in rows],
        "contract": contract,
    }).assign(trading_date=lambda x: x["timestamp"].dt.tz_convert("America/Chicago").dt.date)


def test_analyze_pair_selects_first_two_day_confirmed_crossover():
    old = pd.DataFrame({
        "trading_date": [pd.Timestamp("2026-06-10").date(), pd.Timestamp("2026-06-11").date(), pd.Timestamp("2026-06-12").date()],
        "volume": [100, 80, 60],
    })
    new = pd.DataFrame({
        "trading_date": [pd.Timestamp("2026-06-10").date(), pd.Timestamp("2026-06-11").date(), pd.Timestamp("2026-06-12").date()],
        "volume": [50, 90, 120],
    })
    result = analyze_pair(old, new, "NMM26", "NMU26", 2)
    assert result["selected_trading_date"] == "2026-06-11"
    assert result["method"] == "confirmed_volume_crossover"


def test_analyze_pair_flags_unconfirmed_fallback():
    old = pd.DataFrame({
        "trading_date": [pd.Timestamp("2026-06-10").date(), pd.Timestamp("2026-06-11").date()],
        "volume": [100, 100],
    })
    new = pd.DataFrame({
        "trading_date": [pd.Timestamp("2026-06-10").date(), pd.Timestamp("2026-06-11").date()],
        "volume": [120, 90],
    })
    result = analyze_pair(old, new, "NMM26", "NMU26", 2)
    assert result["selected_trading_date"] == "2026-06-10"
    assert result["method"] == "first_volume_crossover_unconfirmed"
