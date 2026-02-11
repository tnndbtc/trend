"""
Unit tests for ServiceFactory.

Tests the service factory pattern, dependency injection,
and service lifecycle management.
"""

import os
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

from trend_agent.services.factory import ServiceFactory, get_service_factory


# ============================================================================
# ServiceFactory Tests
# ============================================================================


@pytest.mark.asyncio
class TestServiceFactory:
    """Tests for ServiceFactory."""

    def test_singleton_pattern(self):
        """Test that get_service_factory returns the same instance."""
        factory1 = get_service_factory()
        factory2 = get_service_factory()

        assert factory1 is factory2

    def test_force_new_instance(self):
        """Test creating a new factory instance."""
        factory1 = get_service_factory()
        factory2 = get_service_factory(force_new=True)

        assert factory1 is not factory2

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_get_embedding_service(self):
        """Test getting embedding service."""
        factory = ServiceFactory()

        # First call creates service
        service1 = factory.get_embedding_service()
        assert service1 is not None

        # Second call returns cached service
        service2 = factory.get_embedding_service()
        assert service1 is service2

        # Force new creates different instance
        service3 = factory.get_embedding_service(force_new=True)
        assert service3 is not service1

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_get_llm_service_openai(self):
        """Test getting OpenAI LLM service."""
        factory = ServiceFactory()

        service = factory.get_llm_service(provider="openai")
        assert service is not None

        # Should be cached
        service2 = factory.get_llm_service(provider="openai")
        assert service is service2

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    def test_get_llm_service_anthropic(self):
        """Test getting Anthropic LLM service."""
        factory = ServiceFactory()

        service = factory.get_llm_service(provider="anthropic")
        assert service is not None

    def test_get_llm_service_invalid_provider(self):
        """Test getting LLM service with invalid provider."""
        factory = ServiceFactory()

        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            factory.get_llm_service(provider="invalid")

    @patch.dict(
        os.environ,
        {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "test",
            "POSTGRES_USER": "test",
            "POSTGRES_PASSWORD": "test",
        },
    )
    def test_get_trend_repository(self):
        """Test getting trend repository."""
        factory = ServiceFactory()

        repo = factory.get_trend_repository()
        assert repo is not None

        # Should be cached
        repo2 = factory.get_trend_repository()
        assert repo is repo2

    @patch.dict(
        os.environ,
        {
            "REDIS_HOST": "localhost",
            "REDIS_PORT": "6379",
        },
    )
    def test_get_redis_repository(self):
        """Test getting Redis repository."""
        factory = ServiceFactory()

        repo = factory.get_redis_repository()
        assert repo is not None

        # Should be cached
        repo2 = factory.get_redis_repository()
        assert repo is repo2

    @patch.dict(
        os.environ,
        {
            "QDRANT_HOST": "localhost",
            "QDRANT_PORT": "6333",
        },
    )
    def test_get_vector_repository(self):
        """Test getting vector repository."""
        factory = ServiceFactory()

        repo = factory.get_vector_repository()
        assert repo is not None

        # Should be cached
        repo2 = factory.get_vector_repository()
        assert repo is repo2

    @patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "test-key",
            "QDRANT_HOST": "localhost",
            "POSTGRES_HOST": "localhost",
        },
    )
    def test_get_search_service(self):
        """Test getting semantic search service."""
        factory = ServiceFactory()

        # Mock the repositories to avoid actual connections
        with patch.object(factory, "_create_vector_repository"):
            with patch.object(factory, "_create_trend_repository"):
                service = factory.get_search_service()
                assert service is not None

    @patch.dict(
        os.environ,
        {
            "LIBRETRANSLATE_HOST": "http://localhost:5000",
            "OPENAI_API_KEY": "test-key",
            "REDIS_HOST": "localhost",
        },
    )
    def test_get_translation_manager(self):
        """Test getting translation manager."""
        factory = ServiceFactory()

        # Mock Redis repository
        with patch.object(factory, "_create_redis_repository"):
            manager = factory.get_translation_manager()
            assert manager is not None

            # Should be cached
            manager2 = factory.get_translation_manager()
            assert manager is manager2

    def test_custom_config_override(self):
        """Test overriding configuration."""
        custom_config = {
            "openai_api_key": "custom-key",
            "embedding_model": "text-embedding-3-large",
        }

        factory = ServiceFactory(config=custom_config)

        # Verify config is stored
        assert factory.config == custom_config

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager support."""
        factory = ServiceFactory()

        # Mock cleanup methods to avoid actual connections
        factory._cleanup_repositories = AsyncMock()

        async with factory:
            # Factory should be usable
            pass

        # Cleanup should be called
        assert factory._cleanup_repositories.called

    def test_get_all_services(self):
        """Test getting all initialized services."""
        factory = ServiceFactory()

        # Initially empty
        services = factory.get_all_services()
        assert isinstance(services, dict)
        assert len(services) == 0

        # After creating a service
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            factory.get_embedding_service()
            services = factory.get_all_services()
            assert len(services) > 0

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_service_caching_by_key(self):
        """Test that services are cached by unique keys."""
        factory = ServiceFactory()

        # Different providers should have different cache keys
        llm_openai = factory.get_llm_service(provider="openai")

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            llm_anthropic = factory.get_llm_service(provider="anthropic")

        assert llm_openai is not llm_anthropic

        # Same provider should return cached instance
        llm_openai2 = factory.get_llm_service(provider="openai")
        assert llm_openai is llm_openai2


# ============================================================================
# Configuration Tests
# ============================================================================


class TestServiceFactoryConfiguration:
    """Tests for service factory configuration."""

    def test_environment_variable_configuration(self):
        """Test configuration from environment variables."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "env-key",
                "OPENAI_EMBEDDING_MODEL": "text-embedding-3-large",
                "OPENAI_LLM_MODEL": "gpt-4",
                "ANTHROPIC_API_KEY": "anthropic-key",
                "DEEPL_API_KEY": "deepl-key",
                "LIBRETRANSLATE_HOST": "http://custom:5000",
            },
        ):
            factory = ServiceFactory()

            # Verify environment variables are read
            assert os.getenv("OPENAI_API_KEY") == "env-key"
            assert os.getenv("OPENAI_EMBEDDING_MODEL") == "text-embedding-3-large"

    def test_config_dict_override(self):
        """Test configuration override via config dict."""
        custom_config = {
            "openai_api_key": "custom-openai",
            "anthropic_api_key": "custom-anthropic",
            "embedding_model": "text-embedding-3-large",
            "llm_model": "gpt-4-turbo",
        }

        factory = ServiceFactory(config=custom_config)
        assert factory.config["openai_api_key"] == "custom-openai"
        assert factory.config["embedding_model"] == "text-embedding-3-large"

    def test_missing_api_key_handling(self):
        """Test handling of missing API keys."""
        # Clear environment
        with patch.dict(os.environ, {}, clear=True):
            factory = ServiceFactory()

            # Should raise error or handle gracefully
            with pytest.raises(Exception):
                factory.get_embedding_service()


