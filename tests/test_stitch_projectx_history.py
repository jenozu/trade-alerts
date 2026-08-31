from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from rollover import RolloverError
from stitch_projectx_history import (
    build_contract_windows,
    create_stitched_dataset,
    parse_contract_spec,
    parse_rollover_timestamp,
)


def _write_contract_csv(
    tmp_path: Path,
    contract: str,
    timestamps: list[str],
    prices: list[float],
    *,
    symbol: str = "MNQ",
) -> Path:
    frame = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": prices,
            "high": [value + 1.0 for value in prices],
            "low": [value - 1.0 for value in prices],
            "close": [value + 0.25 for value in prices],
            "volume": [100] * len(prices),
            "source": ["PROJECTX"] * len(prices),
            "symbol": [symbol] * len(prices),
            "contract": [contract] * len(prices),
        }
    )
    path = tmp_path / f"{contract}_1m.csv"
    frame.to_csv(path, index=False)
    return path


def test_parse_contract_spec_accepts_contract_equals_path():
    contract, path = parse_contract_spec("mnqm6=data/raw/projectx/MNQM6_1m.csv")
    assert contract == "MNQM6"
    assert path == Path("data/raw/projectx/MNQM6_1m.csv")


def test_parse_contract_spec_rejects_missing_equals():
    with pytest.raises(Exception):
        parse_contract_spec("MNQM6")


def test_rollover_timestamp_must_be_timezone_aware():
    with pytest.raises(Exception):
        parse_rollover_timestamp("2026-06-12 18:00:00")

    parsed = parse_rollover_timestamp("2026-06-12T22:00:00Z")
    assert str(parsed.tz) == "UTC"


def test_build_windows_assigns_old_end_exclusive_and_new_start_inclusive():
    boundary = parse_rollover_timestamp("2026-06-12T22:00:00Z")
    windows = build_contract_windows(["MNQM6", "MNQU6"], [boundary])

    assert windows[0].contract == "MNQM6"
    assert windows[0].start is None
    assert windows[0].end == boundary
    assert windows[1].contract == "MNQU6"
    assert windows[1].start == boundary
    assert windows[1].end is None


def test_build_windows_requires_exactly_n_minus_one_rollovers():
    with pytest.raises(RolloverError):
        build_contract_windows(["MNQH6", "MNQM6", "MNQU6"], [])


def test_build_windows_requires_strictly_increasing_rollovers():
    r1 = parse_rollover_timestamp("2026-03-13T22:00:00Z")
    r2 = parse_rollover_timestamp("2026-03-12T22:00:00Z")
    with pytest.raises(RolloverError):
        build_contract_windows(["MNQH6", "MNQM6", "MNQU6"], [r1, r2])


def test_create_stitched_dataset_preserves_raw_prices_and_contract_identity(tmp_path):
    boundary = parse_rollover_timestamp("2026-06-12T22:00:00Z")
    old_path = _write_contract_csv(
        tmp_path,
        "MNQM6",
        ["2026-06-12T21:58:00Z", "2026-06-12T21:59:00Z", "2026-06-12T22:00:00Z"],
        [19000.0, 19001.0, 19002.0],
    )
    new_path = _write_contract_csv(
        tmp_path,
        "MNQU6",
        ["2026-06-12T21:59:00Z", "2026-06-12T22:00:00Z", "2026-06-12T22:01:00Z"],
        [19100.0, 19101.0, 19102.0],
    )

    stitched, audit = create_stitched_dataset(
        [("MNQM6", old_path), ("MNQU6", new_path)],
        [boundary],
        symbol="MNQ",
    )

    assert stitched["contract"].tolist() == ["MNQM6", "MNQM6", "MNQU6", "MNQU6"]
    assert stitched["open"].tolist() == [19000.0, 19001.0, 19101.0, 19102.0]
    assert stitched["rollover_boundary"].tolist() == [False, False, True, False]
    assert audit["price_adjustment"] == "none"
    assert audit["rollover_boundaries"] == 1


def test_create_stitched_dataset_rejects_symbol_mismatch(tmp_path):
    boundary = parse_rollover_timestamp("2026-06-12T22:00:00Z")
    old_path = _write_contract_csv(
        tmp_path,
        "MNQM6",
        ["2026-06-12T21:59:00Z"],
        [19000.0],
        symbol="MNQ",
    )
    new_path = _write_contract_csv(
        tmp_path,
        "MNQU6",
        ["2026-06-12T22:00:00Z"],
        [19100.0],
        symbol="NQ",
    )

    with pytest.raises(RolloverError):
        create_stitched_dataset(
            [("MNQM6", old_path), ("MNQU6", new_path)],
            [boundary],
            symbol="MNQ",
        )


def test_create_stitched_dataset_supports_three_contracts(tmp_path):
    r1 = parse_rollover_timestamp("2026-03-13T22:00:00Z")
    r2 = parse_rollover_timestamp("2026-06-12T22:00:00Z")

    h_path = _write_contract_csv(
        tmp_path,
        "MNQH6",
        ["2026-03-13T21:59:00Z"],
        [18000.0],
    )
    m_path = _write_contract_csv(
        tmp_path,
        "MNQM6",
        ["2026-03-13T22:00:00Z", "2026-06-12T21:59:00Z"],
        [18500.0, 18900.0],
    )
    u_path = _write_contract_csv(
        tmp_path,
        "MNQU6",
        ["2026-06-12T22:00:00Z"],
        [19100.0],
    )

    stitched, audit = create_stitched_dataset(
        [("MNQH6", h_path), ("MNQM6", m_path), ("MNQU6", u_path)],
        [r1, r2],
        symbol="MNQ",
    )

    assert stitched["contract"].tolist() == ["MNQH6", "MNQM6", "MNQM6", "MNQU6"]
    assert stitched["rollover_boundary"].sum() == 2
    assert audit["contracts_in_order"] == ["MNQH6", "MNQM6", "MNQU6"]
