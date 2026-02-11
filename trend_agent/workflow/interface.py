"""
Workflow Engine Interface.

Defines the core abstractions for building and executing workflows
in the Trend Intelligence Platform.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4


class WorkflowStatus(Enum):
    """Workflow execution status."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """Workflow step execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class WorkflowContext:
    """
    Execution context passed between workflow steps.

    Contains input data, output data, and shared state.
    """

    workflow_id: UUID
    execution_id: UUID
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    state: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class StepResult:
    """Result of a workflow step execution."""

    status: StepStatus
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowStep(ABC):
    """
    Abstract base class for workflow steps.

    Each step represents a single unit of work in a workflow.
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        retry_count: int = 0,
        timeout_seconds: Optional[int] = None,
    ):
        """
        Initialize workflow step.

        Args:
            name: Step name
            description: Step description
            retry_count: Number of retries on failure
            timeout_seconds: Execution timeout
        """
        self.name = name
        self.description = description
        self.retry_count = retry_count
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    async def execute(self, context: WorkflowContext) -> StepResult:
        """
        Execute the workflow step.

        Args:
            context: Workflow execution context

        Returns:
            StepResult with status and outputs
        """
        pass

    async def on_success(self, context: WorkflowContext) -> None:
        """
        Hook called when step succeeds.

        Args:
            context: Workflow execution context
        """
        pass

    async def on_failure(self, context: WorkflowContext, error: Exception) -> None:
        """
        Hook called when step fails.

        Args:
            context: Workflow execution context
            error: Exception that caused the failure
        """
        pass

    async def should_skip(self, context: WorkflowContext) -> bool:
        """
        Determine if step should be skipped.

        Args:
            context: Workflow execution context

        Returns:
            True if step should be skipped
        """
        return False


@dataclass
class WorkflowDefinition:
    """
    Workflow definition.

    Defines the sequence of steps and their dependencies.
    """

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    description: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    inputs: Dict[str, Any] = field(default_factory=dict)
    parallel: bool = False  # Execute steps in parallel
    continue_on_failure: bool = False  # Continue even if a step fails
    timeout_seconds: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WorkflowExecution:
    """
    Workflow execution state.

    Tracks the progress of a workflow execution.
    """

    id: UUID = field(default_factory=uuid4)
    workflow_id: UUID = field(default_factory=uuid4)
    status: WorkflowStatus = WorkflowStatus.PENDING
    context: WorkflowContext = field(default_factory=lambda: WorkflowContext(
        workflow_id=uuid4(),
        execution_id=uuid4(),
    ))
    current_step_index: int = 0
    step_results: Dict[str, StepResult] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class WorkflowEngine(ABC):
    """
    Abstract workflow execution engine.

    Responsible for executing workflows and managing their lifecycle.
    """

    @abstractmethod
    async def execute(
        self,
        workflow: WorkflowDefinition,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> WorkflowExecution:
        """
        Execute a workflow.

        Args:
            workflow: Workflow definition
            inputs: Optional input parameters

        Returns:
            WorkflowExecution with results
        """
        pass

    @abstractmethod
    async def pause(self, execution_id: UUID) -> None:
        """
        Pause a running workflow.

        Args:
            execution_id: Workflow execution ID
        """
        pass

    @abstractmethod
    async def resume(self, execution_id: UUID) -> None:
        """
        Resume a paused workflow.

        Args:
            execution_id: Workflow execution ID
        """
        pass

    @abstractmethod
    async def cancel(self, execution_id: UUID) -> None:
        """
        Cancel a running workflow.

        Args:
            execution_id: Workflow execution ID
        """
        pass

    @abstractmethod
    async def get_execution(self, execution_id: UUID) -> Optional[WorkflowExecution]:
        """
        Get workflow execution status.

        Args:
            execution_id: Workflow execution ID

        Returns:
            WorkflowExecution or None if not found
        """
        pass

    @abstractmethod
    async def list_executions(
        self,
        workflow_id: Optional[UUID] = None,
        status: Optional[WorkflowStatus] = None,
        limit: int = 100,
    ) -> List[WorkflowExecution]:
        """
        List workflow executions.

        Args:
            workflow_id: Filter by workflow ID
            status: Filter by status
            limit: Maximum number of results

        Returns:
            List of workflow executions
        """
        pass


class WorkflowRepository(ABC):
    """
    Abstract repository for workflow definitions.

    Handles persistence of workflow definitions.
    """

    @abstractmethod
    async def save(self, workflow: WorkflowDefinition) -> None:
        """
        Save a workflow definition.

        Args:
            workflow: Workflow definition
        """
        pass

    @abstractmethod
    async def get(self, workflow_id: UUID) -> Optional[WorkflowDefinition]:
        """
        Get a workflow definition.

        Args:
            workflow_id: Workflow ID

        Returns:
            WorkflowDefinition or None if not found
        """
        pass

    @abstractmethod
    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WorkflowDefinition]:
        """
        List workflow definitions.

        Args:
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of workflow definitions
        """
        pass

    @abstractmethod
    async def delete(self, workflow_id: UUID) -> None:
        """
        Delete a workflow definition.

        Args:
            workflow_id: Workflow ID
        """
        pass


# ============================================================================
# Helper Types
# ============================================================================

StepFactory = Callable[..., WorkflowStep]
"""Factory function that creates workflow steps."""

WorkflowTemplate = Callable[[Dict[str, Any]], WorkflowDefinition]
"""Template function that creates workflow definitions."""
