from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pandas as pd

BASE_DIR = Path.home() / "Documents" / "barchart-downloader"
DOWNLOAD_DIR = Path.home() / "Downloads" / "barchart-history"
MANIFEST_PATH = BASE_DIR / "manifest.csv"
AUDIT_JSON = BASE_DIR / "barchart_history_audit.json"
AUDIT_CSV = BASE_DIR / "barchart_history_audit.csv"

EXPECTED_HEADER_COLUMNS = {
    "time",
    "open",
    "high",
    "low",
    "latest",
    "change",
    "%change",
    "volume",
}
NUMERIC_COLUMNS = ["Open", "High", "Low", "Latest", "Change", "%Change", "Volume"]


def read_manifest() -> pd.DataFrame:
    df = pd.read_csv(MANIFEST_PATH)
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")
    return df


def inspect_file(row) -> dict:
    path = DOWNLOAD_DIR / row["filename"]
    result = {
        "contract": row["contract"],
        "filename": row["filename"],
        "exists": path.exists(),
        "size_bytes": None,
        "rows": None,
        "first_timestamp": None,
        "last_timestamp": None,
        "duplicate_timestamps": None,
        "bad_timestamp_rows": None,
        "null_market_rows": None,
        "ohlc_invalid_rows": None,
        "negative_volume_rows": None,
        "one_minute_intervals": None,
        "two_minute_intervals": None,
        "larger_gaps": None,
        "largest_gap_minutes": None,
        "requested_start": str(pd.Timestamp(row["start_date"]).date()),
        "requested_end": str(pd.Timestamp(row["end_date"]).date()),
        "starts_before_requested": None,
        "ends_after_requested": None,
        "header_ok": None,
        "status": "UNKNOWN",
        "problems": [],
    }

    if not path.exists():
        result["status"] = "ERROR"
        result["problems"].append("file_missing")
        return result

    result["size_bytes"] = path.stat().st_size
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        result["status"] = "ERROR"
        result["problems"].append(f"csv_read_failed:{exc}")
        return result

    result["rows"] = len(df)
    header = {str(c).strip().lower() for c in df.columns}
    result["header_ok"] = EXPECTED_HEADER_COLUMNS <= header
    if not result["header_ok"]:
        result["problems"].append("unexpected_header")

    timestamps = pd.to_datetime(df["Time"], errors="coerce")
    result["bad_timestamp_rows"] = int(timestamps.isna().sum())
    if result["bad_timestamp_rows"]:
        result["problems"].append("bad_timestamps")

    valid_ts = timestamps.dropna()
    result["first_timestamp"] = str(valid_ts.min())
    result["last_timestamp"] = str(valid_ts.max())
    result["duplicate_timestamps"] = int(valid_ts.duplicated().sum())
    if result["duplicate_timestamps"]:
        result["problems"].append("duplicate_timestamps")

    requested_start = pd.Timestamp(row["start_date"]).normalize()
    requested_end = pd.Timestamp(row["end_date"]).normalize() + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    result["starts_before_requested"] = bool(valid_ts.min() < requested_start)
    result["ends_after_requested"] = bool(valid_ts.max() > requested_end)
    if result["starts_before_requested"]:
        result["problems"].append("starts_before_requested")
    if result["ends_after_requested"]:
        result["problems"].append("ends_after_requested")

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    market_cols = [c for c in ["Open", "High", "Low", "Latest", "Volume"] if c in df.columns]
    result["null_market_rows"] = int(df[market_cols].isna().any(axis=1).sum())
    if result["null_market_rows"]:
        result["problems"].append("null_market_rows")

    invalid_ohlc = (
        (df["High"] < df["Low"])
        | (df["High"] < df[["Open", "Latest"]].max(axis=1))
        | (df["Low"] > df[["Open", "Latest"]].min(axis=1))
    )
    result["ohlc_invalid_rows"] = int(invalid_ohlc.fillna(False).sum())
    if result["ohlc_invalid_rows"]:
        result["problems"].append("invalid_ohlc")

    result["negative_volume_rows"] = int((df["Volume"] < 0).fillna(False).sum())
    if result["negative_volume_rows"]:
        result["problems"].append("negative_volume")

    diffs = valid_ts.sort_values().drop_duplicates().diff().dropna()
    result["one_minute_intervals"] = int((diffs == pd.Timedelta(minutes=1)).sum())
    result["two_minute_intervals"] = int((diffs == pd.Timedelta(minutes=2)).sum())
    larger = diffs[diffs > pd.Timedelta(minutes=2)]
    result["larger_gaps"] = len(larger)
    result["largest_gap_minutes"] = float(larger.max() / pd.Timedelta(minutes=1)) if len(larger) else 0.0

    critical = {"file_missing", "unexpected_header", "duplicate_timestamps", "invalid_ohlc", "negative_volume"}
    if critical.intersection(result["problems"]):
        result["status"] = "ERROR"
    elif result["problems"]:
        result["status"] = "WARN"
    else:
        result["status"] = "PASS"
    return result


def main() -> None:
    manifest = read_manifest()
    actual_files = list(DOWNLOAD_DIR.glob("*.csv"))
    results = [inspect_file(row) for _, row in manifest.iterrows()]
    pd.DataFrame(results).to_csv(AUDIT_CSV, index=False)
    AUDIT_JSON.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")

    counts = Counter(r["status"] for r in results)
    expected = set(manifest["filename"])
    actual = {p.name for p in actual_files}
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)

    print("=== SUMMARY ===")
    for status in ["PASS", "WARN", "ERROR", "UNKNOWN"]:
        print(f"{status:7}: {counts.get(status, 0)}")
    print("Total rows:", f"{sum((r['rows'] or 0) for r in results):,}")
    print("Total size:", f"{sum((r['size_bytes'] or 0) for r in results) / 1024 / 1024:.2f} MB")
    print("Missing expected files:", len(missing))
    print("Extra CSV files:", len(extra))
    print("1-minute intervals:", f"{sum((r['one_minute_intervals'] or 0) for r in results):,}")
    print("2-minute intervals:", f"{sum((r['two_minute_intervals'] or 0) for r in results):,}")
    print("Gaps > 2 minutes:", f"{sum((r['larger_gaps'] or 0) for r in results):,}")
    print("Largest observed gap:", max((r["largest_gap_minutes"] or 0) for r in results), "minutes")

    if counts.get("ERROR", 0) == 0 and not missing:
        print("AUDIT PASSED WITH NO CRITICAL FILE ERRORS.")
    else:
        print("AUDIT FAILED. Do not stitch or backtest this dataset yet.")


if __name__ == "__main__":
    main()
