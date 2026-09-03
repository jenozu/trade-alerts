from __future__ import annotations

import argparse
from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import sys
from typing import Any
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIRECTORY = PROJECT_ROOT / "src"
if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))

from projectx_client import (  # noqa: E402
    DEFAULT_API_BASE_URL,
    DEFAULT_CHUNK_DAYS,
    DEFAULT_REQUEST_DELAY_SECONDS,
    ContractSelection,
    FreshnessResult,
    ProjectXClient,
    ProjectXDataError,
    ProjectXError,
    ProjectXStaleDataError,
    assess_bar_freshness,
    credentials_from_environment,
    format_api_datetime,
    load_simple_env,
    parse_datetime_utc,
    utc_now,
)
from sessions import SessionError, load_sessions_config  # noqa: E402
from validate_data import (  # noqa: E402
    STATUS_NO_ANALYSIS,
    AnalysisStatus,
    ValidationReport,
    allowed_warnings_from_validation_config,
    classify_analysis_status,
    validate_market_data,
)


DEFAULT_SYMBOL = "MNQ"
DEFAULT_HISTORY_DAYS = 30
DEFAULT_MAX_STALE_MINUTES = 5.0
DEFAULT_TIMEZONE = "America/New_York"


@dataclass(frozen=True)
class CollectionArtifacts:
    parquet_path: Path
    metadata_path: Path
    rows: int
    first_bar: datetime
    last_bar: datetime


def _argument_datetime(value: str) -> datetime:
    try:
        return parse_datetime_utc(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _environment_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false, not {value!r}.")


def default_data_directory() -> Path:
    configured = os.getenv("DATA_DIR")
    return Path(configured) if configured else PROJECT_ROOT / "data"


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Collect completed, read-only MNQ one-minute bars from ProjectX, "
            "validate them, and save a timestamped snapshot."
        )
    )
    parser.add_argument("--symbol", default=os.getenv("PROJECTX_SYMBOL", DEFAULT_SYMBOL))
    parser.add_argument(
        "--days",
        type=int,
        default=int(os.getenv("PROJECTX_HISTORY_DAYS", DEFAULT_HISTORY_DAYS)),
        help="History window when --start is omitted. Default: 30 days",
    )
    parser.add_argument("--start", type=_argument_datetime, default=None)
    parser.add_argument("--end", type=_argument_datetime, default=None)
    parser.add_argument(
        "--contract-id",
        default=None,
        help="Exact ID; otherwise PROJECTX_CONTRACT_ID or active-contract search is used.",
    )
    parser.add_argument("--contract-name", default=None)
    parser.add_argument(
        "--live",
        action=argparse.BooleanOptionalAction,
        default=_environment_bool("PROJECTX_LIVE", False),
        help="Use live-data contract/history lookup. Default comes from PROJECTX_LIVE.",
    )
    parser.add_argument(
        "--chunk-days",
        type=int,
        default=int(os.getenv("PROJECTX_CHUNK_DAYS", DEFAULT_CHUNK_DAYS)),
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=float(
            os.getenv("PROJECTX_REQUEST_DELAY_SECONDS", DEFAULT_REQUEST_DELAY_SECONDS)
        ),
    )
    parser.add_argument(
        "--max-stale-minutes",
        type=float,
        default=float(
            os.getenv("PROJECTX_MAX_STALE_MINUTES", DEFAULT_MAX_STALE_MINUTES)
        ),
    )
    parser.add_argument(
        "--skip-freshness-check",
        action="store_true",
        help="Use only for intentional historical backfills, never the morning job.",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=None,
        help="Default: DATA_DIR/raw/projectx or ./data/raw/projectx",
    )
    return parser.parse_args(argv)


def validate_arguments(args: argparse.Namespace) -> None:
    if args.days <= 0:
        raise ValueError("--days must be greater than zero.")
    if args.chunk_days <= 0:
        raise ValueError("--chunk-days must be greater than zero.")
    if args.delay < 0:
        raise ValueError("--delay cannot be negative.")
    if args.max_stale_minutes < 0:
        raise ValueError("--max-stale-minutes cannot be negative.")
    if args.contract_id and args.contract_name:
        raise ValueError("Use either --contract-id or --contract-name, not both.")
    if args.skip_freshness_check and args.live:
        raise ValueError(
            "--skip-freshness-check is only for intentional historical "
            "backfills; the live/morning job must always enforce freshness."
        )


