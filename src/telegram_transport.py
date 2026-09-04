"""Transport-only Telegram adapter for deterministic alert payloads."""
from __future__ import annotations

import json
import time
from typing import Any, Callable, Mapping
from urllib import error, parse, request


class TelegramTransportError(RuntimeError):
    pass


def render_telegram_alert(alert: Mapping[str, Any]) -> str:
    fields = [
        ("type", alert.get("type")),
        ("scenario_id", alert.get("scenario_id")),
        ("state", alert.get("state")),
        ("as_of", alert.get("as_of")),
    ]
    return "\n".join(f"{name}: {value}" for name, value in fields if value is not None)


def _post(url: str, payload: bytes, timeout: float) -> Mapping[str, Any]:
    req = request.Request(url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def send_telegram_alert(
    alert: Mapping[str, Any], *, token: str | None, chat_id: str | None,
    requester: Callable[[str, bytes, float], Mapping[str, Any]] = _post,
    attempts: int = 3, timeout: float = 10.0,
    sleep_func: Callable[[float], None] = time.sleep,
) -> Mapping[str, Any]:
    if not token or not chat_id:
        raise TelegramTransportError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required.")
    if attempts <= 0:
        raise ValueError("attempts must be positive")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = parse.urlencode({"chat_id": chat_id, "text": render_telegram_alert(alert)}).encode()
    for attempt in range(attempts):
        try:
            response = requester(url, payload, timeout)
            if not response.get("ok"):
                raise TelegramTransportError("Telegram rejected the alert payload.")
            return response
        except (TimeoutError, error.URLError, error.HTTPError) as exc:
            if attempt + 1 == attempts:
                raise TelegramTransportError("Telegram delivery failed after retries.") from exc
            sleep_func(float(2**attempt))
    raise TelegramTransportError("Telegram delivery failed.")
