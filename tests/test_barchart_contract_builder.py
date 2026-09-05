from datetime import date

import pandas as pd
import pytest

from tools.barchart.build_contract_parquets import (
    ContractBuildError,
    _trim_chunk_to_manifest_window,
    build_contract_frame,
)


def _frame(rows, *, contract="NMH22"):
    return pd.DataFrame(
        [
            {
                "timestamp": pd.Timestamp(timestamp, tz="UTC"),
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "source": "BARCHART",
                "symbol": "MNQ",
                "contract": contract,
                "source_file": source_file,
                "chunk_file": chunk_file,
            }
            for (
                timestamp,
                open_,
                high,
                low,
                close,
                volume,
                source_file,
                chunk_file,
            ) in rows
        ]
    )


def test_manifest_ownership_assigns_prior_day_1700_ct_to_next_trading_date():
    frame = _frame(
        [
            ("2026-06-28 21:59", 100, 101, 99, 100.5, 10, "a.csv", "a.parquet"),
            ("2026-06-28 22:00", 101, 102, 100, 101.5, 11, "a.csv", "a.parquet"),
            ("2026-06-29 04:59", 102, 103, 101, 102.5, 12, "a.csv", "a.parquet"),
        ],
        contract="NMU26",
    )

    owned, audit = _trim_chunk_to_manifest_window(
        frame,
        start_date=date(2026, 6, 29),
        end_date=date(2026, 6, 29),
        chunk_file="a.parquet",
    )

    assert owned["timestamp"].tolist() == [
        pd.Timestamp("2026-06-28 22:00", tz="UTC"),
        pd.Timestamp("2026-06-29 04:59", tz="UTC"),
    ]
    assert audit["rows_loaded"] == 3
    assert audit["rows_owned"] == 2
    assert audit["rows_trimmed_outside_manifest_window"] == 1


def test_manifest_ownership_prevents_adjacent_chunk_conflict_from_overlapping_session():
    old_chunk = _frame(
        [
            ("2026-06-28 22:00", 100, 101, 99, 100.5, 10, "old.csv", "old.parquet"),
            ("2026-06-29 04:59", 100, 101, 99, 100.5, 10, "old.csv", "old.parquet"),
        ],
        contract="NMU26",
    )
    new_chunk = _frame(
        [
            ("2026-06-28 22:00", 108, 109, 107, 108.5, 12, "new.csv", "new.parquet"),
            ("2026-06-29 04:59", 108, 109, 107, 108.5, 12, "new.csv", "new.parquet"),
            ("2026-06-29 05:00", 109, 110, 108, 109.5, 13, "new.csv", "new.parquet"),
        ],
        contract="NMU26",
    )

    old_owned, _ = _trim_chunk_to_manifest_window(
        old_chunk,
        start_date=date(2026, 6, 28),
        end_date=date(2026, 6, 28),
        chunk_file="old.parquet",
    )
    new_owned, _ = _trim_chunk_to_manifest_window(
        new_chunk,
        start_date=date(2026, 6, 29),
        end_date=date(2026, 6, 29),
        chunk_file="new.parquet",
    )

    result, audit = build_contract_frame([old_owned, new_owned], contract="NMU26")

    assert not result["timestamp"].duplicated().any()
    assert pd.Timestamp("2026-06-29 04:59", tz="UTC") in result["timestamp"].tolist()
    assert audit["duplicate_rows_removed"] == 0


def test_build_contract_frame_removes_identical_chunk_overlap():
    chunk_a = _frame(
        [
            ("2022-01-03 00:00", 100, 102, 99, 101, 10, "a.csv", "a.parquet"),
            ("2022-01-03 00:01", 101, 103, 100, 102, 11, "a.csv", "a.parquet"),
        ]
    )
    chunk_b = _frame(
        [
            ("2022-01-03 00:01", 101, 103, 100, 102, 11, "b.csv", "b.parquet"),
            ("2022-01-03 00:02", 102, 104, 101, 103, 12, "b.csv", "b.parquet"),
        ]
    )

    result, audit = build_contract_frame([chunk_a, chunk_b], contract="NMH22")

    assert result["timestamp"].tolist() == [
        pd.Timestamp("2022-01-03 00:00", tz="UTC"),
        pd.Timestamp("2022-01-03 00:01", tz="UTC"),
        pd.Timestamp("2022-01-03 00:02", tz="UTC"),
    ]
    assert audit["rows_before_dedup"] == 4
    assert audit["duplicate_rows_removed"] == 1
    assert audit["rows_output"] == 3
    assert audit["one_minute_intervals"] == 2
    assert audit["gaps_over_two_minutes"] == 0
    assert "chunk_file" not in result.columns


def test_build_contract_frame_rejects_conflicting_duplicate_timestamp():
    chunk_a = _frame(
        [
            ("2022-01-03 00:00", 100, 102, 99, 101, 10, "a.csv", "a.parquet"),
        ]
    )
    chunk_b = _frame(
        [
            ("2022-01-03 00:00", 100, 102, 99, 101.25, 10, "b.csv", "b.parquet"),
        ]
    )

    with pytest.raises(ContractBuildError, match="conflicting duplicate timestamps"):
        build_contract_frame([chunk_a, chunk_b], contract="NMH22")


def test_build_contract_frame_reports_large_gaps_without_filling_them():
    chunk = _frame(
        [
            ("2022-01-07 21:59", 100, 101, 99, 100.5, 10, "a.csv", "a.parquet"),
            ("2022-01-09 23:00", 101, 102, 100, 101.5, 12, "a.csv", "a.parquet"),
        ]
    )

    result, audit = build_contract_frame([chunk], contract="NMH22")

    assert len(result) == 2
    assert audit["gaps_over_two_minutes"] == 1
    assert audit["largest_gap_minutes"] > 2
