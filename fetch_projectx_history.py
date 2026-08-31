from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd


API_BASE_URL = "https://api.topstepx.com"
AUTH_ENDPOINT = "/api/Auth/loginKey"
CONTRACT_SEARCH_ENDPOINT = "/api/Contract/search"
HISTORY_ENDPOINT = "/api/History/retrieveBars"

DEFAULT_OUTPUT = Path("data/raw/projectx/nq_1m.csv")
MAX_BARS_PER_REQUEST = 20_000
DEFAULT_CHUNK_DAYS = 10
DEFAULT_REQUEST_DELAY_SECONDS = 0.8
DEFAULT_TIMEOUT_SECONDS = 30
MAX_RETRIES = 5


class ProjectXError(RuntimeError):
    """Raised when a ProjectX API request or response is invalid."""


def load_simple_env(path: Path = Path(".env")) -> None:
    """Load simple KEY=VALUE pairs from .env without adding a dependency."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            continue

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            value = value[1:-1]

        os.environ.setdefault(key, value)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime_utc(value: str) -> datetime:
    """Parse an ISO-like timestamp and return a timezone-aware UTC datetime."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid datetime {value!r}. Use ISO format, e.g. 2026-08-01T00:00:00Z."
        ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def format_api_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def http_post_json(
    endpoint: str,
    payload: dict[str, Any],
    *,
    token: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """POST JSON to ProjectX with small, bounded retry handling."""
    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "trade-alerts-projectx-history/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request_body = json.dumps(payload).encode("utf-8")

    for attempt in range(1, MAX_RETRIES + 1):
        request = Request(
            url,
            data=request_body,
            headers=headers,
            method="POST",
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                data = json.loads(body)
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            retryable = exc.code == 429 or 500 <= exc.code < 600
            if retryable and attempt < MAX_RETRIES:
                wait_seconds = min(2 ** attempt, 30)
                print(
                    f"HTTP {exc.code} from ProjectX; retrying in "
                    f"{wait_seconds}s ({attempt}/{MAX_RETRIES})..."
                )
                time.sleep(wait_seconds)
                continue
            raise ProjectXError(
                f"ProjectX HTTP {exc.code} for {endpoint}: {error_body[:1000]}"
            ) from exc
        except URLError as exc:
            if attempt < MAX_RETRIES:
                wait_seconds = min(2 ** attempt, 30)
                print(
                    f"Network error contacting ProjectX; retrying in "
                    f"{wait_seconds}s ({attempt}/{MAX_RETRIES})..."
                )
                time.sleep(wait_seconds)
                continue
            raise ProjectXError(
                f"Could not reach ProjectX endpoint {endpoint}: {exc}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise ProjectXError(
                f"ProjectX returned invalid JSON for {endpoint}."
            ) from exc

        if not isinstance(data, dict):
            raise ProjectXError(
                f"Unexpected ProjectX response type for {endpoint}: {type(data)!r}"
            )

        if data.get("success") is False:
            raise ProjectXError(
                f"ProjectX API error for {endpoint}: "
                f"{data.get('errorMessage') or 'Unknown error'} "
                f"(code={data.get('errorCode')})"
            )

        return data

    raise ProjectXError(f"ProjectX request failed after {MAX_RETRIES} attempts.")


def authenticate(username: str, api_key: str) -> str:
    response = http_post_json(
        AUTH_ENDPOINT,
        {
            "userName": username,
            "apiKey": api_key,
        },
    )

    token = response.get("token")
    if not response.get("success") or not token:
        raise ProjectXError(
            "Authentication failed or ProjectX did not return a session token."
        )

    return str(token)


def search_contracts(
    token: str,
    *,
    search_text: str,
    live: bool,
) -> list[dict[str, Any]]:
    response = http_post_json(
        CONTRACT_SEARCH_ENDPOINT,
        {
            "searchText": search_text,
            "live": live,
        },
        token=token,
    )

    contracts = response.get("contracts")
    if not isinstance(contracts, list):
        raise ProjectXError("Contract search did not return a contracts list.")

    return [item for item in contracts if isinstance(item, dict)]


def _looks_like_nq_contract(contract: dict[str, Any], symbol: str) -> bool:
    name = str(contract.get("name") or "").upper().strip()
    description = str(contract.get("description") or "").upper()
    symbol_id = str(contract.get("symbolId") or "").upper()

    symbol = symbol.upper()
    if symbol == "NQ":
        return (
            bool(re.match(r"^NQ[A-Z]\d{1,2}$", name))
            or symbol_id.endswith(".ENQ")
            or "E-MINI NASDAQ-100" in description
        )

    return name.startswith(symbol)


def choose_contract(
    contracts: list[dict[str, Any]],
    *,
    symbol: str,
    contract_name: str | None = None,
) -> dict[str, Any]:
    if contract_name:
        wanted = contract_name.upper().strip()
        exact = [
            contract
            for contract in contracts
            if str(contract.get("name") or "").upper().strip() == wanted
        ]
        if len(exact) == 1:
            return exact[0]
        if not exact:
            available = ", ".join(
                str(contract.get("name") or contract.get("id"))
                for contract in contracts
            )
            raise ProjectXError(
                f"Contract {contract_name!r} was not returned by ProjectX. "
                f"Returned: {available}"
            )
        raise ProjectXError(f"Multiple contracts matched {contract_name!r}.")

    candidates = [
        contract
        for contract in contracts
        if _looks_like_nq_contract(contract, symbol)
    ]

    if not candidates:
        available = ", ".join(
            str(contract.get("name") or contract.get("id"))
            for contract in contracts
        )
        raise ProjectXError(
            f"Could not identify a {symbol} contract automatically. "
            f"Returned: {available}. Re-run with --contract-name or --contract-id."
        )

    active = [
        contract
        for contract in candidates
        if bool(contract.get("activeContract"))
    ]

    if len(active) == 1:
        return active[0]

    if len(candidates) == 1:
        return candidates[0]

    names = ", ".join(
        str(contract.get("name") or contract.get("id"))
        for contract in candidates
    )
    raise ProjectXError(
        f"Multiple {symbol} contracts matched and no single active contract "
        f"could be selected: {names}. Use --contract-name or --contract-id."
    )


def retrieve_bars(
    token: str,
    *,
    contract_id: str,
    start_time: datetime,
    end_time: datetime,
    live: bool,
    chunk_days: int,
    request_delay_seconds: float,
) -> list[dict[str, Any]]:
    """Retrieve completed one-minute bars in small date chunks."""
    if start_time >= end_time:
        raise ValueError("start_time must be earlier than end_time.")
    if chunk_days <= 0:
        raise ValueError("chunk_days must be positive.")

    all_bars: list[dict[str, Any]] = []
    cursor = start_time
    request_number = 0

    while cursor < end_time:
        chunk_end = min(cursor + timedelta(days=chunk_days), end_time)
        request_number += 1

        print(
            f"[{request_number}] Fetching "
            f"{format_api_datetime(cursor)} -> {format_api_datetime(chunk_end)}"
        )

        response = http_post_json(
            HISTORY_ENDPOINT,
            {
                "contractId": contract_id,
                "live": live,
                "startTime": format_api_datetime(cursor),
                "endTime": format_api_datetime(chunk_end),
                "unit": 2,
                "unitNumber": 1,
                "limit": MAX_BARS_PER_REQUEST,
                "includePartialBar": False,
            },
            token=token,
        )

        bars = response.get("bars")
        if not isinstance(bars, list):
            raise ProjectXError(
                "Historical response did not contain a bars list."
            )

        valid_bars = [bar for bar in bars if isinstance(bar, dict)]
        print(f"    received {len(valid_bars):,} bars")
        all_bars.extend(valid_bars)

        cursor = chunk_end
        if cursor < end_time and request_delay_seconds > 0:
            time.sleep(request_delay_seconds)

    return all_bars


def normalize_bars(
    bars: list[dict[str, Any]],
    *,
    symbol: str,
    contract_label: str,
) -> pd.DataFrame:
    if not bars:
        raise ProjectXError("ProjectX returned zero historical bars.")

    rows: list[dict[str, Any]] = []
    for bar in bars:
        rows.append(
            {
                "timestamp": bar.get("t"),
                "open": bar.get("o"),
                "high": bar.get("h"),
                "low": bar.get("l"),
                "close": bar.get("c"),
                "volume": bar.get("v"),
                "source": "PROJECTX",
                "symbol": symbol.upper(),
                "contract": contract_label,
            }
        )

    dataframe = pd.DataFrame(rows)

    required = ["timestamp", "open", "high", "low", "close", "volume"]
    missing = [column for column in required if column not in dataframe.columns]
    if missing:
        raise ProjectXError(f"Normalized data is missing columns: {missing}")

    dataframe["timestamp"] = pd.to_datetime(
        dataframe["timestamp"],
        errors="raise",
        utc=True,
    )

    for column in ["open", "high", "low", "close", "volume"]:
        dataframe[column] = pd.to_numeric(dataframe[column], errors="raise")

    dataframe = (
        dataframe
        .drop_duplicates(subset=["timestamp"], keep="last")
        .sort_values("timestamp", kind="stable")
        .reset_index(drop=True)
    )

    invalid_high = dataframe["high"] < dataframe[
        ["open", "close", "low"]
    ].max(axis=1)
    invalid_low = dataframe["low"] > dataframe[
        ["open", "close", "high"]
    ].min(axis=1)

    if invalid_high.any() or invalid_low.any():
        raise ProjectXError(
            "ProjectX historical data contains invalid OHLC relationships."
        )

    if (dataframe[["open", "high", "low", "close"]] <= 0).any().any():
        raise ProjectXError("ProjectX returned zero/negative prices.")
    if (dataframe["volume"] < 0).any():
        raise ProjectXError("ProjectX returned negative volume.")

    return dataframe


def save_csv(dataframe: pd.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = dataframe.copy()
    result["timestamp"] = result["timestamp"].dt.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    result.to_csv(output_path, index=False)
    return output_path


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download read-only ProjectX/TopstepX NQ one-minute historical "
            "bars for the trade-alerts backtesting pipeline."
        )
    )
    parser.add_argument(
        "--symbol",
        default="NQ",
        help="Contract search symbol. Default: NQ",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=60,
        help="Days of history when --start is not supplied. Default: 60",
    )
    parser.add_argument(
        "--start",
        type=parse_datetime_utc,
        default=None,
        help="Optional UTC start datetime, e.g. 2026-07-01T00:00:00Z.",
    )
    parser.add_argument(
        "--end",
        type=parse_datetime_utc,
        default=None,
        help="Optional UTC end datetime. Default: current UTC time.",
    )
    parser.add_argument(
        "--contract-id",
        default=None,
        help="Exact ProjectX contract ID. Bypasses automatic contract search.",
    )
    parser.add_argument(
        "--contract-name",
        default=None,
        help="Exact ProjectX contract name, e.g. NQU6.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help=(
            "Use the live data subscription flag. Default is false/sim data "
            "subscription, which is suitable for backtesting."
        ),
    )
    parser.add_argument(
        "--chunk-days",
        type=int,
        default=DEFAULT_CHUNK_DAYS,
        help=(
            "Calendar days per historical request. Default: 10. "
            "Ten days keeps 1-minute requests below the 20,000-bar cap."
        ),
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_REQUEST_DELAY_SECONDS,
        help="Seconds to wait between historical requests. Default: 0.8",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path. Default: {DEFAULT_OUTPUT}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    if args.days <= 0:
        raise SystemExit("--days must be greater than zero.")
    if args.chunk_days <= 0:
        raise SystemExit("--chunk-days must be greater than zero.")
    if args.delay < 0:
        raise SystemExit("--delay cannot be negative.")
    if args.contract_id and args.contract_name:
        raise SystemExit(
            "Use either --contract-id or --contract-name, not both."
        )

    load_simple_env()

    username = os.getenv("TOPSTEP_USERNAME")
    api_key = os.getenv("TOPSTEP_API_KEY")

    if not username or not api_key:
        print(
            "Missing ProjectX credentials.\n\n"
            "Set these environment variables or put them in a local .env file:\n"
            "TOPSTEP_USERNAME=your_username\n"
            "TOPSTEP_API_KEY=your_api_key\n",
            file=sys.stderr,
        )
        raise SystemExit(2)

    end_time = args.end or utc_now()
    start_time = args.start or (end_time - timedelta(days=args.days))

    if start_time >= end_time:
        raise SystemExit("Start time must be earlier than end time.")

    print("Authenticating with ProjectX...")
    token = authenticate(username, api_key)
    print("Authentication successful.")

    contract_id = args.contract_id
    contract_label = args.contract_name or args.contract_id

    if not contract_id:
        print(f"Searching ProjectX contracts for {args.symbol.upper()}...")
        contracts = search_contracts(
            token,
            search_text=args.symbol.upper(),
            live=args.live,
        )
        selected = choose_contract(
            contracts,
            symbol=args.symbol,
            contract_name=args.contract_name,
        )

        contract_id = str(selected.get("id") or "").strip()
        if not contract_id:
            raise ProjectXError("Selected contract does not have an ID.")

        contract_label = str(
            selected.get("name") or selected.get("id")
        ).strip()

        print(
            "Selected contract: "
            f"{contract_label} ({contract_id})"
            + (
                f" - {selected.get('description')}"
                if selected.get("description")
                else ""
            )
        )

    assert contract_id is not None
    assert contract_label is not None

    print(
        f"Downloading {args.symbol.upper()} 1-minute bars:\n"
        f"  Start:    {format_api_datetime(start_time)}\n"
        f"  End:      {format_api_datetime(end_time)}\n"
        f"  Contract: {contract_label}\n"
        f"  Live flag:{' true' if args.live else ' false'}"
    )

    bars = retrieve_bars(
        token,
        contract_id=contract_id,
        start_time=start_time,
        end_time=end_time,
        live=args.live,
        chunk_days=args.chunk_days,
        request_delay_seconds=args.delay,
    )

    dataframe = normalize_bars(
        bars,
        symbol=args.symbol,
        contract_label=contract_label,
    )

    output_path = save_csv(dataframe, args.output)

    print("\nDownload complete.")
    print(f"Rows:   {len(dataframe):,}")
    print(f"Start:  {dataframe['timestamp'].min()}")
    print(f"End:    {dataframe['timestamp'].max()}")
    print(f"Output: {output_path}")
    print(
        "\nNext step:\n"
        "python run_pipeline.py "
        f"--input {output_path} "
        "--source PROJECTX "
        f"--symbol {args.symbol.upper()} "
        f"--contract {contract_label} "
        "--timezone UTC "
        "--stop-after validate"
    )


if __name__ == "__main__":
    main()
