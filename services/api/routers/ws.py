"""
WebSocket endpoints for real-time trend and topic updates.

Provides WebSocket connections for streaming real-time updates
when new trends are detected or existing trends change.
"""

import asyncio
import json
import logging
from typing import Set, Dict, Any
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


# Connection manager for WebSocket clients
class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.topic_subscriptions: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, topic: str = "all"):
        """
        Accept a WebSocket connection and add to active connections.

        Args:
            websocket: WebSocket connection
            topic: Subscription topic (all, trends, topics)
        """
        await websocket.accept()
        self.active_connections.add(websocket)

        if topic not in self.topic_subscriptions:
            self.topic_subscriptions[topic] = set()
        self.topic_subscriptions[topic].add(websocket)

        logger.info(f"WebSocket connected. Topic: {topic}, Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection from active connections.

        Args:
            websocket: WebSocket connection to remove
        """
        self.active_connections.discard(websocket)

        # Remove from all topic subscriptions
        for topic_connections in self.topic_subscriptions.values():
            topic_connections.discard(websocket)

        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """
        Send a message to a specific WebSocket connection.

        Args:
            message: Message to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str, topic: str = "all"):
        """
        Broadcast a message to all connections subscribed to a topic.

        Args:
            message: Message to broadcast
            topic: Topic to broadcast to (default: all)
        """
        connections = self.topic_subscriptions.get(topic, set())
        disconnected = set()

        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.add(connection)

        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_json(self, data: Dict[str, Any], topic: str = "all"):
        """
        Broadcast JSON data to all connections on a topic.

        Args:
            data: Dictionary to send as JSON
            topic: Topic to broadcast to
        """
        message = json.dumps(data)
        await self.broadcast(message, topic)


# Global connection manager instance
manager = ConnectionManager()


class TrendUpdate(BaseModel):
    """WebSocket message for trend updates."""

    type: str = "trend_update"
    action: str  # created, updated, deleted
    trend_id: str
    rank: int
    title: str
    category: str
    score: float
    timestamp: str


class TopicUpdate(BaseModel):
    """WebSocket message for topic updates."""

    type: str = "topic_update"
    action: str  # created, updated
    topic_id: str
    title: str
    category: str
    item_count: int
    timestamp: str


class ConnectionMessage(BaseModel):
    """WebSocket connection status message."""

    type: str = "connection"
    status: str
    message: str
    timestamp: str
    subscription: str


@router.websocket("/ws/trends")
async def websocket_trends(
    websocket: WebSocket,
    api_key: str = Query(None, description="Optional API key for authentication"),
):
    """
    WebSocket endpoint for real-time trend updates.

    Subscribe to this endpoint to receive notifications when:
    - New trends are created
    - Existing trends are updated (rank changes, score changes)
    - Trends are deleted

    Example client code (JavaScript):
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/ws/trends?api_key=YOUR_KEY');

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Trend update:', data);
    };
    ```

    Args:
        websocket: WebSocket connection
        api_key: Optional API key for authentication
    """
    await manager.connect(websocket, topic="trends")

    # Send welcome message
    welcome = ConnectionMessage(
        type="connection",
        status="connected",
        message="Connected to trends WebSocket. You will receive real-time trend updates.",
        timestamp=datetime.utcnow().isoformat() + "Z",
        subscription="trends",
    )
    await manager.send_personal_message(welcome.json(), websocket)

    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()

            # Echo back for heartbeat/testing
            response = {
                "type": "echo",
                "data": data,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            await manager.send_personal_message(json.dumps(response), websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected from trends WebSocket")


@router.websocket("/ws/topics")
async def websocket_topics(
    websocket: WebSocket,
    api_key: str = Query(None, description="Optional API key for authentication"),
):
    """
    WebSocket endpoint for real-time topic updates.

    Subscribe to this endpoint to receive notifications when:
    - New topics are created (clusters detected)
    - Existing topics are updated (new items added, engagement changes)

    Args:
        websocket: WebSocket connection
        api_key: Optional API key for authentication
    """
    await manager.connect(websocket, topic="topics")

    # Send welcome message
    welcome = ConnectionMessage(
        type="connection",
        status="connected",
        message="Connected to topics WebSocket. You will receive real-time topic updates.",
        timestamp=datetime.utcnow().isoformat() + "Z",
        subscription="topics",
    )
    await manager.send_personal_message(welcome.json(), websocket)

    try:
        while True:
            data = await websocket.receive_text()

            response = {
                "type": "echo",
                "data": data,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            await manager.send_personal_message(json.dumps(response), websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected from topics WebSocket")


@router.websocket("/ws")
async def websocket_all(
    websocket: WebSocket,
    api_key: str = Query(None, description="Optional API key for authentication"),
):
    """
    WebSocket endpoint for all real-time updates (trends + topics).

    Subscribe to this endpoint to receive all types of updates.

    Args:
        websocket: WebSocket connection
        api_key: Optional API key for authentication
    """
    await manager.connect(websocket, topic="all")

    # Send welcome message
    welcome = ConnectionMessage(
        type="connection",
        status="connected",
        message="Connected to all updates WebSocket. You will receive real-time trend and topic updates.",
        timestamp=datetime.utcnow().isoformat() + "Z",
        subscription="all",
    )
    await manager.send_personal_message(welcome.json(), websocket)

    try:
        while True:
            data = await websocket.receive_text()

            response = {
                "type": "echo",
                "data": data,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            await manager.send_personal_message(json.dumps(response), websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected from all updates WebSocket")


# Utility functions for broadcasting updates (to be called from other parts of the application)

async def broadcast_trend_update(trend_id: str, action: str, trend_data: Dict[str, Any]):
    """
    Broadcast a trend update to all connected WebSocket clients.

    This function should be called when trends are created, updated, or deleted.

    Args:
        trend_id: UUID of the trend
        action: Action performed (created, updated, deleted)
        trend_data: Trend data dictionary
    """
    update = TrendUpdate(
        action=action,
        trend_id=trend_id,
        rank=trend_data.get("rank", 0),
        title=trend_data.get("title", ""),
        category=trend_data.get("category", ""),
        score=trend_data.get("score", 0.0),
        timestamp=datetime.utcnow().isoformat() + "Z",
    )

    await manager.broadcast_json(update.dict(), topic="trends")
    await manager.broadcast_json(update.dict(), topic="all")


async def broadcast_topic_update(topic_id: str, action: str, topic_data: Dict[str, Any]):
    """
    Broadcast a topic update to all connected WebSocket clients.

    This function should be called when topics are created or updated.

    Args:
        topic_id: UUID of the topic
        action: Action performed (created, updated)
        topic_data: Topic data dictionary
    """
    update = TopicUpdate(
        action=action,
        topic_id=topic_id,
        title=topic_data.get("title", ""),
        category=topic_data.get("category", ""),
        item_count=topic_data.get("item_count", 0),
        timestamp=datetime.utcnow().isoformat() + "Z",
    )

    await manager.broadcast_json(update.dict(), topic="topics")
    await manager.broadcast_json(update.dict(), topic="all")
