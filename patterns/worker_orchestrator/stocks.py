"""
Stock Analyst Orchestrator-Workers Agent
================================
Design pattern (Anthropic): A central Orchestrator LLM decomposes an incoming request
(Ticker Symbol e.g. NVDA, MU) into independent sub-tasks, dispatches them to specialist
Worker LLMs that run in PARALLEL, then a Synthesizer LLM aggregates all findings and
writes an executive summary + investor blog post.

Data flow:
  ticker (input)
    → orchestrator_node   : LLM creates work orders (what to analyze)
    → dispatch_to_workers : splits work orders into parallel Send branches
    → worker_node × N     : each worker runs its tool + interprets results  (PARALLEL)
    → synthesizer_node    : aggregates findings, writes executive summary + blog post
    → result (output)
"""

import json
import operator   # operator.add is used as the fan-in reducer for parallel writes
from typing import Annotated, TypedDict, List
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send  # Send = the primitive that creates parallel branches

# tools.py lives in the same folder (stock-analysis/tools.py)
# competetive_analysis(ticker)      → returns competitive position, market share, competitors
# financial_analysis(ticker)        → returns revenue growth, profit margin, P/E ratio
# news_sentiment_analysis(ticker)   → returns sentiment score and key news highlights
# bull_case_analysis(ticker)        → returns bullish arguments for the stock
# bear_case_analysis(ticker)        → returns bearish arguments for the stock
from tools import (
    competetive_analysis,
    financial_analysis,
    news_sentiment_analysis,
    bull_case_analysis,
    bear_case_analysis,
)

load_dotenv()


# ============================================================================
# STATE CLASSES
# ============================================================================
# LangGraph passes state between nodes like a baton.
# Every node receives the current state dict and returns a PARTIAL update dict.
# LangGraph merges that partial update back into the shared state.
# ============================================================================

class WorkOrder(TypedDict):
    """
    A single unit of research created by the Orchestrator.
    Think of it as a task ticket handed to one specialist worker.

    worker_type : which specialist to route to — must exactly match a key in WORKER_PROMPTS
                  ("competetive_analysis" | "financial_analysis" | "news_sentiment_analysis"
                   | "bull_case_analysis" | "bear_case_analysis")
    task        : human-readable description of what to research
    ticker      : stock symbol, e.g. "NVDA" — passed directly to the tool
    """
    worker_type: str
    task: str
    ticker: str


class WorkerResult(TypedDict):
    """
    The output a Worker writes back after completing its research.

    worker_type : which worker produced this — used by synthesizer to label findings
    findings    : the LLM-interpreted summary of what the tool returned
    """
    worker_type: str
    findings: str          # ← consistent field name used everywhere


class OrchestratorState(TypedDict):
    """
    The SHARED state that lives for the entire lifetime of one graph run.
    Every top-level node (orchestrator, synthesizer) reads and writes this.

    ticker           : stock symbol set at invocation, never changed — carried through
                       entire workflow so every node knows which stock we're analyzing
    user_query       : Use the user query to divide the tasks for available workers. It may be possible that not all workers will be assigned tasks. It will depend on the specificity of the user query. If the user query is empty, create one generic task for each worker covering its main focus area.
    worker_results   : list of WorkerResults written by worker nodes.
                       Annotated with operator.add so parallel workers APPEND
                       instead of overwriting each other.
    executive_summary: short summary written by synthesizer for investors
    blog_post        : long-form investor post written by synthesizer
    """
    ticker: str
    user_query: str
    work_orders: List[WorkOrder]
    worker_results: Annotated[List[WorkerResult], operator.add]  # ← fan-in reducer
    executive_summary: str
    blog_post: str


class WorkerState(TypedDict):
    """
    The ISOLATED state each parallel worker branch receives via Send().
    Workers do NOT get the full OrchestratorState — only what they need.

    Why a separate class?
    Send("worker", {...}) spawns an independent execution of worker_node with its
    own private state. Each worker only needs: the ticker for context, its one
    assigned work order, and an empty list to write its result into.

    ticker         : carried forward so worker has stock context
    work_order     : exactly ONE task — the one assigned to this worker instance
    worker_results : starts []; worker appends its WorkerResult here.
                     operator.add merges this back into OrchestratorState.worker_results
                     when the branch finishes (fan-in).
    """
    ticker: str
    work_order: WorkOrder
    worker_results: Annotated[List[WorkerResult], operator.add]


# ============================================================================
# HELPERS
# ============================================================================

def get_llm() -> ChatOllama:
    """
    Factory for a fresh LLM instance.
    temperature=0 → deterministic outputs.
    Change the model name here to swap to GPT-4o, Claude, etc.
    """
    return ChatOllama(model="qwen3-coder-next:latest", temperature=0)


