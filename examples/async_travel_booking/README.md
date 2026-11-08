# Async Travel Booking

A travel assistant that books a flight and a hotel at the same time, keeps talking while they're booked, and lets you change the trip (cities, dates) mid-booking. Built on [Deep Agents async subagents](https://www.langchain.com/blog/agents-are-going-async).

## How it works

```
traveler ⇄ travel_supervisor ──start / update / cancel──▶ flight_agent   (own thread)
                ▲                 └──start / update / cancel──▶ hotel_agent    (own thread)
                └──────────── results come back on their own ◀──────────┘
```

Three agents run on one local Agent Server ([langgraph.json](langgraph.json)):

- **`travel_supervisor`** ([supervisor.py](travel_agents/supervisor.py)) talks to the traveler. Once it has the origin, destination and dates, it starts the flight and hotel agents in the same turn and replies straight away.
- **`flight_agent`** and **`hotel_agent`** ([agents.py](travel_agents/agents.py)) each search, pick the cheapest option and book it. Each runs on its own thread.

**Booking needs approval.** `book_flight` and `book_hotel` charge money, so the agent pauses before running them. The supervisor sees that task as `waiting`. The traveler approves on that agent's own thread, so the supervisor is never blocked.

**Changing the trip.** The supervisor sends the change to the running task with `update_async_task`. The task ID stays the same. Both agents use `update_strategy="interrupt"`, because a search for the old dates or cities is wasted work: the old run stops and a new one starts with the new details. The hotel follows the flight, so a new destination or new dates update both tasks. A new origin updates only the flight.

- **Before booking:** the search restarts with the new details.
- **After booking:** the agent searches again and asks for approval for the new booking. A trip holds one flight and one hotel, so booking again replaces the old booking and cancels it in the same step. This is enforced in the tool, not the prompt: in testing, a model told "cancel first, then rebook" once rebooked without cancelling, leaving two flights.

**Results come back on their own.** When an agent finishes, it wakes the supervisor (if idle) or is picked up before its next model call (if busy). The supervisor then relays the confirmation code.

## Tools

[tools.py](travel_agents/tools.py) is a mock with fixed results: the same trip always gives the same options, prices and confirmation codes, so tests repeat. Searches wait `FLIGHT_SEARCH_SECONDS` and `HOTEL_SEARCH_SECONDS` (30 and 20), like a real fare search. That's also what makes "change the trip mid-search" possible: a change can only interrupt a search that's still running. Set them to `0` in `.env` if you just want to click around.

## Run it

Needs Python 3.12+, [uv](https://docs.astral.sh/uv/) and [Ollama](https://ollama.com) with `qwen3-coder-next`. Runs locally, no API cost.

```bash
cd examples/async_travel_booking
cp .env.example .env
uv sync

# terminal 1
uv run langgraph dev --no-browser --n-jobs-per-worker 10 --port 2025

# terminal 2
uv run python test_booking.py                 # all scenarios
uv run python test_booking.py change_cities   # one
```

To use it by hand, open LangGraph Studio from the URL `langgraph dev` prints and pick `travel_supervisor`. When a booking is waiting, open that agent's thread and approve it there.

## Tests

[test_booking.py](test_booking.py) checks the server's records (runs, thread status, tool calls on each agent's thread), not what the model says.

| Scenario | What it checks |
|---|---|
| `book_trip` | Both agents start together and pause for approval. After approval, each books once and the supervisor relays both confirmation codes. |
| `change_cities` | "Fly to Seattle instead" mid-search updates both tasks. Each old run is interrupted, and the new searches are for Seattle. |
| `change_dates_after_booking` | New dates after booking rebook both for the new dates after a second approval, and the old flight and hotel are cancelled (no double booking). |
| `cancel_hotel` | "Skip the hotel" cancels only the hotel task. The flight keeps going. |
