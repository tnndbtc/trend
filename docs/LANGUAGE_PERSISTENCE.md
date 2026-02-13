# Language Persistence & Menu Translation System

Complete guide to the multi-language support system in the AI Trend Intelligence platform.

## 📚 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Supported Languages](#supported-languages)
4. [How It Works](#how-it-works)
5. [Adding New Languages](#adding-new-languages)
6. [Adding Menu Translations](#adding-menu-translations)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The language persistence system provides:
- **8 supported languages** with full menu translations
- **Automatic language persistence** across sessions using cookies
- **Session-based storage** for active language preference
- **Middleware-based** language detection and normalization
- **Context processor** for easy template access to translations
- **Translation provider toggle** (FREE vs AI)

### Key Features

✅ **Persistent**: Language choice saved for 1 year via cookies
✅ **Automatic**: No need to pass `?lang=` in every URL
✅ **Flexible**: Supports URL parameter, session, and cookie sources
✅ **Normalized**: Handles various language code formats
✅ **Translated**: All menu items and UI elements localized

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                    User Request                          │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│         LanguagePreferenceMiddleware                     │
│  Priority: URL param > Session > Cookie > Default       │
│  Saves to: Session + Cookie (1 year)                    │
│  Sets: request.LANGUAGE_CODE                            │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│              Context Processor                           │
│  Loads: MENU_TRANSLATIONS[language]                     │
│  Provides: menu.{key}, current_lang                     │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│                  Template Rendering                      │
│  Uses: {{ menu.dashboard }}, {{ menu.login }}, etc.    │
└─────────────────────────────────────────────────────────┘
```

### Files

| File | Purpose |
|------|---------|
| `trends_viewer/middleware.py` | Language detection and persistence |
| `trends_viewer/translations.py` | Menu translations for all languages |
| `trends_viewer/context_processors.py` | Template context providers |
| `web_interface/settings.py` | Middleware and processor registration |
| `templates/base.html` | Uses translated menu items |

---

## Supported Languages

| Code | Language | Native Name | Status |
|------|----------|-------------|--------|
| `en` | English | English | ✅ Default |
| `zh` | Chinese (Simplified) | 中文 | ✅ Full |
| `es` | Spanish | Español | ✅ Full |
| `fr` | French | Français | ✅ Full |
| `de` | German | Deutsch | ✅ Full |
| `ja` | Japanese | 日本語 | ✅ Full |
| `ko` | Korean | 한국어 | ✅ Full |
| `ru` | Russian | Русский | ✅ Full |

---

## How It Works

### Language Selection Flow

```
1. User clicks language dropdown → Selects "中文 (Chinese)"
                ↓
2. JavaScript: window.location = "/?lang=zh"
                ↓
3. Middleware intercepts request:
   - Detects ?lang=zh parameter
   - Normalizes to 'zh'
   - Saves to session: request.session['language'] = 'zh'
   - Sets attribute: request.LANGUAGE_CODE = 'zh'
   - Sets cookie: language=zh (expires in 1 year)
                ↓
4. Context Processor:
   - Reads request.LANGUAGE_CODE = 'zh'
   - Loads MENU_TRANSLATIONS['zh']
   - Provides to template as 'menu'
                ↓
5. Template renders:
   - {{ menu.dashboard }} → "仪表板"
   - {{ menu.login }} → "登录"
   - {{ menu.my_feed }} → "我的订阅"
                ↓
6. User navigates to another page (no ?lang= needed)
                ↓
7. Middleware reads from session (already 'zh')
                ↓
8. Chinese menu persists automatically
```

### Priority Order

When determining language, the middleware checks in this order:

1. **URL Parameter** (`?lang=zh`)
   → Highest priority, explicitly set by user

2. **Session Variable** (`request.session['language']`)
   → Saved from previous request

3. **Cookie** (`language=zh`)
   → Persists across browser sessions (1 year)

4. **Default** (`en`)
   → Fallback if nothing else is set

### Example Scenarios

#### Scenario 1: First Visit
```
User visits: https://example.com/
→ No lang parameter, no session, no cookie
→ Middleware sets: language = 'en' (default)
→ Cookie set: language=en (1 year)
→ Menu displays in English
```

#### Scenario 2: Explicit Language Change
```
User clicks dropdown, selects "Español"
→ Redirects to: /?lang=es
→ Middleware detects URL param
→ Saves to session: language = 'es'
→ Updates cookie: language=es (1 year)
→ Menu displays in Spanish
```

#### Scenario 3: Subsequent Navigation
```
User clicks "Dashboard" link
→ URL: /dashboard/ (no ?lang= parameter)
→ Middleware reads session: language = 'es'
→ Menu still displays in Spanish
```

#### Scenario 4: Browser Restart
```
User closes browser, reopens next day
→ Session cleared, but cookie persists
→ Middleware reads cookie: language = 'es'
→ Saves to new session: language = 'es'
→ Menu displays in Spanish (language remembered!)
```

---

## Adding New Languages

### Step 1: Add to Middleware

Edit `trends_viewer/middleware.py`:

```python
SUPPORTED_LANGUAGES = {
    'en', 'zh', 'es', 'fr', 'de', 'ja', 'ko', 'ru',
    'pt',  # Add Portuguese
}
```

### Step 2: Add Translations

Edit `trends_viewer/translations.py`:

```python
MENU_TRANSLATIONS = {
    # ... existing languages ...

    'pt': {
        'app_title': 'Inteligência de Tendências IA',
        'dashboard': 'Painel',
        'all_trends': 'Todas as Tendências',
        'all_topics': 'Todos os Tópicos',
        'my_feed': 'Meu Feed',
        'history': 'Histórico',
        'profile': 'Perfil',
        'register': 'Registrar',
        'login': 'Entrar',
        'logout': 'Sair',
        'admin': 'Administrador',
        # ... add all menu items ...
    },
}
```

### Step 3: Add to Language Selector

Edit `templates/base.html`:

```html
<select id="language-select" onchange="changeLanguage(this.value)">
    <!-- ... existing options ... -->
    <option value="pt" {% if current_lang == 'pt' %}selected{% endif %}>
        Português (Portuguese)
    </option>
</select>
```

### Step 4: Test

```bash
# Visit with Portuguese
curl http://localhost:11800/?lang=pt

# Check menu translations appear in Portuguese
```

---

## Adding Menu Translations

### Translation Keys

Current translation keys available in templates via `{{ menu.KEY }}`:

#### Navigation
- `app_title` - Application title
- `dashboard` - Dashboard link
- `all_trends` - All Trends link
- `all_topics` - All Topics link
- `my_feed` - My Feed link
- `history` - History link
- `profile` - Profile link
- `register` - Sign Up button
- `login` - Login link
- `logout` - Logout link
- `admin` - Admin link

#### Actions
- `search` - Search button
- `filter` - Filter button
- `sort` - Sort button
- `save` - Save button
- `cancel` - Cancel button
- `delete` - Delete button
- `edit` - Edit button
- `view` - View button
- `apply` - Apply button
- `reset` - Reset button

#### Content
- `trending_now` - Trending Now header
- `top_trends` - Top Trends
- `latest_trends` - Latest Trends
- `trend_details` - Trend Details
- `related_topics` - Related Topics
- `topics` - Topics
- `translation` - Translation label

### Adding New Keys

1. **Define in translations.py** for all languages:

```python
MENU_TRANSLATIONS = {
    'en': {
        # ... existing keys ...
        'new_feature': 'New Feature',
    },
    'zh': {
        # ... existing keys ...
        'new_feature': '新功能',
    },
    # ... repeat for all languages ...
}
```

2. **Use in templates**:

```html
<h2>{{ menu.new_feature }}</h2>
```

---

## Testing

### Manual Testing

#### Test 1: Language Selection
```bash
# 1. Open browser to http://localhost:11800/
# 2. Select "中文 (Chinese)" from dropdown
# 3. Verify menu changes to Chinese
# 4. Navigate to different pages
# 5. Verify Chinese persists without ?lang= in URL
```

#### Test 2: Cookie Persistence
```bash
# 1. Select a language (e.g., Spanish)
# 2. Close browser completely
# 3. Reopen browser to http://localhost:11800/
# 4. Verify Spanish menu appears (cookie remembered)
```

#### Test 3: URL Parameter Override
```bash
# 1. Have Spanish set in session
# 2. Visit /?lang=fr
# 3. Verify menu changes to French
# 4. Verify session/cookie updated to French
```

### Automated Testing

```python
from django.test import TestCase, Client

class LanguagePersistenceTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_default_language(self):
        """Test default language is English"""
        response = self.client.get('/')
        self.assertEqual(response.context['current_lang'], 'en')

    def test_url_parameter(self):
        """Test ?lang= parameter sets language"""
        response = self.client.get('/?lang=zh')
        self.assertEqual(response.context['current_lang'], 'zh')

    def test_session_persistence(self):
        """Test language persists in session"""
        # Set language
        self.client.get('/?lang=es')

        # Visit without parameter
        response = self.client.get('/')
        self.assertEqual(response.context['current_lang'], 'es')

    def test_cookie_set(self):
        """Test cookie is set correctly"""
        response = self.client.get('/?lang=fr')
        self.assertIn('language', response.cookies)
        self.assertEqual(response.cookies['language'].value, 'fr')
```

---

## Troubleshooting

### Issue: Language not persisting

**Symptoms**: Language resets to English on each page
**Cause**: Middleware not registered or session not working
**Solution**:
```python
# Check web_interface/settings.py
MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',  # Must be before
    'trends_viewer.middleware.LanguagePreferenceMiddleware',  # Our middleware
    # ...
]
```

### Issue: Menu not translating

**Symptoms**: Still see "Dashboard" instead of "仪表板"
**Cause**: Context processor not registered
**Solution**:
```python
# Check web_interface/settings.py TEMPLATES
'context_processors': [
    # ...
    'trends_viewer.context_processors.menu_translations',  # Must be present
]
```

### Issue: Wrong language code format

**Symptoms**: Language detection fails
**Cause**: Using unsupported format like 'zh-Hans'
**Solution**: Middleware normalizes automatically, but ensure LANGUAGE_NORMALIZATION map includes your format

### Issue: Cookie not persisting

**Symptoms**: Language resets after browser restart
**Cause**: Cookie settings or browser configuration
**Solution**:
```python
# Middleware sets cookie with these parameters:
response.set_cookie(
    'language',
    normalized_lang,
    max_age=31536000,  # 1 year
    httponly=False,
    samesite='Lax'
)
```

---

## Developer Notes

### Middleware Execution Order

The middleware MUST be placed after `SessionMiddleware` but can be before or after most others:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',  # REQUIRED BEFORE
    'trends_viewer.middleware.LanguagePreferenceMiddleware',  # OUR MIDDLEWARE
    'django.middleware.common.CommonMiddleware',
    # ... rest of middleware ...
]
```

### Performance Considerations

- **Middleware runs on every request**: Very lightweight, just dictionary lookups
- **Translations loaded once**: Python module caching means MENU_TRANSLATIONS loaded once
- **Cookie overhead**: Minimal, 2-letter language code
- **Session overhead**: Minimal, single key-value pair

### Security Considerations

- **Input validation**: Middleware normalizes all input, prevents injection
- **Cookie settings**: SameSite=Lax prevents CSRF attacks
- **No sensitive data**: Language preference is not sensitive information

---

## Summary

The language persistence system provides a seamless multi-language experience:

1. **User selects language** → Saved to session + cookie
2. **Middleware processes all requests** → Sets request.LANGUAGE_CODE
3. **Context processor provides translations** → Templates access via {{ menu.KEY }}
4. **Language persists automatically** → No ?lang= needed in URLs
5. **Cookie ensures long-term memory** → Survives browser restarts

**Result**: Users select their language once, and it's remembered forever! 🌍
