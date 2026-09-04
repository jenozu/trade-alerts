"""Secret-safe structured JSON-lines production logging."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
from typing import Any, Iterable, Mapping

SENSITIVE_MARKERS = ("password", "api_key", "apikey", "token", "secret", "authorization")


def _redact(value: Any, sensitive_values: tuple[str, ...]) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if any(marker in str(key).lower() for marker in SENSITIVE_MARKERS)
            else _redact(item, sensitive_values)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(item, sensitive_values) for item in value]
    text = str(value)
    for secret in sensitive_values:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    return text if isinstance(value, str) else value


class JsonLineFormatter(logging.Formatter):
    def __init__(self, *, component: str, sensitive_values: Iterable[str] = ()) -> None:
        super().__init__()
        self.component = component
        self.sensitive_values = tuple(value for value in sensitive_values if value)

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "component": self.component,
            "event": getattr(record, "event", record.getMessage()),
            "details": getattr(record, "details", {}),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(_redact(payload, self.sensitive_values), sort_keys=True)


def configure_production_logger(
    log_directory: str | Path,
    *,
    component: str,
    sensitive_values: Iterable[str] = (),
) -> logging.Logger:
    directory = Path(log_directory)
    directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"trade_alerts.production.{component}")
    for existing in logger.handlers:
        existing.close()
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = logging.FileHandler(directory / "production.jsonl", encoding="utf-8")
    handler.setFormatter(JsonLineFormatter(component=component, sensitive_values=sensitive_values))
    logger.addHandler(handler)
    return logger


def log_event(logger: logging.Logger, event: str, **details: Any) -> None:
    logger.info(event, extra={"event": event, "details": details})
