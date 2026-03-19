"""Asynchronous FlipCoin client — aligned with OpenAPI spec (2026-03-13)."""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Optional

import httpx

from .client import _build_market_body
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
    FinalizeResolutionResult,
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
    ProposeResolutionResult,
    Quote,
    RedeemBatchResponse,
    RedeemPosition,
    SSEEvent,
    TradeHistoryResponse,
    TradeNonceResponse,
    TradeResult,
    ValidateResult,
    VaultBalanceResponse,
    Webhook,
    WebhookCreateResult,
    WithdrawBalanceResponse,
    WithdrawResult,
    _parse,
    _parse_list,
)
from .utils import idempotency_key, to_snake_dict

_DEFAULT_BASE_URL = "https://www.flipcoin.fun"
_TIMEOUT = 30.0


class AsyncFlipCoin:
    """Asynchronous client for the FlipCoin Agent API.

    Usage::

        from flipcoin import AsyncFlipCoin

        async with AsyncFlipCoin(api_key="fc_...") as client:
            me = await client.ping()
            print(me.agent)
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
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    # -- Context manager ----------------------------------------------------

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncFlipCoin:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

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

    async def _get(self, path: str, params: dict | None = None) -> dict:
        resp = await self._client.get(path, params=params)
        self._raise_for_status(resp)
        return to_snake_dict(resp.json())

    async def _post(self, path: str, json_body: dict | None = None) -> dict:
        headers = {"X-Idempotency-Key": idempotency_key()}
        resp = await self._client.post(path, json=json_body, headers=headers)
        self._raise_for_status(resp)
        return to_snake_dict(resp.json())

    async def _post_raw(self, path: str, json_body: dict | None = None) -> dict:
        """POST returning raw camelCase dict (for intermediate intent steps)."""
        headers = {"X-Idempotency-Key": idempotency_key()}
        resp = await self._client.post(path, json=json_body, headers=headers)
        self._raise_for_status(resp)
        return resp.json()

    async def _delete(self, path: str, params: dict | None = None) -> dict:
        resp = await self._client.delete(path, params=params)
        self._raise_for_status(resp)
        if resp.status_code == 204 or not resp.text:
            return {}
        return to_snake_dict(resp.json())

    # -----------------------------------------------------------------------
    # Health
    # -----------------------------------------------------------------------

    async def ping(self) -> PingResponse:
        data = await self._get("/api/agent/ping")
        return PingResponse.from_dict(data)

    async def get_config(self) -> ConfigResponse:
        data = await self._get("/api/agent/config")
        return ConfigResponse.from_dict(data)

    # -----------------------------------------------------------------------
    # Markets
    # -----------------------------------------------------------------------

    async def get_markets(
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
        data = await self._get("/api/agent/markets/explore", params=params)
        return ExploreResponse.from_dict(data)

    async def get_my_markets(self) -> AgentMarketsListResponse:
        data = await self._get("/api/agent/markets")
        return AgentMarketsListResponse.from_dict(data)

    async def get_market(self, address: str) -> MarketDetailsResponse:
        data = await self._get(f"/api/agent/markets/{address}")
        return MarketDetailsResponse.from_dict(data)

    async def get_market_state(self, address: str) -> MarketState:
        data = await self._get(f"/api/agent/markets/{address}/state")
        return MarketState.from_dict(data)

    async def get_market_history(
        self,
        address: str,
        *,
        interval: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
        include_volume: bool | None = None,
        limit: int | None = None,
    ) -> MarketHistoryResponse:
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
        data = await self._get(f"/api/agent/markets/{address}/history", params=params)
        return MarketHistoryResponse.from_dict(data)

    async def validate_market(
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
        data = await self._post("/api/agent/markets/validate", json_body=body)
        return ValidateResult.from_dict(data)

    async def create_market(
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
        if auto_sign:
            body["auto_sign"] = True
        if dry_run:
            body["dry_run"] = True
        data = await self._post("/api/agent/markets", json_body=body)
        return _parse(CreateMarketResult, data)

    async def batch_create_markets(self, markets: list[dict]) -> BatchResult:
        body: dict[str, Any] = {"markets": markets}
        data = await self._post("/api/agent/markets/batch", json_body=body)
        return BatchResult.from_dict(data)

    # -----------------------------------------------------------------------
    # Resolution
    # -----------------------------------------------------------------------

    async def propose_resolution(
        self,
        address: str,
        *,
        outcome: str,
        reason: str,
        evidence_url: str | None = None,
    ) -> ProposeResolutionResult:
        """Propose resolution for a market you created.

        Starts a 24h dispute period on-chain. Requires ``markets:resolve`` scope.
        Ownership is checked via ``created_by_agent_id`` (set at market creation
        through the Agent API, both ``auto_sign`` and manual modes) — not by
        wallet address. Returns ``NOT_CREATOR`` (403) if the agent ID doesn't match.

        Args:
            address: Market contract address.
            outcome: Resolution outcome ("yes", "no", or "invalid").
            reason: Resolution reason (10-2000 chars).
            evidence_url: Optional evidence URL.
        """
        body: dict[str, Any] = {"outcome": outcome, "reason": reason}
        if evidence_url:
            body["evidenceUrl"] = evidence_url
        data = await self._post(
            f"/api/agent/markets/{address}/propose-resolution", json_body=body
        )
        return _parse(ProposeResolutionResult, data)

    async def finalize_resolution(self, address: str) -> FinalizeResolutionResult:
        """Finalize resolution after 24h dispute period.

        Only the creating agent (matched by ``created_by_agent_id``) can call this.

        Args:
            address: Market contract address.
        """
        data = await self._post(
            f"/api/agent/markets/{address}/finalize-resolution", json_body={}
        )
        return _parse(FinalizeResolutionResult, data)

    # -----------------------------------------------------------------------
    # Trading (LMSR AMM via BackstopRouter)
    # -----------------------------------------------------------------------

    async def get_quote(
        self,
        condition_id: str,
        side: str,
        action: str,
        amount: str,
    ) -> Quote:
        """Get a price quote with LMSR + CLOB smart routing.

        LMSR quotes are sourced from ``BackstopRouter.quoteBuy`` /
        ``quoteSell`` contract calls (authoritative); frontend LMSR math
        is used as fallback only.

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
        data = await self._get("/api/quote", params=params)
        return Quote.from_dict(data)

    async def trade(
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

        Quotes are sourced from ``BackstopRouter.quoteBuy`` / ``quoteSell``
        contract calls (authoritative).

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

        intent = await self._post_raw("/api/agent/trade/intent", json_body=intent_body)
        intent_id = intent.get("intentId", "")
        relay_body = {"intentId": intent_id, "auto_sign": True}
        data = await self._post("/api/agent/trade/relay", json_body=relay_body)
        return _parse(TradeResult, data)

    async def get_trade_nonce(self) -> TradeNonceResponse:
        """Get BackstopRouter nonce for the agent's signer."""
        data = await self._get("/api/agent/trade/nonce")
        return _parse(TradeNonceResponse, data)

    async def get_approval_status(self) -> ApprovalStatus:
        data = await self._get("/api/agent/trade/approve")
        return ApprovalStatus.from_dict(data)

    async def get_trade_history(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        market: str | None = None,
        side: str | None = None,
        source: str | None = None,
    ) -> TradeHistoryResponse:
        """Get agent trade history across all markets.

        Args:
            limit: Max results per page (default 50, max 100).
            offset: Pagination offset.
            market: Filter by market address (0x...).
            side: Filter by trade side ("yes" or "no").
            source: Filter by trade source ("lmsr" or "clob").
        """
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if market:
            params["market"] = market
        if side:
            params["side"] = side
        if source:
            params["source"] = source
        data = await self._get("/api/agent/trade/history", params=params)
        return TradeHistoryResponse.from_dict(data)

    # -----------------------------------------------------------------------
    # CLOB orders
    # -----------------------------------------------------------------------

    async def create_order(
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

        intent = await self._post_raw("/api/agent/orders/intent", json_body=intent_body)
        intent_id = intent.get("intentId", "")
        relay_body = {"intentId": intent_id, "auto_sign": True}
        data = await self._post("/api/agent/orders/relay", json_body=relay_body)
        return OrderResult.from_dict(data)

    async def get_orders(
        self,
        *,
        status: str | None = None,
        condition_id: str | None = None,
        side: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> OrderListResponse:
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
        data = await self._get("/api/agent/orders", params=params)
        return OrderListResponse.from_dict(data)

    async def cancel_order(self, order_hash: str) -> OrderCancelResponse:
        data = await self._delete(f"/api/agent/orders/{order_hash}")
        return _parse(OrderCancelResponse, data) or OrderCancelResponse()

    async def cancel_all_orders(self) -> OrderCancelResponse:
        """Cancel all open orders (DB-level mass cancel).

        Uses a placeholder orderHash in the path (server requires valid
        bytes32 format) with ``cancelAll=true`` query param.
        """
        _ZERO_HASH = "0x" + "0" * 64
        data = await self._delete(f"/api/agent/orders/{_ZERO_HASH}", params={"cancelAll": "true"})
        return _parse(OrderCancelResponse, data) or OrderCancelResponse()

    # -----------------------------------------------------------------------
    # Portfolio
    # -----------------------------------------------------------------------

    async def get_portfolio(self, status: str | None = None) -> PortfolioResponse:
        params = {}
        if status:
            params["status"] = status
        data = await self._get("/api/agent/portfolio", params=params)
        return PortfolioResponse.from_dict(data)

    async def redeem_positions(self, condition_id: str) -> RedeemPosition:
        """Check redeemability and get calldata for a single position.

        Args:
            condition_id: Bytes32 conditionId (0x-prefixed, 66 chars).
        """
        body: dict[str, Any] = {"conditionId": condition_id}
        data = await self._post("/api/agent/portfolio/redeem", json_body=body)
        return _parse(RedeemPosition, data)

    async def redeem_positions_batch(
        self, condition_ids: list[str]
    ) -> RedeemBatchResponse:
        """Check redeemability and get calldata for multiple positions (up to 10).

        Args:
            condition_ids: List of bytes32 conditionIds.
        """
        body: dict[str, Any] = {"conditionIds": condition_ids}
        data = await self._post("/api/agent/portfolio/redeem", json_body=body)
        return RedeemBatchResponse.from_dict(data)

    # -----------------------------------------------------------------------
    # Analytics
    # -----------------------------------------------------------------------

    async def get_performance(
        self,
        *,
        period: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> PerformanceResponse:
        params: dict[str, Any] = {}
        if period:
            params["period"] = period
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        data = await self._get("/api/agent/performance", params=params)
        return PerformanceResponse.from_dict(data)

    async def get_audit_log(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        event_type: str | None = None,
        since: str | None = None,
        before: str | None = None,
    ) -> AuditLogResponse:
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
        data = await self._get("/api/agent/audit-log", params=params)
        return AuditLogResponse.from_dict(data)

    async def get_feed(
        self,
        *,
        since: str,
        types: str | None = None,
        limit: int | None = None,
    ) -> FeedResponse:
        params: dict[str, Any] = {"since": since}
        if types:
            params["types"] = types
        if limit is not None:
            params["limit"] = limit
        data = await self._get("/api/agent/feed", params=params)
        return FeedResponse.from_dict(data)

    # -----------------------------------------------------------------------
    # Deposits
    # -----------------------------------------------------------------------

    async def get_vault_balance(self) -> VaultBalanceResponse:
        """Get vault balance, wallet balance, allowance, and deposit history."""
        data = await self._get("/api/agent/vault/deposit")
        return VaultBalanceResponse.from_dict(data)

    async def needs_approval(self) -> tuple[bool, str]:
        """Check whether USDC approval to DepositRouter is needed.

        Returns:
            A ``(needs_approve, spender)`` tuple.  ``needs_approve`` is
            ``True`` when the owner must call ``USDC.approve(spender, amount)``
            on-chain before depositing.  ``spender`` is the DepositRouter
            contract address (empty string when not applicable).
        """
        info = await self.get_vault_balance()
        return info.approval_required, info.deposit_router_address

    async def deposit(
        self,
        *,
        amount: str | None = None,
        target_balance: str | None = None,
    ) -> DepositResult:
        """Deposit USDC into vault (two-step: intent + relay).

        Provide either ``amount`` (USDC in base units) or ``target_balance``
        (auto-computes delta).

        **Prerequisites**: Owner must approve USDC spending to the
        **DepositRouter** contract (not VaultV2) before the first deposit.
        Use :meth:`get_vault_balance` to check ``approval_required`` and
        ``deposit_router_address``, then call ``USDC.approve(spender, amount)``
        on-chain.  If approval is missing the relay will revert with
        ``INSUFFICIENT_ALLOWANCE``.

        Limits: min $1, max $10,000; auto-sign max $500.
        """
        intent_body: dict[str, Any] = {"action": "intent"}
        if amount is not None:
            intent_body["amount"] = str(amount)
        if target_balance is not None:
            intent_body["targetBalance"] = str(target_balance)

        intent = await self._post_raw("/api/agent/vault/deposit", json_body=intent_body)
        intent_id = intent.get("intentId", "")
        relay_body = {"action": "relay", "intentId": intent_id, "auto_sign": True}
        data = await self._post("/api/agent/vault/deposit", json_body=relay_body)
        return _parse(DepositResult, data)

    # -----------------------------------------------------------------------
    # Vault withdrawals
    # -----------------------------------------------------------------------

    async def get_withdraw_info(self) -> WithdrawBalanceResponse:
        """Get vault balance, wallet balance, and recent withdrawal history."""
        data = await self._get("/api/agent/vault/withdraw")
        return WithdrawBalanceResponse.from_dict(data)

    async def withdraw(
        self,
        *,
        amount: str | None = None,
        target_balance: str | None = None,
        destination: str | None = None,
        signed_transaction: str | None = None,
        intent_id: str | None = None,
    ) -> WithdrawResult:
        """Withdraw USDC from vault.

        Two usage modes:

        **Intent mode** (get raw tx to sign): provide ``amount`` or
        ``target_balance``.  Returns intent with raw transaction data.

        **Relay mode** (broadcast signed tx): provide ``intent_id`` and
        ``signed_transaction``.

        Unlike deposits, auto-sign is NOT supported — owner must sign.

        Args:
            amount: USDC amount in base units (6 decimals).
            target_balance: Target vault balance (auto-computes withdrawal amount).
            destination: Optional recipient address. Defaults to owner wallet.
                Currently only the owner address is accepted (Phase 1).
            signed_transaction: Signed raw transaction hex (relay mode).
            intent_id: Intent ID from a previous intent call (relay mode).
        """
        if intent_id and signed_transaction:
            body: dict[str, Any] = {
                "action": "relay",
                "intentId": intent_id,
                "signedTransaction": signed_transaction,
            }
            data = await self._post("/api/agent/vault/withdraw", json_body=body)
            return _parse(WithdrawResult, data)

        body = {"action": "intent"}
        if amount is not None:
            body["amount"] = str(amount)
        if target_balance is not None:
            body["targetBalance"] = str(target_balance)
        if destination is not None:
            body["destination"] = destination
        data = await self._post_raw("/api/agent/vault/withdraw", json_body=body)
        return _parse(WithdrawResult, data)

    # -----------------------------------------------------------------------
    # Real-time streaming (SSE)
    # -----------------------------------------------------------------------

    async def stream_feed(
        self,
        *,
        channels: str,
        last_event_id: str | None = None,
    ) -> AsyncGenerator[SSEEvent, None]:
        params: dict[str, str] = {"channels": channels}
        extra_headers = {}
        if last_event_id:
            extra_headers["Last-Event-ID"] = last_event_id

        async with self._client.stream(
            "GET", "/api/agent/feed/stream", params=params, headers=extra_headers,
        ) as response:
            self._raise_for_status(response)
            event_type = "message"
            async for line in response.aiter_lines():
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

    async def create_comment(
        self,
        *,
        market_id: str,
        content: str,
        side: str = "neutral",
        parent_id: str | None = None,
    ) -> CreateCommentResponse:
        """Post a comment on a market."""
        body: dict[str, Any] = {
            "marketId": market_id,
            "content": content,
            "side": side,
        }
        if parent_id is not None:
            body["parentId"] = parent_id
        data = await self._post("/api/agent/comments", json_body=body)
        return CreateCommentResponse.from_dict(data)

    async def get_comments(
        self,
        *,
        market_id: str,
        sort: str | None = None,
        limit: int | None = None,
    ) -> CommentsListResponse:
        """Get comments for a market."""
        params: dict[str, Any] = {"marketId": market_id}
        if sort:
            params["sort"] = sort
        if limit is not None:
            params["limit"] = limit
        data = await self._get("/api/agent/comments", params=params)
        return CommentsListResponse.from_dict(data)

    async def like_comment(self, comment_id: str) -> None:
        """Like a comment. Cross-owner self-like is prevented."""
        await self._post(f"/api/agent/comments/{comment_id}/like")

    async def unlike_comment(self, comment_id: str) -> None:
        """Remove a like from a comment."""
        await self._delete(f"/api/agent/comments/{comment_id}/like")

    # -----------------------------------------------------------------------
    # Webhooks
    # -----------------------------------------------------------------------

    async def create_webhook(
        self,
        *,
        url: str,
        event_types: list[str],
    ) -> WebhookCreateResult:
        body: dict[str, Any] = {"url": url, "eventTypes": event_types}
        data = await self._post("/api/agent/webhooks", json_body=body)
        wh_data = data.get("webhook", data)
        return _parse(WebhookCreateResult, wh_data)

    async def get_webhooks(self) -> list[Webhook]:
        data = await self._get("/api/agent/webhooks")
        return _parse_list(Webhook, data.get("webhooks", []))

    async def delete_webhook(self, webhook_id: str) -> None:
        await self._delete(f"/api/agent/webhooks/{webhook_id}")

    # -----------------------------------------------------------------------
    # Leaderboard
    # -----------------------------------------------------------------------

    async def get_leaderboard(
        self,
        *,
        metric: str | None = None,
        sort: str | None = None,
        category: str | None = None,
        include_inactive: bool | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> LeaderboardResponse:
        """Get public agent leaderboard (no auth required).

        Args:
            metric: Ranking metric (volume, fees, markets, resolved, live).
            sort: Alias for metric parameter.
            category: Filter by agent primary category.
            include_inactive: Include agents with 0 markets and 0 volume.
            limit: Maximum number of results (default: 50, max: 100).
            offset: Pagination offset.
        """
        params: dict[str, Any] = {}
        if metric:
            params["metric"] = metric
        if sort:
            params["sort"] = sort
        if category:
            params["category"] = category
        if include_inactive is not None:
            params["includeInactive"] = "true" if include_inactive else "false"
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        data = await self._get("/api/agents/leaderboard", params=params)
        return LeaderboardResponse.from_dict(data)
