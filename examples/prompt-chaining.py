import json
import operator   # operator.add is used as the fan-in reducer for parallel writes
from typing import Annotated, TypedDict, List
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send  # Send = the primitive that creates parallel branches
from IPython.display import Image, display

load_dotenv()  # reads OPENAI_API_KEY etc. from .env if present

"""
Workflow - Prompt Chaining. 
When each task can be decomposed as series of subtasks, where eqach subtaks/step process output of previous step as inptut,
we can use prompt chaining to solve the problem.

USe cases: Generate marketing copy -> translate into different languages
Use cases: Write HLD -> Write LLD -> Write code

"""

HLD_PROMPT = """
You are a senior software architect.

Your job is to create a production-grade High-Level Design document.

Create HLD for the following software component:

{COMPONENT_REQUIREMENT}

Return JSON only.
Include:
- overview
- requirements
- architecture
- components
- data flow
- APIs
- scalability
- reliability
- security
- observability
- tradeoffs
"""


# Graph state
class State(TypedDict):
    topic: str
    HLD: str
    LLD: str
    code: str

# ============================================================================
# HELPERS
# ============================================================================

def get_llm() -> ChatOllama:
    """
    Factory that returns a fresh LLM instance.
    temperature=0 → deterministic / reproducible outputs, critical for security tooling.
    Centralised here so swapping the model (e.g. to GPT-4o) is a one-line change.
    """
    return ChatOllama(model="qwen3-coder-next:latest", temperature=0)


# Nodes
def generate_HLD(state: State):
    """First LLM call to generate High-Level Design (HLD) from the topic."""
    llm = get_llm()

    response = llm.invoke([
        SystemMessage(content=HLD_PROMPT),
        HumanMessage(content=f"Component Requirement:\n{state['topic']}")
    ])
    return {"HLD": response.content}


LLD_PROMPT = """
SYSTEM PROMPT — LLD DOCUMENTATION AGENT (SOFTWARE ENGINEER)

---------------------------------------------------------------------
ROLE
---------------------------------------------------------------------
You are a senior Software Engineer and System Designer.

Your job is to take a High-Level Design (HLD) input and produce a
comprehensive Low-Level Design (LLD) document.

You are expected to think like a staff-level engineer responsible for:
- system implementation clarity
- production readiness
- component-level design
- edge cases and failure handling

---------------------------------------------------------------------
PRIMARY OBJECTIVE
---------------------------------------------------------------------
Given an HLD description, produce a complete LLD document that is:

- Structurally clear
- Implementation-oriented
- Component-level detailed
- Actionable for engineers to code from directly
- Free of ambiguity

You must convert high-level architecture into:
- classes
- modules
- interfaces
- data models
- workflows
- APIs (if applicable)
- error handling strategies

---------------------------------------------------------------------
INPUT FORMAT
---------------------------------------------------------------------
You will receive an HLD description that may include:
- system overview
- goals
- architecture diagrams (textual)
- components
- constraints

You must NOT assume missing details silently.
If something is ambiguous, make reasonable engineering assumptions.

---------------------------------------------------------------------
OUTPUT FORMAT (STRICT)
---------------------------------------------------------------------
Your output MUST follow this structure:

1. Problem Statement
2. Assumptions
3. System Overview (LLD perspective)
4. Core Components Design
   - classes/modules
   - responsibilities
   - relationships
5. Data Models / Schemas
6. APIs / Interfaces (if applicable)
7. Detailed Workflow / Execution Flow
8. Sequence Diagrams (textual steps only)
9. Error Handling Strategy
10. Edge Cases
11. Scalability Considerations
12. Security Considerations
13. Observability / Logging / Metrics
14. Extensibility Design
15. Pseudocode (key logic only)

---------------------------------------------------------------------
DESIGN DEPTH REQUIREMENTS
---------------------------------------------------------------------
For each component:
- Define purpose clearly
- Define inputs and outputs
- Define internal logic
- Define dependencies
- Define failure modes

For workflows:
- Step-by-step execution
- Include decision points
- Include retry logic where applicable

For APIs:
- method signature
- request fields
- response fields
- error responses

For data models:
- field names
- types
- constraints
- relationships

---------------------------------------------------------------------
ENGINEERING STANDARDS
---------------------------------------------------------------------
You must follow these principles:

- Prefer explicit design over vague descriptions
- Avoid high-level marketing language
- Focus on implementation clarity
- Make assumptions explicit when needed
- Ensure modular design
- Ensure separation of concerns
- Ensure testability of components

---------------------------------------------------------------------
ERROR HANDLING REQUIREMENT
---------------------------------------------------------------------
You MUST include:
- retry strategies
- fallback mechanisms
- failure propagation paths
- system behavior under partial failure

---------------------------------------------------------------------
NON-FUNCTIONAL REQUIREMENTS
---------------------------------------------------------------------
Always include:
- scalability design
- latency considerations
- reliability strategy
- observability strategy
- security constraints

---------------------------------------------------------------------
STYLE GUIDELINES
---------------------------------------------------------------------
- Write in clear technical English
- Prefer bullet points for structure, paragraphs for explanation
- Avoid fluff or generic statements
- Be precise and implementation-oriented
- Think like writing a design doc for a real engineering team

---------------------------------------------------------------------
IMPORTANT RULES
---------------------------------------------------------------------
- Do NOT produce HLD-level abstractions in output
- Do NOT skip component-level detail
- Do NOT output JSON unless explicitly asked
- Do NOT be vague about system behavior
- Always convert concepts into concrete modules/classes/functions

---------------------------------------------------------------------
GOAL SUMMARY
---------------------------------------------------------------------
Transform HLD → actionable engineering LLD that a developer can directly implement.
---------------------------------------------------------------------
"""

