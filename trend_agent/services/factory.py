"""
Service Factory for AI Services.

Provides centralized instantiation, configuration, and lifecycle management
for all AI services in the Trend Intelligence Platform.
"""

import logging
import os
from typing import Dict, Optional

from trend_agent.services.embeddings import OpenAIEmbeddingService
from trend_agent.services.llm import AnthropicLLMService, OpenAILLMService
from trend_agent.services.search import QdrantSemanticSearchService
from trend_agent.services.translation import (
    DeepLTranslationService,
    LibreTranslateService,
    OpenAITranslationService,
)
from trend_agent.services.translation_manager import (
    TranslationCache,
    TranslationManager,
)
from trend_agent.storage.postgres import PostgreSQLTrendRepository
from trend_agent.storage.qdrant import QdrantVectorRepository
from trend_agent.storage.redis import RedisCacheRepository

logger = logging.getLogger(__name__)


class ServiceFactory:
    """
    Factory for creating and managing AI service instances.

    Provides centralized service instantiation with:
    - Environment-based configuration
    - Singleton pattern for service reuse
    - Automatic dependency injection
    - Service lifecycle management
    - Easy testing/mocking support

    Services are lazily initialized on first access and cached for reuse.
    All services can be properly cleaned up via the close() method.

    Example:
        ```python
        # Production usage
        factory = ServiceFactory()
        embedding_service = factory.get_embedding_service()
        llm_service = factory.get_llm_service(provider="openai")
        search_service = factory.get_search_service()

        # Use services...
        embedding = await embedding_service.embed("AI trends")

        # Cleanup when done
        await factory.close()

        # Or use as context manager
        async with ServiceFactory() as factory:
            llm = factory.get_llm_service()
            result = await llm.generate("Explain quantum computing")
        ```

    Environment Variables:
        # OpenAI
        OPENAI_API_KEY: OpenAI API key (required for OpenAI services)
        OPENAI_EMBEDDING_MODEL: Embedding model (default: text-embedding-3-small)
        OPENAI_LLM_MODEL: LLM model (default: gpt-4-turbo)

        # Anthropic
        ANTHROPIC_API_KEY: Anthropic API key (required for Claude)
        ANTHROPIC_MODEL: Model name (default: claude-3-sonnet)

        # Qdrant
        QDRANT_HOST: Qdrant host (default: localhost)
        QDRANT_PORT: Qdrant port (default: 6333)
        QDRANT_COLLECTION: Collection name (default: trend_embeddings)
        QDRANT_API_KEY: Optional API key for Qdrant Cloud

        # PostgreSQL
        POSTGRES_HOST: PostgreSQL host (default: localhost)
        POSTGRES_PORT: PostgreSQL port (default: 5432)
        POSTGRES_DB: Database name (default: trends)
        POSTGRES_USER: Database user (required)
        POSTGRES_PASSWORD: Database password (required)
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize service factory.

        Args:
            config: Optional configuration overrides (for testing)
        """
        self.config = config or {}
        self._services: Dict[str, any] = {}
        self._initialized = False

        logger.info("ServiceFactory initialized")

    # ========================================================================
    # Embedding Services
    # ========================================================================

    def get_embedding_service(
        self, provider: str = "openai", force_new: bool = False
    ):
        """
        Get embedding service instance.

        Args:
            provider: Provider name ("openai")
            force_new: Force creation of new instance (default: False)

        Returns:
            EmbeddingService instance

        Raises:
            ValueError: If provider is not supported or configuration is invalid
        """
        cache_key = f"embedding_{provider}"

        # Return cached instance unless force_new is True
        if not force_new and cache_key in self._services:
            return self._services[cache_key]

        # Create new instance based on provider
        if provider == "openai":
            service = self._create_openai_embedding_service()
        else:
            raise ValueError(
                f"Unsupported embedding provider: {provider}. "
                f"Available: openai"
            )

        # Cache the service
        self._services[cache_key] = service
        logger.info(f"Created {provider} embedding service")

        return service

    def _create_openai_embedding_service(self) -> OpenAIEmbeddingService:
        """Create OpenAI embedding service with configuration."""
        api_key = self.config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
        model = self.config.get("openai_embedding_model") or os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        )
        max_retries = self.config.get("openai_max_retries", 3)
        timeout = self.config.get("openai_timeout", 30)
        max_batch_size = self.config.get("openai_embedding_batch_size", 100)

        return OpenAIEmbeddingService(
            api_key=api_key,
            model=model,
            max_retries=max_retries,
            timeout=timeout,
            max_batch_size=max_batch_size,
        )

    # ========================================================================
    # LLM Services
    # ========================================================================

    def get_llm_service(self, provider: str = "openai", force_new: bool = False):
        """
        Get LLM service instance.

        Args:
            provider: Provider name ("openai", "anthropic")
            force_new: Force creation of new instance (default: False)

        Returns:
            LLMService instance

        Raises:
            ValueError: If provider is not supported or configuration is invalid
        """
        cache_key = f"llm_{provider}"

        # Return cached instance unless force_new is True
        if not force_new and cache_key in self._services:
            return self._services[cache_key]

        # Create new instance based on provider
        if provider == "openai":
            service = self._create_openai_llm_service()
        elif provider == "anthropic":
            service = self._create_anthropic_llm_service()
        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider}. "
                f"Available: openai, anthropic"
            )

        # Cache the service
        self._services[cache_key] = service
        logger.info(f"Created {provider} LLM service")

        return service

    def _create_openai_llm_service(self) -> OpenAILLMService:
        """Create OpenAI LLM service with configuration."""
        api_key = self.config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
        model = self.config.get("openai_llm_model") or os.getenv(
            "OPENAI_LLM_MODEL", "gpt-4-turbo"
        )
        max_retries = self.config.get("openai_max_retries", 3)
        timeout = self.config.get("openai_timeout", 60)

        return OpenAILLMService(
            api_key=api_key,
            model=model,
            max_retries=max_retries,
            timeout=timeout,
        )

    def _create_anthropic_llm_service(self) -> AnthropicLLMService:
        """Create Anthropic LLM service with configuration."""
        api_key = self.config.get("anthropic_api_key") or os.getenv(
            "ANTHROPIC_API_KEY"
        )
        model = self.config.get("anthropic_model") or os.getenv(
            "ANTHROPIC_MODEL", "claude-3-sonnet"
        )
        max_retries = self.config.get("anthropic_max_retries", 3)
        timeout = self.config.get("anthropic_timeout", 60)

        return AnthropicLLMService(
            api_key=api_key,
            model=model,
            max_retries=max_retries,
            timeout=timeout,
        )

    # ========================================================================
    # Search Services
    # ========================================================================

    def get_search_service(self, force_new: bool = False) -> QdrantSemanticSearchService:
        """
        Get semantic search service instance.

        The search service depends on embedding service, vector repository,
        and trend repository, which are automatically instantiated.

        Args:
            force_new: Force creation of new instance (default: False)

        Returns:
            QdrantSemanticSearchService instance

        Raises:
            ValueError: If configuration is invalid
        """
        cache_key = "search_qdrant"

        # Return cached instance unless force_new is True
        if not force_new and cache_key in self._services:
            return self._services[cache_key]

        # Get dependencies
        embedding_service = self.get_embedding_service()
        vector_repository = self.get_vector_repository()
        trend_repository = self.get_trend_repository()

        # Create search service
        default_limit = self.config.get("search_default_limit", 20)
        default_min_similarity = self.config.get("search_min_similarity", 0.7)

        service = QdrantSemanticSearchService(
            embedding_service=embedding_service,
            vector_repository=vector_repository,
            trend_repository=trend_repository,
            default_limit=default_limit,
            default_min_similarity=default_min_similarity,
        )

        # Cache the service
        self._services[cache_key] = service
        logger.info("Created Qdrant semantic search service")

        return service

    # ========================================================================
    # Translation Services
    # ========================================================================

    def get_translation_manager(self, force_new: bool = False) -> TranslationManager:
        """
        Get translation manager with multiple providers and caching.

        The translation manager automatically selects the best provider
        and uses Redis caching to minimize costs.

        Args:
            force_new: Force creation of new instance (default: False)

        Returns:
            TranslationManager instance
        """
        cache_key = "translation_manager"

        if not force_new and cache_key in self._services:
            return self._services[cache_key]

        # Get providers based on configuration
        providers = {}

        # LibreTranslate (free, always include if available)
        try:
            providers["libretranslate"] = self._create_libretranslate_service()
        except Exception as e:
            logger.warning(f"LibreTranslate not available: {e}")

        # OpenAI (paid, high quality)
        try:
            providers["openai"] = self._create_openai_translation_service()
        except Exception as e:
            logger.warning(f"OpenAI translation not available: {e}")

        # DeepL (paid, highest quality)
        try:
            providers["deepl"] = self._create_deepl_service()
        except Exception as e:
            logger.warning(f"DeepL not available: {e}")

        if not providers:
            raise ValueError("No translation providers available")

        # Create translation cache
        cache = None
        try:
            redis_repo = self.get_redis_repository()
            cache_ttl = self.config.get("translation_cache_ttl", 604800)  # 7 days
            cache = TranslationCache(redis_repo, ttl_seconds=cache_ttl)
        except Exception as e:
            logger.warning(f"Translation cache not available: {e}")

        # Provider priority
        priority_config = (
            self.config.get("translation_provider_priority")
            or os.getenv("TRANSLATION_PROVIDER_PRIORITY")
            or "libretranslate,openai,deepl"  # Default priority (FREE first!)
        )

        # Handle both list and comma-separated string
        if isinstance(priority_config, str):
            priority = [p.strip() for p in priority_config.split(",")]
        else:
            priority = priority_config

        # Filter to only available providers
        priority = [p for p in priority if p in providers]

        logger.info(f"Translation provider priority: {', '.join(priority)}")

        # Create manager
        manager = TranslationManager(
            providers=providers,
            cache=cache,
            provider_priority=priority,
            enable_fallback=True,
        )

        self._services[cache_key] = manager
        logger.info(f"Created TranslationManager with {len(providers)} providers")

        return manager

    def _create_openai_translation_service(self) -> OpenAITranslationService:
        """Create OpenAI translation service."""
        api_key = self.config.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
        model = self.config.get("openai_translation_model") or os.getenv(
            "OPENAI_TRANSLATION_MODEL", "gpt-4-turbo"
        )
        max_retries = self.config.get("openai_max_retries", 3)
        timeout = self.config.get("openai_timeout", 30)

        return OpenAITranslationService(
            api_key=api_key,
            model=model,
            max_retries=max_retries,
            timeout=timeout,
        )

    def _create_libretranslate_service(self) -> LibreTranslateService:
        """Create LibreTranslate service."""
        host = self.config.get("libretranslate_host") or os.getenv(
            "LIBRETRANSLATE_HOST", "http://localhost:5000"
        )
        api_key = self.config.get("libretranslate_api_key") or os.getenv(
            "LIBRETRANSLATE_API_KEY"
        )
        timeout = self.config.get("libretranslate_timeout", 30)

        return LibreTranslateService(
            host=host,
            api_key=api_key,
            timeout=timeout,
        )

    def _create_deepl_service(self) -> DeepLTranslationService:
        """Create DeepL translation service."""
        api_key = self.config.get("deepl_api_key") or os.getenv("DEEPL_API_KEY")
        is_pro = self.config.get("deepl_is_pro", False)
        timeout = self.config.get("deepl_timeout", 30)

        return DeepLTranslationService(
            api_key=api_key,
            is_pro=is_pro,
            timeout=timeout,
        )

    # ========================================================================
    # Storage Repositories
    # ========================================================================

    def get_vector_repository(self, force_new: bool = False) -> QdrantVectorRepository:
        """
        Get Qdrant vector repository instance.

        Args:
            force_new: Force creation of new instance (default: False)

        Returns:
            QdrantVectorRepository instance
        """
        cache_key = "vector_repo_qdrant"

        if not force_new and cache_key in self._services:
            return self._services[cache_key]

        # Get configuration
        host = self.config.get("qdrant_host") or os.getenv("QDRANT_HOST", "localhost")
        port = int(self.config.get("qdrant_port") or os.getenv("QDRANT_PORT", 6333))
        collection_name = self.config.get("qdrant_collection") or os.getenv(
            "QDRANT_COLLECTION", "trend_embeddings"
        )
        vector_size = int(
            self.config.get("qdrant_vector_size")
            or os.getenv("QDRANT_VECTOR_SIZE", 1536)
        )
        distance_metric = self.config.get("qdrant_distance") or os.getenv(
            "QDRANT_DISTANCE", "Cosine"
        )
        api_key = self.config.get("qdrant_api_key") or os.getenv("QDRANT_API_KEY")
        timeout = int(
            self.config.get("qdrant_timeout") or os.getenv("QDRANT_TIMEOUT", 30)
        )

        # Create repository
        repo = QdrantVectorRepository(
            host=host,
            port=port,
            collection_name=collection_name,
            vector_size=vector_size,
            distance_metric=distance_metric,
            api_key=api_key,
            timeout=timeout,
        )

        self._services[cache_key] = repo
        logger.info(f"Created Qdrant vector repository (host={host}:{port})")

        return repo

    def get_trend_repository(self, force_new: bool = False) -> PostgreSQLTrendRepository:
        """
        Get PostgreSQL trend repository instance.

        Args:
            force_new: Force creation of new instance (default: False)

        Returns:
            PostgreSQLTrendRepository instance
        """
        cache_key = "trend_repo_postgres"

        if not force_new and cache_key in self._services:
            return self._services[cache_key]

        # Build database URL
        db_url = self._get_database_url()

        # Create repository
        repo = PostgreSQLTrendRepository(db_url=db_url)

        self._services[cache_key] = repo
        logger.info("Created PostgreSQL trend repository")

        return repo

    def _get_database_url(self) -> str:
        """Build PostgreSQL database URL from configuration."""
        # Check for full URL first
        db_url = self.config.get("database_url") or os.getenv("DATABASE_URL")
        if db_url:
            return db_url

        # Build from components
        host = self.config.get("postgres_host") or os.getenv("POSTGRES_HOST", "localhost")
        port = self.config.get("postgres_port") or os.getenv("POSTGRES_PORT", "5432")
        database = self.config.get("postgres_db") or os.getenv("POSTGRES_DB", "trends")
        user = self.config.get("postgres_user") or os.getenv("POSTGRES_USER", "postgres")
        password = self.config.get("postgres_password") or os.getenv(
            "POSTGRES_PASSWORD", ""
        )

        return f"postgresql://{user}:{password}@{host}:{port}/{database}"

    def get_redis_repository(self, force_new: bool = False) -> RedisCacheRepository:
        """
        Get Redis cache repository instance.

        Args:
            force_new: Force creation of new instance (default: False)

        Returns:
            RedisCacheRepository instance
        """
        cache_key = "redis_repo"

        if not force_new and cache_key in self._services:
            return self._services[cache_key]

        # Get configuration
        host = self.config.get("redis_host") or os.getenv("REDIS_HOST", "localhost")
        port = int(self.config.get("redis_port") or os.getenv("REDIS_PORT", 6379))
        password = self.config.get("redis_password") or os.getenv("REDIS_PASSWORD")
        db = int(self.config.get("redis_db") or os.getenv("REDIS_DB", 0))

        # Create repository
        repo = RedisCacheRepository(
            host=host,
            port=port,
            password=password,
            db=db,
        )

        # Note: Redis repo needs async connect() call
        # This will be done by the caller

        self._services[cache_key] = repo
        logger.info(f"Created Redis cache repository (host={host}:{port})")

        return repo

    # ========================================================================
    # Lifecycle Management
    # ========================================================================

    async def close(self):
        """
        Close all cached service instances.

        Properly cleans up resources for all services that have been created.
        Safe to call multiple times.
        """
        logger.info(f"Closing ServiceFactory (active services: {len(self._services)})")

        for key, service in self._services.items():
            try:
                # Check if service has a close method
                if hasattr(service, "close"):
                    if hasattr(service.close, "__await__"):
                        # Async close
                        await service.close()
                    else:
                        # Sync close
                        service.close()
                    logger.debug(f"Closed service: {key}")
            except Exception as e:
                logger.error(f"Error closing service {key}: {e}")

        self._services.clear()
        logger.info("ServiceFactory closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def get_status(self) -> Dict:
        """
        Get factory status and active services.

        Returns:
            Dictionary with factory status information
        """
        return {
            "active_services": list(self._services.keys()),
            "service_count": len(self._services),
            "services": {
                key: {
                    "type": type(service).__name__,
                    "has_close": hasattr(service, "close"),
                }
                for key, service in self._services.items()
            },
        }


# ============================================================================
# Singleton Factory Instance
# ============================================================================

_global_factory: Optional[ServiceFactory] = None


def get_service_factory(config: Optional[Dict] = None) -> ServiceFactory:
    """
    Get or create the global service factory instance.

    This function provides a singleton ServiceFactory for use throughout
    the application. All services are cached and reused.

    Args:
        config: Optional configuration overrides (only used on first call)

    Returns:
        Global ServiceFactory instance

    Example:
        ```python
        # Get factory
        factory = get_service_factory()

        # Use services
        embedding_service = factory.get_embedding_service()
        llm_service = factory.get_llm_service(provider="anthropic")

        # Cleanup (usually done at application shutdown)
        await factory.close()
        ```

    Note:
        For testing, create a new ServiceFactory instance directly
        instead of using this global function.
    """
    global _global_factory

    if _global_factory is None:
        _global_factory = ServiceFactory(config=config)
        logger.info("Created global ServiceFactory instance")

    return _global_factory


async def close_global_factory():
    """
    Close the global service factory.

    Should be called during application shutdown to properly clean up
    all service resources.
    """
    global _global_factory

    if _global_factory is not None:
        await _global_factory.close()
        _global_factory = None
        logger.info("Closed global ServiceFactory")
