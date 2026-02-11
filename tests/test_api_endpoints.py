"""
Integration tests for FastAPI REST API endpoints.

Tests all API routers including trends, topics, search, health, admin, and WebSocket.
Uses FastAPI's TestClient for synchronous testing and httpx.AsyncClient for async tests.
"""

import pytest
from uuid import uuid4, UUID
from datetime import datetime
from fastapi.testclient import TestClient

# Import the FastAPI app
from api.main import app


# Fixtures

@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def valid_api_key():
    """Return a valid API key for testing."""
    return "dev_key_12345"


@pytest.fixture
def admin_api_key():
    """Return a valid admin API key for testing."""
    return "admin_key_67890"


@pytest.fixture
def mock_trend_data():
    """Return mock trend data for testing."""
    return {
        "id": str(uuid4()),
        "topic_id": str(uuid4()),
        "rank": 1,
        "title": "Test Trend",
        "summary": "This is a test trend",
        "key_points": ["Point 1", "Point 2"],
        "category": "Technology",
        "state": "viral",
        "score": 95.5,
        "sources": ["reddit", "hackernews"],
        "item_count": 10,
        "total_engagement": {
            "upvotes": 1000,
            "comments": 200,
            "score": 900.0,
        },
        "velocity": 12.5,
        "first_seen": datetime.utcnow().isoformat(),
        "last_updated": datetime.utcnow().isoformat(),
        "language": "en",
        "keywords": ["AI", "technology"],
    }


# Root endpoint tests

def test_root_endpoint(client):
    """Test the root endpoint returns API information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Trend Intelligence Platform API"
    assert "version" in data
    assert "endpoints" in data


# Health endpoint tests

def test_health_check(client):
    """Test basic health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_detailed_health_check(client):
    """Test detailed health check with service status."""
    response = client.get("/api/v1/health/detailed")
    assert response.status_code in [200, 503]  # May fail if services not available
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "services" in data


