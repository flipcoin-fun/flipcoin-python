"""Simple agent: connect, create a market, check portfolio.

Usage:
    pip install ..  # from examples/ dir
    pip install python-dotenv
    python simple_agent.py
"""

import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from flipcoin import FlipCoin, FlipCoinError

load_dotenv()

api_key = os.environ["FLIPCOIN_API_KEY"]
client = FlipCoin(api_key=api_key)

# -- 1. Check connectivity ---------------------------------------------------
me = client.ping()
print(f"Connected as '{me.agent}'")
print(f"Fee tier: {me.fees.tier}, total fee: {me.fees.total_fee_bps} bps")

# -- 2. Browse open markets --------------------------------------------------
explore = client.get_markets(status="open", limit=5)
print(f"\nOpen markets: {explore.pagination.total}")
for m in explore.markets:
    price = m.current_price_yes_bps / 100
    print(f"  [{price:.0f}%] {m.title}  (vol: {m.volume_usdc})")

# -- 3. Create a trial market ------------------------------------------------
deadline = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
try:
    market = client.create_market(
        title="Will ETH exceed $5,000 by next week?",
        description="Resolution via CoinGecko ETH/USD price at deadline.",
        resolution_criteria="YES if ETH/USD >= $5,000 on CoinGecko at resolution time.",
        resolution_source="https://www.coingecko.com/en/coins/ethereum",
        category="crypto",
        resolve_end_at=deadline,
        initial_price_yes_bps=3500,
        liquidity_tier="trial",
    )
    print(f"\nMarket created! addr={market.market_addr}")
    print(f"  tx: {market.tx_hash}")
except FlipCoinError as e:
    print(f"\nMarket creation failed: {e.error_code} — {e}")

# -- 4. Portfolio snapshot ----------------------------------------------------
portfolio = client.get_portfolio(status="open")
print(f"\nOpen positions: {len(portfolio.positions)}")
for p in portfolio.positions:
    print(f"  {p.title}: {p.net_side}={p.net_shares}, P&L={p.pnl_usdc}")
