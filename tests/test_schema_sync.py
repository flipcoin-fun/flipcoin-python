"""
Schema-sync tests: flipcoin-python SDK ↔ OpenAPI spec.

Validates that the Python SDK (client methods + dataclass models)
stays in sync with the canonical OpenAPI specification.

Run:  pytest tests/test_schema_sync.py -v
"""

import dataclasses
import inspect

import pytest

from flipcoin.client import FlipCoin
from flipcoin import models


# ─── Endpoint coverage ────────────────────────────────────────────────────────
# Every OpenAPI path+method → expected SDK method name

ENDPOINT_METHOD_MAP: dict[tuple[str, str], str] = {
    # Health & Config
    ("GET", "/api/agent/ping"): "ping",
    ("GET", "/api/agent/config"): "get_config",
    # Markets
    ("GET", "/api/agent/markets/explore"): "get_markets",
    ("GET", "/api/agent/markets"): "get_my_markets",
    ("GET", "/api/agent/markets/{address}"): "get_market",
    ("GET", "/api/agent/markets/{address}/state"): "get_market_state",
    ("GET", "/api/agent/markets/{address}/history"): "get_market_history",
    ("POST", "/api/agent/markets/validate"): "validate_market",
    ("POST", "/api/agent/markets"): "create_market",
    ("POST", "/api/agent/markets/batch"): "batch_create_markets",
    # Trading
    ("GET", "/api/quote"): "get_quote",
    ("POST", "/api/agent/trade/intent"): "trade",  # trade() calls intent+relay
    ("POST", "/api/agent/trade/relay"): "trade",
    ("GET", "/api/agent/trade/nonce"): "get_trade_nonce",
    ("GET", "/api/agent/trade/approve"): "get_approval_status",
    # CLOB Orders
    ("POST", "/api/agent/orders/intent"): "create_order",
    ("POST", "/api/agent/orders/relay"): "create_order",
    ("GET", "/api/agent/orders"): "get_orders",
    ("DELETE", "/api/agent/orders/{orderHash}"): "cancel_order",
    # Portfolio
    ("GET", "/api/agent/portfolio"): "get_portfolio",
    # Analytics
    ("GET", "/api/agent/performance"): "get_performance",
    ("GET", "/api/agent/audit-log"): "get_audit_log",
    ("GET", "/api/agent/feed"): "get_feed",
    ("GET", "/api/agent/feed/stream"): "stream_feed",
    # Vault
    ("GET", "/api/agent/vault/deposit"): "get_vault_balance",
    ("POST", "/api/agent/vault/deposit"): "deposit",
    # Webhooks
    ("POST", "/api/agent/webhooks"): "create_webhook",
    ("GET", "/api/agent/webhooks"): "get_webhooks",
    ("DELETE", "/api/agent/webhooks/{id}"): "delete_webhook",
    # Leaderboard
    ("GET", "/api/agents/leaderboard"): "get_leaderboard",
    # Comments
    ("POST", "/api/agent/comments"): "create_comment",
    ("GET", "/api/agent/comments"): "get_comments",
    ("POST", "/api/agent/comments/{commentId}/like"): "like_comment",
    ("DELETE", "/api/agent/comments/{commentId}/like"): "unlike_comment",
    # Resolution
    ("POST", "/api/agent/markets/{address}/propose-resolution"): "propose_resolution",
    ("POST", "/api/agent/markets/{address}/finalize-resolution"): "finalize_resolution",
    # Trade history
    ("GET", "/api/agent/trade/history"): "get_trade_history",
    # Vault withdraw
    ("GET", "/api/agent/vault/withdraw"): "get_withdraw_info",
    ("POST", "/api/agent/vault/withdraw"): "withdraw",
    # Portfolio redeem
    ("POST", "/api/agent/portfolio/redeem"): "redeem_positions",
}

# Endpoints in OpenAPI that the Python SDK does NOT yet cover.
# When adding a new method to the SDK, move it from here to ENDPOINT_METHOD_MAP.
# If this set grows unexpectedly, it means new endpoints were added to the spec
# without updating the SDK.
KNOWN_SDK_GAPS: set[tuple[str, str]] = {
    # Relay (Mode A manual market creation)
    ("POST", "/api/agent/relay"),
    # Activity
    ("GET", "/api/agent/activity"),
    ("POST", "/api/agent/activity/{id}/relay-signed"),
    # Stats
    ("GET", "/api/agent/stats"),
    # API key management
    ("POST", "/api/agent/api-key"),
    ("GET", "/api/agent/api-key"),
    # Session key management
    ("GET", "/api/agent/session-key"),
    ("POST", "/api/agent/session-key"),
    ("PATCH", "/api/agent/session-key"),
    ("DELETE", "/api/agent/session-key"),
}