def test_version_endpoint(client):
    """Test version endpoint."""
    response = client.get("/api/v1/health/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "name" in data


def test_readiness_check(client):
    """Test readiness check endpoint."""
    response = client.get("/api/v1/health/ready")
    assert response.status_code in [200, 503]
    data = response.json()
    assert "ready" in data


def test_liveness_check(client):
    """Test liveness check endpoint."""
    response = client.get("/api/v1/health/liveness")
    assert response.status_code == 200
    data = response.json()
    assert data["alive"] is True


# Trend endpoint tests

def test_list_trends_without_auth(client):
    """Test listing trends without authentication (should work with optional auth)."""
    response = client.get("/api/v1/trends")
    # Should work since auth is optional for this endpoint
    assert response.status_code in [200, 503]  # 503 if DB not available


def test_list_trends_with_auth(client, valid_api_key):
    """Test listing trends with API key."""
    response = client.get(
        "/api/v1/trends",
        headers={"X-API-Key": valid_api_key}
    )
    assert response.status_code in [200, 503]


def test_list_trends_with_filters(client):
    """Test listing trends with query filters."""
    response = client.get(
        "/api/v1/trends",
        params={
            "limit": 10,
            "category": "Technology",
            "min_score": 50.0,
        }
    )
    assert response.status_code in [200, 503]


def test_get_top_trends(client):
    """Test getting top-ranked trends."""
    response = client.get("/api/v1/trends/top?limit=5")
    assert response.status_code in [200, 503]


def test_get_trend_by_id(client):
    """Test getting a single trend by ID."""
    test_id = uuid4()
    response = client.get(f"/api/v1/trends/{test_id}")
    # Should return 404 for non-existent trend or 503 if DB unavailable
    assert response.status_code in [404, 503]


def test_get_trend_stats(client):
    """Test getting trend statistics."""
    response = client.get("/api/v1/trends/stats/overview")
    assert response.status_code in [200, 503]


# Topic endpoint tests

def test_list_topics(client):
    """Test listing topics."""
    response = client.get("/api/v1/topics")
    assert response.status_code in [200, 503]


def test_list_topics_with_filters(client):
    """Test listing topics with filters."""
    response = client.get(
        "/api/v1/topics",
        params={
            "limit": 20,
            "category": "Technology",
            "language": "en",
        }
    )
    assert response.status_code in [200, 503]


def test_get_topic_by_id(client):
    """Test getting a single topic by ID."""
    test_id = uuid4()
    response = client.get(f"/api/v1/topics/{test_id}")
    assert response.status_code in [404, 503]


def test_search_topics(client):
    """Test searching topics by keywords."""
    response = client.post(
        "/api/v1/topics/search",
        params={"query": "artificial intelligence", "limit": 10}
    )
    assert response.status_code in [200, 503]


# Search endpoint tests

def test_keyword_search_without_auth(client):
    """Test keyword search without authentication (should fail)."""
    response = client.post(
        "/api/v1/search/keyword",
        json={
            "query": "AI breakthrough",
            "limit": 20,
            "search_type": "all",
        }
    )
    # Should fail without API key
    assert response.status_code == 401


def test_keyword_search_with_auth(client, valid_api_key):
    """Test keyword search with authentication."""
    response = client.post(
        "/api/v1/search/keyword",
        headers={"X-API-Key": valid_api_key},
        json={
            "query": "AI breakthrough",
            "limit": 20,
            "search_type": "all",
        }
    )
    assert response.status_code in [200, 503]


def test_semantic_search(client, valid_api_key):
    """Test semantic search (should return 501 Not Implemented for now)."""
    response = client.post(
        "/api/v1/search/semantic",
        headers={"X-API-Key": valid_api_key},
        json={
            "query": "AI breakthrough",
            "limit": 20,
            "min_similarity": 0.7,
        }
    )
    # Should return 501 or 503 depending on implementation status
    assert response.status_code in [501, 503]


def test_search_suggestions(client, valid_api_key):
    """Test search suggestions/autocomplete."""
    response = client.get(
        "/api/v1/search/suggestions",
        headers={"X-API-Key": valid_api_key},
        params={"query": "AI", "limit": 5}
    )
    assert response.status_code in [200, 503]


# Admin endpoint tests

def test_admin_without_auth(client):
    """Test admin endpoints without authentication (should fail)."""
    response = client.get("/api/v1/admin/plugins")
    assert response.status_code == 401


def test_admin_with_regular_key(client, valid_api_key):
    """Test admin endpoints with regular API key (should fail)."""
    response = client.get(
        "/api/v1/admin/plugins",
        headers={"X-API-Key": valid_api_key}
    )
    # Should fail - needs admin key
    assert response.status_code == 403


def test_list_plugins(client, admin_api_key):
    """Test listing all collector plugins."""
    response = client.get(
        "/api/v1/admin/plugins",
        headers={"X-API-Key": admin_api_key}
    )
    assert response.status_code in [200, 503]


def test_get_plugin(client, admin_api_key):
    """Test getting a specific plugin."""
    response = client.get(
        "/api/v1/admin/plugins/reddit",
        headers={"X-API-Key": admin_api_key}
    )
    assert response.status_code in [200, 404, 503]


def test_enable_plugin(client, admin_api_key):
    """Test enabling a plugin."""
    response = client.post(
        "/api/v1/admin/plugins/reddit/enable",
        headers={"X-API-Key": admin_api_key}
    )
    assert response.status_code in [200, 404, 503]


def test_disable_plugin(client, admin_api_key):
    """Test disabling a plugin."""
    response = client.post(
        "/api/v1/admin/plugins/reddit/disable",
        headers={"X-API-Key": admin_api_key}
    )
    assert response.status_code in [200, 404, 503]


def test_trigger_collection(client, admin_api_key):
    """Test triggering manual collection."""
    response = client.post(
        "/api/v1/admin/collect",
        headers={"X-API-Key": admin_api_key},
        json={
            "plugin_name": None,
            "force": False,
        }
    )
    assert response.status_code in [202, 503]


def test_get_system_metrics(client, admin_api_key):
    """Test getting system metrics."""
    response = client.get(
        "/api/v1/admin/metrics",
        headers={"X-API-Key": admin_api_key}
    )
    assert response.status_code in [200, 503]


def test_clear_cache(client, admin_api_key):
    """Test clearing cache."""
    response = client.delete(
        "/api/v1/admin/cache/clear",
        headers={"X-API-Key": admin_api_key}
    )
    assert response.status_code in [200, 503]


# WebSocket tests

def test_websocket_trends(client):
    """Test WebSocket connection for trends."""
    with client.websocket_connect("/ws/trends") as websocket:
        # Should receive welcome message
        data = websocket.receive_json()
        assert data["type"] == "connection"
        assert data["status"] == "connected"
        assert data["subscription"] == "trends"

        # Send a test message
        websocket.send_text("ping")

        # Should receive echo response
        response = websocket.receive_json()
        assert response["type"] == "echo"


def test_websocket_topics(client):
    """Test WebSocket connection for topics."""
    with client.websocket_connect("/ws/topics") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "connection"
        assert data["subscription"] == "topics"


def test_websocket_all(client):
    """Test WebSocket connection for all updates."""
    with client.websocket_connect("/ws") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "connection"
        assert data["subscription"] == "all"


# Error handling tests

def test_invalid_api_key(client):
    """Test request with invalid API key."""
    response = client.post(
        "/api/v1/search/keyword",
        headers={"X-API-Key": "invalid_key_12345"},
        json={"query": "test", "limit": 10}
    )
    assert response.status_code == 401


def test_missing_required_field(client, valid_api_key):
    """Test request with missing required fields."""
    response = client.post(
        "/api/v1/search/keyword",
        headers={"X-API-Key": valid_api_key},
        json={"limit": 10}  # Missing 'query' field
    )
    assert response.status_code == 422  # Validation error


def test_invalid_uuid(client):
    """Test endpoint with invalid UUID."""
    response = client.get("/api/v1/trends/invalid-uuid")
    assert response.status_code == 422  # Validation error


def test_pagination_limits(client):
    """Test pagination parameter validation."""
    # Test limit too high
    response = client.get("/api/v1/trends?limit=1000")
    assert response.status_code == 400

    # Test negative offset
    response = client.get("/api/v1/trends?offset=-1")
    assert response.status_code == 400


# Integration tests (require running services)

@pytest.mark.integration
def test_full_trend_workflow(client, valid_api_key):
    """
    Integration test for full trend workflow.

    Note: Requires running database and services.
    """
    # 1. List trends
    response = client.get("/api/v1/trends")
    assert response.status_code == 200

    # 2. Get top trends
    response = client.get("/api/v1/trends/top?limit=5")
    assert response.status_code == 200

    # 3. Get stats
    response = client.get("/api/v1/trends/stats/overview")
    assert response.status_code == 200


@pytest.mark.integration
def test_full_admin_workflow(client, admin_api_key):
    """
    Integration test for admin workflow.

    Note: Requires running services.
    """
    # 1. List plugins
    response = client.get(
        "/api/v1/admin/plugins",
        headers={"X-API-Key": admin_api_key}
    )
    assert response.status_code == 200

    # 2. Get metrics
    response = client.get(
        "/api/v1/admin/metrics",
        headers={"X-API-Key": admin_api_key}
    )
    assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
