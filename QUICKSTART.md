# Quick Start Guide

Get up and running with agentic-ai patterns in 5 minutes.

## Prerequisites

- Python 3.12+
- Ollama running locally (see docs/setup.md)
- Git

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/ankitgoelcmu/agentic-ai.git
cd agentic-ai
```

### 2. Create Virtual Environment

```bash
# Using uv (recommended)
uv venv
source .venv/bin/activate

# Or using standard Python
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
# Using uv
uv sync

# Or using pip
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set:
```
OLLAMA_MODEL=qwen3-coder-next
TAVILY_API_KEY=your_key_here  # Optional
LANGSMITH_API_KEY=your_key_here  # Optional
```

### 5. Verify Ollama is Running

```bash
curl http://localhost:11434/api/tags
```

Should return a list of available models including `qwen3-coder-next:latest`.

## Run Your First Pattern

### Parallel Pattern (Security Checks)

```bash
cd /Users/ankitgoel/agentic-ai
python3 patterns/parallel/security_checks.py
```

Expected output: Security assessment with prompt injection, PII, and malware detection results.

### Routing Pattern (Department Router)

```bash
python3 patterns/routing/department_router.py
```

Expected output: Query classified and routed to HR, Finance, or Tech Support.

### Eval Optimizer Pattern (Stock Analysis)

```bash
python3 patterns/eval_optimizer/stock_analysis_optimizer.py
```

Expected output: Comprehensive stock analysis with iterative improvement feedback.

### Prompt Chaining Pattern (Design to Code)

```bash
python3 patterns/prompt_chaining/design_to_code.py
```

Expected output: High-Level Design (HLD), Low-Level Design (LLD), and generated code.

## Troubleshooting

### Ollama Connection Error

```
ValueError: Connection error connecting to Ollama at http://localhost:11434
```

Solution: Make sure Ollama is running:
```bash
ollama serve
```

### Model Not Found

```
ResponseError: model 'qwen3-coder-next' not found
```

Solution: Pull the model:
```bash
ollama pull qwen3-coder-next:latest
```

### Memory Issues

If Ollama crashes with out-of-memory errors, either:
1. Reduce batch size by modifying the pattern
2. Use a smaller model
3. Increase system RAM

See docs/setup.md for more details.

## What's Next?

- Read individual pattern READMEs in `patterns/*/README.md`
- Check `docs/setup.md` for advanced Ollama configuration
- See `docs/contributing.md` to add your own patterns
- Explore `examples/sigma_rule_writer/` for a complete real-world example

## Common Commands

```bash
# List all patterns
ls patterns/*/

# View pattern details
cat patterns/parallel/README.md

# Run with Python verbose output
python3 -u patterns/routing/department_router.py

# Test all patterns
for pattern in patterns/*/example.py; do
    echo "Testing $pattern..."
    python3 "$pattern"
done
```

## Getting Help

1. Check the pattern's README: `patterns/PATTERN_NAME/README.md`
2. Review docs/setup.md for environment issues
3. Check Anthropic's blog: https://www.anthropic.com/engineering/building-effective-agents
4. Open a GitHub issue in the repository
