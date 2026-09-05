from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
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


class BarchartStitchError(RuntimeError):
    """Raised when the audited Barchart contract series cannot be stitched safely."""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Stitch audited quarterly Barchart MNQ Parquets into one non-back-adjusted "
            "continuous research series using rollover_analysis.json."
        )
    )
    p.add_argument(
        "--contracts-dir",
        type=Path,
        default=Path("data/raw/barchart/contracts"),
    )
    p.add_argument(
        "--rollover-analysis",
        type=Path,
        default=Path("data/raw/barchart/rollover_analysis.json"),
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path("data/raw/barchart/mnq_continuous_1m.parquet"),
    )
    p.add_argument(
        "--audit-output",
        type=Path,
        default=Path("data/raw/barchart/mnq_continuous_1m.audit.json"),
    )
    return p.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_rollover_analysis(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("source") != "BARCHART" or report.get("symbol") != "MNQ":
        raise BarchartStitchError("Rollover analysis must be BARCHART / MNQ.")
    contracts = report.get("contracts_in_order") or []
    rollovers = report.get("rollovers") or []
    failures = report.get("failures") or []
    if failures or report.get("rollovers_failed", 0):
        raise BarchartStitchError("Rollover analysis contains failures; refusing to stitch.")
    if len(contracts) < 2:
        raise BarchartStitchError("Need at least two contracts in rollover analysis.")
    if len(rollovers) != len(contracts) - 1:
        raise BarchartStitchError(
            f"Expected {len(contracts)-1} rollovers for {len(contracts)} contracts; found {len(rollovers)}."
        )

    for index, rollover in enumerate(rollovers):
        expected_from = contracts[index]
        expected_to = contracts[index + 1]
        if rollover.get("from_contract") != expected_from or rollover.get("to_contract") != expected_to:
            raise BarchartStitchError(
                f"Rollover order mismatch at index {index}: expected {expected_from}->{expected_to}."
            )
        if rollover.get("method") != "confirmed_volume_crossover":
            raise BarchartStitchError(
                f"Unconfirmed rollover {expected_from}->{expected_to}; refusing automatic stitch."
            )

    timestamps = [pd.Timestamp(item["rollover_timestamp_utc"]) for item in rollovers]
    for ts in timestamps:
        if ts.tzinfo is None:
            raise BarchartStitchError("Rollover timestamps must be timezone-aware.")
    timestamps = [ts.tz_convert("UTC") for ts in timestamps]
    for previous, current in zip(timestamps, timestamps[1:]):
        if current <= previous:
            raise BarchartStitchError("Rollover timestamps must be strictly increasing.")

    report["_rollover_timestamps"] = timestamps
    return report


def _load_contract(path: Path, expected_contract: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_parquet(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise BarchartStitchError(f"{path.name}: missing required columns {sorted(missing)}")
    if df.empty:
        raise BarchartStitchError(f"{path.name}: empty contract file")

    result = df.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True, errors="raise")
    result = result.sort_values("timestamp", kind="stable").reset_index(drop=True)

    if result["timestamp"].duplicated().any():
        raise BarchartStitchError(f"{path.name}: duplicate timestamps")

    contracts = result["contract"].dropna().astype(str).str.upper().str.strip().unique().tolist()
    if contracts != [expected_contract]:
        raise BarchartStitchError(
            f"{path.name}: expected contract {expected_contract!r}, found {contracts}"
        )
    sources = result["source"].dropna().astype(str).str.upper().str.strip().unique().tolist()
    symbols = result["symbol"].dropna().astype(str).str.upper().str.strip().unique().tolist()
    if sources != ["BARCHART"] or symbols != ["MNQ"]:
        raise BarchartStitchError(f"{path.name}: expected source BARCHART and symbol MNQ")

    return result


def stitch_frames(
    frames: list[pd.DataFrame],
    contracts: list[str],
    rollovers: list[pd.Timestamp],
) -> tuple[pd.DataFrame, list[dict]]:
    if len(frames) != len(contracts):
        raise BarchartStitchError("Frame/contract count mismatch.")
    if len(rollovers) != len(contracts) - 1:
        raise BarchartStitchError("Rollover count mismatch.")

    pieces: list[pd.DataFrame] = []
    segments: list[dict] = []

    for index, (contract, frame) in enumerate(zip(contracts, frames)):
        start = None if index == 0 else rollovers[index - 1]
        end = None if index == len(contracts) - 1 else rollovers[index]

        mask = pd.Series(True, index=frame.index)
        if start is not None:
            mask &= frame["timestamp"] >= start
        if end is not None:
            mask &= frame["timestamp"] < end

        piece = frame.loc[mask].copy().reset_index(drop=True)
        if piece.empty:
            raise BarchartStitchError(f"{contract}: no rows in assigned rollover window")

        piece["rollover_segment"] = index
        piece["rollover_boundary"] = False
        piece["rollover_from_contract"] = pd.NA
        piece["rollover_to_contract"] = pd.NA
        if index > 0:
            piece.loc[0, "rollover_boundary"] = True
            piece.loc[0, "rollover_from_contract"] = contracts[index - 1]
            piece.loc[0, "rollover_to_contract"] = contract

        segments.append(
            {
                "contract": contract,
                "window_start_utc": None if start is None else start.isoformat(),
                "window_end_utc_exclusive": None if end is None else end.isoformat(),
                "rows_selected": int(len(piece)),
                "first_timestamp_utc": piece["timestamp"].min().isoformat(),
                "last_timestamp_utc": piece["timestamp"].max().isoformat(),
            }
        )
        pieces.append(piece)

    stitched = pd.concat(pieces, ignore_index=True)
    stitched = stitched.sort_values("timestamp", kind="stable").reset_index(drop=True)

    if stitched["timestamp"].duplicated().any():
        duplicates = stitched.loc[
            stitched["timestamp"].duplicated(keep=False), ["timestamp", "contract"]
        ].head(10)
        raise BarchartStitchError(
            f"Duplicate timestamps after stitching: {duplicates.to_dict('records')}"
        )

    contract_changes = stitched["contract"].astype(str).ne(stitched["contract"].astype(str).shift())
    expected_boundaries = contract_changes & stitched.index.to_series().ne(0)
    actual_boundaries = stitched["rollover_boundary"].fillna(False).astype(bool)
    if not expected_boundaries.equals(actual_boundaries):
        raise BarchartStitchError("Contract changes do not match rollover boundary markers.")

    return stitched, segments


def main() -> None:
    args = parse_args()
    analysis = _load_rollover_analysis(args.rollover_analysis)
    contracts = analysis["contracts_in_order"]
    rollovers = analysis.pop("_rollover_timestamps")

    frames: list[pd.DataFrame] = []
    inputs: list[dict] = []
    for contract in contracts:
        path = args.contracts_dir / f"{contract}_1m.parquet"
        frame = _load_contract(path, contract)
        frames.append(frame)
        inputs.append(
            {
                "contract": contract,
                "file": str(path),
                "rows": int(len(frame)),
                "sha256": _sha256(path),
                "first_timestamp_utc": frame["timestamp"].min().isoformat(),
                "last_timestamp_utc": frame["timestamp"].max().isoformat(),
            }
        )

    stitched, segments = stitch_frames(frames, contracts, rollovers)
    diffs = stitched["timestamp"].diff().dropna()
    gaps = diffs[diffs > pd.Timedelta(minutes=2)]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.audit_output.parent.mkdir(parents=True, exist_ok=True)
    stitched.to_parquet(args.output, index=False)

    audit = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "BARCHART",
        "symbol": "MNQ",
        "price_adjustment": "none",
        "rollover_rule": analysis.get("rule"),
        "rollover_analysis_file": str(args.rollover_analysis),
        "rollover_analysis_sha256": _sha256(args.rollover_analysis),
        "contracts_in_order": contracts,
        "rollovers_utc": [ts.isoformat() for ts in rollovers],
        "inputs": inputs,
        "segments": segments,
        "output_file": str(args.output),
        "output_sha256": _sha256(args.output),
        "output_rows": int(len(stitched)),
        "first_timestamp_utc": stitched["timestamp"].min().isoformat(),
        "last_timestamp_utc": stitched["timestamp"].max().isoformat(),
        "rollover_boundaries": int(stitched["rollover_boundary"].sum()),
        "duplicate_timestamps": int(stitched["timestamp"].duplicated().sum()),
        "gaps_over_two_minutes": int(len(gaps)),
        "largest_gap_minutes": (
            float(gaps.max().total_seconds() / 60.0) if not gaps.empty else 0.0
        ),
    }
    args.audit_output.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    print("\n" + "=" * 80)
    print("BARCHART CONTINUOUS MNQ STITCH COMPLETE")
    print("=" * 80)
    print(f"Contracts:            {len(contracts)}")
    print(f"Rollover boundaries:  {audit['rollover_boundaries']}")
    print(f"Rows:                 {audit['output_rows']:,}")
    print(f"UTC coverage:         {audit['first_timestamp_utc']} -> {audit['last_timestamp_utc']}")
    print(f"Duplicate timestamps: {audit['duplicate_timestamps']}")
    print(f"Gaps >2m:             {audit['gaps_over_two_minutes']:,}")
    print("Price adjustment:     none")
    print(f"Output:                {args.output}")
    print(f"Audit:                 {args.audit_output}")


if __name__ == "__main__":
    main()
