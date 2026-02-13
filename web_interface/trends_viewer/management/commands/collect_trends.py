import asyncio
import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from asgiref.sync import sync_to_async
from trends_viewer.models import CollectionRun, CollectedTopic, TrendCluster, CrawlerSource

# Import trend_agent modules
from trend_agent.collectors import get_all_collectors
from trend_agent.processing.normalize import normalize
from trend_agent.processing.deduplicate import deduplicate
from trend_agent.processing.cluster import cluster as cluster_topics
from trend_agent.processing.rank import rank_topics, rank_clusters
from trend_agent.processing.content_fetcher import fetch_content_for_topic
from trend_agent.llm.summarizer import summarize_single_topic, summarize_topics_batch
from trend_agent.categories import load_categories
from trend_agent.config import is_source_diversity_enabled, get_max_percentage_per_source


def get_source_display_name(source_str):
    """
    Get the display name for a source.

    For custom sources, looks up the CrawlerSource to get the actual name.
    For other sources, formats them nicely.

    Args:
        source_str: Source identifier (e.g., "SourceType.CUSTOM", "reddit", "bbc")

    Returns:
        Display name for the source (e.g., "Wenxuecity News", "Reddit", "BBC")
    """
    if not source_str:
        return ""

    # Convert to string and handle SourceType enum values
    value_str = str(source_str)

    # Check if it's a custom source
    if 'CUSTOM' in value_str.upper():
        # Try to find the corresponding CrawlerSource
        try:
            custom_source = CrawlerSource.objects.filter(source_type='custom', enabled=True).first()
            if custom_source:
                return custom_source.name
        except Exception:
            pass
        return "Custom"

    # Handle SourceType enum values (e.g., "SourceType.BBC" -> "bbc")
    if value_str.startswith('SourceType.'):
        value_str = value_str.replace('SourceType.', '').lower()

    # Convert to lowercase for comparison
    value_lower = value_str.lower()

    # Special case mappings for nice display names
    special_cases = {
        'google_news': 'Google News',
        'ap_news': 'AP News',
        'al_jazeera': 'Al Jazeera',
        'hackernews': 'Hacker News',
        'bbc': 'BBC',
        'guardian': 'The Guardian',
        'reuters': 'Reuters',
        'reddit': 'Reddit',
        'demo': 'Demo',
    }

    # Return special case or formatted version
    return special_cases.get(value_lower, value_lower.replace('_', ' ').title())


def apply_source_diversity_limit(ranked_topics, max_total, max_percentage_per_source=0.20):
    """
    Apply source diversity limiting to ensure balanced representation.

    Limits each source to a maximum percentage of total selections using round-robin
    selection across sources to maintain ranking quality while enforcing diversity.

    Args:
        ranked_topics: List of topics already sorted by rank (best first)
        max_total: Maximum number of topics to select
        max_percentage_per_source: Maximum fraction each source can contribute (0.0-1.0)

    Returns:
        List of selected topics with source diversity enforced
    """
    if not ranked_topics:
        return []

    # Calculate maximum topics per source
    max_per_source = max(1, int(max_total * max_percentage_per_source))

    # Group topics by source while preserving their rank order
    by_source = {}
    for topic in ranked_topics:
        source = topic.source
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(topic)

    # Round-robin selection across sources to respect both ranking and diversity
    selected = []
    source_counts = {source: 0 for source in by_source.keys()}

    # Keep selecting until we hit the limit or run out of topics
    position = 0
    while len(selected) < max_total:
        added_any = False

        # Try to add one topic from each source at this position
        for source in sorted(by_source.keys()):  # Sort for deterministic ordering
            # Check if this source has topics left and hasn't hit its limit
            if source_counts[source] < max_per_source and position < len(by_source[source]):
                selected.append(by_source[source][position])
                source_counts[source] += 1
                added_any = True

                if len(selected) >= max_total:
                    break

        # If no topics were added this round, we're done (all sources exhausted)
        if not added_any:
            break

        # Move to next position for next round
        position += 1

    return selected


