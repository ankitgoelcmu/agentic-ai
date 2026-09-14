# Routing Pattern

## Overview

Classify incoming requests and route them to specialized handlers using LLM-based decision logic.

## Implementation

Multi-department routing workflow:
1. **Classifier node** (`llm_call_router`): 
   - Uses LLM with structured output (Pydantic `Route` schema)
   - Classifies input into exactly ONE department: HR, FINANCE, or TECH_SUPPORT
   - Based on `CLASSIFIER_PROMPT` with strict decision rules
   
2. **Conditional routing**:
   - Decision determines next node path
   - Routes input to specialized handler based on classification
   
3. **Specialized handlers**:
   - `llm_call_hr`: Handles HR queries (hiring, payroll, benefits, policies)
   - `llm_call_finance`: Handles finance queries (invoices, budgets, accounting, taxes)
   - `llm_call_tech_support`: Handles technical queries (bugs, API issues, system outages)

## How It Works

```
           ┌─ llm_call_hr
INPUT → llm_call_router ─ if "HR"    ─┤
                                       ├─ END
                  ┌─ llm_call_finance
          ─ if "FINANCE"─┤
                       └─ llm_call_tech_support
                 ─ if "TECH_SUPPORT"
```

Structured output ensures deterministic routing without parsing errors.

## Use Cases

- **Customer service**: Route to HR, Finance, or Tech Support
- **Microservices**: Direct requests to appropriate backend service
- **Multi-tenant systems**: Route based on customer type or product
- **Specialized expertise**: Assign tasks to domain-specific handlers

## Key Learnings

- **Structured output**: Using Pydantic models prevents parsing errors and ensures valid routing decisions
- **Single classification**: Each input routes to exactly ONE path (no multi-routing)
- **Classification rules**: Clear, deterministic rules prevent misrouting ambiguous queries
