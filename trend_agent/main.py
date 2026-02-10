import asyncio
from collectors import get_all_collectors
from processing.normalize import normalize
from processing.deduplicate import deduplicate
from processing.cluster import cluster
from processing.rank import rank_clusters
from llm.summarizer import summarize


async def collect_all():
    """Collect topics from all data sources using the collector registry."""
    # Get all registered collectors
    collectors = get_all_collectors()

    # Execute all collector fetch functions in parallel
    sources = [collector() for collector in collectors.values()]
    results = await asyncio.gather(*sources, return_exceptions=True)

    # Collect topics, skipping any collectors that failed
    topics = []
    for idx, result in enumerate(results):
        if isinstance(result, Exception):
            collector_name = list(collectors.keys())[idx]
            print(f"⚠️  Collector '{collector_name}' failed: {result}")
        else:
            topics.extend(result)

    return topics


async def main():
    """Main pipeline: collect, process, and summarize trending topics."""
    print("🔍 Collecting trending topics...")
    raw = await collect_all()
    print(f"   Collected {len(raw)} topics")

    print("\n📝 Normalizing...")
    norm = normalize(raw)

    print("🔄 Deduplicating...")
    dedup = deduplicate(norm)
    print(f"   {len(dedup)} unique topics after deduplication")

    print("\n🗂️  Clustering similar topics...")
    clusters = cluster(dedup)
    print(f"   Created {len(clusters)} clusters")

    print("\n📊 Ranking by importance...")
    ranked = rank_clusters(clusters)

    print("\n🔥 Top Trends:\n")
    print("=" * 80)

    for i, c in enumerate(ranked[:20], 1):
        print(f"\n#{i}")
        print("-" * 80)
        summary = await summarize(c)
        print(summary)
        print(f"\nSources: {len(c)} topics")
        print("-" * 80)

    print("\n✅ Analysis complete!")


if __name__ == "__main__":
    asyncio.run(main())
