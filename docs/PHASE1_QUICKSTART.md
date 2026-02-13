# Phase 1 Quick Start Guide

## Getting Started with Session-Based Preferences

This guide will help you test and use the new preference-based filtering system.

## Prerequisites

1. Django web server running
2. Database populated with some CollectedTopic records
3. At least one completed CollectionRun

## Setup Steps

### 1. Run Migrations (if needed)

```bash
cd web_interface
python manage.py migrate
```

### 2. Start Development Server

```bash
python manage.py runserver
```

### 3. Access the Application

Open your browser and navigate to:
- **Dashboard**: `http://localhost:8000/`
- **My Feed (Filtered Trends)**: `http://localhost:8000/filtered/trends/`
- **My Feed (Filtered Topics)**: `http://localhost:8000/filtered/topics/`

## Using the Filter Interface

### Step-by-Step Example

1. **Navigate to "🔍 My Feed"** from the navigation bar

2. **Set Your Interests**:
   - **Sources**: Select "reddit" and "hackernews" (hold Ctrl/Cmd)
   - **Languages**: Select "English"
   - **Time Range**: Choose "Last 7 days"
   - **Include Keywords**: Enter "AI, machine learning"
   - **Min Upvotes**: Set to 10

3. **Apply Filters**: Click the "🔍 Apply Filters" button

4. **Review Results**:
   - Articles are filtered from existing database (not re-crawled)
   - Only articles matching ALL your criteria are shown
   - Navigate through pages using pagination

5. **Try Preview**: Click "👁️ Preview Results" to see how many articles match without applying

6. **Reset**: Click "🔄 Reset All" to clear all filters

## Testing the System

### Automated Tests

Run the test suite:

```bash
cd web_interface
python manage.py test trends_viewer.tests_preferences
```

### Manual Testing Scenarios

#### Scenario 1: Source Filtering
1. Go to `/filtered/topics/`
2. Select only "reddit" in Sources
3. Click Apply Filters
4. ✅ Verify: All displayed topics have source = "reddit"

#### Scenario 2: Time Range
1. Set time range to "Last 24 hours"
2. Click Apply Filters
3. ✅ Verify: All topics are from the last 24 hours

#### Scenario 3: Keyword Filtering
1. Set Include Keywords: "python"
2. Click Apply Filters
3. ✅ Verify: All topics contain "python" in title or description

#### Scenario 4: Multiple Filters
1. Sources: reddit, hackernews
2. Min Upvotes: 50
3. Time Range: Last 7 days
4. Click Apply Filters
5. ✅ Verify: Results match all criteria

#### Scenario 5: Session Persistence
1. Set some filters
2. Click Apply Filters
3. Navigate to another page
4. Return to `/filtered/topics/`
5. ✅ Verify: Filters are still active (stored in session)

#### Scenario 6: Reset Functionality
1. Set multiple filters
2. Click "Reset All"
3. ✅ Verify: All filters return to defaults

## Verifying Data Flow

### Check Database Queries

The filter system generates efficient SQL queries. Example:

```sql
SELECT * FROM trends_viewer_collectedtopic
WHERE source IN ('reddit', 'hackernews')
  AND language = 'en'
  AND upvotes >= 10
  AND timestamp >= '2024-01-01 00:00:00'
ORDER BY timestamp DESC
LIMIT 50;
```

### Verify No Re-Crawling

1. Note the timestamp of latest CollectedTopic
2. Apply various filters
3. ✅ Verify: No new CollectedTopic records are created
4. ✅ Verify: Filtering happens instantly (database query, not web crawl)

## Troubleshooting

### Issue: No topics displayed
**Solution**:
- Check if database has CollectedTopic records
- Run: `python manage.py shell` then:
  ```python
  from trends_viewer.models import CollectedTopic
  print(CollectedTopic.objects.count())
  ```
- If 0, run the collection command to populate data

### Issue: Filters don't persist
**Solution**:
- Ensure Django sessions are enabled
- Check `SESSION_ENGINE` in settings.py
- Clear browser cookies and try again

### Issue: Preview shows wrong count
**Solution**:
- Check browser console for JavaScript errors
- Verify CSRF token is present in cookies
- Test AJAX endpoint directly:
  ```bash
  curl "http://localhost:8000/api/preferences/preview/?sources=reddit"
  ```

### Issue: Template not found
**Solution**:
- Verify template directory structure:
  ```
  web_interface/
    trends_viewer/
      templates/
        trends_viewer/
          components/
            filter_panel.html
          filtered_topic_list.html
          filtered_trend_list.html
  ```

## Performance Tips

### For Large Datasets

1. **Add Database Indexes**:
   ```python
   # In models.py
   class CollectedTopic(models.Model):
       class Meta:
           indexes = [
               models.Index(fields=['source', 'timestamp']),
               models.Index(fields=['language', 'timestamp']),
               models.Index(fields=['upvotes']),
           ]
   ```

2. **Use Pagination**: Default is 50 items/page for topics, adjust if needed

3. **Enable Query Caching**: Use Django's cache framework for filter options:
   ```python
   # In views_preferences.py
   from django.core.cache import cache

   sources = cache.get_or_set('available_sources', get_available_sources, 300)
   ```

## Next Steps: Phase 2

Once Phase 1 is working, proceed to Phase 2:
- User authentication system
- Persistent preferences in database
- Multiple saved preference profiles
- Cross-device synchronization

See `PHASE2_IMPLEMENTATION.md` for details.

## FAQ

**Q: Do I need to be logged in?**
A: No, Phase 1 uses session-based storage. No login required.

**Q: Can I save multiple filter profiles?**
A: Not in Phase 1. This feature comes in Phase 2 with user accounts.

**Q: Will my preferences sync across devices?**
A: Not in Phase 1. Session is browser-specific. Phase 2 adds cross-device sync.

**Q: How long do preferences last?**
A: Until you clear browser cookies or session expires (default: 7 days).

**Q: Can I filter by custom categories?**
A: The infrastructure is there, but categories need to be set during data collection. This can be added to the ingestion pipeline.

## Support

For issues:
1. Check Django logs: `python manage.py runserver` output
2. Check browser console for JavaScript errors
3. Review test results: `python manage.py test trends_viewer.tests_preferences -v 2`
4. Check database has data: Visit Django admin at `/admin/`
