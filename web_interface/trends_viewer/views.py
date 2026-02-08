from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from .models import CollectionRun, CollectedTopic, TrendCluster


def dashboard(request):
    """Dashboard view showing overview of recent collection runs."""
    recent_runs = CollectionRun.objects.all()[:5]
    latest_run = recent_runs.first() if recent_runs else None

    # Get stats from latest run
    stats = {
        'total_runs': CollectionRun.objects.count(),
        'latest_run': latest_run,
        'recent_runs': recent_runs,
    }

    if latest_run:
        stats['latest_trends'] = TrendCluster.objects.filter(
            collection_run=latest_run
        ).order_by('rank')[:10]

    return render(request, 'trends_viewer/dashboard.html', stats)


class TrendListView(ListView):
    """View for listing all trends from the latest collection run."""
    model = TrendCluster
    template_name = 'trends_viewer/trend_list.html'
    context_object_name = 'trends'
    paginate_by = 20

    def get_queryset(self):
        run_id = self.request.GET.get('run')
        if run_id:
            return TrendCluster.objects.filter(collection_run_id=run_id).order_by('rank')
        # Get latest run's trends
        latest_run = CollectionRun.objects.filter(status='completed').first()
        if latest_run:
            return TrendCluster.objects.filter(collection_run=latest_run).order_by('rank')
        return TrendCluster.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        run_id = self.request.GET.get('run')
        if run_id:
            context['current_run'] = get_object_or_404(CollectionRun, id=run_id)
        else:
            context['current_run'] = CollectionRun.objects.filter(status='completed').first()
        context['all_runs'] = CollectionRun.objects.all()[:10]
        return context


class TrendDetailView(DetailView):
    """View for showing details of a specific trend cluster."""
    model = TrendCluster
    template_name = 'trends_viewer/trend_detail.html'
    context_object_name = 'trend'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['topics'] = self.object.topics.all()
        return context


class TopicListView(ListView):
    """View for listing all collected topics."""
    model = CollectedTopic
    template_name = 'trends_viewer/topic_list.html'
    context_object_name = 'topics'
    paginate_by = 50

    def get_queryset(self):
        queryset = CollectedTopic.objects.all()

        # Filter by source if specified
        source = self.request.GET.get('source')
        if source:
            queryset = queryset.filter(source=source)

        # Filter by run if specified
        run_id = self.request.GET.get('run')
        if run_id:
            queryset = queryset.filter(collection_run_id=run_id)

        return queryset.order_by('-timestamp')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sources'] = ['reddit', 'hackernews', 'google_news']
        context['current_source'] = self.request.GET.get('source', '')
        context['all_runs'] = CollectionRun.objects.all()[:10]
        return context


class CollectionRunListView(ListView):
    """View for listing collection run history."""
    model = CollectionRun
    template_name = 'trends_viewer/collection_run_list.html'
    context_object_name = 'runs'
    paginate_by = 20
    ordering = ['-timestamp']
