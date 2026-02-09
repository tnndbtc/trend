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
from llm.summarizer import summarize_single_topic, summarize_topics_batch
from categories import load_categories


class Command(BaseCommand):
    help = 'Collect and analyze trending topics from multiple sources'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-posts-per-category',
            type=int,
            default=5,
            help='Maximum posts to keep per category after clustering (default: 5)'
        )

    def handle(self, *args, **options):
        max_posts_per_category = options['max_posts_per_category']
        start_time = time.time()

        # Load categories from configuration
        categories = load_categories()
        self.stdout.write(f'Using {len(categories)} categories: {", ".join(categories)}')

        # Create collection run record
        collection_run = CollectionRun.objects.create(
            timestamp=timezone.now(),
            status='running'
        )

        try:
            self.stdout.write(self.style.SUCCESS(f'Started collection run #{collection_run.id}'))

            # Run the async collection pipeline
            asyncio.run(self.run_pipeline(collection_run, categories, max_posts_per_category))

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

    async def run_pipeline(self, collection_run, categories, max_posts_per_category):
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

        # Step 4: Cluster ALL topics into categories first
        self.stdout.write(f'🗂️  Clustering all topics into {len(categories)} categories...')
        clusters, cluster_category_names = cluster_topics(unique_topics, categories)
        self.stdout.write(f'   Created {len(clusters)} clusters')
        for i, (cat_name, cluster) in enumerate(zip(cluster_category_names, clusters), 1):
            self.stdout.write(f'   {i}. {cat_name}: {len(cluster)} posts')

        # Step 5: Deduplicate within each category and select top N posts
        self.stdout.write(f'📊 Deduplicating and selecting top {max_posts_per_category} posts from each category...')

        selected_clusters = []
        selected_category_names = []
        total_selected = 0

        for cluster, cat_name in zip(clusters, cluster_category_names):
            # First, deduplicate similar posts within this category
            # Use lower threshold (0.80 = 80% similarity) to catch posts about same topic
            deduplicated_cluster = deduplicate(cluster, threshold=0.80, debug=False)
            self.stdout.write(f'   {cat_name}: {len(cluster)} posts → {len(deduplicated_cluster)} after dedup')

            # Rank topics in this cluster by engagement
            ranked = rank_topics(deduplicated_cluster)
            # Select top N posts from this category
            selected = ranked[:max_posts_per_category]

            if selected:  # Only keep non-empty clusters
                selected_clusters.append(selected)
                selected_category_names.append(cat_name)
                total_selected += len(selected)
                self.stdout.write(f'   {cat_name}: selected {len(selected)} posts')

        # Flatten selected topics for content fetching and summarization
        selected_topics = []
        for cluster in selected_clusters:
            selected_topics.extend(cluster)

        self.stdout.write(f'   Total selected: {total_selected} posts across {len(selected_clusters)} categories')

        # Update cluster references for subsequent steps
        clusters = selected_clusters
        cluster_category_names = selected_category_names

        # Step 6: Rank clusters by engagement
        self.stdout.write('📊 Ranking clusters by importance...')
        # Pair clusters with their category names for ranking
        clusters_with_categories = list(zip(clusters, cluster_category_names))
        ranked_clusters_raw = rank_clusters(clusters)
        # Re-pair ranked clusters with their original category names
        ranked_clusters = []
        for ranked_cluster in ranked_clusters_raw:
            # Find the category name for this cluster
            for orig_cluster, cat_name in clusters_with_categories:
                if orig_cluster is ranked_cluster:
                    ranked_clusters.append((ranked_cluster, cat_name))
                    break

        # Keep ALL category clusters
        self.stdout.write(f'📦 Using all {len(ranked_clusters)} category clusters')
        top_clusters = ranked_clusters

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

        # Step 10: Create category clusters (without AI-generated summaries)
        self.stdout.write(f'📦 Creating {len(top_clusters)} category clusters...')

        for rank_idx, (topic_cluster, category_name) in enumerate(top_clusters, 1):
            self.stdout.write(f'   Creating cluster #{rank_idx}: {category_name}...')

            # Use category name directly as title (no API call needed)
            trend_title = category_name

            # No category summary - leave empty
            summary = ""

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
