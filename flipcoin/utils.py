"""Utility functions for FlipCoin SDK."""

from __future__ import annotations

import re
import uuid
from typing import Any

# ---------------------------------------------------------------------------
# USDC helpers
# ---------------------------------------------------------------------------

USDC_DECIMALS = 6
USDC_FACTOR = 10**USDC_DECIMALS


def usdc_to_raw(amount: float | int) -> str:
    """Convert human-readable USDC to raw 6-decimal string.

    >>> usdc_to_raw(5.0)
    '5000000'
    >>> usdc_to_raw(0.01)
    '10000'
    """
    return str(int(round(float(amount) * USDC_FACTOR)))


def raw_to_usdc(raw: str | int) -> float:
    """Convert raw 6-decimal USDC string to human-readable float.

    >>> raw_to_usdc("5000000")
    5.0
    >>> raw_to_usdc(10000)
    0.01
    """
    return int(raw) / USDC_FACTOR


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def idempotency_key() -> str:
    """Generate a unique idempotency key for mutation requests."""
    return f"py-{uuid.uuid4().hex[:16]}"


# ---------------------------------------------------------------------------
# Case conversion (camelCase <-> snake_case)
# ---------------------------------------------------------------------------

_RE1 = re.compile(r"(.)([A-Z][a-z]+)")
_RE2 = re.compile(r"([a-z0-9])([A-Z])")


def camel_to_snake(name: str) -> str:
    s = _RE1.sub(r"\1_\2", name)
    return _RE2.sub(r"\1_\2", s).lower()


def snake_to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])


def to_snake_dict(obj: Any) -> Any:
    """Recursively convert dict keys from camelCase to snake_case."""
    if isinstance(obj, dict):
        return {camel_to_snake(k): to_snake_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_snake_dict(item) for item in obj]
    return obj


def to_camel_dict(obj: Any) -> Any:
    """Recursively convert dict keys from snake_case to camelCase."""
    if isinstance(obj, dict):
        return {snake_to_camel(k): to_camel_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_camel_dict(item) for item in obj]
    return obj
