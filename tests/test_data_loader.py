from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data_loader import (
    DataLoaderError,
    DatasetMetadata,
    MissingColumnError,
    TimestampParseError,
    basic_sanity_checks,
    convert_numeric_columns,
    dataset_summary,
    load_csv,
    normalize_column_name,
    parse_timestamp_column,
    save_parquet,
    standardize_column_names,
    validate_required_columns,
)


@pytest.fixture
def valid_raw_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date Time": [
                "2026-08-10 09:30:00",
                "2026-08-10 09:31:00",
                "2026-08-10 09:32:00",
            ],
            "Open": [25000.00, 25001.00, 25002.00],
            "High": [25003.00, 25004.00, 25005.00],
            "Low": [24999.00, 25000.00, 25001.00],
            "Close": [25001.00, 25002.00, 25004.00],
            "Volume": [1000, 1100, 1200],
        }
    )


@pytest.fixture
def canonical_dataframe() -> pd.DataFrame:
    timestamps = pd.to_datetime(
        [
            "2026-08-10 13:30:00+00:00",
            "2026-08-10 13:31:00+00:00",
            "2026-08-10 13:32:00+00:00",
        ],
        utc=True,
    )

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "timestamp_et": timestamps.tz_convert("America/New_York"),
            "open": [25000.00, 25001.00, 25002.00],
            "high": [25003.00, 25004.00, 25005.00],
            "low": [24999.00, 25000.00, 25001.00],
            "close": [25001.00, 25002.00, 25004.00],
            "volume": [1000, 1100, 1200],
        }
    )


def test_normalize_column_name():
    assert normalize_column_name(" Date Time ") == "date_time"
    assert normalize_column_name("OPEN") == "open"
    assert normalize_column_name("Trade-Volume") == "trade_volume"


def test_standardize_column_names(valid_raw_dataframe):
    result = standardize_column_names(valid_raw_dataframe)
    assert "timestamp" in result.columns
    assert "open" in result.columns
    assert "high" in result.columns
    assert "low" in result.columns
    assert "close" in result.columns
    assert "volume" in result.columns


def test_unknown_columns_are_preserved(valid_raw_dataframe):
    df = valid_raw_dataframe.copy()
    df["Extra Field"] = ["a", "b", "c"]
    result = standardize_column_names(df)
    assert "Extra Field" in result.columns


def test_validate_required_columns_passes(canonical_dataframe):
    validate_required_columns(canonical_dataframe)


def test_validate_required_columns_fails_when_close_missing(canonical_dataframe):
    df = canonical_dataframe.drop(columns=["close"])
    with pytest.raises(MissingColumnError):
        validate_required_columns(df)


def test_validate_required_columns_fails_when_volume_missing(canonical_dataframe):
    df = canonical_dataframe.drop(columns=["volume"])
    with pytest.raises(MissingColumnError):
        validate_required_columns(df)


def test_naive_timestamp_requires_timezone(valid_raw_dataframe):
    df = standardize_column_names(valid_raw_dataframe)
    with pytest.raises(TimestampParseError):
        parse_timestamp_column(df, source_timezone=None)


def test_naive_timestamp_localizes_to_new_york(valid_raw_dataframe):
    df = standardize_column_names(valid_raw_dataframe)
    result = parse_timestamp_column(df, source_timezone="America/New_York")

    assert str(result["timestamp"].dt.tz) == "UTC"
    assert str(result["timestamp_et"].dt.tz) == "America/New_York"

    first_et = result["timestamp_et"].iloc[0]
    assert first_et.hour == 9
    assert first_et.minute == 30


def test_utc_timestamp_converts_to_et():
    df = pd.DataFrame(
        {
            "timestamp": ["2026-08-10 13:30:00+00:00"],
            "open": [25000],
            "high": [25001],
            "low": [24999],
            "close": [25000.5],
            "volume": [1000],
        }
    )

    result = parse_timestamp_column(df, source_timezone=None)
    et = result["timestamp_et"].iloc[0]
    assert et.hour == 9
    assert et.minute == 30


def test_invalid_timestamp_raises():
    df = pd.DataFrame({"timestamp": ["definitely-not-a-date"]})
    with pytest.raises(TimestampParseError):
        parse_timestamp_column(df, source_timezone="UTC")


