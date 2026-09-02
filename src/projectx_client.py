from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd


DEFAULT_API_BASE_URL = "https://api.topstepx.com"
AUTH_ENDPOINT = "/api/Auth/loginKey"
CONTRACT_SEARCH_ENDPOINT = "/api/Contract/search"
HISTORY_ENDPOINT = "/api/History/retrieveBars"

MAX_BARS_PER_REQUEST = 20_000
DEFAULT_CHUNK_DAYS = 10
DEFAULT_REQUEST_DELAY_SECONDS = 0.8
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 5

REQUIRED_BAR_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")
BAR_VALUE_COLUMNS = ("open", "high", "low", "close", "volume")


class ProjectXError(RuntimeError):
    """Base exception for read-only ProjectX market-data failures."""


class ProjectXHTTPError(ProjectXError):
    """Raised when ProjectX returns a non-retryable HTTP response."""

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class ProjectXAPIError(ProjectXError):
    """Raised when a successful HTTP response contains an API-level error."""

    def __init__(self, message: str, *, error_code: Any = None) -> None:
        super().__init__(message)
        self.error_code = error_code


class ProjectXAuthenticationError(ProjectXError):
    """Raised when ProjectX authentication fails."""


class ProjectXDataError(ProjectXError):
    """Raised when ProjectX bar data cannot be normalized safely."""


class ProjectXStaleDataError(ProjectXDataError):
    """Raised when the latest completed bar is too old for live analysis."""


@dataclass(frozen=True)
class ProjectXCredentials:
    username: str
    api_key: str


@dataclass(frozen=True)
class ContractSelection:
    contract_id: str
    name: str
    description: str | None
    active: bool | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class FreshnessResult:
    fresh: bool
    reference_time: datetime
    last_bar: datetime
    age_seconds: float
    maximum_age_seconds: float
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["reference_time"] = self.reference_time.isoformat()
        result["last_bar"] = self.last_bar.isoformat()
        return result


RequestFunction = Callable[..., dict[str, Any]]
SleepFunction = Callable[[float], None]


