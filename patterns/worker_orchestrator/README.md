# Stock Analysis Orchestrator-Workers Agent

A production-grade example of the **Worker-Orchestrator Pattern** using LangGraph, specialized for real-time stock analysis and research report generation.

## Architecture Overview

This system implements a **fan-out / fan-in orchestration model**:

```
                         INPUT TICKER
                              ↓
                      ┌──────────────────┐
                      │  ORCHESTRATOR    │
                      │                  │
                      │ Decompose task   │
                      │ into work orders │
                      └────────┬─────────┘
                               ↓
              ┌────────────────────────────────────┐
              │        DISPATCH (Send × N)         │
              │    Routes to parallel workers     │
              └─┬──┬──┬──┬──┬──────────────────────┘
                │  │  │  │  │
        ┌───────┴──┴──┴──┴──┴────────────────┐
        ↓         ↓         ↓         ↓       ↓
    ┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐
    │Worker 1││Worker 2││Worker 3││Worker 4││Worker 5│
    │(Comp)  ││(Fin)   ││(News)  ││(Bull)  ││(Bear)  │
    └───┬────┘└───┬────┘└───┬────┘└───┬────┘└───┬────┘
        │ Tool 1  │ Tool 2  │ Tool 3  │ Tool 4  │ Tool 5
        │ (search)│(search) │(search) │(search) │(search)
        ├─LLM1────┤─LLM2────┤─LLM3────┤─LLM4────┤─LLM5──┐
        │interpret │interpret │interpret │interpret │interpret │
        └────┬─────┴─────┬────┴────┬─────┴─────┬────┴─────┬──
        Result1        Result2        Result3       Result4   Result5
             └─────────────────────┬──────────────────────┘
                                   ↓
                         ┌──────────────────┐
                         │  FAN-IN MERGE    │
                         │(operator.add)    │
                         │ All 5 results    │
                         └────────┬─────────┘
                                  ↓
                         ┌──────────────────┐
                         │  SYNTHESIZER     │
                         │                  │
                         │ Aggregate finds  │
                         │ Write executive  │
                         │ summary + blog   │
                         └────────┬─────────┘
                                  ↓
                         ┌──────────────────┐
                         │  OUTPUT          │
                         │ • Executive Summ │
                         │ • Investor Blog  │
                         └──────────────────┘
```

## Key Components

### 1. Orchestrator Node

**Input**: Stock ticker + optional user query  
**Output**: List of `WorkOrder` objects describing independent analysis tasks

The orchestrator LLM reads a decomposition prompt that instructs it to break down the analysis request into parallel, independent work units. It never calls tools itself—it only decides WHAT work needs to be done.

**Smart Features**:
- Respects user query specificity (if user asks only for bearish outlook, only creates bear case + supporting analysis)
- If user query is empty, creates all 5 generic tasks
- Can handle multiple tickers in one query

**Example Output**:
```json
[
  {"worker_type": "competetive_analysis", "task": "...", "ticker": "NVDA"},
  {"worker_type": "financial_analysis", "task": "...", "ticker": "NVDA"},
  {"worker_type": "news_sentiment_analysis", "task": "...", "ticker": "NVDA"},
  {"worker_type": "bull_case_analysis", "task": "...", "ticker": "NVDA"},
  {"worker_type": "bear_case_analysis", "task": "...", "ticker": "NVDA"}
]
```

### 2. Dispatch Layer

**Type**: Conditional edge function (not a node)  
**Role**: Convert work orders into parallel LangGraph Send objects

```python
# Pseudo-code
for work_order in work_orders:
    return Send("worker", {
        "ticker": ticker,
        "work_order": work_order,
        "worker_results": []  # starts empty
    })
```

This is where LangGraph's parallelism kicks in. Each Send spawns an independent execution of `worker_node` with its own isolated WorkerState. All workers run concurrently.

### 3. Worker Nodes (5 instances in parallel)

**Input**: Single `WorkOrder` + isolated state  
**Output**: `WorkerResult` containing specialist findings

Each worker executes the same three-step pattern:

#### Step 1: Tool Invocation
- **What it does**: Calls its assigned tool (e.g., `competetive_analysis`)
- **Tool layer**: Queries Tavily API with a curated search prompt
- **Output**: Raw JSON with search results (titles, URLs, snippets)
- **Why**: Data fetching is deterministic; no LLM involved yet

#### Step 2: Specialist LLM Interpretation
- **What it does**: Specialist LLM (e.g., "Competitive Intelligence Analyst") reads the raw tool output and synthesizes it
- **Context**: Role-focused system prompt + task description + raw JSON
- **Isolation**: Each worker only sees its own data; no cross-contamination
- **Output**: Concise 3-4 sentence findings summary
- **Why**: Each analyst role interprets the same raw data differently

