"""
Workflow Management API Endpoints.

Provides endpoints for creating, executing, and monitoring workflows.
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from trend_agent.workflow import (
    SimpleWorkflowEngine,
    WorkflowExecution,
    WorkflowStatus,
    get_template,
    list_templates,
)

router = APIRouter(prefix="/workflows", tags=["Workflows"])

# Global workflow engine instance
_workflow_engine = SimpleWorkflowEngine()


class WorkflowExecutionResponse(BaseModel):
    """Workflow execution response."""

    id: str
    workflow_id: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class WorkflowTemplateRequest(BaseModel):
    """Request to create workflow from template."""

    template_name: str = Field(..., description="Template name")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Template parameters")


@router.get(
    "/templates",
    response_model=List[str],
    summary="List workflow templates",
)
async def get_workflow_templates() -> List[str]:
    """List available workflow templates."""
    return list_templates()


@router.post(
    "/execute",
    response_model=WorkflowExecutionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Execute workflow from template",
)
async def execute_workflow(
    request: WorkflowTemplateRequest,
) -> WorkflowExecutionResponse:
    """
    Execute a workflow from a template.

    Available templates:
    - full_pipeline: Complete pipeline from collection to persistence
    - collection_only: Just collect data
    - processing_only: Process existing items
    - refresh: Re-rank and refresh summaries
    """
    try:
        workflow = get_template(request.template_name, **request.parameters)
        execution = await _workflow_engine.execute(workflow)

        return WorkflowExecutionResponse(
            id=str(execution.id),
            workflow_id=str(execution.workflow_id),
            status=execution.status.value,
            started_at=execution.started_at.isoformat() if execution.started_at else None,
            completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
            error=execution.error,
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{request.template_name}' not found"
        )


@router.get(
    "/{execution_id}",
    response_model=WorkflowExecutionResponse,
    summary="Get workflow execution status",
)
async def get_workflow_execution(execution_id: UUID) -> WorkflowExecutionResponse:
    """Get the status of a workflow execution."""
    execution = await _workflow_engine.get_execution(execution_id)

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution {execution_id} not found"
        )

    return WorkflowExecutionResponse(
        id=str(execution.id),
        workflow_id=str(execution.workflow_id),
        status=execution.status.value,
        started_at=execution.started_at.isoformat() if execution.started_at else None,
        completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
        error=execution.error,
    )


@router.post(
    "/{execution_id}/cancel",
    summary="Cancel workflow execution",
)
async def cancel_workflow_execution(execution_id: UUID) -> Dict[str, Any]:
    """Cancel a running workflow execution."""
    await _workflow_engine.cancel(execution_id)

    return {
        "success": True,
        "message": f"Workflow execution {execution_id} cancelled"
    }
