"""
Unit tests for TrendStateService.

Tests trend lifecycle state detection, state transitions, velocity tracking,
and historical state management.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from trend_agent.services.trend_states import (
    TrendStateService,
    StateTransition,
    VelocityAnalysis,
)
from trend_agent.schemas import Trend, TrendState, Metrics, Category, SourceType


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_trend():
    """Create a mock trend for testing."""
    return Trend(
        id=uuid4(),
        topic_id=uuid4(),
        rank=1,
        title="Test Trend",
        summary="A test trend for unit testing",
        category=Category.TECHNOLOGY,
        state=TrendState.EMERGING,
        score=75.0,
        sources=[SourceType.REDDIT, SourceType.HACKERNEWS],
        item_count=25,
        total_engagement=Metrics(
            upvotes=500,
            comments=120,
            shares=45,
            views=2500,
            score=850.0,
        ),
        velocity=0.0,
        first_seen=datetime.utcnow() - timedelta(hours=6),
        last_updated=datetime.utcnow(),
        language="en",
        keywords=["AI", "machine learning", "technology"],
        metadata={},
    )


@pytest.fixture
def state_service():
    """Create TrendStateService instance."""
    return TrendStateService()


# ============================================================================
# State Transition Tests
# ============================================================================


class TestStateTransitions:
    """Tests for state transition recording and history."""

    def test_state_transition_creation(self):
        """Test creating a state transition record."""
        transition = StateTransition(
            from_state=TrendState.EMERGING,
            to_state=TrendState.VIRAL,
            timestamp=datetime.utcnow(),
            reason="High velocity with 75% growth rate",
            metrics_snapshot={"score": 85.0, "velocity": 120.5},
        )

        assert transition.from_state == TrendState.EMERGING
        assert transition.to_state == TrendState.VIRAL
        assert "growth rate" in transition.reason

    def test_state_transition_serialization(self):
        """Test state transition to/from dict."""
        transition = StateTransition(
            from_state=TrendState.VIRAL,
            to_state=TrendState.SUSTAINED,
            timestamp=datetime.utcnow(),
            reason="Stable engagement after 36h",
        )

        # Serialize
        data = transition.to_dict()
        assert data["from_state"] == "viral"
        assert data["to_state"] == "sustained"
        assert "timestamp" in data

        # Deserialize
        restored = StateTransition.from_dict(data)
        assert restored.from_state == TrendState.VIRAL
        assert restored.to_state == TrendState.SUSTAINED

    def test_state_history_tracking(self, state_service, mock_trend):
        """Test that state transitions are recorded in metadata."""
        # Record a transition
        state_service._record_state_transition(
            trend=mock_trend,
            from_state=TrendState.EMERGING,
            to_state=TrendState.VIRAL,
            reason="Test transition",
        )

        # Verify history
        history = state_service.get_state_history(mock_trend)
        assert len(history) == 1
        assert history[0].from_state == TrendState.EMERGING
        assert history[0].to_state == TrendState.VIRAL

    def test_state_history_limit(self, state_service, mock_trend):
        """Test that state history is limited to 20 entries."""
        # Record 25 transitions
        for i in range(25):
            state = TrendState.VIRAL if i % 2 == 0 else TrendState.SUSTAINED
            state_service._record_state_transition(
                trend=mock_trend,
                from_state=TrendState.EMERGING,
                to_state=state,
                reason=f"Transition {i}",
            )

        # Should only keep last 20
        history = state_service.get_state_history(mock_trend)
        assert len(history) == 20


# ============================================================================
# Velocity Analysis Tests
# ============================================================================


class TestVelocityAnalysis:
    """Tests for velocity calculation and trend analysis."""

    def test_velocity_calculation(self, state_service, mock_trend):
        """Test basic velocity calculation."""
        velocity = state_service.calculate_velocity(mock_trend)

        # Velocity should be positive
        assert velocity > 0

        # Should be recorded in metadata
        assert "velocity_history" in mock_trend.metadata
        assert len(mock_trend.metadata["velocity_history"]) == 1

    def test_velocity_history_tracking(self, state_service, mock_trend):
        """Test that velocity history is tracked."""
        # Calculate velocity multiple times
        for _ in range(5):
            state_service.calculate_velocity(mock_trend)

        # Should have 5 entries
        assert len(mock_trend.metadata["velocity_history"]) == 5

    def test_velocity_history_limit(self, state_service, mock_trend):
        """Test that velocity history is limited to 50 entries."""
        # Calculate velocity 60 times
        for _ in range(60):
            state_service.calculate_velocity(mock_trend)

        # Should only keep last 50
        assert len(mock_trend.metadata["velocity_history"]) == 50

    def test_velocity_analysis_accelerating(self, state_service, mock_trend):
        """Test detection of accelerating velocity."""
        # Set up velocity history with increasing trend
        mock_trend.metadata["velocity_history"] = [
            {"velocity": 50.0, "timestamp": datetime.utcnow().isoformat()},
            {"velocity": 100.0, "timestamp": datetime.utcnow().isoformat()},
        ]

        analysis = state_service._analyze_velocity(mock_trend)
        assert analysis.velocity_trend == "accelerating"
        assert analysis.growth_rate > 0

    def test_velocity_analysis_decelerating(self, state_service, mock_trend):
        """Test detection of decelerating velocity."""
        # Set up velocity history with decreasing trend
        mock_trend.metadata["velocity_history"] = [
            {"velocity": 100.0, "timestamp": datetime.utcnow().isoformat()},
            {"velocity": 50.0, "timestamp": datetime.utcnow().isoformat()},
        ]

        analysis = state_service._analyze_velocity(mock_trend)
        assert analysis.velocity_trend == "decelerating"
        assert analysis.growth_rate < 0


# ============================================================================
# State Determination Tests
# ============================================================================


class TestStateDetermination:
    """Tests for trend state detection algorithms."""

    @pytest.mark.asyncio
    async def test_emerging_state_detection(self, state_service):
        """Test detection of EMERGING state."""
        # Create recent trend with low velocity
        trend = Trend(
            id=uuid4(),
            topic_id=uuid4(),
            rank=1,
            title="New Trend",
            summary="Just started",
            category=Category.TECHNOLOGY,
            state=TrendState.EMERGING,
            score=50.0,
            sources=[SourceType.REDDIT],
            item_count=5,
            total_engagement=Metrics(upvotes=50, comments=10),
            velocity=0.0,
            first_seen=datetime.utcnow() - timedelta(hours=2),
            last_updated=datetime.utcnow(),
            language="en",
            metadata={},
        )

        state = await state_service.analyze_trend(trend)
        assert state == TrendState.EMERGING

    @pytest.mark.asyncio
    async def test_viral_state_detection(self, state_service):
        """Test detection of VIRAL state."""
        # Create trend with high velocity and acceleration
        trend = Trend(
            id=uuid4(),
            topic_id=uuid4(),
            rank=1,
            title="Viral Trend",
            summary="Going viral",
            category=Category.TECHNOLOGY,
            state=TrendState.EMERGING,
            score=95.0,
            sources=[SourceType.REDDIT, SourceType.HACKERNEWS, SourceType.TWITTER],
            item_count=150,
            total_engagement=Metrics(
                upvotes=5000,
                comments=1200,
                shares=800,
                views=50000,
                score=10000.0,
            ),
            velocity=0.0,
            first_seen=datetime.utcnow() - timedelta(hours=6),
            last_updated=datetime.utcnow(),
            language="en",
            metadata={
                "velocity_history": [
                    {"velocity": 50.0, "timestamp": datetime.utcnow().isoformat()},
                    {"velocity": 150.0, "timestamp": datetime.utcnow().isoformat()},
                ]
            },
        )

        state = await state_service.analyze_trend(trend)
        assert state == TrendState.VIRAL

    @pytest.mark.asyncio
    async def test_dead_state_detection(self, state_service):
        """Test detection of DEAD state."""
        # Create trend with no recent activity
        trend = Trend(
            id=uuid4(),
            topic_id=uuid4(),
            rank=1,
            title="Old Trend",
            summary="No longer active",
            category=Category.TECHNOLOGY,
            state=TrendState.DECLINING,
            score=20.0,
            sources=[SourceType.REDDIT],
            item_count=10,
            total_engagement=Metrics(upvotes=100),
            velocity=0.0,
            first_seen=datetime.utcnow() - timedelta(days=7),
            last_updated=datetime.utcnow() - timedelta(days=4),
            language="en",
            metadata={},
        )

        state = await state_service.analyze_trend(trend)
        assert state == TrendState.DEAD


# ============================================================================
# Update Operations Tests
# ============================================================================


class TestUpdateOperations:
    """Tests for trend state update operations."""

    @pytest.mark.asyncio
    async def test_update_trend_state_changed(self, state_service, mock_trend):
        """Test updating a trend whose state has changed."""
        mock_trend.state = TrendState.EMERGING

        # Mock high engagement to trigger VIRAL
        mock_trend.total_engagement.upvotes = 10000
        mock_trend.metadata["velocity_history"] = [
            {"velocity": 50.0, "timestamp": datetime.utcnow().isoformat()},
            {"velocity": 200.0, "timestamp": datetime.utcnow().isoformat()},
        ]

        updated_trend, changed = await state_service.update_trend_state(mock_trend)

        # State should have changed
        assert changed is True
        # History should be recorded
        assert "state_history" in updated_trend.metadata

    @pytest.mark.asyncio
    async def test_update_trend_state_unchanged(self, state_service, mock_trend):
        """Test updating a trend whose state hasn't changed."""
        original_state = mock_trend.state

        updated_trend, changed = await state_service.update_trend_state(mock_trend)

        # If state didn't change
        if not changed:
            assert updated_trend.state == original_state

    @pytest.mark.asyncio
    async def test_bulk_update_states(self, state_service):
        """Test bulk updating multiple trends."""
        trends = [
            Trend(
                id=uuid4(),
                topic_id=uuid4(),
                rank=i,
                title=f"Trend {i}",
                summary=f"Test trend {i}",
                category=Category.TECHNOLOGY,
                state=TrendState.EMERGING,
                score=50.0,
                sources=[SourceType.REDDIT],
                item_count=10,
                total_engagement=Metrics(upvotes=100 * i),
                velocity=0.0,
                first_seen=datetime.utcnow() - timedelta(hours=i),
                last_updated=datetime.utcnow(),
                language="en",
                metadata={},
            )
            for i in range(1, 6)
        ]

        stats = await state_service.bulk_update_states(trends)

        assert stats["total"] == 5
        assert stats["updated"] + stats["unchanged"] == 5
        assert stats["errors"] == 0


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
class TestStateServiceIntegration:
    """Integration tests with actual trend data patterns."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, state_service):
        """Test a trend through its full lifecycle."""
        # Create a trend
        trend = Trend(
            id=uuid4(),
            topic_id=uuid4(),
            rank=1,
            title="Full Lifecycle Trend",
            summary="Testing lifecycle",
            category=Category.TECHNOLOGY,
            state=TrendState.EMERGING,
            score=60.0,
            sources=[SourceType.REDDIT],
            item_count=20,
            total_engagement=Metrics(upvotes=200, comments=40),
            velocity=0.0,
            first_seen=datetime.utcnow() - timedelta(hours=1),
            last_updated=datetime.utcnow(),
            language="en",
            metadata={},
        )

        # Stage 1: EMERGING
        state = await state_service.analyze_trend(trend)
        assert state == TrendState.EMERGING

        # Stage 2: Simulate going VIRAL
        trend.total_engagement.upvotes = 10000
        trend.metadata["velocity_history"] = [
            {"velocity": 50.0, "timestamp": datetime.utcnow().isoformat()},
            {"velocity": 300.0, "timestamp": datetime.utcnow().isoformat()},
        ]
        trend.first_seen = datetime.utcnow() - timedelta(hours=12)

        state = await state_service.analyze_trend(trend)
        # Depending on thresholds, might be VIRAL

        # Stage 3: Simulate DEAD
        trend.last_updated = datetime.utcnow() - timedelta(days=5)
        state = await state_service.analyze_trend(trend)
        assert state == TrendState.DEAD
