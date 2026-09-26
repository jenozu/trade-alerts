"""Causal, exact output parity checks for memory-bounded score replay."""
from pathlib import Path

import pandas as pd
import pytest
import yaml

from backtest import run_backtest
from scorer import enrich_scores
from score_candidate_models import CANDIDATE_WEIGHTS
from scripts.run_r45_chunked import (
    BACKTEST_SOURCE_COLUMNS, SCORE_COLUMNS,
    replay_chunks, scored_backtest_projection,
)


def config():
    cfg = yaml.safe_load(Path("config/strategy.yaml").read_text())
    cfg["scoring"]["positive_weights"] = {
        k: float(v) for k, v in CANDIDATE_WEIGHTS["candidate_conservative"].items()
    }
    return cfg


def example_features():
    timestamps = pd.date_range("2026-09-01 13:30", periods=12, freq="min", tz="UTC")
    return pd.DataFrame({
        "timestamp": timestamps,
        "open": [19999.] * 12,
        "high": [20001.] * 12,
        "low": [19998.] * 12,
        "close": [20000., 20001., 19999., 20000.] * 3,
        "pdh": [20002.] * 12,
        "pdl": [19998.] * 12,
        "vwap": [20000.] * 12,
        "active_external_swing_low": [19997.] * 12,
        "new_entry_allowed": [True] * 12,
        "data_healthy": [True] * 12,
    })


def test_chunked_exact_score_and_trade_parity_across_boundaries():
    source = example_features()
    cfg = config()
    expected = scored_backtest_projection(enrich_scores(source, cfg))
    chunks = [source.iloc[i:i + 3].copy() for i in range(0, len(source), 3)]
    actual = replay_chunks(chunks, cfg, output_progress=False)
    pd.testing.assert_frame_equal(expected, actual, check_exact=True)
    pd.testing.assert_frame_equal(
        run_backtest(expected, cfg), run_backtest(actual, cfg),
        check_exact=True,
    )
    assert list(actual.columns) == [
        c for c in (*BACKTEST_SOURCE_COLUMNS, *SCORE_COLUMNS) if c in actual.columns
    ]


def test_chunked_rejects_unsorted_input():
    df = example_features()
    chunks = [df.iloc[4:8].copy(), df.iloc[:4].copy()]
    with pytest.raises(ValueError, match="chronological"):
        replay_chunks(chunks, config(), output_progress=False)


def test_chunked_rejects_unsorted_within_batch():
    df = example_features().iloc[:4].copy()
    df.iloc[[0, 1]] = df.iloc[[1, 0]].to_numpy()
    with pytest.raises(ValueError, match="not sorted"):
        replay_chunks([df], config(), output_progress=False)


def test_chunked_rejects_missing_timestamps():
    df = example_features().iloc[:3].copy()
    df.loc[df.index[0], "timestamp"] = pd.NaT
    with pytest.raises(ValueError, match="invalid timestamps"):
        replay_chunks([df], config(), output_progress=False)
