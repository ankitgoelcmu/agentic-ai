# Eval Optimizer Pattern

## Overview

Generate output, evaluate against criteria, then iterate with feedback until quality criteria are met.

## Implementation

Iterative stock analysis generation and evaluation:

1. **Generator node** (`stock_analysis_generator`):
   - Creates initial stock analysis for a given ticker
   - On first run: generates comprehensive analysis
   - On subsequent runs: uses evaluator feedback to improve previous analysis
   
2. **Evaluator node** (`stock_analysis_evaluator`):
   - Structured output (Pydantic `Feedback` schema) with:
     - `grade`: "complete" or "not complete"
     - `feedback`: Specific guidance for improvement
   - Checks if analysis covers all required aspects:
     - Company overview, financial performance, competitive landscape
     - Future outlook, bull case, bear case, cited sources
   
3. **Feedback loop** (`route_stock_analysis`):
   - If grade == "not complete": Route back to generator with feedback
   - If grade == "complete": Exit to END
   - Iterates until quality criteria met

## How It Works

```
INPUT (ticker) ──→ stock_analysis_generator
                          ↓
                  stock_analysis_evaluator
                          ↓
                   Is complete?
                     /        \
                   No         Yes
                    ↓          ↓
            (with feedback)   END
                    ↓
                  generator (repeat)
```

## Use Cases

- **Content generation**: Write article → evaluate quality → improve → repeat
- **Code generation**: Generate code → evaluate correctness/security → refactor → repeat
- **Financial analysis**: Analyze stock → check completeness → improve → repeat
- **Report generation**: Create report → evaluate coverage → add missing sections → repeat

## Key Learnings

- **Clear completion criteria**: Structured evaluation prevents infinite loops
- **Feedback loop design**: Evaluator feedback must be actionable for the generator
- **Iteration limits**: Consider max iterations to prevent runaway loops
- **Quality over speed**: Trading longer execution for higher-quality output

## Reference

This pattern is based on [Anthropic's "Building Effective Agents"](https://www.anthropic.com/engineering/building-effective-agents) blog post on agentic loops and evaluation strategies.
