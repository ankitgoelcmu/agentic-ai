# Prompt Chaining Pattern

## Overview

Break down a complex task into sequential steps where each step's output becomes the next step's input.

## Implementation

Software design generation workflow with 3 chained LLM calls:

1. **Generate HLD** (High-Level Design)
   - Input: Component requirement description
   - Output: JSON HLD covering overview, architecture, components, data flow, APIs, scalability, security, observability, tradeoffs

2. **Generate LLD** (Low-Level Design)
   - Input: HLD from step 1
   - Output: Detailed LLD with implementation specifics, component interfaces, data structures, algorithms

3. **Generate Code**
   - Input: LLD from step 2
   - Output: Production-ready code implementation

## How It Works

```
Topic/Requirement
      ↓
  generate_HLD()
      ↓
    HLD JSON
      ↓
  generate_LLD()
      ↓
    LLD Document
      ↓
  generate_code()
      ↓
   Code Output
```

Each step is a specialized LLM call with:
- Specific system prompt for that role (architect → engineer → developer)
- Previous step's output as context
- Deterministic output (temperature=0)

## Use Cases

- **Software design**: Requirement → HLD → LLD → Code
- **Content creation**: Topic → outline → draft → final → translate
- **Problem solving**: Problem → analysis → solution → implementation
- **Multi-stage reasoning**: Complex tasks requiring stepwise refinement

## Key Learnings

- **Role specialization**: Each step uses a specialized system prompt (architect, engineer, developer)
- **Context dependency**: Each step relies on previous step's output for accurate continuation
- **Sequential execution**: Cannot parallelize these steps (unlike parallel pattern) because of dependencies
- **Clarity & specification**: Each step should produce clear, structured output for next step to consume

## When to Use Prompt Chaining

✅ When output of one step is input to the next  
✅ When each step requires different expertise/role  
✅ When task is complex and benefits from decomposition  
✅ When intermediate outputs are useful/inspectable  

❌ Not ideal for independent parallel tasks (use Parallel pattern instead)  
❌ Not ideal for decision-based routing (use Routing pattern instead)  

## Reference

Based on [Anthropic's "Building Effective Agents"](https://www.anthropic.com/engineering/building-effective-agents) blog post.
