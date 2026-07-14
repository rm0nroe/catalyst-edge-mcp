"""Recursive, bounded protection for opt-in raw provider signals."""

from __future__ import annotations

import json
import re
from typing import Any

MAX_DEPTH = 5
MAX_ITEMS = 50
MAX_STRING = 1_000
MAX_SERIALIZED_BYTES = 8_192
SENSITIVE_PARTS = (
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "password",
    "email",
    "user_id",
    "userid",
    "account_id",
    "accountid",
)


def _normalized_key(value: object) -> str:
    return re.sub(r"[^a-z0-9_]", "", str(value).lower().replace("-", "_"))


def redact_raw(value: Any, *, _depth: int = 0) -> Any:
    """Remove secret-like keys and bound containers before serialization."""
    if _depth >= MAX_DEPTH:
        return "[maximum depth reached]"
    if isinstance(value, dict):
        output: dict[str, Any] = {}
        for key, child in list(value.items())[:MAX_ITEMS]:
            normalized = _normalized_key(key)
            if any(part in normalized for part in SENSITIVE_PARTS):
                continue
            output[str(key)[:MAX_STRING]] = redact_raw(child, _depth=_depth + 1)
        return output
    if isinstance(value, (list, tuple, set)):
        return [redact_raw(child, _depth=_depth + 1) for child in list(value)[:MAX_ITEMS]]
    if isinstance(value, str):
        return value[:MAX_STRING]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:MAX_STRING]


def bounded_raw(value: Any) -> Any:
    """Redact first, then enforce the per-evidence 8 KiB serialized limit."""
    redacted = redact_raw(value)
    serialized = json.dumps(redacted, default=str, separators=(",", ":"), ensure_ascii=False)
    if len(serialized.encode("utf-8")) <= MAX_SERIALIZED_BYTES:
        return redacted
    preview = serialized.encode("utf-8")[:7_500].decode("utf-8", errors="ignore")
    return {"truncated": True, "preview": preview}
