from __future__ import annotations

import pandas as pd


def main() -> None:
    df = pd.read_csv("manifest.csv")
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])

    print("=== MANIFEST AUDIT ===")
    print("Jobs:", len(df))
    print("First date:", df["start_date"].min().date())
    print("Last date:", df["end_date"].max().date())
    print("Contracts:", df["contract"].nunique())

    print("\n=== CONTRACT COVERAGE ===")
    for contract, group in df.groupby("contract", sort=False):
        print(
            f"{contract:6} | {group['start_date'].min().date()} -> "
            f"{group['end_date'].max().date()} | {len(group):3} downloads"
        )

    print("\n=== CONTRACT ORDER ===")
    print(" -> ".join(df["contract"].drop_duplicates().tolist()))

    chunk_problems = []
    for contract, group in df.groupby("contract", sort=False):
        group = group.sort_values("start_date").reset_index(drop=True)
        for index in range(1, len(group)):
            previous = group.iloc[index - 1]
            current = group.iloc[index]
            expected = previous["end_date"] + pd.Timedelta(days=1)
            if current["start_date"] != expected:
                chunk_problems.append(
                    (contract, previous["end_date"].date(), current["start_date"].date())
                )

    print("\n=== PER-CONTRACT CHUNK CONTINUITY ===")
    if chunk_problems:
        for item in chunk_problems:
            print("PROBLEM:", item)
    else:
        print("All contract chunks are continuous.")

    windows = (
        df.groupby("contract", sort=False)
        .agg(start=("start_date", "min"), end=("end_date", "max"))
        .reset_index()
    )

    print("\n=== CONTRACT WINDOW OVERLAPS ===")
    for index in range(1, len(windows)):
        previous = windows.iloc[index - 1]
        current = windows.iloc[index]
        overlap_start = max(previous["start"], current["start"])
        overlap_end = min(previous["end"], current["end"])
        if overlap_start <= overlap_end:
            days = (overlap_end - overlap_start).days + 1
            print(
                f"{previous['contract']} -> {current['contract']} | "
                f"{overlap_start.date()} -> {overlap_end.date()} | {days} calendar days overlap"
            )
        else:
            print(f"{previous['contract']} -> {current['contract']} | NO OVERLAP")

    problems = []
    if len(df) != 133:
        problems.append(f"Expected 133 jobs, found {len(df)}")
    if not (df["status"] == "pending").all():
        problems.append("Not every manifest job is currently pending.")
    if chunk_problems:
        problems.append(f"{len(chunk_problems)} chunk continuity problems found.")
    if df["filename"].duplicated().any():
        problems.append("Duplicate filenames found.")
    if (df["start_date"] > df["end_date"]).any():
        problems.append("At least one job starts after its end date.")

    print("\n=== SAFETY CHECKS ===")
    if problems:
        print("AUDIT NEEDS REVIEW")
        for problem in problems:
            print(" -", problem)
    else:
        print("BASIC MANIFEST AUDIT PASSED")


if __name__ == "__main__":
    main()
