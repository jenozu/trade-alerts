import pandas as pd
import pytest

from tools.barchart.build_contract_parquets import ContractBuildError, build_contract_frame


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
