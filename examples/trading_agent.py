"""Trading agent: monitor prices, place trades and limit orders.

Usage:
    pip install ..  # from examples/ dir
    pip install python-dotenv
    python trading_agent.py
"""

import os

from dotenv import load_dotenv

from flipcoin import FlipCoin, FlipCoinError, usdc_to_raw

load_dotenv()

client = FlipCoin(api_key=os.environ["FLIPCOIN_API_KEY"])
me = client.ping()
print(f"Trading agent '{me.agent}' ready")

# -- Configuration -----------------------------------------------------------
BUY_THRESHOLD_BPS = 4000  # Buy YES when price < 40%
TRADE_AMOUNT_USDC = 1.0   # $1 per trade
MAX_TRADES = 3


def find_underpriced_markets(min_volume: float = 10.0) -> list:
    """Find open markets with YES price below threshold."""
    explore = client.get_markets(status="open", min_volume=min_volume, limit=50)
    return [
        m for m in explore.markets
        if m.current_price_yes_bps < BUY_THRESHOLD_BPS
    ]


def execute_trade(market) -> None:
    """Get a quote and execute a buy-YES trade."""
    amount = usdc_to_raw(TRADE_AMOUNT_USDC)

    # Step 1: Get quote
    quote = client.get_quote(market.condition_id, "yes", "buy", amount)
    print(f"  Quote venue: {quote.venue} ({quote.reason})")
    if quote.lmsr:
        print(f"  LMSR: {quote.lmsr.shares_out} shares, fee={quote.lmsr.fee}")

    # Step 2: Execute trade
    result = client.trade(
        condition_id=market.condition_id,
        side="yes",
        action="buy",
        usdc_amount=amount,
        max_slippage_bps=500,
    )
    print(f"  Trade executed! tx={result.tx_hash}")
    print(f"  Got {result.shares_out} shares")


def place_limit_order(market) -> None:
    """Place a limit buy order on the CLOB."""
    target_price = max(100, market.current_price_yes_bps - 500)
    result = client.create_order(
        condition_id=market.condition_id,
        side="yes",
        action="buy",
        price_bps=target_price,
        amount=usdc_to_raw(2.0),
        time_in_force="GTC",
    )
    print(f"  Order placed: {result.order_hash} @ {target_price} bps")
    if result.fills:
        print(f"  Immediately filled: {len(result.fills)} fills")


# -- Main loop ---------------------------------------------------------------
print(f"\nScanning for markets with YES price < {BUY_THRESHOLD_BPS / 100:.0f}%...")
candidates = find_underpriced_markets()
print(f"Found {len(candidates)} candidates\n")

trades_made = 0
for market in candidates[:MAX_TRADES]:
    price = market.current_price_yes_bps / 100
    print(f"Market: {market.title}")
    print(f"  Price: {price:.1f}%  Volume: {market.volume_usdc}")

    try:
        execute_trade(market)
        trades_made += 1
    except FlipCoinError as e:
        print(f"  Trade failed: {e.error_code} — {e}")

    try:
        place_limit_order(market)
    except FlipCoinError as e:
        print(f"  Order failed: {e.error_code} — {e}")

    print()

# -- Summary -----------------------------------------------------------------
print(f"Session complete: {trades_made}/{len(candidates[:MAX_TRADES])} trades executed")
orders = client.get_orders(status="open")
print(f"Open orders: {len(orders.orders)}")

perf = client.get_performance(period="7d")
print(f"7-day fees earned: {perf.fees_earned}")
