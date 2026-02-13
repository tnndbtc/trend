# Complete User Preference System - Implementation Guide

## 🎉 Overview

This document describes the **complete two-phase implementation** of the user preference system for the AI Trend Intelligence platform.

### What Was Implemented

✅ **Phase 1**: Session-based preference filtering (no login required)
✅ **Phase 2**: User accounts with persistent preference profiles

---

## Phase 1: Session-Based Preferences

### Features
- Multi-criteria filtering (sources, languages, time ranges, keywords, metrics)
- Real-time filter preview
- Session persistence (browser-based)
- **No re-crawling** - all filtering queries existing database

### Access
- Navigate to **"🔍 My Feed"** in navigation
- URLs: `/filtered/trends/` or `/filtered/topics/`

### Limitations
- Preferences lost when cookies cleared
- No cross-device sync
- No saved profiles

---

## Phase 2: User Accounts & Persistent Preferences

### New Features

#### 1. User Authentication
- **Registration**: Create account at `/register/`
- **Login**: Access account at `/login/`
- **Logout**: Sign out at `/logout/`
- Default preference profile created automatically on registration

#### 2. Preference Profiles
Users can:
- Create multiple named profiles (e.g., "Work", "AI Research", "Weekend Reading")
- Save current filter settings as reusable profiles
- Load saved profiles with one click
- Edit/delete profiles
- Set a default profile (auto-loads on login)
- View preference history

#### 3. Profile Management Dashboard
- Access at `/profile/`
- View all saved profiles
- Manage notification settings
- Track recent activity

#### 4. Quick Profile Actions (in Filter Panel)
- **Load Profile**: Dropdown selector for authenticated users
- **Quick Save**: 💾 button to save current filters instantly
- Profiles automatically sync across devices

#### 5. Notification Preferences (Future-Ready)
- Email notification settings
- Push notification settings
- Min trend score/topic count thresholds

---

## Database Models

### UserPreference
Stores a user's preference profile:
- **Profile Info**: name, description, is_default
- **Filters**: sources, languages, categories
- **Time Settings**: time_range, custom dates
- **Keywords**: include/exclude lists
- **Metrics**: min_upvotes, min_comments, min_score
- **Display**: sort_by, sort_order, items_per_page, view_mode
- **Metadata**: created_at, updated_at, last_used

### UserPreferenceHistory
Tracks changes to preferences:
- action (created/updated/deleted/activated)
- preferences_snapshot (full state at that time)
- timestamp, IP address, user agent

### UserNotificationPreference
Manages notification settings:
- email_enabled, email_frequency
- push_enabled
- min_trend_score, min_topic_count

---

## Installation & Setup

### 1. Run Migrations

```bash
cd web_interface
python manage.py makemigrations
python manage.py migrate
```

### 2. Create Test User (Optional)

```bash
python manage.py createsuperuser
```

### 3. Start Server

```bash
python manage.py runserver
```

### 4. Access Application

Visit `http://localhost:8000/`

---

## Usage Guide

### For Anonymous Users (Phase 1)

1. Go to **"🔍 My Feed"**
2. Set filters (sources, languages, keywords, etc.)
3. Click **"Apply Filters"**
4. Preferences saved in session (until cookies cleared)

### For Authenticated Users (Phase 2)

#### Creating an Account

1. Click **"Sign Up"** in navigation
2. Fill in registration form
3. A default preference profile is created automatically
4. You're logged in and ready to use

#### Saving Preferences

**Method 1: Quick Save (from Filter Panel)**
1. Set your desired filters
2. Click 💾 button in filter panel
3. Enter profile name
4. Profile saved instantly

**Method 2: Save Current (from Profile Dashboard)**
1. Set filters on any filtered view
2. Go to **Profile** → **"💾 Save Current Filters"**
3. Enter name and description
4. Optionally set as default
5. Save

**Method 3: Create from Scratch**
1. Go to **Profile** → **"➕ Create New Profile"**
2. Fill in all preference fields
3. Save

#### Loading Saved Profiles

**Method 1: Quick Load (from Filter Panel)**
1. Use dropdown selector in filter panel header
2. Select profile name
3. Settings load immediately

**Method 2: From Profile Dashboard**
1. Go to **Profile**
2. Click **"▶️ Activate"** on any profile
3. Redirected to filtered view with settings applied

#### Managing Profiles

Go to **Profile** dashboard (`/profile/`):

- **View All Profiles**: See all your saved profiles with metadata
- **Edit**: Click ✏️ to modify profile settings
- **Delete**: Click 🗑️ (cannot delete last profile)
- **Set Default**: Click ⭐ to make it your default
- **View Details**: Expand to see full filter configuration
- **View History**: See recent changes to preferences

#### Setting Default Profile

Your default profile:
- Automatically loads when you log in
- Marked with "(default)" badge
- Only one profile can be default at a time

To set default:
1. Go to Profile dashboard
2. Click ⭐ on desired profile
OR
3. Edit profile and check "Set as my default profile"

