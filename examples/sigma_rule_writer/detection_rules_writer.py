# agent.py
#
# Design note: sigma_search and sigma_validate are kept as direct tools on the
# main agent, not wrapped as subagents. Both are fast, deterministic Python
# function calls with a single correct output, no reasoning involved, so
# subagent isolation would only add latency and cost for zero benefit.
#
# tavily_search IS wrapped as a subagent (research-agent), because it's the
# opposite case: unpredictable in size and content, and technically untrusted
# since it returns real web pages. Isolating it means the main agent never
# processes raw web content directly, only the subagent's condensed, bounded
# report, matching the pattern-finder-vs-investigator split from the Elastic
# Security Labs SOC agent blog post.

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage
from langchain.agents.middleware import TodoListMiddleware
from deepagents.backends import LangSmithSandbox
from langchain_quickjs import CodeInterpreterMiddleware
from langchain.agents.middleware import ToolCallLimitMiddleware, ModelCallLimitMiddleware




from tools import sigma_search, sigma_validate, tavily_search

RESEARCHER_INSTRUCTIONS = """You are a threat intelligence research sub-agent. Given a description of
adversary behavior, research it on the web to surface real-world, current technical detail beyond
what a static rule corpus like SigmaHQ can provide, since the threat landscape evolves faster than
any fixed dataset can track.

You have access to tavily_search.

**Search strategy:**
- Prioritize authoritative, current sources: known threat intelligence and detection engineering
  publishers (Mandiant/Google Threat Intelligence, CrowdStrike, Microsoft Security, Unit 42,
  Recorded Future, The DFIR Report, SANS Internet Storm Center), MITRE ATT&CK itself, and recent
  CVE or security advisories.
- Include at least one query that explicitly targets recency (include "2026" or "latest" in the
  query, not just the technique name alone).
- If the first search returns only generic or dated material, narrow with a more specific term (a
  named tool, malware family, or technique variant) and search again.

**Return format:**
Structured, specific technical detail only: exact command-line patterns, process names, registry
keys, file paths, network indicators, known threat actor or tool associations, MITRE ATT&CK
technique IDs, and how recent the cited behavior is if known. No citations, no meta-commentary,
no general overview, only what's directly useful for writing detection logic.
"""


