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
from processing.cluster import cluster as cluster_topics
from processing.rank import rank_clusters, rank_topics
from processing.content_fetcher import fetch_content_for_topic
from llm.summarizer import summarize, summarize_single_topic, summarize_topics_batch


class Command(BaseCommand):
    help = 'Collect and analyze trending topics from multiple sources'

    def add_arguments(self, parser):
        parser.add_argument(
            '--number-of-topics',
            type=int,
            default=10,
            help='Number of topic clusters to generate (default: 10)'
        )
        parser.add_argument(
            '--max-posts-per-source',
            type=int,
            default=5,
            help='Maximum posts to collect from each source (Reddit, HN, Google News) (default: 5)'
        )

    def handle(self, *args, **options):
        number_of_topics = options['number_of_topics']
        max_posts_per_source = options['max_posts_per_source']
        start_time = time.time()

        # Create collection run record
        collection_run = CollectionRun.objects.create(
            timestamp=timezone.now(),
            status='running'
        )

        try:
            self.stdout.write(self.style.SUCCESS(f'Started collection run #{collection_run.id}'))

            # Run the async collection pipeline
            asyncio.run(self.run_pipeline(collection_run, number_of_topics, max_posts_per_source))

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

    async def run_pipeline(self, collection_run, number_of_topics, max_posts_per_source):
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

        # Step 4: Select top N posts from each source
        self.stdout.write(f'📊 Selecting top {max_posts_per_source} posts from each source...')

        # Group topics by source
        topics_by_source = {}
        for topic in unique_topics:
            source = topic.source
            if source not in topics_by_source:
                topics_by_source[source] = []
            topics_by_source[source].append(topic)

        # For each source, rank and select top N
        selected_topics = []
        for source, topics in topics_by_source.items():
            ranked = rank_topics(topics)
            selected = ranked[:max_posts_per_source]
            selected_topics.extend(selected)
            self.stdout.write(f'   {source}: selected {len(selected)} posts')

        self.stdout.write(f'   Total selected: {len(selected_topics)} posts from {len(topics_by_source)} sources')

        # Step 5: Cluster the selected topics
        self.stdout.write('🗂️  Clustering similar topics...')
        clusters = cluster_topics(selected_topics)
        self.stdout.write(f'   Created {len(clusters)} clusters')

        # Step 6: Rank clusters by engagement
        self.stdout.write('📊 Ranking clusters by importance...')
        ranked_clusters = rank_clusters(clusters)

        # Step 7: Keep top N clusters (or all if N >= cluster count)
        clusters_to_keep = min(number_of_topics, len(ranked_clusters))
        # Actually, keep ALL clusters since we already filtered by source
        # This ensures all source-selected topics are displayed
        self.stdout.write(f'📦 Keeping all {len(ranked_clusters)} clusters (from {len(selected_topics)} source-filtered topics)...')
        top_clusters = ranked_clusters  # Keep all clusters
        self.stdout.write(f'   Selected {len(top_clusters)} clusters for display')

        # Step 7: Fetch full content for selected topics
        self.stdout.write('📥 Fetching full content for topics...')
        for idx, topic in enumerate(selected_topics, 1):
            if idx % 10 == 0:
                self.stdout.write(f'   Fetched {idx}/{len(selected_topics)} topics...')
            topic.content = await fetch_content_for_topic(topic)

        self.stdout.write(f'✅ Content fetched for {len(selected_topics)} topics')

        # Step 8: Batch summarize topics (much more efficient!)
        self.stdout.write('🤖 Batch summarizing topics...')
        BATCH_SIZE = 15  # Process 15 topics per API call
        total_batches = (len(selected_topics) + BATCH_SIZE - 1) // BATCH_SIZE

        for batch_idx in range(0, len(selected_topics), BATCH_SIZE):
            batch = selected_topics[batch_idx:batch_idx + BATCH_SIZE]
            batch_num = (batch_idx // BATCH_SIZE) + 1
            self.stdout.write(f'   Processing batch {batch_num}/{total_batches} ({len(batch)} topics)...')

            try:
                # Batch summarize all topics in this batch
                results = await summarize_topics_batch(batch)

                # Handle case where results is not a list or is empty
                if not isinstance(results, list):
                    raise ValueError(f"Expected list of results, got {type(results)}")

                if len(results) != len(batch):
                    raise ValueError(f"Result count mismatch: expected {len(batch)}, got {len(results)}")

                # Assign results back to topics
                for topic, result in zip(batch, results):
                    topic.title_summary = result.get('title_summary', topic.title)
                    topic.full_summary = result.get('full_summary', f"[{topic.url}] {topic.title}")
                    # Update language if provided
                    if result.get('language'):
                        topic.language = result['language']

            except Exception as e:
                self.stdout.write(f'   ⚠️  Batch {batch_num} failed: {str(e)}')
                self.stdout.write(f'   Falling back to individual processing for this batch...')

                # Fallback: process individually
                for topic in batch:
                    try:
                        summary_result = await summarize_single_topic(topic)
                        topic.title_summary = summary_result.get('title_summary', topic.title)
                        topic.full_summary = summary_result.get('full_summary', f"[{topic.url}] {topic.title}")
                        if summary_result.get('language'):
                            topic.language = summary_result['language']
                    except Exception as e2:
                        self.stdout.write(f'   ⚠️  Failed to summarize topic: {str(e2)}')
                        topic.title_summary = topic.title
                        topic.full_summary = f"[{topic.url}] {topic.title}"

        self.stdout.write(f'✅ Batch summarization complete for {len(selected_topics)} topics')

        # Step 9: Save topics to database
        self.stdout.write('💾 Saving topics to database...')
        saved_topics = []
        for topic in selected_topics:
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
                language=topic.language,
                content=topic.content,
                title_summary=topic.title_summary,
                full_summary=topic.full_summary,
            )
            saved_topics.append((db_topic, topic))

        collection_run.topics_count = len(saved_topics)
        await sync_to_async(collection_run.save)()

        # Step 10: Generate cluster summaries for top clusters
        self.stdout.write(f'🤖 Generating cluster summaries for top {number_of_topics} topic clusters...')

        for rank_idx, topic_cluster in enumerate(top_clusters, 1):
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

            # Determine cluster language (most common language in cluster)
            from collections import Counter
            languages = [t.language for t in topic_cluster if hasattr(t, 'language')]
            cluster_language = Counter(languages).most_common(1)[0][0] if languages else 'en'

            # Create trend cluster in database
            db_cluster = await sync_to_async(TrendCluster.objects.create)(
                collection_run=collection_run,
                rank=rank_idx,
                title=trend_title,
                summary=summary,
                score=score,
                language=cluster_language,
                title_summary=trend_title,
                full_summary=summary,
            )

            # Link topics to this cluster
            for db_topic, original_topic in saved_topics:
                if original_topic in topic_cluster:
                    db_topic.cluster = db_cluster
                    await sync_to_async(db_topic.save)()

        collection_run.clusters_count = len(top_clusters)
        await sync_to_async(collection_run.save)()

        self.stdout.write(self.style.SUCCESS('✨ Analysis complete!'))
