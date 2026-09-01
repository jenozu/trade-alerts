from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import pandas as pd

CANONICAL_REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")
PRICE_COLUMNS = ("open", "high", "low", "close")
NUMERIC_COLUMNS = (*PRICE_COLUMNS, "volume")


class DataLoaderError(RuntimeError):
    """Base error raised when raw market data cannot be normalized safely."""


class MissingColumnError(DataLoaderError):
    """Raised when a required OHLCV column is missing."""


class TimestampParseError(DataLoaderError):
    """Raised when timestamps cannot be parsed/localized safely."""


@dataclass(frozen=True)
class DatasetMetadata:
    source: str = "LSE"
    symbol: str = "NQ"
    contract: str | None = None
    source_timezone: str | None = None
    filename: str | None = None


def normalize_column_name(name: Any) -> str:
    """Normalize a candidate field name without mutating unknown-column storage."""
    value = str(name).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


_COLUMN_ALIASES = {
    "timestamp": {
        "timestamp", "date_time", "datetime", "date_time_utc", "time", "date", "bar_time",
    },
    "open": {"open", "o", "open_price"},
    "high": {"high", "h", "high_price"},
    "low": {"low", "l", "low_price"},
    "close": {"close", "c", "last", "latest", "close_price"},
    "volume": {"volume", "vol", "v", "trade_volume", "total_volume"},
}


def standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Rename recognized LSE/OHLCV field aliases to the canonical schema.

    Unknown columns are deliberately preserved with their original names so raw
    source information is not silently discarded.
    """
    result = df.copy()
    rename: dict[Any, str] = {}
    claimed: set[str] = set()
    for original in result.columns:
        normalized = normalize_column_name(original)
        target = None
        for canonical, aliases in _COLUMN_ALIASES.items():
            if normalized in aliases:
                target = canonical
                break
        if target is not None:
            if target in claimed:
                raise DataLoaderError(
                    f"Multiple source columns map to canonical column '{target}'."
                )
            rename[original] = target
            claimed.add(target)
    return result.rename(columns=rename)



def drop_known_source_footer_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Remove explicitly recognized non-market-data footer rows.

    Barchart CSV exports append a provenance line such as:

        Downloaded from Barchart.com as of ...

    That row is metadata, not a market-data record, and must not be passed
    into timestamp parsing. No other malformed rows are silently removed.
    """
    result = df.copy()

    timestamp_source_column = None
    for column in result.columns:
        normalized = normalize_column_name(column)
        if normalized in _COLUMN_ALIASES["timestamp"]:
            timestamp_source_column = column
            break

    if timestamp_source_column is None:
        return result

    values = result[timestamp_source_column].astype("string")

    barchart_footer = values.str.startswith(
        "Downloaded from Barchart.com",
        na=False,
    )

    if barchart_footer.any():
        result = result.loc[~barchart_footer].copy()

    return result


