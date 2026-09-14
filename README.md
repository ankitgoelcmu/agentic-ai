# Agentic AI Patterns & Examples

A comprehensive repository of agentic AI patterns and real-world examples using LangChain, DeepAgents, and other frameworks.

All patterns are based on [Anthropic's "Building Effective Agents"](https://www.anthropic.com/engineering/building-effective-agents) blog post.

## Structure

### `patterns/` - Core Agentic Patterns

Reusable, abstract patterns for building multi-agent systems:

- **`parallel/`** - Parallel agent execution: Run multiple agents concurrently and aggregate results
- **`routing/`** - Agent routing/dispatch: Route requests to specialized agents based on input
- **`prompt_chaining/`** - Prompt chaining: Break complex tasks into sequential steps where each step's output feeds the next
- **`eval_optimizer/`** - Evaluation & optimization: Evaluate agent outputs and iteratively improve
- **`worker_orchestrator/`** - Distributed workers: Coordinate work across multiple worker agents

Each pattern includes:
- Clear example implementation
- Test suite
- Documentation explaining the use case

### `examples/` - Real-World Use Cases

Complete, production-ready examples:

- **`sigma_rule_writer/`** - Detection rule generation agent for threat detection
- More examples coming...

### `shared/` - Reusable Utilities

Common functionality shared across patterns and examples:

- LLM initialization helpers
- Middleware base classes
- Logging and observability setup
- Tool utilities

## Quick Start

### Installation

```bash
uv venv
source .venv/bin/activate
uv sync
```

### Environment Setup

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

### Running Examples

```bash
# Run a specific pattern
python -m patterns.parallel.example

# Run an example
python -m examples.sigma_rule_writer.detection_rules_writer
```

## Requirements

- Python 3.12+
- LangChain & LangChain-Community
- DeepAgents
- Additional dependencies per pattern/example

See `pyproject.toml` for full dependency list.

## Documentation

- `QUICKSTART.md` - Get running in 5 minutes
- `docs/setup.md` - Ollama installation and configuration
- `docs/contributing.md` - Contribution guidelines
- `docs/learning-resources.md` - Learning path and references
- `docs/patterns-guide.md` - Detailed explanation of each pattern
- `docs/architecture.md` - System architecture and design decisions

## References & Inspiration

This repository's patterns and structure are based on:

1. **Anthropic: Building Effective Agents**
   - Blog: https://www.anthropic.com/engineering/building-effective-agents
   - Covers core patterns: parallel, routing, prompt chaining, eval optimizer

2. **Agentic AI Design Patterns (YouTube)**
   - Video: https://www.youtube.com/watch?v=aHCDrAbH_go
   - Covers system architecture and workflow design principles

These resources provide the foundation for understanding and implementing effective agentic systems.

For a comprehensive learning path, see `docs/learning-resources.md`.

## License

MIT
