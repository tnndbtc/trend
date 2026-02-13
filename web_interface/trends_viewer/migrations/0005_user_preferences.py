# Generated migration for UserPreference models (Phase 2)
# Run this migration with: python manage.py migrate

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('trends_viewer', '0004_crawlersource'),
    ]

    operations = [
        # UserPreference model
        migrations.CreateModel(
            name='UserPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text="Profile name (e.g., 'Work', 'Personal', 'AI Research')", max_length=100)),
                ('description', models.TextField(blank=True, help_text='Optional description of this preference profile')),
                ('is_default', models.BooleanField(default=False, help_text="Whether this is the user's default profile")),
                ('sources', models.JSONField(default=list, help_text='List of preferred data sources')),
                ('languages', models.JSONField(default=list, help_text='List of preferred languages')),
                ('categories', models.JSONField(blank=True, default=list, help_text='List of preferred categories (future use)')),
                ('time_range', models.CharField(choices=[('24h', 'Last 24 hours'), ('7d', 'Last 7 days'), ('30d', 'Last 30 days'), ('all', 'All time'), ('custom', 'Custom range')], default='7d', help_text='Default time range for articles', max_length=20)),
                ('custom_start_date', models.DateTimeField(blank=True, help_text="Custom start date (if time_range='custom')", null=True)),
                ('custom_end_date', models.DateTimeField(blank=True, help_text="Custom end date (if time_range='custom')", null=True)),
                ('keywords_include', models.JSONField(default=list, help_text='Keywords to include (OR logic)')),
                ('keywords_exclude', models.JSONField(default=list, help_text='Keywords to exclude (AND logic)')),
                ('min_upvotes', models.IntegerField(default=0, help_text='Minimum upvotes for articles')),
                ('min_comments', models.IntegerField(default=0, help_text='Minimum comments for articles')),
                ('min_score', models.IntegerField(default=0, help_text='Minimum score for articles')),
                ('sort_by', models.CharField(choices=[('timestamp', 'Time'), ('upvotes', 'Upvotes'), ('comments', 'Comments'), ('score', 'Score')], default='timestamp', help_text='Default sort field', max_length=20)),
                ('sort_order', models.CharField(choices=[('asc', 'Ascending'), ('desc', 'Descending')], default='desc', help_text='Default sort order', max_length=4)),
                ('items_per_page', models.IntegerField(default=50, help_text='Number of items per page')),
                ('view_mode', models.CharField(choices=[('trends', 'Trend Clusters'), ('topics', 'Individual Topics')], default='trends', help_text='Default view mode', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_used', models.DateTimeField(default=django.utils.timezone.now, help_text='When this profile was last activated')),
                ('user', models.ForeignKey(help_text='User who owns this preference profile', on_delete=django.db.models.deletion.CASCADE, related_name='preferences', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User Preference Profile',
                'verbose_name_plural': 'User Preference Profiles',
                'ordering': ['-is_default', '-last_used'],
                'unique_together': {('user', 'name')},
            },
        ),

        # UserPreferenceHistory model
        migrations.CreateModel(
            name='UserPreferenceHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('created', 'Created'), ('updated', 'Updated'), ('deleted', 'Deleted'), ('activated', 'Activated')], max_length=20)),
                ('preferences_snapshot', models.JSONField(help_text='Snapshot of preference values')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=500)),
                ('profile', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='history', to='trends_viewer.userpreference')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='preference_history', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Preference History Entry',
                'verbose_name_plural': 'Preference History',
                'ordering': ['-timestamp'],
            },
        ),

        # UserNotificationPreference model
        migrations.CreateModel(
            name='UserNotificationPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email_enabled', models.BooleanField(default=False, help_text='Enable email notifications')),
                ('email_frequency', models.CharField(choices=[('realtime', 'Real-time (immediate)'), ('hourly', 'Hourly digest'), ('daily', 'Daily digest'), ('weekly', 'Weekly digest')], default='daily', max_length=20)),
                ('push_enabled', models.BooleanField(default=False, help_text='Enable browser push notifications')),
                ('min_trend_score', models.FloatField(default=0.0, help_text='Only notify for trends above this score')),
                ('min_topic_count', models.IntegerField(default=5, help_text='Only notify for trends with at least this many topics')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='notification_preferences', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Notification Preference',
                'verbose_name_plural': 'Notification Preferences',
            },
        ),
    ]