def validate_required_columns(df: pd.DataFrame) -> None:
    missing = [column for column in CANONICAL_REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise MissingColumnError(f"Missing required market-data columns: {missing}")


def _series_has_timezone(series: pd.Series) -> bool:
    if pd.api.types.is_datetime64tz_dtype(series.dtype):
        return True
    # Object/string data can contain explicit offsets. Parse once without forcing UTC.
    try:
        parsed = pd.to_datetime(series, errors="raise", utc=False)
    except Exception:
        return False
    if isinstance(parsed.dtype, pd.DatetimeTZDtype):
        return True
    if len(parsed) == 0:
        return False
    first = parsed.iloc[0]
    return getattr(first, "tzinfo", None) is not None


def parse_timestamp_column(
    df: pd.DataFrame,
    *,
    source_timezone: str | None,
    timestamp_column: str = "timestamp",
) -> pd.DataFrame:
    """Parse timestamps, store them in UTC, and provide a New-York view.

    Naive timestamps are never guessed: a source timezone is mandatory. Explicitly
    offset/UTC timestamps may be converted without supplying source_timezone.
    """
    if timestamp_column not in df.columns:
        raise MissingColumnError(f"Missing timestamp column: {timestamp_column}")

    result = df.copy()
    raw = result[timestamp_column]
    try:
        parsed = pd.to_datetime(raw, errors="raise", utc=False)
    except Exception as exc:
        raise TimestampParseError("Could not parse one or more timestamps.") from exc

    try:
        if isinstance(parsed.dtype, pd.DatetimeTZDtype):
            utc = parsed.dt.tz_convert("UTC")
        else:
            # Mixed explicit-offset strings can come back as object dtype. If all
            # values carry tzinfo, forcing UTC is safe and deterministic.
            explicit_tz = False
            if len(parsed):
                explicit_tz = all(getattr(value, "tzinfo", None) is not None for value in parsed)
            if explicit_tz:
                utc = pd.to_datetime(raw, errors="raise", utc=True)
            else:
                if source_timezone is None:
                    raise TimestampParseError(
                        "Naive timestamps require an explicit source_timezone; "
                        "the LSE timezone must not be guessed."
                    )
                naive = pd.to_datetime(raw, errors="raise")
                localized = naive.dt.tz_localize(
                    source_timezone,
                    ambiguous="raise",
                    nonexistent="raise",
                )
                utc = localized.dt.tz_convert("UTC")
    except TimestampParseError:
        raise
    except Exception as exc:
        raise TimestampParseError(
            f"Could not localize/convert timestamps using timezone {source_timezone!r}."
        ) from exc

    result["timestamp"] = utc
    result["timestamp_et"] = result["timestamp"].dt.tz_convert("America/New_York")
    return result


def convert_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for column in NUMERIC_COLUMNS:
        if column not in result.columns:
            continue
        try:
            result[column] = pd.to_numeric(result[column], errors="raise")
        except Exception as exc:
            raise DataLoaderError(f"Column '{column}' contains non-numeric values.") from exc
    return result


def basic_sanity_checks(df: pd.DataFrame) -> None:
    validate_required_columns(df)
    if df.empty:
        raise DataLoaderError("Market dataset is empty.")

    for column in PRICE_COLUMNS:
        if not pd.api.types.is_numeric_dtype(df[column]):
            raise DataLoaderError(f"'{column}' must be numeric.")
        if df[column].isna().any():
            raise DataLoaderError(f"'{column}' contains missing values.")
        if (df[column] <= 0).any():
            raise DataLoaderError(f"'{column}' contains zero/negative prices.")

    if not pd.api.types.is_numeric_dtype(df["volume"]):
        raise DataLoaderError("'volume' must be numeric.")
    if df["volume"].isna().any():
        raise DataLoaderError("'volume' contains missing values.")
    if (df["volume"] < 0).any():
        raise DataLoaderError("'volume' contains negative values.")

    invalid_high = df["high"] < df[["open", "close", "low"]].max(axis=1)
    invalid_low = df["low"] > df[["open", "close", "high"]].min(axis=1)
    if invalid_high.any() or invalid_low.any() or (df["high"] < df["low"]).any():
        raise DataLoaderError("Invalid OHLC price relationships detected.")


def _attach_metadata(df: pd.DataFrame, metadata: DatasetMetadata | None) -> pd.DataFrame:
    result = df.copy()
    if metadata is None:
        return result
    result["source"] = metadata.source
    result["symbol"] = metadata.symbol
    result["contract"] = metadata.contract
    if metadata.filename is not None:
        result.attrs["source_filename"] = metadata.filename
    result.attrs["source_timezone"] = metadata.source_timezone
    return result


def load_csv(
    filepath: str | Path,
    *,
    metadata: DatasetMetadata | None = None,
    source_timezone: str | None = None,
) -> pd.DataFrame:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise DataLoaderError("Not a file: {path}")

    try:
        raw = pd.read_csv(path)
    except Exception as exc:
        raise DataLoaderError(f"Could not read CSV: {path}") from exc

    raw = drop_known_source_footer_rows(raw)
    result = standardize_column_names(raw)
    validate_required_columns(result)
    tz = metadata.source_timezone if metadata is not None else source_timezone
    result = parse_timestamp_column(result, source_timezone=tz)
    result = convert_numeric_columns(result)
    basic_sanity_checks(result)
    result = result.sort_values("timestamp", kind="stable").reset_index(drop=True)
    result = _attach_metadata(result, metadata)

    canonical = [
        "timestamp", "timestamp_et", "open", "high", "low", "close", "volume",
        "source", "symbol", "contract",
    ]
    ordered = [column for column in canonical if column in result.columns]
    trailing = [column for column in result.columns if column not in ordered]
    return result[ordered + trailing]


def save_parquet(df: pd.DataFrame, filepath: str | Path) -> Path:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_parquet(path, index=False)
    except ImportError as exc:
        raise DataLoaderError(
            "Saving Parquet requires pyarrow (included in requirements.txt)."
        ) from exc
    except Exception as exc:
        raise DataLoaderError(f"Could not save Parquet file: {path}") from exc
    return path


def _single_value(df: pd.DataFrame, column: str) -> Any:
    if column not in df.columns or df.empty:
        return None
    values = df[column].dropna().unique()
    if len(values) == 0:
        return None
    if len(values) == 1:
        return values[0]
    return list(values)


def dataset_summary(df: pd.DataFrame) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "rows": int(len(df)),
        "source": _single_value(df, "source"),
        "symbol": _single_value(df, "symbol"),
        "contract": _single_value(df, "contract"),
    }
    if df.empty:
        summary.update(
            {
                "start": None,
                "end": None,
                "min_price": None,
                "max_price": None,
                "total_volume": 0.0,
            }
        )
        return summary
    if "timestamp" in df.columns:
        summary["start"] = df["timestamp"].min()
        summary["end"] = df["timestamp"].max()
    summary["min_price"] = float(df["low"].min()) if "low" in df.columns else None
    summary["max_price"] = float(df["high"].max()) if "high" in df.columns else None
    summary["total_volume"] = float(df["volume"].sum()) if "volume" in df.columns else None
    return summary
