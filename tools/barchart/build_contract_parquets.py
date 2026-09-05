from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, time, timezone
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "source",
    "symbol",
    "contract",
}
VALUE_COLUMNS = ["open", "high", "low", "close", "volume", "source", "symbol", "contract"]
CHICAGO_TZ = "America/Chicago"
SESSION_OPEN_LOCAL = time(17, 0)


class ContractBuildError(RuntimeError):
    """Raised when normalized Barchart chunks cannot be merged safely."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Merge normalized Barchart chunk Parquets into one audited Parquet per futures contract. "
            "Raw Barchart CSVs are never modified."
        )
    )
    parser.add_argument("--manifest", type=Path, default=Path("manifest.csv"))
    parser.add_argument("--input-dir", type=Path, default=Path("normalized-barchart"))
    parser.add_argument("--output-dir", type=Path, default=Path("contract-parquets"))
    parser.add_argument("--audit-output", type=Path, default=Path("contract_parquets_audit.json"))
    return parser.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_manifest(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    manifest = pd.read_csv(path)
    required = {"contract", "filename", "start_date", "end_date"}
    missing = required - set(manifest.columns)
    if missing:
        raise ContractBuildError(f"Manifest missing required columns: {sorted(missing)}")
    if manifest.empty:
        raise ContractBuildError("Manifest is empty.")

    manifest["contract"] = manifest["contract"].astype(str).str.upper().str.strip()
    if manifest["contract"].eq("").any():
        raise ContractBuildError("Manifest contains a blank contract value.")

    for column in ["start_date", "end_date"]:
        parsed = pd.to_datetime(manifest[column], errors="coerce")
        if parsed.isna().any():
            raise ContractBuildError(f"Manifest contains invalid {column} values.")
        manifest[column] = parsed.dt.date

    if (manifest["start_date"] > manifest["end_date"]).any():
        raise ContractBuildError("Manifest contains start_date after end_date.")
    return manifest


def _normalized_name(raw_filename: str) -> str:
    return f"{Path(str(raw_filename)).stem}.parquet"


def _normalize_timestamp(series: pd.Series, *, source_file: str) -> pd.Series:
    try:
        parsed = pd.to_datetime(series, errors="raise", utc=False)
    except Exception as exc:
        raise ContractBuildError(f"{source_file}: could not parse timestamp column") from exc
    if isinstance(parsed.dtype, pd.DatetimeTZDtype):
        return parsed.dt.tz_convert("UTC")
    if len(parsed) and all(getattr(value, "tzinfo", None) is not None for value in parsed):
        return pd.to_datetime(series, errors="raise", utc=True)
    raise ContractBuildError(f"{source_file}: timestamps must be timezone-aware")


def _load_chunk(path: Path, *, expected_contract: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    try:
        frame = pd.read_parquet(path)
    except Exception as exc:
        raise ContractBuildError(f"Could not read normalized Parquet: {path}") from exc
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ContractBuildError(f"{path.name}: missing required columns {sorted(missing)}")
    if frame.empty:
        raise ContractBuildError(f"{path.name}: normalized chunk is empty")

    result = frame.copy()
    result["timestamp"] = _normalize_timestamp(result["timestamp"], source_file=path.name)
    for column in ["open", "high", "low", "close", "volume"]:
        result[column] = pd.to_numeric(result[column], errors="raise")

    expected = expected_contract.upper().strip()
    contracts = result["contract"].dropna().astype(str).str.upper().str.strip()
    if contracts.empty or not contracts.eq(expected).all():
        raise ContractBuildError(f"{path.name}: contract mismatch; expected {expected!r}")
    result["contract"] = expected

    sources = result["source"].dropna().astype(str).str.upper().str.strip()
    if sources.empty or not sources.eq("BARCHART").all():
        raise ContractBuildError(f"{path.name}: expected source BARCHART")
    symbols = result["symbol"].dropna().astype(str).str.upper().str.strip()
    if symbols.empty or not symbols.eq("MNQ").all():
        raise ContractBuildError(f"{path.name}: expected symbol MNQ")

    invalid_high = result["high"] < result[["open", "close", "low"]].max(axis=1)
    invalid_low = result["low"] > result[["open", "close", "high"]].min(axis=1)
    if invalid_high.any() or invalid_low.any():
        raise ContractBuildError(f"{path.name}: invalid OHLC relationships detected")
    if (result[["open", "high", "low", "close"]] <= 0).any().any():
        raise ContractBuildError(f"{path.name}: zero/negative prices detected")
    if (result["volume"] < 0).any():
        raise ContractBuildError(f"{path.name}: negative volume detected")

    result["chunk_file"] = path.name
    return result.sort_values("timestamp", kind="stable").reset_index(drop=True)


def _trading_date_chicago(timestamps: pd.Series) -> pd.Series:
    local = timestamps.dt.tz_convert(CHICAGO_TZ)
    local_dates = pd.Series(local.dt.date, index=timestamps.index, dtype="object")
    after_open = local.dt.time >= SESSION_OPEN_LOCAL
    return local_dates.where(~after_open, local_dates + pd.to_timedelta(1, unit="D"))


def _trim_chunk_to_manifest_window(
    frame: pd.DataFrame,
    *,
    start_date,
    end_date,
    chunk_file: str,
) -> tuple[pd.DataFrame, dict]:
    """Assign rows to manifest jobs by CME trading date.

    A Barchart request can contain session bars that belong to an adjacent requested
    trading date. A manifest job is therefore allowed to own zero rows after trimming;
    this is expected for weekend/holiday edge requests and is recorded in the audit.
    """
    trading_dates = _trading_date_chicago(frame["timestamp"])
    mask = (trading_dates >= start_date) & (trading_dates <= end_date)
    trimmed = frame.loc[mask].copy().reset_index(drop=True)

    audit = {
        "rows_loaded": int(len(frame)),
        "rows_owned": int(len(trimmed)),
        "rows_trimmed_outside_manifest_window": int(len(frame) - len(trimmed)),
        "requested_start_date": str(start_date),
        "requested_end_date": str(end_date),
        "first_owned_timestamp_utc": None if trimmed.empty else trimmed["timestamp"].min().isoformat(),
        "last_owned_timestamp_utc": None if trimmed.empty else trimmed["timestamp"].max().isoformat(),
        "empty_after_ownership_trim": bool(trimmed.empty),
    }
    return trimmed, audit


def _duplicate_conflicts(frame: pd.DataFrame) -> list[str]:
    conflicts: list[str] = []
    duplicate_rows = frame.loc[frame["timestamp"].duplicated(keep=False)]
    if duplicate_rows.empty:
        return conflicts
    for timestamp, group in duplicate_rows.groupby("timestamp", sort=True):
        for column in VALUE_COLUMNS:
            values = group[column].dropna().astype(str).unique().tolist()
            if len(values) > 1:
                conflicts.append(f"{timestamp}: {column} values differ: {values[:5]}")
                break
    return conflicts


def build_contract_frame(chunks: list[pd.DataFrame], *, contract: str) -> tuple[pd.DataFrame, dict]:
    if not chunks:
        raise ContractBuildError(f"{contract}: no normalized chunks supplied")
    non_empty = [chunk for chunk in chunks if not chunk.empty]
    if not non_empty:
        raise ContractBuildError(f"{contract}: no rows remain across all manifest-owned chunks")

    combined = pd.concat(non_empty, ignore_index=True).sort_values("timestamp", kind="stable").reset_index(drop=True)
    rows_before_dedup = len(combined)
    conflicts = _duplicate_conflicts(combined)
    if conflicts:
        raise ContractBuildError(
            f"{contract}: conflicting duplicate timestamps remain after manifest ownership trim; first conflict: {conflicts[0]}"
        )

    duplicate_rows = int(combined["timestamp"].duplicated(keep="first").sum())
    combined = combined.drop_duplicates(subset=["timestamp"], keep="first").reset_index(drop=True)
    diffs = combined["timestamp"].diff().dropna()
    one_minute = int((diffs == pd.Timedelta(minutes=1)).sum())
    two_minute = int((diffs == pd.Timedelta(minutes=2)).sum())
    gaps = diffs[diffs > pd.Timedelta(minutes=2)]
    chunk_sources = sorted(combined["chunk_file"].dropna().astype(str).unique().tolist())
    combined = combined.drop(columns=["chunk_file"])

    audit = {
        "contract": contract,
        "chunks": len(chunks),
        "non_empty_chunks": len(non_empty),
        "empty_chunks": len(chunks) - len(non_empty),
        "chunk_files": chunk_sources,
        "rows_before_dedup": int(rows_before_dedup),
        "duplicate_rows_removed": duplicate_rows,
        "rows_output": int(len(combined)),
        "first_timestamp_utc": combined["timestamp"].min().isoformat(),
        "last_timestamp_utc": combined["timestamp"].max().isoformat(),
        "one_minute_intervals": one_minute,
        "two_minute_intervals": two_minute,
        "gaps_over_two_minutes": int(len(gaps)),
        "largest_gap_minutes": float(gaps.max().total_seconds() / 60.0) if not gaps.empty else 0.0,
    }
    return combined, audit


def main() -> None:
    args = parse_args()
    manifest = _load_manifest(args.manifest)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.audit_output.parent.mkdir(parents=True, exist_ok=True)
    contracts = manifest["contract"].drop_duplicates().tolist()
    file_audits: list[dict] = []
    failures: list[dict] = []

    print("\n" + "=" * 80)
    print("BUILD BARCHART CONTRACT PARQUETS")
    print("=" * 80)
    print(f"Manifest:   {args.manifest}")
    print(f"Input dir:  {args.input_dir}")
    print(f"Output dir: {args.output_dir}")
    print(f"Contracts:  {len(contracts)}")

    for index, contract in enumerate(contracts, start=1):
        jobs = manifest.loc[manifest["contract"] == contract]
        print(f"\n[{index}/{len(contracts)}] {contract} | {len(jobs)} chunk(s)")
        try:
            chunks: list[pd.DataFrame] = []
            input_files: list[dict] = []
            total_trimmed = 0
            empty_owned_chunks = 0
            for job in jobs.to_dict("records"):
                filename = job["filename"]
                chunk_path = args.input_dir / _normalized_name(filename)
                loaded = _load_chunk(chunk_path, expected_contract=contract)
                chunk, ownership_audit = _trim_chunk_to_manifest_window(
                    loaded,
                    start_date=job["start_date"],
                    end_date=job["end_date"],
                    chunk_file=chunk_path.name,
                )
                chunks.append(chunk)
                total_trimmed += ownership_audit["rows_trimmed_outside_manifest_window"]
                empty_owned_chunks += int(ownership_audit["empty_after_ownership_trim"])
                input_files.append({"file": str(chunk_path), "sha256": _sha256(chunk_path), **ownership_audit})

            contract_frame, audit = build_contract_frame(chunks, contract=contract)
            output_path = args.output_dir / f"{contract}_1m.parquet"
            contract_frame.to_parquet(output_path, index=False)
            audit["rows_trimmed_outside_manifest_windows"] = int(total_trimmed)
            audit["empty_manifest_owned_chunks"] = int(empty_owned_chunks)
            audit["output_file"] = str(output_path)
            audit["output_sha256"] = _sha256(output_path)
            audit["inputs"] = input_files
            file_audits.append(audit)

            print(f"  rows: {audit['rows_output']:,}")
            print(f"  rows trimmed outside manifest ownership: {total_trimmed:,}")
            print(f"  empty manifest-owned chunks: {empty_owned_chunks}")
            print(f"  duplicates removed after trim: {audit['duplicate_rows_removed']:,}")
            print(f"  UTC: {audit['first_timestamp_utc']} -> {audit['last_timestamp_utc']}")
            print(f"  gaps >2m: {audit['gaps_over_two_minutes']:,}")
            print(f"  output: {output_path}")
            print("  status: PASS")
        except Exception as exc:
            failures.append({"contract": contract, "error": repr(exc)})
            print(f"  status: ERROR\n  error: {exc!r}")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "BARCHART",
        "symbol": "MNQ",
        "price_adjustment": "none",
        "chunk_ownership_rule": "CME trading date in America/Chicago; session timestamps at/after 17:00 CT belong to the next calendar trading date",
        "manifest": str(args.manifest),
        "input_directory": str(args.input_dir),
        "output_directory": str(args.output_dir),
        "contracts_expected": len(contracts),
        "contracts_succeeded": len(file_audits),
        "contracts_failed": len(failures),
        "total_output_rows_across_contract_files": int(sum(item["rows_output"] for item in file_audits)),
        "total_rows_trimmed_outside_manifest_windows": int(sum(item.get("rows_trimmed_outside_manifest_windows", 0) for item in file_audits)),
        "total_duplicate_rows_removed": int(sum(item["duplicate_rows_removed"] for item in file_audits)),
        "total_empty_manifest_owned_chunks": int(sum(item.get("empty_manifest_owned_chunks", 0) for item in file_audits)),
        "contracts": file_audits,
        "failures": failures,
    }
    with args.audit_output.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    print("\n" + "=" * 80)
    print("CONTRACT PARQUET BUILD SUMMARY")
    print("=" * 80)
    print(f"Successful contracts: {len(file_audits)} / {len(contracts)}")
    print(f"Failed contracts:     {len(failures)}")
    print(f"Rows across outputs:  {report['total_output_rows_across_contract_files']:,}")
    print(f"Rows ownership-trimmed: {report['total_rows_trimmed_outside_manifest_windows']:,}")
    print(f"Empty owned chunks:   {report['total_empty_manifest_owned_chunks']}")
    print(f"Duplicates removed:   {report['total_duplicate_rows_removed']:,}")
    print(f"Audit:                {args.audit_output}")

    if failures:
        print("\nCONTRACT BUILD FAILED")
        print("Do not choose rollover boundaries or stitch the five-year series yet.")
        raise SystemExit(1)

    print("\nCONTRACT BUILD PASSED")
    print("Normalized chunk Parquets and raw Barchart CSVs were not modified.")


if __name__ == "__main__":
    main()