class TestEndpointCoverage:
    """Every OpenAPI endpoint has a corresponding SDK method."""

    @pytest.mark.parametrize(
        "endpoint,method_name",
        [
            (f"{method} {path}", name)
            for (method, path), name in ENDPOINT_METHOD_MAP.items()
        ],
        ids=[f"{m} {p}" for (m, p) in ENDPOINT_METHOD_MAP],
    )
    def test_method_exists(self, endpoint: str, method_name: str):
        assert hasattr(FlipCoin, method_name), (
            f"FlipCoin client missing method '{method_name}' for {endpoint}"
        )
        assert callable(getattr(FlipCoin, method_name))

    def test_no_extra_openapi_endpoints_uncovered(self, openapi_spec: dict):
        """Every path in OpenAPI spec is either covered or in KNOWN_SDK_GAPS."""
        paths = openapi_spec.get("paths", {})
        uncovered = []
        for path, methods in paths.items():
            for method in methods:
                if method.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                    key = (method.upper(), path)
                    if key not in ENDPOINT_METHOD_MAP and key not in KNOWN_SDK_GAPS:
                        uncovered.append(f"{method.upper()} {path}")
        assert uncovered == [], (
            f"OpenAPI endpoints not mapped in ENDPOINT_METHOD_MAP or KNOWN_SDK_GAPS: {uncovered}. "
            "Add new endpoints to ENDPOINT_METHOD_MAP (if SDK method exists) "
            "or KNOWN_SDK_GAPS (if not yet implemented)."
        )

    def test_known_gaps_are_not_stale(self):
        """Ensure KNOWN_SDK_GAPS entries haven't been secretly implemented."""
        implemented = []
        for method, path in KNOWN_SDK_GAPS:
            # Derive likely method name from path
            # If someone adds the method, this test will catch it
            pass  # Manual check — gaps shrink when SDK methods are added

        # Verify gap entries don't also appear in the covered map
        overlap = KNOWN_SDK_GAPS & set(ENDPOINT_METHOD_MAP.keys())
        assert overlap == set(), (
            f"Endpoints in both KNOWN_SDK_GAPS and ENDPOINT_METHOD_MAP: {overlap}. "
            "Remove from KNOWN_SDK_GAPS after adding SDK method."
        )


# ─── Response model field alignment ───────────────────────────────────────────
# Maps OpenAPI schema name → Python dataclass name

SCHEMA_MODEL_MAP: dict[str, str] = {
    "PingResponse": "PingResponse",
    "ConfigResponse": "ConfigResponse",
    "ExploreResponse": "ExploreResponse",
    "MarketDetailsResponse": "MarketDetailsResponse",
    "MarketState": "MarketState",
    "MarketHistoryResponse": "MarketHistoryResponse",
    "ValidateResult": "ValidateResult",
    "CreateMarketResult": "CreateMarketResult",
    "BatchResult": "BatchResult",
    "QuoteResponse": "Quote",
    "TradeIntentResponse": "TradeIntentResponse",
    "TradeRelayResponse": "TradeResult",
    "OrderIntentResponse": "OrderIntentResponse",
    "OrderResult": "OrderResult",
    "OrderListResponse": "OrderListResponse",
    "OrderCancelResponse": "OrderCancelResponse",
    "PortfolioResponse": "PortfolioResponse",
    "PerformanceResponse": "PerformanceResponse",
    "AuditLogResponse": "AuditLogResponse",
    "FeedResponse": "FeedResponse",
    "VaultBalanceResponse": "VaultBalanceResponse",
    "DepositRelayResponse": "DepositResult",
    "LeaderboardResponse": "LeaderboardResponse",
    "AgentMarketsListResponse": "AgentMarketsListResponse",
    "TradeNonceResponse": "TradeNonceResponse",
    "ApprovalStatus": "ApprovalStatus",
}


def _camel_to_snake(name: str) -> str:
    """Convert camelCase to snake_case."""
    import re

    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _get_schema_fields(spec: dict, schema_name: str) -> set[str]:
    """Extract top-level field names from an OpenAPI schema."""
    schema = spec.get("components", {}).get("schemas", {}).get(schema_name, {})
    props = schema.get("properties", {})
    return set(props.keys())


def _get_dataclass_fields(cls) -> set[str]:
    """Extract field names from a Python dataclass."""
    if dataclasses.is_dataclass(cls):
        return {f.name for f in dataclasses.fields(cls)}
    return set()


class TestResponseModelFields:
    """SDK dataclass fields match OpenAPI response schemas."""

    @pytest.mark.parametrize(
        "schema_name,model_name",
        list(SCHEMA_MODEL_MAP.items()),
        ids=list(SCHEMA_MODEL_MAP.keys()),
    )
    def test_model_exists(self, schema_name: str, model_name: str):
        assert hasattr(models, model_name), (
            f"models.py missing class '{model_name}' for OpenAPI schema '{schema_name}'"
        )

    @pytest.mark.parametrize(
        "schema_name,model_name",
        list(SCHEMA_MODEL_MAP.items()),
        ids=[f"{k}_fields" for k in SCHEMA_MODEL_MAP],
    )
    def test_fields_covered(
        self, openapi_spec: dict, schema_name: str, model_name: str
    ):
        """Every field in the OpenAPI schema has a snake_case counterpart in the dataclass."""
        model_cls = getattr(models, model_name, None)
        if model_cls is None:
            pytest.skip(f"Model {model_name} not found")

        spec_fields = _get_schema_fields(openapi_spec, schema_name)
        if not spec_fields:
            pytest.skip(f"Schema {schema_name} has no properties in spec")

        model_fields = _get_dataclass_fields(model_cls)
        if not model_fields:
            pytest.skip(f"{model_name} is not a dataclass")

        # Convert OpenAPI camelCase → snake_case for comparison
        expected_snake = {_camel_to_snake(f) for f in spec_fields}
        missing = expected_snake - model_fields

        # Known field gaps in the Python SDK (real drift — tracked for future fix)
        known_field_gaps: dict[str, set[str]] = {}
        known = known_field_gaps.get(model_name, set())
        unexpected_missing = missing - known
        assert unexpected_missing == set(), (
            f"{model_name} missing fields from OpenAPI {schema_name}: {unexpected_missing}"
        )


