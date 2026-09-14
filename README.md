# Agentic AI Patterns & Examples

A comprehensive repository of agentic AI patterns and real-world examples using LangChain, DeepAgents, and other frameworks.

## Structure

### `patterns/` - Core Agentic Patterns

Reusable, abstract patterns for building multi-agent systems:

- **`parallel/`** - Parallel agent execution: Run multiple agents concurrently and aggregate results
- **`routing/`** - Agent routing/dispatch: Route requests to specialized agents based on input
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

- `docs/patterns-guide.md` - Detailed explanation of each pattern
- `docs/architecture.md` - System architecture and design decisions
- `docs/contributing.md` - Contribution guidelines

## License

MIT
