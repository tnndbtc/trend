"""
Hierarchical Agent Topology.

Implements supervisor-worker-specialist agent hierarchy for complex workflows.
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

from trend_agent.agents.interface import Agent, AgentTask, AgentConfig, AgentRole

logger = logging.getLogger(__name__)


class AgentTier(Enum):
    """Agent tier in hierarchy."""

    SUPERVISOR = "supervisor"  # Plans, coordinates, synthesizes
    WORKER = "worker"  # Executes tasks, can delegate
    SPECIALIST = "specialist"  # Domain expert, leaf nodes


@dataclass
class AgentCapability:
    """Agent capability definition."""

    name: str
    description: str
    proficiency: float  # 0-1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HierarchicalAgent:
    """Agent with hierarchical metadata."""

    agent: Agent
    tier: AgentTier
    capabilities: List[AgentCapability] = field(default_factory=list)
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    max_concurrent_tasks: int = 5
    current_task_count: int = 0
    total_tasks_completed: int = 0
    average_task_duration: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active: datetime = field(default_factory=datetime.utcnow)

    @property
    def agent_id(self) -> str:
        """Get agent ID."""
        return self.agent.config.name

    def is_available(self) -> bool:
        """Check if agent has capacity for more tasks."""
        return self.current_task_count < self.max_concurrent_tasks

    def has_capability(self, capability_name: str, min_proficiency: float = 0.5) -> bool:
        """
        Check if agent has capability.

        Args:
            capability_name: Capability name
            min_proficiency: Minimum proficiency required

        Returns:
            True if agent has capability
        """
        for cap in self.capabilities:
            if cap.name == capability_name and cap.proficiency >= min_proficiency:
                return True
        return False


class AgentHierarchy:
    """
    Manages hierarchical agent topology.

    Features:
    - Three-tier hierarchy (Supervisor/Worker/Specialist)
    - Parent-child relationships
    - Capability-based agent selection
    - Load balancing
    - Escalation paths
    """

    def __init__(self):
        """Initialize agent hierarchy."""
        self._agents: Dict[str, HierarchicalAgent] = {}
        self._tier_index: Dict[AgentTier, List[str]] = {
            tier: [] for tier in AgentTier
        }
        self._capability_index: Dict[str, List[str]] = {}  # capability -> agent_ids

        logger.info("Agent Hierarchy initialized")

    async def register_agent(
        self,
        agent: Agent,
        tier: AgentTier,
        capabilities: Optional[List[AgentCapability]] = None,
        parent_id: Optional[str] = None,
    ) -> str:
        """
        Register agent in hierarchy.

        Args:
            agent: Agent instance
            tier: Agent tier
            capabilities: Agent capabilities
            parent_id: Optional parent agent ID

        Returns:
            Agent ID
        """
        agent_id = agent.config.name

        # Create hierarchical agent
        h_agent = HierarchicalAgent(
            agent=agent,
            tier=tier,
            capabilities=capabilities or [],
            parent_id=parent_id,
        )

        # Store agent
        self._agents[agent_id] = h_agent

        # Update tier index
        self._tier_index[tier].append(agent_id)

        # Update capability index
        for cap in h_agent.capabilities:
            if cap.name not in self._capability_index:
                self._capability_index[cap.name] = []
            self._capability_index[cap.name].append(agent_id)

        # Update parent's children
        if parent_id and parent_id in self._agents:
            self._agents[parent_id].children_ids.append(agent_id)

        logger.info(
            f"Agent registered: {agent_id} "
            f"(tier={tier.value}, capabilities={len(h_agent.capabilities)})"
        )

        return agent_id

    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister agent.

        Args:
            agent_id: Agent ID

        Returns:
            True if successful
        """
        if agent_id not in self._agents:
            logger.warning(f"Agent not found: {agent_id}")
            return False

        h_agent = self._agents[agent_id]

        # Remove from tier index
        self._tier_index[h_agent.tier].remove(agent_id)

        # Remove from capability index
        for cap in h_agent.capabilities:
            if cap.name in self._capability_index:
                if agent_id in self._capability_index[cap.name]:
                    self._capability_index[cap.name].remove(agent_id)

        # Remove from parent's children
        if h_agent.parent_id and h_agent.parent_id in self._agents:
            parent = self._agents[h_agent.parent_id]
            if agent_id in parent.children_ids:
                parent.children_ids.remove(agent_id)

        # Remove agent
        del self._agents[agent_id]

        logger.info(f"Agent unregistered: {agent_id}")
        return True

    def get_agent(self, agent_id: str) -> Optional[HierarchicalAgent]:
        """
        Get agent by ID.

        Args:
            agent_id: Agent ID

        Returns:
            Hierarchical agent or None
        """
        return self._agents.get(agent_id)

    def get_agents_by_tier(self, tier: AgentTier) -> List[HierarchicalAgent]:
        """
        Get all agents in tier.

        Args:
            tier: Agent tier

        Returns:
            List of agents
        """
        agent_ids = self._tier_index.get(tier, [])
        return [self._agents[aid] for aid in agent_ids if aid in self._agents]

    def get_agents_by_capability(
        self,
        capability: str,
        min_proficiency: float = 0.5,
    ) -> List[HierarchicalAgent]:
        """
        Get agents with specific capability.

        Args:
            capability: Capability name
            min_proficiency: Minimum proficiency

        Returns:
            List of agents
        """
        agent_ids = self._capability_index.get(capability, [])
        agents = []

        for agent_id in agent_ids:
            if agent_id in self._agents:
                h_agent = self._agents[agent_id]
                if h_agent.has_capability(capability, min_proficiency):
                    agents.append(h_agent)

        return agents

    def get_available_agents(
        self,
        tier: Optional[AgentTier] = None,
        capability: Optional[str] = None,
    ) -> List[HierarchicalAgent]:
        """
        Get available agents.

        Args:
            tier: Optional tier filter
            capability: Optional capability filter

        Returns:
            List of available agents
        """
        # Get candidate agents
        if tier:
            candidates = self.get_agents_by_tier(tier)
        elif capability:
            candidates = self.get_agents_by_capability(capability)
        else:
            candidates = list(self._agents.values())

        # Filter by availability
        return [agent for agent in candidates if agent.is_available()]

    def get_parent(self, agent_id: str) -> Optional[HierarchicalAgent]:
        """
        Get parent agent.

        Args:
            agent_id: Agent ID

        Returns:
            Parent agent or None
        """
        h_agent = self._agents.get(agent_id)
        if not h_agent or not h_agent.parent_id:
            return None

        return self._agents.get(h_agent.parent_id)

    def get_children(self, agent_id: str) -> List[HierarchicalAgent]:
        """
        Get child agents.

        Args:
            agent_id: Agent ID

        Returns:
            List of child agents
        """
        h_agent = self._agents.get(agent_id)
        if not h_agent:
            return []

        return [
            self._agents[cid]
            for cid in h_agent.children_ids
            if cid in self._agents
        ]

    def get_escalation_path(self, agent_id: str) -> List[HierarchicalAgent]:
        """
        Get escalation path to supervisor.

        Args:
            agent_id: Agent ID

        Returns:
            List of agents from current to top supervisor
        """
        path = []
        current_id = agent_id

        while current_id:
            h_agent = self._agents.get(current_id)
            if not h_agent:
                break

            path.append(h_agent)

            # Move to parent
            current_id = h_agent.parent_id

        return path

    def get_hierarchy_stats(self) -> Dict[str, Any]:
        """
        Get hierarchy statistics.

        Returns:
            Statistics dictionary
        """
        tier_stats = {}
        for tier in AgentTier:
            agents = self.get_agents_by_tier(tier)
            available = [a for a in agents if a.is_available()]

            tier_stats[tier.value] = {
                "total": len(agents),
                "available": len(available),
                "utilization": 1 - (len(available) / len(agents) if agents else 1),
            }

        return {
            "total_agents": len(self._agents),
            "by_tier": tier_stats,
            "total_capabilities": len(self._capability_index),
        }


