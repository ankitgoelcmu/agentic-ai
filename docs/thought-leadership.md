# Thought Leadership: Agentic AI & Detection Engineering

Your writings on the detection gap and production failures in AI agents that motivated this project and shaped its architecture.

## The Problem: The Detection Gap

**"The Detection Gap: Why AI-Powered Attacks Are Outrunning Our Defenses"**
- Read: https://ankitgoelcmu.medium.com/the-detection-gap-why-ai-powered-attacks-are-outrunning-our-defenses-and-how-im-closing-it-63b75e392def

### Core Insight

AI has compressed the attacker's timeline. Frontier labs (Anthropic, OpenAI, etc.) publish detailed threat intelligence reports documenting real, disrupted model misuse. But defenders are still operating on the old timeline. A threat report that takes 8 months of investigation to write shouldn't take another week of manual translation before a detection exists for it.

### Why Writing Detection Rules Is Hard

Writing a good Sigma rule requires getting several genuinely hard things right at once:

1. **Understanding the security landscape** - knowing the nature of the threat surface
2. **Knowing the exact vocabulary** - Sigma field names, logsource categories, modifiers
3. **Getting the logic direction right** - detection logic must actually match the described behavior
4. **Translating narrative into telemetry** - converting prose about attacks into observable patterns
5. **Handling beyond a single event** - correlation rules, sequences, counting across time windows

The process is manual and time-consuming. The speed mismatch is the gap.

### The Solution: CyberGuard (This Project)

An AI agent that bridges the gap directly:
- User provides: threat report URL, direct description, or threat intelligence document
- Agent reads and parses it
- Identifies every distinct attack technique described (up to 5 per URL)
- Researches real-world technical detail via threat intelligence sources
- Produces validated, ready-to-deploy Sigma detection rules

