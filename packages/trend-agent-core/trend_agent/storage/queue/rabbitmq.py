"""
RabbitMQ Queue Implementation.

Production-grade message queue using RabbitMQ/AMQP protocol.
"""

import logging
import json
from typing import List, Optional, Callable
from datetime import datetime

from trend_agent.storage.queue.interface import (
    QueueRepository,
    Message,
    MessagePriority,
)

logger = logging.getLogger(__name__)


class RabbitMQQueueRepository(QueueRepository):
    """RabbitMQ implementation of message queue."""

    # Priority mapping
    PRIORITY_MAP = {
        MessagePriority.LOW: 1,
        MessagePriority.NORMAL: 5,
        MessagePriority.HIGH: 8,
        MessagePriority.CRITICAL: 10,
    }

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5672,
        username: str = "guest",
        password: str = "guest",
        virtual_host: str = "/",
        connection_timeout: int = 30,
    ):
        """
        Initialize RabbitMQ repository.

        Args:
            host: RabbitMQ host
            port: RabbitMQ port
            username: Authentication username
            password: Authentication password
            virtual_host: Virtual host name
            connection_timeout: Connection timeout in seconds
        """
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._virtual_host = virtual_host
        self._connection_timeout = connection_timeout
        self._connection = None
        self._channel = None

    async def connect(self) -> None:
        """Connect to RabbitMQ."""
        try:
            import aio_pika

            self._connection = await aio_pika.connect_robust(
                host=self._host,
                port=self._port,
                login=self._username,
                password=self._password,
                virtualhost=self._virtual_host,
                timeout=self._connection_timeout,
            )

            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=10)

            logger.info(f"Connected to RabbitMQ at {self._host}:{self._port}")

        except ImportError:
            logger.error("aio-pika not installed. Install with: pip install aio-pika")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def close(self) -> None:
        """Close RabbitMQ connection."""
        if self._connection:
            await self._connection.close()
            logger.info("RabbitMQ connection closed")

    async def publish(
        self,
        queue_name: str,
        message: Message,
    ) -> str:
        """Publish a message to a queue."""
        import aio_pika

        # Ensure queue exists
        queue = await self._channel.declare_queue(
            queue_name,
            durable=True,
            arguments={"x-max-priority": 10},
        )

        # Serialize message body
        body = json.dumps(message.body).encode()

        # Build headers
        headers = {
            **message.headers,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Create AMQP message
        amqp_message = aio_pika.Message(
            body=body,
            priority=self.PRIORITY_MAP[message.priority],
            headers=headers,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            expiration=message.ttl_seconds,
        )

        # Publish with delay if specified
        if message.delay_seconds > 0:
            # Use dead-letter exchange for delayed messages
            delay_queue_name = f"{queue_name}.delay.{message.delay_seconds}"
            delay_queue = await self._channel.declare_queue(
                delay_queue_name,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": "",
                    "x-dead-letter-routing-key": queue_name,
                    "x-message-ttl": message.delay_seconds * 1000,
                },
            )
            await self._channel.default_exchange.publish(
                amqp_message,
                routing_key=delay_queue_name,
            )
        else:
            await self._channel.default_exchange.publish(
                amqp_message,
                routing_key=queue_name,
            )

        message_id = amqp_message.message_id or f"{queue_name}_{datetime.utcnow().timestamp()}"
        logger.debug(f"Published message {message_id} to queue {queue_name}")
        return message_id

    async def publish_batch(
        self,
        queue_name: str,
        messages: List[Message],
    ) -> List[str]:
        """Publish multiple messages to a queue."""
        message_ids = []
        for message in messages:
            message_id = await self.publish(queue_name, message)
            message_ids.append(message_id)
        return message_ids

    async def consume(
        self,
        queue_name: str,
        callback: Callable[[Message], None],
        max_messages: int = 1,
        visibility_timeout: int = 30,
    ) -> None:
        """Consume messages from a queue."""
        import aio_pika

        # Declare queue
        queue = await self._channel.declare_queue(
            queue_name,
            durable=True,
            arguments={"x-max-priority": 10},
        )

        # Set prefetch count
        await self._channel.set_qos(prefetch_count=max_messages)

        async def process_message(amqp_message: aio_pika.IncomingMessage):
            """Process incoming message."""
            async with amqp_message.process():
                try:
                    # Deserialize body
                    body = json.loads(amqp_message.body.decode())

                    # Create Message object
                    message = Message(
                        body=body,
                        headers=amqp_message.headers or {},
                    )
                    message.message_id = amqp_message.message_id
                    message.delivery_count = amqp_message.delivery_tag

                    # Call callback
                    await callback(message)

                    # Message is auto-acked by process() context manager

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode message: {e}")
                    # Reject invalid message
                    await amqp_message.reject(requeue=False)

                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    # Requeue on processing error
                    await amqp_message.reject(requeue=True)

        # Start consuming
        await queue.consume(process_message)

    async def acknowledge(
        self,
        queue_name: str,
        message_id: str,
    ) -> None:
        """Acknowledge successful processing of a message."""
        # RabbitMQ messages are acked in the consume() method
        # This is a no-op for compatibility with the interface
        pass

    async def reject(
        self,
        queue_name: str,
        message_id: str,
        requeue: bool = True,
    ) -> None:
        """Reject a message (failed processing)."""
        # RabbitMQ messages are rejected in the consume() method
        # This is a no-op for compatibility with the interface
        pass

    async def create_queue(
        self,
        queue_name: str,
        durable: bool = True,
        max_length: Optional[int] = None,
        message_ttl: Optional[int] = None,
    ) -> None:
        """Create a new queue."""
        arguments = {"x-max-priority": 10}

        if max_length:
            arguments["x-max-length"] = max_length

        if message_ttl:
            arguments["x-message-ttl"] = message_ttl * 1000  # Convert to milliseconds

        queue = await self._channel.declare_queue(
            queue_name,
            durable=durable,
            arguments=arguments,
        )

        logger.info(f"Created queue: {queue_name}")

    async def delete_queue(
        self,
        queue_name: str,
        if_empty: bool = False,
    ) -> None:
        """Delete a queue."""
        queue = await self._channel.get_queue(queue_name)

        if if_empty:
            # Check if queue is empty
            size = await self.get_queue_size(queue_name)
            if size > 0:
                raise ValueError(f"Queue {queue_name} is not empty ({size} messages)")

        await queue.delete()
        logger.info(f"Deleted queue: {queue_name}")

    async def purge_queue(
        self,
        queue_name: str,
    ) -> int:
        """Remove all messages from a queue."""
        queue = await self._channel.get_queue(queue_name)
        purge_result = await queue.purge()
        logger.info(f"Purged {purge_result} messages from queue {queue_name}")
        return purge_result

    async def get_queue_size(
        self,
        queue_name: str,
    ) -> int:
        """Get number of messages in queue."""
        queue = await self._channel.get_queue(queue_name)
        # Declare queue to get current state
        declared_queue = await self._channel.declare_queue(
            queue_name,
            passive=True,  # Don't create if doesn't exist
        )
        return declared_queue.declaration_result.message_count