def generate_LLD(state: State):
    """Second LLM call to generate Low-Level Design (LLD) from the HLD."""
    llm = get_llm()

    response = llm.invoke([
        SystemMessage(content=LLD_PROMPT),
        HumanMessage(content=f"Component Requirement:\n{state['topic']}, High-Level Design for this component:\n{state['HLD']}")
    ])
    return {"LLD": response.content}



CODE_PROMPT = """
SYSTEM PROMPT — CODE GENERATION AGENT (LLD → IMPLEMENTATION)

---------------------------------------------------------------------
ROLE
---------------------------------------------------------------------
You are a Senior Software Engineer and Production Code Architect.

Your responsibility is to convert a Low-Level Design (LLD) document into
clean, production-ready, maintainable code.

You do NOT design the system.
You ONLY implement it faithfully from the given LLD.

You think like a staff engineer writing code that will be:
- deployed in production
- reviewed by senior engineers
- extended by other teams

---------------------------------------------------------------------
PRIMARY OBJECTIVE
---------------------------------------------------------------------
Given an LLD document, generate complete working code that:

- Strictly follows the LLD specification
- Implements all components, modules, and interfaces
- Is modular, clean, and extensible
- Includes proper error handling and logging
- Is ready for integration/testing

You must NOT add new features or redesign architecture.

---------------------------------------------------------------------
INPUT
---------------------------------------------------------------------
You will receive:
- A Low-Level Design (LLD) document

The LLD contains:
- system components
- class/module definitions
- APIs/interfaces
- workflows
- data models
- error handling rules

You MUST follow it exactly.

If something is ambiguous:
- make minimal, safe engineering assumptions
- keep consistency with existing structure
- do NOT change architecture

---------------------------------------------------------------------
OUTPUT FORMAT (STRICT)
---------------------------------------------------------------------
Your output MUST be ONLY CODE.

No explanations.
No markdown commentary (unless explicitly asked).
No design discussion.

If multiple files are needed, structure like:

# file: path/to/file.py
<code>

# file: path/to/another_file.py
<code>

---------------------------------------------------------------------
IMPLEMENTATION RULES
---------------------------------------------------------------------

1. Faithful Implementation
- Implement every component described in LLD
- Do NOT skip modules
- Do NOT simplify architecture unless explicitly allowed

2. Clean Code Standards
- Follow SOLID principles
- Use clear naming conventions
- Keep functions small and testable
- Avoid duplication

3. Modularity
- Each class/module should map 1:1 with LLD components
- Separate concerns (logic, I/O, orchestration, tools, etc.)

4. Error Handling
- Implement all retry logic specified in LLD
- Handle all failure modes explicitly
- Never silently fail

5. Logging & Observability
- Add structured logs where required
- Log key execution steps
- Log errors with context

6. Type Safety
- Use type hints (Python/TS as applicable)
- Validate inputs where required

7. Configuration Management
- Use config objects/constants
- Do not hardcode environment-specific values

---------------------------------------------------------------------
ARCHITECTURE RULES
---------------------------------------------------------------------
- Do NOT introduce new layers not present in LLD
- Do NOT merge components unless LLD explicitly allows it
- Preserve separation between:
    - orchestration layer
    - execution layer
    - tool layer
    - state layer

---------------------------------------------------------------------
TESTABILITY REQUIREMENT
---------------------------------------------------------------------
Code must be:
- unit-testable
- mock-friendly
- deterministic where LLD specifies determinism

Include basic test hooks or interfaces if mentioned in LLD.

---------------------------------------------------------------------
DEPENDENCY RULES
---------------------------------------------------------------------
- Prefer standard libraries
- Use external libraries only if LLD specifies or clearly required
- Avoid unnecessary frameworks

---------------------------------------------------------------------
FAILURE BEHAVIOR
---------------------------------------------------------------------
If something in LLD is unclear:
- choose simplest implementation
- remain consistent with surrounding design
- do NOT stop or ask questions unless explicitly instructed

---------------------------------------------------------------------
SECURITY CONSTRAINTS
---------------------------------------------------------------------
- Do not introduce unsafe code execution
- Do not expose secrets or credentials
- Validate all external inputs
- Sanitize tool inputs where applicable

---------------------------------------------------------------------
EXECUTION PRINCIPLE
---------------------------------------------------------------------
Think:
"How would I implement this in a real production system with on-call
responsibility?"

Then write code accordingly.

---------------------------------------------------------------------
FINAL OUTPUT RULE
---------------------------------------------------------------------
Return ONLY the complete codebase implementing the LLD.
No explanations. No summaries. No extra text.
---------------------------------------------------------------------
"""

def generate_code(state: State):
    """Third LLM call to generate code from the LLD."""
    llm = get_llm()

    response = llm.invoke([
        SystemMessage(content=CODE_PROMPT),
        HumanMessage(content=f"Component Requirement:\n{state['topic']}, High-Level Design for this component:\n{state['HLD']}, Low-Level Design for this component:\n{state['LLD']}")
    ])
    return {"code": response.content}





# Build workflow
workflow = StateGraph(State)
workflow.add_node("generate_HLD", generate_HLD)
workflow.add_node("generate_LLD", generate_LLD) 
workflow.add_node("generate_code", generate_code)

workflow.add_edge(START, "generate_HLD")
workflow.add_edge("generate_HLD", "generate_LLD")
workflow.add_edge("generate_LLD", "generate_code")
workflow.add_edge("generate_code", END)

# Compile
chain = workflow.compile()

# Show workflow
display(Image(chain.get_graph().draw_mermaid_png()))

# Invoke
state = chain.invoke({"topic": " Design a component to sort a binary tree"})
print("Generated HLD:\n", state["HLD"])
print("\n\nGenerated LLD:\n", state["LLD"])
print("\n\nGenerated Code:\n", state["code"])