SIGMA_AGENT_INSTRUCTIONS = r"""# Sigma Rule Writing Workflow

You are an expert detection engineer. Given a description of adversary behavior, follow this
workflow to produce a complete, valid Sigma rule in YAML.

1. **Search**: Call sigma_search to find existing rules structurally similar to the described
   behavior. Use these as reference for conventions, not to copy verbatim.
2. **Research (mandatory)**: Delegate to research-agent via task() to find current, real-world
   technical detail on the technique. This step always runs, regardless of whether the
   description already contains detail, since SigmaHQ's static corpus may not reflect the
   latest threat landscape.
3. **Draft**: Write a new rule tailored to the described behavior, incorporating both the search
   and research results: title, id (new UUID), status, description, references, author, tags
   (MITRE ATT&CK IDs), logsource, a detection block with a condition, falsepositives, level.
4. **Validate**: Call sigma_validate. If it reports issues, fix them and validate again. Note
   that sigma_validate only checks structural correctness, it cannot detect whether the
   detection logic is inverted or logically backwards, that check in step 3 is your
   responsibility alone.
5. **Respond**: Output only the final YAML rule, no explanation, no markdown formatting around it.
6. "Never delegate to any subagent other than research-agent.
    Do not use task() for any purpose other than the mandatory research step in Step 2."
7. Do NOT use any filesystem tools for this task (write_file, read_file, edit_file, delete,
glob, ls, grep). This workflow never needs to read or write files, search the rule corpus
via sigma_search only, draft the rule directly in your own reasoning, and pass it straight
to sigma_validate.

## Rules for building the detection block, check every one before calling sigma_validate

- **Filter vs. selection**: malicious indicators surfaced by research-agent belong in
  `selection`, as criteria to match ON. `filter` exists only to exclude known-benign noise,
  never to exclude the malicious behavior the rule is meant to detect. Before finalizing the
  condition, check: does anything in `filter` overlap with a malicious indicator? If so, move
  it to `selection`.
- **Regex-like shorthand is not literal text**: `contains` performs literal substring matching
  only. If research findings describe a pattern using bracket/character-class notation (e.g.
  attacker[0-9]{2,4}\.xyz), convert it to Sigma's |re: modifier, or extract concrete literal
  example values instead of copying the shorthand notation verbatim.
- **Quote any string containing a colon** (URLs, timestamps, punctuation in a description). An
  unquoted colon followed by a space causes a YAML parse failure.
- **Never duplicate a key name.** When fixing a reported issue, edit the existing block, do not
  add a new one with the same name.
- **Use only real, established Sigma logsource categories and fields** (process_creation,
  network_connection, file_event, etc. under a real product like windows/linux/macos, with
  standard fields like Image, CommandLine, DestinationHostname). Never invent a logsource or
  field name. If the described behavior is a higher-level concept (a supply-chain or
  package-manager attack), translate it into the concrete runtime artifacts it would produce
  on a real endpoint, the process spawned, files accessed, network connections made, and build
  the rule from those instead.
- **Counting, sequences, or correlation across a shared field (e.g. same source IP) within a
  time window CANNOT be expressed as a single condition string.** Use Sigma's correlation rule
  format instead: a base detection rule (with its own id), followed by a separate YAML document
  (separated by three hyphens on their own line) containing a top-level "correlation" key with:
  type (one of event_count, value_count, temporal, temporal_ordered), rules (a list containing
  the id of the base rule above), group-by (the field to correlate on, e.g. source_ip), timespan
  (e.g. 10m), and condition (e.g. gte: 5). Never invent inline aggregate syntax like
  field|count(window) > N inside a condition string, that is not valid Sigma syntax.

## Stop Immediately When
- sigma_validate returns VALID
- You have called sigma_validate twice, regardless of outcome

## General Guidelines
- The detection logic must actually match the behavior described, never return a searched
  rule unchanged, even if it looks similar
- Prioritize specificity from research-agent findings over generic detection logic from
  sigma_search alone
- Do NOT use write_file or read_file for this task. Draft the rule directly in your own
  reasoning and pass it straight to sigma_validate.
"""

research_sub_agent = {
    "name": "research-agent",
    "description": "Delegate researching real-world technical detail about one attack technique.",
    "system_prompt": RESEARCHER_INSTRUCTIONS,
    "tools": [tavily_search],
    "max_subagent_calls": 5,
}
model = init_chat_model(model="ollama:qwen3-coder-next", temperature=0.0)

agent = create_deep_agent(
    model=model,
    tools=[sigma_search, sigma_validate],  # tavily_search intentionally NOT here, see design note
    system_prompt=SIGMA_AGENT_INSTRUCTIONS,
    subagents=[research_sub_agent],
    #middleware=[TodoListMiddleware()], #LoopDetectionMiddleware()
    middleware=[
    ToolCallLimitMiddleware(tool_name="sigma_search", run_limit=2, exit_behavior="continue"),
    ToolCallLimitMiddleware(tool_name="sigma_validate", run_limit=3, exit_behavior="continue"),
    ToolCallLimitMiddleware(tool_name="write_file", run_limit=1, exit_behavior="continue"),
    ToolCallLimitMiddleware(tool_name="task", run_limit=1, exit_behavior="continue"),
]

)


if __name__ == "__main__":
    


    result = agent.invoke(
        {
            "messages": [
                HumanMessage(
                    content=(
                      "Multiple failed authentication attempts against an AI service provider's API endpoint "
                        "originate from the same source IP address within a short time window, consistent with "
                        "credential stuffing using a list of previously breached API keys. Shortly afterward, a "
                        "successful authentication occurs from that same source IP, followed immediately by an "
                        "unusually large volume of data retrieval requests against the compromised account, "
                        "consistent with an attacker exploiting newly gained access before the legitimate account "
                        "owner notices the compromise. This pattern of repeated failures followed by a successful "
                        "login and immediate high-volume activity from the same source is a recognized indicator "
                        "of automated credential-stuffing attacks against AI API providers."
                    )
                )
            ]
        },
        config={"recursion_limit": 65 },
    )

    for msg in result.get("messages", []):
        if hasattr(msg, "content") and msg.content:
            print(msg.content)