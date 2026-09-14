# Parallel Pattern

## Overview

Execute multiple independent verification tasks in parallel on the same input, then aggregate results for a unified decision.

## Implementation

Security check workflow using LangGraph state machine:
1. **Parallel execution** from START → 3 independent security checks run simultaneously
2. **Check nodes** (3 LLM calls in parallel):
   - `check_prompt_injection`: Detects prompt injection attempts
   - `check_pii`: Detects personally identifiable information
   - `check_malware`: Detects malware/hacking content
3. **Aggregation**: Results from all 3 checks feed into `combine_results` node
4. **Output**: Single combined verdict summarizing security risks

## How It Works

```
       ┌─ check_prompt_injection ─┐
START ├─ check_pii              ─┤─ combine_results ─ END
       └─ check_malware          ─┘
```

All three checks run in parallel against the same input, then results are combined by an LLM into a single security assessment.

## Use Cases

- **Security filtering**: Multi-angle input validation (injection, PII, malware)
- **Code review**: Parallel checks for security, functionality, performance
- **Multi-perspective analysis**: Get diverse viewpoints on a single topic

## Key Learnings

- **Independent subtasks**: Only use parallelization when subtasks don't depend on each other
- **Fan-in aggregation**: Results flow from parallel nodes into a single aggregation node
- **Resource efficiency**: 3 checks that take 2s each run in ~2s total instead of 6s sequentially
