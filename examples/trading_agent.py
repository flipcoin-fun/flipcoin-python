"""Trading agent: monitor prices, place trades and limit orders.

Usage:
    pip install ..  # from examples/ dir
    pip install python-dotenv
    python trading_agent.py
"""

import os
import time

from dotenv import load_dotenv

from flipcoin import FlipCoin, FlipCoinError, raw_to_usdc

load_dotenv()

client = FlipCoin(api_key=os.environ["FLIPCOIN_API_KEY"])
me = client.ping()
print(f"Trading agent '{me.agent_name}' ready")

# ── Configuration ──────────────────────────────────────────────────────────
BUY_THRESHOLD_BPS = 4000  # Buy YES when price < 40%
TRADE_AMOUNT_USDC = 1.0   # $1 per trade
MAX_TRADES = 3


def find_underpriced_markets(min_volume: float = 10.0) -> list:
    """Find open markets with YES price below threshold."""
    explore = client.get_markets(status="open", limit=50)
    candidates = []
    for m in explore.markets:
        vol = raw_to_usdc(m.volume_usdc)
        if m.current_price_yes_bps < BUY_THRESHOLD_BPS and vol >= min_volume:
            candidates.append(m)
    return candidates


def execute_trade(market) -> None:
    """Get a quote and execute a buy-YES trade."""
    # Step 1: Get quote
    quote = client.get_quote(
        market.condition_id, "yes", "buy", TRADE_AMOUNT_USDC
    )
    print(f"  Quote: {quote.shares} shares @ {quote.price} bps, fee={quote.fee}")
    print(f"  Price impact: {quote.price_impact} bps")

    # Step 2: Execute trade
    result = client.trade(
        condition_id=market.condition_id,
        side="yes",
        amount=TRADE_AMOUNT_USDC,
        slippage_bps=500,  # 5% slippage tolerance
    )
    print(f"  Trade executed! tx={result.tx_hash}")
    print(f"  Got {result.shares} shares @ {result.price} bps")


def place_limit_order(market) -> None:
    """Place a limit buy order on the CLOB."""
    target_price = max(100, market.current_price_yes_bps - 500)  # 5% below current
    result = client.create_order(
        condition_id=market.condition_id,
        side="yes",
        price_bps=target_price,
        shares=2.0,
        time_in_force="GTC",
    )
    print(f"  Order placed: {result.order_hash} @ {target_price} bps")
    if result.fills:
        print(f"  Immediately filled: {len(result.fills)} fills")


# ── Main loop ──────────────────────────────────────────────────────────────
print(f"\nScanning for markets with YES price < {BUY_THRESHOLD_BPS / 100:.0f}%...")
candidates = find_underpriced_markets()
print(f"Found {len(candidates)} candidates\n")

trades_made = 0
for market in candidates[:MAX_TRADES]:
    price = market.current_price_yes_bps / 100
    print(f"Market: {market.title}")
    print(f"  Price: {price:.1f}%  Volume: ${raw_to_usdc(market.volume_usdc):,.2f}")

    try:
        execute_trade(market)
        trades_made += 1
    except FlipCoinError as e:
        print(f"  Trade failed: {e.code} — {e}")

    try:
        place_limit_order(market)
    except FlipCoinError as e:
        print(f"  Order failed: {e.code} — {e}")

    print()

# ── Summary ────────────────────────────────────────────────────────────────
print(f"Session complete: {trades_made}/{len(candidates[:MAX_TRADES])} trades executed")
orders = client.get_orders(status="open")
print(f"Open orders: {len(orders)}")

perf = client.get_performance(period="7d")
if perf.creator_stats:
    print(f"7-day volume: ${raw_to_usdc(perf.creator_stats.total_volume_usdc):,.2f}")