class TaskRouter:
    """
    Routes tasks to appropriate agents based on capabilities and load.

    Routing strategies:
    - Capability matching
    - Load balancing
    - Performance-based selection
    - Affinity (prefer agents that worked together)
    """

    def __init__(self, hierarchy: AgentHierarchy):
        """
        Initialize task router.

        Args:
            hierarchy: Agent hierarchy
        """
        self._hierarchy = hierarchy
        self._agent_affinity: Dict[str, Dict[str, float]] = {}  # agent_id -> {agent_id: score}

        logger.info("Task Router initialized")

    async def route_task(
        self,
        task: AgentTask,
        required_capabilities: Optional[List[str]] = None,
        preferred_tier: Optional[AgentTier] = None,
    ) -> Optional[HierarchicalAgent]:
        """
        Route task to best agent.

        Steps:
        1. Find capable agents
        2. Filter by availability
        3. Score candidates (capability, load, performance, affinity)
        4. Select best agent

        Args:
            task: Task to route
            required_capabilities: Required capabilities
            preferred_tier: Preferred agent tier

        Returns:
            Selected agent or None
        """
        # 1. Find capable agents
        candidates = []

        if required_capabilities:
            # Get agents with all required capabilities
            for capability in required_capabilities:
                cap_agents = self._hierarchy.get_agents_by_capability(capability)
                if not candidates:
                    candidates = cap_agents
                else:
                    # Intersection: agents with all capabilities
                    candidates = [a for a in candidates if a in cap_agents]
        elif preferred_tier:
            candidates = self._hierarchy.get_agents_by_tier(preferred_tier)
        else:
            candidates = list(self._hierarchy._agents.values())

        if not candidates:
            logger.warning("No capable agents found for task")
            return None

        # 2. Filter by availability
        available = [agent for agent in candidates if agent.is_available()]

        if not available:
            logger.warning("No available agents found for task")
            return None

        # 3. Score candidates
        scores = {}
        for agent in available:
            scores[agent.agent_id] = self._score_agent(agent, task, required_capabilities or [])

        # 4. Select best agent
        best_agent_id = max(scores.items(), key=lambda x: x[1])[0]
        best_agent = self._hierarchy.get_agent(best_agent_id)

        logger.info(
            f"Task routed to: {best_agent_id} "
            f"(score={scores[best_agent_id]:.2f})"
        )

        return best_agent

    def _score_agent(
        self,
        agent: HierarchicalAgent,
        task: AgentTask,
        required_capabilities: List[str],
    ) -> float:
        """
        Score agent for task.

        Factors:
        - Capability proficiency
        - Load (inverse of current tasks)
        - Performance (success rate, speed)
        - Affinity (previous collaboration)

        Args:
            agent: Agent to score
            task: Task
            required_capabilities: Required capabilities

        Returns:
            Score (0-100)
        """
        scores = {}

        # 1. Capability score (0-40)
        capability_score = 0.0
        if required_capabilities:
            for cap_name in required_capabilities:
                for cap in agent.capabilities:
                    if cap.name == cap_name:
                        capability_score += cap.proficiency

            capability_score = (capability_score / len(required_capabilities)) * 40
        else:
            capability_score = 20  # Neutral if no specific requirements

        scores["capability"] = capability_score

        # 2. Load score (0-30)
        load_ratio = agent.current_task_count / agent.max_concurrent_tasks
        load_score = (1 - load_ratio) * 30  # Lower load = higher score

        scores["load"] = load_score

        # 3. Performance score (0-20)
        # Simplified: based on task completion count
        performance_score = min(20, agent.total_tasks_completed / 50)

        scores["performance"] = performance_score

        # 4. Affinity score (0-10)
        # Check if agent has worked with task-related agents
        affinity_score = 5.0  # Neutral

        scores["affinity"] = affinity_score

        total_score = sum(scores.values())

        return total_score

    def record_collaboration(self, agent_id1: str, agent_id2: str) -> None:
        """
        Record collaboration between agents.

        Args:
            agent_id1: First agent
            agent_id2: Second agent
        """
        # Update affinity scores
        if agent_id1 not in self._agent_affinity:
            self._agent_affinity[agent_id1] = {}

        if agent_id2 not in self._agent_affinity:
            self._agent_affinity[agent_id2] = {}

        # Increase affinity
        self._agent_affinity[agent_id1][agent_id2] = \
            self._agent_affinity[agent_id1].get(agent_id2, 0) + 1

        self._agent_affinity[agent_id2][agent_id1] = \
            self._agent_affinity[agent_id2].get(agent_id1, 0) + 1


