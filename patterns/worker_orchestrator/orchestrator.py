"""
Worker Orchestrator Pattern Implementation

A central orchestrator distributes independent subtasks to a pool of worker agents,
collects results, and aggregates them. Useful for parallel processing, fault tolerance,
and load balancing.

Example: Analyze multiple documents in parallel using worker agents.
"""

import json
from typing import Any, TypedDict, Optional, List
from dataclasses import dataclass
from enum import Enum

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import START, END, StateGraph
from langgraph.types import Send


class TaskStatus(str, Enum):
    """Status of a task in the queue."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """A single task to be processed by a worker."""
    task_id: str
    content: str
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class WorkerResult:
    """Result returned by a worker."""
    task_id: str
    status: TaskStatus
    result: Optional[str] = None
    error: Optional[str] = None


class OrchestratorState(TypedDict, total=False):
    """State for the orchestrator workflow."""
    tasks: List[Task]
    worker_results: List[WorkerResult]
    aggregated_result: Optional[str]
    completed: bool


# =============================================================================
# WORKER: Processes a single task
# =============================================================================

_worker_llm = init_chat_model(
    model="anthropic:claude-haiku-4-5-20251001",
    temperature=0
)

_WORKER_SYSTEM = (
    "You are a task worker. Analyze and process the given content. "
    "Be concise and focused. Extract key insights or perform the requested operation."
)


def worker(task: Task) -> WorkerResult:
    """
    Process a single task using an LLM worker.

    Args:
        task: Task to process

    Returns:
        WorkerResult with the processing outcome
    """
    try:
        response = _worker_llm.invoke([
            SystemMessage(content=_WORKER_SYSTEM),
            HumanMessage(content=task.content)
        ])

        return WorkerResult(
            task_id=task.task_id,
            status=TaskStatus.COMPLETED,
            result=response.content
        )
    except Exception as e:
        return WorkerResult(
            task_id=task.task_id,
            status=TaskStatus.FAILED,
            error=str(e)
        )


# =============================================================================
# ORCHESTRATOR: Distributes work and aggregates results
# =============================================================================

_aggregator_llm = init_chat_model(
    model="anthropic:claude-haiku-4-5-20251001",
    temperature=0
)

_AGGREGATOR_SYSTEM = (
    "You are an aggregator. Given results from multiple workers processing "
    "different tasks, synthesize them into a cohesive summary. "
    "Identify key themes, patterns, and insights across all results."
)


def orchestrator_distribute(state: OrchestratorState) -> list[Send]:
    """
    Orchestrator distributes tasks to workers.

    This node receives a list of tasks and dispatches them as parallel work items.
    Each task will be processed by a worker concurrently.
    """
    tasks = state.get("tasks", [])

    # Dispatch each task to a worker as a parallel Send
    return [Send("worker_node", {"task": task}) for task in tasks]


def worker_node(task: Task) -> dict:
    """
    Worker node that processes a single task.
    This is called in parallel for each task via Send.
    """
    result = worker(task)
    return {"worker_results": [result]}


def orchestrator_aggregate(state: OrchestratorState) -> dict:
    """
    Orchestrator aggregates results from all workers.

    Receives all worker results and synthesizes them using an LLM.
    """
    results = state.get("worker_results", [])

    if not results:
        return {"aggregated_result": "No results to aggregate", "completed": True}

    # Format results for the aggregator
    results_text = "\n\n".join([
        f"Task {r.task_id}:\nStatus: {r.status.value}\n"
        f"Result: {r.result if r.result else 'N/A'}\n"
        f"Error: {r.error if r.error else 'None'}"
        for r in results
    ])

    # Aggregate using LLM
    try:
        response = _aggregator_llm.invoke([
            SystemMessage(content=_AGGREGATOR_SYSTEM),
            HumanMessage(content=f"Aggregate these worker results:\n\n{results_text}")
        ])
        aggregated = response.content
    except Exception as e:
        aggregated = f"Aggregation failed: {str(e)}"

    return {
        "aggregated_result": aggregated,
        "completed": True
    }


def build_orchestrator_graph():
    """Build the orchestrator workflow graph."""
    graph = StateGraph(OrchestratorState)

    # Add nodes
    graph.add_node("orchestrator_distribute", orchestrator_distribute)
    graph.add_node("worker_node", worker_node)
    graph.add_node("orchestrator_aggregate", orchestrator_aggregate)

    # Define flow
    graph.add_edge(START, "orchestrator_distribute")
    # Distribute sends to worker_node in parallel, then automatically routes to next
    graph.add_edge("worker_node", "orchestrator_aggregate")
    graph.add_edge("orchestrator_aggregate", END)

    return graph.compile()


# =============================================================================
# DEMO: Document processing example
# =============================================================================

def create_demo_tasks() -> List[Task]:
    """Create sample tasks for demonstration."""
    documents = [
        {
            "id": "doc_1",
            "content": "The quantum computer achieved a 99.9% accuracy rate in solving "
                      "optimization problems, marking a breakthrough in computational physics."
        },
        {
            "id": "doc_2",
            "content": "Climate models predict a 2.5°C increase in global temperatures by 2100 "
                      "if current emission trends continue. Scientists recommend immediate action."
        },
        {
            "id": "doc_3",
            "content": "The new AI safety framework proposes three pillars: transparency, "
                      "accountability, and robustness. Industry leaders have started adoption."
        },
    ]

    tasks = [
        Task(
            task_id=doc["id"],
            content=f"Analyze this document and extract: 1) Main topic, 2) Key findings, "
                   f"3) Significance. Document: {doc['content']}",
            metadata={"source": "research_docs"}
        )
        for doc in documents
    ]

    return tasks


def run_demo():
    """Run the orchestrator demo."""
    print("\n" + "=" * 70)
    print("WORKER ORCHESTRATOR PATTERN DEMO")
    print("=" * 70)

    # Create tasks
    tasks = create_demo_tasks()
    print(f"\n📋 Created {len(tasks)} tasks for processing:")
    for task in tasks:
        print(f"  - {task.task_id}")

    # Build and execute orchestrator
    print("\n🚀 Distributing tasks to workers...")
    orchestrator = build_orchestrator_graph()

    initial_state = {
        "tasks": tasks,
        "worker_results": [],
        "aggregated_result": None,
        "completed": False
    }

    result = orchestrator.invoke(initial_state)

    # Display results
    print("\n✅ WORKER RESULTS:")
    for worker_result in result.get("worker_results", []):
        print(f"\n  Task: {worker_result.task_id}")
        print(f"  Status: {worker_result.status.value}")
        if worker_result.result:
            print(f"  Result:\n{worker_result.result}")
        if worker_result.error:
            print(f"  Error: {worker_result.error}")

    print("\n📊 AGGREGATED RESULT:")
    print(f"{result.get('aggregated_result', 'N/A')}")
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    os.environ.setdefault("LANGSMITH_TRACING", "false")  # Set to "true" to trace

    run_demo()
