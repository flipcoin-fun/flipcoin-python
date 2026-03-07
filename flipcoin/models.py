"""Data models for FlipCoin SDK responses — aligned with OpenAPI spec (2026-03-04)."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, List, Optional, Type, TypeVar

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Helper: create a dataclass from a dict, ignoring unknown keys
# ---------------------------------------------------------------------------


def _parse(cls: Type[T], data: dict | None) -> T | None:
    if data is None:
        return None
    known = {f.name for f in dataclasses.fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in known})


def _parse_list(cls: Type[T], items: list | None) -> list[T]:
    if not items:
        return []
    return [_parse(cls, item) for item in items if isinstance(item, dict)]


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class FlipCoinError(Exception):
    """Error returned by the FlipCoin API.

    Attributes:
        status_code: HTTP status code.
        error_code: Machine-readable error code (e.g. RELAY_NOT_CONFIGURED).
        details: Additional context (dict or None).
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 0,
        error_code: str = "UNKNOWN",
        details: Any = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.details = details

    @property
    def code(self) -> str:
        """Alias for error_code (backward compat)."""
        return self.error_code

    def __repr__(self) -> str:
        return f"FlipCoinError({self.status_code}, error_code={self.error_code!r}, message={str(self)!r})"


# ---------------------------------------------------------------------------
# Pagination (reusable)
# ---------------------------------------------------------------------------


@dataclass
class Pagination:
    offset: int = 0
    limit: int = 50
    total: int = 0
    has_more: bool = False


# ---------------------------------------------------------------------------
# Health — GET /api/agent/ping
# ---------------------------------------------------------------------------


@dataclass
class RateLimitBucket:
    remaining: int = 0
    limit: int = 0
    window: str = ""
    reset_at: str = ""


@dataclass
class DailyMarkets:
    remaining: int = 0
    limit: int = 0
    reset_at: str = ""


@dataclass
class RateLimitInfo:
    read: Optional[RateLimitBucket] = None
    write: Optional[RateLimitBucket] = None
    create: Optional[RateLimitBucket] = None
    trade: Optional[RateLimitBucket] = None
    daily_markets: Optional[DailyMarkets] = None

    @classmethod
    def from_dict(cls, data: dict | None) -> Optional[RateLimitInfo]:
        if not data:
            return None
        return cls(
            read=_parse(RateLimitBucket, data.get("read")),
            write=_parse(RateLimitBucket, data.get("write")),
            create=_parse(RateLimitBucket, data.get("create")),
            trade=_parse(RateLimitBucket, data.get("trade")),
            daily_markets=_parse(DailyMarkets, data.get("daily_markets")),
        )


@dataclass
class EarlyAdopterInfo:
    is_early_adopter: bool = False
    activation_rank: Optional[int] = None
    slots_total: int = 0
    slots_remaining: int = 0


@dataclass
class SeedSubsidyInfo:
    eligible: bool = False
    total: int = 0
    used: int = 0
    remaining: int = 0


@dataclass
class FeeInfo:
    tier: str = ""
    creator_fee_bps: int = 0
    protocol_fee_bps: int = 0
    total_fee_bps: int = 0
    resolution_fee_bps: int = 0
    creator_fee_percent: str = ""
    total_fee_percent: str = ""
    early_adopter: Optional[EarlyAdopterInfo] = None
    seed_subsidy: Optional[SeedSubsidyInfo] = None

    @classmethod
    def from_dict(cls, data: dict | None) -> Optional[FeeInfo]:
        if not data:
            return None
        obj = _parse(cls, data)
        if obj:
            if isinstance(data.get("early_adopter"), dict):
                obj.early_adopter = _parse(EarlyAdopterInfo, data["early_adopter"])
            if isinstance(data.get("seed_subsidy"), dict):
                obj.seed_subsidy = _parse(SeedSubsidyInfo, data["seed_subsidy"])
        return obj


@dataclass
class AgentInfo:
    """Agent identity returned by the ping endpoint."""
    name: str = ""