def strip_thinking(content: str) -> str:
    """
    Reasoning models (qwen3) emit <think>...</think> before the real answer.
    Strip it so downstream parsing only sees clean text or JSON.
    """
    if "<think>" in content:
        return content.split("</think>")[-1].strip()
    return content.strip()


def parse_json(content: str):
    """
    Extract JSON from LLM output robustly.
    Step 1: strip <think> blocks.
    Step 2: try direct json.loads.
    Step 3: regex-extract first [...] or {...} block if step 2 fails.
    """
    content = strip_thinking(content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        import re
        match = re.search(r'(\[.*?\]|\{.*?\})', content, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


# ============================================================================
# NODE 1 — ORCHESTRATOR
# ============================================================================
# Reads the ticker, decides WHAT to research, produces WorkOrders.
# Does NOT call any tools or interpret any data itself.
# ============================================================================

# IMPORTANT: worker_type values here must EXACTLY match keys in WORKER_PROMPTS
# and the if/elif chain in worker_node. A mismatch causes silent routing failure.
ORCHESTRATOR_PROMPT = """You are a Stock Research Orchestrator. Your only job is to decompose a stock analysis request into parallel, independent research tasks for specialist workers.
                         Use the user query to divide the tasks for available workers. It may be possible that not all workers will be assigned tasks. It will depend on the specificity of the user query. If the user query is empty, create one generic task for each worker covering its main focus area.

Available workers (use these exact worker_type strings):
- competetive_analysis      → competitive position, market share, key rivals
- financial_analysis        → revenue growth, profit margins, P/E ratio
- news_sentiment_analysis   → news sentiment, key themes, recent events
- bull_case_analysis        → bullish arguments: growth opportunities, tailwinds
- bear_case_analysis        → bearish arguments: risks, threats, headwinds

Rules:
- Every work order targets the same ticker symbol.
- All 5 tasks are independent — dispatch all in one batch.
- user_query may contain specific questions or areas of focus; use it to divide the tasks for specific workers as needed.
- if user_query is empty, create one generic task for each worker covering its main focus area.
- Never sequence tasks that can run simultaneously.

Return ONLY a JSON array — no prose, no markdown fences: This is just exmaple if user query is empty, if user query is not empty, then return only the tasks for which the user query has specific questions or areas of focus.
Example output (if user query is empty):
[
  {"worker_type": "competetive_analysis",    "task": "...", "ticker": "NVDA"},
  {"worker_type": "financial_analysis",      "task": "...", "ticker": "NVDA"},
  {"worker_type": "news_sentiment_analysis", "task": "...", "ticker": "NVDA"},
  {"worker_type": "bull_case_analysis",      "task": "...", "ticker": "NVDA"},
  {"worker_type": "bear_case_analysis",      "task": "...", "ticker": "NVDA"}
]


Example output (if user query is "What is the outlook for NVDA and MU, only provide bearish insights for both executives summary and blog post"):
[
  {"worker_type": "competetive_analysis",    "task": "...", "ticker": "NVDA"},
  {"worker_type": "financial_analysis",      "task": "...", "ticker": "NVDA"},
  {"worker_type": "news_sentiment_analysis", "task": "...", "ticker": "NVDA"},
  {"worker_type": "bear_case_analysis",      "task": "...", "ticker": "NVDA"},
  {"worker_type": "competetive_analysis",    "task": "...", "ticker": "MU"},
  {"worker_type": "financial_analysis",      "task": "...", "ticker": "MU"},
  {"worker_type": "news_sentiment_analysis", "task": "...", "ticker": "MU"},
  {"worker_type": "bear_case_analysis",      "task": "...", "ticker": "MU"}
]

Example output (if user query is "What is the outlook for NVDA , only provide  competitive analysis for both executives summary and blog post"):
[
  {"worker_type": "competetive_analysis",    "task": "...", "ticker": "NVDA"}
  
]

"""


def orchestrator_node(state: OrchestratorState) -> dict:
    """
    Entry point of the graph.
    Sends the ticker to the Orchestrator LLM, which returns 5 parallel WorkOrders.
    Returns a partial state update — only work_orders is written, everything else unchanged.
    """
    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=ORCHESTRATOR_PROMPT),
        HumanMessage(content=f"Analyze this stock: {state['ticker']} \nUser query: {state['user_query']}")
    ])

    work_orders = parse_json(response.content)

    print(f"\n{'='*55}")
    print(f"[ORCHESTRATOR] {state['ticker']} — {len(work_orders)} parallel work orders:")
    for i, wo in enumerate(work_orders, 1):
        print(f"  {i}. [{wo['worker_type'].upper()}] {wo['task']}")

    return {"work_orders": work_orders}


