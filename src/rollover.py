from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}
PRICE_COLUMNS = ("open", "high", "low", "close")


class RolloverError(RuntimeError):
    """Raised when contract rollover data cannot be stitched safely."""


@dataclass(frozen=True)
class ContractWindow:
    """One contract's inclusive-start / exclusive-end research window."""

    contract: str
    start: Any | None = None
    end: Any | None = None


def _as_utc_timestamp(value: Any, *, field_name: str) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise RolloverError(f"{field_name} must be timezone-aware.")
    return timestamp.tz_convert("UTC")


def _parse_timestamp_series(series: pd.Series) -> pd.Series:
    try:
        parsed = pd.to_datetime(series, errors="raise", utc=False)
    except Exception as exc:
        raise RolloverError("Could not parse contract timestamps.") from exc

    if isinstance(parsed.dtype, pd.DatetimeTZDtype):
        return parsed.dt.tz_convert("UTC")

    if len(parsed) and all(getattr(value, "tzinfo", None) is not None for value in parsed):
        return pd.to_datetime(series, errors="raise", utc=True)

    raise RolloverError("Contract timestamps must be timezone-aware.")


def prepare_contract_frame(
    df: pd.DataFrame,
    *,
    expected_contract: str | None = None,
) -> pd.DataFrame:
    """Validate one raw contract frame without adjusting its prices."""

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise RolloverError(f"Missing required contract columns: {sorted(missing)}")
    if df.empty:
        raise RolloverError("Cannot stitch an empty contract dataframe.")

    result = df.copy()
    result["timestamp"] = _parse_timestamp_series(result["timestamp"])

    for column in [*PRICE_COLUMNS, "volume"]:
        try:
            result[column] = pd.to_numeric(result[column], errors="raise")
        except Exception as exc:
            raise RolloverError(f"Column {column!r} must be numeric.") from exc

    invalid_high = result["high"] < result[["open", "close", "low"]].max(axis=1)
    invalid_low = result["low"] > result[["open", "close", "high"]].min(axis=1)
    if invalid_high.any() or invalid_low.any():
        raise RolloverError("Invalid OHLC relationships in contract data.")
    if (result[list(PRICE_COLUMNS)] <= 0).any().any():
        raise RolloverError("Contract data contains zero/negative prices.")
    if (result["volume"] < 0).any():
        raise RolloverError("Contract data contains negative volume.")

    result = result.sort_values("timestamp", kind="stable").reset_index(drop=True)
    if result["timestamp"].duplicated().any():
        raise RolloverError("Duplicate timestamps exist inside a contract file.")

    if expected_contract is not None:
        expected = expected_contract.upper().strip()
        if not expected:
            raise RolloverError("Contract name cannot be blank.")

        if "contract" in result.columns:
            existing = result["contract"].dropna().astype(str).str.upper().str.strip()
            if not existing.empty and not existing.eq(expected).all():
                found = sorted(existing.unique().tolist())
                raise RolloverError(
                    f"Contract file does not match expected contract {expected!r}; found {found}."
                )
        result["contract"] = expected

    if "contract" not in result.columns:
        raise RolloverError("Contract data must include a contract label.")

    return result


def load_contract_csv(
    filepath: str | Path,
    *,
    expected_contract: str | None = None,
) -> pd.DataFrame:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise RolloverError(f"Not a file: {path}")
    try:
        raw = pd.read_csv(path)
    except Exception as exc:
        raise RolloverError(f"Could not read contract CSV: {path}") from exc
    return prepare_contract_frame(raw, expected_contract=expected_contract)