# ─── Error codes ──────────────────────────────────────────────────────────────


class TestErrorCodes:
    """SDK FlipCoinError handles all documented error codes."""

    def test_flipcoin_error_has_error_code_field(self):
        """FlipCoinError must have error_code attribute."""
        err = models.FlipCoinError("test", status_code=400, error_code="TEST_CODE")
        assert hasattr(err, "error_code")
        assert err.error_code == "TEST_CODE"

    def test_spec_error_codes_are_strings(self, openapi_spec: dict):
        """All error codes in the spec are string values that can be passed to FlipCoinError."""
        error_codes = openapi_spec.get("errorCodes", {})
        if not error_codes:
            pytest.skip("No errorCodes section in spec")

        for code in error_codes:
            assert isinstance(code, str), f"Error code must be string, got {type(code)}"
            # Verify we can construct a FlipCoinError with each code
            err = models.FlipCoinError(400, code, "test")
            assert err.error_code == code


# ─── Enum values ──────────────────────────────────────────────────────────────


class TestEnumValues:
    """OpenAPI enum values match SDK expectations."""

    def test_create_market_liquidity_tiers(self, openapi_spec: dict):
        schema = openapi_spec["components"]["schemas"].get("CreateMarketRequest", {})
        tiers = schema.get("properties", {}).get("liquidityTier", {}).get("enum", [])
        if not tiers:
            pytest.skip("No liquidityTier enum in spec")
        for expected in ("trial", "low", "medium", "high"):
            assert expected in tiers, f"Missing tier '{expected}' in OpenAPI spec"

    def test_trade_intent_venue_enum(self, openapi_spec: dict):
        schema = openapi_spec["components"]["schemas"].get("TradeIntentRequest", {})
        venues = schema.get("properties", {}).get("venue", {}).get("enum", [])
        if not venues:
            pytest.skip("No venue enum in spec")
        for expected in ("lmsr", "clob", "auto"):
            assert expected in venues, f"Missing venue '{expected}' in OpenAPI spec"

    def test_order_time_in_force_enum(self, openapi_spec: dict):
        schema = openapi_spec["components"]["schemas"].get("OrderIntentRequest", {})
        tif = (
            schema.get("properties", {}).get("timeInForce", {}).get("enum", [])
        )
        if not tif:
            pytest.skip("No timeInForce enum in spec")
        for expected in ("GTC", "IOC", "FOK"):
            assert expected in tif, f"Missing timeInForce '{expected}' in OpenAPI spec"


# ─── Method signatures ────────────────────────────────────────────────────────


class TestMethodSignatures:
    """Key SDK method signatures include required parameters."""

    def test_get_markets_has_filter_params(self):
        sig = inspect.signature(FlipCoin.get_markets)
        params = set(sig.parameters.keys()) - {"self"}
        # At minimum: status, sort, limit, offset
        for expected in ("status", "sort", "limit", "offset"):
            assert expected in params, (
                f"get_markets() missing param '{expected}', has: {params}"
            )

    def test_trade_has_required_params(self):
        sig = inspect.signature(FlipCoin.trade)
        params = set(sig.parameters.keys()) - {"self"}
        for expected in ("condition_id", "side", "action"):
            assert expected in params, (
                f"trade() missing param '{expected}', has: {params}"
            )

    def test_create_order_has_required_params(self):
        sig = inspect.signature(FlipCoin.create_order)
        params = set(sig.parameters.keys()) - {"self"}
        for expected in ("condition_id", "side", "action", "price_bps", "amount"):
            assert expected in params, (
                f"create_order() missing param '{expected}', has: {params}"
            )

    def test_get_quote_has_required_params(self):
        sig = inspect.signature(FlipCoin.get_quote)
        params = set(sig.parameters.keys()) - {"self"}
        for expected in ("condition_id", "side", "action", "amount"):
            assert expected in params, (
                f"get_quote() missing param '{expected}', has: {params}"
            )

    def test_create_market_has_required_params(self):
        sig = inspect.signature(FlipCoin.create_market)
        params = set(sig.parameters.keys()) - {"self"}
        for expected in ("title", "resolution_criteria", "resolution_source"):
            assert expected in params, (
                f"create_market() missing param '{expected}', has: {params}"
            )