# ============================================================================
# DISPATCH — fan-out via LangGraph Send API
# ============================================================================
# NOT a node. Called by LangGraph as a conditional edge after orchestrator_node.
# Returns one Send per work order → LangGraph runs them all in parallel.
# ============================================================================

def dispatch_to_workers(state: OrchestratorState):
    """
    Converts work_orders list into parallel Send objects.
    Each Send spawns an independent execution of worker_node with its own WorkerState.
    Results are merged back via operator.add when each branch finishes.
    """
    return [
        Send("worker", {
            "ticker": state["ticker"],   # original ticker carried for worker context
            "work_order": wo,            # ONE work order per worker instance
            "worker_results": []         # starts empty; worker appends its result here
        })
        for wo in state["work_orders"]
    ]


# ============================================================================
# NODE 2 — WORKER (runs N times in parallel, one per work order)
# ============================================================================
# Each worker: (1) calls its assigned tool, (2) has a specialist LLM interpret
# the raw output, (3) writes a WorkerResult into shared state.
# ============================================================================

# Each worker type gets its own focused system prompt — its "role".
# The LLM reads this as SystemMessage so it knows HOW to interpret tool output.
# A financial analyst interprets numbers differently from a sentiment analyst.
WORKER_PROMPTS = {
    "competetive_analysis": (
        "You are a Competitive Intelligence Analyst. "
        "Given raw tool output, report: "
        "(1) competitive position, (2) key rivals and threats, (3) strategic advantages. "
        "Be concise — 3-4 sentences max."
    ),
    "financial_analysis": (
        "You are a Financial Analyst. "
        "Given raw financial data, analyze: "
        "(1) revenue trends, (2) profitability metrics, (3) valuation vs peers. "
        "Be concise — 3-4 sentences max."
    ),
    "news_sentiment_analysis": (
        "You are a Market Sentiment Analyst. "
        "Given raw sentiment data, summarize: "
        "(1) overall sentiment (positive/negative/neutral), "
        "(2) key themes, (3) recent events driving sentiment. "
        "Be concise — 3-4 sentences max."
    ),
    "bull_case_analysis": (
        "You are a Bullish Equity Analyst. "
        "Given data and trends, make the bull case: "
        "(1) growth catalysts, (2) competitive moat, (3) positive macro tailwinds. "
        "Be concise — 3-4 sentences max."
    ),
    "bear_case_analysis": (
        "You are a Bearish Equity Analyst. "
        "Given data and trends, make the bear case: "
        "(1) key risks, (2) competitive threats, (3) negative macro headwinds. "
        "Be concise — 3-4 sentences max."
    ),
}

# Maps worker_type string → the tool function to call.
# Centralised here so worker_node stays clean — no long if/elif chain.
TOOL_MAP = {
    "competetive_analysis":    competetive_analysis,
    "financial_analysis":      financial_analysis,
    "news_sentiment_analysis": news_sentiment_analysis,
    "bull_case_analysis":      bull_case_analysis,
    "bear_case_analysis":      bear_case_analysis,
}


def worker_node(state: WorkerState) -> dict:
    """
    Executes one work order end-to-end.

    Step 1 — Tool call:
      Looks up the right tool from TOOL_MAP using worker_type.
      Calls tool.invoke({"ticker": ticker}) → returns raw JSON string.
      No LLM involved yet — this is deterministic data fetching.

    Step 2 — LLM interpretation:
      Specialist LLM reads: its role prompt (SystemMessage) + raw tool JSON (HumanMessage).
      Produces a concise human-readable findings summary.
      Each worker has its own focused context — it does NOT see other workers' results.

    Step 3 — Write result:
      Returns {"worker_results": [WorkerResult]} as a partial state update.
      operator.add appends this into OrchestratorState.worker_results alongside
      results from all other parallel workers — no overwriting.
    """
    wo = state["work_order"]
    wtype = wo["worker_type"]
    ticker = wo["ticker"]

    # ── Step 1: Tool call ───────────────────────────────────────
    tool_fn = TOOL_MAP.get(wtype)
    if tool_fn is None:
        # Unknown worker_type — fail gracefully without crashing the graph
        return {"worker_results": [{"worker_type": wtype, "findings": f"Unknown worker type: {wtype}"}]}

    print(f"\n[WORKER: {wtype}] Running tool for {ticker}...")
    # tool.invoke({"ticker": ticker}) calls the @tool-decorated function.
    # Returns a JSON string with the raw analysis data for this ticker.
    raw = tool_fn.invoke({"ticker": ticker})
    print(f"[WORKER: {wtype}] Tool complete. Interpreting with LLM...")

    # ── Step 2: Specialist LLM interprets raw tool output ───────
    # SystemMessage = the worker's role/persona (from WORKER_PROMPTS)
    # HumanMessage  = the task description + full raw JSON from the tool
    # The LLM only sees these two — narrow context = focused output
    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=WORKER_PROMPTS[wtype]),
        HumanMessage(content=f"Task: {wo['task']}\n\nRaw tool output:\n{raw}")
    ])

    findings = strip_thinking(response.content)
    print(f"[WORKER: {wtype}] → {findings[:120]}...")

    # ── Step 3: Write result into shared state ──────────────────
    # operator.add on worker_results ensures this appends, not overwrites
    return {"worker_results": [{"worker_type": wtype, "findings": findings}]}


