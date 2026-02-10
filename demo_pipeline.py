"""
Demo script to test the processing pipeline.

This script demonstrates the complete pipeline functionality
without requiring database dependencies.
"""

import asyncio
from datetime import datetime, timedelta
from pydantic import HttpUrl

# Import pipeline components
from trend_agent.processing import create_standard_pipeline
from trend_agent.types import Metrics, RawItem, SourceType
from tests.mocks.intelligence import MockEmbeddingService, MockLLMService


async def main():
    """Run pipeline demo."""
    print("=" * 80)
    print("Processing Pipeline Demo - Session 3")
    print("=" * 80)
    print()

    # Create mock services
    print("1️⃣  Creating services...")
    embedding_svc = MockEmbeddingService()
    llm_svc = MockLLMService()
    print("   ✅ Mock embedding service created")
    print("   ✅ Mock LLM service created")
    print()

    # Create sample raw items
    print("2️⃣  Creating sample data (20 raw items)...")
    now = datetime.utcnow()
    raw_items = []

    # AI-related items (should cluster together)
    for i in range(5):
        raw_items.append(
            RawItem(
                source=SourceType.REDDIT,
                source_id=f"ai_{i}",
                url=HttpUrl(f"https://reddit.com/ai_{i}"),
                title=f"New AI breakthrough in {['GPT', 'ChatGPT', 'LLMs', 'AI Models', 'Machine Learning'][i]}",
                description="Exciting developments in artificial intelligence",
                content="Detailed content about AI advancements...",
                published_at=now - timedelta(hours=i),
                metrics=Metrics(upvotes=100 + i * 50, comments=20 + i * 10),
            )
        )

    # Politics items (should cluster together)
    for i in range(5):
        raw_items.append(
            RawItem(
                source=SourceType.BBC,
                source_id=f"politics_{i}",
                url=HttpUrl(f"https://bbc.com/politics_{i}"),
                title=f"Political development: {['Election', 'Congress', 'President', 'Legislation', 'Campaign'][i]}",
                description="Latest political news",
                content="Political updates and analysis...",
                published_at=now - timedelta(hours=i + 2),
                metrics=Metrics(upvotes=80 + i * 30, comments=15 + i * 5),
            )
        )

    # Technology items (should cluster together)
    for i in range(5):
        raw_items.append(
            RawItem(
                source=SourceType.HACKERNEWS,
                source_id=f"tech_{i}",
                url=HttpUrl(f"https://news.ycombinator.com/tech_{i}"),
                title=f"Tech news: {['Startup', 'Programming', 'Cloud', 'DevOps', 'SaaS'][i]} updates",
                description="Technology industry news",
                content="Latest in tech...",
                published_at=now - timedelta(hours=i + 1),
                metrics=Metrics(upvotes=120 + i * 40, comments=25 + i * 8),
            )
        )

    # Sports items
    for i in range(5):
        raw_items.append(
            RawItem(
                source=SourceType.REUTERS,
                source_id=f"sports_{i}",
                url=HttpUrl(f"https://reuters.com/sports_{i}"),
                title=f"Sports update: {['Football', 'Basketball', 'Tennis', 'Soccer', 'Baseball'][i]} highlights",
                description="Sports news and scores",
                content="Game highlights and analysis...",
                published_at=now - timedelta(hours=i + 3),
                metrics=Metrics(upvotes=90 + i * 35, comments=18 + i * 6),
            )
        )

    print(f"   ✅ Created {len(raw_items)} raw items")
    print()

    # Create pipeline
    print("3️⃣  Creating processing pipeline...")
    pipeline = create_standard_pipeline(embedding_svc, llm_svc)
    stages = pipeline.get_stages()
    print(f"   ✅ Pipeline created with {len(stages)} stages:")
    for i, stage_name in enumerate(stages, 1):
        print(f"      {i}. {stage_name}")
    print()

    # Run pipeline
    print("4️⃣  Running pipeline...")
    print("   ⏳ Processing items through all stages...")
    result = await pipeline.run(raw_items)
    print()

    # Display results
    print("5️⃣  Pipeline Results:")
    print(f"   Status: {result.status.value}")
    print(f"   Items collected: {result.items_collected}")
    print(f"   Items processed: {result.items_processed}")
    print(f"   Items after dedup: {result.items_deduplicated}")
    print(f"   Topics created: {result.topics_created}")
    print(f"   Trends created: {result.trends_created}")
    print(f"   Duration: {result.duration_seconds:.2f}s")
    if result.errors:
        print(f"   Errors: {len(result.errors)}")
        for error in result.errors:
            print(f"      - {error}")
    print()

    # Display trends
    if "trends" in result.metadata:
        trends = result.metadata["trends"]
        print("6️⃣  Top Trends:")
        print()
        for trend in trends[:10]:  # Top 10
            print(f"   Rank #{trend.rank}: {trend.title}")
            print(f"      Score: {trend.score:.1f}")
            print(f"      Category: {trend.category.value}")
            print(f"      State: {trend.state.value}")
            print(f"      Sources: {', '.join([s.value for s in trend.sources])}")
            print(f"      Engagement: {trend.total_engagement.upvotes} upvotes, "
                  f"{trend.total_engagement.comments} comments")
            print(f"      Velocity: {trend.velocity:.2f} engagement/hour")
            if trend.keywords:
                print(f"      Keywords: {', '.join(trend.keywords[:5])}")
            print()

    # Summary
    print("=" * 80)
    print("✅ Pipeline Demo Complete!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
