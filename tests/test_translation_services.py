"""
Unit tests for translation services.

Tests the OpenAI, LibreTranslate, and DeepL translation providers,
as well as the TranslationCache and TranslationManager.
"""

import asyncio
import hashlib
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from trend_agent.services.translation import (
    BaseTranslationService,
    OpenAITranslationService,
    LibreTranslateService,
    DeepLTranslationService,
)
from trend_agent.services.translation_manager import (
    TranslationCache,
    TranslationManager,
)


# ============================================================================
# Mock Translation Service for Testing
# ============================================================================


class MockTranslationService(BaseTranslationService):
    """Mock translation service for testing."""

    def __init__(self, name: str = "mock", should_fail: bool = False):
        self.name = name
        self.should_fail = should_fail
        self.call_count = 0
        self.translate_calls = []
        self.batch_calls = []

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> str:
        """Mock translate method."""
        self.call_count += 1
        self.translate_calls.append((text, target_language, source_language))

        if self.should_fail:
            raise Exception(f"{self.name} translation failed")

        return f"[{self.name}:{target_language}] {text}"

    async def translate_batch(
        self,
        texts: list[str],
        target_language: str,
        source_language: Optional[str] = None,
    ) -> list[str]:
        """Mock batch translate method."""
        self.call_count += 1
        self.batch_calls.append((texts, target_language, source_language))

        if self.should_fail:
            raise Exception(f"{self.name} batch translation failed")

        return [f"[{self.name}:{target_language}] {text}" for text in texts]

    async def detect_language(self, text: str) -> str:
        """Mock language detection."""
        return "en"

    def get_supported_languages(self) -> list[str]:
        """Mock supported languages."""
        return ["en", "es", "fr", "de", "ja", "zh"]

    def get_stats(self) -> dict:
        """Mock stats."""
        return {"total_calls": self.call_count}


# ============================================================================
# Mock Redis Cache for Testing
# ============================================================================


class MockRedisCache:
    """Mock Redis cache for testing."""

    def __init__(self):
        self.cache = {}
        self.get_count = 0
        self.set_count = 0

    async def get(self, key: str) -> Optional[str]:
        """Mock get."""
        self.get_count += 1
        return self.cache.get(key)

    async def set(self, key: str, value: str, ttl: int = 3600) -> None:
        """Mock set."""
        self.set_count += 1
        self.cache[key] = value

    async def exists(self, key: str) -> bool:
        """Mock exists."""
        return key in self.cache

    async def delete(self, key: str) -> None:
        """Mock delete."""
        if key in self.cache:
            del self.cache[key]

    async def mget(self, keys: list[str]) -> list[Optional[str]]:
        """Mock mget."""
        self.get_count += len(keys)
        return [self.cache.get(key) for key in keys]

    async def mset(self, mapping: dict[str, str], ttl: int = 3600) -> None:
        """Mock mset."""
        self.set_count += len(mapping)
        self.cache.update(mapping)


# ============================================================================
# TranslationCache Tests
# ============================================================================


@pytest.mark.asyncio
class TestTranslationCache:
    """Tests for TranslationCache."""

    async def test_cache_key_generation(self):
        """Test cache key generation."""
        mock_redis = MockRedisCache()
        cache = TranslationCache(redis_repository=mock_redis)

        # Generate key
        key = cache._generate_cache_key("Hello", "en", "es")

        # Should contain prefix and languages
        assert "translation:" in key
        assert ":en:es:" in key

        # Should be deterministic
        key2 = cache._generate_cache_key("Hello", "en", "es")
        assert key == key2

        # Different text should produce different key
        key3 = cache._generate_cache_key("Goodbye", "en", "es")
        assert key != key3

    async def test_cache_get_miss(self):
        """Test cache get when no cached value exists."""
        mock_redis = MockRedisCache()
        cache = TranslationCache(redis_repository=mock_redis)

        result = await cache.get("Hello", "en", "es")
        assert result is None
        assert mock_redis.get_count == 1

    async def test_cache_get_hit(self):
        """Test cache get when cached value exists."""
        mock_redis = MockRedisCache()
        cache = TranslationCache(redis_repository=mock_redis)

        # Set a cached value
        await cache.set("Hello", "Hola", "en", "es")
        assert mock_redis.set_count == 1

        # Retrieve it
        result = await cache.get("Hello", "en", "es")
        assert result == "Hola"
        assert mock_redis.get_count == 1

    async def test_cache_auto_detect_language(self):
        """Test cache with auto-detected language."""
        mock_redis = MockRedisCache()
        cache = TranslationCache(redis_repository=mock_redis)

        # Set with None source language (auto-detect)
        await cache.set("Hello", "Hola", None, "es")

        # Should retrieve with None or "auto"
        result1 = await cache.get("Hello", None, "es")
        assert result1 == "Hola"

        result2 = await cache.get("Hello", "auto", "es")
        assert result2 == "Hola"

    async def test_cache_batch_operations(self):
        """Test batch cache operations."""
        mock_redis = MockRedisCache()
        cache = TranslationCache(redis_repository=mock_redis)

        texts = ["Hello", "Goodbye", "Thank you"]
        translations = ["Hola", "Adiós", "Gracias"]

        # Set batch
        await cache.set_batch(texts, translations, "en", "es")
        assert mock_redis.set_count == 3

        # Get batch - should have all cached
        results = await cache.get_batch(texts, "en", "es")
        assert results == translations
        assert mock_redis.get_count == 3

    async def test_cache_partial_batch_hit(self):
        """Test batch cache with partial hits."""
        mock_redis = MockRedisCache()
        cache = TranslationCache(redis_repository=mock_redis)

        texts = ["Hello", "Goodbye", "Thank you"]

        # Cache only the first one
        await cache.set("Hello", "Hola", "en", "es")

        # Get batch - should return [cached, None, None]
        results = await cache.get_batch(texts, "en", "es")
        assert results[0] == "Hola"
        assert results[1] is None
        assert results[2] is None

    async def test_cache_stats(self):
        """Test cache statistics tracking."""
        mock_redis = MockRedisCache()
        cache = TranslationCache(redis_repository=mock_redis)

        # Initial stats
        stats = cache.get_stats()
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["hit_rate_percent"] == 0.0

        # Cache miss
        await cache.get("Hello", "en", "es")
        stats = cache.get_stats()
        assert stats["cache_misses"] == 1
        assert stats["hit_rate_percent"] == 0.0

        # Cache set and hit
        await cache.set("Hello", "Hola", "en", "es")
        await cache.get("Hello", "en", "es")
        stats = cache.get_stats()
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1
        assert stats["hit_rate_percent"] == 50.0

    async def test_cache_ttl_configuration(self):
        """Test cache TTL configuration."""
        mock_redis = MockRedisCache()
        custom_ttl = 86400  # 1 day

        cache = TranslationCache(
            redis_repository=mock_redis,
            ttl=custom_ttl,
        )

        assert cache.ttl == custom_ttl


