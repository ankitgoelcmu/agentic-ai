"""The flight and hotel agents. Each runs as an async subagent on its own thread.

Built with `create_deep_agent` so that, when started by the supervisor, each
one reports back on its own when it finishes. Booking pauses for a human's
approval; while it waits, the supervisor sees the task as `waiting`.
"""

import os

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model

from travel_agents.tools import book_flight, book_hotel, cancel_flight, cancel_hotel, search_flights, search_hotels


def get_llm():
    return init_chat_model(os.getenv("TRAVEL_MODEL", "ollama:qwen3-coder-next:latest"), temperature=0)


APPROVAL = {"allowed_decisions": ["approve", "reject"]}

FLIGHT_PROMPT = """\
You book round-trip flights.

1. Call search_flights once with the trip's origin, destination and dates.
2. Pick the cheapest nonstop option and call book_flight with its details. A human approves it.
3. Reply with the confirmation code, route, dates and price. If the booking was rejected, say so.

If you get changed trip details later in this conversation, search again with the new details
and book again. Never reuse old search results. Booking again replaces the trip's old flight
and cancels it automatically; tell the traveler both the new and the cancelled confirmation codes.
Do not write files or todo lists."""

HOTEL_PROMPT = """\
You book hotels.

1. Call search_hotels once with the city and dates.
2. Pick the cheapest option and call book_hotel with its details. A human approves it.
3. Reply with the confirmation code, hotel, city, dates and total. If the booking was rejected, say so.

If you get changed trip details later in this conversation, search again with the new details
and book again. Never reuse old search results. Booking again replaces the trip's old hotel
and cancels it automatically; tell the traveler both the new and the cancelled confirmation codes.
You get every trip change, including flight-only ones. If the new destination city and dates are
the same as your current booking, don't search or book again: reply that the hotel booking stands.
Do not write files or todo lists."""

flight_graph = create_deep_agent(
    model=get_llm(),
    tools=[search_flights, book_flight, cancel_flight],
    system_prompt=FLIGHT_PROMPT,
    interrupt_on={"book_flight": APPROVAL},
    name="flight_agent",
)

hotel_graph = create_deep_agent(
    model=get_llm(),
    tools=[search_hotels, book_hotel, cancel_hotel],
    system_prompt=HOTEL_PROMPT,
    interrupt_on={"book_hotel": APPROVAL},
    name="hotel_agent",
)
