from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

OUT = Path("manifest.csv")

# Quarterly MNQ contract windows used for the initial five-year Barchart archive.
# Windows intentionally overlap by five calendar days around roll periods so the
# final continuous series can choose an explicit rollover boundary later.
CONTRACTS = [
    ("NMH22", date(2021, 12, 20), date(2022, 3, 18)),
    ("NMM22", date(2022, 3, 14), date(2022, 6, 17)),
    ("NMU22", date(2022, 6, 13), date(2022, 9, 16)),
    ("NMZ22", date(2022, 9, 12), date(2022, 12, 16)),
    ("NMH23", date(2022, 12, 12), date(2023, 3, 17)),
    ("NMM23", date(2023, 3, 13), date(2023, 6, 16)),
    ("NMU23", date(2023, 6, 12), date(2023, 9, 15)),
    ("NMZ23", date(2023, 9, 11), date(2023, 12, 15)),
    ("NMH24", date(2023, 12, 11), date(2024, 3, 15)),
    ("NMM24", date(2024, 3, 11), date(2024, 6, 21)),
    ("NMU24", date(2024, 6, 17), date(2024, 9, 20)),
    ("NMZ24", date(2024, 9, 16), date(2024, 12, 20)),
    ("NMH25", date(2024, 12, 16), date(2025, 3, 21)),
    ("NMM25", date(2025, 3, 17), date(2025, 6, 20)),
    ("NMU25", date(2025, 6, 16), date(2025, 9, 19)),
    ("NMZ25", date(2025, 9, 15), date(2025, 12, 19)),
    ("NMH26", date(2025, 12, 15), date(2026, 3, 20)),
    ("NMM26", date(2026, 3, 16), date(2026, 6, 19)),
    ("NMU26", date(2026, 6, 15), date(2026, 9, 4)),
]

CHUNK_DAYS = 13


def main() -> None:
    rows: list[dict[str, str]] = []

    for contract, start, end in CONTRACTS:
        cursor = start
        while cursor <= end:
            chunk_end = min(cursor + timedelta(days=CHUNK_DAYS), end)
            filename = f"{contract}_{cursor.isoformat()}_{chunk_end.isoformat()}_1m.csv"
            rows.append(
                {
                    "contract": contract,
                    "start_date": cursor.isoformat(),
                    "end_date": chunk_end.isoformat(),
                    "filename": filename,
                    "status": "pending",
                }
            )
            cursor = chunk_end + timedelta(days=1)

    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["contract", "start_date", "end_date", "filename", "status"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} download jobs to {OUT}")


if __name__ == "__main__":
    main()
