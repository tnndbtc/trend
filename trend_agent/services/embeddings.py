"""
OpenAI Embedding Service implementation.

Provides production-ready text embedding generation using OpenAI's
text-embedding-3-small or text-embedding-ada-002 models.
"""

import asyncio
import logging
import os
import time
from typing import List, Optional

import httpx

from trend_agent.intelligence.interfaces import BaseEmbeddingService, EmbeddingError
from trend_agent.observability.metrics import (
    api_request_counter,
    api_request_duration,
)

logger = logging.getLogger(__name__)


class OpenAIEmbeddingService(BaseEmbeddingService):
    """
    OpenAI embedding service for text vectorization.

    Uses OpenAI's embedding models to generate high-quality text embeddings
    for semantic search, clustering, and similarity comparison.

    Features:
    - Automatic batch processing for efficiency
    - Retry logic with exponential backoff
    - Rate limiting and cost tracking
    - Prometheus metrics integration
    - Async/await support

    Example:
        ```python
        service = OpenAIEmbeddingService(api_key="sk-...")

        # Single embedding
        embedding = await service.embed("Machine learning is fascinating")

        # Batch embeddings
        texts = ["AI trends", "Cloud computing", "Quantum computing"]
        embeddings = await service.embed_batch(texts)
        ```
    """

    # Model configurations
    MODELS = {
        "text-embedding-3-small": {
            "dimension": 1536,
            "max_tokens": 8192,
            "cost_per_1k_tokens": 0.00002,
        },
        "text-embedding-3-large": {
            "dimension": 3072,
            "max_tokens": 8192,
            "cost_per_1k_tokens": 0.00013,
        },
        "text-embedding-ada-002": {
            "dimension": 1536,
            "max_tokens": 8192,
            "cost_per_1k_tokens": 0.0001,
        },
    }

    DEFAULT_MODEL = "text-embedding-3-small"
    API_ENDPOINT = "https://api.openai.com/v1/embeddings"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_retries: int = 3,
        timeout: int = 30,
        max_batch_size: int = 100,
    ):
        """
        Initialize OpenAI embedding service.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model name to use
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
            max_batch_size: Maximum texts per batch request

        Raises:
            ValueError: If API key is not provided
            ValueError: If model is not supported
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        if model not in self.MODELS:
            raise ValueError(
                f"Model '{model}' not supported. "
                f"Available models: {list(self.MODELS.keys())}"
            )

        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        self.max_batch_size = max_batch_size

        self._model_config = self.MODELS[model]
        self._total_cost = 0.0
        self._total_tokens = 0

        # Initialize HTTP client
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        logger.info(
            f"Initialized OpenAIEmbeddingService "
            f"(model={model}, dimension={self.get_dimension()})"
        )

    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not text or not text.strip():
            raise EmbeddingError("Text cannot be empty")

        embeddings = await self.embed_batch([text])
        return embeddings[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with batching.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not texts:
            return []

        # Filter out empty texts
        valid_texts = [t.strip() for t in texts if t and t.strip()]
        if not valid_texts:
            raise EmbeddingError("All texts are empty")

        # Split into batches if needed
        if len(valid_texts) <= self.max_batch_size:
            return await self._generate_embeddings(valid_texts)

        # Process in batches
        all_embeddings = []
        for i in range(0, len(valid_texts), self.max_batch_size):
            batch = valid_texts[i : i + self.max_batch_size]
            batch_embeddings = await self._generate_embeddings(batch)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Internal method to call OpenAI API with retry logic.

        Args:
            texts: Batch of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If all retries fail
        """
        start_time = time.time()
        last_error = None

        for attempt in range(self.max_retries):
            try:
                # Prepare request
                payload = {
                    "model": self.model,
                    "input": texts,
                    "encoding_format": "float",
                }

                # Make API call
                response = await self._client.post(self.API_ENDPOINT, json=payload)
                response.raise_for_status()

                # Parse response
                data = response.json()
                embeddings = [item["embedding"] for item in data["data"]]

                # Track usage
                usage = data.get("usage", {})
                tokens_used = usage.get("total_tokens", 0)
                cost = self._calculate_cost(tokens_used)

                self._total_tokens += tokens_used
                self._total_cost += cost

                # Record metrics
                duration = time.time() - start_time
                api_request_duration.labels(
                    method="POST", endpoint="openai_embeddings"
                ).observe(duration)
                api_request_counter.labels(
                    method="POST",
                    endpoint="openai_embeddings",
                    status_code=response.status_code,
                ).inc()

                logger.debug(
                    f"Generated {len(embeddings)} embeddings "
                    f"({tokens_used} tokens, ${cost:.6f}, {duration:.2f}s)"
                )

                return embeddings

            except httpx.HTTPStatusError as e:
                last_error = e
                status = e.response.status_code

                # Don't retry client errors (except rate limits)
                if 400 <= status < 500 and status != 429:
                    raise EmbeddingError(f"OpenAI API error: {e.response.text}") from e

                # Log and retry
                logger.warning(
                    f"OpenAI API error (attempt {attempt + 1}/{self.max_retries}): "
                    f"{status} - {e.response.text}"
                )

                # Exponential backoff
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Unexpected error (attempt {attempt + 1}/{self.max_retries}): {e}"
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        # All retries failed
        duration = time.time() - start_time
        api_request_duration.labels(
            method="POST", endpoint="openai_embeddings"
        ).observe(duration)
        api_request_counter.labels(
            method="POST", endpoint="openai_embeddings", status_code=500
        ).inc()

        raise EmbeddingError(
            f"Failed to generate embeddings after {self.max_retries} attempts"
        ) from last_error

    def _calculate_cost(self, tokens: int) -> float:
        """Calculate API cost for token usage."""
        cost_per_token = self._model_config["cost_per_1k_tokens"] / 1000
        return tokens * cost_per_token

    def get_dimension(self) -> int:
        """Get embedding vector dimension."""
        return self._model_config["dimension"]

    def get_model_name(self) -> str:
        """Get the name of the embedding model."""
        return self.model

    def get_usage_stats(self) -> dict:
        """
        Get usage statistics.

        Returns:
            Dictionary with total tokens used and estimated cost
        """
        return {
            "total_tokens": self._total_tokens,
            "total_cost_usd": self._total_cost,
            "model": self.model,
            "dimension": self.get_dimension(),
        }

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
        logger.info(
            f"Closed OpenAIEmbeddingService "
            f"(total_tokens={self._total_tokens}, total_cost=${self._total_cost:.6f})"
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
