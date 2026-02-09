#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app/web_interface')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_interface.settings')
django.setup()

from trends_viewer.models import CollectedTopic, TrendCluster, CollectionRun

# Get latest run
run = CollectionRun.objects.latest('timestamp')

print(f'Collection Run #{run.id}')
print(f'Total Topics: {run.topics_count}')
print(f'Total Clusters: {run.clusters_count}\n')

topics = CollectedTopic.objects.filter(collection_run=run).order_by('cluster__rank', 'id')

for idx, topic in enumerate(topics, 1):
    cluster_num = topic.cluster.rank if topic.cluster else 'N/A'
    print(f'{idx}. #{cluster_num} - {topic.title[:50]}...')
    print(f'   Title Summary: {"✓" if topic.title_summary else "✗"} ({len(topic.title_summary or "")} chars)')
    print(f'   Full Summary:  {"✓" if topic.full_summary else "✗"} ({len(topic.full_summary or "")} chars)')
    print(f'   Content:       {"✓" if topic.content else "✗"} ({len(topic.content or "")} chars)')
    print()

# Summary
topics_with_summaries = topics.filter(title_summary__isnull=False).exclude(title_summary='').count()
topics_with_content = topics.filter(content__isnull=False).exclude(content='').count()

print(f'Summary:')
print(f'  Topics with title_summary: {topics_with_summaries}/{run.topics_count}')
print(f'  Topics with full_summary: {topics.filter(full_summary__isnull=False).exclude(full_summary="").count()}/{run.topics_count}')
print(f'  Topics with content: {topics_with_content}/{run.topics_count}')
