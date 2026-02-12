"""
Agent-Specific Observability.

Provides metrics, audit logging, and monitoring for agent operations.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import json

logger = logging.getLogger(__name__)


class AuditAction(Enum):
    """Audit action types."""

    AGENT_REGISTERED = "agent_registered"
    AGENT_UNREGISTERED = "agent_unregistered"
    TASK_SUBMITTED = "task_submitted"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_REJECTED = "task_rejected"
    BUDGET_ALLOCATED = "budget_allocated"
    BUDGET_EXCEEDED = "budget_exceeded"
    CIRCUIT_TRIPPED = "circuit_tripped"
    LOOP_DETECTED = "loop_detected"
    RISK_ASSESSED = "risk_assessed"
    ESCALATION_TRIGGERED = "escalation_triggered"
    POLICY_VIOLATION = "policy_violation"
    MEMORY_CREATED = "memory_created"
    MEMORY_DRIFT_DETECTED = "memory_drift_detected"
    TOOL_CALLED = "tool_called"
    EVENT_CASCADE_DETECTED = "event_cascade_detected"


@dataclass
class AuditLogEntry:
    """Immutable audit log entry."""

    # Identity
    id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Action
    action: AuditAction
    actor: str  # Agent ID or system component
    target: Optional[str] = None  # Resource affected

    # Context
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None

    # Details
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "info"  # info, warning, error, critical

    # Security
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "action": self.action.value,
            "actor": self.actor,
            "target": self.target,
            "correlation_id": self.correlation_id,
            "session_id": self.session_id,
            "details": self.details,
            "severity": self.severity,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }

    def to_json(self) -> str:
        """Convert to JSON."""
        return json.dumps(self.to_dict())


class AuditLogger:
    """
    Immutable audit trail for compliance and security.

    Features:
    - Immutable log entries
    - Comprehensive action tracking
    - SIEM integration ready
    - Compliance reporting
    """

    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize audit logger.

        Args:
            log_file: Optional file for audit logs
        """
        self._log_file = log_file
        self._entries: List[AuditLogEntry] = []

        logger.info(f"Audit Logger initialized (log_file={log_file})")

    async def log(
        self,
        action: AuditAction,
        actor: str,
        target: Optional[str] = None,
        correlation_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info",
    ) -> str:
        """
        Log audit event.

        Args:
            action: Action type
            actor: Agent or system component
            target: Resource affected
            correlation_id: Correlation ID
            details: Additional details
            severity: Severity level

        Returns:
            Log entry ID
        """
        from uuid import uuid4

        entry = AuditLogEntry(
            id=str(uuid4()),
            action=action,
            actor=actor,
            target=target,
            correlation_id=correlation_id,
            details=details or {},
            severity=severity,
        )

        # Store entry
        self._entries.append(entry)

        # Write to file if configured
        if self._log_file:
            try:
                with open(self._log_file, 'a') as f:
                    f.write(entry.to_json() + '\n')
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")

        # Log to standard logger
        log_level = getattr(logging, severity.upper(), logging.INFO)
        logger.log(
            log_level,
            f"AUDIT: {action.value} by {actor} "
            f"(target={target}, correlation={correlation_id})"
        )

        return entry.id

    async def query(
        self,
        action: Optional[AuditAction] = None,
        actor: Optional[str] = None,
        target: Optional[str] = None,
        correlation_id: Optional[str] = None,
        severity: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditLogEntry]:
        """
        Query audit logs.

        Args:
            action: Filter by action
            actor: Filter by actor
            target: Filter by target
            correlation_id: Filter by correlation ID
            severity: Filter by severity
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum results

        Returns:
            List of matching entries
        """
        results = []

        for entry in reversed(self._entries):  # Most recent first
            # Apply filters
            if action and entry.action != action:
                continue

            if actor and entry.actor != actor:
                continue

            if target and entry.target != target:
                continue

            if correlation_id and entry.correlation_id != correlation_id:
                continue

            if severity and entry.severity != severity:
                continue

            if start_time and entry.timestamp < start_time:
                continue

            if end_time and entry.timestamp > end_time:
                continue

            results.append(entry)

            if len(results) >= limit:
                break

        return results

    def get_stats(self) -> Dict[str, Any]:
        """
        Get audit statistics.

        Returns:
            Statistics dictionary
        """
        action_counts = {}
        severity_counts = {}

        for entry in self._entries:
            action_counts[entry.action.value] = \
                action_counts.get(entry.action.value, 0) + 1

            severity_counts[entry.severity] = \
                severity_counts.get(entry.severity, 0) + 1

        return {
            "total_entries": len(self._entries),
            "by_action": action_counts,
            "by_severity": severity_counts,
        }


