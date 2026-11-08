"""The travel supervisor: talks to the traveler, books flight and hotel in the background.

It starts the flight and hotel agents at the same time and replies straight
away. When the traveler changes the trip, it sends the change to the running
task with update_async_task. Both specs use `update_strategy="interrupt"`:
a search for the old dates or cities is wasted work, so it stops and restarts
with the new details on the same thread (same task ID).

The hotel follows the flight: its city and dates come from the trip. Telling
the model "update both tasks" was not enough: in testing it sometimes updated
only the flight, and the hotel went on booking the old city.
`HotelFollowsFlight` enforces it in code instead.
"""

from typing import Any

from deepagents import AsyncSubAgent, create_deep_agent
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage

from travel_agents.agents import get_llm

SYSTEM_PROMPT = """\
You are a travel assistant. You book a round-trip flight and a hotel for the traveler.

## New trip
You need: origin city, destination city, departure date and return date (YYYY-MM-DD).
If any is missing, ask for it. Do not start anything until you have all four.
Then, in the same turn, call start_async_task twice:
- flight_agent: "Book a round-trip flight from <origin> to <destination>, depart <date>, return <date>."
- hotel_agent: "Book a hotel in <destination>, check in <departure date>, check out <return date>."
Reply in one or two sentences that both are in progress. Then stop. Do not check status right away.

## Changes to the trip
- Cities or dates change: call update_async_task on the flight task. Word the message as a change,
  with the full new trip details: "Change of plans: the trip is now <origin> to <destination>,
  depart <date>, return <date>." The hotel task gets the same message automatically.
- The traveler drops the hotel or the flight: call cancel_async_task on that task.
Then confirm the change in one sentence.

## Status and results
- Statuses in the conversation history are stale. Before answering a status question, call list_async_tasks.
- A `waiting` task is waiting for the traveler to approve a booking on that task's own thread.
  Tell them; you cannot approve it for them.
- When a task reports back, relay it in one or two sentences with its confirmation code.
- When both are booked, give a short trip summary: flight code, route, dates, price; hotel code, name, dates, total.
"""

ASYNC_SUBAGENTS: list[AsyncSubAgent] = [
    {
        "name": "flight_agent",
        "description": "Searches and books a round-trip flight. Booking needs the traveler's approval.",
        "graph_id": "flight_agent",
        "update_strategy": "interrupt",
    },
    {
        "name": "hotel_agent",
        "description": "Searches and books a hotel. Booking needs the traveler's approval.",
        "graph_id": "hotel_agent",
        "update_strategy": "interrupt",
    },
]



class HotelFollowsFlight(AgentMiddleware):
    """When the model updates the flight task but not the hotel task, add the same update for the hotel.

    Runs after each model call, before the tools run. The hotel agent gets the full
    trip and keeps its booking when its city and dates are unchanged (see agents.py).
    """

    def after_model(self, state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
        last = (state.get("messages") or [None])[-1]
        if not isinstance(last, AIMessage) or not last.tool_calls:
            return None
        tasks = {t["agent_name"]: t for t in (state.get("async_tasks") or {}).values()}
        flight, hotel = tasks.get("flight_agent"), tasks.get("hotel_agent")
        if not flight or not hotel or hotel["status"] == "cancelled":
            return None
        updates = [c for c in last.tool_calls if c["name"] == "update_async_task"]
        to_flight = [c for c in updates if c["args"].get("task_id") == flight["task_id"]]
        if not to_flight or any(c["args"].get("task_id") == hotel["task_id"] for c in updates):
            return None
        mirrored = {
            "name": "update_async_task",
            "args": {"task_id": hotel["task_id"], "message": to_flight[0]["args"]["message"]},
            "id": f"{to_flight[0]['id']}-hotel",
            "type": "tool_call",
        }
        # Same message ID, so this replaces the model's message rather than adding one.
        return {"messages": [last.model_copy(update={"tool_calls": [*last.tool_calls, mirrored]})]}

    async def aafter_model(self, state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
        return self.after_model(state, runtime)


graph = create_deep_agent(
    model=get_llm(),
    system_prompt=SYSTEM_PROMPT,
    subagents=ASYNC_SUBAGENTS,
    middleware=[HotelFollowsFlight()],
    name="travel_supervisor",
)
