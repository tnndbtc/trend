# ROUND 2: Standardized Language Locales Verification Report

## Executive Summary

After thorough code review of ALL 10 requested components, I have identified a **CRITICAL INCONSISTENCY** in language code standardization:

- **Views.py and Middleware** use standardized locale format: `zh-Hans`, `en-US`, `es-ES`, etc.
- **All Translation Services** expect 2-letter codes: `zh`, `es`, `fr`, etc.
- **DeepL Service** expects UPPERCASE codes: `ZH`, `ES`, `FR`, etc.

This creates a **language code mismatch** that can cause API failures and unexpected translation behavior.

---

## Component-by-Component Analysis

### 1. TRANSLATION MANAGER (trend_agent/services/translation_manager.py)

**Language Code Handling:**
- Line 506: `target_language: str` - receives target language code
- Line 530: Passed directly to cache without normalization
- Line 568: `await provider.translate(text, target_language, source_language)`
- **Issue**: Does NOT normalize language codes before passing to providers

**API Calls:**
```python
# Cache lookup (line 530)
cached = await self.cache.get(text, source_language, target_language)

# Provider translation (line 568-570)
translation = await provider.translate(
    text, target_language, source_language
)
```

**Receives Code Format:** Whatever the views send (e.g., `zh-Hans`, `en-US`)
**Sends Code Format:** Same format to providers

**PROBLEM**: Middleware sends `zh-Hans`, but DeepL expects `ZH` and LibreTranslate expects `zh`

---

### 2. LIBRETRANSLATE SERVICE (trend_agent/services/translation.py, lines 474-731)

**Language Code Handling:**
```python
# Line 621-623: Build payload with target language
payload = {
    "q": text,
    "target": target_language,  # DIRECT - NO NORMALIZATION
    "format": "text",
}

# Line 628-630: Source language
if source_language:
    payload["source"] = source_language  # DIRECT - NO NORMALIZATION
else:
    payload["source"] = "auto"
```

**Supported Languages (line 689-708):**
```python
return [
    "en",
    "es", 
    "fr",
    "de",
    "it",
    "pt",
    "ru",
    "ja",
    "zh-Hans",  # MIXED FORMAT!
    "ko",
    "ar",
    "hi",
    "nl",
    "pl",
    "tr",
]
```

**API Endpoint:** `{host}/translate`
**Payload Format:**
```json
{
    "q": "text to translate",
    "target": "<2-letter code>",
    "source": "<2-letter code or auto>",
    "format": "text"
}
```

**Expected Language Codes:** 2-letter ISO 639-1 (e.g., `es`, `fr`, `zh`)
**Actual Codes Received:** Locale format from views (e.g., `es-ES`, `zh-Hans`)

**CRITICAL ISSUE**: 
- View sends `zh-Hans` → LibreTranslate API expects `zh` → Translation fails
- View sends `es-ES` → LibreTranslate API expects `es` → Translation fails

---

### 3. DEEPL SERVICE (trend_agent/services/translation.py, lines 733-986)

**Language Code Handling:**
```python
# Line 864-870: Build payload
payload = {
    "text": valid_texts,
    "target_lang": target_language.upper(),  # CONVERTS TO UPPERCASE
}

if source_language:
    payload["source_lang"] = source_language.upper()  # CONVERTS TO UPPERCASE
```

**API Endpoint:** `https://api.deepl.com/v2/translate`
**Payload Format:**
```json
{
    "text": ["text1", "text2"],
    "target_lang": "ZH",
    "source_lang": "EN"
}
```

**Expected Language Codes:** 2-letter UPPERCASE (e.g., `DE`, `FR`, `ZH`)
**Actual Codes Received:** Locale format from views (e.g., `de-DE`, `zh-Hans`)

**Conversion Process:**
- Input: `zh-Hans` → `.upper()` → `ZH-HANS` ✓ Works (DeepL recognizes both)
- Input: `en-US` → `.upper()` → `EN-US` ✗ DeepL expects just `EN`

**Partially Broken**: Converts to uppercase but doesn't extract base code

**Supported Languages (line 945-961):**
```python
return [
    "EN",      # Uppercase
    "DE",
    "FR",
    "ES",
    "IT",
    "PT",
    "RU",
    "JA",
    "ZH",
    "NL",
    "PL",
    "TR",
]
```

---

### 4. OPENAI TRANSLATION SERVICE (trend_agent/services/translation.py, lines 57-472)

**Language Code Handling:**
```python
# Line 219: Lookup language name
target_lang_name = LANGUAGE_NAMES.get(target_language, target_language)

# Line 222: Source language lookup
source_lang_name = LANGUAGE_NAMES.get(source_language, source_language)

# Lines 223-234: Build instruction using NAMES (not codes)
instruction = (
    f"Translate the following text from {source_lang_name} "
    f"to {target_lang_name}. "
    f"Preserve formatting, tone, and meaning. "
    f"Return only the translated text."
)
```

