from django.apps import AppConfig


class TrendsViewerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'trends_viewer'
    verbose_name = 'Trends Viewer'

    def ready(self):
        """Import signals when the app is ready."""
        import trends_viewer.signals  # noqa: F401
