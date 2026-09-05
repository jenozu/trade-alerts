from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

BASE_DIR = Path.home() / "Documents" / "barchart-downloader"
RAW_DIR = Path.home() / "Downloads" / "barchart-history"
MANIFEST_PATH = BASE_DIR / "manifest.csv"
OUTPUT_DIR = BASE_DIR / "normalized-barchart"
AUDIT_PATH = BASE_DIR / "normalized_barchart_audit.json"
SOURCE_TIMEZONE = "America/Chicago"


def load_manifest() -> pd.DataFrame:
    df = pd.read_csv(MANIFEST_PATH)
    required = {"contract", "start_date", "end_date", "filename", "status"}
    missing = required - set(df.columns)
    if missing:
        raise RuntimeError(f"Manifest missing required columns: {sorted(missing)}")
    return df


def read_raw_file(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"Time", "Open", "High", "Low", "Latest", "Volume"}
    missing = required - set(df.columns)
    if missing:
        raise RuntimeError(f"{path.name}: missing required columns {sorted(missing)}")
    return df


def clean_frame(
    df: pd.DataFrame,
    *,
    contract: str,
    source_file: str,
) -> tuple[pd.DataFrame, dict]:
    original_rows = len(df)
    parsed_time = pd.to_datetime(df["Time"], errors="coerce")
    data_mask = parsed_time.notna()
    footer_rows_removed = int((~data_mask).sum())

    df = df.loc[data_mask].copy()
    parsed_time = parsed_time.loc[data_mask]

    localized = parsed_time.dt.tz_localize(
        SOURCE_TIMEZONE,
        ambiguous="infer",
        nonexistent="shift_forward",
    )
    timestamp_utc = localized.dt.tz_convert("UTC")

    numeric_cols = ["Open", "High", "Low", "Latest", "Volume"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    before_numeric_drop = len(df)
    df = df.dropna(subset=numeric_cols).copy()
    numeric_rows_removed = before_numeric_drop - len(df)

    result = pd.DataFrame(
        {
            "timestamp": timestamp_utc.loc[df.index],
            "open": df["Open"].astype(float),
            "high": df["High"].astype(float),
            "low": df["Low"].astype(float),
            "close": df["Latest"].astype(float),
            "volume": df["Volume"].astype(float),
            "source": "BARCHART",
            "symbol": "MNQ",
            "contract": contract,
            "source_file": source_file,
        }
    )

    result = result.sort_values("timestamp").reset_index(drop=True)
    duplicate_count = int(result["timestamp"].duplicated().sum())
    if duplicate_count:
        result = result.drop_duplicates(subset=["timestamp"], keep="first").reset_index(drop=True)

    invalid_ohlc = (
        (result["high"] < result["low"])
        | (result["high"] < result[["open", "close"]].max(axis=1))
        | (result["low"] > result[["open", "close"]].min(axis=1))
    )
    invalid_ohlc_count = int(invalid_ohlc.sum())
    if invalid_ohlc_count:
        raise RuntimeError(f"{source_file}: {invalid_ohlc_count} invalid OHLC rows found")

    negative_volume_count = int((result["volume"] < 0).sum())
    if negative_volume_count:
        raise RuntimeError(f"{source_file}: negative volume rows found")

    audit = {
        "source_file": source_file,
        "contract": contract,
        "original_rows": original_rows,
        "footer_rows_removed": footer_rows_removed,
        "numeric_rows_removed": int(numeric_rows_removed),
        "duplicates_removed": duplicate_count,
        "normalized_rows": len(result),
        "first_timestamp_utc": result["timestamp"].min().isoformat() if len(result) else None,
        "last_timestamp_utc": result["timestamp"].max().isoformat() if len(result) else None,
        "invalid_ohlc_rows": invalid_ohlc_count,
        "negative_volume_rows": negative_volume_count,
    }
    return result, audit


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    print("NORMALIZE BARCHART HISTORY")
    print("Manifest jobs:", len(manifest))
    all_audits = []
    failures = []

    for index, row in manifest.iterrows():
        contract = str(row["contract"]).strip()
        filename = str(row["filename"]).strip()
        raw_path = RAW_DIR / filename
        output_path = OUTPUT_DIR / f"{Path(filename).stem}.parquet"

        print(f"[{index + 1}/{len(manifest)}] {contract} | {filename}")
        try:
            raw = read_raw_file(raw_path)
            normalized, audit = clean_frame(
                raw,
                contract=contract,
                source_file=filename,
            )
            normalized.to_parquet(output_path, index=False)
            all_audits.append(audit)
            print("  rows:", f"{audit['normalized_rows']:,}")
            print("  status: PASS")
        except Exception as exc:
            failures.append(
                {"contract": contract, "filename": filename, "error": repr(exc)}
            )
            print("  status: ERROR")
            print("  error:", repr(exc))

    report = {
        "source_timezone": SOURCE_TIMEZONE,
        "manifest_jobs": len(manifest),
        "successful_files": len(all_audits),
        "failed_files": len(failures),
        "total_normalized_rows": sum(x["normalized_rows"] for x in all_audits),
        "total_footer_rows_removed": sum(x["footer_rows_removed"] for x in all_audits),
        "total_numeric_rows_removed": sum(x["numeric_rows_removed"] for x in all_audits),
        "total_duplicates_removed": sum(x["duplicates_removed"] for x in all_audits),
        "files": all_audits,
        "failures": failures,
    }
    AUDIT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== NORMALIZATION SUMMARY ===")
    print("Successful files:", len(all_audits), "/", len(manifest))
    print("Failed files:", len(failures))
    print("Normalized rows:", f"{report['total_normalized_rows']:,}")
    print("Footer rows removed:", report["total_footer_rows_removed"])
    print("Numeric rows removed:", report["total_numeric_rows_removed"])
    print("Duplicates removed:", report["total_duplicates_removed"])
    print("Audit:", AUDIT_PATH)

    if failures:
        print("NORMALIZATION FAILED")
        raise SystemExit(1)

    print("NORMALIZATION PASSED")
    print("Original Barchart CSV files were not modified.")


if __name__ == "__main__":
    main()
