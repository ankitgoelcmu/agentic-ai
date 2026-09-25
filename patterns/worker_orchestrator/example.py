"""
Worker Orchestrator Pattern - Usage Examples

Shows different ways to use the orchestrator for various tasks:
1. Document analysis
2. Data partitioning
3. Batch processing
4. Error handling
"""

import os
from dotenv import load_dotenv
from orchestrator import (
    Task, OrchestratorState, build_orchestrator_graph,
    orchestrator_distribute, orchestrator_aggregate, worker
)


load_dotenv()
os.environ.setdefault("LANGSMITH_TRACING", "false")


# =============================================================================
# EXAMPLE 1: Parallel Document Analysis
# =============================================================================

def example_document_analysis():
    """
    Use case: Analyze multiple documents in parallel.
    Each worker extracts key information from a different document.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Parallel Document Analysis")
    print("=" * 70)

    # Create tasks for different documents
    tasks = [
        Task(
            task_id="doc_sentiment_1",
            content="Analyze sentiment: 'The new product launch was incredibly successful. "
                   "Customer feedback has been overwhelmingly positive.'",
            metadata={"type": "sentiment_analysis"}
        ),
        Task(
            task_id="doc_summary_2",
            content="Summarize: 'The machine learning model achieved 95% accuracy on the test set. "
                   "After fine-tuning on domain-specific data, it improved to 97.5%.'",
            metadata={"type": "summarization"}
        ),
        Task(
            task_id="doc_extraction_3",
            content="Extract entities: 'Google announced a $25M investment in AI safety research. "
                   "The initiative will run through 2025.'",
            metadata={"type": "entity_extraction"}
        ),
    ]

    # Run orchestrator
    orchestrator = build_orchestrator_graph()
    result = orchestrator.invoke({
        "tasks": tasks,
        "worker_results": [],
        "aggregated_result": None,
        "completed": False
    })

    print("\nWorker Results:")
    for wr in result["worker_results"]:
        print(f"\n{wr.task_id}: {wr.status.value}")
        if wr.result:
            print(f"Result: {wr.result[:200]}...")

    print("\nAggregated Insights:")
    print(result["aggregated_result"][:300] + "...")


# =============================================================================
# EXAMPLE 2: Data Partitioning and Analysis
# =============================================================================

def example_data_partitioning():
    """
    Use case: Partition a large dataset into chunks and analyze each chunk.
    Workers process different partitions in parallel.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Data Partitioning and Analysis")
    print("=" * 70)

    # Simulate dataset partitions
    partitions = [
        "Partition 1: Q1 Sales (Jan-Mar): Revenue $2.3M, Growth 15%, Top region: US East",
        "Partition 2: Q2 Sales (Apr-Jun): Revenue $2.8M, Growth 22%, Top region: EMEA",
        "Partition 3: Q3 Sales (Jul-Sep): Revenue $3.1M, Growth 11%, Top region: APAC",
    ]

    tasks = [
        Task(
            task_id=f"partition_{i}",
            content=f"Analyze this sales data partition and identify: "
                   f"1) Revenue trend, 2) Growth rate, 3) Top performing region. "
                   f"Data: {partition}",
            metadata={"partition_id": i}
        )
        for i, partition in enumerate(partitions)
    ]

    # Run orchestrator
    orchestrator = build_orchestrator_graph()
    result = orchestrator.invoke({
        "tasks": tasks,
        "worker_results": [],
        "aggregated_result": None,
        "completed": False
    })

    print("\nPartition Analysis Results:")
    for wr in result["worker_results"]:
        print(f"\n{wr.task_id}:")
        if wr.result:
            print(f"{wr.result[:250]}...")

    print("\nAggregated Insights (Cross-Partition Analysis):")
    print(result["aggregated_result"][:400] + "...")


# =============================================================================
# EXAMPLE 3: Batch Processing with Mixed Task Types
# =============================================================================

def example_batch_processing():
    """
    Use case: Process a batch of heterogeneous tasks.
    Workers handle different task types (translation, summarization, classification, etc.)
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Batch Processing with Mixed Task Types")
    print("=" * 70)

    tasks = [
        Task(
            task_id="task_translate",
            content="Translate to French: 'Artificial intelligence is transforming industries.'",
            metadata={"type": "translation"}
        ),
        Task(
            task_id="task_classify",
            content="Classify sentiment (positive/negative/neutral): "
                   "'I am disappointed with the service but the product quality is excellent.'",
            metadata={"type": "classification"}
        ),
        Task(
            task_id="task_qa",
            content="Answer: What are the three key benefits of machine learning mentioned in "
                   "'Machine learning enables automation, improved decision-making, and cost reduction.'?",
            metadata={"type": "question_answering"}
        ),
    ]

    # Run orchestrator
    orchestrator = build_orchestrator_graph()
    result = orchestrator.invoke({
        "tasks": tasks,
        "worker_results": [],
        "aggregated_result": None,
        "completed": False
    })

    print("\nTask Processing Results:")
    for wr in result["worker_results"]:
        print(f"\n{wr.task_id} ({wr.status.value}):")
        if wr.result:
            print(f"Output: {wr.result[:200]}...")

    print("\nCross-Task Summary:")
    print(result["aggregated_result"][:350] + "...")


# =============================================================================
# EXAMPLE 4: Error Handling and Resilience
# =============================================================================

def example_with_invalid_tasks():
    """
    Use case: Demonstrate error handling when some tasks fail.
    The orchestrator collects both successful and failed results.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Error Handling and Resilience")
    print("=" * 70)

    tasks = [
        Task(
            task_id="valid_task_1",
            content="Summarize: 'AI safety is crucial for responsible AI development.'",
        ),
        Task(
            task_id="valid_task_2",
            content="Extract: 'The study involved 1000 participants from 15 countries.'",
        ),
        Task(
            task_id="edge_case_3",
            content="Process this very complex and unusual request that might cause issues.",
            metadata={"difficult": True}
        ),
    ]

    # Run orchestrator
    orchestrator = build_orchestrator_graph()
    result = orchestrator.invoke({
        "tasks": tasks,
        "worker_results": [],
        "aggregated_result": None,
        "completed": False
    })

    print("\nTask Results (with Error Handling):")
    successful = 0
    failed = 0
    for wr in result["worker_results"]:
        status_symbol = "✅" if wr.status.value == "completed" else "❌"
        print(f"{status_symbol} {wr.task_id}: {wr.status.value}")
        if wr.result:
            print(f"   Result: {wr.result[:150]}...")
        if wr.error:
            print(f"   Error: {wr.error[:150]}")

        if wr.status.value == "completed":
            successful += 1
        else:
            failed += 1

    print(f"\nSummary: {successful} successful, {failed} failed out of {len(tasks)} total")
    print("\nAggregated Results (handles partial failures):")
    print(result["aggregated_result"][:350] + "...")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("\n🎯 WORKER ORCHESTRATOR PATTERN - EXAMPLES")
    print("Shows different use cases and patterns\n")

    # Run all examples
    example_document_analysis()
    example_data_partitioning()
    example_batch_processing()
    example_with_invalid_tasks()

    print("\n" + "=" * 70)
    print("✅ All examples completed!")
    print("=" * 70 + "\n")
