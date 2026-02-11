#!/usr/bin/env python3
"""
Simple connectivity test for storage backends.
Tests only basic connection and ping operations.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def verify_postgresql():
    """Verify PostgreSQL connection."""
    print("=" * 80)
    print("VERIFYING POSTGRESQL CONNECTION")
    print("=" * 80)

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5433"))
    database = os.getenv("POSTGRES_DB", "trends")
    user = os.getenv("POSTGRES_USER", "trend_user")
    password = os.getenv("POSTGRES_PASSWORD", "trend_password")

    print(f"Connecting to PostgreSQL at {host}:{port}/{database}")

    try:
        import asyncpg
        conn = await asyncpg.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
        )

        # Test query
        version = await conn.fetchval("SELECT version()")
        print(f"✅ Connected successfully!")
        print(f"   Server version: {version[:50]}...")

        # Test tables exist
        tables = await conn.fetch("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)

        print(f"✅ Found {len(tables)} tables:")
        for row in tables:
            print(f"   - {row['tablename']}")

        await conn.close()
        print("\n✅ PostgreSQL verification completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ PostgreSQL verification failed: {e}")
        return False


async def verify_qdrant():
    """Verify Qdrant connection."""
    print("\n" + "=" * 80)
    print("VERIFYING QDRANT CONNECTION")
    print("=" * 80)

    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))

    print(f"Connecting to Qdrant at {host}:{port}")

    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(host=host, port=port)

        # Test connection by getting collections
        collections = client.get_collections()

        print(f"✅ Connected successfully!")
        print(f"✅ Found {len(collections.collections)} collections")

        if collections.collections:
            for coll in collections.collections:
                print(f"   - {coll.name}")

        client.close()
        print("\n✅ Qdrant verification completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Qdrant verification failed: {e}")
        return False


async def verify_redis():
    """Verify Redis connection."""
    print("\n" + "=" * 80)
    print("VERIFYING REDIS CONNECTION")
    print("=" * 80)

    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6380"))
    password = os.getenv("REDIS_PASSWORD", None)

    print(f"Connecting to Redis at {host}:{port}")

    try:
        import redis.asyncio as aioredis

        client = await aioredis.from_url(
            f"redis://{host}:{port}/0",
            password=password,
            decode_responses=True,
        )

        # Test ping
        pong = await client.ping()
        print(f"✅ Connected successfully! (ping={pong})")

        # Test basic set/get
        await client.set("test:verify", "OK", ex=10)
        value = await client.get("test:verify")

        if value == "OK":
            print(f"✅ Basic operations working")
        else:
            print(f"⚠️  Unexpected value: {value}")

        # Get info
        info = await client.info("server")
        print(f"✅ Redis version: {info.get('redis_version')}")

        # Clean up
        await client.delete("test:verify")
        await client.close()

        print("\n✅ Redis verification completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Redis verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def verify_rabbitmq():
    """Verify RabbitMQ connection."""
    print("\n" + "=" * 80)
    print("VERIFYING RABBITMQ CONNECTION")
    print("=" * 80)

    host = os.getenv("RABBITMQ_HOST", "localhost")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    user = os.getenv("RABBITMQ_USER", "trend_user")
    password = os.getenv("RABBITMQ_PASSWORD", "trend_password")

    print(f"Connecting to RabbitMQ at {host}:{port}")

    try:
        import aio_pika

        connection = await aio_pika.connect_robust(
            f"amqp://{user}:{password}@{host}:{port}/",
        )

        print(f"✅ Connected successfully!")

        # Create a channel
        channel = await connection.channel()
        print(f"✅ Channel created")

        await connection.close()

        print("\n✅ RabbitMQ verification completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ RabbitMQ verification failed: {e}")
        print("   (Note: aio_pika may not be installed - this is optional)")
        return False


async def main():
    """Run all verification tests."""
    print("\n" + "=" * 80)
    print("STORAGE BACKEND CONNECTIVITY VERIFICATION")
    print("=" * 80)
    print()

    results = {}

    # Run verifications
    results["PostgreSQL"] = await verify_postgresql()
    results["Qdrant"] = await verify_qdrant()
    results["Redis"] = await verify_redis()
    results["RabbitMQ"] = await verify_rabbitmq()

    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)

    all_passed = True
    for service, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{service:15} {status}")
        if not passed and service != "RabbitMQ":  # RabbitMQ is optional
            all_passed = False

    print("=" * 80)

    if all_passed:
        print("\n🎉 All required storage backends verified successfully!")
        return 0
    else:
        print("\n⚠️  Some required storage backends failed verification")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
