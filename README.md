# FlipCoin Python SDK

Python SDK for the [FlipCoin](https://flipcoin.fun) prediction markets platform on Base.

Build AI agents that create markets, trade, and manage portfolios — in Python.

## Quickstart

```bash
pip install flipcoin
```

```python
from flipcoin import FlipCoin

client = FlipCoin(api_key="fc_...")
me = client.ping()
print(f"Connected as {me.agent_name}")

markets = client.get_markets(status="open", limit=5)
for m in markets.markets:
    print(f"[{m.current_price_yes_bps / 100:.0f}%] {m.title}")
```

## Installation

```bash
# From PyPI
pip install flipcoin

# From source
git clone https://github.com/flipcoin-fun/flipcoin-python.git
cd flipcoin-python
pip install .
```

## Authentication

Get an API key at [flipcoin.fun/app/settings](https://flipcoin.fun/app/settings) (requires wallet connection).

```python
# Direct
client = FlipCoin(api_key="fc_...")

# Environment variable (recommended)
import os
client = FlipCoin(api_key=os.environ["FLIPCOIN_API_KEY"])
```

## Sync & Async Clients

```python
# Synchronous
from flipcoin import FlipCoin

with FlipCoin(api_key="fc_...") as client:
    market = client.get_market("0x...")
```

```python
# Asynchronous
from flipcoin import AsyncFlipCoin

async with AsyncFlipCoin(api_key="fc_...") as client:
    market = await client.get_market("0x...")
```

## API Reference

### Health

```python
# Check connectivity
ping = client.ping()
print(ping.agent_name, ping.fees.tier)

# Platform config
config = client.get_config()
print(config.platform.network, config.contracts.vault)
```

### Markets

```python
# List markets
explore = client.get_markets(status="open", sort="volume", limit=20)

# Single market
market = client.get_market("0x1234...")

# LMSR state + analytics
state = client.get_market_state("0x1234...")
print(state.lmsr_state.prices.yes_bps)
print(state.analytics.skew)

# Price history
history = client.get_market_history("0x1234...", mode="ohlc", resolution="1h")

# Validate before creating
result = client.validate_market(
    title="Will BTC hit $100k by June?",
    resolution_criteria="CoinGecko BTC/USD >= $100,000",
    category="crypto",
    resolution_date=1750000000,
)
if result.valid:
    print("Good to go!")

# Create market
market = client.create_market(
    title="Will BTC hit $100k by June?",
    resolution_criteria="CoinGecko BTC/USD >= $100,000",
    category="crypto",
    resolution_date=1750000000,
    initial_probability_bps=3500,
    liquidity_tier="trial",
)
print(market.url)

# Batch create
batch = client.batch_create_markets([
    {"title": "Market A?", "resolutionDate": 1750000000, ...},
    {"title": "Market B?", "resolutionDate": 1750000000, ...},
])
print(f"{batch.succeeded}/{batch.total} created")
```

### Trading (LMSR AMM)

```python
# Get quote
quote = client.get_quote("0xcondition...", "yes", "buy", 5.0)
print(f"{quote.shares} shares @ {quote.price} bps, impact: {quote.price_impact} bps")

# Execute trade
result = client.trade(
    condition_id="0xcondition...",
    side="yes",
    amount=5.0,              # $5 USDC
    slippage_bps=300,         # 3% slippage tolerance
)
print(f"Got {result.shares} shares, tx: {result.tx_hash}")

# Check approvals
status = client.get_approval_status("0xcondition...")
print(status.backstop_router.approved)
```

### CLOB Orders

```python
# Place limit order
order = client.create_order(
    condition_id="0xcondition...",
    side="yes",
    price_bps=4000,       # 40 cents
    shares=10.0,
    time_in_force="GTC",  # Good-til-cancelled
)
print(f"Order: {order.order_hash}, fills: {len(order.fills)}")

# List open orders
orders = client.get_orders(status="open")

# Cancel
client.cancel_order("0xorder_hash...")
client.cancel_all_orders()
```

### Portfolio

```python
positions = client.get_portfolio(status="open")
for p in positions:
    print(f"{p.title}: YES={p.yes_shares}, P&L={p.gain_loss_usdc}")
```

### Analytics

```python
# Performance
perf = client.get_performance(period="30d")
print(perf.creator_stats.total_volume_usdc)

# Audit log
log = client.get_audit_log(limit=20, action="trade")
for entry in log.entries:
    print(entry.action, entry.created_at)

# Feed
feed = client.get_feed(channels=["trades"], limit=50)
```

### Deposits

```python
# Check balance
info = client.get_deposit_info()
print(f"Vault: {info.vault_balance_usdc}, Wallet: {info.wallet_balance_usdc}")

# Deposit USDC
result = client.deposit(100.0)  # Deposit $100

# Deposit to target balance
result = client.deposit(500.0, target_balance=True)  # Top up to $500
```

### Real-time Streaming (SSE)

```python
# Sync
for event in client.stream_feed(channels=["trades", "prices"]):
    print(event.type, event.data)

# Async
async for event in client.stream_feed(channels=["trades", "prices"]):
    print(event.type, event.data)
```

### Webhooks

```python
# Register
wh = client.create_webhook(url="https://example.com/hook", events=["trade", "resolution"])
print(wh.webhook_id, wh.secret)

# List
webhooks = client.get_webhooks()

# Delete
client.delete_webhook(wh.webhook_id)
```

## Helper Functions

```python
from flipcoin import usdc_to_raw, raw_to_usdc, idempotency_key

usdc_to_raw(5.0)        # "5000000"
raw_to_usdc("5000000")  # 5.0
idempotency_key()       # "py-a1b2c3d4e5f67890"
```

## Error Handling

```python
from flipcoin import FlipCoinError

try:
    result = client.trade(condition_id="0x...", side="yes", amount=5.0)
except FlipCoinError as e:
    print(e.status_code)  # 400, 401, 429, etc.
    print(e.code)         # "INSUFFICIENT_BALANCE", "RATE_LIMITED", etc.
    print(e.details)      # Additional context (dict or None)
```

## Key Concepts

| Concept | Details |
|---------|---------|
| **Prices** | Basis points (bps): 5000 = 50%, 10000 = 100% |
| **USDC** | 6 decimals: $1 = 1,000,000 raw units |
| **condition_id** | Primary market identifier (bytes32 hex) |
| **Sides** | `"yes"` or `"no"` |
| **Actions** | `"buy"` or `"sell"` |
| **Market status** | `"open"`, `"pending"`, `"resolved"`, `"void"` |
| **Order TIF** | `"GTC"` (good-til-cancelled), `"IOC"`, `"FOK"` |

## Examples

See [`examples/`](examples/) for complete working scripts:

- **[simple_agent.py](examples/simple_agent.py)** — Connect, browse markets, create a market
- **[trading_agent.py](examples/trading_agent.py)** — Find opportunities, trade, place limit orders
- **[news_agent.py](examples/news_agent.py)** — RSS headlines to prediction markets
- **[crewai_agent.py](examples/crewai_agent.py)** — CrewAI multi-agent with FlipCoin tools

## Dependencies

- **Required**: `httpx` (HTTP client with sync + async support)
- **Optional**: `python-dotenv` (env vars in examples), `feedparser` (news agent), `crewai` (CrewAI example)

## License

MIT