# ============================================================================
# TranslationManager Tests
# ============================================================================


@pytest.mark.asyncio
class TestTranslationManager:
    """Tests for TranslationManager."""

    async def test_provider_selection_by_priority(self):
        """Test provider selection respects priority order."""
        provider1 = MockTranslationService(name="provider1")
        provider2 = MockTranslationService(name="provider2")
        provider3 = MockTranslationService(name="provider3")

        manager = TranslationManager(
            providers={
                "provider1": provider1,
                "provider2": provider2,
                "provider3": provider3,
            },
            cache=None,
            provider_priority=["provider2", "provider1", "provider3"],
        )

        # Should use provider2 first (highest priority)
        result = await manager.translate("Hello", "es")
        assert result.startswith("[provider2:")
        assert provider2.call_count == 1
        assert provider1.call_count == 0
        assert provider3.call_count == 0

    async def test_provider_fallback_on_failure(self):
        """Test automatic fallback to next provider on failure."""
        provider1 = MockTranslationService(name="provider1", should_fail=True)
        provider2 = MockTranslationService(name="provider2")

        manager = TranslationManager(
            providers={
                "provider1": provider1,
                "provider2": provider2,
            },
            cache=None,
            provider_priority=["provider1", "provider2"],
            enable_fallback=True,
        )

        # Should fallback to provider2 when provider1 fails
        result = await manager.translate("Hello", "es")
        assert result.startswith("[provider2:")
        assert provider1.call_count == 1  # Tried first
        assert provider2.call_count == 1  # Used as fallback

    async def test_all_providers_fail(self):
        """Test error when all providers fail."""
        provider1 = MockTranslationService(name="provider1", should_fail=True)
        provider2 = MockTranslationService(name="provider2", should_fail=True)

        manager = TranslationManager(
            providers={
                "provider1": provider1,
                "provider2": provider2,
            },
            cache=None,
            provider_priority=["provider1", "provider2"],
            enable_fallback=True,
        )

        # Should raise exception when all providers fail
        with pytest.raises(Exception, match="All translation providers failed"):
            await manager.translate("Hello", "es")

    async def test_preferred_provider(self):
        """Test using preferred provider."""
        provider1 = MockTranslationService(name="provider1")
        provider2 = MockTranslationService(name="provider2")

        manager = TranslationManager(
            providers={
                "provider1": provider1,
                "provider2": provider2,
            },
            cache=None,
            provider_priority=["provider1", "provider2"],
        )

        # Request specific provider
        result = await manager.translate("Hello", "es", preferred_provider="provider2")
        assert result.startswith("[provider2:")
        assert provider2.call_count == 1
        assert provider1.call_count == 0

    async def test_cache_integration(self):
        """Test cache integration with translation."""
        mock_redis = MockRedisCache()
        cache = TranslationCache(redis_repository=mock_redis)
        provider = MockTranslationService(name="provider1")

        manager = TranslationManager(
            providers={"provider1": provider},
            cache=cache,
            provider_priority=["provider1"],
        )

        # First call - cache miss, should translate
        result1 = await manager.translate("Hello", "es", "en")
        assert result1.startswith("[provider1:")
        assert provider.call_count == 1

        # Second call - cache hit, should NOT translate
        result2 = await manager.translate("Hello", "es", "en")
        assert result2 == result1
        assert provider.call_count == 1  # Not incremented

        # Verify cache stats
        stats = cache.get_stats()
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1

    async def test_batch_translation(self):
        """Test batch translation."""
        provider = MockTranslationService(name="provider1")

        manager = TranslationManager(
            providers={"provider1": provider},
            cache=None,
            provider_priority=["provider1"],
        )

        texts = ["Hello", "Goodbye", "Thank you"]
        results = await manager.translate_batch(texts, "es", "en")

        assert len(results) == 3
        assert all(r.startswith("[provider1:es]") for r in results)
        assert provider.call_count == 1  # Batch call
        assert len(provider.batch_calls) == 1

    async def test_batch_with_cache(self):
        """Test batch translation with caching."""
        mock_redis = MockRedisCache()
        cache = TranslationCache(redis_repository=mock_redis)
        provider = MockTranslationService(name="provider1")

        manager = TranslationManager(
            providers={"provider1": provider},
            cache=cache,
            provider_priority=["provider1"],
        )

        texts = ["Hello", "Goodbye", "Thank you"]

        # First batch - cache miss
        await manager.translate_batch(texts, "es", "en")
        assert provider.call_count == 1

        # Second batch - cache hit
        await manager.translate_batch(texts, "es", "en")
        assert provider.call_count == 1  # Not incremented

    async def test_language_detection(self):
        """Test language detection."""
        provider = MockTranslationService(name="provider1")

        manager = TranslationManager(
            providers={"provider1": provider},
            cache=None,
            provider_priority=["provider1"],
        )

        lang = await manager.detect_language("Hello world")
        assert lang == "en"

    async def test_supported_languages(self):
        """Test getting supported languages from all providers."""
        provider1 = MockTranslationService(name="provider1")
        provider2 = MockTranslationService(name="provider2")

        manager = TranslationManager(
            providers={
                "provider1": provider1,
                "provider2": provider2,
            },
            cache=None,
            provider_priority=["provider1", "provider2"],
        )

        languages = manager.get_supported_languages()
        assert isinstance(languages, list)
        assert "en" in languages
        assert "es" in languages

    async def test_manager_stats(self):
        """Test translation manager statistics."""
        provider1 = MockTranslationService(name="provider1")
        provider2 = MockTranslationService(name="provider2")

        manager = TranslationManager(
            providers={
                "provider1": provider1,
                "provider2": provider2,
            },
            cache=None,
            provider_priority=["provider1", "provider2"],
        )

        # Make some translations
        await manager.translate("Hello", "es")
        await manager.translate("Goodbye", "fr")

        stats = manager.get_stats()
        assert stats["total_translations"] == 2
        assert "provider1" in stats["provider_usage"]
        assert stats["provider_usage"]["provider1"] == 2

    async def test_fallback_disabled(self):
        """Test behavior when fallback is disabled."""
        provider1 = MockTranslationService(name="provider1", should_fail=True)
        provider2 = MockTranslationService(name="provider2")

        manager = TranslationManager(
            providers={
                "provider1": provider1,
                "provider2": provider2,
            },
            cache=None,
            provider_priority=["provider1", "provider2"],
            enable_fallback=False,  # Disabled
        )

        # Should raise exception immediately without trying provider2
        with pytest.raises(Exception):
            await manager.translate("Hello", "es")

        assert provider1.call_count == 1
        assert provider2.call_count == 0  # Not tried


