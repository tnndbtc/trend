import asyncio
from collectors import reddit, hackernews, google_news
from processing.normalize import normalize
from processing.deduplicate import deduplicate
from processing.cluster import cluster
from processing.rank import rank_clusters
from llm.summarizer import summarize


async def collect_all():
    """Collect topics from all data sources."""
    sources = [reddit.fetch(), hackernews.fetch(), google_news.fetch()]
    results = await asyncio.gather(*sources)
    topics = []
    for r in results:
        topics.extend(r)
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
