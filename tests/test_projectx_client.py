from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
from pathlib import Path
from urllib.error import HTTPError

import pandas as pd
import pytest

import projectx_client
import scripts.collect_projectx as collector_script
from projectx_client import (
    AUTH_ENDPOINT,
    CONTRACT_SEARCH_ENDPOINT,
    HISTORY_ENDPOINT,
    ContractSelection,
    ProjectXClient,
    ProjectXDataError,
    ProjectXHTTPError,
    assess_bar_freshness,
    choose_contract,
    credentials_from_environment,
    http_post_json,
    normalize_bars,
    parse_datetime_utc,
)
from scripts.collect_projectx import (
    build_metadata,
    build_snapshot_paths,
    collect,
    main as collector_main,
    parse_arguments,
    validate_arguments,
)
from validate_data import ValidationReport


def _bar(
    timestamp: str,
    *,
    open_: float = 20_000.0,
    high: float = 20_002.0,
    low: float = 19_999.0,
    close: float = 20_001.0,
    volume: float = 100.0,
) -> dict:
    return {
        "t": timestamp,
        "o": open_,
        "h": high,
        "l": low,
        "c": close,
        "v": volume,
    }


def _normalized_bars(*timestamps: str) -> pd.DataFrame:
    return normalize_bars(
        [_bar(timestamp) for timestamp in timestamps],
        symbol="MNQ",
        contract_label="MNQU6",
        contract_id="CON.F.US.MNQ.U26",
    )


def test_credentials_prefer_projectx_names(monkeypatch):
    monkeypatch.setenv("PROJECTX_USERNAME", "projectx-user")
    monkeypatch.setenv("PROJECTX_API_KEY", "projectx-key")
    monkeypatch.setenv("TOPSTEP_USERNAME", "legacy-user")
    monkeypatch.setenv("TOPSTEP_API_KEY", "legacy-key")

    credentials = credentials_from_environment()

    assert credentials.username == "projectx-user"
    assert credentials.api_key == "projectx-key"


def test_credentials_support_legacy_topstep_names(monkeypatch):
    monkeypatch.delenv("PROJECTX_USERNAME", raising=False)
    monkeypatch.delenv("PROJECTX_API_KEY", raising=False)
    monkeypatch.setenv("TOPSTEP_USERNAME", "legacy-user")
    monkeypatch.setenv("TOPSTEP_API_KEY", "legacy-key")

    credentials = credentials_from_environment()

    assert credentials.username == "legacy-user"
    assert credentials.api_key == "legacy-key"


def test_datetime_parser_requires_explicit_timezone():
    with pytest.raises(ValueError, match="timezone"):
        parse_datetime_utc("2026-09-02T08:58:00")


def test_normalize_bars_maps_schema_sorts_and_preserves_contract():
    dataframe = normalize_bars(
        [
            _bar("2026-09-02T12:58:00Z", volume=102),
            _bar("2026-09-02T12:57:00Z", volume=101),
        ],
        symbol="mnq",
        contract_label="MNQU6",
        contract_id="contract-1",
    )

    assert list(dataframe.columns) == [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "source",
        "symbol",
        "contract",
        "contract_id",
    ]
    assert dataframe["timestamp"].is_monotonic_increasing
    assert str(dataframe["timestamp"].dt.tz) == "UTC"
    assert dataframe["symbol"].unique().tolist() == ["MNQ"]
    assert dataframe["contract_id"].unique().tolist() == ["contract-1"]


def test_normalize_bars_collapses_identical_chunk_overlap():
    bar = _bar("2026-09-02T12:57:00Z")
    dataframe = normalize_bars(
        [bar, dict(bar)], symbol="MNQ", contract_label="MNQU6"
    )
    assert len(dataframe) == 1


def test_normalize_bars_rejects_conflicting_duplicate_timestamp():
    first = _bar("2026-09-02T12:57:00Z", close=20_001.0)
    second = _bar("2026-09-02T12:57:00Z", close=20_001.5)
    with pytest.raises(ProjectXDataError, match="Conflicting duplicate"):
        normalize_bars([first, second], symbol="MNQ", contract_label="MNQU6")


@pytest.mark.parametrize(
    "bar, message",
    [
        (_bar("2026-09-02T12:57:00Z", high=19_999.5), "OHLC"),
        (_bar("2026-09-02T12:57:00Z", volume=-1), "negative volume"),
        (
            _bar(
                "2026-09-02T12:57:00Z",
                open_=0,
                high=2,
                low=0,
                close=1,
            ),
            "zero or negative prices",
        ),
    ],
)
def test_normalize_bars_rejects_invalid_market_data(bar, message):
    with pytest.raises(ProjectXDataError, match=message):
        normalize_bars([bar], symbol="MNQ", contract_label="MNQU6")


