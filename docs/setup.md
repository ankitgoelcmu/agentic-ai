# Setup Guide: Ollama and Environment Configuration

Complete guide for setting up Ollama and configuring your environment to run agentic-ai patterns.

## Table of Contents

1. Ollama Installation
2. Model Setup
3. Environment Configuration
4. Verification
5. Troubleshooting

## 1. Ollama Installation

### macOS

```bash
# Using Homebrew
brew install ollama

# Or download from https://ollama.ai/download

# Start Ollama service
ollama serve
```

The service will run on `http://localhost:11434` by default.

### Linux

```bash
# Ubuntu/Debian
curl https://ollama.ai/install.sh | sh

# Start service
ollama serve
```

### Windows

Download installer from https://ollama.ai/download and follow installation wizard.

Start from command line:
```cmd
ollama serve
```

## 2. Model Setup

### Pull Required Model

```bash
# In a new terminal (while ollama serve is running)
ollama pull qwen3-coder-next:latest
```

This downloads the model (approximately 50GB for qwen3-coder-next).

### Verify Model is Installed

```bash
ollama list
```

Should show output like:
```
NAME                    ID              SIZE    MODIFIED
qwen3-coder-next:latest abc123def456    51GB    2 hours ago
```

### Test Model Works

```bash
# Quick test
ollama run qwen3-coder-next "What is 2+2?"
```

Should respond with "4".

### Alternative Models

If you need a smaller model or want alternatives:

```bash
# Smaller models
ollama pull mistral:latest              # 4.1GB
ollama pull neural-chat:latest          # 4.1GB
ollama pull llama2:latest               # 3.8GB

# Larger models
ollama pull llama2:70b                  # 39GB
ollama pull mistral:large               # 26GB
```

Note: Update `.env` with the model name if you switch models.

## 3. Environment Configuration

### Create .env File

```bash
cd /path/to/agentic-ai
cp .env.example .env
```

### Required Variables

```bash
# Ollama Configuration
OLLAMA_MODEL=qwen3-coder-next:latest
OLLAMA_BASE_URL=http://localhost:11434
```

### Optional Variables

```bash
# Web Search (for sigma_rule_writer example)
TAVILY_API_KEY=your_tavily_api_key

# Observability and Tracing
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=agentic-ai

# Debugging
DEBUG=true
```

### Get API Keys

**Tavily Search** (optional):
1. Go to https://tavily.com
2. Sign up for free account
3. Copy API key to .env

**LangSmith** (optional):
1. Go to https://smith.langchain.com
2. Sign up for free account
3. Create new project
4. Copy API key and project name to .env

## 4. Verification

### Step 1: Check Ollama Service

```bash
# Should return 200 OK
curl http://localhost:11434/api/tags
```

Expected response:
```json
{
  "models": [
    {
      "name": "qwen3-coder-next:latest",
      "modified_at": "2024-09-14T10:30:00Z",
      ...
    }
  ]
}
```

### Step 2: Test Python Integration

```bash
python3 << 'EOF'
from langchain_ollama import ChatOllama
from langchain.messages import HumanMessage, SystemMessage

llm = ChatOllama(model="qwen3-coder-next:latest", temperature=0)
response = llm.invoke([
    SystemMessage(content="You are a helpful assistant."),
    HumanMessage(content="What is 2+2?")
])
print(response.content)
EOF
```

Should print: "4" or similar.

### Step 3: Run a Pattern

```bash
cd /Users/ankitgoel/agentic-ai
python3 patterns/parallel/security_checks.py
```

If this completes without errors, you are all set.

## 5. Troubleshooting

### Error: Connection refused (localhost:11434)

Cause: Ollama service not running

Solution:
```bash
# In a new terminal window
ollama serve
```

Keep this window open while running patterns.

### Error: model 'qwen3-coder-next' not found

Cause: Model not downloaded

Solution:
```bash
ollama pull qwen3-coder-next:latest
```

Wait for download to complete (can take 10-20 minutes depending on internet speed).

### Error: Out of memory

Cause: Model requires more RAM than available

Solutions:
1. Close other applications to free up memory
2. Use a smaller model (see "Alternative Models" section)
3. Increase system swap space
4. Run on a machine with more RAM

To check memory usage:
```bash
# macOS
top

# Linux
free -h

# Windows
wmic OS get TotalVisibleMemorySize, FreePhysicalMemory
```

### Error: Model generating very slowly

Cause: Using CPU instead of GPU, or system is under load

Solution:
1. Close other applications
2. If you have GPU support available, configure Ollama to use it:

For NVIDIA GPU (macOS with Apple Silicon, Linux with CUDA):
```bash
# Ollama automatically detects and uses GPU if available
# No additional configuration needed

# Verify GPU is being used by checking logs
```

For Apple Silicon Mac:
- Ollama automatically uses Metal acceleration
- Performance should be good

### Error: .env file not found

Cause: .env file was not created

Solution:
```bash
cp .env.example .env
```

Then edit and add your API keys.

### Patterns running but producing low-quality output

Possible causes and solutions:

1. Model not fully downloaded:
   ```bash
   ollama list
   ```
   Check the size matches expected size

2. Model cached incorrectly:
   ```bash
   ollama rm qwen3-coder-next:latest
   ollama pull qwen3-coder-next:latest
   ```

3. Temperature setting needs adjustment (edit pattern file):
   - Lower temperature (0.0-0.3): More deterministic, less creative
   - Higher temperature (0.7-1.0): More creative, less consistent

## Performance Tuning

### Increase Response Speed

1. Use a smaller model (mistral, neural-chat)
2. Run on a machine with GPU support
3. Increase Ollama context window if needed

### Reduce Memory Usage

1. Use quantized models (they end with "-q4_0", "-q5_0")
2. Reduce batch size
3. Close other applications

### Multi-GPU Setup

If you have multiple GPUs:
```bash
# Ollama v0.1.26+ automatically distributes across GPUs
# No configuration needed
```

## Advanced: Custom Ollama Configuration

### Run on Different Port

```bash
# Instead of default 11434
ollama serve --port 8080

# Update .env
OLLAMA_BASE_URL=http://localhost:8080
```

### Run Ollama in Docker

```bash
docker run -d -v ollama:/root/.ollama -p 11434:11434 ollama/ollama

# Pull model
docker exec <container_id> ollama pull qwen3-coder-next:latest
```

### Enable Ollama Logging

```bash
# macOS / Linux
OLLAMA_DEBUG=1 ollama serve

# Windows
set OLLAMA_DEBUG=1
ollama serve
```

## Next Steps

1. Run QUICKSTART.md to test your setup
2. Check individual pattern READMEs
3. Explore examples/sigma_rule_writer for complete use case
4. See docs/contributing.md to add your own patterns