@dataclass
class PingResponse:
    ok: bool = False
    agent: Optional[AgentInfo] = None
    rate_limit: Optional[RateLimitInfo] = None
    fees: Optional[FeeInfo] = None

    @classmethod
    def from_dict(cls, data: dict) -> PingResponse:
        agent_val = data.get("agent")
        agent_info: Optional[AgentInfo] = None
        if isinstance(agent_val, dict):
            agent_info = _parse(AgentInfo, agent_val)
        elif isinstance(agent_val, str):
            agent_info = AgentInfo(name=agent_val)
        return cls(
            ok=data.get("ok", False),
            agent=agent_info,
            rate_limit=RateLimitInfo.from_dict(data.get("rate_limit")),
            fees=FeeInfo.from_dict(data.get("fees")),
        )

    @property
    def agent_name(self) -> str:
        """Convenience accessor for the agent name string."""
        return self.agent.name if self.agent else ""


# ---------------------------------------------------------------------------
# Config — GET /api/agent/config
# ---------------------------------------------------------------------------


@dataclass
class ContractsV1:
    factory: str = ""
    vault: str = ""


@dataclass
class ContractsV2:
    factory: str = ""
    vault: str = ""
    exchange: str = ""
    backstop_router: str = ""
    share_token: str = ""
    delegation_registry: str = ""
    deposit_router: str = ""


@dataclass
class ContractsInfo:
    v1: Optional[ContractsV1] = None
    v2: Optional[ContractsV2] = None

    @classmethod
    def from_dict(cls, data: dict | None) -> Optional[ContractsInfo]:
        if not data:
            return None
        return cls(
            v1=_parse(ContractsV1, data.get("v1")),
            v2=_parse(ContractsV2, data.get("v2")),
        )


@dataclass
class Capabilities:
    relay: bool = False
    auto_sign: bool = False
    session_keys: bool = False
    treasury: bool = False
    deposit: bool = False


@dataclass
class AutoSignLimits:
    max_trade_usdc: str = ""
    max_tx_per_minute: int = 0
    max_deposit_usdc: str = ""
    max_deposit_per_minute: int = 0


@dataclass
class TradingConfig:
    venues: list[str] = field(default_factory=list)
    auto_sign: Optional[AutoSignLimits] = None
    quote_validity_seconds: int = 0

    @classmethod
    def from_dict(cls, data: dict | None) -> Optional[TradingConfig]:
        if not data:
            return None
        obj = _parse(cls, data)
        if obj and isinstance(data.get("auto_sign"), dict):
            obj.auto_sign = _parse(AutoSignLimits, data["auto_sign"])
        return obj


@dataclass
class LimitsInfo:
    min_trade_usdc: str = ""
    max_trade_usdc: str = ""


@dataclass
class VaultConfig:
    min_deposit_usdc: str = ""
    max_deposit_usdc: str = ""


@dataclass
class UnitsConfig:
    usdc_decimals: int = 6
    price_unit: str = "bps"
    volume_definition: str = ""


@dataclass
class ConfigResponse:
    success: bool = False
    chain_id: int = 0
    mode: str = ""
    fee_recipient_policy: str = ""
    contracts: Optional[ContractsInfo] = None
    capabilities: Optional[Capabilities] = None
    limits: Optional[LimitsInfo] = None
    trading: Optional[TradingConfig] = None
    vault: Optional[VaultConfig] = None
    units: Optional[UnitsConfig] = None

    @classmethod
    def from_dict(cls, data: dict) -> ConfigResponse:
        return cls(
            success=data.get("success", False),
            chain_id=data.get("chain_id", 0),
            mode=data.get("mode", ""),
            fee_recipient_policy=data.get("fee_recipient_policy", ""),
            contracts=ContractsInfo.from_dict(data.get("contracts")),
            capabilities=_parse(Capabilities, data.get("capabilities")),
            limits=_parse(LimitsInfo, data.get("limits")),
            trading=TradingConfig.from_dict(data.get("trading")),
            vault=_parse(VaultConfig, data.get("vault")),
            units=_parse(UnitsConfig, data.get("units")),
        )


