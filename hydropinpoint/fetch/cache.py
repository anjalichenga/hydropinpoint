"""Disk cache for real HTTP responses.

Cache entries are never synthetic: each file records the original fetch timestamp and
is only written after a successful response from the named source.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from hydropinpoint.config import CACHE_DIR, HTTP_RETRIES, HTTP_TIMEOUT_S
from hydropinpoint.contracts import ToolResult

_RATE_LOCK = threading.Lock()
_LAST_REQUEST: dict[str, float] = {}


def _now() -> datetime:
    return datetime.now(UTC)


def make_cache_key(namespace: str, payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]
    return f"{namespace}-{digest}"


def _path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def save_real_response(key: str, value: Any, source: str, fetched_at: datetime) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"value": value, "source": source, "fetched_at": fetched_at.isoformat()}
    path = _path(key)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def load_real_response(key: str) -> ToolResult | None:
    path = _path(key)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ToolResult(
            value=payload["value"],
            source=payload["source"],
            fetched_at=datetime.fromisoformat(payload["fetched_at"]),
            cached=True,
        )
    except (OSError, KeyError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _rate_limit(bucket: str, seconds: float) -> None:
    if seconds <= 0:
        return
    with _RATE_LOCK:
        elapsed = time.monotonic() - _LAST_REQUEST.get(bucket, 0.0)
        if elapsed < seconds:
            time.sleep(seconds - elapsed)
        _LAST_REQUEST[bucket] = time.monotonic()


def request_json(
    *,
    url: str,
    source: str,
    namespace: str,
    params: dict[str, Any] | None = None,
    data: Any = None,
    headers: dict[str, str] | None = None,
    method: str = "GET",
    cache_key: str | None = None,
    rate_limit_s: float = 0.0,
    allow_cache_on_error: bool = True,
) -> ToolResult:
    key = cache_key or make_cache_key(namespace, {"params": params, "data": data})
    errors: list[str] = []
    for attempt in range(HTTP_RETRIES):
        try:
            _rate_limit(namespace, rate_limit_s)
            response = requests.request(
                method, url, params=params, data=data, headers=headers,
                timeout=HTTP_TIMEOUT_S,
            )
            response.raise_for_status()
            value = response.json()
            fetched_at = _now()
            save_real_response(key, value, source, fetched_at)
            return ToolResult(value=value, source=source, fetched_at=fetched_at)
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"attempt {attempt + 1}: {exc}")
            if attempt + 1 < HTTP_RETRIES:
                time.sleep(2**attempt)

    if allow_cache_on_error:
        cached = load_real_response(key)
        if cached is not None:
            cached.error = f"live fetch failed; using saved real response ({'; '.join(errors)})"
            return cached
    return ToolResult(
        value=None,
        source=source,
        fetched_at=_now(),
        error="; ".join(errors) or "request failed",
    )

