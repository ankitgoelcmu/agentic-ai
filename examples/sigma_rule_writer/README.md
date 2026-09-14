# Sigma Rule Writer Example

## Overview

A complete agentic system for generating Sigma detection rules from natural language descriptions of adversary behavior.

## Architecture

- **Main Agent**: Detection engineer agent that orchestrates the workflow
- **Research Subagent**: Gathers real-world threat intelligence via web search
- **Tools**: 
  - `sigma_search`: Find existing similar rules for reference
  - `sigma_validate`: Validate YAML syntax and Sigma compliance
  - `tavily_search`: Research threat intel (via subagent)

## Middleware Stack

- `TodoListMiddleware`: Tracks agent tasks
- `CodeInterpreterMiddleware`: Enables code execution
- `LoopDetectionMiddleware`: Prevents infinite loops

## Workflow

1. **Search**: Find existing Sigma rules similar to the described behavior
2. **Research**: Delegate to research subagent to find current threat intel
3. **Draft**: Write a new Sigma rule incorporating search and research results
4. **Validate**: Validate the rule syntax and semantic correctness
5. **Return**: Output the final YAML rule

## Files

- `detection_rules_writer.py` - Main agent implementation
- `tools.py` - Tool definitions (sigma_search, sigma_validate, tavily_search)
- `middleware.py` - Custom middleware (LoopDetectionMiddleware)

## Running

```bash
# Set environment variables
export OLLAMA_MODEL=qwen3-coder-next
export TAVILY_API_KEY=your_key

# Run the agent
python detection_rules_writer.py
```

## Example Input

```
A malicious npm package masquerading as a legitimate developer tool is installed 
via a compromised dependency chain, triggering a preinstall script that silently 
downloads and launches a secondary interpreter runtime...
```

## Output

Valid Sigma YAML rule ready for deployment.
