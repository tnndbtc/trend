"""
Workflow Engine for Trend Intelligence Platform.

Provides a flexible workflow orchestration system for building
and executing multi-step data processing pipelines.
"""

from trend_agent.workflow.interface import (
    WorkflowStep,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowContext,
    WorkflowEngine,
    WorkflowRepository,
    WorkflowStatus,
    StepStatus,
    StepResult,
)

from trend_agent.workflow.engine import SimpleWorkflowEngine

from trend_agent.workflow.steps import (
    CollectDataStep,
    DeduplicateStep,
    DetectLanguageStep,
    ClusterItemsStep,
    RankTopicsStep,
    GenerateSummariesStep,
    PersistTrendsStep,
)

from trend_agent.workflow.templates import (
    create_full_pipeline_workflow,
    create_collection_only_workflow,
    create_processing_only_workflow,
    create_refresh_workflow,
    create_parallel_collection_workflow,
    create_custom_workflow,
    get_template,
    list_templates,
    WORKFLOW_TEMPLATES,
)

__all__ = [
    # Core interfaces
    "WorkflowStep",
    "WorkflowDefinition",
    "WorkflowExecution",
    "WorkflowContext",
    "WorkflowEngine",
    "WorkflowRepository",
    "WorkflowStatus",
    "StepStatus",
    "StepResult",
    # Engine
    "SimpleWorkflowEngine",
    # Built-in steps
    "CollectDataStep",
    "DeduplicateStep",
    "DetectLanguageStep",
    "ClusterItemsStep",
    "RankTopicsStep",
    "GenerateSummariesStep",
    "PersistTrendsStep",
    # Templates
    "create_full_pipeline_workflow",
    "create_collection_only_workflow",
    "create_processing_only_workflow",
    "create_refresh_workflow",
    "create_parallel_collection_workflow",
    "create_custom_workflow",
    "get_template",
    "list_templates",
    "WORKFLOW_TEMPLATES",
]
