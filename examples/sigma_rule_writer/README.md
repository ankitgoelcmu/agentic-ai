# Sigma Rule Writer Example

## Overview

A multi-agent detection engineering system that generates production-ready Sigma YAML rules from adversary behavior descriptions using Claude (Anthropic) and specialized subagents:

- **Main Agent**: Claude Sonnet 4.6 orchestrates multi-technique workflows
- **URL Reader Subagent**: Claude Haiku 4.5 extracts attack techniques from threat intelligence reports
- **Web Search Subagent**: Claude Haiku 4.5 conducts real-world threat research via Tavily
- **Resource Control**: Middleware enforces limits on tool and model calls to prevent runaway execution
- **Multi-Technique Support**: Can extract and generate rules for 5+ techniques from a single threat intelligence URL

## Architecture

**Main Agent** (Detection Engineer - Claude Sonnet 4.6)
- Orchestrates workflow for one or multiple attack techniques
- Uses `sigma_search` and `sigma_validate` tools directly (fast, deterministic Python functions)
- Delegates URL reading and web research to specialized subagents (unpredictable, untrusted external data)
- Manages todo list for multi-technique scenarios (extracts 5 max techniques from a URL)
- Returns final YAML rules, one per technique, separated by `=== NEXT RULE ===`

**URL Reader Subagent** (Claude Haiku 4.5)
- Specialized for reading and parsing threat intelligence reports from URLs
- Uses `read_url` tool to safely load external content with character limits
- Extracts distinct attack techniques from unstructured threat reports
- Marks content as untrusted (prevents prompt injection from external data)
- Hard-coded to read_url exactly once, preventing runaway downloads

**Web Search Subagent** (Claude Haiku 4.5)
- Specialized for real-world threat intelligence research
- Uses `tavily_search` to find current, authoritative sources
- Targets threat intelligence publishers: Mandiant, CrowdStrike, Microsoft Security, Unit 42, Recorded Future, The DFIR Report, SANS ISC
- Returns only specific technical detail (command patterns, file paths, registry keys, network indicators, MITRE ATT&CK IDs)
- Separated from main agent to keep main agent focused on rule generation, not raw web content

## Tools

**Main Agent Tools** (direct access)
- **`sigma_search(description)`**: Search local Sigma rule corpus for structurally similar rules (fast, keyword-based)
- **`sigma_validate(yaml_string)`**: Validate YAML syntax and Sigma field taxonomy, convert to Sumo Logic query to catch logical errors

**URL Reader Subagent Tools** (isolated)
- **`read_url(url)`**: Safely load web page content with 16K char limit, marks content as untrusted

**Web Search Subagent Tools** (isolated)
- **`tavily_search(query)`**: Search web for current threat intelligence with 3 results max per search

**Middleware Limits** (prevent runaway execution)
- Main agent: `sigma_search` max 8 calls, `sigma_validate` max 5 calls, `task()` max 10 delegations
- URL reader: `read_url` exactly 1 call (hard-coded exit on completion)
- Web search: `tavily_search` max 50 calls (lenient, agent-controlled via reasoning)

## Workflow

For each input, the system follows this process:

```
0. INTAKE (if URL provided)
   └─ Delegate to url-reader-agent to read URL and extract techniques
   └─ (Optionally) Delegate to web-search-agent in parallel for current threat detail
   └─ Create todo list: one task per technique (max 5 from URL)

For each technique (from todo list or single technique if no URL):

1. SEARCH (sigma_search)
   └─ Find existing Sigma rules for reference (structure, field names, logsource)

2. RESEARCH (web-search-agent via task())
   └─ Gather current real-world detail on this specific technique
   └─ Unless Step 0 already provided sufficient detail

3. DRAFT
   └─ Write new Sigma rule matching this specific technique
   └─ Use https://sigmahq.io/docs/basics/rules.html for Sigma syntax
   └─ Check all rules before validating (see "Key Rules" section)

4. VALIDATE (sigma_validate × max 2 attempts)
   └─ Check YAML syntax, field names, condition references
   └─ Convert to Sumo Logic query to catch logical errors
   └─ If invalid: Fix and re-validate

5. OUTPUT
   └─ Return final YAML rule
   └─ If multiple techniques, separate each with: === NEXT RULE ===
```

**Key Insight**: URL readers and web searchers are isolated subagents because they handle untrusted external data. Main agent stays focused on rule generation with structured tools.

## Key Rules for Rule Generation

**Detection Block Design** (checked before sigma_validate):
- **Selection vs Filter**: Malicious indicators go in `selection` (criteria to match). Filter only excludes benign noise, never the malicious behavior being detected.
- **Regex in contains fields**: `contains` does literal substring matching only. Convert bracket/character-class notation (`[0-9]{2,4}`) to Sigma's `|re:` modifier, or extract concrete literal values instead.
- **Quote colons**: Any string containing a colon (URLs, timestamps, descriptions) must be quoted. Unquoted colons cause YAML parse failures.
- **No duplicate keys**: Never create a second block with same name. Always edit the existing block when fixing issues.
- **Correlation rules for counting/sequencing**: Counting or sequencing across a shared field within a time window CANNOT be expressed as a single condition string. Use Sigma's correlation rule format: a base detection rule, followed by a separate YAML document (separated by ---) with "correlation" key containing type, rules, group-by, timespan, condition. Never invent inline syntax like `field|count(window) > N`.

**Sigma Taxonomy Compliance** (never invent):
- Only established logsource categories: `process_creation`, `network_connection`, `file_event`, `image_load`, `registry_event`, etc.
- Only real field names: `Image`, `CommandLine`, `DestinationHostname`, `TargetFilename`, `EventID`, `Image`, `ParentImage`, etc.
- Never invent new fields or logsource categories. Translate high-level concepts (supply-chain attacks, lateral movement) into concrete runtime artifacts on a real endpoint (processes spawned, files accessed, network connections made).

