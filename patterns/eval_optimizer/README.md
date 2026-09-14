# Eval Optimizer Pattern

## Overview

Evaluate agent outputs and iteratively improve through optimization loops.

## Use Case

When quality improvement requires feedback and iteration:
- Code generation with evaluation and refinement
- Prompt optimization based on output quality
- Multi-round reasoning with scoring

## Components

- `example.py` - Working example showing evaluation and optimization
- `tests/` - Unit and integration tests

## Key Concepts

- Evaluation criteria definition
- Score-based optimization
- Feedback integration
- Iteration control

## Example

```python
# See example.py for full implementation
optimizer = EvalOptimizer(
    evaluator=quality_evaluator,
    max_iterations=3
)
final_output = optimizer.optimize(initial_output)
```
