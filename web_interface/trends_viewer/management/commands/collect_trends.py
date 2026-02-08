import asyncio
import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from asgiref.sync import sync_to_async
from trends_viewer.models import CollectionRun, CollectedTopic, TrendCluster

# Import trend_agent modules
from collectors import reddit, hackernews, google_news
from processing.normalize import normalize
from processing.deduplicate import deduplicate
from processing.cluster import cluster
from processing.rank import rank_clusters
from llm.summarizer import summarize


class Command(BaseCommand):
    help = 'Collect and analyze trending topics from multiple sources'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-trends',
            type=int,
            default=20,
            help='Maximum number of trends to summarize (default: 20)'
        )

    def handle(self, *args, **options):
        max_trends = options['max_trends']
        start_time = time.time()

        # Create collection run record
        collection_run = CollectionRun.objects.create(
            timestamp=timezone.now(),
            status='running'
        )

        try:
            self.stdout.write(self.style.SUCCESS(f'Started collection run #{collection_run.id}'))

            # Run the async collection pipeline
            asyncio.run(self.run_pipeline(collection_run, max_trends))

            # Calculate duration
            duration = time.time() - start_time
            collection_run.duration_seconds = duration
            collection_run.status = 'completed'
            collection_run.save()

            self.stdout.write(self.style.SUCCESS(
                f'✅ Collection completed in {duration:.1f}s\n'
                f'   Topics: {collection_run.topics_count}\n'
                f'   Clusters: {collection_run.clusters_count}'
            ))

        except Exception as e:
            collection_run.status = 'failed'
            collection_run.error_message = str(e)
            collection_run.save()
            self.stdout.write(self.style.ERROR(f'❌ Collection failed: {str(e)}'))
            raise

    async def run_pipeline(self, collection_run, max_trends):
        """Run the full trend collection and analysis pipeline."""

        # Step 1: Collect from all sources
        self.stdout.write('🔍 Collecting trending topics...')
        sources = [reddit.fetch(), hackernews.fetch(), google_news.fetch()]
        results = await asyncio.gather(*sources)

        raw_topics = []
        for r in results:
            raw_topics.extend(r)

        self.stdout.write(f'   Collected {len(raw_topics)} raw topics')

        # Step 2: Normalize
        self.stdout.write('📝 Normalizing...')
        normalized = normalize(raw_topics)

        # Step 3: Deduplicate
        self.stdout.write('🔄 Deduplicating...')
        unique_topics = deduplicate(normalized)
        self.stdout.write(f'   {len(unique_topics)} unique topics')

        # Step 4: Save topics to database
        self.stdout.write('💾 Saving topics to database...')
        saved_topics = []
        for topic in unique_topics:
            db_topic = await sync_to_async(CollectedTopic.objects.create)(
                collection_run=collection_run,
                title=topic.title,
                description=topic.description,
                source=topic.source,
                url=topic.url,
                timestamp=topic.timestamp,
                upvotes=topic.metrics.get('upvotes', 0),
                comments=topic.metrics.get('comments', 0),
                score=topic.metrics.get('score', 0),
            )
            saved_topics.append((db_topic, topic))

        collection_run.topics_count = len(saved_topics)
        await sync_to_async(collection_run.save)()

        # Step 5: Cluster similar topics
        self.stdout.write('🗂️  Clustering similar topics...')
        clusters = cluster(unique_topics)
        self.stdout.write(f'   Created {len(clusters)} clusters')

        # Step 6: Rank clusters
        self.stdout.write('📊 Ranking by importance...')
        ranked = rank_clusters(clusters)

        # Step 7: Summarize top trends
        self.stdout.write(f'🤖 Generating summaries for top {max_trends} trends...')

        for rank_idx, topic_cluster in enumerate(ranked[:max_trends], 1):
            self.stdout.write(f'   Processing trend #{rank_idx}...')

            # Generate summary using Claude
            summary = await summarize(topic_cluster)

            # Extract title from summary (first line)
            summary_lines = summary.strip().split('\n')
            trend_title = summary_lines[0] if summary_lines else f"Trend {rank_idx}"

            # Calculate cluster score
            score = sum([
                t.metrics.get('upvotes', 0) +
                t.metrics.get('comments', 0) +
                t.metrics.get('score', 0)
                for t in topic_cluster
            ])

            # Create trend cluster in database
            db_cluster = await sync_to_async(TrendCluster.objects.create)(
                collection_run=collection_run,
                rank=rank_idx,
                title=trend_title,
                summary=summary,
                score=score,
            )

            # Link topics to this cluster
            for db_topic, original_topic in saved_topics:
                if original_topic in topic_cluster:
                    db_topic.cluster = db_cluster
                    await sync_to_async(db_topic.save)()

        collection_run.clusters_count = min(len(ranked), max_trends)
        await sync_to_async(collection_run.save)()

        self.stdout.write(self.style.SUCCESS('✨ Analysis complete!'))