**Sigma Standard Reference**:
- https://sigmahq.io/docs/basics/rules.html - Sigma rule format specification
- Use existing rules in search results as templates for structure, not to copy verbatim

## Middleware

**Main Agent Middleware**:
- **`TodoListMiddleware`**: Tracks techniques to process (creates one todo per technique extracted from URL)
- **`ToolCallLimitMiddleware`**: Enforces limits per tool type
  - `sigma_search`: max 8 calls (prevents repetitive searches)
  - `sigma_validate`: max 5 calls (prevents infinite refinement loops)
  - `task()`: max 10 delegations (prevents excessive subagent spawning)

**URL Reader Subagent Middleware**:
- **`ModelCallLimitMiddleware`**: max 5 model calls (quick read and extraction)
- **`ToolCallLimitMiddleware`**: `read_url` exactly 1 call with hard exit (prevents downloading multiple URLs)

**Web Search Subagent Middleware**:
- **`ModelCallLimitMiddleware`**: max 50 model calls (allows reasoning about search results)
- **`ToolCallLimitMiddleware`**: `tavily_search` max 50 calls with continue behavior (agent can iterate on searches)

## Files

- `detection_rules_writer.py` - Main agent with workflow orchestration
- `tools.py` - Tool implementations with Sigma repo integration
- `middleware.py` - Custom `LoopDetectionMiddleware` class

## Running

```bash
# Setup
cd examples/sigma_rule_writer
pip install -r requirements.txt

# Configure environment
export ANTHROPIC_API_KEY=your_claude_api_key  # Required (get from https://console.anthropic.com)
export TAVILY_API_KEY=your_tavily_key        # Required for web-search-agent
export LANGSMITH_API_KEY=your_langsmith_key  # Optional, for trace visualization

# Run with threat intelligence URL
python detection_rules_writer.py
# Input: "Here is a threat intelligence report: https://www.anthropic.com/threat-intelligence-report-september-2026"
# Output: Multiple Sigma rules, one per technique found in the URL

# Or run with direct technique description
python detection_rules_writer.py
# Input: "A malicious npm package downloads and launches a secondary interpreter runtime..."
# Output: Single Sigma rule for that technique
```

**Models Used**:
- **Main Agent**: `anthropic:claude-sonnet-4-6` (reasoning about rules, tool use)
- **URL Reader**: `anthropic:claude-haiku-4-5-20251001` (fast URL parsing)
- **Web Search**: `anthropic:claude-haiku-4-5-20251001` (efficient threat research)

## Example Input (Direct Technique)

```
A malicious npm package masquerading as a legitimate developer tool is installed 
via a compromised dependency chain, triggering a preinstall script that silently 
downloads and launches a secondary interpreter runtime. The dropped payload 
enumerates configuration files (Claude Code, Cursor, Codex CLI), SSH keys, cloud 
credentials, and version control tokens. Encrypted strings and TLS command-and-control 
bypass traditional HTTP monitoring hooks.
```

Expected Output: Single production-ready Sigma rule detecting this package behavior.

## Example Input (URL with Multiple Techniques)

```
Here is a threat intelligence report describing attack techniques currently used by hackers:
https://www.anthropic.com/threat-intelligence-report-september-2026
```

Expected Output: Multiple Sigma rules, one for each distinct attack technique extracted from the report.

## Real-World Example Output

See `examples/threat_intelligence_report_sample.md` for a complete example:

- **Input**: Threat intelligence URL describing September 2026 attack techniques
- **Output**: 5 production-ready Sigma rules covering:
  1. AI-driven malware staging and evasion
  2. Device code phishing (Azure AD token theft)
  3. ClickFix social engineering (Windows Run dialog)
  4. WhatsApp account takeover automation
  5. Microsoft 365 bulk email exfiltration
- **Validation**: All rules pass sigma_validate and convert to Sumo Logic queries
- **Attribution**: Real threat actors (Midnight Blizzard, Embassy Kit, Storm-2372)

## Output

Valid YAML Sigma rules ready for:
- Deployment to SIEM systems (ELK, Splunk, Sumo Logic, etc.)
- Sharing with detection engineering community
- Integration into detection pipelines
- Conversion to backend-specific queries (Sumo Logic validated)

Rules are separated by `=== NEXT RULE ===` if multiple techniques are detected from a URL.

## Why Claude (Anthropic) Over Ollama?

**Claude Advantages**:
- Superior reasoning for multi-technique extraction from URLs
- Better understanding of threat intelligence prose (unstructured text parsing)
- More reliable Sigma syntax generation (fewer validation failures)
- Specialized Haiku model for fast, focused subagent work (URL reading, web search)
- Extended context window handles full threat reports + reference rules
- Production-grade reliability and consistent quality

**When Ollama May Be Preferred**:
- Offline/airgapped environments
- Cost-sensitive deployments at scale
- Fine-tuned models for specific domain knowledge
- Full control over model behavior

This example demonstrates **production-ready agentic patterns** with Claude. For local LLM versions, see the patterns directory for Ollama-based examples.

## Tracing & Observability

Use LangSmith for:
- **Trace inspection**: View each tool call, LLM invocation (main + subagents), middleware decisions
- **Multi-agent visibility**: See how url-reader and web-search subagents execute in parallel
- **Latency analysis**: Identify which steps consume most time (URL reading vs research vs rule generation)
- **Iteration**: Modify system prompts and see results in trace viewer immediately

Enable with:
```bash
export LANGSMITH_API_KEY=your_key
export LANGSMITH_PROJECT=sigma-rule-writer
```

Then visit https://smith.langchain.com to inspect traces.
