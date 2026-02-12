"""
Budget Engine for Agent Control Plane.

Provides multi-dimensional budget tracking and enforcement.
"""

from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class BudgetType(Enum):
    """Budget dimension types."""

    COST = "cost"  # Dollar cost
    TOKENS = "tokens"  # LLM tokens
    TIME = "time"  # Execution time (seconds)
    CONCURRENCY = "concurrency"  # Concurrent operations
    API_CALLS = "api_calls"  # Number of API calls


@dataclass
class BudgetLimit:
    """Budget limit for a dimension."""

    budget_type: BudgetType
    limit: float
    period: timedelta  # Time period for limit (e.g., daily, hourly)
    soft_limit: Optional[float] = None  # Warning threshold


@dataclass
class BudgetUsage:
    """Budget usage tracking."""

    budget_type: BudgetType
    used: float = 0.0
    reserved: float = 0.0
    last_reset_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BudgetAllocation:
    """Budget allocation for an agent or task."""

    agent_id: str
    limits: Dict[BudgetType, BudgetLimit]
    usage: Dict[BudgetType, BudgetUsage] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class BudgetReservation:
    """Temporary budget reservation."""

    reservation_id: str
    agent_id: str
    budget_type: BudgetType
    amount: float
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


class BudgetEngine:
    """
    Multi-dimensional budget tracking and enforcement.

    Features:
    - Per-agent budget limits
    - Multiple budget dimensions (cost, tokens, time, etc.)
    - Budget reservations (pre-allocate before execution)
    - Automatic reset based on time periods
    - Soft limits (warnings) and hard limits (blocks)
    - Budget alerts and notifications
    """

    # Token pricing (approximate, per 1000 tokens)
    TOKEN_PRICING = {
        "gpt-4": {"prompt": 0.03, "completion": 0.06},
        "gpt-4-turbo": {"prompt": 0.01, "completion": 0.03},
        "gpt-3.5-turbo": {"prompt": 0.0005, "completion": 0.0015},
        "claude-3-opus": {"prompt": 0.015, "completion": 0.075},
        "claude-3-sonnet": {"prompt": 0.003, "completion": 0.015},
    }

    def __init__(self):
        """Initialize budget engine."""
        self._allocations: Dict[str, BudgetAllocation] = {}
        self._reservations: Dict[str, BudgetReservation] = {}

        logger.info("Budget Engine initialized")

    def create_allocation(
        self,
        agent_id: str,
        limits: Dict[BudgetType, BudgetLimit],
    ) -> BudgetAllocation:
        """
        Create budget allocation for agent.

        Args:
            agent_id: Agent ID
            limits: Budget limits by type

        Returns:
            Budget allocation
        """
        allocation = BudgetAllocation(
            agent_id=agent_id,
            limits=limits,
            usage={
                budget_type: BudgetUsage(budget_type=budget_type)
                for budget_type in limits.keys()
            },
        )

        self._allocations[agent_id] = allocation

        logger.info(
            f"Budget allocation created for {agent_id}: "
            f"{', '.join(f'{bt.value}={limit.limit}' for bt, limit in limits.items())}"
        )

        return allocation

    def check_budget(
        self,
        agent_id: str,
        budget_type: BudgetType,
        amount: float,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if agent has budget available.

        Args:
            agent_id: Agent ID
            budget_type: Budget dimension to check
            amount: Amount to check

        Returns:
            Tuple of (has_budget, rejection_reason)
        """
        allocation = self._allocations.get(agent_id)
        if not allocation:
            logger.warning(f"No budget allocation for agent {agent_id}")
            return (True, None)  # No limits = allowed

        if budget_type not in allocation.limits:
            return (True, None)  # No limit for this dimension

        limit = allocation.limits[budget_type]
        usage = allocation.usage[budget_type]

        # Check if period has elapsed (auto-reset)
        self._check_and_reset_period(usage, limit)

        # Calculate available budget
        total_used = usage.used + usage.reserved
        available = limit.limit - total_used

        if amount > available:
            logger.warning(
                f"Budget exceeded for {agent_id} ({budget_type.value}): "
                f"requested={amount}, available={available}"
            )
            return (
                False,
                f"Insufficient {budget_type.value} budget "
                f"(requested={amount}, available={available})",
            )

        # Check soft limit (warning only)
        if limit.soft_limit and total_used + amount >= limit.soft_limit:
            logger.warning(
                f"Soft budget limit reached for {agent_id} ({budget_type.value}): "
                f"{total_used + amount}/{limit.limit}"
            )

        return (True, None)

    def reserve_budget(
        self,
        agent_id: str,
        budget_type: BudgetType,
        amount: float,
        reservation_id: str,
        expires_in: Optional[timedelta] = None,
    ) -> bool:
        """
        Reserve budget for upcoming operation.

        Args:
            agent_id: Agent ID
            budget_type: Budget dimension
            amount: Amount to reserve
            reservation_id: Unique reservation ID
            expires_in: Expiration duration

        Returns:
            True if reservation successful
        """
        # Check if budget available
        has_budget, reason = self.check_budget(agent_id, budget_type, amount)
        if not has_budget:
            logger.warning(
                f"Budget reservation failed for {agent_id}: {reason}"
            )
            return False

        allocation = self._allocations.get(agent_id)
        if allocation and budget_type in allocation.usage:
            # Reserve budget
            allocation.usage[budget_type].reserved += amount

            # Create reservation record
            expires_at = (
                datetime.utcnow() + expires_in if expires_in else None
            )
            reservation = BudgetReservation(
                reservation_id=reservation_id,
                agent_id=agent_id,
                budget_type=budget_type,
                amount=amount,
                expires_at=expires_at,
            )
            self._reservations[reservation_id] = reservation

            logger.debug(
                f"Budget reserved: {agent_id} ({budget_type.value}={amount})"
            )

        return True

    def commit_reservation(
        self,
        reservation_id: str,
        actual_amount: Optional[float] = None,
    ) -> bool:
        """
        Commit reserved budget to actual usage.

        Args:
            reservation_id: Reservation ID
            actual_amount: Actual amount used (if different from reserved)

        Returns:
            True if successful
        """
        reservation = self._reservations.get(reservation_id)
        if not reservation:
            logger.error(f"Reservation not found: {reservation_id}")
            return False

        allocation = self._allocations.get(reservation.agent_id)
        if not allocation:
            logger.error(f"Allocation not found for {reservation.agent_id}")
            return False

        usage = allocation.usage.get(reservation.budget_type)
        if not usage:
            logger.error(
                f"Usage tracking not found for {reservation.budget_type}"
            )
            return False

        # Move from reserved to used
        amount_to_use = actual_amount if actual_amount is not None else reservation.amount

        usage.reserved -= reservation.amount
        usage.used += amount_to_use

        # Remove reservation
        del self._reservations[reservation_id]

        allocation.updated_at = datetime.utcnow()

        logger.debug(
            f"Budget committed: {reservation.agent_id} "
            f"({reservation.budget_type.value}={amount_to_use})"
        )

        return True

    def release_reservation(self, reservation_id: str) -> bool:
        """
        Release reserved budget without using it.

        Args:
            reservation_id: Reservation ID

        Returns:
            True if successful
        """
        reservation = self._reservations.get(reservation_id)
        if not reservation:
            logger.error(f"Reservation not found: {reservation_id}")
            return False

        allocation = self._allocations.get(reservation.agent_id)
        if allocation and reservation.budget_type in allocation.usage:
            # Release reservation
            allocation.usage[reservation.budget_type].reserved -= reservation.amount

        # Remove reservation
        del self._reservations[reservation_id]

        logger.debug(
            f"Budget reservation released: {reservation.agent_id} "
            f"({reservation.budget_type.value}={reservation.amount})"
        )

        return True

    def record_usage(
        self,
        agent_id: str,
        budget_type: BudgetType,
        amount: float,
    ) -> None:
        """
        Record budget usage (without reservation).

        Args:
            agent_id: Agent ID
            budget_type: Budget dimension
            amount: Amount used
        """
        allocation = self._allocations.get(agent_id)
        if not allocation:
            logger.warning(f"No allocation for {agent_id}, creating default")
            # Create default allocation with high limits
            self.create_allocation(
                agent_id,
                {
                    budget_type: BudgetLimit(
                        budget_type=budget_type,
                        limit=float("inf"),
                        period=timedelta(days=30),
                    )
                },
            )
            allocation = self._allocations[agent_id]

        if budget_type not in allocation.usage:
            allocation.usage[budget_type] = BudgetUsage(budget_type=budget_type)

        allocation.usage[budget_type].used += amount
        allocation.updated_at = datetime.utcnow()

        logger.debug(
            f"Budget usage recorded: {agent_id} "
            f"({budget_type.value}={amount})"
        )

    def get_usage(
        self,
        agent_id: str,
        budget_type: Optional[BudgetType] = None,
    ) -> Dict[BudgetType, BudgetUsage]:
        """
        Get budget usage for agent.

        Args:
            agent_id: Agent ID
            budget_type: Optional specific budget type

        Returns:
            Dictionary of usage by type
        """
        allocation = self._allocations.get(agent_id)
        if not allocation:
            return {}

        if budget_type:
            usage = allocation.usage.get(budget_type)
            return {budget_type: usage} if usage else {}

        return allocation.usage.copy()

    def get_remaining(
        self,
        agent_id: str,
        budget_type: BudgetType,
    ) -> Optional[float]:
        """
        Get remaining budget.

        Args:
            agent_id: Agent ID
            budget_type: Budget dimension

        Returns:
            Remaining budget or None if no limit
        """
        allocation = self._allocations.get(agent_id)
        if not allocation or budget_type not in allocation.limits:
            return None

        limit = allocation.limits[budget_type]
        usage = allocation.usage.get(budget_type)

        if not usage:
            return limit.limit

        total_used = usage.used + usage.reserved
        return max(0, limit.limit - total_used)

    def reset_budget(
        self,
        agent_id: str,
        budget_type: Optional[BudgetType] = None,
    ) -> None:
        """
        Reset budget usage.

        Args:
            agent_id: Agent ID
            budget_type: Optional specific budget type (all if None)
        """
        allocation = self._allocations.get(agent_id)
        if not allocation:
            return

        if budget_type:
            if budget_type in allocation.usage:
                allocation.usage[budget_type].used = 0.0
                allocation.usage[budget_type].last_reset_at = datetime.utcnow()
                logger.info(f"Budget reset for {agent_id} ({budget_type.value})")
        else:
            for usage in allocation.usage.values():
                usage.used = 0.0
                usage.last_reset_at = datetime.utcnow()
            logger.info(f"All budgets reset for {agent_id}")

    def cleanup_expired_reservations(self) -> int:
        """
        Clean up expired reservations.

        Returns:
            Number of reservations cleaned up
        """
        now = datetime.utcnow()
        expired = []

        for reservation_id, reservation in self._reservations.items():
            if reservation.expires_at and reservation.expires_at <= now:
                expired.append(reservation_id)

        for reservation_id in expired:
            self.release_reservation(reservation_id)

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired reservations")

        return len(expired)

    def _check_and_reset_period(
        self,
        usage: BudgetUsage,
        limit: BudgetLimit,
    ) -> None:
        """
        Check if period has elapsed and reset usage.

        Args:
            usage: Budget usage
            limit: Budget limit
        """
        elapsed = datetime.utcnow() - usage.last_reset_at

        if elapsed >= limit.period:
            usage.used = 0.0
            usage.last_reset_at = datetime.utcnow()
            logger.info(
                f"Budget auto-reset ({usage.budget_type.value}) after "
                f"{limit.period}"
            )

    @staticmethod
    def calculate_token_cost(
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """
        Calculate cost for token usage.

        Args:
            model: Model name
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Cost in USD
        """
        pricing = BudgetEngine.TOKEN_PRICING.get(model)
        if not pricing:
            # Unknown model, use GPT-4 pricing as default
            logger.warning(f"Unknown model {model}, using GPT-4 pricing")
            pricing = BudgetEngine.TOKEN_PRICING["gpt-4"]

        prompt_cost = (prompt_tokens / 1000) * pricing["prompt"]
        completion_cost = (completion_tokens / 1000) * pricing["completion"]

        return prompt_cost + completion_cost
