"""
Workflow Templates for Trend Intelligence Pipeline.

Provides pre-built workflow templates for common scenarios.
"""

from typing import Dict, Any, List, Optional
from uuid import uuid4

from trend_agent.workflow.interface import WorkflowDefinition
from trend_agent.workflow.steps import (
    CollectDataStep,
    DeduplicateStep,
    DetectLanguageStep,
    ClusterItemsStep,
    RankTopicsStep,
    GenerateSummariesStep,
    PersistTrendsStep,
)


def create_full_pipeline_workflow(
    name: str = "Full Trend Intelligence Pipeline",
    plugin_names: Optional[List[str]] = None,
    top_n_trends: int = 100,
    min_cluster_size: int = 3,
    similarity_threshold: float = 0.85,
) -> WorkflowDefinition:
    """
    Create a complete trend intelligence pipeline workflow.

    This workflow executes all steps:
    1. Collect data from sources
    2. Deduplicate items
    3. Detect languages
    4. Cluster into topics
    5. Rank topics into trends
    6. Generate summaries
    7. Persist to database

    Args:
        name: Workflow name
        plugin_names: List of plugin names to collect from
        top_n_trends: Number of top trends to keep
        min_cluster_size: Minimum cluster size for topics
        similarity_threshold: Similarity threshold for deduplication

    Returns:
        WorkflowDefinition
    """
    return WorkflowDefinition(
        id=uuid4(),
        name=name,
        description="Complete trend intelligence pipeline from collection to persistence",
        steps=[
            CollectDataStep(plugin_names=plugin_names),
            DeduplicateStep(similarity_threshold=similarity_threshold),
            DetectLanguageStep(),
            ClusterItemsStep(min_cluster_size=min_cluster_size),
            RankTopicsStep(top_n=top_n_trends),
            GenerateSummariesStep(),
            PersistTrendsStep(),
        ],
        parallel=False,
        continue_on_failure=False,
        timeout_seconds=3600,  # 1 hour
    )


def create_collection_only_workflow(
    name: str = "Data Collection Only",
    plugin_names: Optional[List[str]] = None,
) -> WorkflowDefinition:
    """
    Create a workflow that only collects data.

    Useful for testing data sources or collecting raw data for analysis.

    Args:
        name: Workflow name
        plugin_names: List of plugin names to collect from

    Returns:
        WorkflowDefinition
    """
    return WorkflowDefinition(
        id=uuid4(),
        name=name,
        description="Collect data from sources without processing",
        steps=[
            CollectDataStep(plugin_names=plugin_names),
        ],
        parallel=False,
        timeout_seconds=600,  # 10 minutes
    )


def create_processing_only_workflow(
    name: str = "Processing Only",
    top_n_trends: int = 100,
    min_cluster_size: int = 3,
    similarity_threshold: float = 0.85,
) -> WorkflowDefinition:
    """
    Create a workflow that processes existing data.

    Assumes items are already provided in the context.
    Useful for reprocessing collected data with different parameters.

    Args:
        name: Workflow name
        top_n_trends: Number of top trends to keep
        min_cluster_size: Minimum cluster size for topics
        similarity_threshold: Similarity threshold for deduplication

    Returns:
        WorkflowDefinition
    """
    return WorkflowDefinition(
        id=uuid4(),
        name=name,
        description="Process existing items through dedup, clustering, ranking, and summarization",
        steps=[
            DeduplicateStep(similarity_threshold=similarity_threshold),
            DetectLanguageStep(),
            ClusterItemsStep(min_cluster_size=min_cluster_size),
            RankTopicsStep(top_n=top_n_trends),
            GenerateSummariesStep(),
            PersistTrendsStep(),
        ],
        parallel=False,
        timeout_seconds=1800,  # 30 minutes
    )


def create_refresh_workflow(
    name: str = "Refresh Trends",
    top_n_trends: int = 100,
) -> WorkflowDefinition:
    """
    Create a workflow for refreshing existing trends.

    Re-ranks existing topics and regenerates summaries.
    Useful for periodic updates without full reprocessing.

    Args:
        name: Workflow name
        top_n_trends: Number of top trends to keep

    Returns:
        WorkflowDefinition
    """
    return WorkflowDefinition(
        id=uuid4(),
        name=name,
        description="Re-rank topics and refresh summaries",
        steps=[
            RankTopicsStep(top_n=top_n_trends),
            GenerateSummariesStep(),
            PersistTrendsStep(),
        ],
        parallel=False,
        timeout_seconds=900,  # 15 minutes
    )


def create_parallel_collection_workflow(
    name: str = "Parallel Data Collection",
    plugin_names: Optional[List[str]] = None,
) -> WorkflowDefinition:
    """
    Create a workflow that collects from multiple sources in parallel.

    Faster than sequential collection but may use more resources.

    Args:
        name: Workflow name
        plugin_names: List of plugin names to collect from

    Returns:
        WorkflowDefinition
    """
    # Create a separate collection step for each plugin
    steps = []

    if plugin_names:
        for plugin_name in plugin_names:
            steps.append(
                CollectDataStep(
                    name=f"collect_{plugin_name}",
                    plugin_names=[plugin_name],
                )
            )
    else:
        steps.append(CollectDataStep())

    return WorkflowDefinition(
        id=uuid4(),
        name=name,
        description="Collect data from multiple sources in parallel",
        steps=steps,
        parallel=True,  # Execute in parallel
        timeout_seconds=600,  # 10 minutes
    )


def create_custom_workflow(
    name: str,
    description: str,
    steps: List,
    parallel: bool = False,
    continue_on_failure: bool = False,
    timeout_seconds: Optional[int] = None,
) -> WorkflowDefinition:
    """
    Create a custom workflow with specified steps.

    Args:
        name: Workflow name
        description: Workflow description
        steps: List of workflow steps
        parallel: Execute steps in parallel
        continue_on_failure: Continue even if a step fails
        timeout_seconds: Workflow timeout

    Returns:
        WorkflowDefinition
    """
    return WorkflowDefinition(
        id=uuid4(),
        name=name,
        description=description,
        steps=steps,
        parallel=parallel,
        continue_on_failure=continue_on_failure,
        timeout_seconds=timeout_seconds,
    )


# ============================================================================
# Template Registry
# ============================================================================

WORKFLOW_TEMPLATES = {
    "full_pipeline": create_full_pipeline_workflow,
    "collection_only": create_collection_only_workflow,
    "processing_only": create_processing_only_workflow,
    "refresh": create_refresh_workflow,
    "parallel_collection": create_parallel_collection_workflow,
}


def get_template(template_name: str, **kwargs) -> WorkflowDefinition:
    """
    Get a workflow template by name.

    Args:
        template_name: Template name
        **kwargs: Template parameters

    Returns:
        WorkflowDefinition

    Raises:
        KeyError: If template not found

    Example:
        workflow = get_template("full_pipeline", top_n_trends=50)
    """
    if template_name not in WORKFLOW_TEMPLATES:
        raise KeyError(f"Workflow template '{template_name}' not found")

    template_func = WORKFLOW_TEMPLATES[template_name]
    return template_func(**kwargs)


def list_templates() -> List[str]:
    """
    List available workflow templates.

    Returns:
        List of template names
    """
    return list(WORKFLOW_TEMPLATES.keys())