class EscalationManager:
    """
    Manages task escalation in agent hierarchy.

    Escalation triggers:
    - Worker unable to complete task
    - High-risk operations
    - Conflicts requiring coordination
    - Human approval needed
    """

    def __init__(self, hierarchy: AgentHierarchy):
        """
        Initialize escalation manager.

        Args:
            hierarchy: Agent hierarchy
        """
        self._hierarchy = hierarchy

        logger.info("Escalation Manager initialized")

    async def escalate_task(
        self,
        task: AgentTask,
        from_agent_id: str,
        reason: str,
    ) -> Optional[HierarchicalAgent]:
        """
        Escalate task to parent agent.

        Args:
            task: Task to escalate
            from_agent_id: Agent escalating task
            reason: Escalation reason

        Returns:
            Parent agent or None
        """
        parent = self._hierarchy.get_parent(from_agent_id)

        if not parent:
            logger.warning(
                f"No parent found for escalation from {from_agent_id}"
            )
            return None

        logger.info(
            f"Task escalated: {from_agent_id} -> {parent.agent_id} "
            f"(reason: {reason})"
        )

        return parent

    async def escalate_to_human(
        self,
        task: AgentTask,
        from_agent_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Escalate task to human operator.

        Args:
            task: Task requiring human attention
            from_agent_id: Agent requesting escalation
            reason: Escalation reason

        Returns:
            Escalation record
        """
        escalation = {
            "task_id": str(task.id),
            "from_agent": from_agent_id,
            "reason": reason,
            "escalated_at": datetime.utcnow().isoformat(),
            "status": "pending_human_review",
        }

        logger.warning(
            f"Human escalation: {from_agent_id} "
            f"(task={task.id}, reason={reason})"
        )

        # In production, send to human review queue
        return escalation
