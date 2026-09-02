from __future__ import annotations

import argparse
import os
import sys
from datetime import timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIRECTORY = PROJECT_ROOT / "src"
if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))

from projectx_client import (  # noqa: E402
    DEFAULT_API_BASE_URL,
    DEFAULT_CHUNK_DAYS,
    DEFAULT_REQUEST_DELAY_SECONDS,
    ProjectXClient,
    ProjectXError,
    credentials_from_environment,
    format_api_datetime,
    load_simple_env,
    parse_datetime_utc,
    save_csv,
    utc_now,
)


DEFAULT_OUTPUT = Path("data/raw/projectx/mnq_1m.csv")


def _argument_datetime(value: str):
    try:
        return parse_datetime_utc(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download read-only ProjectX/TopstepX MNQ one-minute historical "
            "bars for the trade-alerts research pipeline."
        )
    )
    parser.add_argument(
        "--symbol",
        default="MNQ",
        help="Contract search symbol. Default: MNQ",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=60,
        help="Days of history when --start is not supplied. Default: 60",
    )
    parser.add_argument(
        "--start",
        type=_argument_datetime,
        default=None,
        help="Optional timezone-aware start, e.g. 2026-07-01T00:00:00Z.",
    )
    parser.add_argument(
        "--end",
        type=_argument_datetime,
        default=None,
        help="Optional timezone-aware end. Default: current UTC time.",
    )
    parser.add_argument(
        "--contract-id",
        default=None,
        help="Exact ProjectX contract ID. Bypasses automatic contract search.",
    )
    parser.add_argument(
        "--contract-name",
        default=None,
        help="Exact ProjectX contract name, e.g. MNQU6.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use the ProjectX live-data subscription flag.",
    )
    parser.add_argument(
        "--chunk-days",
        type=int,
        default=DEFAULT_CHUNK_DAYS,
        help="Calendar days per historical request. Default: 10",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_REQUEST_DELAY_SECONDS,
        help="Seconds between historical requests. Default: 0.8",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path. Default: {DEFAULT_OUTPUT}",
    )
    return parser.parse_args()


def run(args: argparse.Namespace) -> Path:
    if args.days <= 0:
        raise ValueError("--days must be greater than zero.")
    if args.chunk_days <= 0:
        raise ValueError("--chunk-days must be greater than zero.")
    if args.delay < 0:
        raise ValueError("--delay cannot be negative.")
    if args.contract_id and args.contract_name:
        raise ValueError("Use either --contract-id or --contract-name, not both.")

    load_simple_env(PROJECT_ROOT / ".env")
    credentials = credentials_from_environment()
    base_url = os.getenv("PROJECTX_BASE_URL", DEFAULT_API_BASE_URL)

    end_time = args.end or utc_now()
    start_time = args.start or (end_time - timedelta(days=args.days))
    if start_time >= end_time:
        raise ValueError("Start time must be earlier than end time.")

    client = ProjectXClient(
        username=credentials.username,
        api_key=credentials.api_key,
        base_url=base_url,
        live=args.live,
    )

    print("Authenticating with ProjectX...")
    client.authenticate()
    print("ProjectX authentication: OK")

    contract_id = args.contract_id
    if contract_id is None and args.contract_name is None:
        contract_id = os.getenv("PROJECTX_CONTRACT_ID") or None
    contract = client.resolve_contract(
        symbol=args.symbol,
        contract_name=args.contract_name,
        contract_id=contract_id,
    )
    print(f"Contract: {contract.name} ({contract.contract_id})")
    print(f"Fetching: {format_api_datetime(start_time)} -> {format_api_datetime(end_time)}")

    dataframe = client.fetch_bars(
        symbol=args.symbol,
        contract=contract,
        start_time=start_time,
        end_time=end_time,
        chunk_days=args.chunk_days,
        request_delay_seconds=args.delay,
    )
    output_path = save_csv(dataframe, args.output)

    print("Download complete.")
    print(f"Rows: {len(dataframe):,}")
    print(f"Start: {dataframe['timestamp'].min()}")
    print(f"End: {dataframe['timestamp'].max()}")
    print(f"Output: {output_path}")
    return output_path


def main() -> None:
    try:
        run(parse_arguments())
    except (ProjectXError, ValueError) as exc:
        print(f"ProjectX download failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