# ============================================================================
# OpenAI Translation Service Tests (Mocked)
# ============================================================================


@pytest.mark.asyncio
class TestOpenAITranslationService:
    """Tests for OpenAITranslationService (with mocked API)."""

    @patch("openai.AsyncOpenAI")
    async def test_translate_single_text(self, mock_openai_class):
        """Test single text translation."""
        # Mock OpenAI response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hola, mundo"))]
        mock_response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        service = OpenAITranslationService(api_key="test-key")

        result = await service.translate("Hello, world", "es", "en")
        assert result == "Hola, mundo"

        # Verify API was called
        assert mock_client.chat.completions.create.called

    @patch("openai.AsyncOpenAI")
    async def test_batch_translation(self, mock_openai_class):
        """Test batch translation."""
        # Mock OpenAI response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="[1] Hola\n[2] Adiós\n[3] Gracias"))
        ]
        mock_response.usage = MagicMock(prompt_tokens=20, completion_tokens=15)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        service = OpenAITranslationService(api_key="test-key")

        results = await service.translate_batch(
            ["Hello", "Goodbye", "Thank you"], "es", "en"
        )

        assert len(results) == 3
        assert "Hola" in results[0]

    @patch("openai.AsyncOpenAI")
    async def test_cost_tracking(self, mock_openai_class):
        """Test cost tracking for translations."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hola"))]
        mock_response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_openai_class.return_value = mock_client

        service = OpenAITranslationService(api_key="test-key")

        await service.translate("Hello", "es", "en")

        stats = service.get_stats()
        assert stats["total_requests"] == 1
        assert stats["total_input_tokens"] == 100
        assert stats["total_output_tokens"] == 50
        assert stats["total_cost_usd"] > 0


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