def validate_contract_windows(windows: Sequence[ContractWindow]) -> list[ContractWindow]:
    if not windows:
        raise RolloverError("At least one contract window is required.")

    normalized: list[ContractWindow] = []
    seen_contracts: set[str] = set()

    for index, window in enumerate(windows):
        contract = str(window.contract).upper().strip()
        if not contract:
            raise RolloverError("Contract window has a blank contract name.")
        if contract in seen_contracts:
            raise RolloverError(f"Contract {contract!r} appears more than once in the schedule.")
        seen_contracts.add(contract)

        start = None if window.start is None else _as_utc_timestamp(
            window.start, field_name=f"{contract}.start"
        )
        end = None if window.end is None else _as_utc_timestamp(
            window.end, field_name=f"{contract}.end"
        )

        if start is not None and end is not None and start >= end:
            raise RolloverError(f"Contract {contract!r} has start >= end.")
        if index > 0 and start is None:
            raise RolloverError("Only the first contract window may have no start.")
        if index < len(windows) - 1 and end is None:
            raise RolloverError("Only the final contract window may have no end.")

        normalized.append(ContractWindow(contract=contract, start=start, end=end))

    for previous, current in zip(normalized, normalized[1:]):
        if previous.end is None or current.start is None:
            raise RolloverError("Adjacent contract windows require explicit rollover boundaries.")
        if previous.end > current.start:
            raise RolloverError(
                f"Contract windows overlap: {previous.contract} ends at {previous.end}, "
                f"but {current.contract} starts at {current.start}."
            )
        if previous.end < current.start:
            raise RolloverError(
                f"Contract windows contain an uncovered schedule gap: {previous.end} -> {current.start}."
            )

    return normalized


def stitch_contract_frames(
    frames: Mapping[str, pd.DataFrame],
    windows: Sequence[ContractWindow],
) -> pd.DataFrame:
    """Create a non-adjusted continuous research series from explicit windows.

    Each rollover timestamp belongs to the NEW contract because starts are inclusive
    and ends are exclusive. Raw OHLC prices are never shifted/back-adjusted.
    """

    schedule = validate_contract_windows(windows)
    normalized_frames = {str(key).upper().strip(): value for key, value in frames.items()}
    pieces: list[pd.DataFrame] = []

    for segment_id, window in enumerate(schedule):
        if window.contract not in normalized_frames:
            raise RolloverError(f"Missing dataframe for contract {window.contract!r}.")

        frame = prepare_contract_frame(
            normalized_frames[window.contract],
            expected_contract=window.contract,
        )

        mask = pd.Series(True, index=frame.index)
        if window.start is not None:
            mask &= frame["timestamp"] >= window.start
        if window.end is not None:
            mask &= frame["timestamp"] < window.end

        piece = frame.loc[mask].copy()
        if piece.empty:
            raise RolloverError(
                f"Contract {window.contract!r} has no bars inside its assigned rollover window."
            )

        piece["rollover_segment"] = segment_id
        piece["rollover_boundary"] = False
        piece["rollover_from_contract"] = pd.NA
        piece["rollover_to_contract"] = pd.NA

        if segment_id > 0:
            first_index = piece.index[0]
            piece.loc[first_index, "rollover_boundary"] = True
            piece.loc[first_index, "rollover_from_contract"] = schedule[segment_id - 1].contract
            piece.loc[first_index, "rollover_to_contract"] = window.contract

        pieces.append(piece)

    result = pd.concat(pieces, ignore_index=True)
    result = result.sort_values("timestamp", kind="stable").reset_index(drop=True)

    if result["timestamp"].duplicated().any():
        duplicates = result.loc[result["timestamp"].duplicated(keep=False), "timestamp"]
        raise RolloverError(
            f"Duplicate timestamps exist after stitching: {duplicates.head().tolist()}"
        )

    contract_changes = result["contract"].astype(str).ne(result["contract"].astype(str).shift(1))
    expected_boundaries = contract_changes & result.index.to_series().ne(0)
    actual_boundaries = result["rollover_boundary"].fillna(False).astype(bool)
    if not expected_boundaries.equals(actual_boundaries):
        raise RolloverError("Contract changes and rollover boundary markers are inconsistent.")

    return result


def split_rollover_segments(df: pd.DataFrame) -> list[pd.DataFrame]:
    """Split a stitched dataset so downstream indicators never bridge a rollover."""

    if "rollover_segment" not in df.columns or "contract" not in df.columns:
        raise RolloverError(
            "Stitched data must include 'rollover_segment' and 'contract' columns."
        )

    result: list[pd.DataFrame] = []
    for segment_id, group in df.groupby("rollover_segment", sort=True):
        segment = group.sort_values("timestamp", kind="stable").copy().reset_index(drop=True)
        contracts = segment["contract"].dropna().astype(str).unique()
        if len(contracts) != 1:
            raise RolloverError(
                f"Rollover segment {segment_id!r} contains multiple contracts: {contracts.tolist()}"
            )
        result.append(segment)
    return result


def save_stitched_csv(df: pd.DataFrame, filepath: str | Path) -> Path:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    result = df.copy()
    result["timestamp"] = _parse_timestamp_series(result["timestamp"]).dt.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    result.to_csv(path, index=False)
    return path
