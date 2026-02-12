# Agent Control Plane - Quick Start Guide

Complete governance layer for production autonomous AI agents.

---

## Installation

```bash
# All components are included in trend_agent.agents
from trend_agent.agents import (
    # Governance
    TaskArbitrator,
    CircuitBreaker,
    BudgetEngine,

    # Memory
    MemoryStore,
    GroundTruthMemory,
    SynthesizedMemory,

    # Safety
    RiskScorer,
    TrustManager,

    # Hierarchy
    AgentHierarchy,
    TaskRouter,

    # Observability
    AuditLogger,
    AgentMetrics,
)
```

---

## 1. Basic Governed Agent Execution

Execute a task with full governance:

```python
from trend_agent.agents import (
    TaskArbitrator,
    TaskSubmission,
    TaskPriority,
    CircuitBreaker,
    AuditLogger,
    AuditAction,
)

# Initialize governance
arbitrator = TaskArbitrator()
breaker = CircuitBreaker()
audit = AuditLogger()

# Create task
task = AgentTask(description="Analyze tech trends")

# Submit with governance
submission = TaskSubmission(
    task=task,
    agent_id="researcher",
    priority=TaskPriority.HIGH,
)

# Check arbitration (dedup, rate limits, loops)
accepted, record, reason = await arbitrator.submit_task(submission)
if not accepted:
    print(f"Task rejected: {reason}")
    return

# Check circuit breaker
circuit_id = f"agent:researcher"
if not breaker.can_proceed(circuit_id):
    print("Circuit is open - agent is unhealthy")
    return

try:
    # Execute
    await arbitrator.start_task(record.task_id)
    result = await agent.process_task(task)

    # Success
    breaker.record_success(circuit_id)
    await arbitrator.complete_task(record.task_id, result=result)
    await audit.log(AuditAction.TASK_COMPLETED, "researcher")

except Exception as e:
    # Failure
    breaker.record_failure(circuit_id, str(e))
    await arbitrator.complete_task(record.task_id, error=str(e))
    await audit.log(AuditAction.TASK_FAILED, "researcher", severity="error")
```

---

## 2. Budget Management

Track and enforce budgets:

```python
from trend_agent.agents import BudgetEngine, BudgetType, BudgetLimit
from datetime import timedelta

engine = BudgetEngine()

# Create daily budget
engine.create_allocation(
    agent_id="researcher",
    limits={
        BudgetType.COST: BudgetLimit(
            budget_type=BudgetType.COST,
            limit=50.0,  # $50/day
            period=timedelta(days=1),
            soft_limit=40.0,  # Warning at $40
        ),
        BudgetType.TOKENS: BudgetLimit(
            budget_type=BudgetType.TOKENS,
            limit=500000,  # 500K tokens/day
            period=timedelta(days=1),
        ),
    },
)

# Before execution: Reserve budget
has_budget, reason = engine.check_budget(
    agent_id="researcher",
    budget_type=BudgetType.COST,
    amount=2.50,
)

if has_budget:
    engine.reserve_budget(
        agent_id="researcher",
        budget_type=BudgetType.COST,
        amount=2.50,
        reservation_id="task_123",
    )

    # ... execute task ...

    # After execution: Commit actual usage
    engine.commit_reservation("task_123", actual_amount=2.23)
else:
    print(f"Budget exceeded: {reason}")

# Check remaining budget
remaining = engine.get_remaining("researcher", BudgetType.COST)
print(f"Remaining budget: ${remaining:.2f}")
```

---

## 3. Memory with Provenance

Track memory lineage and prevent drift:

