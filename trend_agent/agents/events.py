"""
Event Streaming with Dampening Layer.

Prevents event storms and cascading failures through intelligent event management.
"""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import logging

from trend_agent.agents.correlation import get_correlation_id

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """Event priority levels."""

    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


@dataclass
class Event:
    """Event with metadata."""

    # Identity
    event_id: str
    event_type: str
    correlation_id: str

    # Content
    payload: Dict[str, Any] = field(default_factory=dict)

    # Routing
    source: str = ""  # Agent or system component
    target: Optional[str] = None  # Specific target or None for broadcast

    # Priority
    priority: EventPriority = EventPriority.NORMAL

    # Timing
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ttl_seconds: Optional[int] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def compute_hash(self) -> str:
        """
        Compute hash for deduplication.

        Based on event type, source, and payload.

        Returns:
            SHA-256 hash
        """
        content = f"{self.event_type}|{self.source}|"

        # Add sorted payload items
        sorted_payload = sorted(self.payload.items())
        content += "|".join(f"{k}={v}" for k, v in sorted_payload)

        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class EventWindow:
    """Time window for event counting."""

    event_type: str
    window_start: datetime
    window_duration: timedelta
    event_count: int = 0
    event_hashes: set = field(default_factory=set)


class EventDampener:
    """
    Event dampening layer for preventing event storms.

    Features:
    - Event deduplication (time-windowed)
    - Rate limiting per event type
    - Cascade detection
    - Backpressure management
    """

    def __init__(
        self,
        dedup_window: timedelta = timedelta(seconds=30),
        rate_limits: Optional[Dict[str, int]] = None,
        cascade_threshold: int = 100,
        cascade_fanout_ratio: float = 10.0,
    ):
        """
        Initialize event dampener.

        Args:
            dedup_window: Time window for deduplication
            rate_limits: Event type -> max events per minute
            cascade_threshold: Max events per window before cascade detection
            cascade_fanout_ratio: Max fan-out ratio before cascade
        """
        self._dedup_window = dedup_window
        self._rate_limits = rate_limits or {}
        self._cascade_threshold = cascade_threshold
        self._cascade_fanout_ratio = cascade_fanout_ratio

        # Tracking
        self._recent_events: Dict[str, List[Event]] = {}  # event_hash -> events
        self._windows: Dict[str, EventWindow] = {}  # event_type -> window
        self._correlation_counts: Dict[str, int] = {}  # correlation_id -> count

        logger.info(
            f"Event Dampener initialized "
            f"(dedup_window={dedup_window}, cascade_threshold={cascade_threshold})"
        )

    async def should_emit(
        self,
        event: Event,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if event should be emitted.

        Applies:
        1. Deduplication
        2. Rate limiting
        3. Cascade detection

        Args:
            event: Event to check

        Returns:
            Tuple of (should_emit, rejection_reason)
        """
        # 1. Check deduplication
        is_duplicate = self._check_duplicate(event)
        if is_duplicate:
            logger.debug(f"Event deduplicated: {event.event_type}")
            return (False, "Duplicate event within dedup window")

        # 2. Check rate limits
        rate_limited = self._check_rate_limit(event)
        if rate_limited:
            logger.warning(f"Event rate limited: {event.event_type}")
            return (False, f"Rate limit exceeded for {event.event_type}")

        # 3. Check cascade detection
        cascade_detected = await self._check_cascade(event)
        if cascade_detected:
            logger.error(f"Event cascade detected: {event.correlation_id}")
            return (False, f"Event cascade detected for correlation {event.correlation_id}")

        # Event can be emitted
        self._record_event(event)

        return (True, None)

    def _check_duplicate(self, event: Event) -> bool:
        """
        Check if event is duplicate within dedup window.

        Args:
            event: Event to check

        Returns:
            True if duplicate
        """
        event_hash = event.compute_hash()
        cutoff = datetime.utcnow() - self._dedup_window

        # Get recent events with same hash
        recent = self._recent_events.get(event_hash, [])

        # Check if any recent event is within dedup window
        for recent_event in recent:
            if recent_event.timestamp >= cutoff:
                return True

        return False

    def _check_rate_limit(self, event: Event) -> bool:
        """
        Check if event type has exceeded rate limit.

        Args:
            event: Event to check

        Returns:
            True if rate limited
        """
        if event.event_type not in self._rate_limits:
            return False

        limit = self._rate_limits[event.event_type]

        # Get or create window
        window = self._get_or_create_window(event.event_type)

        # Check if window has expired
        if datetime.utcnow() >= window.window_start + window.window_duration:
            # Reset window
            window.window_start = datetime.utcnow()
            window.event_count = 0
            window.event_hashes.clear()

        # Check limit
        return window.event_count >= limit

    async def _check_cascade(self, event: Event) -> bool:
        """
        Detect event cascades.

        Cascade indicators:
        - Too many events with same correlation ID
        - Exponential fan-out pattern

        Args:
            event: Event to check

        Returns:
            True if cascade detected
        """
        # Count events for this correlation
        correlation_count = self._correlation_counts.get(event.correlation_id, 0)

        if correlation_count >= self._cascade_threshold:
            logger.error(
                f"Cascade threshold exceeded: {event.correlation_id} "
                f"({correlation_count} events)"
            )
            return True

        # Check fan-out ratio (simplified)
        # In production, analyze actual fan-out pattern
        window = self._get_or_create_window(event.event_type)
        if window.event_count > 0:
            fanout = correlation_count / max(1, window.event_count / 10)
            if fanout > self._cascade_fanout_ratio:
                logger.warning(
                    f"High fan-out detected: {event.correlation_id} "
                    f"(ratio={fanout:.2f})"
                )
                return True

        return False

    def _record_event(self, event: Event) -> None:
        """
        Record event for tracking.

        Args:
            event: Event to record
        """
        # Record for deduplication
        event_hash = event.compute_hash()
        if event_hash not in self._recent_events:
            self._recent_events[event_hash] = []
        self._recent_events[event_hash].append(event)

        # Update window
        window = self._get_or_create_window(event.event_type)
        window.event_count += 1
        window.event_hashes.add(event_hash)

        # Update correlation count
        self._correlation_counts[event.correlation_id] = \
            self._correlation_counts.get(event.correlation_id, 0) + 1

    def _get_or_create_window(self, event_type: str) -> EventWindow:
        """
        Get or create event window.

        Args:
            event_type: Event type

        Returns:
            Event window
        """
        if event_type not in self._windows:
            self._windows[event_type] = EventWindow(
                event_type=event_type,
                window_start=datetime.utcnow(),
                window_duration=timedelta(minutes=1),
            )

        return self._windows[event_type]

    def cleanup_old_events(self) -> int:
        """
        Clean up old event tracking data.

        Returns:
            Number of events cleaned up
        """
        cutoff = datetime.utcnow() - self._dedup_window
        cleaned = 0

        # Clean up recent events
        for event_hash in list(self._recent_events.keys()):
            events = self._recent_events[event_hash]
            events = [e for e in events if e.timestamp >= cutoff]

            if events:
                self._recent_events[event_hash] = events
            else:
                del self._recent_events[event_hash]
                cleaned += 1

        if cleaned > 0:
            logger.debug(f"Cleaned up {cleaned} old event records")

        return cleaned

    def get_stats(self) -> Dict[str, Any]:
        """
        Get dampener statistics.

        Returns:
            Statistics dictionary
        """
        total_recent_events = sum(len(events) for events in self._recent_events.values())

        return {
            "unique_event_hashes": len(self._recent_events),
            "total_recent_events": total_recent_events,
            "active_windows": len(self._windows),
            "active_correlations": len(self._correlation_counts),
            "window_stats": {
                event_type: {
                    "count": window.event_count,
                    "unique": len(window.event_hashes),
                }
                for event_type, window in self._windows.items()
            },
        }


class EventBus:
    """
    Event bus with dampening and routing.

    Features:
    - Publisher/subscriber pattern
    - Event dampening
    - Priority-based delivery
    - Correlation tracking
    """

    def __init__(self, dampener: Optional[EventDampener] = None):
        """
        Initialize event bus.

        Args:
            dampener: Event dampener instance
        """
        self._dampener = dampener or EventDampener()
        self._subscribers: Dict[str, List[Callable]] = {}  # event_type -> handlers

        logger.info("Event Bus initialized")

    async def publish(
        self,
        event: Event,
    ) -> tuple[bool, Optional[str]]:
        """
        Publish event to subscribers.

        Args:
            event: Event to publish

        Returns:
            Tuple of (published, rejection_reason)
        """
        # Check dampening
        should_emit, reason = await self._dampener.should_emit(event)
        if not should_emit:
            return (False, reason)

        # Get subscribers
        handlers = self._subscribers.get(event.event_type, [])
        handlers.extend(self._subscribers.get("*", []))  # Wildcard subscribers

        if not handlers:
            logger.debug(f"No subscribers for event type: {event.event_type}")
            return (True, None)

        # Deliver to subscribers
        delivered_count = 0
        for handler in handlers:
            try:
                # Call handler (async or sync)
                if hasattr(handler, '__call__'):
                    result = handler(event)
                    if hasattr(result, '__await__'):
                        await result
                    delivered_count += 1
            except Exception as e:
                logger.error(
                    f"Event handler error: {handler.__name__} - {e}",
                    exc_info=True,
                )

        logger.debug(
            f"Event published: {event.event_type} "
            f"(delivered to {delivered_count} subscribers)"
        )

        return (True, None)

    def subscribe(
        self,
        event_type: str,
        handler: Callable,
    ) -> None:
        """
        Subscribe to event type.

        Args:
            event_type: Event type to subscribe to (use "*" for all)
            handler: Handler function (receives Event)
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append(handler)

        logger.info(
            f"Subscriber registered: {handler.__name__} -> {event_type}"
        )

    def unsubscribe(
        self,
        event_type: str,
        handler: Callable,
    ) -> bool:
        """
        Unsubscribe from event type.

        Args:
            event_type: Event type
            handler: Handler function

        Returns:
            True if unsubscribed
        """
        if event_type in self._subscribers:
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)
                logger.info(
                    f"Subscriber removed: {handler.__name__} <- {event_type}"
                )
                return True

        return False

    def get_subscriber_count(self, event_type: str) -> int:
        """
        Get number of subscribers for event type.

        Args:
            event_type: Event type

        Returns:
            Subscriber count
        """
        return len(self._subscribers.get(event_type, []))

    def get_stats(self) -> Dict[str, Any]:
        """
        Get event bus statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "subscriber_counts": {
                event_type: len(handlers)
                for event_type, handlers in self._subscribers.items()
            },
            "dampener_stats": self._dampener.get_stats(),
        }
