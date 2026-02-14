# QUICK FIX GUIDE - Language Locale Issues

## TL;DR

**Problem**: Language codes flow in locale format (e.g., `zh-Hans`, `es-ES`) through entire translation pipeline, but APIs expect 2-letter codes (e.g., `zh`, `es`).

**Impact**: 
- LibreTranslate: Will fail for any locale-format request
- DeepL: Will fail for any locale-format request
- Database cache: Will miss translations that exist in different format
- Admin dashboard: Wrong translation statistics

**Root Cause**: Missing normalization in `TranslationManager`

---

## Critical Fixes (In Order)

### Fix #1: Add Normalization Method to TranslationManager

**File**: `trend_agent/services/translation_manager.py`

**Add this method to the `TranslationManager` class:**

```python
def _normalize_to_provider_code(self, lang_code: str) -> str:
    """
    Convert language code to 2-letter ISO 639-1 format for API providers.
    
    Converts locale formats (zh-Hans, es-ES) to provider format (zh, es).
    
    Args:
        lang_code: Language code in any format
        
    Returns:
        2-letter ISO 639-1 code or None
    """
    if not lang_code:
        return None
    
    lang_code_lower = str(lang_code).lower()
    
    # Handle special cases
    special_cases = {
        'zh-hans': 'zh',
        'zh-hant': 'zh',
        'zh-cn': 'zh',
        'zh-tw': 'zh',
        'en-us': 'en',
        'en-gb': 'en',
        'es-es': 'es',
        'es-mx': 'es',
        'fr-fr': 'fr',
        'de-de': 'de',
        'ja-jp': 'ja',
        'ko-kr': 'ko',
        'ru-ru': 'ru',
        'ar-sa': 'ar',
        'pt-pt': 'pt',
        'it-it': 'it',
    }
    
    if lang_code_lower in special_cases:
        return special_cases[lang_code_lower]
    
    # Default: extract first 2 letters
    return lang_code_lower[:2]
```

---

### Fix #2: Normalize in translate() Method

**File**: `trend_agent/services/translation_manager.py`  
**Method**: `async def translate()` (line 503)

**Replace lines 568-570:**

```python
# BEFORE (WRONG):
translation = await provider.translate(
    text, target_language, source_language
)

# AFTER (CORRECT):
# Normalize codes for provider
target_lang_normalized = self._normalize_to_provider_code(target_language)
source_lang_normalized = self._normalize_to_provider_code(source_language) if source_language else None

translation = await provider.translate(
    text, target_lang_normalized, source_lang_normalized
)
```

---

### Fix #3: Normalize in translate_batch() Method

**File**: `trend_agent/services/translation_manager.py`  
**Method**: `async def translate_batch()` (line 618)

**Add normalization before provider call (around line 685):**

```python
# Normalize codes for provider
target_lang_normalized = self._normalize_to_provider_code(target_language)
source_lang_normalized = self._normalize_to_provider_code(source_language) if source_language else None

batch_translations = await provider.translate_batch(
    texts_to_translate, target_lang_normalized, source_lang_normalized
)
```

---

### Fix #4: Fix LibreTranslate Service

**File**: `trend_agent/services/translation.py`  
**Method**: `async def _translate_single()` (line 608)

**Add normalization before API call (around line 620):**

```python
# Normalize language code for API
def _normalize_code(self, lang_code: str) -> str:
    """Extract 2-letter code from any format."""
    if not lang_code:
        return None
    lang_lower = str(lang_code).lower()
    # Handle special cases
    special = {'zh-hans': 'zh', 'zh-hant': 'zh', 'zh-cn': 'zh', 'zh-tw': 'zh',
               'en-us': 'en', 'en-gb': 'en', 'es-es': 'es', 'fr-fr': 'fr'}
    if lang_lower in special:
        return special[lang_lower]
    return lang_lower[:2]

# In the method:
normalized_target = self._normalize_code(target_language)
normalized_source = self._normalize_code(source_language) if source_language else "auto"

payload = {
    "q": text,
    "target": normalized_target,  # Use normalized code
    "format": "text",
    "source": normalized_source,
}
```

---

### Fix #5: Fix DeepL Service

**File**: `trend_agent/services/translation.py`  
**Method**: `async def translate_batch()` (line 840)

**Change lines 866-870 from:**

```python
# BEFORE (WRONG - uppercases entire string):
payload = {
    "text": valid_texts,
    "target_lang": target_language.upper(),
}
if source_language:
    payload["source_lang"] = source_language.upper()
```

**To:**

```python
# AFTER (CORRECT - extracts base code then uppercases):
def _normalize_code(self, lang_code: str) -> str:
    """Extract 2-letter code and uppercase for DeepL."""
    if not lang_code:
        return None
    lang_lower = str(lang_code).lower()
    # Handle special cases
    special = {'zh-hans': 'zh', 'zh-hant': 'zh', 'zh-cn': 'zh', 'zh-tw': 'zh',
               'en-us': 'en', 'en-gb': 'en', 'es-es': 'es', 'fr-fr': 'fr'}
    base = special.get(lang_lower, lang_lower[:2])
    return base.upper()

# In the method:
normalized_target = self._normalize_code(target_language)
normalized_source = self._normalize_code(source_language) if source_language else None

payload = {
    "text": valid_texts,
    "target_lang": normalized_target,  # Now correctly uppercase 2-letter
}
if normalized_source:
    payload["source_lang"] = normalized_source
```

---

## Testing After Fixes

### Test 1: Chinese Translation
```python
# Should translate successfully
manager.translate("Hello", target_language="zh-Hans")
# Internally normalizes to "zh" for API
```

### Test 2: Spanish with DeepL
```python
# Should translate successfully
manager.translate("Hello", target_language="es-ES", preferred_provider="deepl")
# Internally normalizes to "ES" for API
```

### Test 3: Database Cache
```python
# Should find cached translation
manager.translate("Hello", target_language="zh-Hans")  # First call - API
manager.translate("Hello", target_language="zh-Hans")  # Second call - cache hit
```

---

## Verification Checklist

- [ ] TranslationManager._normalize_to_provider_code() added
- [ ] TranslationManager.translate() normalizes before API call
- [ ] TranslationManager.translate_batch() normalizes before API call
- [ ] LibreTranslateService._normalize_code() added
- [ ] LibreTranslateService._translate_single() uses normalized codes
- [ ] DeepLTranslationService._normalize_code() added
- [ ] DeepLTranslationService.translate_batch() uses normalized codes
- [ ] OpenAI service still works (no changes needed)
- [ ] Cache operations use normalized codes
- [ ] Tests pass with locale-format language codes
- [ ] Admin dashboard shows correct statistics

---

## Files to Modify

1. `trend_agent/services/translation_manager.py` - Add normalization logic
2. `trend_agent/services/translation.py` - Fix LibreTranslate and DeepL services

## Files NOT to Modify

- `web_interface/trends_viewer/views.py` - Middleware/views are correct
- `web_interface/trends_viewer/middleware.py` - Middleware is correct
- `web_interface/trends_viewer/models.py` - Database format is flexible
- `api/routers/translation.py` - Can be improved but not critical

---

## Summary

The fix requires adding a normalization layer in `TranslationManager` that converts locale-format codes (e.g., `zh-Hans`) to 2-letter ISO 639-1 codes (e.g., `zh`) before passing to API providers.

**Total Code Changes**: ~100 lines  
**Estimated Time**: 2-4 hours including testing  
**Risk Level**: LOW (isolated changes, clear contract)

