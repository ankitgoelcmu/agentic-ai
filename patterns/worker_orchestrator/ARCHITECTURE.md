# Stock Analysis Agent: Architecture & Diagrams

## High-Level Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     INPUT: ticker + user_query                       │
│                   (e.g., "NVDA", "Bull case only")                   │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ↓
        ┌─────────────────────┐
        │  ORCHESTRATOR NODE  │
        │                     │
        │ Reads ticket +      │
        │ user query          │
        │                     │
        │ LLM decides:        │
        │ What tasks needed?  │
        │                     │
        │ Outputs:            │
        │ 4-5 WorkOrders      │
        └──────────┬──────────┘
                   │
                   ↓
        ┌──────────────────────┐
        │  DISPATCH FUNCTION   │
        │  (not a node)        │
        │                      │
        │ Convert WorkOrders   │
        │ into Send objects    │
        │                      │
        │ Spawn N parallel     │
        │ worker branches      │
        └──────┬────┬──┬──┬───┘
               │    │  │  │
    ┌──────────┴────┴──┴──┴──────────────┐
    │      ALL 5 WORKERS RUN PARALLEL     │
    └──┬────────┬──────────┬────────┬────┘
       │        │          │        │
       ↓        ↓          ↓        ↓
  ┌────────┐┌────────┐┌────────┐┌────────┐
  │Worker 1││Worker 2││Worker 3││Worker 4│
  │ Comp   ││ Fin    ││ News   ││ Bull   │
  └──┬─────┘└───┬────┘└───┬────┘└───┬────┘
     │          │         │         │
  ┌──▼──────┬───▼──────┬──▼──────┬──▼──────┐
  │ Tool    │ Tool     │ Tool    │ Tool    │
  │ Search  │ Search   │ Search  │ Search  │
  └──┬──────┴───┬──────┴──┬──────┴──┬──────┘
     │          │        │         │
  ┌──▼──────┬───▼──────┬──▼──────┬──▼──────┐
  │ LLM     │ LLM      │ LLM     │ LLM     │
  │ Interp  │ Interp   │ Interp  │ Interp  │
  └──┬──────┴───┬──────┴──┬──────┴──┬──────┘
     │          │        │         │
  ┌──▼──────────▼────────▼────────▼──────┐
  │  FAN-IN MERGE (operator.add)         │
  │  All results combined into list      │
  │  (order preserved, no overwriting)   │
  └─────────────────┬────────────────────┘
                    │
                    ↓
        ┌───────────────────────┐
        │  SYNTHESIZER NODE     │
        │                       │
        │ Reads ALL findings    │
        │ Performs cross-      │
        │ analyst reasoning     │
        │                       │
        │ Outputs:              │
        │ • exec_summary        │
        │ • blog_post           │
        └────────┬──────────────┘
                 │
                 ↓
        ┌──────────────────────┐
        │ FINAL OUTPUT         │
        │ • Executive Summary  │
        │ • Investor Blog Post │
        └──────────────────────┘
```

---

## State Flow Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                   INITIAL STATE                               │
├──────────────────────────────────────────────────────────────┤
│ ticker: "NVDA"                                                │
│ user_query: "Bull case only"                                  │
│ work_orders: []                                               │
│ worker_results: []                                            │
│ executive_summary: ""                                         │
│ blog_post: ""                                                 │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   │ [Orchestrator outputs work_orders]
                   ↓
┌──────────────────────────────────────────────────────────────┐
│               STATE AFTER ORCHESTRATOR                        │
├──────────────────────────────────────────────────────────────┤
│ ticker: "NVDA"                                                │
│ user_query: "Bull case only"                                  │
│ work_orders: [                                                │
│   {worker_type: "competetive_analysis", ...},                │
│   {worker_type: "financial_analysis", ...},                  │
│   {worker_type: "bull_case_analysis", ...}                   │
│ ]                                                             │
│ worker_results: []                                            │
│ executive_summary: ""                                         │
│ blog_post: ""                                                 │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   │ [Dispatch spawns 3 parallel Send branches]
                   │ [Each worker appends result to worker_results]
                   │ [operator.add ensures no overwriting]
                   ↓
┌──────────────────────────────────────────────────────────────┐
│            STATE AFTER ALL WORKERS COMPLETE                  │
├──────────────────────────────────────────────────────────────┤
│ ticker: "NVDA"                                                │
│ user_query: "Bull case only"                                  │
│ work_orders: [3 work orders]                                  │
│ worker_results: [                                             │
│   {worker_type: "competetive_analysis", findings: "..."},     │
│   {worker_type: "financial_analysis", findings: "..."},       │
│   {worker_type: "bull_case_analysis", findings: "..."}        │
│ ]                    ↑                                        │
│ executive_summary: ""                                         │
│ blog_post: ""                                                 │
│                                                               │
│ NOTE: operator.add merged all 3 results into one list        │
│       without overwriting. Preserves order.                   │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   │ [Synthesizer reads all findings]
                   │ [Writes executive_summary + blog_post]
                   ↓
┌──────────────────────────────────────────────────────────────┐
│              FINAL STATE (OUTPUT)                             │
├──────────────────────────────────────────────────────────────┤
│ ticker: "NVDA"                                                │
│ user_query: "Bull case only"                                  │
│ work_orders: [3 work orders]                                  │
│ worker_results: [3 findings]                                  │
│ executive_summary: "NVIDIA is a dominant AI chip maker..."    │
│ blog_post: "NVIDIA: The AI Infrastructure Leader..."          │
└──────────────────────────────────────────────────────────────┘
```

