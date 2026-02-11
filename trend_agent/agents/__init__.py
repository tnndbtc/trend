"""
AI Agent Platform for Trend Intelligence.

Multi-agent system for autonomous data analysis, research, and decision-making.

Includes Agent Control Plane with:
- Task Arbitration (deduplication, budget enforcement, loop detection)
- Budget Engine (multi-dimensional cost tracking)
- Circuit Breaker (runaway prevention)
- Memory Architecture (3-tier with provenance)
- Lineage Tracking (causality graphs)
- Event Dampening (cascade prevention)
- Risk Scoring & Trust Levels
- Hierarchical Agents (supervisor/worker/specialist)
- Audit Logging & Metrics
"""

# Core interfaces
from trend_agent.agents.interface import (
    Agent,
    AgentConfig,
    AgentTask,
    AgentRole,
    AgentStatus,
    AgentRegistry,
    ToolRegistry,
    AgentOrchestrator,
    Message,
    MessageRole,
    Tool,
    ToolCall,
    ToolResult,
)

# Correlation tracking
from trend_agent.agents.correlation import (
    CorrelationContext,
    CorrelationIDFilter,
    get_correlation_id,
)

# Middleware
from trend_agent.agents.middleware import (
    CorrelationIDMiddleware,
    GovernanceMiddleware,
)

# Task arbitration
from trend_agent.agents.arbitration import (
    TaskArbitrator,
    TaskSubmission,
    TaskRecord,
    TaskPriority,
    TaskStatus,
)

# Circuit breaker
from trend_agent.agents.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    FeedbackLoopDetector,
    CircuitOpenError,
)

# Budget engine
from trend_agent.agents.budget import (
    BudgetEngine,
    BudgetType,
    BudgetLimit,
    BudgetAllocation,
)

# Memory architecture
from trend_agent.agents.memory import (
    MemoryStore,
    MemoryEntry,
    MemoryTier,
    GroundTruthMemory,
    SynthesizedMemory,
    EphemeralMemory,
    DriftDetector,
)

# Lineage tracking
from trend_agent.agents.lineage import (
    LineageTracker,
    LineageNode,
    LineageEdge,
    ActionType,
)

# Event system
from trend_agent.agents.events import (
    EventBus,
    EventDampener,
    Event,
    EventPriority,
)

# Safety mechanisms
from trend_agent.agents.safety import (
    RiskScorer,
    RiskAssessment,
    RiskLevel,
    ConfidenceScorer,
    ConfidenceScore,
    TrustManager,
    TrustLevel,
)

# Hierarchy
from trend_agent.agents.hierarchy import (
    AgentHierarchy,
    HierarchicalAgent,
    AgentTier,
    AgentCapability,
    TaskRouter,
    EscalationManager,
)

# Observability
from trend_agent.agents.observability import (
    AuditLogger,
    AuditLogEntry,
    AuditAction,
    AgentMetrics,
)

__all__ = [
    # Core abstractions
    "Agent",
    "AgentConfig",
    "AgentTask",
    "AgentRole",
    "AgentStatus",
    "AgentRegistry",
    "ToolRegistry",
    "AgentOrchestrator",
    "Message",
    "MessageRole",
    "Tool",
    "ToolCall",
    "ToolResult",
    # Correlation
    "CorrelationContext",
    "CorrelationIDFilter",
    "get_correlation_id",
    # Middleware
    "CorrelationIDMiddleware",
    "GovernanceMiddleware",
    # Arbitration
    "TaskArbitrator",
    "TaskSubmission",
    "TaskRecord",
    "TaskPriority",
    "TaskStatus",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitState",
    "FeedbackLoopDetector",
    "CircuitOpenError",
    # Budget
    "BudgetEngine",
    "BudgetType",
    "BudgetLimit",
    "BudgetAllocation",
    # Memory
    "MemoryStore",
    "MemoryEntry",
    "MemoryTier",
    "GroundTruthMemory",
    "SynthesizedMemory",
    "EphemeralMemory",
    "DriftDetector",
    # Lineage
    "LineageTracker",
    "LineageNode",
    "LineageEdge",
    "ActionType",
    # Events
    "EventBus",
    "EventDampener",
    "Event",
    "EventPriority",
    # Safety
    "RiskScorer",
    "RiskAssessment",
    "RiskLevel",
    "ConfidenceScorer",
    "ConfidenceScore",
    "TrustManager",
    "TrustLevel",
    # Hierarchy
    "AgentHierarchy",
    "HierarchicalAgent",
    "AgentTier",
    "AgentCapability",
    "TaskRouter",
    "EscalationManager",
    # Observability
    "AuditLogger",
    "AuditLogEntry",
    "AuditAction",
    "AgentMetrics",
]