**Why this architecture matters**:
- URL reader and web search are isolated subagents (untrusted external data stays out of main agent's focus)
- Main agent stays focused on rule generation with structured tools (sigma_search, sigma_validate)
- Middleware enforces resource bounds to prevent runaway execution
- Evaluation loop validates rules before output

---

## The Reality: What Actually Breaks in Production

**"What Actually Breaks When You Deploy an AI Agent"**
- Read: https://ankitgoelcmu.medium.com/what-actually-breaks-when-you-deploy-an-ai-agent-d8f2457e2d94

### Eight Production Failure Modes

#### 1. Context Drift
**Problem**: Context gets bloated. Model attention dilutes. Original constraints from system prompt are forgotten.

**Fix**: Keep tool outputs condensed at source. Tool call budgets. Structured output only.

**Real example from CyberGuard**: Agent violated constraint "Do not call tavily_search more than 10 times" because context bloat caused token count to climb from 2.1K to 31.2K in just 5 iterations.

#### 2. Infinite Loops
**Problem**: Agent keeps calling same tool with same query, unaware it already tried this.

**Fix**: 
- Max iteration limit (framework level)
- Constraints at system-prompt level
- Tool call limits at code level

**Real example**: Agent kept calling `tavily_search` with identical query: "credential stuffing anomalous request rate threshold detection AI API 2026" — same query, every single call, no variation.

#### 3. Tool Failures
**Problem**: Tool returns vague error message. Model can't self-correct. Every retry resends full accumulated context, compounding the cost.

**Fix**:
- Schema validation for tool arguments
- Structured output from tools
- Specific, named error messages (not "INVALID - could not parse")
- Retry on timeouts with backoff

**Real example**: Sigma validation returned "INVALID - could not parse: Duplicate key '{k}'". Model spent 5 iterations debugging, rewriting the same rule, getting identical unhelpful error each time.

#### 4. Bad Task Decomposition
**Problem**: Main agent's task planning is too vague, too large, or in the wrong order.

**Fix**:
- Force a short planning step upfront
- Break TODOs into atomic tasks
- Verify each task before moving to next

#### 5. Cost Explosion
**Problem**: A stuck agent doesn't fail gracefully. It fails expensively. Every retry resends accumulated conversation. Cost isn't linear—it compounds.

**Real example from CyberGuard**: Looping on same tool calls led to cascading cost explosion. Each failed attempt made every subsequent attempt more expensive than the last.

#### 6. Weak Evals
**Problem**: Validator returns VALID while rule is functionally broken. Structurally perfect. Functionally broken. Most dangerous because you won't see the crash.

**Fix**:
- Add deeper validation (real backend conversion, not just parsing)
- Return specific errors for self-correction
- Accept that no single validation layer catches everything

**How CyberGuard solves this**: 
- Three-layer validation in sigma_validate:
  - Structural & syntax validation (pure parsing)
  - Logical & executable validation (real backend conversion to Sumo Logic query)
  - Semantic correctness (condition references valid selections, fields exist)

#### 7. No Human in the Loop
**Problem**: Risky actions execute without human approval.

**Fix**: Based on confidence and risk level, add human approval gates.

#### 8. No Recovery Path
**Problem**: Agent run crashes mid-processing or gets interrupted with no way to resume.

**Fix**: Save checkpoints. Support resuming. Build in failure detection (heartbeats) and resumption logic.

---

## The One Thing Underneath All Five Failures I Hit

**"Enforce in code what code can verify. Reserve the prompt for genuine judgment calls. Even then, don't assume the agent will get it right. Test it against real, repeated, and adversarial cases."**

The fixes that made the biggest difference weren't in the prompt. They were in the code:
- Tool call budgets are middleware, not system prompt suggestions
- Error messages come from code-level error handling, not LLM reasoning
- Validation layers are stacked: syntax, logic, semantic correctness (each catches different blind spots)
- Resource limits are hard boundaries enforced by framework, not hopes expressed in natural language

---

## How This Maps to agentic-ai Patterns

### Parallel Pattern
Relates to: Weak evals, multiple perspectives on correctness
- Run multiple independent checks (like security screening)
- Aggregate to catch what one validator might miss

### Routing Pattern
Relates to: Task decomposition, specialized handling
- Classify input precisely before delegating
- Let specialized agents focus on their domain

### Prompt Chaining Pattern
Relates to: Task decomposition, clear handoffs
- Break complex work into sequential steps
- Each step has clear input/output contract

### Eval Optimizer Pattern
Relates to: Weak evals, validation loops, iterative improvement
- Generate output
- Evaluate against criteria
- Feed feedback back to improve
- Stop when criteria are met

### Worker Orchestrator Pattern
Relates to: Cost explosion prevention, task distribution
- Distribute work to prevent single-agent bottleneck
- Coordinate results
- Bound resource usage per worker

---

## Connection to sigma_rule_writer

CyberGuard (sigma_rule_writer in this repo) is a concrete example of all eight failure modes resolved through:

1. **Isolation**: Subagents handle untrusted external data (URLs, web search)
2. **Bounded execution**: Tool call limits per type
3. **Multi-layer validation**: Syntax + logic + semantic correctness
4. **Specific errors**: Real error messages from underlying libraries, not LLM-generated guesses
5. **Clear task boundaries**: Each technique gets its own todo, processed independently
6. **Middleware enforcement**: ToolCallLimitMiddleware, ModelCallLimitMiddleware at framework level
7. **Evaluation loop**: sigma_validate is called, failures trigger refining loop (max 2 attempts)
8. **Structured outputs**: Tools return typed schemas, not free-text prose

The repo includes the actual code that implements these principles. Not as an example of "best practices from a blog," but as a field-tested system that failed all eight ways first, then fixed them.

---

## Key Takeaway

The gap isn't real if defenders can't close it fast enough. The defense gap isn't a timeline problem. It's a task decomposition problem. The solution isn't a faster human. It's a system that can:

- Read unstructured threat intelligence
- Extract structured attack patterns
- Research real-world technical detail
- Generate production-ready detection code
- Validate the output automatically
- All while staying within resource bounds, preventing loops, and failing gracefully

That's CyberGuard. That's this project.
