#!/usr/bin/env python3
"""
Manual integration test for the complete pipeline flow.

This script tests the end-to-end flow:
1. Collection → 2. Processing → 3. Storage → 4. Query

Run this after infrastructure is set up to verify everything works.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trend_agent.orchestrator import TrendIntelligenceOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_collection_only():
    """Test just the collection phase."""
    print("\n" + "=" * 80)
    print("TEST 1: COLLECTION ONLY")
    print("=" * 80 + "\n")

    orchestrator = TrendIntelligenceOrchestrator()

    try:
        await orchestrator.connect()
        print("✅ Connected to all storage backends\n")

        # Test collecting from a single plugin (HackerNews is usually fast)
        print("🔄 Collecting from HackerNews...")
        result = await orchestrator.collect_from_plugin("hackernews")

        print(f"\n📊 Collection Results:")
        print(f"   Items collected: {result['items_collected']}")
        print(f"   Items saved: {result['items_saved']}")
        print(f"   Duration: {result['duration_seconds']:.2f}s")

        if result['items_saved'] > 0:
            print("\n✅ TEST PASSED: Collection working!")
            return True
        else:
            print("\n⚠️  TEST WARNING: No items collected (might be normal if source has no new data)")
            return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await orchestrator.disconnect()


async def test_processing_only():
    """Test just the processing phase (requires items in database)."""
    print("\n" + "=" * 80)
    print("TEST 2: PROCESSING ONLY")
    print("=" * 80 + "\n")

    orchestrator = TrendIntelligenceOrchestrator()

    try:
        await orchestrator.connect()
        print("✅ Connected to all storage backends\n")

        # Test processing pending items
        print("🔄 Processing pending items...")
        result = await orchestrator.process_pending_items(limit=10)

        print(f"\n📊 Processing Results:")
        print(f"   Items processed: {result['items_processed']}")
        print(f"   Items updated: {result['items_updated']}")
        print(f"   Embeddings saved: {result['embeddings_saved']}")
        print(f"   Topics created: {result['topics_created']}")
        print(f"   Trends created: {result['trends_created']}")
        print(f"   Duration: {result['duration_seconds']:.2f}s")
        print(f"   Pipeline status: {result['pipeline_status']}")

        if result['items_processed'] > 0:
            print("\n✅ TEST PASSED: Processing working!")
            return True
        else:
            print("\n⚠️  TEST INFO: No pending items to process")
            print("   (This is normal if no items have been collected yet)")
            return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await orchestrator.disconnect()


async def test_full_pipeline():
    """Test the complete end-to-end pipeline."""
    print("\n" + "=" * 80)
    print("TEST 3: FULL END-TO-END PIPELINE")
    print("=" * 80 + "\n")

    orchestrator = TrendIntelligenceOrchestrator()

    try:
        await orchestrator.connect()
        print("✅ Connected to all storage backends\n")

        # Run full pipeline for HackerNews
        print("🚀 Running full pipeline (collect + process)...")
        result = await orchestrator.run_full_pipeline(plugin_name="hackernews")

        print(f"\n📊 Full Pipeline Results:")
        print(f"\n   Collection:")
        print(f"      Items collected: {result['collection']['items_collected']}")
        print(f"      Items saved: {result['collection']['items_saved']}")

        print(f"\n   Processing:")
        print(f"      Items processed: {result['processing']['items_processed']}")
        print(f"      Topics created: {result['processing']['topics_created']}")
        print(f"      Trends created: {result['processing']['trends_created']}")

        print(f"\n   Total Duration: {result['total_duration_seconds']:.2f}s")

        if result['collection']['items_saved'] > 0:
            print("\n✅ TEST PASSED: Full pipeline working!")
            return True
        else:
            print("\n⚠️  TEST WARNING: No items processed (might be normal)")
            return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await orchestrator.disconnect()


async def test_database_queries():
    """Test querying data from the database."""
    print("\n" + "=" * 80)
    print("TEST 4: DATABASE QUERIES")
    print("=" * 80 + "\n")

    orchestrator = TrendIntelligenceOrchestrator()

    try:
        await orchestrator.connect()
        print("✅ Connected to all storage backends\n")

        # Query recent items
        print("🔍 Querying database for recent items...")

        # Get count of items
        count_query = "SELECT COUNT(*) FROM processed_items"
        count = await orchestrator.db_pool.pool.fetchval(count_query)
        print(f"   Total items in database: {count}")

        # Get recent items
        recent_query = """
            SELECT source, COUNT(*) as count
            FROM processed_items
            GROUP BY source
            ORDER BY count DESC
        """
        results = await orchestrator.db_pool.pool.fetch(recent_query)

        print(f"\n   Items by source:")
        for row in results:
            print(f"      {row['source']}: {row['count']}")

        # Get trends count
        trends_count = await orchestrator.db_pool.pool.fetchval(
            "SELECT COUNT(*) FROM trends"
        )
        print(f"\n   Total trends: {trends_count}")

        # Get topics count
        topics_count = await orchestrator.db_pool.pool.fetchval(
            "SELECT COUNT(*) FROM topics"
        )
        print(f"   Total topics: {topics_count}")

        print("\n✅ TEST PASSED: Database queries working!")
        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await orchestrator.disconnect()


async def main():
    """Run all integration tests."""
    print("\n" + "=" * 80)
    print("TREND INTELLIGENCE PLATFORM - INTEGRATION TEST SUITE")
    print("=" * 80)

    tests = [
        ("Collection", test_collection_only),
        ("Processing", test_processing_only),
        ("Full Pipeline", test_full_pipeline),
        ("Database Queries", test_database_queries),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            passed = await test_func()
            results[test_name] = passed
        except Exception as e:
            print(f"\n❌ {test_name} test crashed: {e}")
            results[test_name] = False

        # Small pause between tests
        await asyncio.sleep(1)

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:20} {status}")

    print("=" * 80)

    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
