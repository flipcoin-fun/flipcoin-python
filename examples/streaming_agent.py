"""Streaming agent: real-time SSE feed with auto-reconnect and backoff.

Demonstrates:
- Subscribing to trades + prices channels
- Automatic reconnection with Last-Event-ID resume
- Exponential backoff with jitter on errors
- Handling server-initiated reconnect events
- Rate limit (429) handling

Usage:
    pip install ..  # from examples/ dir
    pip install python-dotenv
    python streaming_agent.py
"""

import asyncio
import os
import random

from dotenv import load_dotenv

from flipcoin import AsyncFlipCoin, FlipCoinError

load_dotenv()

# -- Configuration -----------------------------------------------------------
MAX_RETRIES = 20
CHANNELS = "prices"  # Add "trades:0xCONDITION_ID" for specific markets


async def stream_with_reconnect(client: AsyncFlipCoin, channels: str):
    """Stream events with automatic reconnection and exponential backoff."""
    last_event_id: str | None = None
    retries = 0

    while retries <= MAX_RETRIES:
        try:
            print(f"[connect] channels={channels}, last_event_id={last_event_id}")
            async for event in client.stream_feed(
                channels=channels, last_event_id=last_event_id,
            ):
                retries = 0  # Reset backoff on successful event

                # Server requests reconnect (connections close after 5 min)
                if event.type == "reconnect":
                    print("[reconnect] Server requested reconnect")
                    break

                # Track event ID for resume on reconnect
                if "id" in event.data:
                    last_event_id = str(event.data["id"])

                # Process events
                if event.type == "connected":
                    print(f"[connected] Subscribed: {event.data}")
                elif event.type == "trade":
                    d = event.data
                    print(
                        f"[trade] {d.get('side', '?')} "
                        f"${d.get('amount_usdc', '?')} "
                        f"@ {d.get('price_yes_bps', '?')} bps"
                    )
                elif event.type == "prices":
                    markets = event.data.get("markets", [])
                    for m in markets[:3]:
                        print(
                            f"[price] {m.get('title', '?')[:40]}: "
                            f"{m.get('price_yes_bps', '?')} bps"
                        )
                else:
                    print(f"[{event.type}] {event.data}")

        except FlipCoinError as e:
            if e.status_code == 429:
                wait = (e.details or {}).get("retryAfterMs", 5000) / 1000
                print(f"[429] Rate limited, waiting {wait:.1f}s...")
                await asyncio.sleep(wait)
            else:
                wait = min(2**retries, 60) + random.uniform(0, 2)
                print(f"[error] {e.error_code}: {e}, retrying in {wait:.1f}s...")
                await asyncio.sleep(wait)

        except (ConnectionError, TimeoutError) as e:
            wait = min(2**retries, 60) + random.uniform(0, 2)
            print(f"[disconnect] {type(e).__name__}, reconnecting in {wait:.1f}s...")
            await asyncio.sleep(wait)

        retries += 1

    print(f"[exit] Max retries ({MAX_RETRIES}) exceeded")


async def main():
    api_key = os.environ["FLIPCOIN_API_KEY"]

    async with AsyncFlipCoin(api_key=api_key) as client:
        me = await client.ping()
        print(f"Streaming agent '{me.agent}' ready\n")
        await stream_with_reconnect(client, CHANNELS)


if __name__ == "__main__":
    asyncio.run(main())
