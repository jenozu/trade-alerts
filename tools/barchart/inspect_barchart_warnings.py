from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE_DIR = Path.home() / "Documents" / "barchart-downloader"
DOWNLOAD_DIR = Path.home() / "Downloads" / "barchart-history"
MANIFEST = BASE_DIR / "manifest.csv"


def main() -> None:
    manifest = pd.read_csv(MANIFEST)
    bad_row_examples = []
    start_offsets = []
    files_with_bad_timestamp = 0
    files_with_null_market_row = 0

    for _, job in manifest.iterrows():
        path = DOWNLOAD_DIR / job["filename"]
        df = pd.read_csv(path)
        ts = pd.to_datetime(df["Time"], errors="coerce")
        bad_mask = ts.isna()

        if bad_mask.any():
            files_with_bad_timestamp += 1
            if len(bad_row_examples) < 10:
                for _, row in df.loc[bad_mask].iterrows():
                    bad_row_examples.append({"file": path.name, "row": row.to_dict()})

        market_columns = [
            col for col in ["Open", "High", "Low", "Latest", "Volume"] if col in df.columns
        ]
        if market_columns and df[market_columns].isna().any(axis=1).any():
            files_with_null_market_row += 1

        valid_ts = ts.dropna()
        if not valid_ts.empty:
            requested_start = pd.Timestamp(job["start_date"]).normalize()
            actual_start = valid_ts.min()
            offset_minutes = (actual_start - requested_start) / pd.Timedelta(minutes=1)
            start_offsets.append(
                {
                    "file": path.name,
                    "contract": job["contract"],
                    "requested_start": requested_start,
                    "actual_start": actual_start,
                    "offset_minutes": float(offset_minutes),
                }
            )

    print("=== BAD ROW COUNTS ===")
    print("Files with bad timestamp:", files_with_bad_timestamp)
    print("Files with null OHLCV row:", files_with_null_market_row)

    print("\n=== EXAMPLE BAD ROWS ===")
    for example in bad_row_examples:
        print("FILE:", example["file"])
        print("ROW:", example["row"])

    offsets = pd.DataFrame(start_offsets)
    before = offsets[offsets["offset_minutes"] < 0]
    exact = offsets[offsets["offset_minutes"] == 0]
    after = offsets[offsets["offset_minutes"] > 0]

    print("\n=== START-DATE OFFSET SUMMARY ===")
    print("Files inspected:", len(offsets))
    print("Start before requested:", len(before))
    print("Start exactly requested:", len(exact))
    print("Start after requested:", len(after))

    if not before.empty:
        print("Earliest relative start:", before["offset_minutes"].min(), "minutes")
        print("Median early start:", before["offset_minutes"].median(), "minutes")
        print("\n=== MOST EXTREME EARLY STARTS ===")
        print(
            before.sort_values("offset_minutes")
            .head(20)[
                ["contract", "requested_start", "actual_start", "offset_minutes", "file"]
            ]
            .to_string(index=False)
        )
        print("\n=== UNIQUE EARLY-OFFSET VALUES ===")
        print(before["offset_minutes"].value_counts().sort_index().to_string())


if __name__ == "__main__":
    main()