```python
from trend_agent.agents import (
    MemoryStore,
    GroundTruthMemory,
    SynthesizedMemory,
    DriftDetector,
    SourceType,
)

store = MemoryStore()
detector = DriftDetector()

# Store ground truth (immutable source)
ground_truth = GroundTruthMemory(
    content="Apple announces Vision Pro at WWDC 2024",
    source_type=SourceType.WEB_SCRAPE,
    source_id="techcrunch_20240610",
    created_by="data_collector",
)
gt_id = await store.store(ground_truth)

# Create synthesized memory (LLM-generated)
synthesized = SynthesizedMemory(
    content="Apple's Vision Pro represents major AR advancement",
    derived_from=[str(gt_id)],
    generation=1,  # 1 step from ground truth
    created_by="analyst_agent",
    synthesis_model="gpt-4",
    synthesis_cost=0.023,
)
syn_id = await store.store(synthesized)

# Check for semantic drift
has_drifted, reason = await detector.check_drift(synthesized, store)
if has_drifted:
    print(f"Memory drift detected: {reason}")

    # Regenerate from ground truth
    chain = await store.get_lineage_chain(str(syn_id))
    ground_truth = chain[0]  # Original source
    # ... regenerate synthesized memory ...

# Query lineage
chain = await store.get_lineage_chain(str(syn_id))
print(f"Memory lineage: {' -> '.join(m.content[:30] for m in chain)}")
```

---

## 4. Causality Tracking

Track and visualize operation chains:

```python
from trend_agent.agents import LineageTracker, ActionType

tracker = LineageTracker()

# Record task submission
task_node = await tracker.record_action(
    correlation_id="corr_abc123",
    action_type=ActionType.TASK_SUBMITTED,
    agent_id="researcher",
    resource_id="task_456",
)

# Record tool call (caused by task)
tool_node = await tracker.record_action(
    correlation_id="corr_abc123",
    action_type=ActionType.TOOL_CALLED,
    source_id=task_node,  # Causality link
    agent_id="researcher",
    resource_id="search_google",
)

# Record memory creation (caused by tool)
memory_node = await tracker.record_action(
    correlation_id="corr_abc123",
    action_type=ActionType.MEMORY_CREATED,
    source_id=tool_node,
    resource_id="memory_789",
)

# Get full causality chain
chain = await tracker.get_causality_chain("corr_abc123")
for node in chain:
    print(f"{node.action_type.value} by {node.agent_id}")

# Detect cycles (feedback loops)
has_cycle, path = await tracker.detect_cycle("corr_abc123")
if has_cycle:
    print(f"Feedback loop detected: {' -> '.join(path)}")

# Export for visualization
dot = await tracker.export_dot("corr_abc123")
with open("causality.dot", "w") as f:
    f.write(dot)
# Generate image: dot -Tpng causality.dot -o causality.png
```

---

## 5. Event Dampening

Prevent event storms:

```python
from trend_agent.agents import EventBus, EventDampener, Event, EventPriority
from datetime import timedelta

# Create bus with dampening
dampener = EventDampener(
    dedup_window=timedelta(seconds=30),
    rate_limits={
        "trend_updated": 100,  # Max 100/min
        "alert": 10,
    },
    cascade_threshold=100,
)

bus = EventBus(dampener=dampener)

# Subscribe
def handle_trend(event: Event):
    print(f"Trend: {event.payload['trend_id']}")

bus.subscribe("trend_updated", handle_trend)

# Publish (automatically dampened)
event = Event(
    event_id="evt_123",
    event_type="trend_updated",
    correlation_id="corr_abc",
    source="trend_analyzer",
    priority=EventPriority.HIGH,
    payload={"trend_id": "ai_boom", "score": 95},
)

published, reason = await bus.publish(event)
if not published:
    print(f"Event dampened: {reason}")
```

---

## 6. Risk Assessment

Assess operation risk before execution:

```python
from trend_agent.agents import RiskScorer, RiskLevel

scorer = RiskScorer()

# Assess task risk
assessment = await scorer.assess_risk(
    task=my_task,
    agent_id="researcher",
    estimated_cost=5.0,
    scope_size=50,  # Affects 50 resources
    impact_level="high",
    is_novel=False,
    chain_depth=3,
)

print(f"Risk score: {assessment.risk_score:.1f}/100")
print(f"Risk level: {assessment.risk_level.value}")

if assessment.requires_approval:
    print(f"Manual approval required: {assessment.approval_reason}")
    # ... send to human review queue ...
else:
    # Auto-approve and execute
    await execute_task(my_task)
```

---

## 7. Trust Management

Build agent reputation:

```python
from trend_agent.agents import TrustManager, TrustLevel

manager = TrustManager()

# Record task outcomes
manager.record_task_completion(
    agent_id="researcher",
    success=True,
    duration=12.5,
    cost=0.23,
)

# Calculate trust level
trust_level = manager.calculate_trust_level("researcher")
print(f"Trust level: {trust_level.name}")

# Get performance summary
summary = manager.get_performance_summary("researcher")
print(f"Success rate: {summary['success_rate']:.1%}")
print(f"Total cost: ${summary['total_cost']:.2f}")

# Grant permissions based on trust
if trust_level >= TrustLevel.ELEVATED:
    # Allow high-risk operations
    allow_autonomous_execution = True
```

---

## 8. Hierarchical Agents

Organize agents in supervisor-worker topology:

```python
from trend_agent.agents import (
    AgentHierarchy,
    AgentTier,
    AgentCapability,
    TaskRouter,
)

hierarchy = AgentHierarchy()

# Register supervisor
await hierarchy.register_agent(
    agent=supervisor_agent,
    tier=AgentTier.SUPERVISOR,
    capabilities=[
        AgentCapability(name="planning", description="Task planning", proficiency=0.9),
        AgentCapability(name="coordination", description="Multi-agent", proficiency=0.95),
    ],
)

# Register worker
await hierarchy.register_agent(
    agent=researcher_agent,
    tier=AgentTier.WORKER,
    parent_id="supervisor",
    capabilities=[
        AgentCapability(name="research", description="Info gathering", proficiency=0.85),
        AgentCapability(name="analysis", description="Data analysis", proficiency=0.80),
    ],
)

# Route task to best agent
router = TaskRouter(hierarchy)
best_agent = await router.route_task(
    task=my_task,
    required_capabilities=["research", "analysis"],
)

print(f"Routing to: {best_agent.agent_id} ({best_agent.tier.value})")
```

---

## 9. Metrics & Monitoring

Export metrics for Prometheus:

```python
from trend_agent.agents import AgentMetrics

metrics = AgentMetrics()

# Record operations
metrics.record_task("researcher", status="success", duration=12.5, cost=0.23)
metrics.record_loop_detection("researcher")
metrics.record_budget_usage("researcher", "cost", 0.23)
metrics.set_risk_score("researcher", 35.5)
metrics.set_trust_level("researcher", 2)

# Export for Prometheus
prometheus_output = metrics.export_prometheus()
print(prometheus_output)

# Output:
# agent_tasks_total{agent="researcher",status="success"} 1
# agent_budget_usage_usd{agent="researcher"} 0.23
# agent_feedback_loops_detected{agent="researcher"} 1
# agent_risk_score{agent="researcher"} 35.5
# agent_trust_level{agent="researcher"} 2
```

---

## 10. Complete Integration Example

Full governance-aware agent execution:

```python
from trend_agent.agents import (
    TaskArbitrator,
    TaskSubmission,
    CircuitBreaker,
    BudgetEngine,
    BudgetType,
    RiskScorer,
    TrustManager,
    MemoryStore,
    LineageTracker,
    ActionType,
    AuditLogger,
    AuditAction,
    AgentMetrics,
)

class GovernedAgent:
    """Agent with full governance integration."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.arbitrator = TaskArbitrator()
        self.breaker = CircuitBreaker()
        self.budget = BudgetEngine()
        self.risk = RiskScorer()
        self.trust = TrustManager()
        self.memory = MemoryStore()
        self.lineage = LineageTracker()
        self.audit = AuditLogger()
        self.metrics = AgentMetrics()

    async def execute_task(self, task: AgentTask):
        """Execute task with full governance."""

        # 1. Risk assessment
        assessment = await self.risk.assess_risk(
            task, self.agent_id, estimated_cost=2.0
        )
        if assessment.requires_approval:
            await self.audit.log(
                AuditAction.ESCALATION_TRIGGERED,
                self.agent_id,
            )
            return await self.request_approval(assessment)

        # 2. Circuit breaker check
        circuit_id = f"agent:{self.agent_id}"
        if not self.breaker.can_proceed(circuit_id):
            await self.audit.log(
                AuditAction.TASK_REJECTED,
                self.agent_id,
                severity="error",
            )
            raise Exception("Circuit is open")

        # 3. Task arbitration
        submission = TaskSubmission(task=task, agent_id=self.agent_id)
        accepted, record, reason = await self.arbitrator.submit_task(submission)

        if not accepted:
            await self.audit.log(
                AuditAction.TASK_REJECTED,
                self.agent_id,
                details={"reason": reason},
            )
            return None

        # 4. Budget reservation
        has_budget, _ = self.budget.check_budget(
            self.agent_id, BudgetType.COST, 2.0
        )
        if has_budget:
            self.budget.reserve_budget(
                self.agent_id,
                BudgetType.COST,
                2.0,
                str(record.task_id),
            )

        # 5. Record lineage
        task_node = await self.lineage.record_action(
            correlation_id=record.correlation_id,
            action_type=ActionType.TASK_STARTED,
            agent_id=self.agent_id,
            resource_id=str(record.task_id),
        )

        try:
            # 6. Execute
            start_time = datetime.utcnow()
            await self.arbitrator.start_task(record.task_id)

            result = await self.process_task_internal(task)

            duration = (datetime.utcnow() - start_time).total_seconds()

            # 7. Success path
            self.breaker.record_success(circuit_id)
            await self.arbitrator.complete_task(
                record.task_id, result=result, budget_used=1.23
            )
            self.budget.commit_reservation(str(record.task_id), 1.23)
            self.trust.record_task_completion(
                self.agent_id, success=True, duration=duration, cost=1.23
            )

            await self.audit.log(
                AuditAction.TASK_COMPLETED,
                self.agent_id,
                target=str(record.task_id),
            )
            self.metrics.record_task(
                self.agent_id, "success", duration, 1.23
            )

            return result

        except Exception as e:
            # 8. Failure path
            self.breaker.record_failure(circuit_id, str(e))
            await self.arbitrator.complete_task(
                record.task_id, error=str(e)
            )
            self.budget.release_reservation(str(record.task_id))
            self.trust.record_task_completion(
                self.agent_id, success=False, duration=0, cost=0
            )

            await self.audit.log(
                AuditAction.TASK_FAILED,
                self.agent_id,
                severity="error",
            )
            self.metrics.record_task(
                self.agent_id, "failed", 0, 0
            )

            raise

# Usage
agent = GovernedAgent("researcher")
result = await agent.execute_task(my_task)
```

---

## Configuration

See `config/agent_control_plane.yaml` for all configuration options.

## Documentation

- **SESSION_11_IMPLEMENTATION.md** - Complete implementation details
- **ARCHITECTURE_GAP_ANALYSIS.md** - Architecture compliance
- Individual module docstrings for API reference

## Metrics Endpoint

Add to FastAPI:

```python
from fastapi import FastAPI
from trend_agent.agents import AgentMetrics

app = FastAPI()
metrics = AgentMetrics()

@app.get("/metrics")
def get_metrics():
    return metrics.export_prometheus()
```

---

**The Agent Control Plane is production-ready!** 🚀

For questions, see the detailed implementation docs or architecture specifications.
