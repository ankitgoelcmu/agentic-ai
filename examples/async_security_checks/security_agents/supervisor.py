"""Supervisor: the `combine_results` node, promoted to an agent that stays available.

In the parallel pattern the graph blocked until all three checks returned,
then combined them. Here the supervisor starts the three checks as async
subagents, answers the user straight away, keeps talking while they run, and
writes the combined verdict once every check has reported back.

`AsyncSubAgentMiddleware` (added by `create_deep_agent` for `AsyncSubAgent`
specs) gives the supervisor five tools: start_async_task, check_async_task,
update_async_task, cancel_async_task and list_async_tasks.

No `url` in the specs, so the subagents are reached over in-process ASGI
transport. That needs all four graphs in the same langgraph.json.
"""

from deepagents import AsyncSubAgent, create_deep_agent

from security_agents.models import get_llm

SYSTEM_PROMPT = """\
You are the coordinator of a security review team. For every input the user submits for review,
you run three independent checks in parallel, then combine their verdicts for the security team.

## When the user submits an input for review
1. Call start_async_task three times in the same turn, once per check: prompt_injection_checker,
   pii_checker and malware_checker. Pass the user's input text verbatim in each description.
2. Reply in one or two sentences that the three checks are running. Then stop.
   Do not check status right after starting. Results arrive on their own.

## While checks are running
- Answer any other question directly and briefly. You do not need the checks to do that.
- If the user corrects or adds to the input, call update_async_task on the affected check(s).
- If the user asks to stop a check, call cancel_async_task.
- If the user asks for status, call list_async_tasks or check_async_task first, because statuses
  in the conversation history are stale. A `waiting` check needs a human decision on that
  check's own thread; tell the user, you cannot approve it for them.

## When a check reports back
- If some checks are still unfinished (running, pending or waiting), say in one line which check
  finished and its verdict. Do not write a combined verdict yet, not even a provisional one.
- Only when all three are finished (success, error or cancelled), write the combined assessment:

COMBINED VERDICT: <SAFE | REVIEW | BLOCK>
- Prompt injection: <Yes/No> - <reason>
- PII: <Yes/No> - <reason>
- Malware: <Yes/No> - <reason, and whether the sample was quarantined>
Summary: <two sentences on the overall risk for the security team>

Use BLOCK if any check found malware or prompt injection, REVIEW if only PII was found,
and SAFE if nothing was found. A cancelled check counts as not run; say so.
"""

ASYNC_SUBAGENTS: list[AsyncSubAgent] = [
    {
        "name": "prompt_injection_checker",
        "description": "Detects prompt injection attempts in the input. Takes about 20 seconds.",
        "graph_id": "prompt_injection_checker",
    },
    {
        "name": "pii_checker",
        "description": "Detects personally identifiable information in the input. Takes about 30 seconds.",
        "graph_id": "pii_checker",
        # Follow-ups wait until the current scan finishes, then run on the same
        # thread. Fits additions ("also check this second record").
        "update_strategy": "enqueue",
    },
    {
        "name": "malware_checker",
        "description": (
            "Detonates the described file or payload in a sandbox and quarantines it if malicious. "
            "Slowest check, about 90 seconds. Quarantine needs a human's approval."
        ),
        "graph_id": "malware_checker",
        # Default strategy, stated for clarity: a follow-up stops the current
        # run and restarts it with the correction. Fits fixes ("wrong file").
        "update_strategy": "interrupt",
    },
]

graph = create_deep_agent(
    model=get_llm(),
    system_prompt=SYSTEM_PROMPT,
    subagents=ASYNC_SUBAGENTS,
    name="supervisor",
)
