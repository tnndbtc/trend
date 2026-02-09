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

print(f'Collection Run #{run.id}\n')

# Get first topic
topic = CollectedTopic.objects.filter(collection_run=run).first()

print(f"Topic Title: {topic.title}")
print(f"Topic URL: {topic.url}")
print(f"\nTitle Summary: {topic.title_summary if topic.title_summary else 'EMPTY'}")
print(f"Title Summary Length: {len(topic.title_summary) if topic.title_summary else 0}")
print(f"\nFull Summary: {topic.full_summary[:200] if topic.full_summary else 'EMPTY'}...")
print(f"Full Summary Length: {len(topic.full_summary) if topic.full_summary else 0}")
print(f"\nContent: {topic.content[:200] if topic.content else 'EMPTY'}...")
print(f"Content Length: {len(topic.content) if topic.content else 0}")
print(f"\nDescription: {topic.description[:200] if topic.description else 'EMPTY'}...")
print(f"Description Length: {len(topic.description) if topic.description else 0}")
