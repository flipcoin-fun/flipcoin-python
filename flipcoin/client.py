"""Synchronous FlipCoin client — aligned with OpenAPI spec (2026-03-11)."""

from __future__ import annotations

import json
from typing import Any, Generator, Optional

import httpx

from .models import (
    AgentMarketsListResponse,
    ApprovalStatus,
    AuditLogResponse,
    BatchResult,
    Comment,
    CommentsListResponse,
    ConfigResponse,
    CreateCommentResponse,
    CreateMarketResult,
    DepositResult,
    ExploreResponse,
    FeedResponse,
    FlipCoinError,
    LeaderboardResponse,
    Market,
    MarketDetailsResponse,
    MarketHistoryResponse,
    MarketState,
    Order,
    OrderCancelResponse,
    OrderListResponse,
    OrderResult,
    PerformanceResponse,
    PingResponse,
    PortfolioResponse,
    Quote,
    SSEEvent,
    TradeResult,
    ValidateResult,
    VaultBalanceResponse,
    Webhook,
    WebhookCreateResult,
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
        print(me.agent)

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
            error_code=body.get("errorCode", "UNKNOWN"),
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
        """Check connectivity and return agent info + rate limits."""
        data = self._get("/api/agent/ping")
        return PingResponse.from_dict(data)

    def get_config(self) -> ConfigResponse:
        """Get platform configuration (contracts, fees, limits, capabilities)."""
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
        fingerprint: str | None = None,
        created_by_agent: str | None = None,
        creator_addr: str | None = None,
        min_volume: float | None = None,
        resolve_end_before: str | None = None,
        resolve_end_after: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> ExploreResponse:
        """Browse all platform markets with filters (exploreMarkets)."""
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        if sort:
            params["sort"] = sort
        if search:
            params["search"] = search
        if fingerprint:
            params["fingerprint"] = fingerprint
        if created_by_agent:
            params["createdByAgent"] = created_by_agent
        if creator_addr:
            params["creatorAddr"] = creator_addr
        if min_volume is not None:
            params["minVolume"] = min_volume
        if resolve_end_before:
            params["resolveEndBefore"] = resolve_end_before
        if resolve_end_after:
            params["resolveEndAfter"] = resolve_end_after
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        data = self._get("/api/agent/markets/explore", params=params)
        return ExploreResponse.from_dict(data)

    def get_my_markets(self) -> AgentMarketsListResponse:
        """List agent's own markets and pending requests (listAgentMarkets)."""
        data = self._get("/api/agent/markets")
        return AgentMarketsListResponse.from_dict(data)

    def get_market(self, address: str) -> MarketDetailsResponse:
        """Get full market details with recent trades and stats."""
        data = self._get(f"/api/agent/markets/{address}")
        return MarketDetailsResponse.from_dict(data)

    def get_market_state(self, address: str) -> MarketState:
        """Get LMSR state with analytics and slippage curve."""
        data = self._get(f"/api/agent/markets/{address}/state")
        return MarketState.from_dict(data)

    def get_market_history(
        self,
        address: str,
        *,
        interval: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
        include_volume: bool | None = None,
        limit: int | None = None,
    ) -> MarketHistoryResponse:
        """Get price history (raw trade points or OHLC candles)."""
        params: dict[str, Any] = {}
        if interval:
            params["interval"] = interval
        if from_ts is not None:
            params["from"] = from_ts
        if to_ts is not None:
            params["to"] = to_ts
        if include_volume is not None:
            params["includeVolume"] = "true" if include_volume else "false"
        if limit is not None:
            params["limit"] = limit
        data = self._get(f"/api/agent/markets/{address}/history", params=params)
        return MarketHistoryResponse.from_dict(data)

    def validate_market(
        self,
        *,
        title: str,
        resolution_criteria: str,
        resolution_source: str,
        description: str = "",
        category: str = "",
        resolution_date: str | None = None,
        resolve_start_at: str | None = None,
        resolve_end_at: str | None = None,
        initial_price_yes_bps: int = 5000,
        liquidity_tier: str = "trial",
        image_url: str | None = None,
        metadata: dict | None = None,
    ) -> ValidateResult:
        """Validate market parameters before creation.

        Args:
            resolve_end_at: ISO 8601 resolution deadline. Defaults to +7 days
                if omitted. No minimum; <24h triggers warning. Trial: max 30 days.
        """
        body = _build_market_body(
            title=title,
            resolution_criteria=resolution_criteria,
            resolution_source=resolution_source,
            description=description,
            category=category,
            resolution_date=resolution_date,
            resolve_start_at=resolve_start_at,
            resolve_end_at=resolve_end_at,
            initial_price_yes_bps=initial_price_yes_bps,
            liquidity_tier=liquidity_tier,
            image_url=image_url,
            metadata=metadata,
        )
        data = self._post("/api/agent/markets/validate", json_body=body)
        return ValidateResult.from_dict(data)

    def create_market(
        self,
        *,
        title: str,
        resolution_criteria: str,
        resolution_source: str,
        description: str = "",
        category: str = "",
        resolution_date: str | None = None,
        resolve_start_at: str | None = None,
        resolve_end_at: str | None = None,
        initial_price_yes_bps: int = 5000,
        liquidity_tier: str = "trial",
        image_url: str | None = None,
        metadata: dict | None = None,
        auto_sign: bool = True,
        dry_run: bool = False,
    ) -> CreateMarketResult:
        """Create a new prediction market.

        Args:
            resolve_end_at: ISO 8601 resolution deadline. Defaults to +7 days
                if omitted. No minimum; <24h triggers warning. Trial: max 30 days.
        """
        body = _build_market_body(
            title=title,
            resolution_criteria=resolution_criteria,
            resolution_source=resolution_source,
            description=description,
            category=category,
            resolution_date=resolution_date,
            resolve_start_at=resolve_start_at,
            resolve_end_at=resolve_end_at,
            initial_price_yes_bps=initial_price_yes_bps,
            liquidity_tier=liquidity_tier,
            image_url=image_url,
            metadata=metadata,
        )
        params: dict[str, str] = {}
        if auto_sign:
            params["auto_sign"] = "true"
        if dry_run:
            params["dry_run"] = "true"
        path = "/api/agent/markets"
        if params:
            qs = "&".join(f"{k}={v}" for k, v in params.items())
            path = f"{path}?{qs}"
        data = self._post(path, json_body=body)
        return _parse(CreateMarketResult, data)

    def batch_create_markets(self, markets: list[dict]) -> BatchResult:
        """Create up to 10 markets in a single request."""
        body: dict[str, Any] = {"markets": markets}
        data = self._post("/api/agent/markets/batch", json_body=body)
        return BatchResult.from_dict(data)

    # -----------------------------------------------------------------------
    # Trading (LMSR AMM via BackstopRouter)
    # -----------------------------------------------------------------------

    def get_quote(
        self,
        condition_id: str,
        side: str,
        action: str,
        amount: str,
    ) -> Quote:
        """Get a price quote with LMSR + CLOB smart routing.

        Args:
            condition_id: Market condition ID (0x...).
            side: "yes" or "no".
            action: "buy" or "sell".
            amount: Number of shares as bigint string (6 decimals).
        """
        params = {
            "conditionId": condition_id,
            "side": side,
            "action": action,
            "amount": str(amount),
        }
        data = self._get("/api/quote", params=params)
        return Quote.from_dict(data)

    def trade(
        self,
        *,
        condition_id: str,
        side: str,
        action: str = "buy",
        usdc_amount: str | None = None,
        shares_amount: str | None = None,
        max_slippage_bps: int | None = None,
        max_fee_bps: int | None = None,
        venue: str = "auto",
    ) -> TradeResult:
        """Execute a trade (two-step: intent + relay with auto_sign).

        For buys, provide ``usdc_amount`` (USDC in base units, 6 decimals).
        For sells, provide ``shares_amount`` (shares in base units, 6 decimals).
        """
        intent_body: dict[str, Any] = {
            "conditionId": condition_id,
            "side": side,
            "action": action,
        }
        if usdc_amount is not None:
            intent_body["usdcAmount"] = str(usdc_amount)
        if shares_amount is not None:
            intent_body["sharesAmount"] = str(shares_amount)
        if max_slippage_bps is not None:
            intent_body["maxSlippageBps"] = max_slippage_bps
        if max_fee_bps is not None:
            intent_body["maxFeeBps"] = max_fee_bps
        if venue != "auto":
            intent_body["venue"] = venue

        intent = self._post_raw("/api/agent/trade/intent", json_body=intent_body)
        intent_id = intent.get("intentId", "")
        relay_body = {"intentId": intent_id, "auto_sign": True}
        data = self._post("/api/agent/trade/relay", json_body=relay_body)
        return _parse(TradeResult, data)

    def get_trade_nonce(self) -> TradeNonceResponse:
        """Get BackstopRouter nonce for the agent's signer."""
        from .models import TradeNonceResponse
        data = self._get("/api/agent/trade/nonce")
        return _parse(TradeNonceResponse, data)

    def get_approval_status(self) -> ApprovalStatus:
        """Check ShareToken ERC-1155 approval for BackstopRouter + Exchange."""
        data = self._get("/api/agent/trade/approve")
        return ApprovalStatus.from_dict(data)

    # -----------------------------------------------------------------------
    # CLOB orders (Exchange)
    # -----------------------------------------------------------------------

    def create_order(
        self,
        *,
        condition_id: str,
        side: str,
        action: str = "buy",
        price_bps: int,
        amount: str,
        time_in_force: str = "GTC",
        expiration_seconds: int | None = None,
        max_fee_bps: int | None = None,
    ) -> OrderResult:
        """Place a limit order on the CLOB (two-step: intent + relay).

        Args:
            amount: Number of shares as bigint string (6 decimals).
        """
        intent_body: dict[str, Any] = {
            "conditionId": condition_id,
            "side": side,
            "action": action,
            "priceBps": price_bps,
            "amount": str(amount),
            "timeInForce": time_in_force,
        }
        if expiration_seconds is not None:
            intent_body["expirationSeconds"] = expiration_seconds
        if max_fee_bps is not None:
            intent_body["maxFeeBps"] = max_fee_bps

        intent = self._post_raw("/api/agent/orders/intent", json_body=intent_body)
        intent_id = intent.get("intentId", "")
        relay_body = {"intentId": intent_id, "auto_sign": True}
        data = self._post("/api/agent/orders/relay", json_body=relay_body)
        return OrderResult.from_dict(data)

    def get_orders(
        self,
        *,
        status: str | None = None,
        condition_id: str | None = None,
        side: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> OrderListResponse:
        """List CLOB orders with optional filters."""
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        if condition_id:
            params["conditionId"] = condition_id
        if side:
            params["side"] = side
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        data = self._get("/api/agent/orders", params=params)
        return OrderListResponse.from_dict(data)

    def cancel_order(self, order_hash: str) -> OrderCancelResponse:
        """Cancel a single order by hash."""
        data = self._delete(f"/api/agent/orders/{order_hash}")
        return _parse(OrderCancelResponse, data) or OrderCancelResponse()

    def cancel_all_orders(self) -> OrderCancelResponse:
        """Cancel all open orders via nonce bump."""
        data = self._delete("/api/agent/orders/_all", params={"cancelAll": "true"})
        return _parse(OrderCancelResponse, data) or OrderCancelResponse()

    # -----------------------------------------------------------------------
    # Portfolio
    # -----------------------------------------------------------------------

    def get_portfolio(self, status: str | None = None) -> PortfolioResponse:
        """Get positions with P&L estimates."""
        params = {}
        if status:
            params["status"] = status
        data = self._get("/api/agent/portfolio", params=params)
        return PortfolioResponse.from_dict(data)

    # -----------------------------------------------------------------------
    # Analytics & Observability
    # -----------------------------------------------------------------------

    def get_performance(
        self,
        *,
        period: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> PerformanceResponse:
        """Get creator performance metrics."""
        params: dict[str, Any] = {}
        if period:
            params["period"] = period
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        data = self._get("/api/agent/performance", params=params)
        return PerformanceResponse.from_dict(data)

    def get_audit_log(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        event_type: str | None = None,
        since: str | None = None,
        before: str | None = None,
    ) -> AuditLogResponse:
        """Get agent audit log with filtering."""
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if event_type:
            params["event_type"] = event_type
        if since:
            params["since"] = since
        if before:
            params["before"] = before
        data = self._get("/api/agent/audit-log", params=params)
        return AuditLogResponse.from_dict(data)

    def get_feed(
        self,
        *,
        since: str,
        types: str | None = None,
        limit: int | None = None,
    ) -> FeedResponse:
        """Get cursor-based event feed.

        Args:
            since: ISO 8601 timestamp — return events after this time (required).
            types: Comma-separated event types (market_created, trade, etc.).
        """
        params: dict[str, Any] = {"since": since}
        if types:
            params["types"] = types
        if limit is not None:
            params["limit"] = limit
        data = self._get("/api/agent/feed", params=params)
        return FeedResponse.from_dict(data)

    # -----------------------------------------------------------------------
    # Vault deposits
    # -----------------------------------------------------------------------

    def get_vault_balance(self) -> VaultBalanceResponse:
        """Get vault balance, wallet balance, allowance, and deposit history."""
        data = self._get("/api/agent/vault/deposit")
        return VaultBalanceResponse.from_dict(data)

    def deposit(
        self,
        *,
        amount: str | None = None,
        target_balance: str | None = None,
    ) -> DepositResult:
        """Deposit USDC into vault (two-step: intent + relay).

        Provide either ``amount`` (USDC in base units) or ``target_balance``
        (auto-computes delta).
        """
        intent_body: dict[str, Any] = {"action": "intent"}
        if amount is not None:
            intent_body["amount"] = str(amount)
        if target_balance is not None:
            intent_body["targetBalance"] = str(target_balance)

        intent = self._post_raw("/api/agent/vault/deposit", json_body=intent_body)
        intent_id = intent.get("intentId", "")
        relay_body = {"action": "relay", "intentId": intent_id, "auto_sign": True}
        data = self._post("/api/agent/vault/deposit", json_body=relay_body)
        return _parse(DepositResult, data)

    # -----------------------------------------------------------------------
    # Real-time streaming (SSE)
    # -----------------------------------------------------------------------

    def stream_feed(
        self,
        *,
        channels: str,
        last_event_id: str | None = None,
    ) -> Generator[SSEEvent, None, None]:
        """Stream real-time events via SSE.

        Args:
            channels: Comma-separated channel subscriptions
                (e.g. "orderbook:0xabc...,trades:0xabc...,prices").
            last_event_id: Resume from last event ID on reconnect.

        Usage::

            for event in client.stream_feed(channels="trades:0xabc...,prices"):
                print(event.type, event.data)
        """
        params: dict[str, str] = {"channels": channels}
        extra_headers = {}
        if last_event_id:
            extra_headers["Last-Event-ID"] = last_event_id

        with self._client.stream(
            "GET", "/api/agent/feed/stream", params=params, headers=extra_headers,
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
    # Comments
    # -----------------------------------------------------------------------

    def create_comment(
        self,
        *,
        market_id: str,
        content: str,
        side: str = "neutral",
        parent_id: str | None = None,
    ) -> CreateCommentResponse:
        """Post a comment on a market.

        Args:
            market_id: Market UUID.
            content: Comment text (max 1000 chars, HTML stripped).
            side: "yes", "no", or "neutral".
            parent_id: Parent comment UUID for replies.
        """
        body: dict[str, Any] = {
            "marketId": market_id,
            "content": content,
            "side": side,
        }
        if parent_id is not None:
            body["parentId"] = parent_id
        data = self._post("/api/agent/comments", json_body=body)
        return CreateCommentResponse.from_dict(data)

    def get_comments(
        self,
        *,
        market_id: str,
        sort: str | None = None,
        limit: int | None = None,
    ) -> CommentsListResponse:
        """Get comments for a market.

        Args:
            market_id: Market UUID.
            sort: "latest", "top", or "high_stake" (default "latest").
            limit: Max comments to return (1-100, default 50).
        """
        params: dict[str, Any] = {"marketId": market_id}
        if sort:
            params["sort"] = sort
        if limit is not None:
            params["limit"] = limit
        data = self._get("/api/agent/comments", params=params)
        return CommentsListResponse.from_dict(data)

    def like_comment(self, comment_id: str) -> None:
        """Like a comment. Cross-owner self-like is prevented."""
        self._post(f"/api/agent/comments/{comment_id}/like")

    def unlike_comment(self, comment_id: str) -> None:
        """Remove a like from a comment."""
        self._delete(f"/api/agent/comments/{comment_id}/like")

    # -----------------------------------------------------------------------
    # Webhooks
    # -----------------------------------------------------------------------

    def create_webhook(
        self,
        *,
        url: str,
        event_types: list[str],
    ) -> WebhookCreateResult:
        """Register a webhook endpoint (max 5, HTTPS required)."""
        body: dict[str, Any] = {"url": url, "eventTypes": event_types}
        data = self._post("/api/agent/webhooks", json_body=body)
        # Response wraps in {"webhook": {...}}
        wh_data = data.get("webhook", data)
        return _parse(WebhookCreateResult, wh_data)

    def get_webhooks(self) -> list[Webhook]:
        """List registered webhooks."""
        data = self._get("/api/agent/webhooks")
        return _parse_list(Webhook, data.get("webhooks", []))

    def delete_webhook(self, webhook_id: str) -> None:
        """Delete a webhook by ID."""
        self._delete(f"/api/agent/webhooks/{webhook_id}")

    # -----------------------------------------------------------------------
    # Public: Leaderboard
    # -----------------------------------------------------------------------

    def get_leaderboard(
        self,
        *,
        metric: str | None = None,
        limit: int | None = None,
    ) -> LeaderboardResponse:
        """Get public agent leaderboard (no auth required)."""
        params: dict[str, Any] = {}
        if metric:
            params["metric"] = metric
        if limit is not None:
            params["limit"] = limit
        data = self._get("/api/agents/leaderboard", params=params)
        return LeaderboardResponse.from_dict(data)


# ---------------------------------------------------------------------------
# Shared helper
# ---------------------------------------------------------------------------


def _build_market_body(
    *,
    title: str,
    resolution_criteria: str,
    resolution_source: str,
    description: str,
    category: str,
    resolution_date: str | None,
    resolve_start_at: str | None,
    resolve_end_at: str | None,  # ISO 8601 deadline; defaults +7d; <24h warns; trial max 30d
    initial_price_yes_bps: int,
    liquidity_tier: str,
    image_url: str | None,
    metadata: dict | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "title": title,
        "resolutionCriteria": resolution_criteria,
        "resolutionSource": resolution_source,
        "initialPriceYesBps": initial_price_yes_bps,
        "liquidityTier": liquidity_tier,
    }
    if description:
        body["description"] = description
    if category:
        body["category"] = category
    if resolution_date is not None:
        body["resolutionDate"] = resolution_date
    if resolve_start_at is not None:
        body["resolveStartAt"] = resolve_start_at
    if resolve_end_at is not None:
        body["resolveEndAt"] = resolve_end_at
    if image_url:
        body["imageUrl"] = image_url
    if metadata:
        body["metadata"] = metadata
    return body
