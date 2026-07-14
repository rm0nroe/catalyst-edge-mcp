"""Secure, side-effect-free request validation helpers."""

import re

TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,11}$")
FORBIDDEN_SUBSTRINGS = ("script", "exec", "union", "select", "drop", "delete", "insert", "update")


def normalize_ticker(value: str) -> str:
    """Normalize and validate a US-style ticker symbol."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Ticker symbol is required")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError("Invalid ticker format")
    ticker = value.strip().upper()
    lowered = ticker.lower()
    if (
        "/" in ticker
        or "\\" in ticker
        or "--" in ticker
        or "/*" in ticker
        or "*/" in ticker
        or re.search(r"\bor\s+1\s*=\s*1\b", lowered)
        or any(fragment in lowered for fragment in FORBIDDEN_SUBSTRINGS)
    ):
        raise ValueError("Invalid ticker format")
    if not TICKER_PATTERN.fullmatch(ticker):
        raise ValueError("Invalid ticker format")
    return ticker