def test_normalize_bars_rejects_zero_bars():
    with pytest.raises(ProjectXDataError, match="zero historical bars"):
        normalize_bars([], symbol="MNQ", contract_label="MNQU6")


def test_choose_contract_selects_single_active_mnq_contract():
    selected = choose_contract(
        [
            {"id": "old", "name": "MNQM6", "activeContract": False},
            {
                "id": "current",
                "name": "MNQU6",
                "activeContract": True,
                "description": "Micro E-mini Nasdaq-100",
            },
        ],
        symbol="MNQ",
    )
    assert selected.contract_id == "current"
    assert selected.name == "MNQU6"
    assert selected.active is True


def test_choose_contract_honors_explicit_contract_name():
    selected = choose_contract(
        [
            {"id": "june", "name": "MNQM6"},
            {"id": "september", "name": "MNQU6"},
        ],
        symbol="MNQ",
        contract_name="mnqm6",
    )
    assert selected.contract_id == "june"


def test_choose_contract_rejects_ambiguous_contracts():
    with pytest.raises(ProjectXDataError, match="Multiple contracts"):
        choose_contract(
            [
                {"id": "one", "name": "MNQM6"},
                {"id": "two", "name": "MNQU6"},
            ],
            symbol="MNQ",
        )


def test_projectx_client_uses_proven_auth_and_history_payloads():
    calls: list[tuple[str, dict, str | None]] = []
    sleeps: list[float] = []

    def requester(endpoint, payload, *, token=None, **_kwargs):
        calls.append((endpoint, payload, token))
        if endpoint == AUTH_ENDPOINT:
            return {"success": True, "token": "token-1"}
        if endpoint == HISTORY_ENDPOINT:
            return {"success": True, "bars": []}
        raise AssertionError(endpoint)

    client = ProjectXClient(
        username="user",
        api_key="key",
        live=True,
        requester=requester,
        sleep_func=sleeps.append,
    )
    client.retrieve_bars(
        contract_id="contract-1",
        start_time=datetime(2026, 8, 1, tzinfo=timezone.utc),
        end_time=datetime(2026, 8, 22, tzinfo=timezone.utc),
        chunk_days=10,
        request_delay_seconds=0.8,
    )

    assert calls[0][0] == AUTH_ENDPOINT
    assert calls[0][1] == {"userName": "user", "apiKey": "key"}
    history_calls = [call for call in calls if call[0] == HISTORY_ENDPOINT]
    assert len(history_calls) == 3
    assert sleeps == [0.8, 0.8]
    for _, payload, token in history_calls:
        assert token == "token-1"
        assert payload["contractId"] == "contract-1"
        assert payload["live"] is True
        assert payload["unit"] == 2
        assert payload["unitNumber"] == 1
        assert payload["limit"] == 20_000
        assert payload["includePartialBar"] is False
    assert client.history_request_count == 3


def test_projectx_client_refreshes_expired_token_once():
    authentication_count = 0
    search_tokens: list[str] = []

    def requester(endpoint, payload, *, token=None, **_kwargs):
        nonlocal authentication_count
        if endpoint == AUTH_ENDPOINT:
            authentication_count += 1
            return {"success": True, "token": f"token-{authentication_count}"}
        if endpoint == CONTRACT_SEARCH_ENDPOINT:
            search_tokens.append(token)
            if token == "token-1":
                raise ProjectXHTTPError("expired", status_code=401)
            return {"success": True, "contracts": []}
        raise AssertionError(endpoint)

    client = ProjectXClient(username="user", api_key="key", requester=requester)
    assert client.search_contracts(search_text="MNQ") == []
    assert authentication_count == 2
    assert search_tokens == ["token-1", "token-2"]


