"""Regression tests for shared directional confluence preprocessing."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from confluence_zones import (
    directional_confluence_strength,
    directional_confluence_strength_prepared,
    prepare_directional_confluence,
)
from scorer import enrich_scores, score_setup


@pytest.fixture
def config():
    return yaml.safe_load(Path("config/strategy.yaml").read_text())


@pytest.mark.parametrize("seed", [0, 12, 42])
def test_prepared_matches_public_directional_confluence(config, seed):
    rng = np.random.default_rng(seed)
    row = pd.Series({
        "close": 20000 + float(rng.normal(0, 6)),
        "pdh": 20000 + float(rng.normal(0, 6)),
        "pdl": 20000 + float(rng.normal(0, 6)),
        "vwap": 20000 + float(rng.normal(0, 6)),
        "active_external_swing_low": 20000 + float(rng.normal(0, 6)),
        "active_external_swing_high": 20000 + float(rng.normal(0, 6)),
        "test_equal_cluster_level": 20000 + float(rng.normal(0, 6)),
        "internal_equilibrium": 20000 + float(rng.normal(0, 6)),
    })
    prepared = prepare_directional_confluence(row, config)
    for direction in ("long", "short"):
        assert directional_confluence_strength_prepared(
            prepared, direction=direction
        ) == directional_confluence_strength(row, config, direction=direction)


def test_missing_close_and_empty_levels(config):
    for row in (pd.Series({"close": np.nan}), pd.Series({"close": 20000.0})):
        prepared = prepare_directional_confluence(row, config)
        for direction in ("long", "short"):
            assert directional_confluence_strength_prepared(
                prepared, direction=direction
            ) == directional_confluence_strength(row, config, direction=direction)


def test_scoring_prepared_matches_standalone(config):
    timestamp = pd.date_range("2026-09-01 13:30", periods=5, freq="min", tz="UTC")
    rows = pd.DataFrame({
        "timestamp": timestamp,
        "open": [19999.] * 5,
        "high": [20001.] * 5,
        "low": [19998.] * 5,
        "close": [20000., 20001., 19999., 20000., 20001.],
        "pdh": [20002.] * 5,
        "pdl": [19998.] * 5,
        "vwap": [20000.] * 5,
        "active_external_swing_low": [19997.] * 5,
        "new_entry_allowed": [True] * 5,
        "data_healthy": [True] * 5,
    })
    batch = enrich_scores(rows, config)
    for i, row in rows.iterrows():
        for direction in ("long", "short"):
            direct = score_setup(row, direction=direction, config=config)
            assert batch.at[i, f"{direction}_raw_score"] == direct.raw_score
            assert batch.at[i, f"{direction}_score_band"] == direct.score_band
            assert bool(batch.at[i, f"{direction}_disabled"]) == direct.disabled
            for component, value in direct.contributions.items():
                assert batch.at[i, f"{direction}_score_{component}"] == value