**LANGUAGE_NAMES Dictionary (lines 30-54):**
```python
LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "zh-Hans": "Chinese (Simplified)",  # LOCALE FORMAT SUPPORTED!
    "ko": "Korean",
    ...
}
```

**API Call (line 349-356):**
```python
payload = {
    "model": self.model,
    "messages": [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_content},
    ],
    "temperature": 0.3,
}
```

**Receives Code Format:** 2-letter or locale (e.g., `zh-Hans`, `es`)
**API Behavior:** Uses language name (e.g., "Chinese (Simplified)"), not code
**Result:** Works because it translates codes to human-readable names

**Status**: Mostly works due to LANGUAGE_NAMES mapping

---

### 5. DJANGO VIEWS (web_interface/trends_viewer/views.py)

**Language Code Handling:**

**normalize_lang_code() function (lines 56-79):**
```python
def normalize_lang_code(lang_code):
    """Normalize language codes to proper locale format (language-REGION)."""
    lang_map = {
        # Legacy Chinese codes
        'zh': 'zh-Hans',
        'zh-CN': 'zh-Hans',
        'zh-TW': 'zh-Hant',
        
        # Legacy two-letter codes
        'en': 'en-US',
        'es': 'es-ES',
        'fr': 'fr-FR',
        'de': 'de-DE',
        'ja': 'ja-JP',
        'ko': 'ko-KR',
        'ru': 'ru-RU',
        'ar': 'ar-SA',
    }
    return lang_map.get(lang_code, lang_code)
```

**Usage in translate_text_sync() (line 203):**
```python
normalized_lang = normalize_lang_code(target_lang)
logger.info(f"Translating text to {normalized_lang} (original: {target_lang}, provider: {preferred_provider})")

translated = loop.run_until_complete(
    manager.translate(
        text,
        normalized_lang,  # PASSES LOCALE FORMAT
        source_language='en',
        preferred_provider=preferred_provider
    )
)
```

**Output Language Codes:** Locale format (`zh-Hans`, `en-US`, `es-ES`, etc.)

**Critical Issue**: normalize_lang_code() converts 2-letter codes to locale format, then passes them to translation manager, which passes them to providers expecting 2-letter codes!

Flow: `'es'` → `normalize_lang_code()` → `'es-ES'` → `manager.translate()` → `LibreTranslateService.translate()` → API expects `'es'` ✗

---

### 6. DJANGO TASKS (web_interface/trends_viewer/tasks.py)

**Language Code Handling:**

**pre_translate_trends() (lines 21-102):**
```python
@shared_task(bind=True, max_retries=3)
def pre_translate_trends(self, trend_ids, target_lang='zh-Hans'):
    # Line 37-38
    normalized_lang = normalize_lang_code(target_lang)
    logger.info(f"[PRE-TRANSLATE] Starting translation of {len(trend_ids)} trends to {normalized_lang} (from {target_lang})")
    
    # Line 62
    translate_trends_batch([trend], normalized_lang, session=None)
```

**bulk_translate_all_trends() (lines 105-156):**
```python
def bulk_translate_all_trends(target_lang='zh-Hans', days_back=None):
    # Line 120
    normalized_lang = normalize_lang_code(target_lang)
    
    # Line 149
    result = pre_translate_trends.delay(trend_ids, normalized_lang)
```

**translate_single_trend() (lines 159-184):**
```python
def translate_single_trend(trend_id, target_lang='zh-Hans'):
    # Line 174
    normalized_lang = normalize_lang_code(target_lang)
    
    # Line 177
    result = pre_translate_trends.delay([trend_id], normalized_lang)
```

**Flow**: `target_lang` → normalize → passes locale format to batch function → to translation manager

---

### 7. ADMIN TRANSLATION DASHBOARD (web_interface/trends_viewer/admin_translation.py)

**Language Code Handling:**

**translation_dashboard_view() (lines 135-199):**
```python
for lang_code, lang_name in settings.TRANSLATION_PRIORITY_LANGUAGES:
    # Line 152: Normalize for database lookup
    normalized_lang = normalize_lang_code(lang_code)
    
    # Line 155-158: Query with normalized code
    translated_trends = TrendTranslationStatus.objects.filter(
        language=normalized_lang,  # USES NORMALIZED (LOCALE) FORMAT
        translated=True
    ).count()
```

**translation_stats_api() (lines 202-244):**
```python
for lang_code, lang_name in settings.TRANSLATION_PRIORITY_LANGUAGES:
    # Line 214: Same normalization
    normalized_lang = normalize_lang_code(lang_code)
    
    # Line 217-220: Database query
    translated_trends = TrendTranslationStatus.objects.filter(
        language=normalized_lang,
        translated=True
    ).count()
```