class AgentMetrics:
    """
    Agent-specific Prometheus metrics.

    Metrics:
    - agent_tasks_total
    - agent_budget_usage_usd
    - agent_feedback_loops_detected
    - agent_circuit_breaker_trips
    - memory_drift_detected
    - event_cascade_detected
    - agent_risk_score
    - agent_trust_level
    """

    def __init__(self):
        """Initialize metrics."""
        self._metrics: Dict[str, Dict[str, Any]] = {}

        logger.info("Agent Metrics initialized")

    def record_task(
        self,
        agent_id: str,
        status: str,
        duration: float,
        cost: float,
    ) -> None:
        """
        Record task execution.

        Args:
            agent_id: Agent ID
            status: Task status (success, failed, rejected)
            duration: Task duration in seconds
            cost: Task cost in USD
        """
        key = f"agent_tasks_{status}"

        if agent_id not in self._metrics:
            self._metrics[agent_id] = {}

        self._metrics[agent_id][key] = \
            self._metrics[agent_id].get(key, 0) + 1

        self._metrics[agent_id]["total_cost"] = \
            self._metrics[agent_id].get("total_cost", 0.0) + cost

        self._metrics[agent_id]["total_duration"] = \
            self._metrics[agent_id].get("total_duration", 0.0) + duration

        logger.debug(
            f"Metric recorded: {agent_id} - {key} "
            f"(duration={duration:.2f}s, cost=${cost:.4f})"
        )

    def record_budget_usage(
        self,
        agent_id: str,
        budget_type: str,
        amount: float,
    ) -> None:
        """
        Record budget usage.

        Args:
            agent_id: Agent ID
            budget_type: Budget type (cost, tokens, time, etc.)
            amount: Amount used
        """
        key = f"budget_{budget_type}"

        if agent_id not in self._metrics:
            self._metrics[agent_id] = {}

        self._metrics[agent_id][key] = \
            self._metrics[agent_id].get(key, 0.0) + amount

    def record_loop_detection(self, agent_id: str) -> None:
        """
        Record feedback loop detection.

        Args:
            agent_id: Agent ID
        """
        if agent_id not in self._metrics:
            self._metrics[agent_id] = {}

        self._metrics[agent_id]["loops_detected"] = \
            self._metrics[agent_id].get("loops_detected", 0) + 1

        logger.warning(f"Loop detected metric: {agent_id}")

    def record_circuit_trip(self, circuit_id: str) -> None:
        """
        Record circuit breaker trip.

        Args:
            circuit_id: Circuit ID
        """
        if "circuits" not in self._metrics:
            self._metrics["circuits"] = {}

        self._metrics["circuits"][circuit_id] = \
            self._metrics["circuits"].get(circuit_id, 0) + 1

        logger.error(f"Circuit trip metric: {circuit_id}")

    def record_memory_drift(self, agent_id: str) -> None:
        """
        Record memory drift detection.

        Args:
            agent_id: Agent ID
        """
        if agent_id not in self._metrics:
            self._metrics[agent_id] = {}

        self._metrics[agent_id]["memory_drift"] = \
            self._metrics[agent_id].get("memory_drift", 0) + 1

        logger.warning(f"Memory drift metric: {agent_id}")

    def record_event_cascade(self, correlation_id: str) -> None:
        """
        Record event cascade detection.

        Args:
            correlation_id: Correlation ID
        """
        if "cascades" not in self._metrics:
            self._metrics["cascades"] = {}

        self._metrics["cascades"][correlation_id] = \
            self._metrics["cascades"].get(correlation_id, 0) + 1

        logger.error(f"Event cascade metric: {correlation_id}")

    def set_risk_score(self, agent_id: str, score: float) -> None:
        """
        Set current risk score.

        Args:
            agent_id: Agent ID
            score: Risk score (0-100)
        """
        if agent_id not in self._metrics:
            self._metrics[agent_id] = {}

        self._metrics[agent_id]["risk_score"] = score

    def set_trust_level(self, agent_id: str, level: int) -> None:
        """
        Set current trust level.

        Args:
            agent_id: Agent ID
            level: Trust level (0-4)
        """
        if agent_id not in self._metrics:
            self._metrics[agent_id] = {}

        self._metrics[agent_id]["trust_level"] = level

    def get_agent_metrics(self, agent_id: str) -> Dict[str, Any]:
        """
        Get metrics for agent.

        Args:
            agent_id: Agent ID

        Returns:
            Metrics dictionary
        """
        return self._metrics.get(agent_id, {})

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all metrics.

        Returns:
            Complete metrics dictionary
        """
        return self._metrics.copy()

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics
        """
        lines = []

        # Agent task metrics
        lines.append("# HELP agent_tasks_total Total tasks processed by agent")
        lines.append("# TYPE agent_tasks_total counter")

        for agent_id, metrics in self._metrics.items():
            if agent_id in ("circuits", "cascades"):
                continue

            for status in ("success", "failed", "rejected"):
                key = f"agent_tasks_{status}"
                count = metrics.get(key, 0)
                lines.append(
                    f'agent_tasks_total{{agent="{agent_id}",status="{status}"}} {count}'
                )

        # Budget usage
        lines.append("")
        lines.append("# HELP agent_budget_usage_usd Budget usage in USD")
        lines.append("# TYPE agent_budget_usage_usd gauge")

        for agent_id, metrics in self._metrics.items():
            if agent_id in ("circuits", "cascades"):
                continue

            cost = metrics.get("total_cost", 0.0)
            lines.append(f'agent_budget_usage_usd{{agent="{agent_id}"}} {cost}')

        # Loop detections
        lines.append("")
        lines.append("# HELP agent_feedback_loops_detected Feedback loops detected")
        lines.append("# TYPE agent_feedback_loops_detected counter")

        for agent_id, metrics in self._metrics.items():
            if agent_id in ("circuits", "cascades"):
                continue

            loops = metrics.get("loops_detected", 0)
            if loops > 0:
                lines.append(f'agent_feedback_loops_detected{{agent="{agent_id}"}} {loops}')

        # Circuit breaker trips
        lines.append("")
        lines.append("# HELP agent_circuit_breaker_trips Circuit breaker trips")
        lines.append("# TYPE agent_circuit_breaker_trips counter")

        if "circuits" in self._metrics:
            for circuit_id, trips in self._metrics["circuits"].items():
                lines.append(f'agent_circuit_breaker_trips{{circuit="{circuit_id}"}} {trips}')

        # Memory drift
        lines.append("")
        lines.append("# HELP memory_drift_detected Memory drift detections")
        lines.append("# TYPE memory_drift_detected counter")

        for agent_id, metrics in self._metrics.items():
            if agent_id in ("circuits", "cascades"):
                continue

            drift = metrics.get("memory_drift", 0)
            if drift > 0:
                lines.append(f'memory_drift_detected{{agent="{agent_id}"}} {drift}')

        # Event cascades
        lines.append("")
        lines.append("# HELP event_cascade_detected Event cascade detections")
        lines.append("# TYPE event_cascade_detected counter")

        if "cascades" in self._metrics:
            for correlation_id, count in self._metrics["cascades"].items():
                lines.append(f'event_cascade_detected{{correlation="{correlation_id}"}} {count}')

        # Risk scores
        lines.append("")
        lines.append("# HELP agent_risk_score Current risk score (0-100)")
        lines.append("# TYPE agent_risk_score gauge")

        for agent_id, metrics in self._metrics.items():
            if agent_id in ("circuits", "cascades"):
                continue

            risk = metrics.get("risk_score")
            if risk is not None:
                lines.append(f'agent_risk_score{{agent="{agent_id}"}} {risk}')

        # Trust levels
        lines.append("")
        lines.append("# HELP agent_trust_level Current trust level (0-4)")
        lines.append("# TYPE agent_trust_level gauge")

        for agent_id, metrics in self._metrics.items():
            if agent_id in ("circuits", "cascades"):
                continue

            trust = metrics.get("trust_level")
            if trust is not None:
                lines.append(f'agent_trust_level{{agent="{agent_id}"}} {trust}')

        return "\n".join(lines) + "\n"