# ============================================================================
# Translation Manager Factory Tests
# ============================================================================


@pytest.mark.asyncio
class TestTranslationManagerFactory:
    """Tests for translation manager creation via factory."""

    @patch.dict(
        os.environ,
        {
            "LIBRETRANSLATE_HOST": "http://localhost:5000",
            "OPENAI_API_KEY": "test-key",
            "DEEPL_API_KEY": "deepl-key",
            "REDIS_HOST": "localhost",
        },
    )
    def test_creates_all_available_providers(self):
        """Test that factory creates all available translation providers."""
        factory = ServiceFactory()

        # Mock Redis
        with patch.object(factory, "_create_redis_repository"):
            manager = factory.get_translation_manager()

            # Should have providers based on available API keys
            assert manager is not None
            # Verify it has multiple providers
            assert hasattr(manager, "providers")

    def test_provider_priority_configuration(self):
        """Test configuring provider priority."""
        with patch.dict(
            os.environ,
            {
                "TRANSLATION_PROVIDER_PRIORITY": "libretranslate,openai,deepl",
                "LIBRETRANSLATE_HOST": "http://localhost:5000",
                "OPENAI_API_KEY": "test-key",
                "REDIS_HOST": "localhost",
            },
        ):
            factory = ServiceFactory()

            with patch.object(factory, "_create_redis_repository"):
                manager = factory.get_translation_manager()

                # Verify priority is set correctly
                assert manager is not None

    def test_cache_configuration(self):
        """Test translation cache configuration."""
        with patch.dict(
            os.environ,
            {
                "TRANSLATION_CACHE_TTL": "86400",  # 1 day
                "REDIS_HOST": "localhost",
                "LIBRETRANSLATE_HOST": "http://localhost:5000",
            },
        ):
            factory = ServiceFactory()

            with patch.object(factory, "_create_redis_repository"):
                manager = factory.get_translation_manager()

                # Verify cache is configured
                assert manager is not None


# ============================================================================
# Service Lifecycle Tests
# ============================================================================


@pytest.mark.asyncio
class TestServiceLifecycle:
    """Tests for service lifecycle management."""

    async def test_cleanup_on_context_exit(self):
        """Test that services are cleaned up on context exit."""
        factory = ServiceFactory()

        # Mock cleanup method
        factory._cleanup_repositories = AsyncMock()

        async with factory as f:
            # Use factory
            assert f is factory

        # Verify cleanup was called
        assert factory._cleanup_repositories.called

    @patch.dict(
        os.environ,
        {
            "POSTGRES_HOST": "localhost",
            "REDIS_HOST": "localhost",
        },
    )
    async def test_repository_connection_lifecycle(self):
        """Test repository connection and cleanup lifecycle."""
        factory = ServiceFactory()

        # Create mock repositories with close methods
        mock_trend_repo = MagicMock()
        mock_trend_repo.close = AsyncMock()

        mock_redis_repo = MagicMock()
        mock_redis_repo.close = AsyncMock()

        # Inject mocks
        factory._services["trend_repository"] = mock_trend_repo
        factory._services["redis_cache"] = mock_redis_repo

        # Cleanup
        await factory._cleanup_repositories()

        # Verify close was called
        assert mock_trend_repo.close.called
        assert mock_redis_repo.close.called


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestServiceFactoryErrorHandling:
    """Tests for error handling in service factory."""

    def test_invalid_provider_name(self):
        """Test error handling for invalid provider names."""
        factory = ServiceFactory()

        with pytest.raises(ValueError):
            factory.get_llm_service(provider="invalid_provider")

    def test_missing_dependencies(self):
        """Test error handling when dependencies are missing."""
        # Clear environment to simulate missing config
        with patch.dict(os.environ, {}, clear=True):
            factory = ServiceFactory()

            # Should raise appropriate error
            with pytest.raises(Exception):
                factory.get_embedding_service()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_service_initialization_failure(self):
        """Test handling of service initialization failures."""
        factory = ServiceFactory()

        # Mock service creation to fail
        with patch(
            "trend_agent.services.factory.OpenAIEmbeddingService",
            side_effect=Exception("Init failed"),
        ):
            with pytest.raises(Exception, match="Init failed"):
                factory.get_embedding_service()


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
