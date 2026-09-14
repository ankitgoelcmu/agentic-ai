# Sigma Rule Writer Example

## Overview

A multi-agent detection engineering system that generates production-ready Sigma YAML rules from adversary behavior descriptions using a hybrid approach:
- **LLM-based generation** (qwen3-coder-next via Ollama)
- **LangSmith observability** for trace analysis and debugging
- **Subagent architecture** for isolated threat research

## Architecture

**Main Agent** (Detection Engineer)
- Orchestrates the 5-step workflow
- Uses `sigma_search` and `sigma_validate` tools directly
- Delegates research to subagent (not main agent)
- Returns final YAML rule

**Research Subagent**
- Isolated from main agent to avoid processing raw web content
- Uses `tavily_search` to find real-world threat intelligence
- Returns condensed, bounded summary to main agent
- Matches Elastic Security Labs SOC agent pattern (pattern-finder vs investigator split)

## Tools

- **`sigma_search(description)`**: Find structurally similar rules in Sigma corpus for reference
- **`sigma_validate(yaml_string)`**: Check YAML syntax and Sigma taxonomy compliance
- **`tavily_search(query)`**: Web search for current threat intelligence (subagent only)
- **`reset_search_counter()`** / **`reset_tavily_counter()`**: Control tool call budgets

## Workflow

```
┌─ Search (sigma_search)
│   └─ Find existing rules for reference
│
├─ Research (research-agent via task())
│   └─ Tavily search × 2-3 for current threat intel
│
├─ Draft
│   └─ Write new Sigma rule with search + research results
│
├─ Validate (sigma_validate)
│   └─ Check YAML syntax and Sigma field taxonomy
│   └─ If invalid: Fix and re-validate (max 2 attempts)
│
└─ Output: Final YAML rule
```

## Tool Call Budgets (Prevent Excessive Calls)

- `sigma_search`: 1 call maximum per request
- `research-agent`: 1 delegation per request (always required)
- `tavily_search`: 2-3 calls max (inside subagent, 5 total allowed)
- `sigma_validate`: 2 calls max

## Key Rules for Rule Generation

**Detection Block Design**:
- Malicious indicators found by research go in `selection` (what to match)
- Filter blocks exclude benign noise only (never exclude malicious indicators)
- Cannot use regex shorthand (e.g., `[0-9]`) in `contains` fields; must use `|re:` modifier

**Sigma Taxonomy Compliance**:
- Only established logsource categories: `process_creation`, `network_connection`, `file_event`, etc.
- Only real field names: `Image`, `CommandLine`, `DestinationHostname`, `TargetFilename`
- Never invent new fields; translate high-level concepts into concrete runtime artifacts

**Common Pitfalls** (checked before calling validate):
- Unquoted colons in strings cause YAML parse failures
- Never create duplicate selection/filter blocks (edit existing instead)
- Regex-like patterns in `contains` are treated as literal strings
- If logsource is too high-level (e.g., supply-chain attack), decompose into process/file/network artifacts

## Middleware

- **`TodoListMiddleware`**: Tracks tasks and subtasks during agent execution
- **`CodeInterpreterMiddleware`**: Enables code interpretation in thread mode
- **`LoopDetectionMiddleware`**: Prevents infinite reasoning loops (max_repeats=1)

## Files

- `detection_rules_writer.py` - Main agent with workflow orchestration
- `tools.py` - Tool implementations with Sigma repo integration
- `middleware.py` - Custom `LoopDetectionMiddleware` class

## Running

```bash
# Setup
cd examples/sigma_rule_writer
python -m pip install -r requirements.txt

# Configure
export OLLAMA_MODEL=qwen3-coder-next  # Must be running locally on port 11434
export TAVILY_API_KEY=your_key
export LANGSMITH_API_KEY=your_key  # Optional, for trace visualization

# Run
python detection_rules_writer.py
```

## Example Input

```
A malicious npm package masquerading as a legitimate developer tool is installed 
via a compromised dependency chain, triggering a preinstall script that silently 
downloads and launches a secondary interpreter runtime. The dropped payload 
specifically enumerates and targets configuration files belonging to multiple 
AI coding assistant CLI tools, including Claude Code, Cursor, and Codex CLI, 
alongside SSH keys, cloud provider credentials, and version control tokens.
```

## Output

Valid YAML Sigma rule ready for:
- Deployment to SIEM systems (ELK, Splunk, etc.)
- Sharing with detection engineering community
- Integration into detection pipelines

## Tracing & Observability

Use LangSmith for:
- Trace inspection: View each tool call, LLM invocation, and subagent delegation
- Debug latency: Identify which steps consume most time
- Iterate: Tweak prompts and see results in trace viewer

Set `LANGSMITH_API_KEY` to enable automatic tracing.