# ---------------------------------------------------------------------------
# Markets — MarketSummary / MarketDetailsResponse
# ---------------------------------------------------------------------------


@dataclass
class Market:
    """Market summary (from explore or agent markets list)."""
    id: str = ""
    market_addr: str = ""
    condition_id: str = ""
    title: str = ""
    description: str = ""
    status: str = ""
    volume_usdc: float = 0.0
    liquidity_usdc: float = 0.0
    trades_count: int = 0
    created_at: str = ""
    resolve_end_at: str = ""
    resolved_outcome: Optional[bool] = None
    resolution_criteria: str = ""
    resolution_source: str = ""
    resolution_date: str = ""
    category: str = ""
    fingerprint: str = ""
    image_url: Optional[str] = None
    # Extended fields from MarketDetailsResponse
    current_price_yes_bps: int = 0
    current_price_no_bps: int = 0
    agent_metadata: Optional[dict] = None
    resolution: Optional[dict] = None


@dataclass
class ResolutionInfo:
    proposed_outcome: Optional[str] = None
    proposed_at: Optional[str] = None
    finalize_after: Optional[str] = None
    can_finalize: bool = False
    dispute_time_remaining: int = 0
    is_disputed: bool = False


@dataclass
class Trade:
    trader: str = ""
    side: str = ""
    amount_usdc: float = 0.0
    shares: float = 0.0
    fee: float = 0.0
    price_yes_bps: int = 0
    tx_hash: str = ""
    block_number: int = 0
    event_time: str = ""


@dataclass
class MarketStats:
    volume24h: str = "0"
    trades24h: int = 0


@dataclass
class MarketDetailsResponse:
    market: Optional[Market] = None
    recent_trades: list[Trade] = field(default_factory=list)
    stats: Optional[MarketStats] = None

    @classmethod
    def from_dict(cls, data: dict) -> MarketDetailsResponse:
        market_data = data.get("market", data)
        return cls(
            market=_parse(Market, market_data) if isinstance(market_data, dict) else None,
            recent_trades=_parse_list(Trade, data.get("recent_trades")),
            stats=_parse(MarketStats, data.get("stats")),
        )


@dataclass
class ExploreResponse:
    markets: list[Market] = field(default_factory=list)
    pagination: Optional[Pagination] = None

    @classmethod
    def from_dict(cls, data: dict) -> ExploreResponse:
        return cls(
            markets=_parse_list(Market, data.get("markets")),
            pagination=_parse(Pagination, data.get("pagination")),
        )


@dataclass
class AgentMarketsListResponse:
    markets: list[Market] = field(default_factory=list)
    pending_requests: list[dict] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> AgentMarketsListResponse:
        return cls(
            markets=_parse_list(Market, data.get("markets")),
            pending_requests=data.get("pending_requests", []),
        )


# ---------------------------------------------------------------------------
# Market validation & creation
# ---------------------------------------------------------------------------


@dataclass
class ValidationIssue:
    field: str = ""
    code: str = ""
    message: str = ""
    severity: str = ""


@dataclass
class SimilarMarket:
    market_addr: str = ""
    title: str = ""
    status: str = ""
    fingerprint: str = ""
    created_at: str = ""


@dataclass
class DuplicateCheck:
    has_duplicates: bool = False
    similar_markets: list[SimilarMarket] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict | None) -> Optional[DuplicateCheck]:
        if not data:
            return None
        return cls(
            has_duplicates=data.get("has_duplicates", False),
            similar_markets=_parse_list(SimilarMarket, data.get("similar_markets")),
        )


@dataclass
class ValidatePreview:
    slug: str = ""
    fingerprint: str = ""
    seed_usdc: str = ""
    initial_price_yes_bps: int = 0
    deadline: str = ""
    estimated_max_loss: str = ""
    liquidity_tier: str = ""


