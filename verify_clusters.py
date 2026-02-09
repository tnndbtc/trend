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

# Get all clusters
clusters = TrendCluster.objects.filter(collection_run=run).order_by('rank')

print('Clusters and their topics:')
for cluster in clusters:
    print(f'\n#{cluster.rank} - {cluster.title[:50]}...')
    topics = cluster.topics.all()
    print(f'  Topic count: {topics.count()}')
    for topic in topics:
        print(f'    - [{topic.source}] {topic.title[:60]}...')

# Check for topics without cluster
orphaned = CollectedTopic.objects.filter(collection_run=run, cluster__isnull=True)
if orphaned.exists():
    print(f'\n⚠️  {orphaned.count()} topics without cluster:')
    for topic in orphaned:
        print(f'  - [{topic.source}] {topic.title[:60]}...')
