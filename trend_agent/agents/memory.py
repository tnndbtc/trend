"""
Three-Tier Memory Architecture for Agent Control Plane.

Prevents semantic drift through immutable ground truth and lineage tracking.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from uuid import UUID, uuid4
import hashlib
import json
import logging

from trend_agent.agents.correlation import get_correlation_id

logger = logging.getLogger(__name__)


class MemoryTier(Enum):
    """Memory tier levels."""

    GROUND_TRUTH = "ground_truth"  # Immutable source data
    SYNTHESIZED = "synthesized"  # LLM-generated, linked to sources
    EPHEMERAL = "ephemeral"  # Session-scoped, TTL-based


class SourceType(Enum):
    """Source type for ground truth."""

    DATABASE = "database"
    API_RESPONSE = "api_response"
    WEB_SCRAPE = "web_scrape"
    USER_INPUT = "user_input"
    FILE_UPLOAD = "file_upload"
    SENSOR_DATA = "sensor_data"


@dataclass
class MemoryEntry:
    """
    Base memory entry with provenance tracking.

    All memory entries include:
    - Unique ID
    - Content
    - Provenance (source information)
    - Lineage (derivation chain)
    - Integrity (cryptographic signature)
    """

    # Identity
    id: UUID = field(default_factory=uuid4)
    tier: MemoryTier = MemoryTier.EPHEMERAL

    # Content
    content: str = ""
    content_type: str = "text/plain"
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Provenance
    source_type: Optional[SourceType] = None
    source_id: str = ""
    created_by: str = ""  # Agent ID or system component
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Lineage
    derived_from: List[str] = field(default_factory=list)  # Source memory IDs
    correlation_id: str = ""
    generation: int = 0  # Steps from ground truth (0 = ground truth)

    # Integrity
    signature: str = ""  # SHA-256 hash of content + metadata
    version: int = 1

    # Lifecycle
    ttl: Optional[timedelta] = None
    expires_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None

    def __post_init__(self):
        """Compute signature and set correlation ID."""
        if not self.signature:
            self.signature = self._compute_signature()

        if not self.correlation_id:
            self.correlation_id = get_correlation_id()

        if self.ttl and not self.expires_at:
            self.expires_at = self.created_at + self.ttl

    def _compute_signature(self) -> str:
        """
        Compute cryptographic signature.

        Includes:
        - Content
        - Metadata (sorted for determinism)
        - Source information
        - Creation timestamp

        Returns:
            SHA-256 hash
        """
        signature_data = {
            "content": self.content,
            "content_type": self.content_type,
            "metadata": dict(sorted(self.metadata.items())),
            "source_type": self.source_type.value if self.source_type else None,
            "source_id": self.source_id,
            "created_at": self.created_at.isoformat(),
        }

        signature_json = json.dumps(signature_data, sort_keys=True)
        return hashlib.sha256(signature_json.encode()).hexdigest()

    def verify_integrity(self) -> bool:
        """
        Verify memory integrity.

        Returns:
            True if signature matches current content
        """
        current_signature = self._compute_signature()
        return current_signature == self.signature

    def is_expired(self) -> bool:
        """
        Check if memory has expired.

        Returns:
            True if expired
        """
        if not self.expires_at:
            return False

        return datetime.utcnow() >= self.expires_at


@dataclass
class GroundTruthMemory(MemoryEntry):
    """
    Immutable source data memory.

    Characteristics:
    - Cannot be modified after creation
    - No derivation chain (generation = 0)
    - No expiration
    - Must have source information
    """

    tier: MemoryTier = field(default=MemoryTier.GROUND_TRUTH, init=False)
    generation: int = field(default=0, init=False)
    ttl: Optional[timedelta] = field(default=None, init=False)

    def __post_init__(self):
        """Validate ground truth constraints."""
        super().__post_init__()

        if not self.source_type:
            raise ValueError("Ground truth must have source_type")

        if not self.source_id:
            raise ValueError("Ground truth must have source_id")


@dataclass
class SynthesizedMemory(MemoryEntry):
    """
    LLM-generated memory linked to sources.

    Characteristics:
    - Derived from ground truth or other synthesized memories
    - Tracks generation distance from ground truth
    - Includes synthesis metadata (model, prompt, parameters)
    """

    tier: MemoryTier = field(default=MemoryTier.SYNTHESIZED, init=False)

    # Synthesis metadata
    synthesis_model: str = ""
    synthesis_prompt: str = ""
    synthesis_parameters: Dict[str, Any] = field(default_factory=dict)
    synthesis_cost: float = 0.0

    def __post_init__(self):
        """Validate synthesized memory constraints."""
        super().__post_init__()

        if not self.derived_from:
            raise ValueError("Synthesized memory must be derived from sources")

        if self.generation < 1:
            raise ValueError("Synthesized memory must have generation >= 1")


@dataclass
class EphemeralMemory(MemoryEntry):
    """
    Session-scoped memory with TTL.

    Characteristics:
    - Short-lived (default 1 hour)
    - Used for temporary agent state
    - Automatically expires
    """

    tier: MemoryTier = field(default=MemoryTier.EPHEMERAL, init=False)
    ttl: Optional[timedelta] = field(default_factory=lambda: timedelta(hours=1))


class MemoryStore:
    """
    Three-tier memory storage with lineage tracking.

    Features:
    - Segregated storage by tier
    - Provenance tracking
    - Lineage queries
    - Drift detection
    - Automatic cleanup of expired memories
    """

    def __init__(self):
        """Initialize memory store."""
        self._memories: Dict[str, MemoryEntry] = {}
        self._ground_truth_index: Dict[str, List[str]] = {}  # source_id -> memory_ids
        self._lineage_index: Dict[str, List[str]] = {}  # parent_id -> child_ids

        logger.info("Memory Store initialized")

    async def store(self, memory: MemoryEntry) -> str:
        """
        Store memory entry.

        Args:
            memory: Memory to store

        Returns:
            Memory ID
        """
        memory_id = str(memory.id)

        # Validate integrity
        if not memory.verify_integrity():
            raise ValueError("Memory integrity check failed")

        # Store memory
        self._memories[memory_id] = memory

        # Update indices
        if memory.tier == MemoryTier.GROUND_TRUTH and memory.source_id:
            if memory.source_id not in self._ground_truth_index:
                self._ground_truth_index[memory.source_id] = []
            self._ground_truth_index[memory.source_id].append(memory_id)

        # Update lineage index
        for parent_id in memory.derived_from:
            if parent_id not in self._lineage_index:
                self._lineage_index[parent_id] = []
            self._lineage_index[parent_id].append(memory_id)

        logger.debug(
            f"Memory stored: {memory_id} "
            f"(tier={memory.tier.value}, generation={memory.generation})"
        )

        return memory_id

    async def retrieve(self, memory_id: str) -> Optional[MemoryEntry]:
        """
        Retrieve memory by ID.

        Args:
            memory_id: Memory ID

        Returns:
            Memory entry or None
        """
        memory = self._memories.get(memory_id)

        if memory and memory.is_expired():
            logger.warning(f"Memory expired: {memory_id}")
            return None

        return memory

    async def find_ground_truth(self, source_id: str) -> List[MemoryEntry]:
        """
        Find ground truth memories by source ID.

        Args:
            source_id: Source identifier

        Returns:
            List of ground truth memories
        """
        memory_ids = self._ground_truth_index.get(source_id, [])
        memories = []

        for memory_id in memory_ids:
            memory = await self.retrieve(memory_id)
            if memory:
                memories.append(memory)

        return memories

    async def get_lineage_chain(
        self,
        memory_id: str,
    ) -> List[MemoryEntry]:
        """
        Get full lineage chain from ground truth to memory.

        Args:
            memory_id: Memory ID

        Returns:
            List of memories in lineage chain (oldest to newest)
        """
        memory = await self.retrieve(memory_id)
        if not memory:
            return []

        chain = []

        # Recursively traverse to ground truth
        async def traverse(mem: MemoryEntry):
            # Get parent memories
            for parent_id in mem.derived_from:
                parent = await self.retrieve(parent_id)
                if parent:
                    await traverse(parent)

            chain.append(mem)

        await traverse(memory)

        return chain

    async def get_derived_memories(
        self,
        memory_id: str,
    ) -> List[MemoryEntry]:
        """
        Get all memories derived from this memory.

        Args:
            memory_id: Memory ID

        Returns:
            List of derived memories
        """
        child_ids = self._lineage_index.get(memory_id, [])
        memories = []

        for child_id in child_ids:
            memory = await self.retrieve(child_id)
            if memory:
                memories.append(memory)

        return memories

    async def search(
        self,
        query: str,
        tier: Optional[MemoryTier] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """
        Search memories by content.

        Args:
            query: Search query
            tier: Optional tier filter
            limit: Maximum results

        Returns:
            List of matching memories
        """
        results = []
        query_lower = query.lower()

        for memory in self._memories.values():
            # Skip expired
            if memory.is_expired():
                continue

            # Filter by tier
            if tier and memory.tier != tier:
                continue

            # Simple text search (in production, use vector embeddings)
            if query_lower in memory.content.lower():
                results.append(memory)

            if len(results) >= limit:
                break

        return results

    async def cleanup_expired(self) -> int:
        """
        Remove expired memories.

        Returns:
            Number of memories removed
        """
        expired = []

        for memory_id, memory in self._memories.items():
            if memory.is_expired():
                expired.append(memory_id)

        for memory_id in expired:
            del self._memories[memory_id]

            # Remove from lineage index
            for child_list in self._lineage_index.values():
                if memory_id in child_list:
                    child_list.remove(memory_id)

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired memories")

        return len(expired)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get memory store statistics.

        Returns:
            Statistics dictionary
        """
        tier_counts = {tier: 0 for tier in MemoryTier}

        for memory in self._memories.values():
            tier_counts[memory.tier] += 1

        return {
            "total_memories": len(self._memories),
            "by_tier": {tier.value: count for tier, count in tier_counts.items()},
            "ground_truth_sources": len(self._ground_truth_index),
            "lineage_edges": sum(len(children) for children in self._lineage_index.values()),
        }


