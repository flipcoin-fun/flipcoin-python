"""Data models for FlipCoin SDK responses."""

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
    """Error returned by the FlipCoin API."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 0,
        code: str = "UNKNOWN",
        details: Any = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.details = details

    def __repr__(self) -> str:
        return f"FlipCoinError({self.status_code}, code={self.code!r}, message={str(self)!r})"


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@dataclass
class PingFees:
    tier: str = ""
    maker_fee_bps: int = 0
    taker_fee_bps: int = 0


@dataclass
class PingResponse:
    agent_id: str = ""
    agent_name: str = ""
    owner_addr: str = ""
    is_active: bool = False
    fees: Optional[PingFees] = None

    @classmethod
    def from_dict(cls, data: dict) -> PingResponse:
        obj = _parse(cls, data)
        if obj and isinstance(data.get("fees"), dict):
            obj.fees = _parse(PingFees, data["fees"])
        return obj


@dataclass
class PlatformInfo:
    name: str = ""
    version: str = ""
    network: str = ""
    chain_id: int = 0


@dataclass
class ContractsInfo:
    factory: str = ""
    vault: str = ""
    usdc: str = ""
    backstop_router: str = ""
    exchange: str = ""
    share_token: str = ""
    delegation_registry: str = ""


@dataclass
class FeesInfo:
    maker_fee_bps: int = 0
    taker_fee_bps: int = 0
    creator_fee_bps: int = 0


@dataclass
class LimitsInfo:
    min_trade_usdc: float = 0.0
    max_trade_usdc: float = 0.0
    min_order_shares: float = 0.0


@dataclass
class ConfigResponse:
    platform: Optional[PlatformInfo] = None
    contracts: Optional[ContractsInfo] = None
    fees: Optional[FeesInfo] = None
    limits: Optional[LimitsInfo] = None

    @classmethod
    def from_dict(cls, data: dict) -> ConfigResponse:
        return cls(
            platform=_parse(PlatformInfo, data.get("platform")),
            contracts=_parse(ContractsInfo, data.get("contracts")),
            fees=_parse(FeesInfo, data.get("fees")),
            limits=_parse(LimitsInfo, data.get("limits")),
        )


# ---------------------------------------------------------------------------
# Markets
# ---------------------------------------------------------------------------


@dataclass
class Market:
    market_addr: str = ""
    condition_id: str = ""
    title: str = ""
    description: str = ""
    category: str = ""
    resolution_criteria: str = ""
    resolution_source: str = ""
    creator_addr: str = ""
    status: str = ""
    current_price_yes_bps: int = 0
    current_price_no_bps: int = 0
    volume_usdc: str = "0"
    liquidity_usdc: str = "0"
    total_yes_shares: str = "0"
    total_no_shares: str = "0"
    created_at: str = ""
    resolution_date: int = 0
    resolve_end_at: int = 0
    is_pending: bool = False
    proposed_outcome: Optional[str] = None
    finalize_after: Optional[int] = None
    can_finalize: bool = False
    dispute_time_remaining: Optional[int] = None
    image_url: Optional[str] = None
    url: Optional[str] = None


@dataclass
class Pagination:
    total: int = 0
    limit: int = 20
    offset: int = 0
    has_more: bool = False


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


# ---------------------------------------------------------------------------
# Market validation & creation
# ---------------------------------------------------------------------------


@dataclass
class ValidationIssue:
    code: str = ""
    severity: str = ""
    message: str = ""


@dataclass
class ValidateParams:
    seed_usdc: float = 0.0
    initial_price_yes_bps: int = 0
    estimated_max_loss: float = 0.0


@dataclass
class SimilarMarket:
    title: str = ""
    condition_id: str = ""
    similarity: float = 0.0


@dataclass
class ValidateResult:
    valid: bool = False
    issues: list[ValidationIssue] = field(default_factory=list)
    params: Optional[ValidateParams] = None
    warnings: list[str] = field(default_factory=list)
    similar_markets: list[SimilarMarket] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> ValidateResult:
        return cls(
            valid=data.get("valid", False),
            issues=_parse_list(ValidationIssue, data.get("issues")),
            params=_parse(ValidateParams, data.get("params")),
            warnings=data.get("warnings", []),
            similar_markets=_parse_list(SimilarMarket, data.get("similar_markets")),
        )


@dataclass
class CreateMarketResult:
    success: bool = False
    market_addr: str = ""
    tx_hash: str = ""
    condition_id: str = ""
    url: str = ""


@dataclass
class BatchMarketResult:
    index: int = 0
    success: bool = False
    market_addr: str = ""
    condition_id: str = ""
    tx_hash: str = ""
    error: Optional[str] = None


@dataclass
class BatchResult:
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    results: list[BatchMarketResult] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> BatchResult:
        obj = _parse(cls, data)
        if obj:
            obj.results = _parse_list(BatchMarketResult, data.get("results"))
        return obj


# ---------------------------------------------------------------------------
# Market state & history
# ---------------------------------------------------------------------------


@dataclass
class LmsrPrices:
    yes_bps: int = 0
    no_bps: int = 0


@dataclass
class LmsrState:
    b: float = 0.0
    q_yes: float = 0.0
    q_no: float = 0.0
    fee_bps: int = 0
    prices: Optional[LmsrPrices] = None
    yes_shares_total: str = "0"
    no_shares_total: str = "0"

    @classmethod
    def from_dict(cls, data: dict) -> LmsrState:
        obj = _parse(cls, data)
        if obj and isinstance(data.get("prices"), dict):
            obj.prices = _parse(LmsrPrices, data["prices"])
        return obj


@dataclass
class AnalyticsState:
    skew: float = 0.0
    state_imbalance: float = 0.0
    max_loss_usdc: float = 0.0


@dataclass
class SlippageCurveEntry:
    amount_usdc: float = 0.0
    baseline_price_yes_bps: int = 0
    post_trade_price_yes_bps: int = 0
    price_impact_bps: int = 0
    avg_fill_price_ex_fee_bps: int = 0
    avg_fill_price_incl_fee_bps: int = 0
    shares_out: float = 0.0


@dataclass
class SlippageCurve:
    buy_yes: list[SlippageCurveEntry] = field(default_factory=list)
    buy_no: list[SlippageCurveEntry] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> SlippageCurve:
        return cls(
            buy_yes=_parse_list(SlippageCurveEntry, data.get("buy_yes")),
            buy_no=_parse_list(SlippageCurveEntry, data.get("buy_no")),
        )


@dataclass
class MarketState:
    schema_version: str = ""
    units: Optional[dict] = None
    market: Optional[dict] = None
    condition_id: str = ""
    lmsr_state: Optional[LmsrState] = None
    analytics: Optional[AnalyticsState] = None
    slippage_curve: Optional[SlippageCurve] = None

    @classmethod
    def from_dict(cls, data: dict) -> MarketState:
        return cls(
            schema_version=data.get("schema_version", ""),
            units=data.get("units"),
            market=data.get("market"),
            condition_id=data.get("condition_id", ""),
            lmsr_state=LmsrState.from_dict(data["lmsr_state"])
            if isinstance(data.get("lmsr_state"), dict)
            else None,
            analytics=_parse(AnalyticsState, data.get("analytics")),
            slippage_curve=SlippageCurve.from_dict(data["slippage_curve"])
            if isinstance(data.get("slippage_curve"), dict)
            else None,
        )


@dataclass
class HistoryPointRaw:
    timestamp: int = 0
    price_yes_bps: int = 0
    price_no_bps: int = 0
    volume_usdc: str = "0"


@dataclass
class HistoryPointOHLC:
    timestamp: int = 0
    open: int = 0
    high: int = 0
    low: int = 0
    close: int = 0
    volume_usdc: str = "0"


@dataclass
class MarketHistoryResponse:
    condition_id: str = ""
    mode: str = "raw"
    resolution: str = ""
    data: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, raw: dict) -> MarketHistoryResponse:
        mode = raw.get("mode", "raw")
        point_cls = HistoryPointOHLC if mode == "ohlc" else HistoryPointRaw
        return cls(
            condition_id=raw.get("condition_id", ""),
            mode=mode,
            resolution=raw.get("resolution", ""),
            data=_parse_list(point_cls, raw.get("data")),
        )


# ---------------------------------------------------------------------------
# Trading
# ---------------------------------------------------------------------------


@dataclass
class Quote:
    condition_id: str = ""
    side: str = ""
    action: str = ""
    shares: str = "0"
    fee: str = "0"
    price: int = 0
    price_impact: int = 0


@dataclass
class TradeResult:
    success: bool = False
    condition_id: str = ""
    tx_hash: str = ""
    shares: str = "0"
    fee: str = "0"
    price: int = 0


@dataclass
class ApprovalDetail:
    approved: bool = False
    operator: str = ""


@dataclass
class ApprovalStatus:
    condition_id: str = ""
    backstop_router: Optional[ApprovalDetail] = None
    exchange: Optional[ApprovalDetail] = None

    @classmethod
    def from_dict(cls, data: dict) -> ApprovalStatus:
        return cls(
            condition_id=data.get("condition_id", ""),
            backstop_router=_parse(ApprovalDetail, data.get("backstop_router")),
            exchange=_parse(ApprovalDetail, data.get("exchange")),
        )


# ---------------------------------------------------------------------------
# CLOB orders
# ---------------------------------------------------------------------------


@dataclass
class Fill:
    counterparty_hash: str = ""
    fill_amount: str = "0"
    fill_price: int = 0
    match_type: str = ""


@dataclass
class OrderResult:
    success: bool = False
    order_hash: str = ""
    condition_id: str = ""
    status: str = ""
    fills: list[Fill] = field(default_factory=list)
    unfilled: str = "0"

    @classmethod
    def from_dict(cls, data: dict) -> OrderResult:
        obj = _parse(cls, data)
        if obj:
            obj.fills = _parse_list(Fill, data.get("fills"))
        return obj


@dataclass
class Order:
    order_hash: str = ""
    condition_id: str = ""
    side: str = ""
    price_bps: int = 0
    shares_placed: str = "0"
    shares_filled: str = "0"
    shares_open: str = "0"
    time_in_force: str = "GTC"
    status: str = ""
    created_at: str = ""


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------


@dataclass
class Position:
    market_addr: str = ""
    title: str = ""
    status: str = ""
    yes_shares: str = "0"
    no_shares: str = "0"
    total_cost_usdc: str = "0"
    current_value_usdc: str = "0"
    gain_loss_usdc: str = "0"
    gain_loss_percent: float = 0.0


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


@dataclass
class VolumeBySource:
    agent: str = "0"
    manual: str = "0"
    total: str = "0"


@dataclass
class CreatorStats:
    markets_created: int = 0
    markets_resolved: int = 0
    total_volume_usdc: str = "0"
    avg_volume_per_market: str = "0"
    creator_fees_earned_usdc: str = "0"
    volume_by_source: Optional[VolumeBySource] = None

    @classmethod
    def from_dict(cls, data: dict) -> CreatorStats:
        obj = _parse(cls, data)
        if obj and isinstance(data.get("volume_by_source"), dict):
            obj.volume_by_source = _parse(VolumeBySource, data["volume_by_source"])
        return obj


@dataclass
class CategoryStats:
    category: str = ""
    markets: int = 0
    volume_usdc: str = "0"
    avg_volume: str = "0"


@dataclass
class MarketPerformance:
    condition_id: str = ""
    title: str = ""
    volume_usdc: str = "0"
    status: str = ""


@dataclass
class ActivityInfo:
    total_trades: int = 0
    last_trade_at: str = ""


@dataclass
class PerformanceResponse:
    period: str = ""
    volume_definition: str = ""
    creator_stats: Optional[CreatorStats] = None
    by_category: list[CategoryStats] = field(default_factory=list)
    by_market: list[MarketPerformance] = field(default_factory=list)
    activity: Optional[ActivityInfo] = None

    @classmethod
    def from_dict(cls, data: dict) -> PerformanceResponse:
        return cls(
            period=data.get("period", ""),
            volume_definition=data.get("volume_definition", ""),
            creator_stats=CreatorStats.from_dict(data["creator_stats"])
            if isinstance(data.get("creator_stats"), dict)
            else None,
            by_category=_parse_list(CategoryStats, data.get("by_category")),
            by_market=_parse_list(MarketPerformance, data.get("by_market")),
            activity=_parse(ActivityInfo, data.get("activity")),
        )


@dataclass
class AuditLogEntry:
    id: str = ""
    action: str = ""
    details: Optional[dict] = None
    created_at: str = ""
    ip: str = ""


@dataclass
class AuditLogResponse:
    entries: list[AuditLogEntry] = field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> AuditLogResponse:
        return cls(
            entries=_parse_list(AuditLogEntry, data.get("entries")),
            total=data.get("total", 0),
            limit=data.get("limit", 50),
            offset=data.get("offset", 0),
        )


# ---------------------------------------------------------------------------
# Feed & streaming
# ---------------------------------------------------------------------------


@dataclass
class FeedEvent:
    type: str = ""
    data: Optional[dict] = None
    timestamp: str = ""


@dataclass
class FeedResponse:
    events: list[FeedEvent] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> FeedResponse:
        return cls(events=_parse_list(FeedEvent, data.get("events")))


@dataclass
class SSEEvent:
    type: str = "message"
    data: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Vault / deposits
# ---------------------------------------------------------------------------


@dataclass
class RecentDeposit:
    amount_usdc: str = "0"
    tx_hash: str = ""
    created_at: str = ""


@dataclass
class DepositInfo:
    vault_balance_usdc: str = "0"
    wallet_balance_usdc: str = "0"
    allowance_usdc: str = "0"
    recent_deposits: list[RecentDeposit] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> DepositInfo:
        obj = _parse(cls, data)
        if obj:
            obj.recent_deposits = _parse_list(
                RecentDeposit, data.get("recent_deposits")
            )
        return obj


@dataclass
class DepositResult:
    success: bool = False
    tx_hash: str = ""
    amount_usdc: str = "0"


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------


@dataclass
class Webhook:
    id: str = ""
    url: str = ""
    events: list[str] = field(default_factory=list)
    secret: str = ""
    is_active: bool = True
    created_at: str = ""


@dataclass
class WebhookCreateResult:
    success: bool = False
    webhook_id: str = ""
    secret: str = ""