def test_assess_bar_freshness_passes_recent_bar_and_rejects_stale_bar():
    dataframe = _normalized_bars("2026-09-02T12:57:00Z")
    recent = assess_bar_freshness(
        dataframe,
        reference_time=datetime(2026, 9, 2, 12, 58, tzinfo=timezone.utc),
        maximum_age=timedelta(minutes=5),
    )
    stale = assess_bar_freshness(
        dataframe,
        reference_time=datetime(2026, 9, 2, 13, 8, tzinfo=timezone.utc),
        maximum_age=timedelta(minutes=5),
    )
    assert recent.fresh is True
    assert stale.fresh is False
    assert stale.reason == "latest_bar_is_stale"


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_http_post_json_retries_rate_limit(monkeypatch):
    calls = 0
    sleeps: list[float] = []

    def fake_urlopen(_request, timeout):
        nonlocal calls
        calls += 1
        assert timeout == 30
        if calls == 1:
            raise HTTPError(
                "https://api.topstepx.com/test",
                429,
                "rate limited",
                hdrs=None,
                fp=BytesIO(b"rate limited"),
            )
        return _FakeResponse({"success": True, "value": 1})

    monkeypatch.setattr(projectx_client, "urlopen", fake_urlopen)
    result = http_post_json(
        "/test", {}, max_retries=2, sleep_func=sleeps.append
    )
    assert result["value"] == 1
    assert calls == 2
    assert sleeps == [2.0]


def test_snapshot_paths_use_configured_eastern_time():
    parquet, metadata = build_snapshot_paths(
        output_directory=Path("data/raw/projectx"),
        symbol="MNQ",
        collected_at=datetime(2026, 9, 2, 12, 58, tzinfo=timezone.utc),
        timezone_name="America/New_York",
    )
    assert parquet.name == "2026-09-02_0858_mnq_1m.parquet"
    assert metadata.name == "2026-09-02_0858_mnq_1m_metadata.json"


def test_collector_saves_timestamped_parquet_and_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECTX_USERNAME", "user")
    monkeypatch.setenv("PROJECTX_API_KEY", "key")
    monkeypatch.setenv("APP_TIMEZONE", "America/New_York")
    reference = datetime(2026, 9, 2, 12, 58, tzinfo=timezone.utc)
    dataframe = _normalized_bars(
        "2026-09-02T12:55:00Z",
        "2026-09-02T12:56:00Z",
        "2026-09-02T12:57:00Z",
    )

    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["live"] is True
            self.history_request_count = 1

        def authenticate(self):
            return "token"

        def resolve_contract(self, **_kwargs):
            return ContractSelection(
                contract_id="contract-1",
                name="MNQU6",
                description="Micro E-mini Nasdaq-100",
                active=True,
                raw={},
            )

        def fetch_bars(self, **_kwargs):
            return dataframe

    args = parse_arguments(
        [
            "--live",
            "--days",
            "1",
            "--output-directory",
            str(tmp_path),
        ]
    )
    artifacts = collect(
        args,
        client_factory=FakeClient,
        now_func=lambda: reference,
    )

    assert artifacts.rows == 3
    assert artifacts.parquet_path.exists()
    assert artifacts.metadata_path.exists()
    saved = pd.read_parquet(artifacts.parquet_path)
    metadata = json.loads(artifacts.metadata_path.read_text(encoding="utf-8"))
    assert len(saved) == 3
    assert metadata["status"] == "PASS"
    assert metadata["contract"]["name"] == "MNQU6"
    assert metadata["history_request_count"] == 1
    assert metadata["freshness"]["fresh"] is True
    assert "api_key" not in json.dumps(metadata).lower()


def test_market_data_client_contains_no_order_endpoint_constants():
    endpoints = {AUTH_ENDPOINT, CONTRACT_SEARCH_ENDPOINT, HISTORY_ENDPOINT}
    assert all("order" not in endpoint.lower() for endpoint in endpoints)


def test_live_morning_collection_cannot_skip_freshness_check():
    args = parse_arguments(["--live", "--skip-freshness-check", "--days", "1"])

    with pytest.raises(ValueError, match="freshness"):
        validate_arguments(args)


def test_historical_backfill_may_skip_freshness_check():
    args = parse_arguments(["--no-live", "--skip-freshness-check", "--days", "30"])
    validate_arguments(args)  # must not raise