@dataclass
class ValidateResult:
    success: bool = False
    valid: bool = False
    issues: list[ValidationIssue] = field(default_factory=list)
    duplicate_check: Optional[DuplicateCheck] = None
    preview: Optional[ValidatePreview] = None

    @classmethod
    def from_dict(cls, data: dict) -> ValidateResult:
        return cls(
            success=data.get("success", False),
            valid=data.get("valid", False),
            issues=_parse_list(ValidationIssue, data.get("issues")),
            duplicate_check=DuplicateCheck.from_dict(data.get("duplicate_check")),
            preview=_parse(ValidatePreview, data.get("preview")),
        )


@dataclass
class CreateMarketResult:
    success: bool = False
    status: str = ""
    request_id: str = ""
    market_addr: str = ""
    tx_hash: str = ""
    typed_data: Optional[dict] = None


@dataclass
class BatchItemResult:
    index: int = 0
    status: str = ""
    request_id: str = ""
    typed_data: Optional[dict] = None
    error: Optional[dict] = None


@dataclass
class BatchSummary:
    total: int = 0
    pending: int = 0
    errors: int = 0


@dataclass
class BatchResult:
    success: bool = False
    results: list[BatchItemResult] = field(default_factory=list)
    summary: Optional[BatchSummary] = None

    @classmethod
    def from_dict(cls, data: dict) -> BatchResult:
        return cls(
            success=data.get("success", False),
            results=_parse_list(BatchItemResult, data.get("results")),
            summary=_parse(BatchSummary, data.get("summary")),
        )


# ---------------------------------------------------------------------------
# Market state — GET /api/agent/markets/{address}/state
# ---------------------------------------------------------------------------


@dataclass
class LmsrInfo:
    q_yes: str = ""
    q_no: str = ""
    b: str = ""
    price_yes_bps: int = 0
    price_no_bps: int = 0


@dataclass
class MarketAnalytics:
    volume24h: str = "0"
    trades24h: int = 0
    liquidity_usdc: str = "0"


@dataclass
class SlippageCurveEntry:
    amount_usdc: str = ""
    price_impact_bps: int = 0
    effective_price_bps: int = 0


@dataclass
class MarketState:
    success: bool = False
    market: str = ""
    condition_id: str = ""
    lmsr: Optional[LmsrInfo] = None
    analytics: Optional[MarketAnalytics] = None
    slippage_curve: list[SlippageCurveEntry] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> MarketState:
        return cls(
            success=data.get("success", False),
            market=data.get("market", ""),
            condition_id=data.get("condition_id", ""),
            lmsr=_parse(LmsrInfo, data.get("lmsr")),
            analytics=_parse(MarketAnalytics, data.get("analytics")),
            slippage_curve=_parse_list(SlippageCurveEntry, data.get("slippage_curve")),
        )


# ---------------------------------------------------------------------------
# Market history — GET /api/agent/markets/{address}/history
# ---------------------------------------------------------------------------


@dataclass
class HistoryPoint:
    timestamp: str = ""
    timestamp_start: str = ""
    price_yes_bps: int = 0
    price_yes_bps_open: int = 0
    price_yes_bps_high: int = 0
    price_yes_bps_low: int = 0
    price_yes_bps_close: int = 0
    volume_usdc: float = 0.0
    trades_count: int = 0
    block_number: int = 0


@dataclass
class MarketHistoryResponse:
    history: list[HistoryPoint] = field(default_factory=list)
    interval: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> MarketHistoryResponse:
        return cls(
            history=_parse_list(HistoryPoint, data.get("history")),
            interval=data.get("interval", ""),
        )


# ---------------------------------------------------------------------------
# Quote — GET /api/quote
# ---------------------------------------------------------------------------


@dataclass
class LmsrQuote:
    available: bool = False
    shares_out: str = "0"
    amount_out: str = "0"
    fee: str = "0"
    price_yes_bps: int = 0
    price_no_bps: int = 0
    new_price_yes_bps: int = 0
    price_impact_bps: int = 0
    avg_price_bps: int = 0


@dataclass
class ClobQuote:
    available: bool = False
    can_fill_full: bool = False
    shares_out: str = "0"
    amount_out: str = "0"
    avg_price_bps: int = 0
    levels_used: int = 0
    best_bid_bps: int = 0
    best_ask_bps: int = 0
    spread_bps: int = 0
    depth_near_mid: int = 0


