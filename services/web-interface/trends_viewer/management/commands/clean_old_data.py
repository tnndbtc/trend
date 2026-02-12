from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from trends_viewer.models import CollectionRun


class Command(BaseCommand):
    help = 'Clean old collection data to free up disk space'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Keep data from the last N days (default: 30). Use 0 to delete everything.'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']

        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('  Clean Old Data'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write('')

        # Get all runs
        all_runs = CollectionRun.objects.all().order_by('-timestamp')
        total_runs = all_runs.count()

        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)

        # Find runs to delete (purely date-based, no exceptions)
        runs_to_delete = CollectionRun.objects.filter(timestamp__lt=cutoff_date)

        delete_count = runs_to_delete.count()
        keep_count = total_runs - delete_count

        self.stdout.write(f'📊 Current Status:')
        self.stdout.write(f'   Total collection runs: {total_runs}')
        if days == 0:
            self.stdout.write(f'   Cutoff date: {cutoff_date.strftime("%Y-%m-%d %H:%M")} (NOW)')
            self.stdout.write(f'   Retention policy: DELETE EVERYTHING')
        else:
            self.stdout.write(f'   Cutoff date: {cutoff_date.strftime("%Y-%m-%d %H:%M")}')
            self.stdout.write(f'   Retention policy: Keep only last {days} day(s)')
        self.stdout.write('')

        if delete_count == 0:
            self.stdout.write(self.style.SUCCESS('✅ No old data to clean!'))
            self.stdout.write(f'   All {total_runs} runs are within retention period.')
            return

        # Calculate affected data
        topics_count = sum(run.topics_count for run in runs_to_delete)
        clusters_count = sum(run.clusters_count for run in runs_to_delete)

        self.stdout.write(f'🗑️  Data to be deleted:')
        self.stdout.write(f'   Collection runs: {delete_count}')
        self.stdout.write(f'   Topics: {topics_count}')
        self.stdout.write(f'   Clusters: {clusters_count}')
        self.stdout.write('')
        self.stdout.write(f'✅ Data to keep:')
        self.stdout.write(f'   Collection runs: {keep_count}')
        self.stdout.write('')

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No data will be deleted'))
            self.stdout.write('')
            self.stdout.write('Runs that would be deleted:')
            for run in runs_to_delete[:10]:  # Show first 10
                self.stdout.write(f'   - Run #{run.id}: {run.timestamp.strftime("%Y-%m-%d %H:%M")} '
                                f'({run.topics_count} topics, {run.clusters_count} clusters)')
            if delete_count > 10:
                self.stdout.write(f'   ... and {delete_count - 10} more')
            return

        # Perform deletion
        self.stdout.write(self.style.WARNING('⚠️  Deleting old data...'))

        # Delete runs (CASCADE will delete related topics and clusters)
        deleted_info = runs_to_delete.delete()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('✅ Cleanup Complete!'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write('')
        self.stdout.write(f'Deleted:')
        self.stdout.write(f'   {deleted_info[1].get("trends_viewer.CollectionRun", 0)} collection runs')
        self.stdout.write(f'   {deleted_info[1].get("trends_viewer.CollectedTopic", 0)} topics')
        self.stdout.write(f'   {deleted_info[1].get("trends_viewer.TrendCluster", 0)} clusters')
        self.stdout.write('')
        self.stdout.write(f'Remaining: {keep_count} collection runs')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('💡 Tip: Run "docker-compose exec web python manage.py clean_old_data --dry-run" to preview before deleting'))