#### Step 3: State Update
- **What it does**: Appends `WorkerResult` into shared state
- **Mechanism**: `operator.add` ensures parallel workers append, not overwrite
- **Result**: By the time all workers finish, state has all 5 results merged

### 4. Fan-In Merge

**Mechanism**: LangGraph's `operator.add` annotation

When used on a List field, `operator.add` acts as a reducer:
```python
worker_results: Annotated[List[WorkerResult], operator.add]
```

Instead of the last worker overwriting others' results, each worker appends its result. By the time synthesizer runs, all 5 findings are available in order.

### 5. Synthesizer Node

**Input**: All 5 worker findings (merged)  
**Output**: Executive summary + investor blog post

The synthesizer LLM:
1. Reads ALL specialist findings (labeled by analyst type)
2. Performs cross-analyst reasoning (balancing bull vs bear, weaving narratives)
3. Writes two investor-facing documents:
   - **Executive Summary**: 2-3 paragraphs for a portfolio manager (60-second read)
   - **Blog Post**: 5-7 paragraphs for public investors (detailed, balanced, disclaimers)

**Output Format**:
```json
{
  "executive_summary": "...",
  "blog_post": "..."
}
```

---

## Tools Overview

All tools are decorated with `@tool` and return JSON strings. They integrate with **Tavily Search API** for real-time data.

### 1. **Competitive Analysis** `competetive_analysis(ticker)`

**Search Query**: `"{ticker} stock competitive analysis market share vs competitors 2025"`

**Returns**:
```json
{
  "ticker": "NVDA",
  "results": [
    {
      "title": "NVIDIA vs AMD: Competitive Landscape 2025",
      "url": "https://...",
      "content": "NVIDIA maintains 80% market share in AI chips..."
    },
    ...
  ]
}
```

**Worker Interpretation**: Competitive Intelligence Analyst extracts competitive position, key rivals, strategic advantages.

---

### 2. **Financial Analysis** `financial_analysis(ticker)`

**Search Query**: `"{ticker} financial results revenue earnings profit margin PE ratio 2025"`

**Returns**:
```json
{
  "ticker": "NVDA",
  "results": [
    {
      "title": "NVIDIA Q3 2025 Earnings: Record Revenue",
      "url": "https://...",
      "content": "Revenue: $40B (+50% YoY), Net Margin: 58%, P/E: 45x..."
    },
    ...
  ]
}
```

**Worker Interpretation**: Financial Analyst extracts revenue trends, profitability metrics, valuation vs peers.

---

### 3. **News & Sentiment Analysis** `news_sentiment_analysis(ticker)`

**Search Query**: `"{ticker} stock news analyst sentiment outlook 2025"` (with `topic="news"`)

**Returns**:
```json
{
  "ticker": "NVDA",
  "results": [
    {
      "title": "Goldman Sachs Upgrades NVIDIA on AI Tailwinds",
      "url": "https://...",
      "content": "GS analysts expect NVIDIA to reach $2T valuation by 2027..."
    },
    ...
  ]
}
```

**Worker Interpretation**: Market Sentiment Analyst summarizes overall sentiment, key themes, recent events.

---

### 4. **Bull Case Analysis** `bull_case_analysis(ticker)`

**Search Query**: `"{ticker} stock bull case growth catalysts investment thesis upside 2025"`

**Returns**:
```json
{
  "ticker": "NVDA",
  "results": [
    {
      "title": "Why NVIDIA Stock Could Double: Bull Case Analysis",
      "url": "https://...",
      "content": "AI proliferation, data center dominance, software monetization..."
    },
    ...
  ]
}
```

**Worker Interpretation**: Bullish Equity Analyst makes the bull case: growth catalysts, competitive moat, positive macro tailwinds.

---

### 5. **Bear Case Analysis** `bear_case_analysis(ticker)`

**Search Query**: `"{ticker} stock bear case risks challenges headwinds downside 2025"`

**Returns**:
```json
{
  "ticker": "NVDA",
  "results": [
    {
      "title": "NVIDIA Valuation at Risk: Bear Case for 2025",
      "url": "https://...",
      "content": "Saturation risks, regulatory concerns, margin compression..."
    },
    ...
  ]
}
```

**Worker Interpretation**: Bearish Equity Analyst makes the bear case: key risks, competitive threats, negative macro headwinds.

---

## State Management

### OrchestratorState (Shared)

The top-level state that persists for the entire graph run:

```python
class OrchestratorState(TypedDict):
    ticker: str                                      # input: stock symbol
    user_query: str                                  # input: optional specific query
    work_orders: List[WorkOrder]                     # orchestrator → dispatch
    worker_results: Annotated[List[WorkerResult],    # workers append (fan-in)
                              operator.add]
    executive_summary: str                           # synthesizer output
    blog_post: str                                   # synthesizer output
```

