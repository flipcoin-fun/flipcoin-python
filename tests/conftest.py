"""Shared fixtures for schema-sync tests."""

import json
import os

import httpx
import pytest

OPENAPI_URL = "https://www.flipcoin.fun/api/openapi.json"
SIBLING_SPEC_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "flipcoin",
    "src",
    "app",
    "api",
    "openapi.json",
    "route.ts",
)


@pytest.fixture(scope="session")
def openapi_spec() -> dict:
    """Fetch the OpenAPI spec from the live API (primary) or fail."""
    try:
        resp = httpx.get(OPENAPI_URL, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        pytest.skip(f"Could not fetch OpenAPI spec from {OPENAPI_URL}: {exc}")
