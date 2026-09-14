# Routing Pattern

## Overview

Route requests to specialized agents based on input classification.

## Use Case

When different types of requests require different handling:
- Customer service routing (billing, technical, general)
- Content routing (code review, documentation, testing)
- Task-specific agent selection

## Components

- `example.py` - Working example showing routing logic
- `tests/` - Unit and integration tests

## Key Concepts

- Input classification
- Agent selection
- Routing strategy
- Fallback handling

## Example

```python
# See example.py for full implementation
router = AgentRouter(agents={
    "technical": technical_agent,
    "billing": billing_agent,
    "general": general_agent
})
result = router.route(input_text)
```