**Key**: `worker_results` uses `operator.add` so each parallel worker appends instead of overwriting.

### WorkerState (Isolated)

Each parallel worker instance gets its own isolated state:

```python
class WorkerState(TypedDict):
    ticker: str                                      # context for the worker
    work_order: WorkOrder                            # ONE task assigned to this worker
    worker_results: Annotated[List[WorkerResult],    # worker appends its result here
                              operator.add]
```

**Why separate?** LangGraph's Send() creates independent branches with their own state. This state is merged back into OrchestratorState when the branch finishes via the `operator.add` reducer.

---

## Execution Flow

### Example: Analyzing NVIDIA with a Bull-Only Query

**Input**:
```python
ticker = "NVDA"
user_query = "What is the outlook for NVDA? Only provide bullish insights."
```

### Step 1: Orchestrator Decides Work

Orchestrator LLM reads:
- Ticker: NVDA
- User Query: Bull-only outlook
- Available workers: 5 types

Orchestrator decides:
```json
[
  {"worker_type": "competetive_analysis", "task": "Analyze NVDA's competitive advantages", "ticker": "NVDA"},
  {"worker_type": "financial_analysis", "task": "Analyze NVDA's revenue growth and profitability", "ticker": "NVDA"},
  {"worker_type": "news_sentiment_analysis", "task": "Find positive sentiment and growth catalysts", "ticker": "NVDA"},
  {"worker_type": "bull_case_analysis", "task": "Make the bullish case for NVDA", "ticker": "NVDA"}
]
```

(Notice: no bear case, since user only asked for bullish insights)

### Step 2: Dispatch to Workers

LangGraph spawns 4 parallel Send() branches (one per work order).

Each worker runs its three-step process **concurrently**:
- Worker 1 (Competitive) searches, LLM interprets → Result 1
- Worker 2 (Financial) searches, LLM interprets → Result 2
- Worker 3 (News) searches, LLM interprets → Result 3
- Worker 4 (Bull) searches, LLM interprets → Result 4

### Step 3: Fan-In Merge

LangGraph waits for all 4 workers to finish, then merges results via `operator.add`:

```python
worker_results = [
  {"worker_type": "competetive_analysis", "findings": "..."},
  {"worker_type": "financial_analysis", "findings": "..."},
  {"worker_type": "news_sentiment_analysis", "findings": "..."},
  {"worker_type": "bull_case_analysis", "findings": "..."}
]
```

### Step 4: Synthesizer Aggregates

Synthesizer LLM reads:
- Ticker: NVDA
- All 4 findings (pre-labeled by analyst type)
- Task: Write executive summary + blog post with bullish bias

Output:
```json
{
  "executive_summary": "NVIDIA is well-positioned for continued growth... competitive moat ... upside potential ...",
  "blog_post": "NVIDIA: An AI Powerhouse Entering a New Era of Growth\n\n..."
}
```

---

## Pattern Benefits

### 1. Parallelism
- All 5 workers run concurrently (or fewer if user filters tasks)
- Total time = longest worker + overhead, NOT sum of all workers
- Example: 5 parallel 10-second searches + 2 second LLM per worker ≈ 12 seconds total (vs 60+ seconds serial)

### 2. Specialization
- Each worker has a focused role ("Competitive Analyst," "Financial Analyst," etc.)
- Same raw data interpreted differently by different specialists
- Specialist LLM can give concise, relevant output (3-4 sentences vs verbose)

### 3. Separation of Concerns
- Orchestrator decides WHAT (no tools)
- Workers execute HOW (tools + interpretation)
- Synthesizer reasons cross-functionally
- Clean boundaries = easier to debug, modify, extend

### 4. Flexibility
- User query can guide task decomposition
- Can add new workers without changing orchestrator or synthesizer
- Handles multiple tickers in one request
- Can adapt to partial failures (if one worker fails, others still complete)

### 5. Scalability
- Same pattern works for 5 workers or 500 workers
- LangGraph handles fan-out/fan-in automatically
- Each worker is stateless (can be distributed)

---

## How to Run

### Prerequisites

```bash
pip install langchain langchain-ollama langgraph tavily-python python-dotenv
```

### Environment Setup

Create `.env` file:

```bash
TAVILY_API_KEY=your_tavily_api_key
# Optional: If using remote LLM
ANTHROPIC_API_KEY=your_anthropic_key
```

### Run the Analysis

```bash
python stocks.py
```