---

## Parallel Execution Timeline

```
Time    Orchestrator   Worker 1    Worker 2    Worker 3    Synthesizer
(s)     (decompose)    (Comp)      (Fin)       (News)      (aggregate)

0       ┌──────────────┐
        │ Parse input  │
        │ Create 3     │
        │ work orders  │
        └──────┬───────┘
               │

1              │      ┌──────────┐ ┌──────────┐ ┌──────────┐
               ├─────→│ Tavily   │ │ Tavily   │ │ Tavily   │
               │      │ Search   │ │ Search   │ │ Search   │
               │      │ (comp)   │ │ (fin)    │ │ (news)   │
               │      └────┬─────┘ └────┬─────┘ └────┬─────┘
               │           │            │            │

6              │           ├────────────┤────────────┤
               │           │ LLM 1      │ LLM 2      │ LLM 3
               │           │ interpret  │ interpret  │ interpret
               │           │            │            │

8              │           └────────────┴────────────┘
               │                         ↓
               │                  ┌──────────────┐
               │                  │ Merge:       │
               │                  │ operator.add │
               │                  └──────┬───────┘
               │                         │

9                                         ↓
               │                  ┌──────────────┐
               │                  │ LLM reads    │
               │                  │ all findings │
               │                  │ write output │
               │                  └──────┬───────┘
               │                         │

11             │                         ↓
               └─────────────────────────→ END


KEY: Worker 1 = ~7-8s (search + LLM)
     Worker 2 = ~7-8s (search + LLM)
     Worker 3 = ~7-8s (search + LLM)
     Merge = ~0.5s (fast)
     Synthesizer = ~2-3s (LLM)
     
     Total PARALLEL: ~11s
     Total SERIAL (if sequential): ~35s
     
     SPEEDUP: 3.2x faster with parallelism
```

---

## Worker Instance Isolation

```
┌───────────────────────────────────────────────────────────────┐
│                 ORCHESTRATOR STATE                             │
│  (shared, visible to all nodes)                               │
│                                                                │
│  ticker = "NVDA"                                               │
│  user_query = "Bull case"                                      │
│  work_orders = [WO1, WO2, WO3]                                 │
│  worker_results = []  (will be merged)                         │
│  ...                                                           │
└──┬───────────────────────────────────────────────────────────┘
   │
   │ dispatch_to_workers() creates Send() objects
   │
   ├─ Send("worker", {WORKER_STATE_1})
   ├─ Send("worker", {WORKER_STATE_2})
   └─ Send("worker", {WORKER_STATE_3})
   
   ↓

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ WORKER STATE 1  │  │ WORKER STATE 2  │  │ WORKER STATE 3  │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│ ticker: "NVDA"  │  │ ticker: "NVDA"  │  │ ticker: "NVDA"  │
│ work_order: WO1 │  │ work_order: WO2 │  │ work_order: WO3 │
│ worker_results: │  │ worker_results: │  │ worker_results: │
│   []            │  │   []            │  │   []            │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
    Isolated         Isolated         Isolated
    execution of     execution of     execution of
    worker_node      worker_node      worker_node
    (Branch 1)       (Branch 2)       (Branch 3)
         │                    │                    │
         └────────────────────┴────────────────────┘
                      ↓

        ┌──────────────────────────────┐
        │ FAN-IN MERGE                 │
        │ operator.add combines all 3: │
        │ result1 + result2 + result3  │
        │ → single merged list          │
        └──────────────────────────────┘
                      ↓

        ┌──────────────────────────────┐
        │ ORCHESTRATOR STATE UPDATED    │
        │ worker_results = [R1, R2, R3] │
        │ (back to shared state)        │
        └──────────────────────────────┘

NOTE: Each worker_node gets its own WORKERSTATE with ONLY:
  - ticker (for context)
  - work_order (its ONE assigned task)
  - empty worker_results list
  
This is NOT the full OrchestratorState. Each instance is isolated.
When it finishes, its result is merged into OrchestratorState via operator.add.
```

---

## Tool Invocation per Worker