---

## API Endpoints

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/register/` | GET/POST | User registration |
| `/login/` | GET/POST | User login |
| `/logout/` | GET | User logout |

### Profile Management
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/profile/` | GET | Profile dashboard |
| `/profile/create/` | GET/POST | Create new profile |
| `/profile/edit/<id>/` | GET/POST | Edit profile |
| `/profile/delete/<id>/` | POST | Delete profile |
| `/profile/activate/<id>/` | GET | Activate profile |
| `/profile/set-default/<id>/` | GET | Set as default |
| `/profile/save-current/` | GET/POST | Save current filters |
| `/profile/notifications/` | GET/POST | Manage notifications |

### AJAX Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/profile/quick-save/` | POST | Quick save current filters |
| `/api/profile/list/` | GET | Get user's profiles (JSON) |
| `/api/preferences/update/` | POST | Update session preferences |
| `/api/preferences/reset/` | POST | Reset session preferences |
| `/api/preferences/preview/` | GET | Preview filter results |

---

## File Structure

```
web_interface/trends_viewer/
├── models.py                           # Original models (CollectedTopic, etc.)
├── models_preferences.py               # NEW: UserPreference models
├── preferences.py                      # NEW: PreferenceManager (Phase 1)
├── views.py                            # Original views
├── views_preferences.py                # NEW: Filtered views (Phase 1)
├── views_auth.py                       # NEW: Auth & profile views (Phase 2)
├── forms.py                            # NEW: Auth & preference forms
├── admin.py                            # UPDATED: Added preference admin
├── urls.py                             # UPDATED: Added all new routes
├── tests_preferences.py                # NEW: Test suite
├── templates/trends_viewer/
│   ├── base.html                       # UPDATED: Added user auth links
│   ├── components/
│   │   └── filter_panel.html           # NEW: Comprehensive filter UI
│   ├── filtered_topic_list.html        # NEW: Filtered topics view
│   ├── filtered_trend_list.html        # NEW: Filtered trends view
│   ├── auth/
│   │   ├── register.html               # NEW: Registration form
│   │   └── login.html                  # NEW: Login form
│   └── profile/
│       ├── dashboard.html              # NEW: Profile management
│       └── save_current.html           # NEW: Save filters form
└── migrations/
    └── 0005_user_preferences.py        # NEW: Database migration

docs/
├── PHASE1_USER_PREFERENCES.md          # Phase 1 documentation
├── PHASE1_QUICKSTART.md                # Phase 1 quick start
└── USER_PREFERENCES_COMPLETE.md        # THIS FILE
```

---

## Key Design Decisions

### 1. Session + Database Hybrid

**Session Storage (Phase 1):**
- Current filter state stored in Django session
- Works for all users (anonymous + authenticated)
- Fast, no database writes

**Database Storage (Phase 2):**
- Named profiles saved to database
- Persistent across devices/sessions
- Can be loaded into session on demand

**Flow:**
1. User adjusts filters → Stored in session
2. User saves profile → Session → Database
3. User loads profile → Database → Session
4. User applies filters → Session → Query database

### 2. No Re-Crawling

**All filtering happens at the database level:**
```python
CollectedTopic.objects.filter(
    source__in=['reddit', 'hackernews'],
    language='en',
    upvotes__gte=10,
    timestamp__gte=last_7_days
).order_by('-timestamp')
```

**Benefits:**
- Instant results
- No API rate limits
- Works offline
- Efficient pagination

### 3. Profile Ownership & Security

- Profiles tied to User via ForeignKey
- Users can only see/edit their own profiles
- @login_required decorators enforce authentication
- History tracks all changes with IP/user agent

### 4. Default Profile Auto-Load

On login:
1. Check for user's default profile
2. Load settings into session automatically
3. User immediately sees their personalized feed

### 5. Flexible Architecture

**Easy to extend:**
- Add new filter types (just update PreferenceManager)
- Add new data sources (automatically appear in filter UI)
- Add categories when ready (already in model)
- Notification system ready for implementation

---

## Testing

### Automated Tests

```bash
cd web_interface
python manage.py test trends_viewer.tests_preferences
```

### Manual Testing Scenarios

#### Phase 1 (Anonymous User)
1. ✅ Open `/filtered/topics/`
2. ✅ Apply filters
3. ✅ Verify results match
4. ✅ Close browser, reopen
5. ✅ Verify filters persist (session)

#### Phase 2 (Authenticated User)
1. ✅ Register new account
2. ✅ Verify default profile created
3. ✅ Set filters and quick save
4. ✅ Load saved profile from dropdown
5. ✅ Create new profile from dashboard
6. ✅ Edit profile
7. ✅ Set profile as default
8. ✅ Logout and login
9. ✅ Verify default profile auto-loads
10. ✅ Delete profile
11. ✅ View preference history