@dataclass
class SplitLeg:
    shares: str = "0"
    cost: str = "0"
    avg_price_bps: int = 0


@dataclass
class SplitLegs:
    clob: Optional[SplitLeg] = None
    lmsr: Optional[SplitLeg] = None

    @classmethod
    def from_dict(cls, data: dict | None) -> Optional[SplitLegs]:
        if not data:
            return None
        return cls(
            clob=_parse(SplitLeg, data.get("clob")),
            lmsr=_parse(SplitLeg, data.get("lmsr")),
        )


@dataclass
class PriceImpactGuard:
    current_price_yes_bps: int = 0
    new_price_yes_bps: int = 0
    impact_bps: int = 0
    max_allowed_impact_bps: int = 0
    level: str = "ok"


@dataclass
class Quote:
    quote_id: str = ""
    condition_id: str = ""
    side: str = ""
    action: str = ""
    amount: str = "0"
    venue: str = ""
    reason: str = ""
    may_partial_fill: bool = False
    valid_until: str = ""
    split_legs: Optional[SplitLegs] = None
    lmsr: Optional[LmsrQuote] = None
    clob: Optional[ClobQuote] = None
    price_impact_guard: Optional[PriceImpactGuard] = None

    @classmethod
    def from_dict(cls, data: dict) -> Quote:
        obj = _parse(cls, data)
        if obj:
            obj.split_legs = SplitLegs.from_dict(data.get("split_legs"))
            if isinstance(data.get("lmsr"), dict):
                obj.lmsr = _parse(LmsrQuote, data["lmsr"])
            if isinstance(data.get("clob"), dict):
                obj.clob = _parse(ClobQuote, data["clob"])
            if isinstance(data.get("price_impact_guard"), dict):
                obj.price_impact_guard = _parse(PriceImpactGuard, data["price_impact_guard"])
        return obj


# ---------------------------------------------------------------------------
# Trading — LMSR (BackstopRouter)
# ---------------------------------------------------------------------------


@dataclass
class BalanceCheck:
    available: str = "0"
    required: str = "0"
    sufficient: bool = True


@dataclass
class TradeQuote:
    shares_out: str = "0"
    fee: str = "0"
    price_impact_bps: int = 0
    avg_price_bps: int = 0


@dataclass
class TradeIntentResponse:
    intent_id: str = ""
    status: str = ""
    venue: str = ""
    quote: Optional[TradeQuote] = None
    typed_data: Optional[dict] = None
    balance_check: Optional[BalanceCheck] = None
    price_impact_guard: Optional[PriceImpactGuard] = None

    @classmethod
    def from_dict(cls, data: dict) -> TradeIntentResponse:
        obj = _parse(cls, data)
        if obj:
            if isinstance(data.get("quote"), dict):
                obj.quote = _parse(TradeQuote, data["quote"])
            if isinstance(data.get("balance_check"), dict):
                obj.balance_check = _parse(BalanceCheck, data["balance_check"])
            if isinstance(data.get("price_impact_guard"), dict):
                obj.price_impact_guard = _parse(PriceImpactGuard, data["price_impact_guard"])
        return obj


@dataclass
class TradeResult:
    intent_id: str = ""
    status: str = ""
    venue: str = ""
    tx_hash: str = ""
    shares_out: str = "0"
    usdc_out: str = "0"
    fee_usdc: str = "0"
    next_nonce: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    retryable: bool = False


@dataclass
class TradeNonceResponse:
    venue: str = ""
    nonce: int = 0
    signer_address: str = ""
    contract: str = ""


@dataclass
class ApprovalDetail:
    operator: str = ""
    approved: bool = False


@dataclass
class ApprovalStatus:
    owner: str = ""
    share_token: str = ""
    approvals: Optional[dict] = None
    all_approved: bool = False
    instructions: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> ApprovalStatus:
        return _parse(cls, data)


# ---------------------------------------------------------------------------
# CLOB orders
# ---------------------------------------------------------------------------


