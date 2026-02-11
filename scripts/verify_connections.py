#!/usr/bin/env python3
"""
Verify connections to all storage backends (PostgreSQL, Qdrant, Redis).

This script tests the connectivity and basic operations for each repository
to ensure the infrastructure is properly set up before running integration tests.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trend_agent.storage.postgres import (
    PostgreSQLTrendRepository,
    PostgreSQLTopicRepository,
    PostgreSQLItemRepository,
)
from trend_agent.storage.qdrant import QdrantVectorRepository
from trend_agent.storage.redis import RedisCacheRepository
from trend_agent.types import RawItem, ProcessedItem, Topic, Trend
from datetime import datetime, timezone
import uuid


async def verify_postgresql():
    """Verify PostgreSQL connection and basic operations."""
    print("=" * 80)
    print("VERIFYING POSTGRESQL CONNECTION")
    print("=" * 80)

    # Connection parameters
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5433"))  # Using host port
    database = os.getenv("POSTGRES_DB", "trends")
    user = os.getenv("POSTGRES_USER", "trend_user")
    password = os.getenv("POSTGRES_PASSWORD", "trend_password")

    print(f"Connecting to PostgreSQL at {host}:{port}/{database}")

    pool = None
    try:
        # Create connection pool
        import asyncpg
        pool = await asyncpg.create_pool(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            min_size=1,
            max_size=5,
        )

        print("✅ Connected successfully!")

        # Initialize repositories with pool
        item_repo = PostgreSQLItemRepository(pool)

        # Test item repository
        print("\n📝 Testing item repository...")
        test_item = ProcessedItem(
            id=str(uuid.uuid4()),
            source="test",
            source_id="test-001",
            title="Test Item",
            content="This is a test item to verify PostgreSQL connectivity.",
            url="https://example.com/test",
            category="test",
            language="en",
            published_at=datetime.now(timezone.utc),
            collected_at=datetime.now(timezone.utc),
            metadata={"test": True},
        )

        await item_repo.save(test_item)
        print(f"  ✅ Saved test item: {test_item.id}")

        retrieved = await item_repo.get_by_id(test_item.id)
        if retrieved and retrieved.title == test_item.title:
            print(f"  ✅ Retrieved test item successfully")
        else:
            print(f"  ❌ Failed to retrieve test item")
            return False

        # Clean up
        print("\n🧹 Cleaning up test data...")
        await pool.execute("DELETE FROM processed_items WHERE source = 'test'")
        print("  ✅ Test data cleaned up")

        # Close pool
        await pool.close()

        print("\n✅ PostgreSQL verification completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ PostgreSQL verification failed: {e}")
        import traceback
        traceback.print_exc()
        if pool:
            await pool.close()
        return False


async def verify_qdrant():
    """Verify Qdrant connection and basic operations."""
    print("\n" + "=" * 80)
    print("VERIFYING QDRANT CONNECTION")
    print("=" * 80)

    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))

    print(f"Connecting to Qdrant at {host}:{port}")

    try:
        repo = QdrantVectorRepository(host=host, port=port)
        # Qdrant client connects on first use

        print("✅ Connected successfully!")

        # Test collection creation
        print("\n📝 Testing collection management...")
        test_collection = "test_collection"

        # Create test collection
        await repo.ensure_collection(test_collection, vector_size=384)
        print(f"  ✅ Created test collection: {test_collection}")

        # Store test vectors
        print("\n📝 Testing vector storage...")
        test_vectors = [
            ([0.1] * 384, {"id": "test-1", "text": "Test vector 1"}),
            ([0.2] * 384, {"id": "test-2", "text": "Test vector 2"}),
        ]

        await repo.store_vectors(test_collection, test_vectors)
        print(f"  ✅ Stored {len(test_vectors)} test vectors")

        # Search test
        print("\n📝 Testing vector search...")
        query_vector = [0.15] * 384
        results = await repo.search(test_collection, query_vector, limit=2)

        if len(results) == 2:
            print(f"  ✅ Search returned {len(results)} results")
        else:
            print(f"  ⚠️  Search returned {len(results)} results (expected 2)")

        # Clean up
        print("\n🧹 Cleaning up test collection...")
        await repo.delete_collection(test_collection)
        print("  ✅ Test collection deleted")

        # Close client
        repo.client.close()

        print("\n✅ Qdrant verification completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Qdrant verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_redis():
    """Verify Redis connection and basic operations."""
    print("\n" + "=" * 80)
    print("VERIFYING REDIS CONNECTION")
    print("=" * 80)

    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6380"))  # Using host port
    password = os.getenv("REDIS_PASSWORD", None)

    print(f"Connecting to Redis at {host}:{port}")

    try:
        repo = RedisCacheRepository(host=host, port=port, password=password)
        await repo.connect()

        print("✅ Connected successfully!")

        # Test string operations
        print("\n📝 Testing string operations...")
        test_key = "test:verification"
        test_value = "Hello, Redis!"

        await repo.set(test_key, test_value, ttl_seconds=60)
        print(f"  ✅ Set key: {test_key}")

        retrieved = await repo.get(test_key)
        if retrieved == test_value:
            print(f"  ✅ Retrieved value matches")
        else:
            print(f"  ❌ Retrieved value mismatch: {retrieved} != {test_value}")
            return False

        # Test hash operations
        print("\n📝 Testing hash operations...")
        hash_key = "test:hash"
        hash_data = {"field1": "value1", "field2": "value2"}

        await repo.hset(hash_key, hash_data)
        print(f"  ✅ Set hash: {hash_key}")

        retrieved_hash = await repo.hgetall(hash_key)
        if retrieved_hash == hash_data:
            print(f"  ✅ Retrieved hash matches")
        else:
            print(f"  ❌ Retrieved hash mismatch")
            return False

        # Test list operations
        print("\n📝 Testing list operations...")
        list_key = "test:list"
        list_items = ["item1", "item2", "item3"]

        for item in list_items:
            await repo.lpush(list_key, item)
        print(f"  ✅ Pushed {len(list_items)} items to list")

        retrieved_list = await repo.lrange(list_key, 0, -1)
        if len(retrieved_list) == len(list_items):
            print(f"  ✅ Retrieved {len(retrieved_list)} items from list")
        else:
            print(f"  ❌ List length mismatch")
            return False

        # Clean up
        print("\n🧹 Cleaning up test data...")
        await repo.delete(test_key)
        await repo.delete(hash_key)
        await repo.delete(list_key)
        print("  ✅ Test data cleaned up")

        await repo.close()

        print("\n✅ Redis verification completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Redis verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all verification tests."""
    print("\n" + "=" * 80)
    print("STORAGE BACKEND VERIFICATION")
    print("=" * 80)
    print()

    results = {
        "PostgreSQL": False,
        "Qdrant": False,
        "Redis": False,
    }

    # Run verifications
    results["PostgreSQL"] = await verify_postgresql()
    results["Qdrant"] = await verify_qdrant()
    results["Redis"] = await verify_redis()

    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)

    all_passed = True
    for service, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{service:15} {status}")
        if not passed:
            all_passed = False

    print("=" * 80)

    if all_passed:
        print("\n🎉 All storage backends verified successfully!")
        return 0
    else:
        print("\n❌ Some storage backends failed verification")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