class Command(BaseCommand):
    help = 'Collect and analyze trending topics from multiple sources'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-posts-per-category',
            type=int,
            default=1000,
            help='Maximum posts to keep per category after clustering (default: 1000)'
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

        # Step 1: Load all plugins (static and dynamic from database)
        self.stdout.write('⚙️  Loading collector plugins...')
        try:
            from trend_agent.ingestion.manager import DefaultPluginManager

            plugin_manager = DefaultPluginManager()
            await plugin_manager.load_plugins()
            self.stdout.write('   ✅ Plugins loaded successfully')

            # Refresh the collector registry to include newly loaded dynamic plugins
            from trend_agent.collectors import auto_discover_collectors
            auto_discover_collectors()

        except Exception as e:
            self.stdout.write(f'   ⚠️  Failed to load plugins: {e}')

        # Step 2: Collect from all sources
        self.stdout.write('🔍 Collecting trending topics...')

        # Get all registered collectors
        collectors = get_all_collectors()
        self.stdout.write(f'   Using {len(collectors)} collectors: {", ".join(collectors.keys())}')

        # Execute all collector fetch functions in parallel
        sources = [collector() for collector in collectors.values()]
        results = await asyncio.gather(*sources, return_exceptions=True)

        # Collect topics, logging any collectors that failed
        raw_topics = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                collector_name = list(collectors.keys())[idx]
                self.stdout.write(f'   ⚠️  Collector \'{collector_name}\' failed: {result}')
            else:
                raw_topics.extend(result)

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
            # Use threshold of 0.88 (88% similarity) to remove duplicates while preserving topically-similar distinct posts
            deduplicated_cluster = deduplicate(cluster, threshold=0.88, debug=False)
            self.stdout.write(f'   {cat_name}: {len(cluster)} posts → {len(deduplicated_cluster)} after dedup')

            # Rank topics in this cluster by engagement
            ranked = rank_topics(deduplicated_cluster)

            # Apply source diversity limiting if enabled
            if is_source_diversity_enabled():
                max_pct = get_max_percentage_per_source()
                selected = apply_source_diversity_limit(ranked, max_posts_per_category, max_pct)
                self.stdout.write(f'   {cat_name}: applied source diversity limit ({int(max_pct*100)}% per source)')
            else:
                # No diversity limiting - use simple top N selection
                selected = ranked[:max_posts_per_category]

            if selected:  # Only keep non-empty clusters
                selected_clusters.append(selected)
                selected_category_names.append(cat_name)
                total_selected += len(selected)

                # Show source distribution for this category
                source_counts = {}
                for topic in selected:
                    source_counts[topic.source] = source_counts.get(topic.source, 0) + 1
                source_dist = ', '.join([f'{src}: {cnt}' for src, cnt in sorted(source_counts.items())])
                self.stdout.write(f'   {cat_name}: selected {len(selected)} posts ({source_dist})')

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
        BATCH_SIZE = 5  # Process 5 topics per API call (reduced for full-length rewrites)
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

        # Step 8.5: Ensure all summaries are in English (backup translation)
        self.stdout.write('🌐 Ensuring all summaries are in English...')
        non_english_count = 0
        translated_count = 0

        # Import translation manager
        try:
            from trends_viewer.views import get_translation_manager
            translation_manager = get_translation_manager()
        except Exception as e:
            self.stdout.write(f'   ⚠️  Translation manager not available: {e}')
            translation_manager = None

        for topic in selected_topics:
            # Check if topic language is not English or if summaries contain non-ASCII (likely non-English)
            is_non_english = topic.language != 'en'

            # Also check if the title_summary or full_summary contains non-ASCII characters
            # This catches cases where the LLM didn't translate despite instructions
            has_non_ascii_summary = any(ord(char) > 127 for char in (topic.title_summary or ''))
            has_non_ascii_full = any(ord(char) > 127 for char in (topic.full_summary or ''))

            if is_non_english or has_non_ascii_summary or has_non_ascii_full:
                non_english_count += 1

                # Try to translate if translation manager is available
                if translation_manager:
                    try:
                        # Translate title_summary if it has non-English content
                        if has_non_ascii_summary or is_non_english:
                            translated_title = await translation_manager.translate(
                                topic.title_summary or topic.title,
                                target_language='en',
                                source_language=topic.language if topic.language != 'en' else 'auto'
                            )
                            if translated_title:
                                topic.title_summary = translated_title
                                translated_count += 1

                        # Translate full_summary if it has non-English content
                        if has_non_ascii_full or is_non_english:
                            translated_full = await translation_manager.translate(
                                topic.full_summary or topic.description or '',
                                target_language='en',
                                source_language=topic.language if topic.language != 'en' else 'auto'
                            )
                            if translated_full:
                                topic.full_summary = translated_full

                        # Update language to 'en' since we've translated
                        topic.language = 'en'

                    except Exception as e:
                        self.stdout.write(f'   ⚠️  Translation failed for topic: {str(e)}')
                        # Keep original summaries if translation fails
                else:
                    self.stdout.write(f'   ℹ️  Skipping translation (manager unavailable), relying on LLM translation')

        if non_english_count > 0:
            self.stdout.write(f'   Found {non_english_count} non-English topics')
            if translated_count > 0:
                self.stdout.write(f'   ✅ Translated {translated_count} summaries to English via backup translation')
            else:
                self.stdout.write(f'   ℹ️  Relying on LLM translation (no backup translation needed)')

        # Step 9: Save topics to database
        self.stdout.write('💾 Saving topics to database...')
        saved_topics = []
        for topic in selected_topics:
            # Handle both Pydantic models and dict-like access for metrics
            if hasattr(topic.metrics, 'upvotes'):
                upvotes = topic.metrics.upvotes or 0
                comments = topic.metrics.comments or 0
                score = topic.metrics.score or 0
            else:
                upvotes = topic.metrics.get('upvotes', 0)
                comments = topic.metrics.get('comments', 0)
                score = topic.metrics.get('score', 0)

            # RawItem has published_at, not timestamp
            timestamp = getattr(topic, 'published_at', None) or getattr(topic, 'timestamp', None)

            # Get source string and display name
            source_str = str(topic.source) if hasattr(topic.source, 'value') else topic.source
            source_name = await sync_to_async(get_source_display_name)(source_str)

            db_topic = await sync_to_async(CollectedTopic.objects.create)(
                collection_run=collection_run,
                title=topic.title,
                description=topic.description or "",
                source=source_str,
                source_name=source_name,
                url=str(topic.url),
                timestamp=timestamp,
                upvotes=upvotes,
                comments=comments,
                score=score,
                language=topic.language,
                content=topic.content or "",
                title_summary=topic.title_summary or topic.title,
                full_summary=topic.full_summary or "",
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

            # Calculate cluster score - handle Pydantic models
            score = 0
            for t in topic_cluster:
                if hasattr(t.metrics, 'upvotes'):
                    score += (t.metrics.upvotes or 0) + (t.metrics.comments or 0) + (t.metrics.score or 0)
                else:
                    score += t.metrics.get('upvotes', 0) + t.metrics.get('comments', 0) + t.metrics.get('score', 0)

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
