from django.db import models
from django.utils import timezone


class CollectionRun(models.Model):
    """Represents a single execution of the trend collection pipeline."""
    timestamp = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=[
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='running')
    topics_count = models.IntegerField(default=0)
    clusters_count = models.IntegerField(default=0)
    duration_seconds = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Collection Run {self.id} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class CollectedTopic(models.Model):
    """Represents a single topic collected from a data source."""
    collection_run = models.ForeignKey(CollectionRun, on_delete=models.CASCADE, related_name='topics')
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    source = models.CharField(max_length=50, choices=[
        ('reddit', 'Reddit'),
        ('hackernews', 'Hacker News'),
        ('google_news', 'Google News'),
    ])
    url = models.URLField(max_length=1000)
    timestamp = models.DateTimeField()

    # Metrics stored as JSON-like fields
    upvotes = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    score = models.IntegerField(default=0)

    cluster = models.ForeignKey('TrendCluster', on_delete=models.SET_NULL, null=True, blank=True, related_name='topics')

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.source}: {self.title[:50]}"


class TrendCluster(models.Model):
    """Represents a cluster of related topics identified as a trend."""
    collection_run = models.ForeignKey(CollectionRun, on_delete=models.CASCADE, related_name='clusters')
    rank = models.IntegerField()
    title = models.CharField(max_length=500)
    summary = models.TextField()
    score = models.FloatField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['rank']
        unique_together = ['collection_run', 'rank']

    def __str__(self):
        return f"Trend #{self.rank}: {self.title}"

    def get_sources(self):
        """Get unique sources for topics in this cluster."""
        return self.topics.values_list('source', flat=True).distinct()

    def get_topic_count(self):
        """Get count of topics in this cluster."""
        return self.topics.count()
