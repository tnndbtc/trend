"""
Circuit Breaker for Agent Control Plane.

Prevents runaway agent behavior and cascading failures.
"""

from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker state."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit tripped, blocking operations
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""

    # Failure threshold before opening circuit
    failure_threshold: int = 5

    # Success threshold before closing circuit from half-open
    success_threshold: int = 2

    # Time window for counting failures
    window_seconds: int = 60

    # Time to wait before entering half-open state
    cooldown_seconds: int = 60

    # Max time circuit can stay open
    max_open_duration_seconds: int = 300


@dataclass
class CircuitRecord:
    """Record of circuit breaker state."""

    circuit_id: str
    state: CircuitState
    trip_reason: Optional[str] = None
    tripped_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    failure_count: int = 0
    success_count: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class CircuitBreaker:
    """
    Circuit breaker for agent operations.

    Prevents:
    - Runaway agent loops
    - Cascading failures
    - Resource exhaustion

    Usage:
        breaker = CircuitBreaker()

        # Check before operation
        if not breaker.can_proceed(circuit_id):
            raise CircuitOpenError("Circuit is open")

        try:
            result = await perform_operation()
            breaker.record_success(circuit_id)
        except Exception as e:
            breaker.record_failure(circuit_id, str(e))
            raise
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        """
        Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration
        """
        self._config = config or CircuitBreakerConfig()
        self._circuits: Dict[str, CircuitRecord] = {}

        logger.info(
            f"Circuit Breaker initialized "
            f"(failure_threshold={self._config.failure_threshold}, "
            f"cooldown={self._config.cooldown_seconds}s)"
        )

    def can_proceed(self, circuit_id: str) -> bool:
        """
        Check if operation can proceed.

        Args:
            circuit_id: Circuit identifier

        Returns:
            True if operation can proceed
        """
        circuit = self._get_or_create_circuit(circuit_id)

        # Check state transitions
        self._update_circuit_state(circuit)

        if circuit.state == CircuitState.OPEN:
            logger.warning(f"Circuit OPEN: {circuit_id} - blocking operation")
            return False

        return True

    def record_success(self, circuit_id: str) -> None:
        """
        Record successful operation.

        Args:
            circuit_id: Circuit identifier
        """
        circuit = self._get_or_create_circuit(circuit_id)

        circuit.last_success_at = datetime.utcnow()
        circuit.success_count += 1
        circuit.consecutive_successes += 1
        circuit.consecutive_failures = 0

        # Check if we should close circuit
        if circuit.state == CircuitState.HALF_OPEN:
            if circuit.consecutive_successes >= self._config.success_threshold:
                self._close_circuit(circuit)

        logger.debug(
            f"Circuit success: {circuit_id} "
            f"(consecutive={circuit.consecutive_successes})"
        )

    def record_failure(
        self,
        circuit_id: str,
        reason: Optional[str] = None,
    ) -> None:
        """
        Record failed operation.

        Args:
            circuit_id: Circuit identifier
            reason: Failure reason
        """
        circuit = self._get_or_create_circuit(circuit_id)

        circuit.last_failure_at = datetime.utcnow()
        circuit.failure_count += 1
        circuit.consecutive_failures += 1
        circuit.consecutive_successes = 0

        # Check if we should trip circuit
        if circuit.state == CircuitState.CLOSED:
            if self._should_trip_circuit(circuit):
                self._trip_circuit(circuit, reason)

        # If in half-open, return to open
        elif circuit.state == CircuitState.HALF_OPEN:
            self._trip_circuit(circuit, "Failed during recovery")

        logger.warning(
            f"Circuit failure: {circuit_id} "
            f"(consecutive={circuit.consecutive_failures}, reason={reason})"
        )

    def trip(
        self,
        circuit_id: str,
        reason: str,
    ) -> None:
        """
        Manually trip circuit.

        Use for detected loops or abnormal conditions.

        Args:
            circuit_id: Circuit identifier
            reason: Reason for tripping
        """
        circuit = self._get_or_create_circuit(circuit_id)
        self._trip_circuit(circuit, reason)

        logger.error(f"Circuit manually tripped: {circuit_id} - {reason}")

    def reset(self, circuit_id: str) -> None:
        """
        Manually reset circuit.

        Args:
            circuit_id: Circuit identifier
        """
        circuit = self._get_or_create_circuit(circuit_id)
        self._close_circuit(circuit)

        logger.info(f"Circuit manually reset: {circuit_id}")

    def get_circuit_state(self, circuit_id: str) -> CircuitState:
        """
        Get circuit state.

        Args:
            circuit_id: Circuit identifier

        Returns:
            Circuit state
        """
        circuit = self._get_or_create_circuit(circuit_id)
        self._update_circuit_state(circuit)
        return circuit.state

    def get_circuit_record(self, circuit_id: str) -> CircuitRecord:
        """
        Get circuit record.

        Args:
            circuit_id: Circuit identifier

        Returns:
            Circuit record
        """
        return self._get_or_create_circuit(circuit_id)

    def get_all_circuits(self) -> List[CircuitRecord]:
        """
        Get all circuit records.

        Returns:
            List of circuit records
        """
        return list(self._circuits.values())

    def _get_or_create_circuit(self, circuit_id: str) -> CircuitRecord:
        """
        Get or create circuit record.

        Args:
            circuit_id: Circuit identifier

        Returns:
            Circuit record
        """
        if circuit_id not in self._circuits:
            self._circuits[circuit_id] = CircuitRecord(
                circuit_id=circuit_id,
                state=CircuitState.CLOSED,
            )

        return self._circuits[circuit_id]

    def _update_circuit_state(self, circuit: CircuitRecord) -> None:
        """
        Update circuit state based on time and conditions.

        Args:
            circuit: Circuit record
        """
        if circuit.state == CircuitState.OPEN:
            # Check if cooldown period has elapsed
            if circuit.tripped_at:
                cooldown_elapsed = datetime.utcnow() - circuit.tripped_at
                if cooldown_elapsed >= timedelta(seconds=self._config.cooldown_seconds):
                    circuit.state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit entering HALF_OPEN: {circuit.circuit_id}")

        # Reset failure count if window has elapsed
        if circuit.last_failure_at:
            window_elapsed = datetime.utcnow() - circuit.last_failure_at
            if window_elapsed >= timedelta(seconds=self._config.window_seconds):
                circuit.failure_count = 0
                circuit.consecutive_failures = 0

    def _should_trip_circuit(self, circuit: CircuitRecord) -> bool:
        """
        Check if circuit should be tripped.

        Args:
            circuit: Circuit record

        Returns:
            True if circuit should be tripped
        """
        # Check consecutive failures
        if circuit.consecutive_failures >= self._config.failure_threshold:
            return True

        # Check failure count within window
        if circuit.failure_count >= self._config.failure_threshold:
            if circuit.last_failure_at:
                window_elapsed = datetime.utcnow() - circuit.last_failure_at
                if window_elapsed <= timedelta(seconds=self._config.window_seconds):
                    return True

        return False

    def _trip_circuit(self, circuit: CircuitRecord, reason: Optional[str]) -> None:
        """
        Trip circuit to open state.

        Args:
            circuit: Circuit record
            reason: Reason for tripping
        """
        circuit.state = CircuitState.OPEN
        circuit.tripped_at = datetime.utcnow()
        circuit.trip_reason = reason

        logger.error(
            f"Circuit TRIPPED: {circuit.circuit_id} - {reason} "
            f"(failures={circuit.failure_count})"
        )

    def _close_circuit(self, circuit: CircuitRecord) -> None:
        """
        Close circuit to normal operation.

        Args:
            circuit: Circuit record
        """
        circuit.state = CircuitState.CLOSED
        circuit.tripped_at = None
        circuit.trip_reason = None
        circuit.failure_count = 0
        circuit.consecutive_failures = 0

        logger.info(
            f"Circuit CLOSED: {circuit.circuit_id} "
            f"(successes={circuit.success_count})"
        )


class FeedbackLoopDetector:
    """
    Detects feedback loops in agent operations.

    Strategies:
    - Correlation ID cycle detection
    - Task pattern oscillation
    - Exponential task growth
    """

    def __init__(self, max_chain_depth: int = 20):
        """
        Initialize loop detector.

        Args:
            max_chain_depth: Max causality chain depth before warning
        """
        self._max_chain_depth = max_chain_depth
        self._correlation_chains: Dict[str, List[str]] = {}

        logger.info(f"Loop Detector initialized (max_depth={max_chain_depth})")

    async def check_causality_chain(
        self,
        correlation_id: str,
        task_id: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if task creates a feedback loop.

        Args:
            correlation_id: Correlation ID
            task_id: Task ID

        Returns:
            Tuple of (loop_detected, reason)
        """
        # Get or create chain
        if correlation_id not in self._correlation_chains:
            self._correlation_chains[correlation_id] = []

        chain = self._correlation_chains[correlation_id]

        # Check for cycle (same task appears twice in chain)
        if task_id in chain:
            logger.error(
                f"Feedback loop detected: task {task_id} appears in "
                f"correlation chain {correlation_id}"
            )
            return (True, f"Task {task_id} creates cycle in causality chain")

        # Check chain depth
        if len(chain) >= self._max_chain_depth:
            logger.warning(
                f"Deep causality chain detected: {correlation_id} "
                f"(depth={len(chain)})"
            )
            return (True, f"Causality chain exceeds max depth ({self._max_chain_depth})")

        # Add task to chain
        chain.append(task_id)

        return (False, None)

    def get_chain(self, correlation_id: str) -> List[str]:
        """
        Get causality chain.

        Args:
            correlation_id: Correlation ID

        Returns:
            List of task IDs in chain
        """
        return self._correlation_chains.get(correlation_id, [])

    def cleanup_old_chains(
        self,
        max_age: timedelta = timedelta(hours=1),
    ) -> int:
        """
        Clean up old causality chains.

        Args:
            max_age: Maximum age for chains

        Returns:
            Number of chains removed
        """
        # In production, store timestamps with chains and clean up old ones
        # For now, just limit total number of chains
        MAX_CHAINS = 1000

        if len(self._correlation_chains) > MAX_CHAINS:
            # Remove oldest 10%
            to_remove = len(self._correlation_chains) - int(MAX_CHAINS * 0.9)
            keys_to_remove = list(self._correlation_chains.keys())[:to_remove]

            for key in keys_to_remove:
                del self._correlation_chains[key]

            logger.info(f"Cleaned up {to_remove} old causality chains")
            return to_remove

        return 0


class CircuitOpenError(Exception):
    """Exception raised when circuit is open."""

    pass
