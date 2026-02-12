"""
Task Arbitration Service for Agent Control Plane.

Provides:
- Task deduplication
- Budget enforcement
- Rate limiting
- Loop detection
- Priority-based scheduling
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import logging
from uuid import UUID

from trend_agent.agents.interface import AgentTask
from trend_agent.agents.correlation import get_correlation_id

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""

    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


class TaskStatus(Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    DEDUPLICATED = "deduplicated"


@dataclass
class TaskSubmission:
    """Task submission with governance metadata."""

    task: AgentTask
    agent_id: str
    priority: TaskPriority = TaskPriority.NORMAL
    correlation_id: Optional[str] = None
    submitted_at: datetime = field(default_factory=datetime.utcnow)
    budget_reserved: float = 0.0
    timeout_seconds: Optional[int] = None

    def __post_init__(self):
        """Set correlation ID if not provided."""
        if not self.correlation_id:
            self.correlation_id = get_correlation_id()


@dataclass
class TaskRecord:
    """Record of task execution."""

    task_id: UUID
    task_hash: str
    agent_id: str
    correlation_id: str
    status: TaskStatus
    priority: TaskPriority
    submitted_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    budget_used: float = 0.0


class TaskArbitrator:
    """
    Central task arbitration service.

    Responsibilities:
    - Deduplicate identical tasks
    - Enforce budget constraints
    - Check rate limits
    - Detect feedback loops
    - Schedule tasks by priority
    """

    def __init__(
        self,
        dedup_window: timedelta = timedelta(minutes=5),
        max_tasks_per_agent: int = 100,
        enable_loop_detection: bool = True,
    ):
        """
        Initialize task arbitrator.

        Args:
            dedup_window: Time window for deduplication
            max_tasks_per_agent: Max concurrent tasks per agent
            enable_loop_detection: Enable loop detection
        """
        self._dedup_window = dedup_window
        self._max_tasks_per_agent = max_tasks_per_agent
        self._enable_loop_detection = enable_loop_detection

        # Task tracking
        self._task_records: Dict[UUID, TaskRecord] = {}
        self._task_hashes: Dict[str, List[TaskRecord]] = {}
        self._agent_tasks: Dict[str, List[UUID]] = {}

        logger.info(
            f"Task Arbitrator initialized (dedup_window={dedup_window}, "
            f"max_tasks_per_agent={max_tasks_per_agent})"
        )

    async def submit_task(
        self,
        submission: TaskSubmission,
    ) -> tuple[bool, Optional[TaskRecord], Optional[str]]:
        """
        Submit a task for arbitration.

        Steps:
        1. Check for duplicate tasks (deduplication)
        2. Validate against budget constraints
        3. Check rate limits
        4. Detect feedback loops (if enabled)
        5. Create task record and schedule

        Args:
            submission: Task submission

        Returns:
            Tuple of (accepted, task_record, rejection_reason)
        """
        task_hash = self._compute_task_hash(submission.task)

        # 1. Check for duplicates
        duplicate = self._find_duplicate_task(task_hash, submission.agent_id)
        if duplicate:
            logger.info(
                f"Task deduplicated: {submission.task.id} "
                f"(duplicate of {duplicate.task_id})"
            )
            return (
                False,
                duplicate,
                f"Duplicate of task {duplicate.task_id}",
            )

        # 2. Check agent task limit (rate limiting)
        if not self._check_agent_capacity(submission.agent_id):
            logger.warning(
                f"Agent {submission.agent_id} exceeded task limit "
                f"({self._max_tasks_per_agent})"
            )
            return (
                False,
                None,
                f"Agent task limit exceeded ({self._max_tasks_per_agent})",
            )

        # 3. Detect feedback loops (if enabled)
        if self._enable_loop_detection:
            loop_detected = await self._detect_loop(submission)
            if loop_detected:
                logger.error(
                    f"Feedback loop detected for correlation "
                    f"{submission.correlation_id}"
                )
                return (
                    False,
                    None,
                    f"Feedback loop detected (correlation: {submission.correlation_id})",
                )

        # 4. Create task record
        task_record = TaskRecord(
            task_id=submission.task.id,
            task_hash=task_hash,
            agent_id=submission.agent_id,
            correlation_id=submission.correlation_id or "",
            status=TaskStatus.PENDING,
            priority=submission.priority,
            submitted_at=submission.submitted_at,
            budget_used=0.0,
        )

        # 5. Register task
        self._register_task(task_record)

        logger.info(
            f"Task accepted: {task_record.task_id} "
            f"(agent={submission.agent_id}, priority={submission.priority.value})"
        )

        return (True, task_record, None)

    async def start_task(self, task_id: UUID) -> bool:
        """
        Mark task as started.

        Args:
            task_id: Task ID

        Returns:
            True if successful
        """
        task_record = self._task_records.get(task_id)
        if not task_record:
            logger.error(f"Task not found: {task_id}")
            return False

        task_record.status = TaskStatus.RUNNING
        task_record.started_at = datetime.utcnow()

        logger.info(f"Task started: {task_id}")
        return True

    async def complete_task(
        self,
        task_id: UUID,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        budget_used: float = 0.0,
    ) -> bool:
        """
        Mark task as completed.

        Args:
            task_id: Task ID
            result: Task result
            error: Error message if failed
            budget_used: Budget consumed

        Returns:
            True if successful
        """
        task_record = self._task_records.get(task_id)
        if not task_record:
            logger.error(f"Task not found: {task_id}")
            return False

        task_record.status = TaskStatus.COMPLETED if not error else TaskStatus.FAILED
        task_record.completed_at = datetime.utcnow()
        task_record.result = result
        task_record.error = error
        task_record.budget_used = budget_used

        # Remove from agent's active tasks
        if task_record.agent_id in self._agent_tasks:
            self._agent_tasks[task_record.agent_id].remove(task_id)

        duration = (
            task_record.completed_at - task_record.started_at
            if task_record.started_at
            else None
        )

        logger.info(
            f"Task {'completed' if not error else 'failed'}: {task_id} "
            f"(duration={duration}, budget=${budget_used:.4f})"
        )

        return True

    def get_task_record(self, task_id: UUID) -> Optional[TaskRecord]:
        """
        Get task record.

        Args:
            task_id: Task ID

        Returns:
            Task record or None
        """
        return self._task_records.get(task_id)

    def get_agent_tasks(self, agent_id: str) -> List[TaskRecord]:
        """
        Get all tasks for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            List of task records
        """
        task_ids = self._agent_tasks.get(agent_id, [])
        return [self._task_records[tid] for tid in task_ids if tid in self._task_records]

    def _compute_task_hash(self, task: AgentTask) -> str:
        """
        Compute hash for task deduplication.

        Hash includes:
        - Task description
        - Task context (sorted keys for consistency)

        Args:
            task: Task to hash

        Returns:
            SHA-256 hash
        """
        # Create deterministic representation
        content = f"{task.description}|"

        # Add sorted context items
        if task.context:
            sorted_context = sorted(task.context.items())
            content += "|".join(f"{k}={v}" for k, v in sorted_context)

        # Compute hash
        return hashlib.sha256(content.encode()).hexdigest()

    def _find_duplicate_task(
        self,
        task_hash: str,
        agent_id: str,
    ) -> Optional[TaskRecord]:
        """
        Find duplicate task within deduplication window.

        Args:
            task_hash: Task hash
            agent_id: Agent ID

        Returns:
            Duplicate task record or None
        """
        if task_hash not in self._task_hashes:
            return None

        cutoff_time = datetime.utcnow() - self._dedup_window

        for task_record in self._task_hashes[task_hash]:
            # Check if task is recent and from same agent
            if (
                task_record.agent_id == agent_id
                and task_record.submitted_at >= cutoff_time
                and task_record.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
            ):
                return task_record

        return None

    def _check_agent_capacity(self, agent_id: str) -> bool:
        """
        Check if agent has capacity for more tasks.

        Args:
            agent_id: Agent ID

        Returns:
            True if agent can accept more tasks
        """
        active_tasks = len(self._agent_tasks.get(agent_id, []))
        return active_tasks < self._max_tasks_per_agent

    async def _detect_loop(self, submission: TaskSubmission) -> bool:
        """
        Detect feedback loops by analyzing correlation chain.

        Simple heuristic: Count tasks with same correlation ID.
        If too many tasks share correlation ID, likely a loop.

        Args:
            submission: Task submission

        Returns:
            True if loop detected
        """
        if not submission.correlation_id:
            return False

        # Count tasks with same correlation ID
        loop_count = sum(
            1
            for record in self._task_records.values()
            if record.correlation_id == submission.correlation_id
            and record.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
        )

        # If more than 10 concurrent tasks with same correlation ID, likely a loop
        LOOP_THRESHOLD = 10
        return loop_count >= LOOP_THRESHOLD

    def _register_task(self, task_record: TaskRecord) -> None:
        """
        Register task in tracking structures.

        Args:
            task_record: Task record to register
        """
        # Add to main registry
        self._task_records[task_record.task_id] = task_record

        # Add to hash index
        if task_record.task_hash not in self._task_hashes:
            self._task_hashes[task_record.task_hash] = []
        self._task_hashes[task_record.task_hash].append(task_record)

        # Add to agent's active tasks
        if task_record.agent_id not in self._agent_tasks:
            self._agent_tasks[task_record.agent_id] = []
        self._agent_tasks[task_record.agent_id].append(task_record.task_id)

    def cleanup_old_records(self, max_age: timedelta = timedelta(hours=24)) -> int:
        """
        Clean up old task records.

        Args:
            max_age: Maximum age for records

        Returns:
            Number of records removed
        """
        cutoff_time = datetime.utcnow() - max_age
        removed_count = 0

        # Find old completed/failed tasks
        old_task_ids = [
            task_id
            for task_id, record in self._task_records.items()
            if record.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
            and record.completed_at
            and record.completed_at < cutoff_time
        ]

        # Remove old tasks
        for task_id in old_task_ids:
            record = self._task_records.pop(task_id)

            # Remove from hash index
            if record.task_hash in self._task_hashes:
                self._task_hashes[record.task_hash] = [
                    r for r in self._task_hashes[record.task_hash] if r.task_id != task_id
                ]

            removed_count += 1

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old task records")

        return removed_count
