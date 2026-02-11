"""
Integration tests for Translation API endpoints.

Tests the FastAPI translation router endpoints with mocked services.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from api.main import app


# ============================================================================
# Test Client Setup
# ============================================================================


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_translation_manager():
    """Create mock translation manager."""
    manager = MagicMock()

    # Mock translate method
    manager.translate = AsyncMock(return_value="Translated text")

    # Mock translate_batch method
    manager.translate_batch = AsyncMock(
        return_value=["Translation 1", "Translation 2", "Translation 3"]
    )

    # Mock detect_language method
    manager.detect_language = AsyncMock(return_value="en")

    # Mock get_supported_languages method
    manager.get_supported_languages = MagicMock(
        return_value=["en", "es", "fr", "de", "ja", "zh", "ar", "ru"]
    )

    # Mock get_stats method
    manager.get_stats = MagicMock(
        return_value={
            "total_translations": 100,
            "cache_stats": {
                "cache_hits": 30,
                "cache_misses": 70,
                "hit_rate_percent": 30.0,
            },
            "provider_usage": {
                "libretranslate": 50,
                "openai": 30,
                "deepl": 20,
            },
            "provider_failures": {
                "libretranslate": 2,
                "openai": 1,
                "deepl": 0,
            },
        }
    )

    # Mock cache attribute
    mock_cache = MagicMock()
    mock_cache.get = AsyncMock(return_value=None)  # Default: no cache hit
    manager.cache = mock_cache

    return manager


# ============================================================================
# Translation Endpoint Tests
# ============================================================================


def test_translate_endpoint(client, mock_translation_manager):
    """Test POST /api/v1/translation/translate endpoint."""
    with patch(
        "api.routers.translation.get_service_factory"
    ) as mock_factory_getter:
        mock_factory = MagicMock()
        mock_factory.get_translation_manager = MagicMock(
            return_value=mock_translation_manager
        )
        mock_factory_getter.return_value = mock_factory

        response = client.post(
            "/api/v1/translation/translate",
            json={
                "text": "Hello, world!",
                "target_language": "es",
                "source_language": "en",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "translated_text" in data
        assert data["translated_text"] == "Translated text"
        assert data["target_language"] == "es"
        assert data["source_language"] == "en"
        assert data["original_text"] == "Hello, world!"


def test_translate_with_cache_hit(client, mock_translation_manager):
    """Test translation with cache hit."""
    # Configure cache to return a cached value
    mock_translation_manager.cache.get = AsyncMock(return_value="Cached translation")

    with patch(
        "api.routers.translation.get_service_factory"
    ) as mock_factory_getter:
        mock_factory = MagicMock()
        mock_factory.get_translation_manager = MagicMock(
            return_value=mock_translation_manager
        )
        mock_factory_getter.return_value = mock_factory

        response = client.post(
            "/api/v1/translation/translate",
            json={
                "text": "Hello",
                "target_language": "es",
                "source_language": "en",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["translated_text"] == "Cached translation"
        assert data["cached"] is True
        assert data["provider_used"] == "cache"


def test_translate_with_preferred_provider(client, mock_translation_manager):
    """Test translation with preferred provider."""
    with patch(
        "api.routers.translation.get_service_factory"
    ) as mock_factory_getter:
        mock_factory = MagicMock()
        mock_factory.get_translation_manager = MagicMock(
            return_value=mock_translation_manager
        )
        mock_factory_getter.return_value = mock_factory

        response = client.post(
            "/api/v1/translation/translate",
            json={
                "text": "Hello",
                "target_language": "es",
                "preferred_provider": "openai",
            },
        )

        assert response.status_code == 200
        # Verify preferred_provider was passed
        mock_translation_manager.translate.assert_called_once()
        call_kwargs = mock_translation_manager.translate.call_args[1]
        assert call_kwargs["preferred_provider"] == "openai"


def test_translate_validation_error(client):
    """Test translation with invalid input."""
    response = client.post(
        "/api/v1/translation/translate",
        json={
            "text": "",  # Empty text (should fail validation)
            "target_language": "es",
        },
    )

    assert response.status_code == 422  # Validation error


def test_translate_missing_required_fields(client):
    """Test translation with missing required fields."""
    response = client.post(
        "/api/v1/translation/translate",
        json={
            "text": "Hello",
            # Missing target_language
        },
    )

    assert response.status_code == 422


# ============================================================================
# Batch Translation Endpoint Tests
# ============================================================================


def test_batch_translate_endpoint(client, mock_translation_manager):
    """Test POST /api/v1/translation/translate/batch endpoint."""
    with patch(
        "api.routers.translation.get_service_factory"
    ) as mock_factory_getter:
        mock_factory = MagicMock()
        mock_factory.get_translation_manager = MagicMock(
            return_value=mock_translation_manager
        )
        mock_factory_getter.return_value = mock_factory

        response = client.post(
            "/api/v1/translation/translate/batch",
            json={
                "texts": ["Hello", "Goodbye", "Thank you"],
                "target_language": "fr",
                "source_language": "en",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "translations" in data
        assert len(data["translations"]) == 3
        assert data["total_translations"] == 3
        assert "provider_stats" in data


def test_batch_translate_validation_min_items(client):
    """Test batch translation with too few items."""
    response = client.post(
        "/api/v1/translation/translate/batch",
        json={
            "texts": [],  # Empty list (should fail validation)
            "target_language": "fr",
        },
    )

    assert response.status_code == 422


def test_batch_translate_validation_max_items(client, mock_translation_manager):
    """Test batch translation with too many items."""
    with patch(
        "api.routers.translation.get_service_factory"
    ) as mock_factory_getter:
        mock_factory = MagicMock()
        mock_factory.get_translation_manager = MagicMock(
            return_value=mock_translation_manager
        )
        mock_factory_getter.return_value = mock_factory

        # Create 101 texts (max is 100)
        many_texts = [f"Text {i}" for i in range(101)]

        response = client.post(
            "/api/v1/translation/translate/batch",
            json={
                "texts": many_texts,
                "target_language": "fr",
            },
        )

        # Should fail validation (max_items=100)
        assert response.status_code == 422


# ============================================================================
# Language Detection Endpoint Tests
# ============================================================================


def test_detect_language_endpoint(client, mock_translation_manager):
    """Test POST /api/v1/translation/detect-language endpoint."""
    with patch(
        "api.routers.translation.get_service_factory"
    ) as mock_factory_getter:
        mock_factory = MagicMock()
        mock_factory.get_translation_manager = MagicMock(
            return_value=mock_translation_manager
        )
        mock_factory_getter.return_value = mock_factory

        response = client.post(
            "/api/v1/translation/detect-language",
            params={"text": "Bonjour le monde"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "detected_language" in data
        assert data["detected_language"] == "en"  # Mock returns "en"
        assert "text" in data


def test_detect_language_validation_min_length(client):
    """Test language detection with text too short."""
    response = client.post(
        "/api/v1/translation/detect-language",
        params={"text": "Hi"},  # Only 2 chars (min is 3)
    )

    assert response.status_code == 422


# ============================================================================
# Supported Languages Endpoint Tests
# ============================================================================


def test_get_supported_languages(client, mock_translation_manager):
    """Test GET /api/v1/translation/languages endpoint."""
    with patch(
        "api.routers.translation.get_service_factory"
    ) as mock_factory_getter:
        mock_factory = MagicMock()
        mock_factory.get_translation_manager = MagicMock(
            return_value=mock_translation_manager
        )
        mock_factory_getter.return_value = mock_factory

        response = client.get("/api/v1/translation/languages")

        assert response.status_code == 200
        data = response.json()

        assert "languages" in data
        assert "count" in data
        assert isinstance(data["languages"], list)
        assert data["count"] > 0
        assert "en" in data["languages"]


# ============================================================================
# Translation Stats Endpoint Tests
# ============================================================================


def test_get_translation_stats(client, mock_translation_manager):
    """Test GET /api/v1/translation/stats endpoint."""
    with patch(
        "api.routers.translation.get_service_factory"
    ) as mock_factory_getter:
        mock_factory = MagicMock()
        mock_factory.get_translation_manager = MagicMock(
            return_value=mock_translation_manager
        )
        mock_factory_getter.return_value = mock_factory

        response = client.get("/api/v1/translation/stats")

        assert response.status_code == 200
        data = response.json()

        assert "total_translations" in data
        assert "cache_hits" in data
        assert "cache_hit_rate_percent" in data
        assert "provider_usage" in data
        assert "provider_failures" in data

        assert data["total_translations"] == 100
        assert data["cache_hits"] == 30
        assert data["cache_hit_rate_percent"] == 30.0


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_translate_service_error(client, mock_translation_manager):
    """Test handling of translation service errors."""
    # Configure manager to raise error
    mock_translation_manager.translate = AsyncMock(
        side_effect=Exception("Translation service failed")
    )

    with patch(
        "api.routers.translation.get_service_factory"
    ) as mock_factory_getter:
        mock_factory = MagicMock()
        mock_factory.get_translation_manager = MagicMock(
            return_value=mock_translation_manager
        )
        mock_factory_getter.return_value = mock_factory

        response = client.post(
            "/api/v1/translation/translate",
            json={
                "text": "Hello",
                "target_language": "es",
            },
        )

        assert response.status_code == 500
        assert "Translation failed" in response.text


def test_batch_translate_service_error(client, mock_translation_manager):
    """Test handling of batch translation errors."""
    mock_translation_manager.translate_batch = AsyncMock(
        side_effect=Exception("Batch translation failed")
    )

    with patch(
        "api.routers.translation.get_service_factory"
    ) as mock_factory_getter:
        mock_factory = MagicMock()
        mock_factory.get_translation_manager = MagicMock(
            return_value=mock_translation_manager
        )
        mock_factory_getter.return_value = mock_factory

        response = client.post(
            "/api/v1/translation/translate/batch",
            json={
                "texts": ["Hello", "World"],
                "target_language": "es",
            },
        )

        assert response.status_code == 500


def test_detect_language_service_error(client, mock_translation_manager):
    """Test handling of language detection errors."""
    mock_translation_manager.detect_language = AsyncMock(
        side_effect=Exception("Detection failed")
    )

    with patch(
        "api.routers.translation.get_service_factory"
    ) as mock_factory_getter:
        mock_factory = MagicMock()
        mock_factory.get_translation_manager = MagicMock(
            return_value=mock_translation_manager
        )
        mock_factory_getter.return_value = mock_factory

        response = client.post(
            "/api/v1/translation/detect-language",
            params={"text": "Hello world"},
        )

        assert response.status_code == 500


# ============================================================================
# Response Model Tests
# ============================================================================


def test_translate_response_schema(client, mock_translation_manager):
    """Test that translation response matches schema."""
    with patch(
        "api.routers.translation.get_service_factory"
    ) as mock_factory_getter:
        mock_factory = MagicMock()
        mock_factory.get_translation_manager = MagicMock(
            return_value=mock_translation_manager
        )
        mock_factory_getter.return_value = mock_factory

        response = client.post(
            "/api/v1/translation/translate",
            json={
                "text": "Hello",
                "target_language": "es",
                "source_language": "en",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields
        required_fields = [
            "original_text",
            "translated_text",
            "source_language",
            "target_language",
            "provider_used",
            "cached",
        ]

        for field in required_fields:
            assert field in data


def test_batch_translate_response_schema(client, mock_translation_manager):
    """Test that batch translation response matches schema."""
    with patch(
        "api.routers.translation.get_service_factory"
    ) as mock_factory_getter:
        mock_factory = MagicMock()
        mock_factory.get_translation_manager = MagicMock(
            return_value=mock_translation_manager
        )
        mock_factory_getter.return_value = mock_factory

        response = client.post(
            "/api/v1/translation/translate/batch",
            json={
                "texts": ["Hello", "World"],
                "target_language": "es",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "translations" in data
        assert "total_translations" in data
        assert "provider_stats" in data
        assert isinstance(data["translations"], list)


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
