# Learning Resources

Comprehensive learning path for understanding agentic AI patterns and system design.

## Core Resources

### 1. Agentic AI Design Patterns (YouTube)

**Link**: https://www.youtube.com/watch?v=aHCDrAbH_go

**Duration**: 20 minutes

**What You'll Learn**:
- System architecture principles
- Workflow design and orchestration
- How to structure multi-agent systems
- Component composition patterns
- Scaling considerations

**When to Watch**: Start here for big picture understanding before diving into code.

### 2. Anthropic: Building Effective Agents

**Link**: https://www.anthropic.com/engineering/building-effective-agents

**Duration**: 30 minutes reading

**What You'll Learn**:
- Parallel execution pattern: Run agents concurrently
- Routing pattern: Direct tasks to specialized agents
- Prompt chaining: Sequential task decomposition
- Agentic loops: Evaluation and iterative improvement
- When to use each pattern

**When to Read**: Read after watching the YouTube video for concrete pattern definitions.

## How These Resources Map to Our Patterns

| Resource | Focus Area | Our Implementation |
|----------|-----------|------------------|
| YouTube Video | System design, orchestration, architecture | patterns/worker_orchestrator, overall structure |
| Anthropic Blog | Core patterns, when to use each | patterns/parallel, routing, prompt_chaining, eval_optimizer |

## Suggested Learning Order

### For Beginners

1. **Watch** YouTube video (20 min)
   - Understand what agentic systems are
   - Learn basic architecture concepts
   - Get context before diving into code

2. **Read** Anthropic blog (30 min)
   - Understand the 5 core patterns
   - Learn when to use each pattern
   - See decision framework

3. **Run** QUICKSTART.md (15 min)
   - Set up your environment
   - Run first pattern to see it in action
   - Verify everything works

4. **Explore** Pattern READMEs (30 min)
   - Read each pattern's documentation
   - Understand use cases and learnings
   - See ASCII workflow diagrams

5. **Review** Pattern Code (1-2 hours)
   - Read security_checks.py (parallel pattern)
   - Read department_router.py (routing pattern)
   - Read design_to_code.py (prompt chaining)
   - Read stock_analysis_optimizer.py (eval optimizer)
   - Understand LangGraph syntax

### For Experienced Engineers

1. **Skim** YouTube video (10 min)
   - Focus on architecture decisions
   - Skip basics you already know

2. **Read** Anthropic blog (20 min)
   - Focus on pattern selection criteria
   - Review use case examples

3. **Dive** Into Pattern Code (30 min)
   - Study LangGraph StateGraph usage
   - Review conditional edges and routing logic
   - Examine node design patterns

4. **Contribute** Your Own Pattern
   - See docs/contributing.md
   - Implement a new pattern
   - Share back with community

## Additional Learning Resources

### LangChain & LangGraph

- **LangChain Python Docs**: https://python.langchain.com
- **LangGraph Docs**: https://langgraph.js.org
- **LLM Integration**: Learn how to swap models (OpenAI, Anthropic, local via Ollama)

### Ollama (Local LLM)

- **Ollama Website**: https://ollama.ai
- **Model Repository**: https://ollama.ai/library
- **Documentation**: Installation and configuration guides

### DeepAgents

- **GitHub**: https://github.com/stanfordnlp/deepagents
- **Documentation**: Multi-agent coordination patterns

### LangSmith (Observability)

- **Website**: https://smith.langchain.com
- **Documentation**: Trace inspection and debugging

## Key Concepts You'll Learn

### From YouTube Video

- What is an agentic system?
- Components: LLM, tools, memory, planning
- Synchronous vs asynchronous execution
- Orchestration patterns
- Scaling multi-agent systems

### From Anthropic Blog

1. **Parallel Execution Pattern**
   - Run multiple independent tasks concurrently
   - Aggregate results
   - Use case: Security screening, multi-perspective analysis

2. **Routing Pattern**
   - Classify input and direct to appropriate handler
   - Use structured output for deterministic routing
   - Use case: Customer support, request dispatch

3. **Prompt Chaining Pattern**
   - Break complex task into sequential steps
   - Each step builds on previous output
   - Use case: Design-to-code, content generation

4. **Agentic Loop (Eval Optimizer) Pattern**
   - Generate output
   - Evaluate against criteria
   - Iterate with feedback until complete
   - Use case: Code generation, analysis refinement

5. **Worker Orchestrator Pattern**
   - Distribute work across multiple workers
   - Manage task queue and coordination
   - Use case: Large-scale processing, map-reduce jobs

## Practice Exercises

### Exercise 1: Run Parallel Pattern

1. Follow QUICKSTART.md to set up
2. Run: `python3 patterns/parallel/security_checks.py`
3. Modify the security checks (add malware_score, etc.)
4. Observe how parallel execution changes behavior

### Exercise 2: Create Your Own Routing

1. Read department_router.py
2. Create a new routing pattern (e.g., route support tickets)
3. Add new departments to the routing logic
4. See docs/contributing.md for submission guidelines

### Exercise 3: Implement Prompt Chaining

1. Read design_to_code.py
2. Create a prompt chaining pattern for a different domain
3. Examples: API Design -> Implementation, Recipe -> Shopping List -> Meal Plan
4. Share your pattern with the community

### Exercise 4: Build an Eval Loop

1. Read stock_analysis_optimizer.py
2. Create an evaluator for a different task (code quality, essay quality, etc.)
3. Implement the feedback loop
4. Test with Ollama

## Troubleshooting & Common Questions

**Q: Do I need to understand all patterns before starting?**
A: No. Start with parallel and routing patterns as they're simplest. Work up to eval optimizer and worker orchestrator.

**Q: Can I use different LLMs besides Ollama?**
A: Yes. Any LangChain-supported LLM works. Update .env and the `get_llm()` function in patterns.

**Q: How long does it take to understand all patterns?**
A: 2-3 hours for a complete overview. 1-2 days to implement your own pattern.

**Q: What if Ollama crashes while learning?**
A: See docs/setup.md troubleshooting section. Usually just restart Ollama or free up system memory.

## Next Steps

1. Choose your starting point above
2. Follow the learning order recommended for your experience level
3. Run patterns as you learn
4. Modify patterns to experiment
5. Contribute your own pattern when ready

## Questions or Feedback?

If you have suggestions for improving these learning resources:

1. Open a GitHub issue
2. Share what worked and what didn't
3. Suggest additional resources or exercises
4. Help improve documentation for others

## Resources Checklist

Print or bookmark these as you learn:

- [ ] YouTube: Agentic AI Design Patterns
- [ ] Anthropic: Building Effective Agents
- [ ] QUICKSTART.md
- [ ] docs/setup.md
- [ ] Individual pattern READMEs
- [ ] docs/contributing.md (when ready to contribute)

Good luck on your agentic AI journey!