def load_simple_env(path: str | Path = Path(".env")) -> None:
    """Load simple KEY=VALUE pairs without overriding existing environment values."""
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def credentials_from_environment() -> ProjectXCredentials:
    """Resolve preferred PROJECTX names with legacy TOPSTEP aliases."""
    username = os.getenv("PROJECTX_USERNAME") or os.getenv("TOPSTEP_USERNAME")
    api_key = os.getenv("PROJECTX_API_KEY") or os.getenv("TOPSTEP_API_KEY")
    if not username or not api_key:
        raise ProjectXAuthenticationError(
            "Missing ProjectX credentials. Set PROJECTX_USERNAME and "
            "PROJECTX_API_KEY (legacy TOPSTEP_USERNAME/TOPSTEP_API_KEY are also supported)."
        )
    return ProjectXCredentials(username=username, api_key=api_key)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc_datetime(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware.")
    return value.astimezone(timezone.utc)


def parse_datetime_utc(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(
            f"Invalid datetime {value!r}. Use ISO format, e.g. 2026-08-01T00:00:00Z."
        ) from exc
    if parsed.tzinfo is None:
        raise ValueError(f"Datetime {value!r} must include a timezone or Z suffix.")
    return parsed.astimezone(timezone.utc)


def format_api_datetime(value: datetime) -> str:
    return as_utc_datetime(value, field_name="API datetime").isoformat().replace(
        "+00:00", "Z"
    )


def _api_error_message(endpoint: str, data: dict[str, Any]) -> str:
    message = data.get("errorMessage") or data.get("message") or "Unknown error"
    return f"ProjectX API error for {endpoint}: {message} (code={data.get('errorCode')})"


def http_post_json(
    endpoint: str,
    payload: dict[str, Any],
    *,
    token: str | None = None,
    base_url: str = DEFAULT_API_BASE_URL,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    sleep_func: SleepFunction = time.sleep,
) -> dict[str, Any]:
    """POST JSON to ProjectX with bounded retries and safe error messages."""
    if max_retries < 1:
        raise ValueError("max_retries must be at least 1.")

    url = f"{base_url.rstrip('/')}{endpoint}"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "trade-alerts-projectx-market-data/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request_body = json.dumps(payload).encode("utf-8")

    for attempt in range(1, max_retries + 1):
        request = Request(url, data=request_body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
            data = json.loads(body)
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            retryable = exc.code == 429 or 500 <= exc.code < 600
            if retryable and attempt < max_retries:
                sleep_func(float(min(2**attempt, 30)))
                continue
            raise ProjectXHTTPError(
                f"ProjectX HTTP {exc.code} for {endpoint}: {error_body[:1000]}",
                status_code=exc.code,
            ) from exc
        except URLError as exc:
            if attempt < max_retries:
                sleep_func(float(min(2**attempt, 30)))
                continue
            raise ProjectXError(
                f"Could not reach ProjectX endpoint {endpoint}: {exc.reason}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise ProjectXError(f"ProjectX returned invalid JSON for {endpoint}.") from exc

        if not isinstance(data, dict):
            raise ProjectXError(
                f"Unexpected ProjectX response type for {endpoint}: {type(data).__name__}"
            )
        if data.get("success") is False:
            raise ProjectXAPIError(
                _api_error_message(endpoint, data), error_code=data.get("errorCode")
            )
        return data

    raise ProjectXError(f"ProjectX request failed after {max_retries} attempts.")


def _looks_like_contract(contract: dict[str, Any], symbol: str) -> bool:
    name = str(contract.get("name") or "").upper().strip()
    description = str(contract.get("description") or "").upper()
    symbol_id = str(contract.get("symbolId") or "").upper()
    symbol = symbol.upper().strip()

    if symbol == "NQ":
        return (
            bool(re.match(r"^NQ[A-Z]\d{1,2}$", name))
            or symbol_id.endswith(".ENQ")
            or "E-MINI NASDAQ-100" in description
        )
    if symbol == "MNQ":
        return (
            bool(re.match(r"^MNQ[A-Z]\d{1,2}$", name))
            or symbol_id.endswith(".MNQ")
            or "MICRO E-MINI NASDAQ-100" in description
        )
    return name.startswith(symbol)


def choose_contract(
    contracts: list[dict[str, Any]],
    *,
    symbol: str,
    contract_name: str | None = None,
) -> ContractSelection:
    """Select an explicit contract or the single active symbol contract."""
    if not contracts:
        raise ProjectXDataError("ProjectX contract search returned zero contracts.")

    if contract_name:
        wanted = contract_name.upper().strip()
        candidates = [
            contract
            for contract in contracts
            if str(contract.get("name") or "").upper().strip() == wanted
        ]
    else:
        candidates = [
            contract for contract in contracts if _looks_like_contract(contract, symbol)
        ]
        active = [contract for contract in candidates if bool(contract.get("activeContract"))]
        if len(active) == 1:
            candidates = active

    if len(candidates) != 1:
        names = ", ".join(
            str(contract.get("name") or contract.get("id") or "unknown")
            for contract in contracts
        )
        if not candidates:
            raise ProjectXDataError(
                f"Could not resolve {contract_name or symbol!r}. Returned: {names}"
            )
        raise ProjectXDataError(
            f"Multiple contracts matched {contract_name or symbol!r}: {names}. "
            "Specify --contract-name or --contract-id."
        )

    selected = candidates[0]
    contract_id = str(selected.get("id") or "").strip()
    if not contract_id:
        raise ProjectXDataError("Selected ProjectX contract does not contain an ID.")
    name = str(selected.get("name") or contract_id).strip()
    active_value = selected.get("activeContract")
    return ContractSelection(
        contract_id=contract_id,
        name=name,
        description=(
            str(selected.get("description")) if selected.get("description") else None
        ),
        active=bool(active_value) if active_value is not None else None,
        raw=dict(selected),
    )


def _duplicate_conflicts(dataframe: pd.DataFrame) -> list[pd.Timestamp]:
    duplicates = dataframe.loc[
        dataframe.duplicated(subset=["timestamp"], keep=False)
    ]
    conflicts: list[pd.Timestamp] = []
    for timestamp, rows in duplicates.groupby("timestamp", sort=False):
        if len(rows.loc[:, BAR_VALUE_COLUMNS].drop_duplicates()) > 1:
            conflicts.append(timestamp)
    return conflicts


def normalize_bars(
    bars: list[dict[str, Any]],
    *,
    symbol: str,
    contract_label: str,
    contract_id: str | None = None,
) -> pd.DataFrame:
    """Normalize ProjectX t/o/h/l/c/v bars and reject ambiguous data."""
    if not bars:
        raise ProjectXDataError("ProjectX returned zero historical bars.")

    rows = [
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
            "contract_id": contract_id,
        }
        for bar in bars
    ]
    dataframe = pd.DataFrame(rows)

    try:
        dataframe["timestamp"] = pd.to_datetime(
            dataframe["timestamp"], errors="raise", utc=True
        )
        for column in BAR_VALUE_COLUMNS:
            dataframe[column] = pd.to_numeric(dataframe[column], errors="raise")
    except (TypeError, ValueError) as exc:
        raise ProjectXDataError(f"ProjectX returned an invalid bar value: {exc}") from exc

    if dataframe.loc[:, REQUIRED_BAR_COLUMNS].isna().any().any():
        raise ProjectXDataError("ProjectX returned missing OHLCV bar values.")

    conflicts = _duplicate_conflicts(dataframe)
    if conflicts:
        examples = ", ".join(str(value) for value in conflicts[:3])
        raise ProjectXDataError(
            f"Conflicting duplicate ProjectX timestamps detected: {examples}"
        )

    dataframe = (
        dataframe.drop_duplicates(subset=["timestamp"], keep="last")
        .sort_values("timestamp", kind="stable")
        .reset_index(drop=True)
    )

    invalid_ohlc = (
        (dataframe["high"] < dataframe[["open", "close", "low"]].max(axis=1))
        | (dataframe["low"] > dataframe[["open", "close", "high"]].min(axis=1))
        | (dataframe["high"] < dataframe["low"])
    )
    if invalid_ohlc.any():
        raise ProjectXDataError("ProjectX data contains invalid OHLC relationships.")
    if (dataframe[["open", "high", "low", "close"]] <= 0).any().any():
        raise ProjectXDataError("ProjectX returned zero or negative prices.")
    if (dataframe["volume"] < 0).any():
        raise ProjectXDataError("ProjectX returned negative volume.")

    return dataframe


def assess_bar_freshness(
    dataframe: pd.DataFrame,
    *,
    reference_time: datetime,
    maximum_age: timedelta,
    maximum_future_skew: timedelta = timedelta(minutes=1),
) -> FreshnessResult:
    if dataframe.empty or "timestamp" not in dataframe.columns:
        raise ProjectXDataError("Cannot assess freshness without timestamped bars.")
    if maximum_age.total_seconds() < 0:
        raise ValueError("maximum_age cannot be negative.")

    reference = as_utc_datetime(reference_time, field_name="reference_time")
    last_timestamp = pd.Timestamp(dataframe["timestamp"].max())
    if last_timestamp.tzinfo is None:
        raise ProjectXDataError("ProjectX bar timestamps must be timezone-aware.")
    last_bar = last_timestamp.to_pydatetime().astimezone(timezone.utc)
    age_seconds = (reference - last_bar).total_seconds()
    maximum_age_seconds = maximum_age.total_seconds()

    reason: str | None = None
    if age_seconds < -maximum_future_skew.total_seconds():
        reason = "latest_bar_is_in_the_future"
    elif age_seconds > maximum_age_seconds:
        reason = "latest_bar_is_stale"

    return FreshnessResult(
        fresh=reason is None,
        reference_time=reference,
        last_bar=last_bar,
        age_seconds=float(age_seconds),
        maximum_age_seconds=float(maximum_age_seconds),
        reason=reason,
    )


def save_csv(dataframe: pd.DataFrame, output_path: str | Path) -> Path:
    """Backward-compatible CSV output used by the historical CLI."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    result = dataframe.copy()
    result["timestamp"] = result["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    result.to_csv(path, index=False)
    return path


class ProjectXClient:
    """Read-only ProjectX client for contract discovery and completed bars."""

    def __init__(
        self,
        *,
        username: str,
        api_key: str,
        base_url: str = DEFAULT_API_BASE_URL,
        live: bool = False,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        requester: RequestFunction = http_post_json,
        sleep_func: SleepFunction = time.sleep,
    ) -> None:
        if not username or not api_key:
            raise ProjectXAuthenticationError("ProjectX username and API key are required.")
        self.username = username
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.live = bool(live)
        self.timeout = int(timeout)
        self.max_retries = int(max_retries)
        self._requester = requester
        self._sleep = sleep_func
        self._token: str | None = None
        self.history_request_count = 0

    def _post(
        self,
        endpoint: str,
        payload: dict[str, Any],
        *,
        token: str | None = None,
    ) -> dict[str, Any]:
        return self._requester(
            endpoint,
            payload,
            token=token,
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=self.max_retries,
            sleep_func=self._sleep,
        )

    def authenticate(self, *, force: bool = False) -> str:
        if self._token and not force:
            return self._token
        try:
            response = self._post(
                AUTH_ENDPOINT,
                {"userName": self.username, "apiKey": self._api_key},
            )
        except ProjectXError as exc:
            raise ProjectXAuthenticationError(f"ProjectX authentication failed: {exc}") from exc
        token = response.get("token")
        if not response.get("success") or not token:
            raise ProjectXAuthenticationError(
                "ProjectX authentication failed or returned no session token."
            )
        self._token = str(token)
        return self._token

    def _authorized_post(
        self, endpoint: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        token = self.authenticate()
        try:
            return self._post(endpoint, payload, token=token)
        except ProjectXHTTPError as exc:
            if exc.status_code not in {401, 403}:
                raise
        except ProjectXAPIError as exc:
            if str(exc.error_code) not in {"401", "403"}:
                raise

        refreshed = self.authenticate(force=True)
        return self._post(endpoint, payload, token=refreshed)

    def search_contracts(self, *, search_text: str) -> list[dict[str, Any]]:
        response = self._authorized_post(
            CONTRACT_SEARCH_ENDPOINT,
            {"searchText": search_text.upper(), "live": self.live},
        )
        contracts = response.get("contracts")
        if not isinstance(contracts, list):
            raise ProjectXDataError("Contract search did not return a contracts list.")
        return [item for item in contracts if isinstance(item, dict)]

    def resolve_contract(
        self,
        *,
        symbol: str,
        contract_name: str | None = None,
        contract_id: str | None = None,
    ) -> ContractSelection:
        if contract_id:
            label = contract_name or contract_id
            return ContractSelection(
                contract_id=contract_id,
                name=label,
                description=None,
                active=None,
                raw={"id": contract_id, "name": label},
            )
        return choose_contract(
            self.search_contracts(search_text=symbol),
            symbol=symbol,
            contract_name=contract_name,
        )

    def retrieve_bars(
        self,
        *,
        contract_id: str,
        start_time: datetime,
        end_time: datetime,
        chunk_days: int = DEFAULT_CHUNK_DAYS,
        request_delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS,
    ) -> list[dict[str, Any]]:
        start = as_utc_datetime(start_time, field_name="start_time")
        end = as_utc_datetime(end_time, field_name="end_time")
        if start >= end:
            raise ValueError("start_time must be earlier than end_time.")
        if chunk_days <= 0:
            raise ValueError("chunk_days must be positive.")
        if request_delay_seconds < 0:
            raise ValueError("request_delay_seconds cannot be negative.")

        all_bars: list[dict[str, Any]] = []
        cursor = start
        self.history_request_count = 0
        while cursor < end:
            chunk_end = min(cursor + timedelta(days=chunk_days), end)
            self.history_request_count += 1
            response = self._authorized_post(
                HISTORY_ENDPOINT,
                {
                    "contractId": contract_id,
                    "live": self.live,
                    "startTime": format_api_datetime(cursor),
                    "endTime": format_api_datetime(chunk_end),
                    "unit": 2,
                    "unitNumber": 1,
                    "limit": MAX_BARS_PER_REQUEST,
                    "includePartialBar": False,
                },
            )
            bars = response.get("bars")
            if not isinstance(bars, list):
                raise ProjectXDataError("Historical response did not contain a bars list.")
            all_bars.extend(bar for bar in bars if isinstance(bar, dict))

            cursor = chunk_end
            if cursor < end and request_delay_seconds > 0:
                self._sleep(request_delay_seconds)

        return all_bars

    def fetch_bars(
        self,
        *,
        symbol: str,
        contract: ContractSelection,
        start_time: datetime,
        end_time: datetime,
        chunk_days: int = DEFAULT_CHUNK_DAYS,
        request_delay_seconds: float = DEFAULT_REQUEST_DELAY_SECONDS,
    ) -> pd.DataFrame:
        bars = self.retrieve_bars(
            contract_id=contract.contract_id,
            start_time=start_time,
            end_time=end_time,
            chunk_days=chunk_days,
            request_delay_seconds=request_delay_seconds,
        )
        return normalize_bars(
            bars,
            symbol=symbol,
            contract_label=contract.name,
            contract_id=contract.contract_id,
        )
