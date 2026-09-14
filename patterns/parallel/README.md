# Parallel Pattern

## Overview

Run multiple agents concurrently and aggregate their results.

## Use Case

When a task can be decomposed into independent subtasks that can be handled by specialized agents in parallel:
- Fact-checking from multiple sources
- Multi-perspective analysis
- Parallel research across different domains

## Components

- `example.py` - Working example showing parallel agent execution
- `tests/` - Unit and integration tests

## Key Concepts

- Independent agent execution
- Result aggregation
- Error handling across parallel tasks
- Resource management

## Example

```python
# See example.py for full implementation
agents = [agent1, agent2, agent3]
results = await asyncio.gather(*[agent.invoke(task) for agent in agents])
aggregated = aggregate_results(results)
```