# ============================================================================
# NODE 3 — SYNTHESIZER
# ============================================================================
# Reads ALL worker findings (already merged by operator.add), writes the
# executive summary and blog post. The only node that produces final output.
# ============================================================================

SYNTHESIZER_PROMPT = """You are a Senior Equity Research Analyst writing for investors.

You have received parallel research from 5 specialist analysts for a single stock.
Synthesize their findings into two outputs:

1. executive_summary: 2-3 paragraph overview covering competitive position,
   financial health, market sentiment, and the bull vs bear debate.
   Written for a portfolio manager who has 60 seconds to read it.

2. blog_post: A detailed 5-7 paragraph investor-facing blog post.
   Cover: company overview, financial highlights, competitive landscape,
   market sentiment, bull case, bear case, and a balanced conclusion.
   Use plain language. End with a risk disclaimer.

Return ONLY this JSON (no markdown fences):
{
  "executive_summary": "...",
  "blog_post": "..."
}"""


def synthesizer_node(state: OrchestratorState) -> dict:
    """
    The final node — aggregates all worker findings and produces investor content.

    By the time this runs, state["worker_results"] has all 5 workers' findings,
    merged together by operator.add as each parallel branch completed.

    Step 1: Format all findings into one text block labelled by analyst type.
    Step 2: LLM reads ticker + all findings → writes executive_summary + blog_post.
    Step 3: Return both as partial state update.
    """

    # ── Step 1: Compile all worker findings ─────────────────────
    # state["worker_results"] = merged list from all 5 parallel workers
    findings_text = "\n\n".join(
        f"[{r['worker_type'].upper()} ANALYST]\n{r['findings']}"
        for r in state["worker_results"]
    )

    # ── Step 2: LLM synthesizes into executive summary + blog post
    # The synthesizer sees: the ticker, all 5 analyst findings.
    # Its job is cross-analyst reasoning — balancing bull vs bear,
    # weaving financial data with sentiment and competitive context.
    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=SYNTHESIZER_PROMPT),
        HumanMessage(content=f"Stock: {state['ticker']}\n\nAnalyst findings:\n{findings_text}")
    ])

    decision = parse_json(response.content)

    print(f"\n{'='*55}")
    print(f"[SYNTHESIZER] Writing complete for {state['ticker']}")

    # ── Step 3: Write outputs into OrchestratorState ────────────
    # These are the two keys the caller reads from result[...]
    return {
        "executive_summary": decision.get("executive_summary", ""),
        "blog_post": decision.get("blog_post", ""),
    }


# ============================================================================
# GRAPH ASSEMBLY
# ============================================================================

def build_stock_agent():
    """
    Wires all nodes together.

    Graph:
      START → orchestrator → [Send × 5 workers in parallel] → synthesizer → END
    """
    graph = StateGraph(OrchestratorState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("worker", worker_node)
    graph.add_node("synthesizer", synthesizer_node)

    graph.add_edge(START, "orchestrator")

    # Fan-out: dispatch_to_workers returns 5 Send objects → 5 parallel worker branches
    graph.add_conditional_edges("orchestrator", dispatch_to_workers, ["worker"])

    # Fan-in: LangGraph waits for ALL worker branches before running synthesizer
    graph.add_edge("worker", "synthesizer")
    graph.add_edge("synthesizer", END)

    return graph.compile()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    agent = build_stock_agent()

    ticker = "NVDA, MU"  # ← change this to analyze a different stock symbol
    user_query = "What is the outlook for NVDA and MU, only provide bullish insights for both executives summary and blog post"  # ← change this to include a specific query
    print("STOCK ANALYST ORCHESTRATOR-WORKERS AGENT")
    print("=" * 55)
    print(f"Analyzing: {ticker}")
    print(f"User Query: {user_query}")

    result = agent.invoke({
        "ticker": ticker,
        "user_query": user_query,  # optional: can include specific questions or focus areas for the workers    
        "work_orders": [],
        "worker_results": [],    # operator.add accumulates all 5 workers into this
        "executive_summary": "",
        "blog_post": "",
    })

    print("\n" + "=" * 55)
    print("EXECUTIVE SUMMARY:")
    print(result["executive_summary"])

    print("\n" + "=" * 55)
    print("INVESTOR BLOG POST:")
    print(result["blog_post"])