def test_numeric_strings_are_converted():
    df = pd.DataFrame(
        {
            "open": ["25000.25"],
            "high": ["25001.00"],
            "low": ["24999.50"],
            "close": ["25000.75"],
            "volume": ["1234"],
        }
    )

    result = convert_numeric_columns(df)
    assert pd.api.types.is_numeric_dtype(result["open"])
    assert pd.api.types.is_numeric_dtype(result["volume"])


def test_invalid_numeric_value_raises():
    df = pd.DataFrame(
        {
            "open": ["bad"],
            "high": ["25001"],
            "low": ["24999"],
            "close": ["25000"],
            "volume": ["100"],
        }
    )

    with pytest.raises(DataLoaderError):
        convert_numeric_columns(df)


def test_valid_dataframe_passes_sanity_checks(canonical_dataframe):
    basic_sanity_checks(canonical_dataframe)


def test_negative_price_fails(canonical_dataframe):
    df = canonical_dataframe.copy()
    df.loc[0, "low"] = -1
    with pytest.raises(DataLoaderError):
        basic_sanity_checks(df)


def test_zero_price_fails(canonical_dataframe):
    df = canonical_dataframe.copy()
    df.loc[0, "open"] = 0
    with pytest.raises(DataLoaderError):
        basic_sanity_checks(df)


def test_negative_volume_fails(canonical_dataframe):
    df = canonical_dataframe.copy()
    df.loc[0, "volume"] = -100
    with pytest.raises(DataLoaderError):
        basic_sanity_checks(df)


def test_invalid_high_fails(canonical_dataframe):
    df = canonical_dataframe.copy()
    df.loc[0, "high"] = 24990
    with pytest.raises(DataLoaderError):
        basic_sanity_checks(df)


def test_invalid_low_fails(canonical_dataframe):
    df = canonical_dataframe.copy()
    df.loc[0, "low"] = 25010
    with pytest.raises(DataLoaderError):
        basic_sanity_checks(df)


def test_load_csv_end_to_end(tmp_path, valid_raw_dataframe):
    csv_path = tmp_path / "sample.csv"
    valid_raw_dataframe.to_csv(csv_path, index=False)

    metadata = DatasetMetadata(
        source="LSE",
        symbol="NQ",
        contract="NQU26",
        source_timezone="America/New_York",
        filename=csv_path.name,
    )

    result = load_csv(csv_path, metadata=metadata)

    assert len(result) == 3
    assert result["source"].iloc[0] == "LSE"
    assert result["symbol"].iloc[0] == "NQ"
    assert result["contract"].iloc[0] == "NQU26"
    assert str(result["timestamp"].dt.tz) == "UTC"
    assert str(result["timestamp_et"].dt.tz) == "America/New_York"


def test_load_csv_sorts_timestamps(tmp_path):
    raw = pd.DataFrame(
        {
            "timestamp": [
                "2026-08-10 09:32:00",
                "2026-08-10 09:30:00",
                "2026-08-10 09:31:00",
            ],
            "open": [25002, 25000, 25001],
            "high": [25003, 25001, 25002],
            "low": [25001, 24999, 25000],
            "close": [25002, 25000, 25001],
            "volume": [100, 100, 100],
        }
    )

    csv_path = tmp_path / "unsorted.csv"
    raw.to_csv(csv_path, index=False)

    metadata = DatasetMetadata(
        source="LSE",
        symbol="NQ",
        contract=None,
        source_timezone="America/New_York",
    )

    result = load_csv(csv_path, metadata=metadata)
    assert result["timestamp"].is_monotonic_increasing


def test_save_parquet(tmp_path, canonical_dataframe):
    output = tmp_path / "normalized" / "sample.parquet"
    returned_path = save_parquet(canonical_dataframe, output)

    assert returned_path.exists()

    reloaded = pd.read_parquet(returned_path)
    assert len(reloaded) == len(canonical_dataframe)
    assert {
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    }.issubset(reloaded.columns)


def test_dataset_summary(canonical_dataframe):
    df = canonical_dataframe.copy()
    df["source"] = "LSE"
    df["symbol"] = "NQ"
    df["contract"] = "NQU26"

    summary = dataset_summary(df)

    assert summary["rows"] == 3
    assert summary["source"] == "LSE"
    assert summary["symbol"] == "NQ"
    assert summary["contract"] == "NQU26"
    assert summary["min_price"] == 24999.0
    assert summary["max_price"] == 25005.0
    assert summary["total_volume"] == 3300.0