class DriftDetector:
    """
    Detects semantic drift in synthesized memories.

    Strategies:
    - Compare synthesized content to ground truth
    - Detect contradictions in lineage chain
    - Flag high-generation memories for review
    """

    def __init__(
        self,
        max_generation: int = 5,
        similarity_threshold: float = 0.7,
    ):
        """
        Initialize drift detector.

        Args:
            max_generation: Max generation before flagging
            similarity_threshold: Min similarity to ground truth
        """
        self._max_generation = max_generation
        self._similarity_threshold = similarity_threshold

        logger.info(
            f"Drift Detector initialized "
            f"(max_generation={max_generation}, "
            f"threshold={similarity_threshold})"
        )

    async def check_drift(
        self,
        memory: MemoryEntry,
        memory_store: MemoryStore,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if memory has drifted from ground truth.

        Args:
            memory: Memory to check
            memory_store: Memory store

        Returns:
            Tuple of (has_drifted, reason)
        """
        # Check generation distance
        if memory.generation > self._max_generation:
            return (
                True,
                f"Generation {memory.generation} exceeds maximum {self._max_generation}",
            )

        # For synthesized memories, compare to ground truth
        if memory.tier == MemoryTier.SYNTHESIZED:
            # Get lineage chain
            chain = await memory_store.get_lineage_chain(str(memory.id))

            # Find ground truth in chain
            ground_truth = next(
                (m for m in chain if m.tier == MemoryTier.GROUND_TRUTH),
                None,
            )

            if not ground_truth:
                return (True, "No ground truth found in lineage")

            # Simple similarity check (in production, use embeddings)
            similarity = self._compute_similarity(memory.content, ground_truth.content)

            if similarity < self._similarity_threshold:
                return (
                    True,
                    f"Similarity {similarity:.2f} below threshold {self._similarity_threshold}",
                )

        return (False, None)

    def _compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute text similarity.

        Simple implementation using character overlap.
        In production, use sentence transformers or embeddings.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0-1)
        """
        # Convert to sets of words
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        # Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0