```
WORKER INSTANCE (e.g., Bull Case Analyst):

┌──────────────────────────────────────────────────────────┐
│         Step 1: Tool Call (Deterministic)                │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ work_order.worker_type = "bull_case_analysis"            │
│ tool_fn = TOOL_MAP["bull_case_analysis"]                │
│                                                          │
│ raw = tool_fn.invoke({"ticker": "NVDA"})                │
│                                                          │
│ result = {                                              │
│   "ticker": "NVDA",                                      │
│   "results": [                                           │
│     {title: "...", url: "...", content: "..."},          │
│     {title: "...", url: "...", content: "..."},          │
│     ...                                                  │
│   ]                                                      │
│ }                                                        │
│                                                          │
│ Execution time: ~7-10s (Tavily search latency)          │
│                                                          │
└──────────────────┬───────────────────────────────────────┘
                   │

┌──────────────────────────────────────────────────────────┐
│      Step 2: Specialist LLM Interpretation                │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ system_msg = WORKER_PROMPTS["bull_case_analysis"]       │
│ "You are a Bullish Equity Analyst. Given data..."       │
│                                                          │
│ human_msg = f"""                                        │
│ Task: {work_order.task}                                 │
│                                                          │
│ Raw tool output:                                        │
│ {raw}  (← full JSON from tool)                          │
│ """                                                      │
│                                                          │
│ llm_response = llm.invoke([system_msg, human_msg])      │
│                                                          │
│ findings = llm_response.content                         │
│ "NVIDIA stands to benefit from..."                      │
│                                                          │
│ Execution time: ~1-3s (LLM inference)                   │
│                                                          │
└──────────────────┬───────────────────────────────────────┘
                   │

┌──────────────────────────────────────────────────────────┐
│      Step 3: Write Result to State                        │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ return {                                                │
│   "worker_results": [                                   │
│     {                                                   │
│       "worker_type": "bull_case_analysis",              │
│       "findings": findings  (from LLM)                  │
│     }                                                   │
│   ]                                                     │
│ }                                                        │
│                                                          │
│ This appends to worker_results via operator.add         │
│ Does NOT overwrite other workers' results               │
│                                                          │
└──────────────────────────────────────────────────────────┘

TOTAL TIME PER WORKER: ~8-13 seconds
ALL 3 WORKERS IN PARALLEL: Still ~8-13 seconds (longest worker wins)
```

---

## operator.add Mechanism

```
Problem: Multiple workers write to state.worker_results simultaneously.
If we use dict update, last writer overwrites all others.

Solution: Annotated[List[WorkerResult], operator.add]

SIMULATION:

Initial state:
  worker_results = []

Worker 1 writes:
  return {"worker_results": [Result1]}
  
Worker 2 writes:
  return {"worker_results": [Result2]}
  
Worker 3 writes:
  return {"worker_results": [Result3]}

Without operator.add (❌ BROKEN):
  state.worker_results = [Result3]  ← overwrites Result1 & Result2!

With operator.add (✅ CORRECT):
  state.worker_results = [] + [Result1] + [Result2] + [Result3]
                      = [Result1, Result2, Result3]
  
  operator.add(list1, list2) ≈ list1.extend(list2)

RESULT: All 3 findings coexist without overwriting.
```

---

## State Class Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│           OrchestratorState                              │
│      (Shared, lives for entire run)                      │
├─────────────────────────────────────────────────────────┤
│ ticker: str                                              │
│ user_query: str                                          │
│ work_orders: List[WorkOrder]     ← set by orchestrator  │
│ worker_results: Annotated[List[WorkerResult], op.add]   │
│   ↑ fan-in: receives merged results from all workers    │
│ executive_summary: str           ← set by synthesizer   │
│ blog_post: str                   ← set by synthesizer   │
└──┬──────────────────────────────────────────────────────┘
   │ dispatch_to_workers() sends WorkerState instances
   ↓
┌─────────────────────────────────────────────────────────┐
│           WorkerState (per Send)                         │
│      (Isolated, one copy per parallel branch)           │
├─────────────────────────────────────────────────────────┤
│ ticker: str                      ← carried from above   │
│ work_order: WorkOrder            ← ONE task per worker  │
│ worker_results: Annotated[List[WorkerResult], op.add]   │
│   ↑ worker appends its result here                      │
│   ↓ merged back to OrchestratorState when branch done   │
└─────────────────────────────────────────────────────────┘

Key insight:
  OrchestratorState is the "top level"
  WorkerState is "slice" of state for each parallel branch
  Merging happens at fan-in automatically
```

---

## Graph Topology

```
START
  │
  ↓