def _allowed_warning_categories_from_config() -> frozenset[str]:
    """Allowed warning categories from the sessions.yaml ``validation`` block.

    This is a best-effort policy read for snapshot metadata only: if the
    config is absent or malformed the collector falls back to the strict
    default (no allowed categories) and still takes the snapshot.
    """
    path = PROJECT_ROOT / "config" / "sessions.yaml"
    if not path.exists():
        return frozenset()
    try:
        config = load_sessions_config(path)
    except (SessionError, OSError, ValueError):
        return frozenset()
    return allowed_warnings_from_validation_config(config)


def build_snapshot_paths(
    *,
    output_directory: Path,
    symbol: str,
    collected_at: datetime,
    timezone_name: str,
) -> tuple[Path, Path]:
    local_time = collected_at.astimezone(ZoneInfo(timezone_name))
    prefix = f"{local_time:%Y-%m-%d_%H%M}_{symbol.lower()}_1m"
    return (
        output_directory / f"{prefix}.parquet",
        output_directory / f"{prefix}_metadata.json",
    )


def _atomic_save_parquet(dataframe, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    dataframe.to_parquet(temporary, index=False)
    temporary.replace(path)


def _atomic_save_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, default=str)
        file.write("\n")
    temporary.replace(path)


def _contract_metadata(contract: ContractSelection) -> dict[str, Any]:
    return {
        "id": contract.contract_id,
        "name": contract.name,
        "description": contract.description,
        "active": contract.active,
    }


def _status_label(
    validation: ValidationReport,
    freshness: FreshnessResult | None,
    allowed_warning_categories: Collection[str],
) -> str:
    """Deterministic snapshot status: PASS / DEGRADED / FAIL.

    FAIL keeps the historical meaning (validation errors or stale data: no
    analysis downstream). DEGRADED is new: usable history with material
    warnings that are not explicitly allowed by configuration.
    """
    if not validation.passed:
        return "FAIL"
    if freshness is not None and not freshness.fresh:
        return "FAIL"
    status = classify_analysis_status(
        validation,
        allowed_warning_categories=allowed_warning_categories,
    ).status
    if status == STATUS_NO_ANALYSIS:
        return "FAIL"
    return status.upper()


def build_metadata(
    *,
    collected_at: datetime,
    start_time: datetime,
    end_time: datetime,
    symbol: str,
    live: bool,
    contract: ContractSelection,
    dataframe,
    validation: ValidationReport,
    freshness: FreshnessResult | None,
    freshness_check_skipped: bool,
    history_request_count: int | None,
    chunk_days: int,
    request_delay_seconds: float,
    allowed_warning_categories: Collection[str] = (),
) -> dict[str, Any]:
    first_bar = dataframe["timestamp"].min()
    last_bar = dataframe["timestamp"].max()
    analysis = classify_analysis_status(
        validation,
        allowed_warning_categories=allowed_warning_categories,
    )
    if freshness is not None and not freshness.fresh:
        # Fatal stale live data is no_analysis regardless of the validation
        # result: the collector refuses the snapshot (ProjectXStaleDataError)
        # and the metadata must not contradict that by claiming analysis is
        # fine. Mirrors _status_label FAIL and the collector exception; the
        # configured freshness threshold is untouched.
        detail = freshness.reason or "latest bar exceeds the maximum age"
        reason = (
            f"freshness: {detail} (last bar {freshness.last_bar.isoformat()}, "
            f"age {freshness.age_seconds / 60.0:.1f} minutes)"
        )
        analysis = AnalysisStatus(STATUS_NO_ANALYSIS, (reason,))
    return {
        "status": _status_label(
            validation, freshness, allowed_warning_categories
        ),
        "analysis_status": analysis.status,
        "analysis_reasons": list(analysis.reasons),
        "collected_at": collected_at.isoformat(),
        "requested_start": start_time.isoformat(),
        "requested_end": end_time.isoformat(),
        "symbol": symbol.upper(),
        "source": "PROJECTX",
        "live": live,
        "contract": _contract_metadata(contract),
        "history_request_count": history_request_count,
        "chunk_days": chunk_days,
        "request_delay_seconds": request_delay_seconds,
        "bar_count": int(len(dataframe)),
        "first_bar": first_bar.isoformat(),
        "last_bar": last_bar.isoformat(),
        "timezone": str(dataframe["timestamp"].dt.tz),
        "validation": validation.to_dict(),
        "freshness_check_skipped": freshness_check_skipped,
        "freshness": freshness.to_dict() if freshness else None,
    }


