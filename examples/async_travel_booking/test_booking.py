"""Test the travel supervisor against a running `langgraph dev` server.

    uv run langgraph dev --no-browser --n-jobs-per-worker 10 --port 2025
    uv run python test_booking.py                 # all scenarios
    uv run python test_booking.py change_cities   # one scenario

Each check looks at the server's own records (runs, thread status, tool calls
on the flight and hotel threads), not at what the model says.
"""

import asyncio
import os
import sys
import time

from langgraph_sdk import get_client

client = get_client(url=os.getenv("LANGGRAPH_URL", "http://127.0.0.1:2025"))
results: list[tuple[str, bool, str]] = []

TRIP = "Book me a trip from San Francisco to Portland, departing 2026-12-10 and returning 2026-12-14."


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""), flush=True)


def text(m: dict) -> str:
    c = m.get("content")
    return c if isinstance(c, str) else " ".join(b.get("text", "") for b in c or [] if isinstance(b, dict))


async def say(thread: str, msg: str) -> None:
    print(f"  > {msg}", flush=True)
    start = time.monotonic()
    await client.runs.wait(thread, "travel_supervisor", input={"messages": [{"role": "user", "content": msg}]},
                           multitask_strategy="enqueue")
    messages = await get_messages(thread)
    reply = next((text(m) for m in reversed(messages) if m["type"] == "ai" and text(m).strip()), "")
    print(f"  < ({time.monotonic() - start:.0f}s) {reply[:150]!r}", flush=True)


async def get_messages(thread: str) -> list[dict]:
    return (await client.threads.get_state(thread))["values"].get("messages", [])


async def task(thread: str, agent: str) -> dict | None:
    tasks = (await client.threads.get_state(thread))["values"].get("async_tasks") or {}
    return next((t for t in tasks.values() if t["agent_name"] == agent), None)


async def calls(thread: str, tool: str) -> list[dict]:
    """Every call to `tool` on a thread, oldest first, as its args."""
    return [c["args"] for m in await get_messages(thread) for c in m.get("tool_calls") or [] if c["name"] == tool]


async def tool_results(thread: str, prefix: str) -> list[str]:
    return [text(m) for m in await get_messages(thread) if m["type"] == "tool" and text(m).startswith(prefix)]


async def wait(what: str, predicate, timeout: float = 600) -> bool:
    print(f"  ... waiting for {what}", flush=True)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if await predicate():
            return True
        await asyncio.sleep(3)
    return False


async def thread_status(thread: str) -> str:
    return (await client.threads.get(thread))["status"]


async def approve(t: dict, graph: str) -> None:
    """The traveler approves the booking on the subagent's own thread (task ID == thread ID)."""
    print(f"  > traveler approves the {graph} booking", flush=True)
    await client.runs.wait(t["thread_id"], graph, command={"resume": {"decisions": [{"type": "approve"}]}})


async def book_and_approve(thread: str) -> tuple[dict, dict]:
    """Start the trip, wait for both bookings to need approval, approve both."""
    await say(thread, TRIP)
    flight, hotel = await task(thread, "flight_agent"), await task(thread, "hotel_agent")
    check("supervisor started the flight and hotel tasks", bool(flight and hotel))
    for t, graph in [(flight, "flight_agent"), (hotel, "hotel_agent")]:

        async def paused(t=t):
            return await thread_status(t["thread_id"]) == "interrupted"

        check(f"{graph} paused for booking approval", await wait(f"{graph} to ask for approval", paused))
        await approve(t, graph)
    return flight, hotel


async def settled(thread: str) -> bool:
    """Both tasks finished and the supervisor has nothing left to do."""
    flight, hotel = await task(thread, "flight_agent"), await task(thread, "hotel_agent")
    done = all(t and t["status"] in {"success", "cancelled", "error"} for t in (flight, hotel))
    last = (await get_messages(thread))[-1]
    return done and await thread_status(thread) == "idle" and last["type"] == "ai"


async def cleanup(thread: str) -> None:
    for agent in ("flight_agent", "hotel_agent"):
        if t := await task(thread, agent):
            for run in await client.runs.list(t["thread_id"]):
                if run["status"] in {"pending", "running"}:
                    await client.runs.cancel(t["thread_id"], run["run_id"])


# ------------------------------------------------------------------ scenarios


