# Stock Analysis Tools Reference

This document details all tools used in the stock analysis orchestrator-workers agent.

## Tool Architecture

All tools are decorated with `@tool` from LangChain and are invoked with the signature:

```python
tool.invoke({"ticker": ticker})  # Returns JSON string
```

Tools are **deterministic data fetchers** — they don't call LLMs. They query real data sources (Tavily Search API) and return raw results as JSON.

---

## Tools Summary

| Tool Name | Input | Output Type | Use Case | Worker |
|-----------|-------|------------|----------|--------|
| `competetive_analysis` | `ticker` (str) | JSON search results | Competitive positioning | Competitive Intel Analyst |
| `financial_analysis` | `ticker` (str) | JSON search results | Financial metrics & trends | Financial Analyst |
| `news_sentiment_analysis` | `ticker` (str) | JSON search results | Market sentiment & news | Market Sentiment Analyst |
| `bull_case_analysis` | `ticker` (str) | JSON search results | Bullish arguments | Bullish Equity Analyst |
| `bear_case_analysis` | `ticker` (str) | JSON search results | Bearish arguments | Bearish Equity Analyst |

---

## Detailed Tool Specifications

### 1. `competetive_analysis(ticker: str) -> str`

**Purpose**: Fetch competitive intelligence data for a stock ticker.

**Tavily Search Query**:
```
"{ticker} stock competitive analysis market share vs competitors 2025"
```

**Search Depth**: Advanced (deeper searches, more results)  
**Max Results**: 5

**Return Format**:
```json
{
  "ticker": "NVDA",
  "query": "NVIDIA stock competitive analysis market share vs competitors 2025",
  "results": [
    {
      "title": "NVIDIA vs AMD: Who Wins the AI Chip War?",
      "url": "https://example.com/article1",
      "content": "NVIDIA dominates with 80% market share in AI accelerators..."
    },
    {
      "title": "Intel's AI Strategy: Can It Compete with NVIDIA?",
      "url": "https://example.com/article2",
      "content": "Intel is investing heavily in AI chips to challenge NVIDIA's market..."
    },
    ...
  ]
}
```

**What the Worker Does**:
- Reads all 5 search results
- Extracts: competitive position, key rivals, strategic advantages
- Condenses to 3-4 sentences: "NVIDIA maintains X market share. Key competitors include Y. Strategic advantage: Z."

**Example Output**:
> "NVIDIA maintains 80% market share in AI accelerators, far ahead of AMD and Intel. The competitive moat is strengthened by software ecosystem (CUDA), first-mover advantage, and production capacity. Key threats: AMD's EPYC Genoa gaining traction, Intel's Arc Accelerators, and emerging startups like Cerebras."

---

### 2. `financial_analysis(ticker: str) -> str`

**Purpose**: Fetch financial metrics and performance data.

**Tavily Search Query**:
```
"{ticker} financial results revenue earnings profit margin PE ratio 2025"
```

**Search Depth**: Advanced  
**Max Results**: 5

**Return Format**:
```json
{
  "ticker": "NVDA",
  "query": "NVIDIA financial results revenue earnings profit margin PE ratio 2025",
  "results": [
    {
      "title": "NVIDIA Q3 2025 Earnings: Revenue Exceeds Expectations",
      "url": "https://example.com/earnings",
      "content": "Revenue: $40.4B (+50% YoY), Net Income: $23B, Margin: 57%, P/E: 48x"
    },
    {
      "title": "NVIDIA Financial Forecast 2025-2027",
      "url": "https://example.com/forecast",
      "content": "Expected CAGR: 35%, Gross Margin: 60%+, Earnings Per Share Growth: 40%"
    },
    ...
  ]
}
```

**What the Worker Does**:
- Reads all 5 search results
- Extracts: revenue trends, profit margins, P/E ratio, valuation vs peers
- Condenses to 3-4 sentences: "Revenue growing at X%. Margin is Y%. P/E compares as Z."

**Example Output**:
> "NVIDIA's Q3 2025 revenue of $40.4B represents 50% year-over-year growth, significantly outpacing the broader semiconductor industry. Net margins of 57% demonstrate exceptional operational leverage and pricing power. With a P/E ratio of 48x, valuation is premium to peers but justified by consistent earnings growth and dominant market position."

---

### 3. `news_sentiment_analysis(ticker: str) -> str`

**Purpose**: Fetch recent news and market sentiment for a ticker.

**Tavily Search Query**:
```
"{ticker} stock news analyst sentiment outlook 2025"
```