def collect(
    args: argparse.Namespace,
    *,
    client_factory=ProjectXClient,
    now_func=utc_now,
) -> CollectionArtifacts:
    validate_arguments(args)
    load_simple_env(PROJECT_ROOT / ".env")
    credentials = credentials_from_environment()

    collected_at = now_func()
    end_time = args.end or collected_at
    start_time = args.start or (end_time - timedelta(days=args.days))
    if start_time >= end_time:
        raise ValueError("Start time must be earlier than end time.")

    client = client_factory(
        username=credentials.username,
        api_key=credentials.api_key,
        base_url=os.getenv("PROJECTX_BASE_URL", DEFAULT_API_BASE_URL),
        live=args.live,
    )

    print("ProjectX authentication: starting")
    client.authenticate()
    print("ProjectX authentication: OK")

    configured_contract_id = args.contract_id
    if configured_contract_id is None and args.contract_name is None:
        configured_contract_id = os.getenv("PROJECTX_CONTRACT_ID") or None

    contract = client.resolve_contract(
        symbol=args.symbol,
        contract_name=args.contract_name,
        contract_id=configured_contract_id,
    )
    print(f"Contract: {contract.name} ({contract.contract_id})")
    print(
        "Request: "
        f"{format_api_datetime(start_time)} -> {format_api_datetime(end_time)} "
        f"live={str(args.live).lower()}"
    )

    dataframe = client.fetch_bars(
        symbol=args.symbol,
        contract=contract,
        start_time=start_time,
        end_time=end_time,
        chunk_days=args.chunk_days,
        request_delay_seconds=args.delay,
    )
    validation = validate_market_data(
        dataframe,
        tick_size=0.25,
        expected_interval_minutes=1,
        large_gap_points=100.0,
    )

    freshness: FreshnessResult | None = None
    if not args.skip_freshness_check:
        freshness = assess_bar_freshness(
            dataframe,
            reference_time=end_time,
            maximum_age=timedelta(minutes=args.max_stale_minutes),
        )

    timezone_name = os.getenv("APP_TIMEZONE", DEFAULT_TIMEZONE)
    output_directory = args.output_directory or (
        default_data_directory() / "raw" / "projectx"
    )
    parquet_path, metadata_path = build_snapshot_paths(
        output_directory=output_directory,
        symbol=args.symbol,
        collected_at=collected_at,
        timezone_name=timezone_name,
    )
    metadata = build_metadata(
        collected_at=collected_at,
        start_time=start_time,
        end_time=end_time,
        symbol=args.symbol,
        live=args.live,
        contract=contract,
        dataframe=dataframe,
        validation=validation,
        freshness=freshness,
        freshness_check_skipped=args.skip_freshness_check,
        history_request_count=getattr(client, "history_request_count", None),
        chunk_days=args.chunk_days,
        request_delay_seconds=args.delay,
        allowed_warning_categories=_allowed_warning_categories_from_config(),
    )
    _atomic_save_parquet(dataframe, parquet_path)
    _atomic_save_json(metadata, metadata_path)

    print(f"1m bars: {len(dataframe):,}")
    print(f"Last bar: {dataframe['timestamp'].max()}")
    print(f"Validation: {'PASS' if validation.passed else 'FAIL'}")
    print(f"Saved: {parquet_path}")
    print(f"Metadata: {metadata_path}")

    if not validation.passed:
        raise ProjectXDataError(
            f"ProjectX snapshot failed validation; see {metadata_path}."
        )
    if freshness is not None and not freshness.fresh:
        raise ProjectXStaleDataError(
            f"{freshness.reason}: last bar {freshness.last_bar.isoformat()}, "
            f"age {freshness.age_seconds / 60.0:.1f} minutes."
        )

    return CollectionArtifacts(
        parquet_path=parquet_path,
        metadata_path=metadata_path,
        rows=int(len(dataframe)),
        first_bar=dataframe["timestamp"].min().to_pydatetime(),
        last_bar=dataframe["timestamp"].max().to_pydatetime(),
    )


def main(argv: list[str] | None = None) -> None:
    try:
        # Load before argument parsing so non-secret .env defaults such as
        # PROJECTX_LIVE and DATA_DIR are honored as well as credentials.
        load_simple_env(PROJECT_ROOT / ".env")
        collect(parse_arguments(argv))
    except ProjectXStaleDataError as exc:
        print(f"NO ANALYSIS — STALE MARKET DATA: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    except (ProjectXError, ValueError, OSError) as exc:
        print(f"NO ANALYSIS — PROJECTX DATA UNAVAILABLE: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