**Output**:
```
STOCK ANALYST ORCHESTRATOR-WORKERS AGENT
=======================================================
Analyzing: NVDA
User Query: What is the outlook for NVDA? Only provide bullish insights.

[ORCHESTRATOR] NVDA — 4 parallel work orders:
  1. [COMPETETIVE_ANALYSIS] Analyze competitive position...
  2. [FINANCIAL_ANALYSIS] Analyze financial metrics...
  3. [NEWS_SENTIMENT_ANALYSIS] Find positive sentiment...
  4. [BULL_CASE_ANALYSIS] Make the bullish case...

[WORKER: competetive_analysis] Running tool for NVDA...
[WORKER: competetive_analysis] Tool complete. Interpreting with LLM...
[WORKER: competetive_analysis] → NVIDIA maintains strong competitive...

[WORKER: financial_analysis] Running tool for NVDA...
...

[SYNTHESIZER] Writing complete for NVDA

=======================================================
EXECUTIVE SUMMARY:
NVIDIA is a dominant force in AI infrastructure...

=======================================================
INVESTOR BLOG POST:
NVIDIA: An AI Powerhouse Entering a New Era of Growth

...
```

---

## Customization

### Change the LLM Model

In `stocks.py`, modify `get_llm()`:

```python
def get_llm():
    return ChatOllama(model="llama2", temperature=0)  # or any other model
```

### Add New Analysis Types

1. Create a new `@tool` function in `tools.py`:
```python
@tool
def sentiment_analysis(ticker: str) -> str:
    # Implementation
    pass
```

2. Add it to `TOOL_MAP` in `stocks.py`:
```python
TOOL_MAP = {
    ...
    "sentiment_analysis": sentiment_analysis,
}
```

3. Add a specialist prompt in `WORKER_PROMPTS`:
```python
WORKER_PROMPTS = {
    ...
    "sentiment_analysis": "You are a Sentiment Analyst...",
}
```

4. Orchestrator will automatically recognize it as a valid worker type.

### Filter Analysis by User Query

The system already supports this. Examples:

```python
user_query = "Only competitive analysis"
# → Creates only competitive_analysis work order

user_query = "Bull and bear case only"
# → Creates only bull_case_analysis and bear_case_analysis

user_query = ""  # empty
# → Creates all 5 work orders (default behavior)
```

---

## Diagram: Parallel Execution Timeline

```
Time        Orchestrator    Worker1    Worker2    Worker3    Worker4    Worker5    Synthesizer
│           (decompose)     (Comp)     (Fin)      (News)     (Bull)     (Bear)     (aggregate)
│
├── T=0s    ┌──────────────┐
│           │ Parse query  │
│           │ Create 5     │
│           │ work orders  │
│           └──────┬───────┘
│                  │
├── T=1s          │      ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│                 ├─────→│ Search   │ │ Search   │ │ Search   │ │ Search   │ │ Search   │
│                 │      │ API      │ │ API      │ │ API      │ │ API      │ │ API      │
│                 │      └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
│                 │           │            │            │            │            │
├── T=10s        │           ├────────────┤────────────┤────────────┤────────────┤
│                │           │ LLM        │ LLM        │ LLM        │ LLM        │ LLM
│                │           │ interpret  │ interpret  │ interpret  │ interpret  │ interpret
│                │           │            │            │            │            │
├── T=12s        │           └────────────┴────────────┴────────────┴────────────┘
│                │                                            ↓
│                │                                    ┌──────────────┐
│                │                                    │ Merge all    │
│                │                                    │ results via  │
│                │                                    │ operator.add │
│                │                                    └──────┬───────┘
│                │                                           ↓
├── T=13s        │                                    ┌──────────────┐
│                │                                    │ LLM reads    │
│                │                                    │ all findings │
│                │                                    │ write output │
│                │                                    └──────┬───────┘
│                │                                           ↓
├── T=15s        └───────────────────────────────────────────────→ END
│
```

**Key insight**: Workers 1-5 run concurrently (10s each). Total: ~15s vs 50s+ if serial.

---

## Comparison: Orchestrator-Worker vs Alternatives

| Aspect | Orchestrator-Worker | Sequential | Single Agent |
|--------|---------------------|-----------|--------------|
| **Parallelism** | ✅ Concurrent | ❌ Serial | ❌ N/A |
| **Specialization** | ✅ Role-based | ❌ Generic | ❌ Generic |
| **Speed** | ✅ Fast (1 longest worker) | ❌ Slow (all workers) | ⚠️ Slow (no tool calls) |
| **Scalability** | ✅ Add workers easily | ❌ Harder | ❌ Harder |
| **Debugging** | ✅ Clear boundaries | ✅ Simpler | ❌ Black box |
| **Cost** | ✅ Efficient | ❌ Redundant | ⚠️ Depends |

---

## Further Reading

- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **Fan-Out/Fan-In Pattern**: https://www.anthropic.com/research/research-agent (Anthropic's agents guide)
- **Tavily API**: https://tavily.com/

---

## Author

Created as an example of production-grade agentic orchestration patterns with LangGraph.