**Search Depth**: Advanced  
**Max Results**: 5  
**Topic Filter**: "news" (focuses on recent news articles)

**Return Format**:
```json
{
  "ticker": "NVDA",
  "query": "NVIDIA stock news analyst sentiment outlook 2025",
  "results": [
    {
      "title": "Goldman Sachs Upgrades NVIDIA to Buy on AI Tailwinds",
      "url": "https://example.com/upgrade",
      "content": "Goldman Sachs analysts expect NVIDIA to reach $2T valuation by 2027..."
    },
    {
      "title": "Markets Rally on NVIDIA's Q3 Beat",
      "url": "https://example.com/rally",
      "content": "NVIDIA stock surges 12% following better-than-expected earnings..."
    },
    ...
  ]
}
```

**What the Worker Does**:
- Reads all 5 search results
- Extracts: overall sentiment (positive/negative/neutral), key themes, recent events
- Condenses to 3-4 sentences: "Overall sentiment is X. Key themes: Y. Recent event: Z."

**Example Output**:
> "Market sentiment toward NVIDIA is overwhelmingly positive, with analyst upgrades citing sustained AI infrastructure demand. Key themes include AI adoption acceleration, data center expansion, and software monetization opportunities. Recent positive catalysts include Q3 earnings beats and partnerships with major cloud providers."

---

### 4. `bull_case_analysis(ticker: str) -> str`

**Purpose**: Fetch bullish arguments and upside thesis for a ticker.

**Tavily Search Query**:
```
"{ticker} stock bull case growth catalysts investment thesis upside 2025"
```

**Search Depth**: Advanced  
**Max Results**: 5

**Return Format**:
```json
{
  "ticker": "NVDA",
  "query": "NVIDIA stock bull case growth catalysts investment thesis upside 2025",
  "results": [
    {
      "title": "NVIDIA Bull Case: Why Stock Could Double by 2027",
      "url": "https://example.com/bull",
      "content": "AI proliferation, data center dominance, software opportunities, international expansion..."
    },
    {
      "title": "Long-Term NVIDIA: Secular Growth in AI Infrastructure",
      "url": "https://example.com/secular",
      "content": "NVIDIA positioned to benefit from trillion-dollar AI market opportunity..."
    },
    ...
  ]
}
```

**What the Worker Does**:
- Reads all 5 search results
- Makes the bullish case: growth catalysts, competitive moat, positive macro tailwinds
- Condenses to 3-4 sentences: "Catalysts: X. Moat: Y. Tailwinds: Z."

**Example Output**:
> "NVIDIA stands to benefit from massive secular growth in AI infrastructure, with addressable markets expanding into enterprise software, automotive, and consumer applications. The company's CUDA ecosystem creates a durable competitive moat, with high switching costs for customers. Key catalysts include international market expansion, new product launches, and enterprise AI adoption acceleration driven by genAI workflows."

---

### 5. `bear_case_analysis(ticker: str) -> str`

**Purpose**: Fetch bearish arguments and downside risks for a ticker.

**Tavily Search Query**:
```
"{ticker} stock bear case risks challenges headwinds downside 2025"
```

**Search Depth**: Advanced  
**Max Results**: 5

**Return Format**:
```json
{
  "ticker": "NVDA",
  "query": "NVIDIA stock bear case risks challenges headwinds downside 2025",
  "results": [
    {
      "title": "NVIDIA Valuation Risk: Why Stock Is Overpriced",
      "url": "https://example.com/bear",
      "content": "Valuation stretched at 48x P/E, risks include AI saturation, competition..."
    },
    {
      "title": "NVIDIA Bears: Margin Compression and Concentration Risk",
      "url": "https://example.com/risks",
      "content": "Customer concentration with mega-cap cloud providers, margin compression fears..."
    },
    ...
  ]
}
```

**What the Worker Does**:
- Reads all 5 search results
- Makes the bearish case: key risks, competitive threats, negative macro headwinds
- Condenses to 3-4 sentences: "Risks: X. Threats: Y. Headwinds: Z."

**Example Output**:
> "NVIDIA's valuation of 48x P/E is elevated relative to historical averages and peers, leaving little room for disappointment. The company faces rising competitive threats from AMD, Intel, and custom silicon efforts by major cloud providers seeking to reduce dependency. Key risks include AI market saturation concerns, potential margin compression, and concentration risk with a handful of mega-cap customers."

---

## Tool Invocation Pattern

### In Worker Node:

```python
def worker_node(state: WorkerState) -> dict:
    wo = state["work_order"]
    wtype = wo["worker_type"]
    ticker = wo["ticker"]
    
    # Step 1: Get the right tool
    tool_fn = TOOL_MAP[wtype]  # e.g., competetive_analysis
    
    # Step 2: Invoke it with the ticker
    raw = tool_fn.invoke({"ticker": ticker})
    # raw is now a JSON string with search results
    
    # Step 3: Pass raw results to specialist LLM for interpretation
    response = llm.invoke([
        SystemMessage(content=WORKER_PROMPTS[wtype]),
        HumanMessage(content=f"Analyze: {raw}")
    ])
    
    # Step 4: Return interpreted findings
    return {"worker_results": [{"worker_type": wtype, "findings": response.content}]}
```

---

## Data Flow Example: NVDA Bull Case

```
INPUT:
  ticker = "NVDA"
  worker_type = "bull_case_analysis"

↓

TOOL INVOCATION:
  bull_case_analysis.invoke({"ticker": "NVDA"})
  
↓

TAVILY SEARCH:
  Query: "NVIDIA stock bull case growth catalysts investment thesis upside 2025"
  Results: 5 articles from finance sites, analyst reports, research papers
  
↓

TOOL OUTPUT (JSON String):
{
  "ticker": "NVDA",
  "results": [
    {title: "...", url: "...", content: "..."},
    {title: "...", url: "...", content: "..."},
    ...
  ]
}

↓

SPECIALIST LLM INTERPRETATION:
  SystemMessage: "You are a Bullish Equity Analyst. Make the bull case..."
  HumanMessage: "Analyze this raw data: [full JSON above]"
  
↓

LLM OUTPUT (Interpreted Findings):
  "NVIDIA stands to benefit from... Key catalysts... Competitive moat... Tailwinds..."

↓

WORKER RESULT:
{
  "worker_type": "bull_case_analysis",
  "findings": "NVIDIA stands to benefit from..."
}
```

---

## API Dependency: Tavily

All tools depend on the **Tavily Search API** for real-time data.

**Setup**:
1. Sign up at https://tavily.com
2. Get API key
3. Set `TAVILY_API_KEY=your_key` in `.env`

**Query Features Used**:
- `search_depth="advanced"`: Deeper, more comprehensive searches
- `max_results=5`: Limit to 5 results per search
- `topic="news"`: For news-specific queries (sentiment analysis only)

**Cost**: Tavily offers free tier + paid plans. Check their pricing.

---

## Extending Tools

### Adding a New Tool

1. **Create the tool function** in `tools.py`:
```python
@tool
def new_analysis(ticker: str) -> str:
    """
    Description for the tool docstring.
    """
    results = _tavily().search(
        query=f"{ticker} relevant search query 2025",
        search_depth="advanced",
        max_results=5,
    )
    return json.dumps({
        "ticker": ticker,
        "results": [
            {"title": r["title"], "url": r["url"], "content": r["content"]}
            for r in results.get("results", [])
        ],
    })
```

2. **Add to TOOL_MAP** in `stocks.py`:
```python
TOOL_MAP = {
    ...
    "new_analysis": new_analysis,
}
```

3. **Add specialist prompt** in `stocks.py`:
```python
WORKER_PROMPTS = {
    ...
    "new_analysis": "You are a New Analysis Specialist. Analyze: ...",
}
```

4. **Orchestrator automatically recognizes it** — no other changes needed.

---

## Error Handling

### Tool Failures

If a tool fails (e.g., Tavily API is down), the worker gracefully handles it:

```python
try:
    raw = tool_fn.invoke({"ticker": ticker})
    # interpret with LLM
except Exception as e:
    return {"worker_results": [
        {"worker_type": wtype, "findings": f"Tool failed: {str(e)}"}
    ]}
```

The graph continues — other workers still complete, and synthesizer gets partial results.

---

## Performance Notes

- **Tavily Search**: ~5-10 seconds per query (network dependent)
- **LLM Interpretation**: ~1-2 seconds per worker (depends on model)
- **Total per worker**: ~6-12 seconds
- **All 5 workers in parallel**: ~6-12 seconds (not 30-60 seconds)

This is why the orchestrator-worker pattern is faster than sequential analysis.

---

## References

- **LangChain Tools**: https://python.langchain.com/docs/modules/tools/
- **Tavily API Docs**: https://docs.tavily.com/
- **Supported Search Parameters**: search_depth, max_results, topic, etc.
