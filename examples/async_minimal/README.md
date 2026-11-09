# Async Subagents: Minimal Example

The smallest working example of [Deep Agents async subagents](https://www.langchain.com/blog/agents-are-going-async): a supervisor starts a flight search in the background, replies at once, and takes a change of city while the search is still running.

```bash
uv sync
uv run langgraph dev --n-jobs-per-worker 10   # terminal 1
uv run python run.py                          # terminal 2
```

You should see:
1. A reply within seconds, while the search is still running.
2. "Make it Seattle" updates the running search instead of waiting for it.
3. About 30 seconds later, the Seattle result arrives on its own.

The `asyncio.sleep(30)` in `search_flights` fakes a slow real API. Without it the search finishes too fast to change it mid-run. In real code, remove it.

Runs on a local Ollama model (`qwen3-coder-next`), so it costs nothing. For a fuller version with a hotel agent, booking approvals and tests, see [async_travel_booking](../async_travel_booking).
