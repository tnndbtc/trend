#!/usr/bin/env python3
"""
Storage Services Health Check Script

This script verifies that all storage services (PostgreSQL, Qdrant, Redis)
are running and accessible. Run this before integration tests.

Usage:
    python scripts/verify-storage-services.py
"""

import asyncio
import sys
from typing import Dict, List, Tuple

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


async def check_postgres() -> Tuple[bool, str]:
    """Check PostgreSQL connection."""
    try:
        import asyncpg

        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            database="trends",
            user="trend_user",
            password="trend_password",
            timeout=5,
        )

        # Test query
        version = await conn.fetchval("SELECT version()")
        await conn.close()

        return True, f"PostgreSQL connected: {version.split(',')[0]}"
    except ImportError:
        return False, "asyncpg not installed (pip install asyncpg)"
    except Exception as e:
        return False, f"PostgreSQL connection failed: {str(e)}"


async def check_qdrant() -> Tuple[bool, str]:
    """Check Qdrant connection."""
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(host="localhost", port=6333, timeout=5)

        # Get cluster info
        collections = client.get_collections()

        return True, f"Qdrant connected: {len(collections.collections)} collections"
    except ImportError:
        return False, "qdrant-client not installed (pip install qdrant-client)"
    except Exception as e:
        return False, f"Qdrant connection failed: {str(e)}"


async def check_redis() -> Tuple[bool, str]:
    """Check Redis connection."""
    try:
        import redis.asyncio as aioredis

        client = await aioredis.from_url(
            "redis://localhost:6379/0",
            encoding="utf-8",
            decode_responses=True,
        )

        # Test ping
        pong = await client.ping()
        info = await client.info()
        version = info.get("redis_version", "unknown")

        await client.close()

        return True, f"Redis connected: version {version}"
    except ImportError:
        return False, "redis not installed (pip install redis)"
    except Exception as e:
        return False, f"Redis connection failed: {str(e)}"


async def check_postgres_schema() -> Tuple[bool, str]:
    """Check if PostgreSQL schema is initialized."""
    try:
        import asyncpg

        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            database="trends",
            user="trend_user",
            password="trend_password",
            timeout=5,
        )

        # Check if main tables exist
        tables = await conn.fetch(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('trends', 'topics', 'processed_items')
            """
        )

        table_names = [row["table_name"] for row in tables]
        await conn.close()

        if len(table_names) == 3:
            return True, f"Schema initialized: {', '.join(table_names)}"
        elif len(table_names) > 0:
            return (
                False,
                f"Partial schema: {', '.join(table_names)}. Run init-db.sql",
            )
        else:
            return False, "Schema not initialized. Run scripts/init-db.sql"
    except Exception as e:
        return False, f"Schema check failed: {str(e)}"


def print_header():
    """Print script header."""
    print(f"\n{BLUE}{'=' * 70}{RESET}")
    print(f"{BLUE}Storage Services Health Check{RESET}")
    print(f"{BLUE}{'=' * 70}{RESET}\n")


def print_result(service: str, success: bool, message: str):
    """Print check result."""
    status = f"{GREEN}✓ OK{RESET}" if success else f"{RED}✗ FAIL{RESET}"
    print(f"{status:20s} {service:20s} {message}")


def print_summary(results: Dict[str, Tuple[bool, str]]):
    """Print summary of all checks."""
    print(f"\n{BLUE}{'=' * 70}{RESET}")

    passed = sum(1 for success, _ in results.values() if success)
    total = len(results)

    if passed == total:
        print(f"{GREEN}All checks passed! ({passed}/{total}){RESET}")
        print(f"{GREEN}Storage layer is ready for use.{RESET}")
    else:
        print(f"{RED}Some checks failed. ({passed}/{total} passed){RESET}")
        print(f"{YELLOW}Please fix the issues above before running tests.{RESET}")

    print(f"{BLUE}{'=' * 70}{RESET}\n")


async def main():
    """Run all health checks."""
    print_header()

    # Run all checks
    results = {}

    print(f"{YELLOW}Checking database connections...{RESET}\n")

    # PostgreSQL
    success, message = await check_postgres()
    print_result("PostgreSQL", success, message)
    results["postgres"] = (success, message)

    # PostgreSQL Schema
    if results["postgres"][0]:
        success, message = await check_postgres_schema()
        print_result("PostgreSQL Schema", success, message)
        results["postgres_schema"] = (success, message)
    else:
        print_result("PostgreSQL Schema", False, "Skipped (connection failed)")
        results["postgres_schema"] = (False, "Skipped")

    # Qdrant
    success, message = await check_qdrant()
    print_result("Qdrant", success, message)
    results["qdrant"] = (success, message)

    # Redis
    success, message = await check_redis()
    print_result("Redis", success, message)
    results["redis"] = (success, message)

    # Print summary
    print_summary(results)

    # Exit with error code if any check failed
    all_passed = all(success for success, _ in results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted by user{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{RED}Error: {e}{RESET}")
        sys.exit(1)
