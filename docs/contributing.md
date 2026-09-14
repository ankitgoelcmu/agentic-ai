# Contributing Guide

Add your own agentic AI patterns and examples to this repository.

## Before You Start

1. **Watch & Read Learning Resources** (required)
   - YouTube: Agentic AI Design Patterns: https://www.youtube.com/watch?v=aHCDrAbH_go
   - Blog: Anthropic's "Building Effective Agents": https://www.anthropic.com/engineering/building-effective-agents
   - See `docs/learning-resources.md` for complete learning path

2. **Understand which pattern category your idea fits into:**
   - **Pattern**: Reusable, abstract pattern (parallel, routing, prompt_chaining, eval_optimizer, worker_orchestrator)
   - **Example**: Real-world use case (sigma_rule_writer, etc.)

## Adding a New Pattern

### 1. Create Pattern Directory

```bash
cd patterns/
mkdir your_pattern_name
cd your_pattern_name

# Create files
touch __init__.py README.md your_pattern_name.py
```

### 2. Write the Implementation

File: `patterns/your_pattern_name/your_pattern_name.py`

Requirements:
- Use LangGraph for workflow orchestration
- Use ChatOllama (or other LLM) via LangChain
- Include clear comments explaining the pattern
- Use deterministic temperature (0.0) for reproducibility
- Handle errors gracefully

```python
# Example structure
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

class State(TypedDict):
    input: str
    output: str

def my_node(state: State):
    llm = ChatOllama(model="qwen3-coder-next:latest", temperature=0)
    # Your implementation
    return {"output": result}

# Build graph
builder = StateGraph(State)
builder.add_node("my_node", my_node)
builder.add_edge(START, "my_node")
builder.add_edge("my_node", END)

workflow = builder.compile()

# Test execution
if __name__ == "__main__":
    result = workflow.invoke({"input": "test"})
    print(result)
```

### 3. Write the README

File: `patterns/your_pattern_name/README.md`

Include sections:
1. Overview: What is this pattern?
2. Implementation: How does it work?
3. How It Works: Visual workflow (ASCII diagram)
4. Use Cases: When to use this pattern
5. Key Learnings: Important insights
6. Reference: Link to Anthropic's blog

Example template:
```markdown
# Your Pattern Name

## Overview
Brief description of the pattern.

## Implementation
See `your_pattern_name.py` for complete implementation.

Explanation of key components...

## How It Works

[ASCII diagram of workflow]

## Use Cases

- Use case 1
- Use case 2

## Key Learnings

- Learning 1
- Learning 2

## Reference

This pattern is based on [Anthropic's "Building Effective Agents"](https://www.anthropic.com/engineering/building-effective-agents) blog post.
```

### 4. Test Your Pattern

```bash
# Test syntax
python3 -m py_compile your_pattern_name.py

# Test execution (requires Ollama running)
python3 your_pattern_name.py

# Should complete without errors and produce expected output
```

### 5. Update Main README

Edit: `README.md`

Add your pattern to the patterns list:
```markdown
- **`your_pattern_name/`** - Description of what it does
```

### 6. Commit and Push

```bash
cd /Users/ankitgoel/agentic-ai
git add patterns/your_pattern_name/
git add README.md
git commit -m "Add your_pattern_name pattern

- Implement your_pattern_name with [describe approach]
- Add README with use cases and learnings
- Pattern demonstrates [key concept] from Anthropic's blog"
git push origin main
```

## Adding a New Example

### 1. Create Example Directory

```bash
cd examples/
mkdir your_example_name
cd your_example_name

touch __init__.py README.md main.py tools.py
```

### 2. Structure

Examples should include:

- `main.py`: Main agent/workflow implementation
- `tools.py`: Tool definitions and implementations
- `README.md`: Documentation explaining the use case
- `middleware.py` (optional): Custom middleware if needed
- Other supporting files as needed

### 3. Write README

Include:
1. Overview: What problem does this solve?
2. Architecture: Components and how they interact
3. Workflow: Step-by-step process
4. Setup: Required environment variables
5. Running: How to execute the example
6. Expected Output: What should the result look like

### 4. Test Your Example

```bash
# Verify imports work
python3 -c "from examples.your_example import main"

# Run the example
python3 examples/your_example/main.py
```

### 5. Update Examples README

If you created `examples/README.md`, document your example:
```markdown
## Your Example Name

Description of what it does, what problem it solves, and how to run it.

See `your_example_name/README.md` for details.
```

### 6. Commit and Push

```bash
git add examples/your_example_name/
git commit -m "Add your_example_name example

- Implements [what it does]
- Demonstrates [key patterns or techniques]
- Includes [tools/features]"
git push origin main
```

## Shared Code Guidelines

### Adding Utilities to `shared/`

If your pattern or example needs reusable utilities:

```python
# shared/your_utility.py

def reusable_function(arg1, arg2):
    """Clear docstring explaining what this does."""
    return result

# Then import in your pattern
from shared.your_utility import reusable_function
```

Update `shared/tools.py` if adding to existing utilities.

## Naming Conventions

- **Pattern files**: Descriptive name: `security_checks.py`, `department_router.py` (not `example.py`)
- **Directories**: Snake case: `prompt_chaining`, `eval_optimizer`
- **Functions**: Snake case: `generate_response`, `check_validity`
- **Classes**: Pascal case: `State`, `Router`, `SecurityValidator`

## Code Style

- Use type hints: `def my_function(x: str) -> dict:`
- Keep functions focused and single-responsibility
- Avoid comments that restate what code does
- Add comments only for "why" not "what"
- Maximum line length: 88 characters (Black style)

## Documentation Style

- Use clear, concise language
- No em dashes (use regular hyphens: - or colons :)
- Include code examples
- Link to Anthropic's blog when relevant
- ASCII diagrams for workflow visualization

## Pull Request Checklist

Before submitting:

- [ ] Files compile without syntax errors
- [ ] Pattern/example runs successfully with Ollama
- [ ] README is complete and clear
- [ ] Code follows naming conventions
- [ ] Anthropic blog referenced
- [ ] No em dashes used in documentation
- [ ] Commit message is descriptive
- [ ] Changes tested locally

## Questions?

If you're unsure about anything:

1. Check existing patterns for examples
2. Review Anthropic's blog post
3. Read the QUICKSTART and setup docs
4. Open an issue in the repository

## Recognition

Contributors will be recognized in the repository. When your pattern or example is merged, your GitHub username will be added to the authors list.

## License

By contributing, you agree that your code will be licensed under the same license as the repository (MIT).
