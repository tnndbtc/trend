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
print(f'Status: {run.status}')
print(f'Total Topics (recorded): {run.topics_count}')
print(f'Total Clusters (recorded): {run.clusters_count}')
print(f'Actual Topic Count: {CollectedTopic.objects.filter(collection_run=run).count()}')
print(f'Actual Cluster Count: {TrendCluster.objects.filter(collection_run=run).count()}')
print('\nTopics per cluster:')

for cluster in TrendCluster.objects.filter(collection_run=run).order_by('rank'):
    print(f'  Cluster #{cluster.rank}: {cluster.topics.count()} posts - "{cluster.title[:60]}"')
