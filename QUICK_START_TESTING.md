# 🚀 Quick Start: Testing User Preferences

## ✅ Integration Complete!

The user preference system is now **fully integrated** into `setup.sh`.

---

## 🎯 How to Test (3 Easy Steps)

### Step 1: Start Web Interface

```bash
./setup.sh
# Select: 2) Basic Setup (Web Interface Only)
```

### Step 2: Setup User Preferences

```bash
./setup.sh
# Select: 14) Setup User Preferences (Phase 1 + Phase 2)
```

### Step 3: Test It!

**Option A - Interactive Test Guide:**
```bash
./setup.sh
# Select: 15) Test User Preferences
# Follow the on-screen instructions
```

**Option B - Direct Testing:**

Open your browser to:
```
http://localhost:11800/filtered/topics/
```

Then:
1. Set filters (sources, languages, keywords, etc.)
2. Click "Apply Filters"
3. See filtered results (queried from database, NO re-crawling!)

---

## 📊 View All URLs

```bash
./setup.sh
# Select: 11) Show All Access URLs
```

This shows:
- 🔍 Filtered Topics: http://localhost:11800/filtered/topics/
- 📈 Filtered Trends: http://localhost:11800/filtered/trends/
- 👤 User Profile: http://localhost:11800/profile/
- 🆕 Sign Up: http://localhost:11800/register/
- 🔑 Login: http://localhost:11800/login/

---

## 🧪 Automated Tests

```bash
# Run from command line
docker-compose exec web python manage.py test trends_viewer.tests_preferences
```

---

## 📚 Full Documentation

- **Setup Integration**: `docs/SETUP_INTEGRATION.md`
- **Complete Guide**: `docs/USER_PREFERENCES_COMPLETE.md`
- **Quick Start**: `docs/PHASE1_QUICKSTART.md`
- **Implementation Summary**: `IMPLEMENTATION_SUMMARY.md`

---

## ✨ What's Changed

| Before | After |
|--------|-------|
| ❌ Separate `setup_user_preferences.sh` | ✅ Integrated into `setup.sh` |
| ❌ Option 11 didn't show preference URLs | ✅ Option 11 shows all preference URLs |
| ❌ No menu option for setup | ✅ Option 14: Setup User Preferences |
| ❌ No menu option for testing | ✅ Option 15: Test User Preferences |
| ❌ No CLI mode | ✅ `./setup.sh setup-prefs` and `./setup.sh test-prefs` |

---

## 🎉 Ready to Use!

Everything is now in one place - just use `./setup.sh`!