**bulk_translate_view() (lines 247-284):**
```python
if request.method == 'POST':
    target_lang = request.POST.get('language')
    # ...
    # Line 265: Passes raw language code to task
    result = bulk_translate_all_trends.apply_async((target_lang, days_back), ignore_result=True)
```

**Database Queries**: Use locale format (`zh-Hans`, `es-ES`)
**Database Storage**: TrendTranslationStatus.language stores locale format

---

### 8. API ENDPOINTS (api/routers/translation.py)

**Language Code Handling:**

**TranslateRequest Model (lines 30-46):**
```python
class TranslateRequest(BaseModel):
    text: str = Field(...)
    target_language: str = Field(..., description="Target language code (ISO 639-1)", min_length=2, max_length=5)
    source_language: Optional[str] = Field(None, description="Source language code")
```

**translate_text() endpoint (lines 137-211):**
```python
async def translate_text(request: TranslateRequest):
    # ...
    # Line 184-189: Passes code directly to manager
    translated = await translation_manager.translate(
        text=request.text,
        target_language=request.target_language,
        source_language=request.source_language,
        preferred_provider=request.preferred_provider,
    )
```

**Example Response (line 78-87):**
```json
{
    "original_text": "Hello, world!",
    "translated_text": "¡Hola, mundo!",
    "source_language": "en",
    "target_language": "es",
    "provider_used": "libretranslate",
    "cached": false
}
```

**Issue**: API accepts any 2-5 character code but doesn't validate or normalize

---

### 9. DATABASE MODELS (web_interface/trends_viewer/models.py)

**TranslatedContent Model (lines 397-494):**
```python
class TranslatedContent(models.Model):
    source_language = models.CharField(
        max_length=10,
        help_text="Source language code (e.g., 'en', 'zh-Hans', 'auto')"
    )
    
    target_language = models.CharField(
        max_length=10,
        help_text="Target language code (e.g., 'en', 'zh-Hans', 'es')"
    )
```

**Storage Format**: Accepts any format up to 10 characters
**Query Usage** (from translation_manager.py, line 44-48):
```python
cached = TranslatedContent.objects.filter(
    source_text_hash=source_text_hash,
    source_language=source_lang or 'auto',
    target_language=target_lang  # WHATEVER FORMAT IS PASSED
).first()
```

**TrendTranslationStatus Model (lines 496-547):**
```python
class TrendTranslationStatus(models.Model):
    language = models.CharField(
        max_length=10,
        help_text="Target language code (e.g., 'zh-Hans', 'es', 'fr')"
    )
```

**Storage Format**: Expects locale format based on help text and admin usage

**Status**: Database accepts any format; no validation

---

### 10. MIDDLEWARE (web_interface/trends_viewer/middleware.py)

**Language Code Handling:**

**SUPPORTED_LANGUAGES (lines 18-29):**
```python
SUPPORTED_LANGUAGES = {
    'en-US',   # English (United States)
    'zh-Hans', # Simplified Chinese
    'zh-Hant', # Traditional Chinese
    'es-ES',   # Spanish
    'fr-FR',   # French
    'de-DE',   # German
    'ja-JP',   # Japanese
    'ko-KR',   # Korean
    'ru-RU',   # Russian
    'ar-SA',   # Arabic
}
```

**LANGUAGE_NORMALIZATION (lines 32-65):**
```python
LANGUAGE_NORMALIZATION = {
    # Legacy two-letter codes
    'en': 'en-US',
    'zh': 'zh-Hans',
    'es': 'es-ES',
    ...
}
```

**normalize_lang_code() function (lines 68-98):**
```python
def normalize_lang_code(lang_code):
    # Converts legacy 2-letter to locale format
    # 'zh' → 'zh-Hans', 'es' → 'es-ES'
    return lang_map.get(lang_code, lang_code)
```

**Output Format**: Always locale format (`zh-Hans`, `en-US`, etc.)

**Flow**: User URL → Middleware normalizes → Sets `request.LANGUAGE_CODE` to locale format → Views use it

---

## Critical Issues Summary

### Issue #1: Language Code Format Mismatch

| Component | Sends | Receives | Issue |
|-----------|-------|----------|-------|
| Middleware | `zh-Hans` | User input | ✓ Correct |
| Views | `zh-Hans` | Middleware | ✓ Correct |
| Translation Manager | `zh-Hans` | Views | ✗ Should convert to `zh` |
| LibreTranslate API | `zh-Hans` | Manager | ✗ Expects `zh` |
| DeepL API | `ZH-HANS` | Manager | ✗ Expects `ZH` |
| OpenAI | Converted to name | Manager | ✓ Works via names |
| Database | `zh-Hans` | Manager | ~ Inconsistent |

### Issue #2: Missing Normalization in Translation Manager

