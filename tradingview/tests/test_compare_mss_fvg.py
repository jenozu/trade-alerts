"""Read-only parity-audit contract tests. Does not run TradingView Pine."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import yaml

from tradingview.audit.compare_mss_fvg import (
    AuditInputError,
    PINE_FIELDS,
    REPO,
    audit,
    prepare_bars,
    python_reference,
)


@pytest.fixture(scope="module")
def config():
    return yaml.safe_load((REPO / "config/strategy.yaml").read_text(encoding="utf-8"))


@pytest.fixture
def pine_chart(config):
    # Construct one-minute OHLC and compute the expected Python truth using
    # the repo's real swing/structure/FVG modules (no hardcoded expected flags).
    size = 180
    time = pd.date_range("2025-03-10T13:30:00Z", periods=size, freq="min")
    n = np.arange(size)
    mid = 20500.0 + np.round((17.0 * np.sin(n / 8.0) + n / 16.0) * 4) / 4
    open_ = mid - 0.5
    close = mid + 0.5
    bars = pd.DataFrame({
        "time": (time.astype("int64") // 1_000_000_000).astype("int64"),
        "open": open_,
        "high": np.maximum(open_, close) + 1.0,
        "low": np.minimum(open_, close) - 1.0,
        "close": close,
    })
    truth = python_reference(prepare_bars(bars, chart=True), config)
    for raw, title in PINE_FIELDS.items():
        bars[title] = truth[raw].astype(int).to_numpy()
    return bars


def test_exact_reference_chart_events_match(pine_chart, config):
    result = audit(pine_chart, settings=config, warmup_bars=20, min_shared_bars=100)
    assert result["status"] == "raw_events_match"
    assert result["compared_bars"] == 160
    assert all(v["disagreeing_bars"] == 0 for v in result["signals"].values())


def test_unsorted_chart_export_preserves_flag_timestamp_pairing(pine_chart, config):
    shuffled = pine_chart.sample(frac=1, random_state=17).reset_index(drop=True)
    result = audit(shuffled, settings=config, warmup_bars=20, min_shared_bars=100)
    assert result["status"] == "raw_events_match"


def test_single_mss_mismatch_detected(pine_chart, config):
    changed = pine_chart.copy()
    title = PINE_FIELDS["bullish_mss"]
    changed.loc[75, title] = 1 - int(changed.loc[75, title])
    result = audit(changed, settings=config, warmup_bars=20, min_shared_bars=100)
    assert result["status"] == "differences_found"
    assert result["signals"]["bullish_mss"]["disagreeing_bars"] == 1
    assert len(result["first_mismatches"]) == 1


def test_naive_datetime_is_not_assumed_to_be_utc(pine_chart, config):
    chart = pine_chart.copy()
    chart["time"] = pd.to_datetime(chart["time"], unit="s").dt.strftime("%Y-%m-%d %H:%M:%S")
    with pytest.raises(AuditInputError, match="without a numeric UTC offset"):
        audit(chart, settings=config, warmup_bars=20, min_shared_bars=100)


def test_missing_plot_series_reports_actionable_chart_export_error(pine_chart, config):
    chart = pine_chart.drop(columns=[PINE_FIELDS["bearish_fvg_created"]])
    with pytest.raises(AuditInputError, match="Export chart data"):
        audit(chart, settings=config, warmup_bars=20, min_shared_bars=100)


def test_trade_list_csv_rejected(pine_chart, config):
    fake = pine_chart[["time", "close"]].copy()
    with pytest.raises(AuditInputError, match="Missing 'open'"):
        audit(fake, settings=config, min_shared_bars=100)


def test_reference_price_roll_mismatch_blocks_comparison(pine_chart, config):
    independent = prepare_bars(pine_chart, chart=True)
    for name in ("open", "high", "low", "close"):
        independent[name] += 0.25
    with pytest.raises(AuditInputError, match="prices do not align"):
        audit(pine_chart, settings=config, reference_bars=independent,
              warmup_bars=20, min_shared_bars=100)


def test_reference_identical_price_series_valid(pine_chart, config):
    independent = prepare_bars(pine_chart, chart=True)
    result = audit(pine_chart, settings=config, reference_bars=independent,
                   warmup_bars=20, min_shared_bars=100)
    assert result["status"] == "raw_events_match"
    assert result["price_source"] == "independent_ohlc_checked"


def test_duplicate_timestamps_rejected(pine_chart, config):
    chart = pine_chart.copy()
    chart.loc[11, "time"] = chart.loc[10, "time"]
    with pytest.raises(AuditInputError, match="Duplicate 1-minute"):
        audit(chart, settings=config, min_shared_bars=100)


def test_warmup_requires_sufficient_intersection(pine_chart, config):
    with pytest.raises(AuditInputError, match="require at least"):
        audit(pine_chart, settings=config, warmup_bars=90, min_shared_bars=100)
