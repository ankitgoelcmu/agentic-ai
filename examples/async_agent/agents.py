"""The smallest async subagents example: one supervisor, one flight agent."""

import asyncio

from deepagents import AsyncSubAgent, create_deep_agent

MODEL = "ollama:qwen3-coder-next:latest"


async def search_flights(city: str) -> str:
    """Find the cheapest flight to a city."""
    # Fakes a slow real API (30s) so you can change the city mid-search.
    # Remove it in real code; the actual API call is the slow part.
    await asyncio.sleep(30)
    return f"Cheapest flight to {city}: $244, nonstop."


flight_agent = create_deep_agent(
    model=MODEL,
    tools=[search_flights],
    system_prompt="Search flights for the requested city and report the cheapest.",
)

supervisor = create_deep_agent(
    model=MODEL,
    system_prompt=(
        "You are a travel assistant.\n"
        "- Flight search: call start_async_task with flight_agent, reply in one sentence, then stop.\n"
        "- The user changes the city: call update_async_task on the running task, reply in one sentence, then stop.\n"
        "- Never call check_async_task unless the user asks for status. Results come back on their own."
    ),
    subagents=[
        AsyncSubAgent(
            name="flight_agent",
            description="Finds the cheapest flight to a city.",
            graph_id="flight_agent",
        )
    ],
)
