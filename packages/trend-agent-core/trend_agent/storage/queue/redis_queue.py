"""
Redis Queue Implementation.

Lightweight message queue using Redis lists and streams.
Suitable for simpler workloads and development environments.
"""

import logging
import json
import uuid
from typing import List, Optional, Callable
from datetime import datetime
import asyncio

from trend_agent.storage.queue.interface import (
    QueueRepository,
    Message,
    MessagePriority,
)

logger = logging.getLogger(__name__)


class RedisQueueRepository(QueueRepository):
    """Redis implementation of message queue using Redis Lists and Streams."""

    # Priority queue suffixes
    PRIORITY_SUFFIXES = {
        MessagePriority.CRITICAL: ":critical",
        MessagePriority.HIGH: ":high",
        MessagePriority.NORMAL: ":normal",
        MessagePriority.LOW: ":low",
    }

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        max_connections: int = 50,
    ):
        """
        Initialize Redis queue repository.

        Args:
            host: Redis host
            port: Redis port
            password: Optional password
            db: Database number
            max_connections: Maximum connection pool size
        """
        self._host = host
        self._port = port
        self._password = password
        self._db = db
        self._max_connections = max_connections
        self._redis = None

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            import redis.asyncio as aioredis

            self._redis = await aioredis.from_url(
                f"redis://{self._host}:{self._port}/{self._db}",
                password=self._password,
                max_connections=self._max_connections,
                decode_responses=False,  # Handle bytes for binary data
            )

            # Test connection
            await self._redis.ping()

            logger.info(f"Connected to Redis queue at {self._host}:{self._port}")

        except ImportError:
            logger.error("redis not installed. Install with: pip install redis[asyncio]")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            logger.info("Redis queue connection closed")

    def _get_queue_key(self, queue_name: str, priority: MessagePriority) -> str:
        """Get Redis key for queue with priority."""
        return f"queue:{queue_name}{self.PRIORITY_SUFFIXES[priority]}"

    async def publish(
        self,
        queue_name: str,
        message: Message,
    ) -> str:
        """Publish a message to a queue."""
        # Generate message ID
        message_id = str(uuid.uuid4())
        message.message_id = message_id
        message.timestamp = datetime.utcnow()

        # Serialize message
        message_data = {
            "id": message_id,
            "body": message.body,
            "priority": message.priority.value,
            "headers": message.headers,
            "timestamp": message.timestamp.isoformat(),
            "delivery_count": 0,
        }

        message_json = json.dumps(message_data)

        # Handle delayed messages
        if message.delay_seconds > 0:
            # Use sorted set for delayed messages
            delay_key = f"queue:{queue_name}:delayed"
            score = datetime.utcnow().timestamp() + message.delay_seconds

            await self._redis.zadd(delay_key, {message_json: score})
            logger.debug(f"Scheduled delayed message {message_id} for {message.delay_seconds}s")
        else:
            # Add to priority queue
            queue_key = self._get_queue_key(queue_name, message.priority)
            await self._redis.rpush(queue_key, message_json)
            logger.debug(f"Published message {message_id} to queue {queue_name}")

        # Set TTL if specified
        if message.ttl_seconds:
            ttl_key = f"queue:{queue_name}:msg:{message_id}"
            await self._redis.setex(
                ttl_key,
                message.ttl_seconds,
                message_json,
            )

        return message_id

    async def publish_batch(
        self,
        queue_name: str,
        messages: List[Message],
    ) -> List[str]:
        """Publish multiple messages to a queue."""
        message_ids = []

        # Group messages by priority
        priority_groups = {p: [] for p in MessagePriority}

        for message in messages:
            message_id = str(uuid.uuid4())
            message.message_id = message_id
            message.timestamp = datetime.utcnow()

            message_data = {
                "id": message_id,
                "body": message.body,
                "priority": message.priority.value,
                "headers": message.headers,
                "timestamp": message.timestamp.isoformat(),
                "delivery_count": 0,
            }

            priority_groups[message.priority].append(json.dumps(message_data))
            message_ids.append(message_id)

        # Batch publish by priority
        pipe = self._redis.pipeline()
        for priority, message_list in priority_groups.items():
            if message_list:
                queue_key = self._get_queue_key(queue_name, priority)
                pipe.rpush(queue_key, *message_list)

        await pipe.execute()

        logger.debug(f"Published {len(message_ids)} messages to queue {queue_name}")
        return message_ids

    async def consume(
        self,
        queue_name: str,
        callback: Callable[[Message], None],
        max_messages: int = 1,
        visibility_timeout: int = 30,
    ) -> None:
        """Consume messages from a queue."""
        # Check delayed messages and move to active queue
        await self._process_delayed_messages(queue_name)

        # Process messages in priority order
        for priority in [
            MessagePriority.CRITICAL,
            MessagePriority.HIGH,
            MessagePriority.NORMAL,
            MessagePriority.LOW,
        ]:
            queue_key = self._get_queue_key(queue_name, priority)
            processing_key = f"{queue_key}:processing"

            # Move messages to processing queue (atomic)
            for _ in range(max_messages):
                # BRPOPLPUSH for atomic pop and push
                message_json = await self._redis.brpoplpush(
                    queue_key,
                    processing_key,
                    timeout=1,
                )

                if not message_json:
                    continue

                try:
                    # Deserialize message
                    message_data = json.loads(message_json)

                    # Create Message object
                    message = Message(
                        body=message_data["body"],
                        headers=message_data.get("headers", {}),
                    )
                    message.message_id = message_data["id"]
                    message.delivery_count = message_data.get("delivery_count", 0) + 1

                    # Process message
                    await callback(message)

                    # Remove from processing queue (acknowledge)
                    await self._redis.lrem(processing_key, 1, message_json)

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message: {e}")
                    # Remove invalid message
                    await self._redis.lrem(processing_key, 1, message_json)

                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Move back to main queue (requeue)
                    await self._redis.lrem(processing_key, 1, message_json)
                    await self._redis.rpush(queue_key, message_json)

    async def _process_delayed_messages(self, queue_name: str) -> None:
        """Move delayed messages to active queue if time has come."""
        delay_key = f"queue:{queue_name}:delayed"
        now = datetime.utcnow().timestamp()

        # Get messages ready for processing
        ready_messages = await self._redis.zrangebyscore(
            delay_key,
            min=0,
            max=now,
        )

        if ready_messages:
            # Move to appropriate priority queues
            pipe = self._redis.pipeline()
            for message_json in ready_messages:
                message_data = json.loads(message_json)
                priority = MessagePriority(message_data["priority"])
                queue_key = self._get_queue_key(queue_name, priority)

                pipe.rpush(queue_key, message_json)
                pipe.zrem(delay_key, message_json)

            await pipe.execute()
            logger.debug(f"Moved {len(ready_messages)} delayed messages to active queue")

    async def acknowledge(
        self,
        queue_name: str,
        message_id: str,
    ) -> None:
        """Acknowledge successful processing of a message."""
        # Messages are acknowledged in consume() method
        # This is for explicit acknowledgment if needed
        for priority in MessagePriority:
            queue_key = self._get_queue_key(queue_name, priority)
            processing_key = f"{queue_key}:processing"

            # Remove message from processing queue
            # We need to scan for the message with matching ID
            messages = await self._redis.lrange(processing_key, 0, -1)
            for msg_json in messages:
                msg_data = json.loads(msg_json)
                if msg_data["id"] == message_id:
                    await self._redis.lrem(processing_key, 1, msg_json)
                    logger.debug(f"Acknowledged message {message_id}")
                    return

    async def reject(
        self,
        queue_name: str,
        message_id: str,
        requeue: bool = True,
    ) -> None:
        """Reject a message (failed processing)."""
        for priority in MessagePriority:
            queue_key = self._get_queue_key(queue_name, priority)
            processing_key = f"{queue_key}:processing"

            # Find and remove message from processing queue
            messages = await self._redis.lrange(processing_key, 0, -1)
            for msg_json in messages:
                msg_data = json.loads(msg_json)
                if msg_data["id"] == message_id:
                    await self._redis.lrem(processing_key, 1, msg_json)

                    if requeue:
                        # Push back to main queue
                        await self._redis.rpush(queue_key, msg_json)
                        logger.debug(f"Requeued message {message_id}")
                    else:
                        logger.debug(f"Rejected message {message_id} without requeue")
                    return

    async def create_queue(
        self,
        queue_name: str,
        durable: bool = True,
        max_length: Optional[int] = None,
        message_ttl: Optional[int] = None,
    ) -> None:
        """Create a new queue."""
        # Redis lists are created on first use
        # Store queue metadata
        metadata_key = f"queue:{queue_name}:metadata"
        metadata = {
            "durable": durable,
            "max_length": max_length or 0,
            "message_ttl": message_ttl or 0,
            "created_at": datetime.utcnow().isoformat(),
        }

        await self._redis.hset(
            metadata_key,
            mapping={k: str(v) for k, v in metadata.items()},
        )

        logger.info(f"Created queue: {queue_name}")

    async def delete_queue(
        self,
        queue_name: str,
        if_empty: bool = False,
    ) -> None:
        """Delete a queue."""
        if if_empty:
            size = await self.get_queue_size(queue_name)
            if size > 0:
                raise ValueError(f"Queue {queue_name} is not empty ({size} messages)")

        # Delete all priority queues
        keys_to_delete = []
        for priority in MessagePriority:
            queue_key = self._get_queue_key(queue_name, priority)
            processing_key = f"{queue_key}:processing"
            keys_to_delete.extend([queue_key, processing_key])

        # Delete delayed queue and metadata
        keys_to_delete.extend([
            f"queue:{queue_name}:delayed",
            f"queue:{queue_name}:metadata",
        ])

        if keys_to_delete:
            await self._redis.delete(*keys_to_delete)

        logger.info(f"Deleted queue: {queue_name}")

    async def purge_queue(
        self,
        queue_name: str,
    ) -> int:
        """Remove all messages from a queue."""
        total_purged = 0

        # Purge all priority queues
        for priority in MessagePriority:
            queue_key = self._get_queue_key(queue_name, priority)
            length = await self._redis.llen(queue_key)
            if length > 0:
                await self._redis.delete(queue_key)
                total_purged += length

        # Purge delayed queue
        delay_key = f"queue:{queue_name}:delayed"
        delayed_count = await self._redis.zcard(delay_key)
        if delayed_count > 0:
            await self._redis.delete(delay_key)
            total_purged += delayed_count

        logger.info(f"Purged {total_purged} messages from queue {queue_name}")
        return total_purged

    async def get_queue_size(
        self,
        queue_name: str,
    ) -> int:
        """Get number of messages in queue."""
        total_size = 0

        # Count messages in all priority queues
        for priority in MessagePriority:
            queue_key = self._get_queue_key(queue_name, priority)
            total_size += await self._redis.llen(queue_key)

        # Count delayed messages
        delay_key = f"queue:{queue_name}:delayed"
        total_size += await self._redis.zcard(delay_key)

        return total_size
