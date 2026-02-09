#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app/web_interface')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web_interface.settings')
django.setup()

from trends_viewer.models import CollectedTopic, CollectionRun
from collections import Counter

# Get latest run
run = CollectionRun.objects.latest('timestamp')

print(f'Collection Run #{run.id}')
print(f'Total Topics: {run.topics_count}\n')

# Get all topics
topics = CollectedTopic.objects.filter(collection_run=run)

# Count by source
source_counts = Counter(topic.source for topic in topics)

print('Topics by Source:')
for source, count in sorted(source_counts.items()):
    print(f'  {source}: {count} posts')

print(f'\nTotal: {sum(source_counts.values())} posts')

print('\nDetailed breakdown:')
for source in sorted(source_counts.keys()):
    print(f'\n{source.upper()}:')
    source_topics = topics.filter(source=source).order_by('-upvotes', '-comments', '-score')
    for idx, topic in enumerate(source_topics, 1):
        print(f'  {idx}. {topic.title[:60]}... (score: {topic.upvotes + topic.comments + topic.score})')
