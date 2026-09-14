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


"""Workflow. Pattern = Evaluator-Optimizer
Input task is first evaluated by a specialized agent, then optimized based on the evaluation feedback
Pros - Continuous improvement of outputs, can lead to higher quality results, allows for iterative refinement
Cons - Can be slower due to multiple iterations, requires careful design of evaluation criteria and feedback loop
Think of it as a student writing an essay. The student (agent) writes a draft (initial output), then a teacher (evaluator) reviews the essay and provides feedback on what can be improved. The student then takes that feedback and revises the essay (optimization) to produce a better final version. This process can repeat multiple times until the essay is of high quality.
this workflow is effective when we clearly defined evaluation criteria and when the task can benefit from iterative refinement. For example, if you have a task to generate a piece of creative writing, you can have an evaluator that assesses the creativity, coherence, and style of the writing, and then provides feedback to the generator to improve those aspects in the next iteration.
Use Cases:
1. Content generation - e.g. writing an article, creating marketing copy etc.
2. Code generation - generate code, then have an evaluator check for correctness, security vulnerabilities, performance issues etc. and provide feedback to optimize the code.
3. Design generation - generate a design, then have an evaluator check for aesthetics, usability, accessibility etc. and provide feedback to optimize the design.


"""

# Graph state
class State(TypedDict):
    ticker: str
    stock_analysis: str
    stock_analysis_feedback: str
    analysis_complete_or_not: str

def get_llm() -> ChatOllama:
    """
    Factory that returns a fresh LLM instance.
    temperature=0 → deterministic / reproducible outputs, critical for security tooling.
    Centralised here so swapping the model (e.g. to GPT-4o) is a one-line change.
    """
    return ChatOllama(model="qwen3-coder-next:latest", temperature=0)

# Schema for structured output to use in evaluation
class Feedback(BaseModel):
    grade: Literal["complete", "not complete"] = Field(
        description="Decide if the stock analysis is complete or not. Stock Analysis is considered complete if it covers all the following aspects: 1) company overview, 2) financial performance, 3) competitive landscape, 4) future outlook. 5) Bull Case Analysis. 6) Bear Case Analysis. If any of these aspects are missing or insufficiently covered, the analysis is not complete.",
    )
    feedback: str = Field(
        description="If the stock analysis is not complete. Stock Analysis is considered complete if it covers all the following aspects: 1) company overview, 2) financial performance, 3) competitive landscape, 4) future outlook. 5) Bull Case Analysis. 6) Bear Case Analysis. If any of these aspects are missing or insufficiently covered, the analysis is not complete. provide feedback on how to improve it.",
    )

# Augment the LLM with schema for structured output
llm = get_llm()
evaluator = llm.with_structured_output(Feedback)

def stock_analysis_generator(state: State) -> str:
    """
    LLM generates a stock analysis based on the input ticker.
    """
    llm = get_llm()
    if state.get("stock_analysis_feedback"):
        # Use the feedback to improve the analysis
        prompt = f"Here is the feedback on the previous stock analysis:\n{state['stock_analysis_feedback']}\n\nPlease provide an improved stock analysis for the company with ticker symbol {state['ticker']}. Make sure to cover all aspectsof stock invest analysis so that customer can make an informed investment decision. "
        response = llm.invoke([
        SystemMessage(content="You are a financial analyst that provides comprehensive stock analysis."),
        HumanMessage(content=prompt)
    ])
    else:
        # Initial analysis without feedback
        prompt = f"Please provide a comprehensive stock analysis for the company with ticker symbol {state['ticker']}. Provide Bull analysis only."
        response = llm.invoke([
            SystemMessage(content="You are a financial analyst that provides comprehensive stock analysis."),
            HumanMessage(content=prompt)
        ])
    return {"stock_analysis": response.content}

def stock_analysis_evaluator(state: State) -> str:
    """
    LLM evaluates the stock analysis and provides feedback on whether it's complete or not, and how to improve it if it's not complete.
    """
    response = evaluator.invoke([
        SystemMessage(content="You are a stock analysis evaluator. Your task is to evaluate the stock analysis provided by the generator and determine if it's complete or not. A stock analysis is considered complete if it covers all the following aspects: 1) company overview, 2) financial performance, 3) competitive landscape, 4) future outlook. 5) Bull Case Analysis. 6) Bear Case Analysis. 7) Cited Sources. If any of these aspects are missing or insufficiently covered, the analysis is not complete."),
        HumanMessage(content=f"This is the stock analysis:\n{state['stock_analysis']}\n\nIs this stock analysis complete? If not, please provide feedback on how to improve it.")
    ])

    return {
        "stock_analysis_feedback": response.feedback,
        "analysis_complete_or_not": response.grade
    }

# Conditional edge function to route back to stock_analysis_generator  or end based upon feedback from the stock_analysis_evaluator
def route_stock_analysis(state: State):
    if state["analysis_complete_or_not"] == "not complete":
        return "not complete"   # must match the key in add_conditional_edges dict
    else:
        return "complete"

# Build workflow
optimizer_builder = StateGraph(State)
optimizer_builder.add_node("stock_analysis_generator", stock_analysis_generator)
optimizer_builder.add_node("stock_analysis_evaluator", stock_analysis_evaluator)


optimizer_builder.add_edge(START, "stock_analysis_generator")
optimizer_builder.add_edge("stock_analysis_generator", "stock_analysis_evaluator")
optimizer_builder.add_conditional_edges(
    "stock_analysis_evaluator",
    route_stock_analysis ,
    {"complete": END,
     "not complete": "stock_analysis_generator"
     },
)
# Compile the workflow
optimizer_workflow = optimizer_builder.compile()

# Show the workflow
display(Image(optimizer_workflow.get_graph().draw_mermaid_png()))

# Invoke
state = optimizer_workflow.invoke({"ticker": "NBIS"})
print(state["stock_analysis_feedback"])
print(state["stock_analysis"])