@dataclass
class Fill:
    match_type: str = ""
    fill_amount: str = "0"
    counterparty_hash: str = ""


@dataclass
class OrderIntentResponse:
    intent_id: str = ""
    status: str = ""
    venue: str = ""
    order: Optional[dict] = None
    typed_data: Optional[dict] = None
    match_estimate: Optional[dict] = None
    balance_check: Optional[BalanceCheck] = None

    @classmethod
    def from_dict(cls, data: dict) -> OrderIntentResponse:
        obj = _parse(cls, data)
        if obj and isinstance(data.get("balance_check"), dict):
            obj.balance_check = _parse(BalanceCheck, data["balance_check"])
        return obj


@dataclass
class OrderResult:
    intent_id: str = ""
    status: str = ""
    venue: str = ""
    order_hash: str = ""
    fills: list[Fill] = field(default_factory=list)
    filled_shares: str = "0"
    total_shares: str = "0"
    unfilled: str = "0"
    error: Optional[str] = None
    error_code: Optional[str] = None
    idempotent: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> OrderResult:
        obj = _parse(cls, data)
        if obj:
            obj.fills = _parse_list(Fill, data.get("fills"))
        return obj


@dataclass
class Order:
    """ClobOrder from the API."""
    order_hash: str = ""
    condition_id: str = ""
    token_id: str = ""
    side: str = ""
    is_buy: bool = False
    price_bps: int = 0
    total_shares: int = 0
    filled_shares: int = 0
    filled_percent: int = 0
    status: str = ""
    db_status: str = ""
    time_in_force: str = "GTC"
    expiration: str = ""
    auto_sign: bool = False
    created_at: str = ""
    updated_at: str = ""


@dataclass
class OrderListResponse:
    orders: list[Order] = field(default_factory=list)
    pagination: Optional[Pagination] = None

    @classmethod
    def from_dict(cls, data: dict) -> OrderListResponse:
        return cls(
            orders=_parse_list(Order, data.get("orders")),
            pagination=_parse(Pagination, data.get("pagination")),
        )


@dataclass
class OrderCancelResponse:
    success: bool = False
    order_hash: Optional[str] = None
    tx_hash: Optional[str] = None
    cancel_all: Optional[bool] = None
    cancelled_count: Optional[int] = None


# ---------------------------------------------------------------------------
# Portfolio — GET /api/agent/portfolio
# ---------------------------------------------------------------------------


@dataclass
class Position:
    market_addr: str = ""
    title: str = ""
    status: str = ""
    yes_shares: float = 0.0
    no_shares: float = 0.0
    net_side: str = ""
    net_shares: float = 0.0
    avg_entry_price_usdc: float = 0.0
    current_price_bps: int = 0
    current_value_usdc: float = 0.0
    pnl_usdc: float = 0.0
    last_trade_at: str = ""


@dataclass
class PortfolioTotals:
    markets_active: int = 0
    markets_resolved: int = 0


@dataclass
class PortfolioResponse:
    positions: list[Position] = field(default_factory=list)
    totals: Optional[PortfolioTotals] = None

    @classmethod
    def from_dict(cls, data: dict) -> PortfolioResponse:
        return cls(
            positions=_parse_list(Position, data.get("positions")),
            totals=_parse(PortfolioTotals, data.get("totals")),
        )


# ---------------------------------------------------------------------------
# Analytics — GET /api/agent/performance
# ---------------------------------------------------------------------------


@dataclass
class VolumeBySource:
    backstop: str = "0"
    clob: str = "0"
    total: str = "0"


@dataclass
class CategoryPerf:
    category: str = ""
    volume: str = "0"
    fees: str = "0"
    markets: int = 0


@dataclass
class MarketPerf:
    market_addr: str = ""
    title: str = ""
    volume: str = "0"
    fees: str = "0"


