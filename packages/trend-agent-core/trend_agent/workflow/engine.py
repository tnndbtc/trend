"""
Workflow Execution Engine.

Executes workflow definitions, managing step execution, retries, and state.
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

from trend_agent.workflow.interface import (
    WorkflowEngine,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowStatus,
    WorkflowContext,
    StepStatus,
    StepResult,
    WorkflowStep,
)

logger = logging.getLogger(__name__)


class SimpleWorkflowEngine(WorkflowEngine):
    """
    Simple workflow execution engine.

    Executes workflows sequentially or in parallel with support for:
    - Retries
    - Timeouts
    - Error handling
    - State management
    """

    def __init__(self):
        """Initialize workflow engine."""
        self._executions: Dict[UUID, WorkflowExecution] = {}

    async def execute(
        self,
        workflow: WorkflowDefinition,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> WorkflowExecution:
        """Execute a workflow."""
        # Create execution
        execution = WorkflowExecution(
            workflow_id=workflow.id,
            status=WorkflowStatus.PENDING,
        )

        # Initialize context
        execution.context = WorkflowContext(
            workflow_id=workflow.id,
            execution_id=execution.id,
            inputs=inputs or workflow.inputs,
            started_at=datetime.utcnow(),
        )

        # Store execution
        self._executions[execution.id] = execution

        # Start execution
        execution.status = WorkflowStatus.RUNNING
        execution.started_at = datetime.utcnow()

        try:
            if workflow.parallel:
                await self._execute_parallel(workflow, execution)
            else:
                await self._execute_sequential(workflow, execution)

            # Mark as completed
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.context.completed_at = datetime.utcnow()

            logger.info(
                f"Workflow {workflow.name} completed successfully. "
                f"Execution ID: {execution.id}"
            )

        except Exception as e:
            # Mark as failed
            execution.status = WorkflowStatus.FAILED
            execution.completed_at = datetime.utcnow()
            execution.error = str(e)

            logger.error(
                f"Workflow {workflow.name} failed: {e}. "
                f"Execution ID: {execution.id}",
                exc_info=True
            )

        return execution

    async def _execute_sequential(
        self,
        workflow: WorkflowDefinition,
        execution: WorkflowExecution,
    ) -> None:
        """Execute workflow steps sequentially."""
        for index, step in enumerate(workflow.steps):
            execution.current_step_index = index

            # Check if execution was cancelled
            if execution.status == WorkflowStatus.CANCELLED:
                logger.info(f"Workflow execution {execution.id} was cancelled")
                break

            # Check if execution was paused
            while execution.status == WorkflowStatus.PAUSED:
                await asyncio.sleep(1)

            # Check if step should be skipped
            if await step.should_skip(execution.context):
                logger.info(f"Skipping step: {step.name}")
                execution.step_results[step.name] = StepResult(
                    status=StepStatus.SKIPPED
                )
                continue

            # Execute step
            try:
                result = await self._execute_step(step, execution.context)
                execution.step_results[step.name] = result

                # Update context outputs
                execution.context.outputs.update(result.outputs)

                # Call success hook
                if result.status == StepStatus.COMPLETED:
                    await step.on_success(execution.context)

                # Handle failure
                if result.status == StepStatus.FAILED:
                    if not workflow.continue_on_failure:
                        raise RuntimeError(
                            f"Step {step.name} failed: {result.error}"
                        )

            except Exception as e:
                logger.error(f"Error executing step {step.name}: {e}", exc_info=True)

                if not workflow.continue_on_failure:
                    raise

    async def _execute_parallel(
        self,
        workflow: WorkflowDefinition,
        execution: WorkflowExecution,
    ) -> None:
        """Execute workflow steps in parallel."""
        tasks = []

        for index, step in enumerate(workflow.steps):
            # Check if step should be skipped
            if await step.should_skip(execution.context):
                logger.info(f"Skipping step: {step.name}")
                execution.step_results[step.name] = StepResult(
                    status=StepStatus.SKIPPED
                )
                continue

            # Create task for parallel execution
            task = asyncio.create_task(
                self._execute_step(step, execution.context)
            )
            tasks.append((step.name, task))

        # Wait for all tasks to complete
        for step_name, task in tasks:
            try:
                result = await task
                execution.step_results[step_name] = result

                # Update context outputs (thread-safe)
                execution.context.outputs.update(result.outputs)

            except Exception as e:
                logger.error(f"Error executing step {step_name}: {e}", exc_info=True)

                if not workflow.continue_on_failure:
                    raise

    async def _execute_step(
        self,
        step: WorkflowStep,
        context: WorkflowContext,
    ) -> StepResult:
        """Execute a single workflow step with retry logic."""
        logger.info(f"Executing step: {step.name}")

        retry_count = 0
        last_error = None

        while retry_count <= step.retry_count:
            try:
                # Execute step with timeout
                if step.timeout_seconds:
                    result = await asyncio.wait_for(
                        step.execute(context),
                        timeout=step.timeout_seconds,
                    )
                else:
                    result = await step.execute(context)

                logger.info(f"Step {step.name} completed: {result.status}")
                return result

            except asyncio.TimeoutError:
                last_error = f"Step timed out after {step.timeout_seconds}s"
                logger.warning(f"Step {step.name} timed out")

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Step {step.name} failed (attempt {retry_count + 1}): {e}")

                # Call failure hook
                await step.on_failure(context, e)

            # Increment retry count
            retry_count += 1

            if retry_count <= step.retry_count:
                # Wait before retrying
                wait_time = min(2 ** retry_count, 60)  # Exponential backoff
                logger.info(f"Retrying step {step.name} in {wait_time}s...")
                await asyncio.sleep(wait_time)

        # All retries exhausted
        return StepResult(
            status=StepStatus.FAILED,
            error=last_error,
        )

    async def pause(self, execution_id: UUID) -> None:
        """Pause a running workflow."""
        execution = self._executions.get(execution_id)
        if execution:
            execution.status = WorkflowStatus.PAUSED
            logger.info(f"Workflow execution {execution_id} paused")

    async def resume(self, execution_id: UUID) -> None:
        """Resume a paused workflow."""
        execution = self._executions.get(execution_id)
        if execution and execution.status == WorkflowStatus.PAUSED:
            execution.status = WorkflowStatus.RUNNING
            logger.info(f"Workflow execution {execution_id} resumed")

    async def cancel(self, execution_id: UUID) -> None:
        """Cancel a running workflow."""
        execution = self._executions.get(execution_id)
        if execution:
            execution.status = WorkflowStatus.CANCELLED
            execution.completed_at = datetime.utcnow()
            logger.info(f"Workflow execution {execution_id} cancelled")

    async def get_execution(self, execution_id: UUID) -> Optional[WorkflowExecution]:
        """Get workflow execution status."""
        return self._executions.get(execution_id)

    async def list_executions(
        self,
        workflow_id: Optional[UUID] = None,
        status: Optional[WorkflowStatus] = None,
        limit: int = 100,
    ) -> List[WorkflowExecution]:
        """List workflow executions."""
        executions = list(self._executions.values())

        # Filter by workflow_id
        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]

        # Filter by status
        if status:
            executions = [e for e in executions if e.status == status]

        # Sort by start time (most recent first)
        executions.sort(
            key=lambda e: e.started_at or datetime.min,
            reverse=True,
        )

        # Limit results
        return executions[:limit]
