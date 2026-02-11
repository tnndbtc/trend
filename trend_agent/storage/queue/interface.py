"""
Message Queue Interface.

For asynchronous task processing, event streaming, and distributed messaging.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Callable
from datetime import datetime
from enum import Enum


class MessagePriority(Enum):
    """Message priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class Message:
    """Queue message wrapper."""

    def __init__(
        self,
        body: Any,
        priority: MessagePriority = MessagePriority.NORMAL,
        headers: Optional[Dict[str, Any]] = None,
        delay_seconds: int = 0,
        ttl_seconds: Optional[int] = None,
    ):
        """
        Initialize message.

        Args:
            body: Message payload (will be JSON-serialized)
            priority: Message priority level
            headers: Optional metadata headers
            delay_seconds: Delay before message becomes available
            ttl_seconds: Time-to-live in seconds (None = no expiration)
        """
        self.body = body
        self.priority = priority
        self.headers = headers or {}
        self.delay_seconds = delay_seconds
        self.ttl_seconds = ttl_seconds
        self.message_id: Optional[str] = None
        self.timestamp: Optional[datetime] = None
        self.delivery_count: int = 0


class QueueRepository(ABC):
    """Abstract interface for message queue operations."""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to message queue broker."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close connection to message queue broker."""
        pass

    @abstractmethod
    async def publish(
        self,
        queue_name: str,
        message: Message,
    ) -> str:
        """
        Publish a message to a queue.

        Args:
            queue_name: Name of the queue
            message: Message to publish

        Returns:
            Message ID
        """
        pass

    @abstractmethod
    async def publish_batch(
        self,
        queue_name: str,
        messages: List[Message],
    ) -> List[str]:
        """
        Publish multiple messages to a queue.

        Args:
            queue_name: Name of the queue
            messages: Messages to publish

        Returns:
            List of message IDs
        """
        pass

    @abstractmethod
    async def consume(
        self,
        queue_name: str,
        callback: Callable[[Message], None],
        max_messages: int = 1,
        visibility_timeout: int = 30,
    ) -> None:
        """
        Consume messages from a queue.

        Args:
            queue_name: Name of the queue
            callback: Async callback function to process messages
            max_messages: Maximum number of messages to retrieve
            visibility_timeout: Seconds message is invisible after retrieval
        """
        pass

    @abstractmethod
    async def acknowledge(
        self,
        queue_name: str,
        message_id: str,
    ) -> None:
        """
        Acknowledge successful processing of a message.

        Args:
            queue_name: Name of the queue
            message_id: ID of the message to acknowledge
        """
        pass

    @abstractmethod
    async def reject(
        self,
        queue_name: str,
        message_id: str,
        requeue: bool = True,
    ) -> None:
        """
        Reject a message (failed processing).

        Args:
            queue_name: Name of the queue
            message_id: ID of the message to reject
            requeue: Whether to requeue the message
        """
        pass

    @abstractmethod
    async def create_queue(
        self,
        queue_name: str,
        durable: bool = True,
        max_length: Optional[int] = None,
        message_ttl: Optional[int] = None,
    ) -> None:
        """
        Create a new queue.

        Args:
            queue_name: Name of the queue
            durable: Whether queue survives broker restarts
            max_length: Maximum number of messages in queue
            message_ttl: Default message TTL in seconds
        """
        pass

    @abstractmethod
    async def delete_queue(
        self,
        queue_name: str,
        if_empty: bool = False,
    ) -> None:
        """
        Delete a queue.

        Args:
            queue_name: Name of the queue
            if_empty: Only delete if queue is empty
        """
        pass

    @abstractmethod
    async def purge_queue(
        self,
        queue_name: str,
    ) -> int:
        """
        Remove all messages from a queue.

        Args:
            queue_name: Name of the queue

        Returns:
            Number of messages purged
        """
        pass

    @abstractmethod
    async def get_queue_size(
        self,
        queue_name: str,
    ) -> int:
        """
        Get number of messages in queue.

        Args:
            queue_name: Name of the queue

        Returns:
            Number of messages
        """
        pass