@dataclass
class PerformanceResponse:
    success: bool = False
    fees_earned: str = "0"
    volume_by_source: Optional[VolumeBySource] = None
    by_category: list[CategoryPerf] = field(default_factory=list)
    by_market: list[MarketPerf] = field(default_factory=list)
    period: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> PerformanceResponse:
        return cls(
            success=data.get("success", False),
            fees_earned=data.get("fees_earned", "0"),
            volume_by_source=_parse(VolumeBySource, data.get("volume_by_source")),
            by_category=_parse_list(CategoryPerf, data.get("by_category")),
            by_market=_parse_list(MarketPerf, data.get("by_market")),
            period=data.get("period", ""),
        )


# ---------------------------------------------------------------------------
# Audit log — GET /api/agent/audit-log
# ---------------------------------------------------------------------------


@dataclass
class AuditLogEntry:
    id: str = ""
    event_type: str = ""
    created_at: str = ""
    event_data: Optional[dict] = None


@dataclass
class AuditLogResponse:
    entries: list[AuditLogEntry] = field(default_factory=list)
    pagination: Optional[Pagination] = None

    @classmethod
    def from_dict(cls, data: dict) -> AuditLogResponse:
        return cls(
            entries=_parse_list(AuditLogEntry, data.get("entries")),
            pagination=_parse(Pagination, data.get("pagination")),
        )


# ---------------------------------------------------------------------------
# Feed — GET /api/agent/feed
# ---------------------------------------------------------------------------


@dataclass
class FeedEvent:
    type: str = ""
    timestamp: str = ""
    data: Optional[dict] = None


@dataclass
class FeedResponse:
    events: list[FeedEvent] = field(default_factory=list)
    cursor: str = ""
    has_more: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> FeedResponse:
        return cls(
            events=_parse_list(FeedEvent, data.get("events")),
            cursor=data.get("cursor", ""),
            has_more=data.get("has_more", False),
        )


@dataclass
class SSEEvent:
    type: str = "message"
    data: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Vault / deposits — GET/POST /api/agent/vault/deposit
# ---------------------------------------------------------------------------


@dataclass
class RecentDeposit:
    id: str = ""
    amount: str = "0"
    status: str = ""
    tx_hash: str = ""
    created_at: str = ""


@dataclass
class VaultBalanceResponse:
    vault_balance: str = "0"
    wallet_balance: str = "0"
    allowance: str = "0"
    deposit_router_address: str = ""
    approval_required: bool = False
    recent_deposits: list[RecentDeposit] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> VaultBalanceResponse:
        obj = _parse(cls, data)
        if obj:
            obj.recent_deposits = _parse_list(RecentDeposit, data.get("recent_deposits"))
        return obj


@dataclass
class DepositResult:
    intent_id: str = ""
    status: str = ""
    tx_hash: str = ""
    amount: str = "0"
    next_nonce: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    retryable: bool = False


# ---------------------------------------------------------------------------
# Webhooks — GET/POST/DELETE /api/agent/webhooks
# ---------------------------------------------------------------------------


@dataclass
class Webhook:
    id: str = ""
    url: str = ""
    event_types: list[str] = field(default_factory=list)
    is_active: bool = True
    created_at: str = ""
    last_delivery_at: Optional[str] = None
    last_delivery_status: Optional[str] = None
    consecutive_failures: int = 0


@dataclass
class WebhookCreateResult:
    id: str = ""
    url: str = ""
    event_types: list[str] = field(default_factory=list)
    is_active: bool = True
    created_at: str = ""
    secret: str = ""


# ---------------------------------------------------------------------------
# Leaderboard — GET /api/agents/leaderboard
# ---------------------------------------------------------------------------


@dataclass
class LeaderboardEntry:
    rank: int = 0
    agent_name: str = ""
    owner_addr: str = ""
    volume: str = "0"
    fees: str = "0"
    markets_created: int = 0


@dataclass
class LeaderboardResponse:
    success: bool = False
    leaderboard: list[LeaderboardEntry] = field(default_factory=list)
    metric: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> LeaderboardResponse:
        return cls(
            success=data.get("success", False),
            leaderboard=_parse_list(LeaderboardEntry, data.get("leaderboard")),
            metric=data.get("metric", ""),
        )
