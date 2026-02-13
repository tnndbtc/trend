# User Preference Setup Integration

## ✅ Changes Made

The user preference setup has been **fully integrated** into the main `setup.sh` script.

### What Changed

1. **Deleted**: `setup_user_preferences.sh` (standalone script)
2. **Updated**: `setup.sh` with user preference functionality

### New Menu Options

**Option 11: Show All Access URLs** (Updated)
- Now includes user preference URLs:
  - 🔍 My Feed (Filtered Topics)
  - 📈 My Feed (Filtered Trends)
  - 👤 User Profile
  - 🆕 Sign Up
  - 🔑 Login

**Option 14: Setup User Preferences** (New)
- Runs database migrations for UserPreference models
- Shows available features for Phase 1 and Phase 2
- Provides next steps and documentation links

**Option 15: Test User Preferences** (New)
- Comprehensive testing guide for Phase 1 (anonymous users)
- Testing guide for Phase 2 (authenticated users)
- Lists all test URLs
- Shows how to run automated tests

### Command-Line Mode

New commands added:
```bash
# Setup user preferences
./setup.sh setup-prefs

# Show testing guide
./setup.sh test-prefs

# Show help (updated with new commands)
./setup.sh help
```

---

## 🚀 How to Use

### Method 1: Interactive Menu

```bash
./setup.sh

# Select from menu:
# 14) Setup User Preferences (Phase 1 + Phase 2)
# 15) Test User Preferences
```

### Method 2: Direct Commands

```bash
# Setup user preferences
./setup.sh setup-prefs

# Test user preferences
./setup.sh test-prefs

# View all URLs (including preference URLs)
./setup.sh

# Then select option 11
```

---

## 📖 Testing Guide

### Quick Test (Phase 1 - No Login)

1. **Start the web interface** (if not running):
   ```bash
   ./setup.sh
   # Select option 2) Basic Setup (Web Interface Only)
   ```

2. **Setup user preferences**:
   ```bash
   ./setup.sh
   # Select option 14) Setup User Preferences
   ```

3. **Test the functionality**:
   - Open: http://localhost:11800/filtered/topics/
   - Set filters (sources, languages, keywords, etc.)
   - Click "Apply Filters"
   - Verify results are filtered correctly
   - **Articles queried from database, NOT re-crawled!**

### Full Test (Phase 2 - With Login)

1. **Follow Phase 1 setup first**

2. **Create an account**:
   - Visit: http://localhost:11800/register/
   - Fill in registration form
   - Login automatically

3. **Test saved profiles**:
   - Go to http://localhost:11800/filtered/topics/
   - Set your preferred filters
   - Click 💾 button in filter panel
   - Enter profile name → Save
   - Change filters
   - Use dropdown to load saved profile
   - Verify filters are restored

4. **Test profile management**:
   - Visit: http://localhost:11800/profile/
   - View all saved profiles
   - Edit a profile
   - Set a profile as default
   - Delete a profile
   - View preference history

5. **Test cross-device sync**:
   - Login on another browser/device
   - Verify same profiles are available

---

## 🧪 Automated Tests

Run the comprehensive test suite:

```bash
# Using docker-compose
docker-compose exec web python manage.py test trends_viewer.tests_preferences

# Or from setup.sh menu
./setup.sh
# Select option 15) Test User Preferences
# Follow the automated test instructions
```

---

## 📊 All Access URLs

After setup, all these URLs are available:

### Main Application
- **Django Web**: http://localhost:11800
- **Django Admin**: http://localhost:11800/admin

### User Preferences (Phase 1 + Phase 2)
- **🔍 Filtered Topics**: http://localhost:11800/filtered/topics/
- **📈 Filtered Trends**: http://localhost:11800/filtered/trends/
- **👤 User Profile**: http://localhost:11800/profile/
- **🆕 Sign Up**: http://localhost:11800/register/
- **🔑 Login**: http://localhost:11800/login/

To see all URLs with local IP addresses:
```bash
./setup.sh
# Select option 11) Show All Access URLs
```

---

## 📚 Documentation

Complete guides available:

- **`docs/USER_PREFERENCES_COMPLETE.md`** - Complete system documentation
- **`docs/PHASE1_USER_PREFERENCES.md`** - Phase 1 detailed docs
- **`docs/PHASE1_QUICKSTART.md`** - Phase 1 quick start guide
- **`README_USER_PREFERENCES.md`** - Quick README
- **`IMPLEMENTATION_SUMMARY.md`** - Implementation overview

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Web container is running (`docker-compose ps`)
- [ ] Migrations applied successfully
- [ ] Can access http://localhost:11800/filtered/topics/
- [ ] Can set filters and apply them
- [ ] Can register a new account
- [ ] Can save a preference profile
- [ ] Can load a saved profile
- [ ] Can view profile dashboard
- [ ] No re-crawling occurs (check database queries are efficient)

---

## 🎯 Summary

✅ **setup_user_preferences.sh** deleted
✅ **setup.sh** updated with user preference functionality
✅ **Option 11** now shows all preference URLs
✅ **Option 14** runs user preference setup
✅ **Option 15** provides testing guide
✅ **Command-line mode** supports `./setup.sh setup-prefs` and `./setup.sh test-prefs`

**Everything is now consolidated in one place!**
