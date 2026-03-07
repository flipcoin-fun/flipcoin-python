"""Simple agent: connect, create a market, check portfolio.

Usage:
    pip install ..  # from examples/ dir
    pip install python-dotenv
    python simple_agent.py
"""

import os
import time

from dotenv import load_dotenv

from flipcoin import FlipCoin, FlipCoinError, raw_to_usdc

load_dotenv()

api_key = os.environ["FLIPCOIN_API_KEY"]
client = FlipCoin(api_key=api_key)

# ── 1. Check connectivity ──────────────────────────────────────────────────
me = client.ping()
print(f"Connected as '{me.agent_name}' (ID: {me.agent_id})")
print(f"Fee tier: {me.fees.tier}, taker fee: {me.fees.taker_fee_bps} bps")

# ── 2. Browse open markets ─────────────────────────────────────────────────
explore = client.get_markets(status="open", limit=5)
print(f"\nOpen markets: {explore.pagination.total}")
for m in explore.markets:
    price = m.current_price_yes_bps / 100
    vol = raw_to_usdc(m.volume_usdc)
    print(f"  [{price:.0f}%] {m.title}  (vol: ${vol:,.2f})")

# ── 3. Create a trial market ───────────────────────────────────────────────
try:
    market = client.create_market(
        title="Will ETH exceed $5,000 by next week?",
        description="Resolution via CoinGecko ETH/USD price at deadline.",
        resolution_criteria="YES if ETH/USD >= $5,000 on CoinGecko at resolution time.",
        category="crypto",
        resolution_date=int(time.time()) + 7 * 24 * 3600,
        initial_probability_bps=3500,
        liquidity_tier="trial",
    )
    print(f"\nMarket created! {market.url}")
    print(f"  condition_id: {market.condition_id}")
    print(f"  tx: {market.tx_hash}")
except FlipCoinError as e:
    print(f"\nMarket creation failed: {e.code} — {e}")

# ── 4. Portfolio snapshot ───────────────────────────────────────────────────
positions = client.get_portfolio(status="open")
print(f"\nOpen positions: {len(positions)}")
for p in positions:
    print(f"  {p.title}: YES={p.yes_shares}, NO={p.no_shares}")
