from django.contrib import admin
from .models import CollectionRun, CollectedTopic, TrendCluster


@admin.register(CollectionRun)
class CollectionRunAdmin(admin.ModelAdmin):
    list_display = ['id', 'timestamp', 'status', 'topics_count', 'clusters_count', 'duration_seconds']
    list_filter = ['status', 'timestamp']
    search_fields = ['id']
    readonly_fields = ['timestamp']


@admin.register(CollectedTopic)
class CollectedTopicAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'source', 'timestamp', 'upvotes', 'comments', 'score', 'collection_run']
    list_filter = ['source', 'timestamp', 'collection_run']
    search_fields = ['title', 'description']
    readonly_fields = ['timestamp']


@admin.register(TrendCluster)
class TrendClusterAdmin(admin.ModelAdmin):
    list_display = ['id', 'rank', 'title', 'score', 'collection_run', 'created_at']
    list_filter = ['collection_run', 'created_at']
    search_fields = ['title', 'summary']
    readonly_fields = ['created_at']
    ordering = ['collection_run', 'rank']
