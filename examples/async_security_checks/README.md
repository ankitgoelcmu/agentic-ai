# Async Security Checks

The [parallel pattern](../../patterns/parallel) rebuilt on [Deep Agents async subagents](https://www.langchain.com/blog/agents-are-going-async), with a harness that tests each part of the feature against a local Agent Server.

## What changed from the parallel pattern

In [`security_checks.py`](../../patterns/parallel/security_checks.py), three checks fan out from `START` and `combine_results` waits for all of them. The whole graph blocks until the slowest check returns. That works when each check is one LLM call. It stops working when a check is a 90-second sandbox detonation and a person is waiting for an answer.

Here the same three checks run as **async subagents**, each on its own thread on the Agent Server. `combine_results` becomes a **supervisor** that starts them, replies to the user straight away, keeps talking while they run, and writes the combined verdict when the last one reports back.

```
parallel pattern (blocking)                 this example (async)

       ┌─ check_prompt_injection ─┐         user ⇄ supervisor ──start──▶ prompt_injection_checker ─┐
START ─┼─ check_pii              ─┼─ combine        │    ▲    ├──start──▶ pii_checker            ─┤
       └─ check_malware          ─┘   results       │    │    └──start──▶ malware_checker        ─┤
                                                    │    └────────── task notifications ◀──────────┘
                                                    └─ answers other questions while checks run
```

| | Parallel pattern | Async security checks |
|---|---|---|
| Checks | 3 nodes in one graph | 3 graphs, each its own thread |
| Who combines | `combine_results` node | supervisor agent |
| User waits for | the slowest check | the supervisor's first reply |
| Change a running check | not possible | `update_async_task` |
| Stop a running check | not possible | `cancel_async_task` |
| A check needs a human | not possible | task shows `waiting`, human answers on the check's thread |

## The feature, part by part

| Feature | Where it's used | Tested by |
|---|---|---|
| `start_async_task` returns at once | supervisor starts all three checks in one turn | `parallel` |
| Supervisor stays responsive | user asks an unrelated question mid-review | `parallel` |
| Thread tagging (`parent_thread_id`, `subagent_name`) | every check's thread | `parallel` |
| Task notifications (`deepagents_notification`) | results reach the supervisor without polling | `parallel`, `waiting` |
| `waiting` status + human answer on the subagent thread | `quarantine_sample` needs approval | `waiting` |
| `update_strategy="interrupt"` | correction to the malware check | `update_interrupt` |
| `update_strategy="enqueue"` | addition to the PII check | `update_enqueue` |
| `cancel_async_task`, `list_async_tasks` | stop the sandbox, list statuses | `cancel_list` |

## Files

- [`security_agents/supervisor.py`](security_agents/supervisor.py): the supervisor and the three `AsyncSubAgent` specs
- [`security_agents/checkers.py`](security_agents/checkers.py): the three checks, with their original system prompts
- [`security_agents/tools.py`](security_agents/tools.py): slow, deterministic scan tools (regex, plus a configurable `sleep` that stands in for real scan time)
- [`security_agents/models.py`](security_agents/models.py): one `get_llm()` for every agent, as in the original
- [`test_async_features.py`](test_async_features.py): the test harness
- [`langgraph.json`](langgraph.json): registers all four graphs in one deployment, so the supervisor reaches the checks in-process (ASGI, no `url`)

## Run it

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/) and [Ollama](https://ollama.com) with `qwen3-coder-next` pulled. Everything runs locally and costs nothing.

```bash
cd examples/async_security_checks
cp .env.example .env
uv sync

# terminal 1: the local Agent Server
uv run langgraph dev --no-browser --n-jobs-per-worker 10

# terminal 2: the tests
uv run python test_async_features.py                   # all scenarios
uv run python test_async_features.py parallel waiting  # or some of them
```

`--n-jobs-per-worker 10` matters. Every active run takes a worker slot: the supervisor, its three checks, and each notification run. With the default slots, starts queue up and the test looks hung.

To try the supervisor by hand, open LangGraph Studio from the URL `langgraph dev` prints and pick the `supervisor` graph.

### Using a different model

Set `SECURITY_MODEL` in `.env` to any `provider:model` string, for example `anthropic:claude-haiku-5-5`, and install the extra (`uv sync --extra anthropic`). That makes the run paid.

### Timing

The tools sleep for `INJECTION_SCAN_SECONDS`, `DLP_SCAN_SECONDS` and `SANDBOX_SECONDS` (20, 30 and 90 by default). The update and cancel tests only work if the check is still running when the follow-up arrives, so keep `SANDBOX_SECONDS` well above how long one supervisor turn takes on your model. On a slow local model, raise it.

## How the tests decide pass or fail

Each scenario talks to the supervisor as a user would, then checks the server's own records: run statuses on each check's thread, the task records in the supervisor's `async_tasks` state, thread metadata, and the notification messages. It doesn't trust what the model *says* happened.

A failure means one of two things, and the detail line tells you which:

- **The feature misbehaved.** For example, the first run on an `interrupt` update was not interrupted, or a result never reached the supervisor.
- **The model didn't call the tool the scenario asked for.** For example, it answered "I'll update the check" without calling `update_async_task`. This is more likely with small local models.

## Things I learned building it

- **Checks must be built with `create_deep_agent`.** It attaches the middleware that wakes the supervisor when a check finishes. A plain `create_agent` graph finishes silently, and the supervisor only learns the result if it polls.
- **The human answers on the check's thread, not the supervisor's.** The task ID is that thread's ID, so approving a quarantine is a `Command(resume=...)` run on the malware check's thread. The supervisor is never blocked by it.
- **The official example repo is behind the docs.** [`async-deep-agents`](https://github.com/langchain-ai/async-deep-agents) uses `async_subagents=` and `launch_async_subagent`. Current `deepagents` (0.7.30+) takes the specs in `subagents=` and names the tools `start_async_task`, `check_async_task` and so on.
- **The waiting status is pulled, not pushed.** A finished check wakes an idle supervisor. A check that pauses for approval does not. In my runs the supervisor saw `waiting` only on its next turn (here, when the user asked for status).
- **Don't let the model write the verdict early.** On the first run, the model saw `waiting`, decided it couldn't wait, and wrote a provisional `REVIEW` verdict. The real `BLOCK` came after the approval. The prompt now forbids a combined verdict while any check is unfinished, and the harness waits until every task is finished, not just for the first verdict.

## Reference

- [Agents are going async](https://www.langchain.com/blog/agents-are-going-async), LangChain blog
- [Async subagents docs (Python)](https://docs.langchain.com/oss/python/deepagents/async-subagents)