async def book_trip():
    """Flight and hotel book in parallel; the supervisor relays both confirmations."""
    thread = (await client.threads.create())["thread_id"]
    flight, hotel = await book_and_approve(thread)
    await wait("both tasks to report back", lambda: settled(thread))
    flight_codes = [r.split()[2].rstrip(":") for r in await tool_results(flight["thread_id"], "BOOKED flight")]
    hotel_codes = [r.split()[2].rstrip(":") for r in await tool_results(hotel["thread_id"], "BOOKED hotel")]
    check("flight booked once", len(flight_codes) == 1, f"{flight_codes}")
    check("hotel booked once", len(hotel_codes) == 1, f"{hotel_codes}")
    summary = " ".join(text(m) for m in await get_messages(thread) if m["type"] == "ai")
    check("supervisor told the traveler both confirmation codes",
          all(code in summary for code in flight_codes + hotel_codes), f"{flight_codes + hotel_codes}")


async def change_cities():
    """Changing the destination mid-search interrupts both searches and restarts them for the new city."""
    thread = (await client.threads.create())["thread_id"]
    await say(thread, TRIP)
    flight, hotel = await task(thread, "flight_agent"), await task(thread, "hotel_agent")
    await say(thread, "Change of plans: fly to Seattle instead of Portland. Same dates.")

    updated = {c["task_id"] for c in await calls(thread, "update_async_task")}
    check("supervisor updated the flight task", flight["task_id"] in updated)
    check("hotel task updated too (hotel follows the flight)", hotel["task_id"] in updated)

    for t, tool, key in [(flight, "search_flights", "destination"), (hotel, "search_hotels", "city")]:
        runs = sorted(await client.runs.list(t["thread_id"]), key=lambda r: r["created_at"])
        check(f"{t['agent_name']}: old run interrupted, new run started", len(runs) >= 2 and runs[0]["status"] == "interrupted",
              f"{[r['status'] for r in runs]}")

        async def searched_seattle(t=t, tool=tool, key=key):
            return any("seattle" in c.get(key, "").lower() for c in await calls(t["thread_id"], tool))

        ok = await wait(f"{t['agent_name']} to search Seattle", searched_seattle)
        check(f"{t['agent_name']} searched again for Seattle", ok, f"{[c.get(key) for c in await calls(t['thread_id'], tool)]}")
    await cleanup(thread)


async def change_dates_after_booking():
    """After both are booked, new dates cancel the old bookings and book new ones."""
    thread = (await client.threads.create())["thread_id"]
    flight, hotel = await book_and_approve(thread)
    await wait("both tasks to report back", lambda: settled(thread))
    old = {"flight": await tool_results(flight["thread_id"], "BOOKED flight"),
           "hotel": await tool_results(hotel["thread_id"], "BOOKED hotel")}

    await say(thread, "Please move the trip: depart 2026-12-12 and return 2026-12-16. Same cities.")
    for t, graph, kind in [(flight, "flight_agent", "flight"), (hotel, "hotel_agent", "hotel")]:

        async def paused(t=t):
            return await thread_status(t["thread_id"]) == "interrupted"

        if not await wait(f"{graph} to ask approval for the new booking", paused):
            check(f"{graph} asked to approve a rebooking", False)
            continue
        await approve(t, graph)
        old_code = old[kind][0].split()[2].rstrip(":") if old[kind] else "?"
        booked = await tool_results(t["thread_id"], f"BOOKED {kind}")
        check(f"{graph} cancelled the old booking {old_code} (no double booking)",
              bool(booked) and f"CANCELLED the previous {kind} booking {old_code}" in booked[-1], booked[-1][-70:] if booked else "")
        check(f"{graph} rebooked for 2026-12-12", len(booked) == 2 and "2026-12-12" in booked[-1], booked[-1][:90] if booked else "")
    await wait("both tasks to report back", lambda: settled(thread))


async def cancel_hotel():
    """Dropping the hotel cancels only that task; the flight keeps going."""
    thread = (await client.threads.create())["thread_id"]
    await say(thread, TRIP)
    await say(thread, "Skip the hotel, I'm staying with friends. Keep the flight.")
    flight, hotel = await task(thread, "flight_agent"), await task(thread, "hotel_agent")
    check("supervisor cancelled the hotel task", hotel["status"] == "cancelled", f"hotel={hotel['status']}")
    flight_run = (await client.runs.get(flight["thread_id"], flight["run_id"]))["status"]
    check("flight task kept going", flight["status"] != "cancelled" and flight_run in {"pending", "running", "success"},
          f"flight task={flight['status']}, run={flight_run}")
    await cleanup(thread)


SCENARIOS = {f.__name__: f for f in (book_trip, change_cities, change_dates_after_booking, cancel_hotel)}


async def main() -> int:
    for name in sys.argv[1:] or SCENARIOS:
        print(f"\n=== {name}: {SCENARIOS[name].__doc__}", flush=True)
        try:
            await SCENARIOS[name]()
        except Exception as e:
            check(f"{name} ran without an exception", False, f"{type(e).__name__}: {e}")
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
