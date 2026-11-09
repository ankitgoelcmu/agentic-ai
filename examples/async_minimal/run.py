"""Talk to the supervisor: ask, change your mind mid-search, get the result."""

import asyncio

from langgraph_sdk import get_client

client = get_client(url="http://127.0.0.1:2024")


async def say(thread, text):
    print("you:", text)
    await client.runs.wait(
        thread,
        "supervisor",
        multitask_strategy="enqueue",
        input={"messages": [{"role": "user", "content": text}]},
    )
    await show(thread)


async def show(thread):
    state = await client.threads.get_state(thread)
    print("agent:", state["values"]["messages"][-1]["content"], "\n")


async def main():
    thread = (await client.threads.create())["thread_id"]
    await say(thread, "Find me a flight to Portland.")  # replies in seconds; search keeps running
    await say(thread, "Actually, make it Seattle.")  # changes the running search
    await asyncio.sleep(45)  # the result arrives on its own
    await show(thread)


asyncio.run(main())
