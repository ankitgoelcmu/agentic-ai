import json
import operator   # operator.add is used as the fan-in reducer for parallel writes
from typing import Annotated, TypedDict, List
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send  # Send = the primitive that creates parallel branches
from IPython.display import Image, display
from pydantic import BaseModel, Field

from typing_extensions import Literal

load_dotenv()  # reads OPENAI_API_KEY etc. from .env if present

"""
Workflow. Pattern = Router
Input task can be classiefied
Router wil route to appropiate specialized sub agent to perform the task
Pros - One agent is not overwhelmed with all the knowledge, each agent can specialize in one type of task, easier to maintain and update
Cons - Requires good classification of tasks, if task is misclassified it can lead to poor performance 
Think of it as a traffic routing system. If you have a task, you need to figure out which lane (agent) it should go down. If you route it correctly, it gets to the destination efficiently. If you route it incorrectly, it might get lost or take a long time to get there.
This is based on the fact that different type of tasks required diffrent specilaed agents, rather than relying on ane agent for everything. For example, if the task is to generate code, it should be routed to a code generation agent that is specialized in that, rather than a general purpose agent that might not be as good at it.
routing ensures that each input is processed by the most suitable component, leading to improved efficiency, accuracy, and resource utilization.

Use cases: Direct user query to apprpiate department == finance, tech support, HR etc. , In software architecture, routing can be used to direct requests to the appropriate microservice based on the type of request, In machine learning pipelines, routing can be used to direct data to the appropriate model or processing step based on the characteristics of the data.
When to use routing: 
1.Diverse Input Types:  diffrent queries require diffrent specialized agents to handle.
Resource Optimization: You want to assign simple queries to cost-effective processors while routing complex requests to advanced systems
Performance Optimization: You need to balance load and ensure optimal response times across different query types
2. 

"""
CLASSIFIER_PROMPT = """
You are an intelligent request routing system.

Your task is to classify the user query into exactly ONE of the following departments:

- HR
- FINANCE
- TECH_SUPPORT

---------------------------------------------------------------------
CLASSIFICATION RULES
---------------------------------------------------------------------

1. HR (Human Resources)
Route to HR if the query is related to:
- Hiring, recruitment, interviews
- Payroll policies, salary structure (non-financial calculations)
- Leave, attendance, holidays
- Employee benefits, onboarding, offboarding
- Workplace policies, code of conduct
- Internal employee relations

2. FINANCE
Route to FINANCE if the query is related to:
- Invoices, billing, payments
- Budgets, expenses, reimbursements
- Accounting, bookkeeping
- Taxation, financial reporting
- Pricing, cost analysis
- Refunds and transaction issues

3. TECH_SUPPORT
Route to TECH_SUPPORT if the query is related to:
- Software bugs or errors
- System outages or performance issues
- API issues, integration problems
- Login/authentication problems
- Hardware or device troubleshooting
- Technical configuration or setup

---------------------------------------------------------------------
DECISION RULES
---------------------------------------------------------------------

- Choose ONLY one department (no multiple labels).
- If the query spans multiple domains, choose the PRIMARY intent.
- If ambiguous:
    → prefer TECH_SUPPORT for system/technical issues
    → prefer FINANCE for money-related issues
    → otherwise default to HR for internal policy questions
- Do NOT explain your reasoning.
- Output ONLY the department name exactly as: HR, FINANCE, or TECH_SUPPORT

---------------------------------------------------------------------
OUTPUT FORMAT (STRICT)
---------------------------------------------------------------------

Return only one word:
HR
FINANCE
or
TECH_SUPPORT

No additional text, punctuation, or explanation.
"""

def get_llm() -> ChatOllama:
    """
    Factory that returns a fresh LLM instance.
    temperature=0 → deterministic / reproducible outputs, critical for security tooling.
    Centralised here so swapping the model (e.g. to GPT-4o) is a one-line change.
    """
    return ChatOllama(model="qwen3-coder-next:latest", temperature=0)


# Schema for structured output to use as routing logic
class Route(BaseModel):
    step: Literal["HR", "FINANCE", "TECH_SUPPORT"] = Field(
        None, description="The next step in the routing process. Route to HR, FINANCE, or TECH_SUPPORT based on the query."
    )

# Augment the LLM with schema for structured output
llm = get_llm()
router = llm.with_structured_output(Route)

# State
class State(TypedDict):
    input: str
    decision: str
    output: str


def llm_call_router(state: State):
    """Route the input to the appropriate node"""

    # Run the augmented LLM with structured output to serve as routing logic
    decision = router.invoke(
        [
            SystemMessage(
                content=CLASSIFIER_PROMPT
            ),
            HumanMessage(content=state["input"]),
        ]
    )

    return {"decision": decision.step}



def llm_call_hr(state: State):
    """Simulate HR processing the query"""
    return {"output": f"HR processed the query: {state['input']}"}

def llm_call_finance(state: State):
    """Simulate Finance processing the query"""
    return {"output": f"Finance processed the query: {state['input']}"}

def llm_call_tech_support(state: State):
    """Simulate Tech Support processing the query"""
    return {"output": f"Tech Support processed the query: {state['input']}"}    


# Conditional edge function to route to the appropriate node
def route_decision(state: State):
     # Return the node name you want to visit next
    if state["decision"] == "HR":
        return "llm_call_hr"
    elif state["decision"] == "FINANCE":
        return "llm_call_finance"
    elif state["decision"] == "TECH_SUPPORT":
        return "llm_call_tech_support"
    else:
        raise ValueError(f"Invalid decision: {state['decision']}")
    
# Build the graph
router_graph = StateGraph(State)
router_graph.add_node("llm_call_router", llm_call_router)
router_graph.add_node("llm_call_hr", llm_call_hr)
router_graph.add_node("llm_call_finance", llm_call_finance)
router_graph.add_node("llm_call_tech_support", llm_call_tech_support)

#add edges with conditional routing
router_graph.add_edge(START, "llm_call_router")
router_graph.add_conditional_edges(
    "llm_call_router",
    route_decision,
    { # Name returned by route_decision : Name of next node to visit
        "llm_call_hr": "llm_call_hr",
        "llm_call_finance": "llm_call_finance",
        "llm_call_tech_support": "llm_call_tech_support"
    }
)
router_graph.add_edge("llm_call_hr", END)
router_graph.add_edge("llm_call_finance", END)
router_graph.add_edge("llm_call_tech_support", END)

#complete graph
router_workflow = router_graph.compile()
#display graph
display(Image(router_workflow.get_graph().draw_mermaid_png()))

# Invoke the workflow with different inputs to see routing in action
state = router_workflow.invoke({"input": "I have a question about my Taxes MONEY."})
print(state["decision"])  # Should be "FINANCE"
print(state["output"])  # Should be processed by Finance





