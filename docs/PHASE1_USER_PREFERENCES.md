# Phase 1: Session-Based User Preferences

## Overview

Phase 1 implements a **session-based preference system** that allows users to filter articles by their interests **without requiring authentication**. Preferences are stored in Django sessions and applied to database queries - articles are **not re-crawled**, only filtered from existing persisted data.

## Features

### 1. Multi-Criteria Filtering

Users can filter articles by:

- **📰 Data Sources**: Select specific sources (Reddit, HackerNews, etc.)
- **🌐 Languages**: Filter by language (English, Chinese, Japanese, etc.)
- **📅 Time Ranges**: View articles from specific time periods
  - Last 24 hours
  - Last 7 days (default)
  - Last 30 days
  - All time
  - Custom date range
- **✅ Include Keywords**: Only show articles containing specific keywords
- **❌ Exclude Keywords**: Hide articles containing specific keywords
- **⬆️ Minimum Engagement**: Filter by minimum upvotes, comments, or score
- **📊 Sorting**: Sort by timestamp, upvotes, comments, or score (ascending/descending)

### 2. Session-Based Storage

- Preferences stored in Django session (no database writes)
- Persists across page visits within the same session
- No login required
- Works immediately without setup

### 3. Database Query Optimization

- All filtering happens at the database level (Django ORM)
- **No re-crawling** - filters existing CollectedTopic records
- Efficient pagination for large result sets
- Real-time preview of filter results

## Usage

### Accessing Filtered Views

1. **Navigate to "🔍 My Feed"** in the navigation bar
2. This opens `/filtered/trends/` or `/filtered/topics/`

### Setting Preferences

1. **Expand Filter Panel** (visible at top of filtered pages)
2. **Select Your Interests**:
   - Hold Ctrl/Cmd to multi-select sources or languages
   - Enter comma-separated keywords
   - Set minimum engagement thresholds
   - Choose time range
3. **Apply Filters** - Click "🔍 Apply Filters" button
4. **Preview Results** (optional) - Click "👁️ Preview Results" to see count without applying
5. **Reset Filters** - Click "🔄 Reset All" to return to defaults

### URL Examples

```
# Filtered trends view
/filtered/trends/

# Filtered topics view
/filtered/topics/

# With applied filters (example)
/filtered/topics/?apply_filters=1&sources=reddit&sources=hackernews&languages=en&time_range=7d&min_upvotes=10
```

## Technical Architecture

### Components

1. **PreferenceManager** (`preferences.py`)
   - Manages session-based preference storage
   - Converts preferences to Django ORM filter parameters
   - Handles keyword filtering with Q objects

2. **Filtered Views** (`views_preferences.py`)
   - `FilteredTopicListView`: Shows individual topics filtered by preferences
   - `FilteredTrendListView`: Shows trend clusters with filtered topics

3. **Filter Panel Component** (`templates/components/filter_panel.html`)
   - Reusable UI component for filter controls
   - JavaScript for dynamic behavior (collapse/expand, custom date range)

4. **AJAX Endpoints**
   - `/api/preferences/update/`: Update preferences without page reload
   - `/api/preferences/reset/`: Reset to defaults
   - `/api/preferences/preview/`: Preview filter results

### Data Flow

```
User selects filters
    ↓
Preferences stored in session (PreferenceManager)
    ↓
View retrieves preferences from session
    ↓
Preferences converted to Django ORM filters
    ↓
Database query with filters (CollectedTopic.objects.filter(...))
    ↓
Results rendered with pagination
```

### Database Queries

Example generated queries:

```python
# User selects: sources=[reddit, hackernews], languages=[en], min_upvotes=10, time_range=7d

CollectedTopic.objects.filter(
    source__in=['reddit', 'hackernews'],
    language__in=['en'],
    upvotes__gte=10,
    timestamp__gte=datetime.now() - timedelta(days=7)
).order_by('-timestamp')
```

## Performance Considerations

1. **No Re-Crawling**: All data comes from existing database records
2. **Indexed Queries**: Ensure database indexes on:
   - `source`
   - `language`
   - `timestamp`
   - `upvotes`, `comments`, `score`
3. **Pagination**: Default 50 items per page (topics), 20 per page (trends)
4. **Session Storage**: Minimal overhead, no database writes for preferences

## Limitations (Phase 1)

1. **Not Persistent Across Devices**: Preferences stored in browser session
2. **Lost on Logout/Clear Cookies**: Session-based, not saved to database
3. **No User Profiles**: Anonymous filtering, no personalization tracking
4. **No Preference History**: Can't save multiple filter "profiles"

→ **These limitations are addressed in Phase 2** (User Accounts & Persistent Preferences)

## Testing Phase 1

### Manual Testing Checklist

1. ✅ Open `/filtered/topics/` or `/filtered/trends/`
2. ✅ Select multiple sources (hold Ctrl/Cmd)
3. ✅ Choose a language
4. ✅ Set time range to "Last 7 days"
5. ✅ Add include keyword (e.g., "AI")
6. ✅ Add exclude keyword (e.g., "spam")
7. ✅ Set min upvotes to 10
8. ✅ Click "Apply Filters"
9. ✅ Verify results match filters
10. ✅ Click "Preview Results" to see count
11. ✅ Navigate to next page (pagination)
12. ✅ Click "Reset All" - verify defaults restored
13. ✅ Close browser, reopen - verify preferences persist in session
14. ✅ Clear cookies - verify preferences reset

### Automated Testing

```python
# Test preference manager
from web_interface.trends_viewer.preferences import PreferenceManager

# Test filtering
from web_interface.trends_viewer.views_preferences import FilteredTopicListView

# Run tests
python manage.py test web_interface.trends_viewer.tests
```

## Configuration

### Session Settings

In `settings.py`:

```python
# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # or 'cached_db' for better performance
SESSION_COOKIE_AGE = 86400 * 7  # 7 days
SESSION_SAVE_EVERY_REQUEST = False  # Only save when modified
```

### Default Preferences

Edit in `preferences.py`:

```python
DEFAULT_PREFERENCES = {
    'sources': [],
    'languages': [],
    'time_range': '7d',  # Change default time range
    'min_upvotes': 0,
    # ...
}
```

## Next Steps: Phase 2

Phase 2 will add:

1. **User Authentication** (Django auth system)
2. **UserPreference Model** (persistent storage in database)
3. **Multiple Preference Profiles** (save/load/delete)
4. **User Dashboard** with saved preferences
5. **Cross-Device Sync** (login from any device)
6. **Preference History** tracking

---

## Quick Reference

| Feature | URL | Description |
|---------|-----|-------------|
| Filtered Trends | `/filtered/trends/` | Trends with filtered topics |
| Filtered Topics | `/filtered/topics/` | Individual topics filtered |
| Update Preferences (AJAX) | `/api/preferences/update/` | POST to update |
| Reset Preferences (AJAX) | `/api/preferences/reset/` | POST to reset |
| Preview Results (AJAX) | `/api/preferences/preview/` | GET with params |

## Support

For issues or questions:
- Check Django session is enabled in settings
- Verify database contains CollectedTopic records
- Check browser console for JavaScript errors
- Review server logs for Django errors
