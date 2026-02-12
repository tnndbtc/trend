"""
Trend State Management Service.

This module provides sophisticated trend lifecycle state detection and management.
It tracks state transitions, velocity trends, and growth patterns to accurately
classify trends across their lifecycle (EMERGING → VIRAL → SUSTAINED → DECLINING → DEAD).
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from trend_agent.schemas import Trend, TrendState, Metrics
from trend_agent.storage.interfaces import TrendRepository

logger = logging.getLogger(__name__)


# ============================================================================
# State Transition History
# ============================================================================


class StateTransition:
    """Record of a state transition."""

    def __init__(
        self,
        from_state: TrendState,
        to_state: TrendState,
        timestamp: datetime,
        reason: str,
        metrics_snapshot: Optional[Dict[str, Any]] = None,
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.timestamp = timestamp
        self.reason = reason
        self.metrics_snapshot = metrics_snapshot or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
            "metrics_snapshot": self.metrics_snapshot,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "StateTransition":
        """Create from dictionary."""
        return StateTransition(
            from_state=TrendState(data["from_state"]),
            to_state=TrendState(data["to_state"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            reason=data["reason"],
            metrics_snapshot=data.get("metrics_snapshot", {}),
        )


# ============================================================================
# Velocity Analysis
# ============================================================================


class VelocityAnalysis:
    """Analysis of trend velocity and growth patterns."""

    def __init__(
        self,
        current_velocity: float,
        velocity_trend: str,  # "accelerating", "stable", "decelerating"
        growth_rate: float,  # % change in velocity
        time_since_peak: Optional[timedelta] = None,
        is_at_peak: bool = False,
    ):
        self.current_velocity = current_velocity
        self.velocity_trend = velocity_trend
        self.growth_rate = growth_rate
        self.time_since_peak = time_since_peak
        self.is_at_peak = is_at_peak


# ============================================================================
# Trend State Service
# ============================================================================


class TrendStateService:
    """
    Service for managing trend lifecycle states.

    Provides sophisticated algorithms for:
    - State detection based on velocity and engagement patterns
    - Automatic state transitions
    - Velocity trend analysis (acceleration/deceleration)
    - State transition history tracking
    """

    # State transition thresholds
    VIRAL_VELOCITY_THRESHOLD = 100.0  # engagement/hour
    VIRAL_GROWTH_RATE_THRESHOLD = 0.5  # 50% growth rate
    SUSTAINED_MIN_HOURS = 24  # Min hours at high engagement for sustained
    DECLINING_DECELERATION_THRESHOLD = -0.3  # -30% velocity drop
    DEAD_HOURS_THRESHOLD = 72  # Hours of inactivity to declare dead

    def __init__(self, trend_repo: Optional[TrendRepository] = None):
        """
        Initialize trend state service.

        Args:
            trend_repo: Optional repository for persisting state changes
        """
        self._trend_repo = trend_repo

    async def analyze_trend(self, trend: Trend) -> TrendState:
        """
        Analyze a trend and determine its current state.

        Args:
            trend: Trend to analyze

        Returns:
            Recommended TrendState

        This method uses multiple factors:
        - Current velocity and velocity trends
        - Engagement patterns and growth rate
        - Time since first seen and peak engagement
        - Historical state transitions
        """
        # Get velocity analysis
        velocity_analysis = self._analyze_velocity(trend)

        # Get time-based metrics
        age = datetime.utcnow() - trend.first_seen
        time_since_update = datetime.utcnow() - trend.last_updated

        # Determine state based on multiple factors
        new_state = self._determine_state(
            trend=trend,
            velocity_analysis=velocity_analysis,
            age=age,
            time_since_update=time_since_update,
        )

        return new_state

    async def update_trend_state(
        self, trend: Trend, force: bool = False
    ) -> Tuple[Trend, bool]:
        """
        Update a trend's state if it has changed.

        Args:
            trend: Trend to update
            force: Force state update even if same

        Returns:
            Tuple of (updated_trend, state_changed)
        """
        old_state = trend.state
        new_state = await self.analyze_trend(trend)

        if new_state == old_state and not force:
            return trend, False

        # Record state transition
        reason = self._get_transition_reason(trend, new_state)
        self._record_state_transition(
            trend=trend,
            from_state=old_state,
            to_state=new_state,
            reason=reason,
        )

        # Update trend
        trend.state = new_state

        # Update peak engagement tracking
        if new_state == TrendState.VIRAL:
            if trend.peak_engagement_at is None:
                trend.peak_engagement_at = datetime.utcnow()
        elif new_state == TrendState.DECLINING and trend.peak_engagement_at is None:
            # Set peak to last update time if we missed the viral state
            trend.peak_engagement_at = trend.last_updated

        # Persist to database if repository available
        if self._trend_repo:
            try:
                await self._trend_repo.update(trend)
                logger.info(
                    f"Updated trend '{trend.title[:50]}' state: "
                    f"{old_state.value} → {new_state.value}"
                )
            except Exception as e:
                logger.error(f"Failed to persist state update: {e}")

        return trend, True

    async def bulk_update_states(self, trends: List[Trend]) -> Dict[str, int]:
        """
        Update states for multiple trends.

        Args:
            trends: List of trends to update

        Returns:
            Statistics dictionary with counts
        """
        stats = {
            "total": len(trends),
            "updated": 0,
            "unchanged": 0,
            "errors": 0,
        }

        for trend in trends:
            try:
                _, changed = await self.update_trend_state(trend)
                if changed:
                    stats["updated"] += 1
                else:
                    stats["unchanged"] += 1
            except Exception as e:
                logger.error(f"Error updating trend {trend.id}: {e}")
                stats["errors"] += 1

        logger.info(
            f"Bulk state update: {stats['updated']}/{stats['total']} updated, "
            f"{stats['errors']} errors"
        )

        return stats

    def get_state_history(self, trend: Trend) -> List[StateTransition]:
        """
        Get state transition history for a trend.

        Args:
            trend: Trend to get history for

        Returns:
            List of state transitions (oldest first)
        """
        history_data = trend.metadata.get("state_history", [])
        return [StateTransition.from_dict(t) for t in history_data]

    def calculate_velocity(
        self, trend: Trend, previous_velocity: Optional[float] = None
    ) -> float:
        """
        Calculate current velocity (engagement per hour).

        Args:
            trend: Trend to analyze
            previous_velocity: Optional previous velocity for comparison

        Returns:
            Velocity in engagement/hour
        """
        # Calculate time span in hours
        time_span = trend.last_updated - trend.first_seen
        hours = max(1.0, time_span.total_seconds() / 3600)

        # Calculate weighted total engagement
        total_engagement = (
            trend.total_engagement.upvotes * 1.0
            + trend.total_engagement.comments * 2.0  # Comments worth more
            + trend.total_engagement.shares * 3.0  # Shares worth even more
            + trend.total_engagement.views * 0.05  # Views worth less
        )

        # Velocity = engagement per hour
        velocity = total_engagement / hours

        # Store velocity in metadata for historical tracking
        if "velocity_history" not in trend.metadata:
            trend.metadata["velocity_history"] = []

        trend.metadata["velocity_history"].append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "velocity": velocity,
                "hours": hours,
                "total_engagement": total_engagement,
            }
        )

        # Keep only last 50 velocity measurements
        if len(trend.metadata["velocity_history"]) > 50:
            trend.metadata["velocity_history"] = trend.metadata["velocity_history"][
                -50:
            ]

        return velocity

    # ========================================================================
    # Private Methods
    # ========================================================================

    def _analyze_velocity(self, trend: Trend) -> VelocityAnalysis:
        """
        Analyze velocity trends and growth patterns.

        Args:
            trend: Trend to analyze

        Returns:
            VelocityAnalysis object
        """
        # Get velocity history
        velocity_history = trend.metadata.get("velocity_history", [])

        # Calculate current velocity
        current_velocity = self.calculate_velocity(trend)

        # Determine velocity trend
        velocity_trend = "stable"
        growth_rate = 0.0

        if len(velocity_history) >= 2:
            # Compare with previous velocity
            prev_velocity = velocity_history[-2]["velocity"]
            if prev_velocity > 0:
                growth_rate = (current_velocity - prev_velocity) / prev_velocity

                if growth_rate > 0.2:  # 20% increase
                    velocity_trend = "accelerating"
                elif growth_rate < -0.2:  # 20% decrease
                    velocity_trend = "decelerating"

        # Check if at peak
        is_at_peak = False
        time_since_peak = None

        if trend.peak_engagement_at:
            time_since_peak = datetime.utcnow() - trend.peak_engagement_at

            # Check if we're still at peak (within 6 hours)
            if time_since_peak < timedelta(hours=6):
                is_at_peak = True

        return VelocityAnalysis(
            current_velocity=current_velocity,
            velocity_trend=velocity_trend,
            growth_rate=growth_rate,
            time_since_peak=time_since_peak,
            is_at_peak=is_at_peak,
        )

    def _determine_state(
        self,
        trend: Trend,
        velocity_analysis: VelocityAnalysis,
        age: timedelta,
        time_since_update: timedelta,
    ) -> TrendState:
        """
        Determine trend state based on multiple factors.

        Args:
            trend: Trend to analyze
            velocity_analysis: Velocity analysis results
            age: Time since trend first seen
            time_since_update: Time since last update

        Returns:
            Recommended TrendState
        """
        # DEAD: No activity for extended period
        if time_since_update > timedelta(hours=self.DEAD_HOURS_THRESHOLD):
            return TrendState.DEAD

        # VIRAL: High velocity AND accelerating growth
        if (
            velocity_analysis.current_velocity > self.VIRAL_VELOCITY_THRESHOLD
            and velocity_analysis.velocity_trend == "accelerating"
            and velocity_analysis.growth_rate > self.VIRAL_GROWTH_RATE_THRESHOLD
        ):
            return TrendState.VIRAL

        # SUSTAINED: Past viral peak, but maintaining engagement
        if (
            trend.state == TrendState.VIRAL
            and velocity_analysis.velocity_trend == "stable"
            and velocity_analysis.current_velocity > self.VIRAL_VELOCITY_THRESHOLD * 0.5
            and age > timedelta(hours=self.SUSTAINED_MIN_HOURS)
        ):
            return TrendState.SUSTAINED

        # DECLINING: Was viral/sustained, now decelerating
        if (
            trend.state in [TrendState.VIRAL, TrendState.SUSTAINED]
            and velocity_analysis.velocity_trend == "decelerating"
            and velocity_analysis.growth_rate < self.DECLINING_DECELERATION_THRESHOLD
        ):
            return TrendState.DECLINING

        # EMERGING: New trend with growing engagement
        if age < timedelta(hours=12) and velocity_analysis.velocity_trend in [
            "accelerating",
            "stable",
        ]:
            return TrendState.EMERGING

        # Default: Maintain current state if no clear transition
        # or transition to DECLINING if old and not viral
        if age > timedelta(days=2) and trend.state == TrendState.EMERGING:
            return TrendState.DECLINING

        return trend.state

    def _get_transition_reason(self, trend: Trend, new_state: TrendState) -> str:
        """
        Generate human-readable reason for state transition.

        Args:
            trend: Trend being transitioned
            new_state: New state

        Returns:
            Reason string
        """
        velocity_analysis = self._analyze_velocity(trend)
        age = datetime.utcnow() - trend.first_seen

        if new_state == TrendState.VIRAL:
            return (
                f"High velocity ({velocity_analysis.current_velocity:.1f} eng/hr) "
                f"with {velocity_analysis.growth_rate*100:.0f}% growth rate"
            )
        elif new_state == TrendState.SUSTAINED:
            return (
                f"Stable engagement after {age.total_seconds()/3600:.1f}h, "
                f"velocity={velocity_analysis.current_velocity:.1f} eng/hr"
            )
        elif new_state == TrendState.DECLINING:
            return (
                f"Decelerating velocity ({velocity_analysis.growth_rate*100:.0f}% decline), "
                f"current={velocity_analysis.current_velocity:.1f} eng/hr"
            )
        elif new_state == TrendState.DEAD:
            time_since_update = datetime.utcnow() - trend.last_updated
            return f"No activity for {time_since_update.total_seconds()/3600:.1f}h"
        elif new_state == TrendState.EMERGING:
            return (
                f"New trend detected, velocity={velocity_analysis.current_velocity:.1f} eng/hr, "
                f"trend={velocity_analysis.velocity_trend}"
            )
        else:
            return "State maintained"

    def _record_state_transition(
        self,
        trend: Trend,
        from_state: TrendState,
        to_state: TrendState,
        reason: str,
    ) -> None:
        """
        Record state transition in trend metadata.

        Args:
            trend: Trend being transitioned
            from_state: Previous state
            to_state: New state
            reason: Reason for transition
        """
        # Initialize state history if needed
        if "state_history" not in trend.metadata:
            trend.metadata["state_history"] = []

        # Create transition record
        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            timestamp=datetime.utcnow(),
            reason=reason,
            metrics_snapshot={
                "score": trend.score,
                "velocity": trend.velocity,
                "total_engagement": {
                    "upvotes": trend.total_engagement.upvotes,
                    "comments": trend.total_engagement.comments,
                    "shares": trend.total_engagement.shares,
                    "views": trend.total_engagement.views,
                    "score": trend.total_engagement.score,
                },
                "item_count": trend.item_count,
            },
        )

        # Add to history
        trend.metadata["state_history"].append(transition.to_dict())

        # Keep only last 20 transitions
        if len(trend.metadata["state_history"]) > 20:
            trend.metadata["state_history"] = trend.metadata["state_history"][-20:]

        logger.debug(
            f"Recorded state transition for '{trend.title[:50]}': "
            f"{from_state.value} → {to_state.value} ({reason})"
        )


# ============================================================================
# Factory Function
# ============================================================================


def get_trend_state_service(
    trend_repo: Optional[TrendRepository] = None,
) -> TrendStateService:
    """
    Factory function to create TrendStateService.

    Args:
        trend_repo: Optional trend repository

    Returns:
        TrendStateService instance
    """
    return TrendStateService(trend_repo=trend_repo)