def test_collector_marks_degraded_metadata_for_warning_bearing_snapshot(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("PROJECTX_USERNAME", "user")
    monkeypatch.setenv("PROJECTX_API_KEY", "key")
    monkeypatch.setenv("APP_TIMEZONE", "America/New_York")
    reference = datetime(2026, 9, 2, 12, 58, tzinfo=timezone.utc)
    dataframe = _normalized_bars(
        "2026-09-02T12:55:00Z",
        "2026-09-02T12:56:00Z",
        "2026-09-02T12:57:00Z",
    )
    # Off-tick price: structurally valid OHLC, but a material data-quality
    # warning (20000.13 is not a multiple of the 0.25 NQ tick).
    dataframe.loc[0, "open"] = 20000.13

    class FakeClient:
        def __init__(self, **kwargs):
            assert kwargs["live"] is True
            self.history_request_count = 1

        def authenticate(self):
            return "token"

        def resolve_contract(self, **_kwargs):
            return ContractSelection(
                contract_id="contract-1",
                name="MNQU6",
                description="Micro E-mini Nasdaq-100",
                active=True,
                raw={},
            )

        def fetch_bars(self, **_kwargs):
            return dataframe

    args = parse_arguments(
        [
            "--live",
            "--days",
            "1",
            "--output-directory",
            str(tmp_path),
        ]
    )

    artifacts = collect(
        args,
        client_factory=FakeClient,
        now_func=lambda: reference,
    )

    metadata = json.loads(artifacts.metadata_path.read_text(encoding="utf-8"))
    # Warnings do not fail the snapshot; they degrade the analysis status.
    assert metadata["status"] == "DEGRADED"
    assert metadata["analysis_status"] == "degraded"
    assert any("off_tick_prices" in reason for reason in metadata["analysis_reasons"])


def _metadata_kwargs(
    dataframe: pd.DataFrame,
    *,
    collected_at: datetime,
    last_bar: datetime,
    freshness=None,
) -> dict:
    return {
        "collected_at": collected_at,
        "start_time": last_bar,
        "end_time": collected_at,
        "symbol": "MNQ",
        "live": True,
        "contract": ContractSelection("id", "MNQ", "test", True, {}),
        "dataframe": dataframe,
        "validation": ValidationReport(rows=1),
        "freshness": freshness,
        "freshness_check_skipped": False,
        "history_request_count": 1,
        "chunk_days": 1,
        "request_delay_seconds": 0.0,
    }


def test_build_metadata_marks_fatal_stale_live_data_no_analysis() -> None:
    """A fresh validation plus a stale FreshnessResult must not claim analysis
    can run: fatal stale live data is no_analysis with a freshness reason,
    consistent with status FAIL and the collector exception. The configured
    freshness threshold itself is not part of this mapping."""
    dataframe = _normalized_bars("2026-09-02T12:59:00Z")
    now = datetime(2026, 9, 2, 13, 5, tzinfo=timezone.utc)
    last = datetime(2026, 9, 2, 12, 59, tzinfo=timezone.utc)
    freshness = assess_bar_freshness(
        dataframe,
        reference_time=now,
        maximum_age=timedelta(minutes=5),
    )
    assert freshness.fresh is False
    assert freshness.reason == "latest_bar_is_stale"

    metadata = build_metadata(
        **_metadata_kwargs(
            dataframe,
            collected_at=now,
            last_bar=last,
            freshness=freshness,
        )
    )
    assert metadata["status"] == "FAIL"
    assert metadata["analysis_status"] == "no_analysis"
    assert any("freshness" in reason for reason in metadata["analysis_reasons"])
    assert any("latest_bar_is_stale" in reason for reason in metadata["analysis_reasons"])


def test_build_metadata_fresh_live_data_keeps_pass_status() -> None:
    """A fresh snapshot with clean validation stays analysis-ready: the
    freshness override must not fire when the data is fresh."""
    dataframe = _normalized_bars("2026-09-02T12:59:00Z")
    now = datetime(2026, 9, 2, 13, 1, tzinfo=timezone.utc)
    last = datetime(2026, 9, 2, 12, 59, tzinfo=timezone.utc)
    freshness = assess_bar_freshness(
        dataframe,
        reference_time=now,
        maximum_age=timedelta(minutes=5),
    )
    assert freshness.fresh is True
    metadata = build_metadata(
        **_metadata_kwargs(
            dataframe,
            collected_at=now,
            last_bar=last,
            freshness=freshness,
        )
    )
    assert metadata["status"] == "PASS"
    assert metadata["analysis_status"] == "pass"


def test_collector_exits_nonzero_and_emits_fail_safe_without_credentials(
    monkeypatch, capsys
):
    for name in (
        "PROJECTX_USERNAME",
        "PROJECTX_API_KEY",
        "TOPSTEP_USERNAME",
        "TOPSTEP_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    # This test must remain deterministic even on a real VPS that has a valid
    # project-level .env.  The behavior under test is the fail-safe path when
    # no credentials are available, not whether the host machine has secrets.
    monkeypatch.setattr(collector_script, "load_simple_env", lambda _path: None)

    with pytest.raises(SystemExit) as exc_info:
        collector_main(["--days", "1"])

    assert exc_info.value.code == 1
    assert "NO ANALYSIS — PROJECTX DATA UNAVAILABLE" in capsys.readouterr().err