#### Cross-Device Sync
1. ✅ Login on Device A
2. ✅ Create/save profiles
3. ✅ Login on Device B with same account
4. ✅ Verify profiles available
5. ✅ Activate profile on Device B
6. ✅ Verify same settings load

---

## Performance Optimization

### Database Indexes

Add these indexes for optimal performance:

```python
# In models.py
class CollectedTopic(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['source', 'timestamp']),
            models.Index(fields=['language', 'timestamp']),
            models.Index(fields=['upvotes']),
            models.Index(fields=['comments']),
            models.Index(fields=['score']),
        ]
```

Then run:
```bash
python manage.py makemigrations
python manage.py migrate
```

### Caching

Enable caching for filter options:

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### Pagination

Current defaults:
- Topics: 50 per page
- Trends: 20 per page

Adjust in views_preferences.py if needed.

---

## Security Considerations

### 1. CSRF Protection
All POST forms include `{% csrf_token %}`

### 2. Authentication Required
Profile management requires login via `@login_required`

### 3. User Isolation
Users can only access their own profiles (enforced by QuerySets)

### 4. Input Validation
All forms use Django's validation system

### 5. SQL Injection Prevention
Using Django ORM (parameterized queries)

### 6. XSS Prevention
Django auto-escapes template variables

---

## Future Enhancements

### Phase 3 (Potential)
1. **Email Notifications**
   - Send daily/weekly digests
   - Notify when new trends match user interests
   - Already have model ready: `UserNotificationPreference`

2. **Advanced Analytics**
   - Track which profiles are most used
   - Recommend profiles based on behavior
   - Trend prediction based on user interests

3. **Social Features**
   - Share profiles publicly
   - Follow other users' profiles
   - Community-curated preference profiles

4. **AI-Powered Recommendations**
   - Auto-suggest filter adjustments
   - "You might also like..." based on history
   - Smart profile creation from browsing patterns

5. **Mobile App**
   - Push notifications
   - Offline sync
   - Native UI for profile management

---

## Troubleshooting

### Issue: Migrations fail
**Solution:**
```bash
python manage.py migrate --fake trends_viewer zero
python manage.py migrate trends_viewer
```

### Issue: Profiles not loading
**Solution:**
- Check browser console for JavaScript errors
- Verify user is authenticated
- Check network tab for AJAX request failures

### Issue: Filters not persisting
**Solution:**
- Ensure sessions are enabled in settings.py
- Check `SESSION_ENGINE` is configured
- Clear browser cookies and try again

### Issue: Default profile not auto-loading
**Solution:**
- Check `views_auth.py` → `_load_default_preference_to_session()`
- Verify user has a profile with `is_default=True`
- Check server logs for errors

### Issue: Quick save button not working
**Solution:**
- Verify CSRF token is present (check cookies)
- Check `/api/profile/quick-save/` endpoint in network tab
- Ensure user is authenticated

---

## Support & Contribution

### Getting Help
1. Check this documentation
2. Review `PHASE1_QUICKSTART.md` for Phase 1 issues
3. Check Django logs: `python manage.py runserver` output
4. Review browser console for JavaScript errors

### Contributing
1. Add new filter types in `preferences.py`
2. Extend models in `models_preferences.py`
3. Create new templates in `templates/trends_viewer/`
4. Write tests in `tests_preferences.py`

---

## Summary

### ✅ What Works Now

**For All Users:**
- Session-based filtering (no login)
- Multi-criteria filters
- Real-time preview
- Efficient database queries (no re-crawling)

**For Authenticated Users:**
- User accounts (register/login/logout)
- Multiple saved preference profiles
- Quick save/load from filter panel
- Profile management dashboard
- Default profile auto-load
- Preference history tracking
- Cross-device profile sync
- Notification settings (ready for implementation)

### 📊 Statistics

- **Files Created**: 15+
- **Models**: 3 new (UserPreference, UserPreferenceHistory, UserNotificationPreference)
- **Views**: 20+ (authentication + profile management)
- **Templates**: 6+ new HTML files
- **URL Routes**: 15+ new endpoints
- **AJAX Endpoints**: 5
- **Test Coverage**: Comprehensive test suite included

---

## Quick Reference Commands

```bash
# Setup
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser

# Run server
python manage.py runserver

# Run tests
python manage.py test trends_viewer.tests_preferences

# Create migration
python manage.py makemigrations trends_viewer

# Apply migration
python manage.py migrate trends_viewer
```

## Quick Reference URLs

```
# Main
/                                    # Dashboard
/filtered/trends/                    # Filtered trends (Phase 1+2)
/filtered/topics/                    # Filtered topics (Phase 1+2)

# Auth
/register/                           # Sign up
/login/                              # Sign in
/logout/                             # Sign out

# Profile
/profile/                            # Profile dashboard
/profile/create/                     # Create profile
/profile/save-current/               # Save current filters
/profile/activate/<id>/              # Activate profile

# Admin
/admin/                              # Django admin
```

---

**🎉 Implementation Complete! Both Phase 1 and Phase 2 are ready for production use.**
