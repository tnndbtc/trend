"""
Lineage Graph for Causality Tracking.

Provides visualization and querying of agent operation causality chains.
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions in lineage graph."""

    TASK_SUBMITTED = "task_submitted"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TOOL_CALLED = "tool_called"
    MEMORY_CREATED = "memory_created"
    MEMORY_ACCESSED = "memory_accessed"
    EVENT_EMITTED = "event_emitted"
    EVENT_RECEIVED = "event_received"
    API_CALLED = "api_called"
    DATA_MODIFIED = "data_modified"


@dataclass
class LineageNode:
    """Node in lineage graph representing an action."""

    # Identity
    node_id: str
    action_type: ActionType
    correlation_id: str

    # Action details
    agent_id: Optional[str] = None
    resource_id: Optional[str] = None  # Task ID, memory ID, etc.
    resource_type: Optional[str] = None

    # Timing
    timestamp: datetime = field(default_factory=datetime.utcnow)

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LineageEdge:
    """Edge in lineage graph representing causality."""

    source_id: str  # Node ID that caused action
    target_id: str  # Node ID of resulting action
    edge_type: str = "caused"  # Relationship type
    metadata: Dict[str, Any] = field(default_factory=dict)


class LineageTracker:
    """
    Tracks and queries causality chains.

    Features:
    - Record agent actions
    - Build causality graph
    - Query lineage chains
    - Detect cycles
    - Export for visualization
    """

    def __init__(self):
        """Initialize lineage tracker."""
        self._nodes: Dict[str, LineageNode] = {}
        self._edges: List[LineageEdge] = []
        self._correlation_nodes: Dict[str, List[str]] = {}  # correlation_id -> node_ids
        self._adjacency: Dict[str, List[str]] = {}  # node_id -> [child_node_ids]

        logger.info("Lineage Tracker initialized")

    async def record_action(
        self,
        correlation_id: str,
        action_type: ActionType,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Record an action in lineage graph.

        Args:
            correlation_id: Correlation ID
            action_type: Type of action
            source_id: Optional source node ID (for causality edge)
            target_id: Optional target resource ID
            agent_id: Agent performing action
            resource_id: ID of resource affected
            resource_type: Type of resource
            metadata: Additional metadata

        Returns:
            Node ID
        """
        # Create node
        node_id = f"{correlation_id}:{action_type.value}:{datetime.utcnow().timestamp()}"

        node = LineageNode(
            node_id=node_id,
            action_type=action_type,
            correlation_id=correlation_id,
            agent_id=agent_id,
            resource_id=resource_id or target_id,
            resource_type=resource_type,
            metadata=metadata or {},
        )

        # Store node
        self._nodes[node_id] = node

        # Index by correlation ID
        if correlation_id not in self._correlation_nodes:
            self._correlation_nodes[correlation_id] = []
        self._correlation_nodes[correlation_id].append(node_id)

        # Create causality edge if source provided
        if source_id and source_id in self._nodes:
            edge = LineageEdge(
                source_id=source_id,
                target_id=node_id,
                edge_type="caused",
            )
            self._edges.append(edge)

            # Update adjacency list
            if source_id not in self._adjacency:
                self._adjacency[source_id] = []
            self._adjacency[source_id].append(node_id)

        logger.debug(
            f"Lineage recorded: {node_id} "
            f"(action={action_type.value}, correlation={correlation_id})"
        )

        return node_id

    async def get_causality_chain(
        self,
        correlation_id: str,
    ) -> List[LineageNode]:
        """
        Get full causality chain for correlation ID.

        Args:
            correlation_id: Correlation ID

        Returns:
            List of nodes in chronological order
        """
        node_ids = self._correlation_nodes.get(correlation_id, [])
        nodes = [self._nodes[nid] for nid in node_ids if nid in self._nodes]

        # Sort by timestamp
        nodes.sort(key=lambda n: n.timestamp)

        return nodes

    async def get_node_ancestors(
        self,
        node_id: str,
    ) -> List[LineageNode]:
        """
        Get all ancestor nodes (nodes that caused this node).

        Args:
            node_id: Node ID

        Returns:
            List of ancestor nodes
        """
        ancestors = []
        visited: Set[str] = set()

        # Find edges pointing to this node
        def traverse(nid: str):
            if nid in visited:
                return

            visited.add(nid)

            # Find parent edges
            for edge in self._edges:
                if edge.target_id == nid:
                    if edge.source_id in self._nodes:
                        ancestors.append(self._nodes[edge.source_id])
                        traverse(edge.source_id)

        traverse(node_id)

        return ancestors

    async def get_node_descendants(
        self,
        node_id: str,
    ) -> List[LineageNode]:
        """
        Get all descendant nodes (nodes caused by this node).

        Args:
            node_id: Node ID

        Returns:
            List of descendant nodes
        """
        descendants = []
        visited: Set[str] = set()

        def traverse(nid: str):
            if nid in visited:
                return

            visited.add(nid)

            # Get children from adjacency list
            for child_id in self._adjacency.get(nid, []):
                if child_id in self._nodes:
                    descendants.append(self._nodes[child_id])
                    traverse(child_id)

        traverse(node_id)

        return descendants

    async def detect_cycle(
        self,
        correlation_id: str,
    ) -> tuple[bool, Optional[List[str]]]:
        """
        Detect cycles in causality chain.

        Args:
            correlation_id: Correlation ID

        Returns:
            Tuple of (has_cycle, cycle_path)
        """
        node_ids = self._correlation_nodes.get(correlation_id, [])

        # Build subgraph for this correlation
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        cycle_path: List[str] = []

        def has_cycle_util(nid: str, path: List[str]) -> bool:
            visited.add(nid)
            rec_stack.add(nid)
            path.append(nid)

            # Check all children
            for child_id in self._adjacency.get(nid, []):
                if child_id not in node_ids:
                    continue  # Only check within correlation

                if child_id not in visited:
                    if has_cycle_util(child_id, path):
                        return True
                elif child_id in rec_stack:
                    # Cycle detected
                    cycle_start = path.index(child_id)
                    cycle_path.extend(path[cycle_start:])
                    return True

            path.pop()
            rec_stack.remove(nid)
            return False

        for node_id in node_ids:
            if node_id not in visited:
                if has_cycle_util(node_id, []):
                    logger.error(
                        f"Cycle detected in correlation {correlation_id}: "
                        f"{' -> '.join(cycle_path)}"
                    )
                    return (True, cycle_path)

        return (False, None)

    async def build_lineage_graph(
        self,
        correlation_id: str,
    ) -> Dict[str, Any]:
        """
        Build lineage graph structure for visualization.

        Returns NetworkX-compatible graph structure.

        Args:
            correlation_id: Correlation ID

        Returns:
            Graph dictionary with nodes and edges
        """
        chain = await self.get_causality_chain(correlation_id)

        # Build graph structure
        nodes = []
        edges = []

        for node in chain:
            nodes.append({
                "id": node.node_id,
                "label": f"{node.action_type.value}\n{node.agent_id or 'system'}",
                "action_type": node.action_type.value,
                "agent_id": node.agent_id,
                "resource_id": node.resource_id,
                "timestamp": node.timestamp.isoformat(),
                "metadata": node.metadata,
            })

        # Filter edges for this correlation
        node_ids = {n.node_id for n in chain}
        for edge in self._edges:
            if edge.source_id in node_ids and edge.target_id in node_ids:
                edges.append({
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "type": edge.edge_type,
                    "metadata": edge.metadata,
                })

        return {
            "correlation_id": correlation_id,
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }

    async def export_dot(
        self,
        correlation_id: str,
    ) -> str:
        """
        Export lineage graph as Graphviz DOT format.

        Args:
            correlation_id: Correlation ID

        Returns:
            DOT format string
        """
        graph = await self.build_lineage_graph(correlation_id)

        lines = [
            "digraph lineage {",
            '  rankdir=TB;',
            '  node [shape=box, style=rounded];',
            ""
        ]

        # Add nodes
        for node in graph["nodes"]:
            label = node["label"].replace("\n", "\\n")
            color = self._get_node_color(node["action_type"])
            lines.append(f'  "{node["id"]}" [label="{label}", fillcolor="{color}", style=filled];')

        lines.append("")

        # Add edges
        for edge in graph["edges"]:
            lines.append(f'  "{edge["source"]}" -> "{edge["target"]}";')

        lines.append("}")

        return "\n".join(lines)

    def _get_node_color(self, action_type: str) -> str:
        """
        Get color for node based on action type.

        Args:
            action_type: Action type

        Returns:
            Color name
        """
        color_map = {
            "task_submitted": "lightblue",
            "task_started": "lightgreen",
            "task_completed": "palegreen",
            "tool_called": "lightyellow",
            "memory_created": "plum",
            "memory_accessed": "lavender",
            "event_emitted": "orange",
            "event_received": "peachpuff",
            "api_called": "lightcyan",
            "data_modified": "pink",
        }
        return color_map.get(action_type, "white")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get lineage statistics.

        Returns:
            Statistics dictionary
        """
        action_counts = {}
        for node in self._nodes.values():
            action_type = node.action_type.value
            action_counts[action_type] = action_counts.get(action_type, 0) + 1

        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "total_correlations": len(self._correlation_nodes),
            "action_counts": action_counts,
        }

    async def cleanup_old_lineage(
        self,
        max_age_hours: int = 24,
    ) -> int:
        """
        Clean up old lineage data.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of nodes removed
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        old_nodes = []

        for node_id, node in self._nodes.items():
            if node.timestamp < cutoff:
                old_nodes.append(node_id)

        # Remove nodes
        for node_id in old_nodes:
            node = self._nodes.pop(node_id)

            # Remove from correlation index
            if node.correlation_id in self._correlation_nodes:
                self._correlation_nodes[node.correlation_id].remove(node_id)

            # Remove from adjacency list
            self._adjacency.pop(node_id, None)

        # Remove edges
        self._edges = [
            e for e in self._edges
            if e.source_id not in old_nodes and e.target_id not in old_nodes
        ]

        if old_nodes:
            logger.info(f"Cleaned up {len(old_nodes)} old lineage nodes")

        return len(old_nodes)
