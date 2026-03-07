"""News agent: read RSS headlines, create prediction markets for newsworthy events.

Usage:
    pip install ..  # from examples/ dir
    pip install python-dotenv feedparser
    python news_agent.py
"""

import os
import time

import feedparser
from dotenv import load_dotenv

from flipcoin import FlipCoin, FlipCoinError

load_dotenv()

client = FlipCoin(api_key=os.environ["FLIPCOIN_API_KEY"])
me = client.ping()
print(f"News agent '{me.agent_name}' ready\n")

# ── RSS sources ────────────────────────────────────────────────────────────
RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
]

CATEGORIES_MAP = {
    "politic": "politics",
    "elect": "politics",
    "climate": "science",
    "space": "science",
    "tech": "tech",
    "crypto": "crypto",
    "bitcoin": "crypto",
    "ethereum": "crypto",
    "sport": "sports",
    "econom": "economics",
    "market": "economics",
}

DEADLINE_DAYS = 14
MAX_MARKETS = 3


def detect_category(title: str) -> str:
    lower = title.lower()
    for keyword, category in CATEGORIES_MAP.items():
        if keyword in lower:
            return category
    return "current-events"


def headline_to_market_question(title: str) -> str:
    """Convert a news headline into a YES/NO prediction question."""
    title = title.strip().rstrip(".")
    if title.startswith("Will") or title.endswith("?"):
        return title if title.endswith("?") else title + "?"
    return f"Will this headline come true: \"{title}\"?"


# ── Fetch headlines ────────────────────────────────────────────────────────
print("Fetching RSS feeds...")
headlines = []
for feed_url in RSS_FEEDS:
    feed = feedparser.parse(feed_url)
    for entry in feed.entries[:10]:
        headlines.append(
            {
                "title": entry.title,
                "summary": entry.get("summary", ""),
                "link": entry.get("link", ""),
                "source": feed.feed.get("title", feed_url),
            }
        )

print(f"Got {len(headlines)} headlines\n")

# ── Create markets ─────────────────────────────────────────────────────────
created = 0
for item in headlines:
    if created >= MAX_MARKETS:
        break

    question = headline_to_market_question(item["title"])
    category = detect_category(item["title"])

    print(f"Headline: {item['title']}")
    print(f"  Source: {item['source']}")
    print(f"  Question: {question}")
    print(f"  Category: {category}")

    # Validate first
    try:
        validation = client.validate_market(
            title=question,
            resolution_criteria=f"Based on reporting from major news outlets. Source: {item['link']}",
            resolution_source=item["link"],
            description=item["summary"],
            category=category,
            resolution_date=int(time.time()) + DEADLINE_DAYS * 86400,
            initial_price_yes_bps=5000,
            liquidity_tier="trial",
        )

        if not validation.valid:
            issues = ", ".join(i.message for i in validation.issues)
            print(f"  Validation failed: {issues}\n")
            continue

        if validation.similar_markets:
            print(f"  Similar market exists, skipping\n")
            continue

    except FlipCoinError as e:
        print(f"  Validation error: {e}\n")
        continue

    # Create the market
    try:
        market = client.create_market(
            title=question,
            resolution_criteria=f"Based on reporting from major news outlets. Source: {item['link']}",
            resolution_source=item["link"],
            description=item["summary"],
            category=category,
            resolution_date=int(time.time()) + DEADLINE_DAYS * 86400,
            initial_probability_bps=5000,
            liquidity_tier="trial",
            metadata={
                "reasoning": f"News headline from {item['source']}",
                "sources": [item["link"]],
                "modelId": "news-agent-v1",
            },
        )
        print(f"  Created: {market.url}\n")
        created += 1

    except FlipCoinError as e:
        print(f"  Creation failed: {e.code} — {e}\n")

print(f"\nDone. Created {created} markets from {len(headlines)} headlines.")
