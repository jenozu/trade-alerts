from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIRECTORY = PROJECT_ROOT / "src"
if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))

from rollover import (  # noqa: E402
    ContractWindow,
    RolloverError,
    load_contract_csv,
    save_stitched_csv,
    stitch_contract_frames,
)

DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "raw" / "projectx" / "mnq_continuous_1m.csv"
DEFAULT_AUDIT_OUTPUT = PROJECT_ROOT / "data" / "raw" / "projectx" / "mnq_continuous_1m.audit.json"


def parse_contract_spec(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            "Contract input must use CONTRACT=PATH, e.g. MNQM6=data/raw/projectx/MNQM6_1m.csv"
        )
    contract, raw_path = value.split("=", 1)
    contract = contract.upper().strip()
    raw_path = raw_path.strip()
    if not contract or not raw_path:
        raise argparse.ArgumentTypeError("Contract input requires both CONTRACT and PATH.")
    return contract, Path(raw_path)


def parse_rollover_timestamp(value: str) -> pd.Timestamp:
    try:
        timestamp = pd.Timestamp(value)
    except Exception as exc:
        raise argparse.ArgumentTypeError(f"Invalid rollover timestamp: {value!r}") from exc
    if timestamp.tzinfo is None:
        raise argparse.ArgumentTypeError(
            "Rollover timestamps must be timezone-aware, e.g. 2026-06-12T22:00:00Z."
        )
    return timestamp.tz_convert("UTC")


def build_contract_windows(
    contracts: Sequence[str],
    rollovers: Sequence[pd.Timestamp],
) -> list[ContractWindow]:
    if len(contracts) < 2:
        raise RolloverError("At least two contracts are required for a rollover stitch.")
    if len(rollovers) != len(contracts) - 1:
        raise RolloverError(
            f"Expected {len(contracts) - 1} rollover timestamp(s) for {len(contracts)} contracts; "
            f"received {len(rollovers)}."
        )

    normalized_rollovers = [parse_rollover_timestamp(str(value)) for value in rollovers]
    for previous, current in zip(normalized_rollovers, normalized_rollovers[1:]):
        if current <= previous:
            raise RolloverError("Rollover timestamps must be strictly increasing.")

    windows: list[ContractWindow] = []
    for index, contract in enumerate(contracts):
        start = None if index == 0 else normalized_rollovers[index - 1]
        end = None if index == len(contracts) - 1 else normalized_rollovers[index]
        windows.append(ContractWindow(contract=contract, start=start, end=end))
    return windows


def _resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def _validate_symbol(frame: pd.DataFrame, *, symbol: str, contract: str) -> None:
    if "symbol" not in frame.columns:
        return
    values = frame["symbol"].dropna().astype(str).str.upper().str.strip().unique().tolist()
    if values and any(value != symbol for value in values):
        raise RolloverError(
            f"Contract {contract!r} contains symbol values {values}; expected only {symbol!r}."
        )


def create_stitched_dataset(
    contract_specs: Sequence[tuple[str, Path]],
    rollovers: Sequence[pd.Timestamp],
    *,
    symbol: str = "MNQ",
) -> tuple[pd.DataFrame, dict]:
    if len(contract_specs) < 2:
        raise RolloverError("At least two --contract inputs are required.")

    symbol = symbol.upper().strip()
    contracts = [contract.upper().strip() for contract, _ in contract_specs]
    if len(set(contracts)) != len(contracts):
        raise RolloverError("Each contract may appear only once in the stitch order.")

    windows = build_contract_windows(contracts, rollovers)
    frames: dict[str, pd.DataFrame] = {}
    input_records: list[dict] = []

    for contract, raw_path in contract_specs:
        contract = contract.upper().strip()
        path = _resolve_path(raw_path)
        frame = load_contract_csv(path, expected_contract=contract)
        _validate_symbol(frame, symbol=symbol, contract=contract)
        frames[contract] = frame
        input_records.append(
            {
                "contract": contract,
                "file": str(path),
                "rows_loaded": int(len(frame)),
                "start_loaded": str(frame["timestamp"].min()),
                "end_loaded": str(frame["timestamp"].max()),
            }
        )

    stitched = stitch_contract_frames(frames, windows)

    selected_records: list[dict] = []
    for contract in contracts:
        group = stitched.loc[stitched["contract"].astype(str).str.upper() == contract]
        selected_records.append(
            {
                "contract": contract,
                "rows_selected": int(len(group)),
                "start_selected": str(group["timestamp"].min()),
                "end_selected": str(group["timestamp"].max()),
            }
        )

    audit = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "price_adjustment": "none",
        "boundary_rule": "old contract end exclusive; new contract start inclusive",
        "contracts_in_order": contracts,
        "rollovers_utc": [str(parse_rollover_timestamp(str(value))) for value in rollovers],
        "inputs": input_records,
        "selected_segments": selected_records,
        "output_rows": int(len(stitched)),
        "rollover_boundaries": int(stitched["rollover_boundary"].fillna(False).astype(bool).sum()),
    }
    return stitched, audit


def save_audit(audit: dict, filepath: Path) -> Path:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with filepath.open("w", encoding="utf-8") as file:
        json.dump(audit, file, indent=2, default=str)
    return filepath


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Stitch ProjectX quarterly futures contract CSVs into one non-adjusted "
            "research series using explicit rollover timestamps."
        )
    )
    parser.add_argument(
        "--contract",
        action="append",
        required=True,
        type=parse_contract_spec,
        metavar="CONTRACT=PATH",
        help=(
            "Contract file in chronological order. Repeat once per contract, e.g. "
            "--contract MNQM6=data/raw/projectx/MNQM6_1m.csv"
        ),
    )
    parser.add_argument(
        "--rollover",
        action="append",
        default=[],
        type=parse_rollover_timestamp,
        metavar="TIMESTAMP",
        help=(
            "Timezone-aware UTC rollover boundary between adjacent contracts. "
            "Repeat N-1 times for N contracts."
        ),
    )
    parser.add_argument("--symbol", default="MNQ", help="Expected root symbol. Default: MNQ")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--audit-output", type=Path, default=DEFAULT_AUDIT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    stitched, audit = create_stitched_dataset(
        args.contract,
        args.rollover,
        symbol=args.symbol,
    )

    output_path = _resolve_path(args.output)
    audit_path = _resolve_path(args.audit_output)
    save_stitched_csv(stitched, output_path)
    save_audit(audit, audit_path)

    print("\n============================================================")
    print("PROJECTX CONTRACT STITCH COMPLETE")
    print("============================================================")
    print(f"Symbol: {audit['symbol']}")
    print(f"Contracts: {' -> '.join(audit['contracts_in_order'])}")
    print(f"Rows: {audit['output_rows']:,}")
    print(f"Rollover boundaries: {audit['rollover_boundaries']}")
    print("Price adjustment: none")
    print(f"\nStitched CSV:\n{output_path}")
    print(f"\nAudit JSON:\n{audit_path}")


if __name__ == "__main__":
    main()