┌──────────────────┐
│  orchestrator    │
└────────┬─────────┘
         │
         ↓
  ┌─────────────────────────────────┐
  │  dispatch_to_workers()          │
  │  (conditional edge, not a node) │
  │  Returns: [Send, Send, Send]    │
  └────┬──────────────────────────┬──┴────────┐
       │                          │           │
       ↓                          ↓           ↓
  ┌────────────┐           ┌────────────┐  ┌────────────┐
  │  worker    │  (parallel)  │  worker  │  │  worker    │
  │ instance 1 │           │ instance 2│  │ instance 3 │
  └────┬───────┘           └────┬──────┘  └────┬───────┘
       │                        │              │
       └────────────────┬───────┴──────────────┘
                        ↓
         ┌──────────────────────────┐
         │  (LangGraph waits here)  │
         │  (Fan-in merge happens)  │
         │  (operator.add combines) │
         └──────────┬───────────────┘
                    ↓
         ┌──────────────────────────┐
         │    synthesizer           │
         └──────────┬───────────────┘
                    ↓
                   END

Graph.compile() handles all scheduling automatically.
```

---

## Real Execution Order (with Timing)

```
T=0s   | Invoke graph with input
       |
T=0.1s | START → orchestrator node
       | Orchestrator LLM decides tasks
       |
T=1.2s | orchestrator → dispatch_to_workers()
       | Creates 3 Send objects
       |
T=1.3s | LangGraph spawns 3 parallel branches
       | Each has its own WorkerState
       |
T=1.3s | [BRANCH 1] worker_node(WorkerState_1)
T=1.3s | [BRANCH 2] worker_node(WorkerState_2)
T=1.3s | [BRANCH 3] worker_node(WorkerState_3)
       |
       | ──── PARALLEL EXECUTION ────
       |
T=1.5s | Branch 1: Tool call starts (Tavily search)
T=1.5s | Branch 2: Tool call starts (Tavily search)
T=1.5s | Branch 3: Tool call starts (Tavily search)
       |
T=8.5s | Branch 1: Tool returns, LLM starts
T=8.5s | Branch 2: Tool returns, LLM starts
T=8.5s | Branch 3: Tool returns, LLM starts
       |
T=10s  | Branch 1: Returns result + merged into state
T=10.1s| Branch 2: Returns result + merged into state
T=10.2s| Branch 3: Returns result + merged into state
       |
T=10.3s| ──── FAN-IN COMPLETE ────
       | All results now in OrchestratorState.worker_results
       | via operator.add
       |
T=10.3s| worker → synthesizer node
       | Synthesizer reads all 3 findings
       |
T=10.3s| Synthesizer LLM starts
       |
T=12.5s| Synthesizer writes outputs
       | (executive_summary, blog_post)
       |
T=12.6s| synthesizer → END
       |
T=12.6s| Return final state to caller

Total execution: ~12.6 seconds
(vs ~25+ seconds if all done sequentially)
```

---

## Decision Tree: Orchestrator Task Assignment

```
START: Analyzing ticker "NVDA", user_query "Bull case only"

┌─────────────────────────────────┐
│ Parse user_query                │
└────────────┬────────────────────┘
             │
    ┌────────▼────────┐
    │ Is query empty? │
    └────┬────────┬───┘
      NO │        │ YES
         │        └──────────────────────────────┐
         │                                       │
    ┌────▼──────────────────────────┐  ┌────────▼───────────┐
    │ Extract specific keywords:    │  │ Create all 5 tasks │
    │ • "bull" → bull_case_analysis │  │ (generic)          │
    │ • "bear" → bear_case_analysis │  └────────────────────┘
    │ • "competitive" → comp...     │
    │ • "financial" → financial...  │
    │ • "news" → news_sentiment...  │
    │ • "sentiment" → news_sentiment│
    └────┬──────────────────────────┘
         │
    ┌────▼──────────────────────────┐
    │ Create WorkOrders for matched  │
    │ worker types + supporting      │
    │ analyses                       │
    │                                │
    │ Example:                       │
    │ - bull_case_analysis           │
    │ - financial_analysis (support) │
    │ - competitive_analysis (support)
    └────┬──────────────────────────┘
         │
    ┌────▼──────────────────────────┐
    │ Return JSON array of          │
    │ WorkOrders                    │
    └───────────────────────────────┘
```

---

## Summary: Why This Pattern Works

| Aspect | Benefit | Example |
|--------|---------|---------|
| **Parallelism** | 3.2x faster | 5 workers × 10s each = 32s serial vs 10s parallel |
| **Specialization** | Focused outputs | Financial analyst interprets earnings differently than sentiment analyst |
| **Resilience** | One worker fails, others complete | If Tavily is slow for one query, others proceed |
| **Scalability** | Add workers without changing core | Add news_sentiment_2, sentiment_analysis — just new tools |
| **Clarity** | Clear dataflow | Easy to trace: orchestrator → dispatch → workers → synthesizer |
| **Maintainability** | Separate concerns | Each node has one job; TOOL_MAP keeps routing clean |

