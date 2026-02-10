"""
Qdrant vector database repository implementation.

This module provides a Qdrant-based implementation of the VectorRepository
interface for storing and searching vector embeddings.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from trend_agent.storage.interfaces import (
    BaseVectorRepository,
    ConnectionError,
    StorageError,
)
from trend_agent.types import VectorMatch

logger = logging.getLogger(__name__)


class QdrantVectorRepository(BaseVectorRepository):
    """
    Qdrant implementation of VectorRepository.

    This implementation uses Qdrant vector database for efficient similarity
    search on high-dimensional embeddings.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "trend_embeddings",
        vector_size: int = 1536,
        distance_metric: str = "Cosine",
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize Qdrant vector repository.

        Args:
            host: Qdrant server host
            port: Qdrant server port
            collection_name: Name of the collection to use
            vector_size: Dimension of embedding vectors
            distance_metric: Distance metric (Cosine, Euclid, Dot)
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.distance_metric = distance_metric
        self.timeout = timeout

        try:
            # Initialize Qdrant client
            if api_key:
                self.client = QdrantClient(
                    host=host,
                    port=port,
                    api_key=api_key,
                    timeout=timeout,
                )
            else:
                self.client = QdrantClient(
                    host=host,
                    port=port,
                    timeout=timeout,
                )

            logger.info(f"Connected to Qdrant at {host}:{port}")

        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise ConnectionError(f"Qdrant connection failed: {e}")

    async def _ensure_collection_exists(self):
        """
        Ensure the collection exists, create it if it doesn't.

        This is called automatically by operations that need the collection.
        """
        try:
            collections = self.client.get_collections().collections
            collection_exists = any(
                c.name == self.collection_name for c in collections
            )

            if not collection_exists:
                # Map distance metric string to Qdrant Distance enum
                distance_map = {
                    "Cosine": Distance.COSINE,
                    "Euclid": Distance.EUCLID,
                    "Dot": Distance.DOT,
                }
                distance = distance_map.get(self.distance_metric, Distance.COSINE)

                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=distance,
                    ),
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")

        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}")
            raise StorageError(f"Collection initialization failed: {e}")

    async def upsert(
        self,
        id: str,
        vector: List[float],
        metadata: Dict[str, Any],
    ) -> bool:
        """
        Insert or update a vector embedding.

        Args:
            id: Unique identifier for the vector
            vector: The embedding vector
            metadata: Associated metadata

        Returns:
            True if successful

        Raises:
            StorageError: If upsert operation fails
        """
        try:
            # Ensure collection exists before upserting
            await self._ensure_collection_exists()

            # Validate vector dimension
            if len(vector) != self.vector_size:
                raise ValueError(
                    f"Vector dimension {len(vector)} does not match expected {self.vector_size}"
                )

            # Create point with ID, vector, and payload (metadata)
            point = PointStruct(
                id=id,
                vector=vector,
                payload=metadata,
            )

            # Upsert the point
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point],
            )

            logger.debug(f"Upserted vector {id} to Qdrant")
            return True

        except ValueError as e:
            logger.error(f"Invalid vector dimension: {e}")
            raise StorageError(f"Invalid vector: {e}")
        except Exception as e:
            logger.error(f"Failed to upsert vector {id}: {e}")
            raise StorageError(f"Vector upsert failed: {e}")

    async def upsert_batch(
        self,
        vectors: List[tuple[str, List[float], Dict[str, Any]]],
    ) -> bool:
        """
        Insert or update multiple vectors in a batch.

        Args:
            vectors: List of (id, vector, metadata) tuples

        Returns:
            True if successful

        Raises:
            StorageError: If batch upsert fails
        """
        try:
            # Ensure collection exists before upserting
            await self._ensure_collection_exists()

            # Create points for batch upload
            points = []
            for vec_id, vector, metadata in vectors:
                # Validate vector dimension
                if len(vector) != self.vector_size:
                    logger.warning(
                        f"Skipping vector {vec_id}: dimension {len(vector)} does not match {self.vector_size}"
                    )
                    continue

                point = PointStruct(
                    id=vec_id,
                    vector=vector,
                    payload=metadata,
                )
                points.append(point)

            if not points:
                logger.warning("No valid vectors to upsert in batch")
                return False

            # Batch upsert - Qdrant handles this efficiently
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )

            logger.info(f"Batch upserted {len(points)} vectors to Qdrant")
            return True

        except Exception as e:
            logger.error(f"Failed to batch upsert vectors: {e}")
            raise StorageError(f"Batch vector upsert failed: {e}")

    async def search(
        self,
        vector: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        min_score: float = 0.0,
    ) -> List[VectorMatch]:
        """
        Search for similar vectors.

        Args:
            vector: Query vector
            limit: Maximum results to return
            filters: Optional metadata filters
            min_score: Minimum similarity score

        Returns:
            List of matching vectors with scores

        Raises:
            StorageError: If search fails
        """
        try:
            # Ensure collection exists before searching
            await self._ensure_collection_exists()

            # Validate vector dimension
            if len(vector) != self.vector_size:
                raise ValueError(
                    f"Query vector dimension {len(vector)} does not match expected {self.vector_size}"
                )

            # Build filter conditions if provided
            query_filter = None
            if filters:
                # Convert dict filters to Qdrant Filter
                conditions = []
                for key, value in filters.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value),
                        )
                    )

                if conditions:
                    query_filter = Filter(must=conditions)

            # Execute search
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=limit,
                query_filter=query_filter,
                score_threshold=min_score,
            )

            # Convert results to VectorMatch objects
            matches = []
            for hit in search_result:
                match = VectorMatch(
                    id=str(hit.id),
                    score=hit.score,
                    metadata=hit.payload or {},
                )
                matches.append(match)

            logger.debug(
                f"Vector search returned {len(matches)} results (limit={limit}, min_score={min_score})"
            )
            return matches

        except ValueError as e:
            logger.error(f"Invalid query vector: {e}")
            raise StorageError(f"Invalid query vector: {e}")
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise StorageError(f"Vector search failed: {e}")

    async def get(self, id: str) -> Optional[tuple[List[float], Dict[str, Any]]]:
        """
        Get a vector by ID.

        Args:
            id: Vector identifier

        Returns:
            Tuple of (vector, metadata) if found, None otherwise

        Raises:
            StorageError: If retrieval fails
        """
        try:
            # Ensure collection exists
            await self._ensure_collection_exists()

            # Retrieve the point by ID
            points = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[id],
                with_vectors=True,
                with_payload=True,
            )

            if not points:
                return None

            point = points[0]
            vector = point.vector
            metadata = point.payload or {}

            return (vector, metadata)

        except UnexpectedResponse as e:
            if "not found" in str(e).lower():
                return None
            logger.error(f"Failed to get vector {id}: {e}")
            raise StorageError(f"Vector retrieval failed: {e}")
        except Exception as e:
            logger.error(f"Failed to get vector {id}: {e}")
            raise StorageError(f"Vector retrieval failed: {e}")

    async def delete(self, id: str) -> bool:
        """
        Delete a vector by ID.

        Args:
            id: Vector identifier

        Returns:
            True if deleted, False if not found

        Raises:
            StorageError: If deletion fails
        """
        try:
            # Ensure collection exists
            await self._ensure_collection_exists()

            # Delete the point
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(
                    points=[id],
                ),
            )

            logger.debug(f"Deleted vector {id} from Qdrant")
            return True

        except Exception as e:
            logger.error(f"Failed to delete vector {id}: {e}")
            raise StorageError(f"Vector deletion failed: {e}")

    async def count(self) -> int:
        """
        Get total number of vectors in the collection.

        Returns:
            Number of vectors

        Raises:
            StorageError: If count fails
        """
        try:
            # Ensure collection exists
            await self._ensure_collection_exists()

            # Get collection info
            collection_info = self.client.get_collection(
                collection_name=self.collection_name
            )

            count = collection_info.points_count
            logger.debug(f"Qdrant collection {self.collection_name} has {count} vectors")

            return count

        except Exception as e:
            logger.error(f"Failed to count vectors: {e}")
            raise StorageError(f"Vector count failed: {e}")

    async def delete_collection(self) -> bool:
        """
        Delete the entire collection.

        This is a destructive operation useful for testing or cleanup.

        Returns:
            True if successful

        Raises:
            StorageError: If deletion fails
        """
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            logger.info(f"Deleted Qdrant collection: {self.collection_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise StorageError(f"Collection deletion failed: {e}")

    async def create_payload_index(self, field_name: str, field_type: str = "keyword"):
        """
        Create an index on a payload field for faster filtering.

        Args:
            field_name: Name of the payload field
            field_type: Type of index (keyword, integer, float, geo, text)

        Raises:
            StorageError: If index creation fails
        """
        try:
            # Ensure collection exists
            await self._ensure_collection_exists()

            # Map field type string to Qdrant schema
            schema_map = {
                "keyword": models.PayloadSchemaType.KEYWORD,
                "integer": models.PayloadSchemaType.INTEGER,
                "float": models.PayloadSchemaType.FLOAT,
                "geo": models.PayloadSchemaType.GEO,
                "text": models.PayloadSchemaType.TEXT,
            }

            schema_type = schema_map.get(field_type, models.PayloadSchemaType.KEYWORD)

            # Create index
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field_name,
                field_schema=schema_type,
            )

            logger.info(
                f"Created payload index on '{field_name}' with type '{field_type}'"
            )

        except Exception as e:
            logger.error(f"Failed to create payload index: {e}")
            raise StorageError(f"Payload index creation failed: {e}")

    async def scroll_all(
        self,
        batch_size: int = 100,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[tuple[str, List[float], Dict[str, Any]]]:
        """
        Scroll through all vectors in the collection.

        Useful for batch processing or migration.

        Args:
            batch_size: Number of vectors to fetch per batch
            filters: Optional metadata filters

        Returns:
            List of (id, vector, metadata) tuples

        Raises:
            StorageError: If scroll fails
        """
        try:
            # Ensure collection exists
            await self._ensure_collection_exists()

            # Build filter if provided
            query_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value),
                        )
                    )
                if conditions:
                    query_filter = Filter(must=conditions)

            # Scroll through all points
            all_vectors = []
            offset = None

            while True:
                result, offset = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=batch_size,
                    offset=offset,
                    with_vectors=True,
                    with_payload=True,
                    scroll_filter=query_filter,
                )

                for point in result:
                    all_vectors.append((str(point.id), point.vector, point.payload or {}))

                # Break if no more results
                if offset is None:
                    break

            logger.info(f"Scrolled {len(all_vectors)} vectors from Qdrant")
            return all_vectors

        except Exception as e:
            logger.error(f"Failed to scroll vectors: {e}")
            raise StorageError(f"Vector scroll failed: {e}")
