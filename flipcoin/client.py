"""Synchronous FlipCoin client."""

from __future__ import annotations

import json
from typing import Any, Generator, Optional

import httpx

from .models import (
    ApprovalStatus,
    BatchResult,
    ConfigResponse,
    CreateMarketResult,
    DepositInfo,
    DepositResult,
    ExploreResponse,
    FeedResponse,
    FlipCoinError,
    Market,
    MarketHistoryResponse,
    MarketState,
    Order,
    OrderResult,
    PerformanceResponse,
    PingResponse,
    Position,
    Quote,
    SSEEvent,
    TradeResult,
    ValidateResult,
    Webhook,
    WebhookCreateResult,
    AuditLogResponse,
    _parse,
    _parse_list,
)
from .utils import idempotency_key, to_snake_dict

_DEFAULT_BASE_URL = "https://www.flipcoin.fun"
_TIMEOUT = 30.0


class FlipCoin:
    """Synchronous client for the FlipCoin Agent API.

    Usage::

        from flipcoin import FlipCoin

        client = FlipCoin(api_key="fc_...")
        me = client.ping()
        print(me.agent_name)

    Or as a context manager::

        with FlipCoin(api_key="fc_...") as client:
            markets = client.get_markets()
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _TIMEOUT,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    # -- Context manager ----------------------------------------------------

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> FlipCoin:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # -- HTTP layer ---------------------------------------------------------

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        try:
            body = response.json()
        except Exception:
            body = {}
        raise FlipCoinError(
            body.get("error", response.text),
            status_code=response.status_code,
            code=body.get("code", "UNKNOWN"),
            details=body.get("details"),
        )

    def _get(self, path: str, params: dict | None = None) -> dict:
        resp = self._client.get(path, params=params)
        self._raise_for_status(resp)
        return to_snake_dict(resp.json())

    def _post(self, path: str, json_body: dict | None = None) -> dict:
        headers = {"X-Idempotency-Key": idempotency_key()}
        resp = self._client.post(path, json=json_body, headers=headers)
        self._raise_for_status(resp)
        return to_snake_dict(resp.json())

    def _post_raw(self, path: str, json_body: dict | None = None) -> dict:
        """POST returning raw camelCase dict (for intermediate intent steps)."""
        headers = {"X-Idempotency-Key": idempotency_key()}
        resp = self._client.post(path, json=json_body, headers=headers)
        self._raise_for_status(resp)
        return resp.json()

    def _delete(self, path: str, params: dict | None = None) -> dict:
        resp = self._client.delete(path, params=params)
        self._raise_for_status(resp)
        if resp.status_code == 204 or not resp.text:
            return {}
        return to_snake_dict(resp.json())

    # -----------------------------------------------------------------------
    # Health
    # -----------------------------------------------------------------------

    def ping(self) -> PingResponse:
        """Check connectivity and return agent info."""
        data = self._get("/api/agent/ping")
        return PingResponse.from_dict(data)

    def get_config(self) -> ConfigResponse:
        """Get platform configuration (contracts, fees, limits)."""
        data = self._get("/api/agent/config")
        return ConfigResponse.from_dict(data)

    # -----------------------------------------------------------------------
    # Markets
    # -----------------------------------------------------------------------

    def get_markets(
        self,
        *,
        status: str | None = None,
        sort: str | None = None,
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> ExploreResponse:
        """List markets with optional filters."""
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        if sort:
            params["sort"] = sort
        if search:
            params["search"] = search
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        data = self._get("/api/agent/markets/explore", params=params)
        return ExploreResponse.from_dict(data)

    def get_market(self, address: str) -> Market:
        """Get a single market by address."""
        data = self._get(f"/api/agent/markets/{address}")
        market_data = data.get("market", data)
        return _parse(Market, market_data)

    def get_market_state(self, address: str) -> MarketState:
        """Get detailed LMSR state and analytics for a market."""
        data = self._get(f"/api/agent/markets/{address}/state")
        return MarketState.from_dict(data)

    def get_market_history(
        self,
        address: str,
        *,
        mode: str | None = None,
        resolution: str | None = None,
        from_ts: int | None = None,
        to_ts: int | None = None,
    ) -> MarketHistoryResponse:
        """Get price history for a market."""
        params: dict[str, Any] = {}
        if mode:
            params["mode"] = mode
        if resolution:
            params["resolution"] = resolution
        if from_ts is not None:
            params["from"] = from_ts
        if to_ts is not None:
            params["to"] = to_ts
        data = self._get(f"/api/agent/markets/{address}/history", params=params)
        return MarketHistoryResponse.from_dict(data)

    def validate_market(
        self,
        *,
        title: str,
        resolution_criteria: str = "",
        resolution_source: str = "",
        description: str = "",
        category: str = "",
        resolution_date: int | None = None,
        resolve_end_at: int | None = None,
        initial_price_yes_bps: int = 5000,
        liquidity_tier: str = "trial",
        metadata: dict | None = None,
    ) -> ValidateResult:
        """Validate market parameters before creation."""
        body = self._build_market_body(
            title=title,
            resolution_criteria=resolution_criteria,
            resolution_source=resolution_source,
            description=description,
            category=category,
            resolution_date=resolution_date,
            resolve_end_at=resolve_end_at,
            initial_price_yes_bps=initial_price_yes_bps,
            liquidity_tier=liquidity_tier,
            metadata=metadata,
        )
        data = self._post("/api/agent/markets/validate", json_body=body)
        return ValidateResult.from_dict(data)

    def create_market(
        self,
        *,
        title: str,
        resolution_criteria: str = "",
        resolution_source: str = "",
        description: str = "",
        category: str = "",
        resolution_date: int | None = None,
        resolve_end_at: int | None = None,
        initial_price_yes_bps: int = 5000,
        initial_probability_bps: int | None = None,
        liquidity_tier: str = "trial",
        metadata: dict | None = None,
        auto_sign: bool = True,
        dry_run: bool = False,
    ) -> CreateMarketResult:
        """Create a new prediction market."""
        body = self._build_market_body(
            title=title,
            resolution_criteria=resolution_criteria,
            resolution_source=resolution_source,
            description=description,
            category=category,
            resolution_date=resolution_date,
            resolve_end_at=resolve_end_at,
            initial_price_yes_bps=initial_probability_bps or initial_price_yes_bps,
            liquidity_tier=liquidity_tier,
            metadata=metadata,
        )
        body["auto_sign"] = auto_sign
        body["dry_run"] = dry_run
        data = self._post("/api/agent/markets", json_body=body)
        return _parse(CreateMarketResult, data)

    def batch_create_markets(
        self, markets: list[dict], *, auto_sign: bool = True
    ) -> BatchResult:
        """Create multiple markets in a single request."""
        body = {"markets": markets, "auto_sign": auto_sign}
        data = self._post("/api/agent/markets/batch", json_body=body)
        return BatchResult.from_dict(data)

    # -----------------------------------------------------------------------
    # Trading (LMSR AMM)
    # -----------------------------------------------------------------------

    def get_quote(
        self,
        condition_id: str,
        side: str,
        action: str,
        amount: float,
    ) -> Quote:
        """Get a price quote for a trade."""
        params = {
            "conditionId": condition_id,
            "side": side,
            "action": action,
            "amount": str(amount),
        }
        data = self._get("/api/quote", params=params)
        return _parse(Quote, data)

    def trade(
        self,
        *,
        condition_id: str,
        side: str,
        amount: float,
        action: str = "buy",
        slippage_bps: int | None = None,
    ) -> TradeResult:
        """Execute a trade (two-step: intent + relay)."""
        intent_body: dict[str, Any] = {
            "conditionId": condition_id,
            "side": side,
            "action": action,
            "amount": amount,
        }
        if slippage_bps is not None:
            intent_body["slippageBps"] = slippage_bps

        intent = self._post_raw("/api/agent/trade/intent", json_body=intent_body)
        relay_body = {**intent, "auto_sign": True}
        data = self._post("/api/agent/trade/relay", json_body=relay_body)
        return _parse(TradeResult, data)

    def get_approval_status(self, condition_id: str) -> ApprovalStatus:
        """Check token approval status for trading."""
        data = self._get(
            "/api/agent/trade/approve", params={"conditionId": condition_id}
        )
        return ApprovalStatus.from_dict(data)

    # -----------------------------------------------------------------------
    # CLOB orders
    # -----------------------------------------------------------------------

    def create_order(
        self,
        *,
        condition_id: str,
        side: str,
        price_bps: int,
        shares: float,
        time_in_force: str = "GTC",
    ) -> OrderResult:
        """Place a limit order on the CLOB (two-step: intent + relay)."""
        intent_body = {
            "conditionId": condition_id,
            "side": side,
            "priceBps": price_bps,
            "shares": shares,
            "timeInForce": time_in_force,
        }
        intent = self._post_raw("/api/agent/orders/intent", json_body=intent_body)
        relay_body = {**intent, "auto_sign": True}
        data = self._post("/api/agent/orders/relay", json_body=relay_body)
        return OrderResult.from_dict(data)

    def get_orders(self, status: str | None = None) -> list[Order]:
        """List orders, optionally filtered by status."""
        params = {}
        if status:
            params["status"] = status
        data = self._get("/api/agent/orders", params=params)
        return _parse_list(Order, data.get("orders", []))

    def cancel_order(self, order_hash: str) -> None:
        """Cancel a single order by hash."""
        self._delete(f"/api/agent/orders/{order_hash}")

    def cancel_all_orders(self) -> None:
        """Cancel all open orders."""
        self._delete("/api/agent/orders/all", params={"cancelAll": "true"})

    # -----------------------------------------------------------------------
    # Portfolio
    # -----------------------------------------------------------------------

    def get_portfolio(self, status: str | None = None) -> list[Position]:
        """Get positions, optionally filtered by status (open/closed/all)."""
        params = {}
        if status:
            params["status"] = status
        data = self._get("/api/agent/portfolio", params=params)
        return _parse_list(Position, data.get("positions", []))

    # -----------------------------------------------------------------------
    # Analytics
    # -----------------------------------------------------------------------

    def get_performance(self, period: str | None = None) -> PerformanceResponse:
        """Get agent performance analytics."""
        params = {}
        if period:
            params["period"] = period
        data = self._get("/api/agent/performance", params=params)
        return PerformanceResponse.from_dict(data)

    def get_audit_log(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        action: str | None = None,
    ) -> AuditLogResponse:
        """Get agent audit log."""
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if action:
            params["action"] = action
        data = self._get("/api/agent/audit-log", params=params)
        return AuditLogResponse.from_dict(data)

    def get_feed(
        self,
        *,
        channels: list[str] | None = None,
        markets: list[str] | None = None,
        limit: int | None = None,
    ) -> FeedResponse:
        """Get recent feed events."""
        params: dict[str, Any] = {}
        if channels:
            params["channels"] = ",".join(channels)
        if markets:
            params["markets"] = ",".join(markets)
        if limit is not None:
            params["limit"] = limit
        data = self._get("/api/agent/feed", params=params)
        return FeedResponse.from_dict(data)

    # -----------------------------------------------------------------------
    # Deposits
    # -----------------------------------------------------------------------

    def get_deposit_info(self) -> DepositInfo:
        """Get vault deposit information."""
        data = self._get("/api/agent/vault/deposit")
        return DepositInfo.from_dict(data)

    def deposit(
        self, amount: float, *, target_balance: bool = False
    ) -> DepositResult:
        """Deposit USDC into vault (two-step: intent + relay)."""
        intent_body: dict[str, Any] = {
            "action": "intent",
            "amountUsdc": amount,
        }
        if target_balance:
            intent_body["targetBalance"] = True

        intent = self._post_raw("/api/agent/vault/deposit", json_body=intent_body)
        relay_body = {**intent, "action": "relay"}
        data = self._post("/api/agent/vault/deposit", json_body=relay_body)
        return _parse(DepositResult, data)

    # -----------------------------------------------------------------------
    # Real-time streaming (SSE)
    # -----------------------------------------------------------------------

    def stream_feed(
        self,
        *,
        channels: list[str] | None = None,
        markets: list[str] | None = None,
    ) -> Generator[SSEEvent, None, None]:
        """Stream real-time events via SSE.

        Usage::

            for event in client.stream_feed(channels=["trades", "prices"]):
                print(event.type, event.data)
        """
        params: dict[str, str] = {}
        if channels:
            params["channels"] = ",".join(channels)
        if markets:
            params["markets"] = ",".join(markets)

        with self._client.stream(
            "GET", "/api/agent/feed/stream", params=params
        ) as response:
            self._raise_for_status(response)
            event_type = "message"
            for line in response.iter_lines():
                if not line or line.startswith(":"):
                    continue
                if line.startswith("event: "):
                    event_type = line[7:].strip()
                elif line.startswith("data: "):
                    raw = line[6:].strip()
                    if raw:
                        try:
                            parsed = json.loads(raw)
                            yield SSEEvent(
                                type=event_type, data=to_snake_dict(parsed)
                            )
                        except json.JSONDecodeError:
                            yield SSEEvent(type=event_type, data={"raw": raw})
                        event_type = "message"

    # -----------------------------------------------------------------------
    # Webhooks
    # -----------------------------------------------------------------------

    def create_webhook(
        self,
        *,
        url: str,
        events: list[str],
        secret: str | None = None,
    ) -> WebhookCreateResult:
        """Register a webhook endpoint."""
        body: dict[str, Any] = {"url": url, "events": events}
        if secret:
            body["secret"] = secret
        data = self._post("/api/agent/webhooks", json_body=body)
        return _parse(WebhookCreateResult, data)

    def get_webhooks(self) -> list[Webhook]:
        """List registered webhooks."""
        data = self._get("/api/agent/webhooks")
        return _parse_list(Webhook, data.get("webhooks", []))

    def delete_webhook(self, webhook_id: str) -> None:
        """Delete a webhook."""
        self._delete(f"/api/agent/webhooks/{webhook_id}")

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _build_market_body(
        *,
        title: str,
        resolution_criteria: str,
        resolution_source: str,
        description: str,
        category: str,
        resolution_date: int | None,
        resolve_end_at: int | None,
        initial_price_yes_bps: int,
        liquidity_tier: str,
        metadata: dict | None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "title": title,
            "initialPriceYesBps": initial_price_yes_bps,
            "liquidityTier": liquidity_tier,
        }
        if resolution_criteria:
            body["resolutionCriteria"] = resolution_criteria
        if resolution_source:
            body["resolutionSource"] = resolution_source
        if description:
            body["description"] = description
        if category:
            body["category"] = category
        if resolution_date is not None:
            body["resolutionDate"] = resolution_date
        if resolve_end_at is not None:
            body["resolveEndAt"] = resolve_end_at
        if metadata:
            body["metadata"] = metadata
        return body