The `TranslationManager.translate()` and `TranslationManager.translate_batch()` methods receive language codes from views (locale format) but **DO NOT normalize them** before passing to providers that expect 2-letter codes.

**Missing Logic:**
```python
# Should be added to TranslationManager.translate() line 503-509
async def translate(
    self,
    text: str,
    target_language: str,  # Receives "zh-Hans"
    source_language: Optional[str] = None,
    preferred_provider: Optional[str] = None,
) -> str:
    # MISSING: Normalize to 2-letter codes for providers
    normalized_target = self._normalize_to_provider_format(target_language)
    normalized_source = self._normalize_to_provider_format(source_language) if source_language else None
```

### Issue #3: Provider-Specific Requirements

| Provider | Expected Format | Current Code |
|----------|-----------------|--------------|
| LibreTranslate | 2-letter (`zh`, `es`) | Gets locale (`zh-Hans`, `es-ES`) |
| DeepL | 2-letter UPPERCASE (`ZH`, `ES`) | Gets `.upper()` of locale (`ZH-HANS`, `ES-ES`) |
| OpenAI | Any (converts to names) | Gets locale (`zh-Hans`, `es-ES`) ✓ Works |

---

## Failure Scenarios

### Scenario 1: User Selects "Chinese (Simplified)"
1. Middleware receives `zh-Hans`
2. View normalizes: `zh` → `zh-Hans`
3. Manager receives `zh-Hans`
4. LibreTranslate API receives `zh-Hans`
5. LibreTranslate API fails: "Unknown target language: zh-Hans"

### Scenario 2: DeepL with Spanish
1. View sends `es-ES`
2. Manager sends `es-ES`
3. DeepL converts: `.upper()` → `ES-ES`
4. DeepL API fails: "Unknown target language: ES-ES" (expects `ES`)

### Scenario 3: Database Cache Miss
1. View sends `zh-Hans` for translation
2. Cache lookup: `TranslatedContent.filter(target_language='zh-Hans')`
3. No match (database might have `zh`)
4. Unnecessary API call

---

## Code Locations Requiring Changes

### CRITICAL (Will cause API failures):
1. **trend_agent/services/translation_manager.py**
   - Add language code normalization in `translate()` (line 503)
   - Add language code normalization in `translate_batch()` (line 618)

2. **trend_agent/services/translation.py**
   - LibreTranslate: normalize codes to 2-letter before API call (line 621)
   - DeepL: extract base language code instead of just uppercasing (line 866)

### IMPORTANT (Data consistency):
3. **web_interface/trends_viewer/views.py**
   - Fix normalize_lang_code() to convert TO provider format, not FROM (line 56)

4. **web_interface/trends_viewer/admin_translation.py**
   - Ensure consistent format in database queries (lines 152, 214)

### INFORMATIONAL (Validation):
5. **api/routers/translation.py**
   - Add language code validation in TranslateRequest (line 34)

6. **web_interface/trends_viewer/models.py**
   - Add language code validators to TranslatedContent and TrendTranslationStatus

---

## Recommendations

### Priority 1: Fix Provider Calls
1. Create a provider-specific language code converter in translation_manager.py
2. Normalize codes BEFORE sending to each provider
3. Test with actual API calls

### Priority 2: Unify Format
1. Choose single format: **2-letter ISO 639-1** for providers, **locale format** for UI
2. Normalize at API boundary (in translation_manager)
3. Keep database flexible but document expected format

### Priority 3: Add Validation
1. Validate language codes in API endpoints
2. Add database constraints for valid codes
3. Add logging for code conversions

---

## Example Fix Implementation

```python
# In TranslationManager.translate() (line 503)

async def translate(
    self,
    text: str,
    target_language: str,
    source_language: Optional[str] = None,
    preferred_provider: Optional[str] = None,
) -> str:
    if not text or not text.strip():
        return text
    
    # NORMALIZE CODES TO 2-LETTER FORMAT FOR PROVIDERS
    target_lang_normalized = self._normalize_to_provider_code(target_language)
    source_lang_normalized = self._normalize_to_provider_code(source_language) if source_language else None
    
    # Check cache first (using normalized codes)
    if self.cache:
        cached = await self.cache.get(text, source_lang_normalized, target_lang_normalized)
        if cached:
            self._cache_hits += 1
            return cached
    
    # ... rest of method uses normalized codes ...

def _normalize_to_provider_code(self, lang_code: str) -> str:
    """Convert any format to 2-letter ISO 639-1 code."""
    if not lang_code:
        return None
    
    # Extract first 2 letters if locale format
    base_code = lang_code.split('-')[0].lower()
    
    # Map special cases
    special_cases = {
        'zh-hans': 'zh',
        'zh-hant': 'zh',
        'en-us': 'en',
        'en-gb': 'en',
    }
    return special_cases.get(lang_code.lower(), base_code)
```

