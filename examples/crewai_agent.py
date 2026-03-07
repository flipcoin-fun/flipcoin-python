"""CrewAI integration: wrap FlipCoin as CrewAI tools.

Usage:
    pip install ..  # from examples/ dir
    pip install python-dotenv crewai crewai-tools
    python crewai_agent.py

Requires: crewai >= 0.28.0, crewai-tools
"""

import os
import time

from crewai import Agent, Crew, Task
from crewai_tools import BaseTool
from dotenv import load_dotenv

from flipcoin import FlipCoin, FlipCoinError, raw_to_usdc

load_dotenv()

# ── FlipCoin Tools ─────────────────────────────────────────────────────────


class ListMarketsTool(BaseTool):
    name: str = "list_prediction_markets"
    description: str = (
        "List open prediction markets on FlipCoin. "
        "Returns market titles, prices, and volumes. "
        "Use search parameter to filter by keyword."
    )

    def _run(self, search: str = "", limit: int = 10) -> str:
        client = FlipCoin(api_key=os.environ["FLIPCOIN_API_KEY"])
        explore = client.get_markets(status="open", search=search, limit=limit)

        if not explore.markets:
            return "No open markets found."

        lines = []
        for m in explore.markets:
            price = m.current_price_yes_bps / 100
            vol = raw_to_usdc(m.volume_usdc)
            lines.append(f"- [{price:.0f}%] {m.title} (vol: ${vol:,.2f}, id: {m.condition_id})")

        return f"Found {explore.pagination.total} markets:\n" + "\n".join(lines)


class CreateMarketTool(BaseTool):
    name: str = "create_prediction_market"
    description: str = (
        "Create a new binary YES/NO prediction market on FlipCoin. "
        "Provide a clear title as a question, resolution criteria, "
        "and number of days until resolution."
    )

    def _run(
        self,
        title: str,
        resolution_criteria: str,
        days: int = 7,
        category: str = "current-events",
        initial_probability: int = 50,
    ) -> str:
        client = FlipCoin(api_key=os.environ["FLIPCOIN_API_KEY"])
        try:
            market = client.create_market(
                title=title,
                resolution_criteria=resolution_criteria,
                category=category,
                resolution_date=int(time.time()) + days * 86400,
                initial_probability_bps=initial_probability * 100,
                liquidity_tier="trial",
            )
            return (
                f"Market created successfully!\n"
                f"URL: {market.url}\n"
                f"Condition ID: {market.condition_id}\n"
                f"TX: {market.tx_hash}"
            )
        except FlipCoinError as e:
            return f"Failed to create market: {e.code} - {e}"


class TradeTool(BaseTool):
    name: str = "trade_prediction_market"
    description: str = (
        "Buy YES or NO shares in a prediction market. "
        "Provide the condition_id, side ('yes' or 'no'), and amount in USD."
    )

    def _run(self, condition_id: str, side: str, amount: float = 1.0) -> str:
        client = FlipCoin(api_key=os.environ["FLIPCOIN_API_KEY"])
        try:
            quote = client.get_quote(condition_id, side, "buy", amount)
            result = client.trade(
                condition_id=condition_id,
                side=side,
                amount=amount,
            )
            return (
                f"Trade executed!\n"
                f"Bought {result.shares} {side.upper()} shares\n"
                f"Price: {result.price} bps ({result.price / 100:.1f}%)\n"
                f"Fee: {result.fee}\n"
                f"TX: {result.tx_hash}"
            )
        except FlipCoinError as e:
            return f"Trade failed: {e.code} - {e}"


class PortfolioTool(BaseTool):
    name: str = "get_portfolio"
    description: str = "Get current prediction market positions and P&L."

    def _run(self) -> str:
        client = FlipCoin(api_key=os.environ["FLIPCOIN_API_KEY"])
        positions = client.get_portfolio(status="open")
        if not positions:
            return "No open positions."
        lines = []
        for p in positions:
            lines.append(
                f"- {p.title}: YES={p.yes_shares}, NO={p.no_shares}, "
                f"P&L: {p.gain_loss_usdc} ({p.gain_loss_percent:+.1f}%)"
            )
        return f"Open positions ({len(positions)}):\n" + "\n".join(lines)


# ── CrewAI Setup ───────────────────────────────────────────────────────────

researcher = Agent(
    role="Market Researcher",
    goal="Find interesting prediction market opportunities by analyzing current markets",
    backstory="You are an expert analyst who identifies underpriced prediction markets.",
    tools=[ListMarketsTool(), PortfolioTool()],
    verbose=True,
)

trader = Agent(
    role="Market Trader",
    goal="Create new prediction markets and trade on interesting opportunities",
    backstory="You are a prediction market maker who creates and trades markets strategically.",
    tools=[CreateMarketTool(), TradeTool(), ListMarketsTool()],
    verbose=True,
)

research_task = Task(
    description=(
        "Search the FlipCoin prediction markets for opportunities. "
        "Look for markets with YES prices below 40% that seem undervalued. "
        "Also check our current portfolio. "
        "Summarize the top 3 opportunities."
    ),
    expected_output="A list of the top 3 market opportunities with analysis.",
    agent=researcher,
)

trading_task = Task(
    description=(
        "Based on the research, decide whether to trade on any of the identified "
        "opportunities. If you find a good opportunity with price below 40%, "
        "buy $1 worth of YES shares. Report what you did."
    ),
    expected_output="A summary of trades executed or reasons for not trading.",
    agent=trader,
    context=[research_task],
)

crew = Crew(
    agents=[researcher, trader],
    tasks=[research_task, trading_task],
    verbose=True,
)

# ── Run ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    result = crew.kickoff()
    print("\n" + "=" * 60)
    print("CREW RESULT:")
    print(result)
