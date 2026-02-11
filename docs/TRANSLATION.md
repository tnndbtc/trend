# Translation Services Documentation

## Overview

The Trend Intelligence Platform includes comprehensive multi-language translation support, enabling automatic translation of trend content to multiple target languages with intelligent provider selection, caching, and fallback mechanisms.

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Translation Providers](#translation-providers)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [API Endpoints](#api-endpoints)
- [Pipeline Integration](#pipeline-integration)
- [Caching Strategy](#caching-strategy)
- [Cost Optimization](#cost-optimization)
- [Best Practices](#best-practices)

---

## Features

✅ **Multi-Provider Support**
- OpenAI GPT (high quality, context-aware)
- LibreTranslate (free, self-hosted, privacy-focused)
- DeepL (commercial, highest quality)

✅ **Intelligent Routing**
- Automatic provider selection
- Fallback on failure
- Cost-based prioritization

✅ **Performance Optimization**
- Redis-based caching (7-day TTL)
- Batch translation support
- Cache hit rate tracking

✅ **Production Ready**
- Retry logic with exponential backoff
- Cost tracking per character/token
- Prometheus metrics integration
- Comprehensive error handling

✅ **Cross-Language Support**
- 30+ languages supported
- Automatic language detection
- CJK, RTL, and romanization handling

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│           Translation Manager                        │
│  (Provider selection, caching, fallback)             │
└────┬──────────────┬───────────────┬──────────────────┘
     │              │               │
     ▼              ▼               ▼
┌──────────┐   ┌─────────────┐  ┌──────────┐
│ OpenAI   │   │LibreTranslate│ │  DeepL   │
│Translation│   │  Service    │  │Translation│
└──────────┘   └─────────────┘  └──────────┘
     │              │               │
     ▼              ▼               ▼
┌──────────┐   ┌─────────────┐  ┌──────────┐
│ OpenAI   │   │ LibreTranslate│ │  DeepL   │
│   API    │   │ (self-hosted)│  │   API    │
└──────────┘   └─────────────┘  └──────────┘

                     │
                     ▼
              ┌─────────────┐
              │Redis Cache  │
              │(Translation)│
              └─────────────┘
```

### Flow

1. **Request** → TranslationManager
2. **Check Cache** → Redis (if cached, return immediately)
3. **Select Provider** → Based on priority/availability
4. **Translate** → Call provider API
5. **Cache Result** → Store in Redis (7 days TTL)
6. **Fallback** → Try next provider if current fails
7. **Return** → Translated text

---

## Translation Providers

### 1. OpenAI Translation (GPT-based)

**Pros:**
- ✅ Excellent quality, context-aware
- ✅ Handles idioms and technical content well
- ✅ 50+ languages supported
- ✅ Preserves formatting and structure

**Cons:**
- ❌ More expensive than specialized APIs
- ❌ Slower than dedicated translation services

**Cost:** ~$0.0025 per 1k characters (GPT-4-turbo)

**Use Cases:**
- Technical documentation
- Marketing content
- Nuanced translations requiring context

### 2. LibreTranslate (Open Source)

**Pros:**
- ✅ Free and open-source
- ✅ Self-hosted (no data sent to third parties)
- ✅ No usage limits when self-hosted
- ✅ Privacy-focused

**Cons:**
- ❌ Lower quality than commercial services
- ❌ Requires hosting resources
- ❌ Limited to ~30 languages

**Cost:** Free (hosting costs only)

**Use Cases:**
- High-volume translation
- Privacy-sensitive content
- Cost-constrained projects

### 3. DeepL Translation

**Pros:**
- ✅ Industry-leading quality
- ✅ Excellent for European languages
- ✅ Fast response times
- ✅ Formal/informal tone control

**Cons:**
- ❌ Paid service
- ❌ Fewer languages than others (~30)

**Cost:** $20 per 1M characters

**Use Cases:**
- Professional translations
- European language pairs
- Quality-critical content

---

## Configuration

### Environment Variables

```bash
# OpenAI Translation
export OPENAI_API_KEY="sk-..."
export OPENAI_TRANSLATION_MODEL="gpt-4-turbo"  # or gpt-3.5-turbo

# LibreTranslate
export LIBRETRANSLATE_HOST="http://localhost:5000"
export LIBRETRANSLATE_API_KEY=""  # Optional for public instances

# DeepL
export DEEPL_API_KEY="your-deepl-key"
export DEEPL_IS_PRO=false  # true for Pro API

# Translation Cache
export TRANSLATION_CACHE_TTL=604800  # 7 days in seconds

# Provider Priority (comma-separated)
export TRANSLATION_PROVIDER_PRIORITY="libretranslate,openai,deepl"
```

### Docker Compose

Start LibreTranslate service:

```bash
# Start with translation profile
docker compose --profile translation up -d libretranslate

# Check status
docker logs trend-libretranslate

# Access at http://localhost:5000
```

### Service Configuration

```python
from trend_agent.services import ServiceFactory

# Custom configuration
config = {
    "libretranslate_host": "http://libretranslate:5000",
    "translation_provider_priority": ["libretranslate", "openai", "deepl"],
    "translation_cache_ttl": 604800,  # 7 days
}

factory = ServiceFactory(config=config)
translation_manager = factory.get_translation_manager()
```

---

## Usage Examples

### Direct Translation

```python
from trend_agent.services import get_service_factory

async def translate_example():
    factory = get_service_factory()
    translation_manager = factory.get_translation_manager()

    # Single translation
    translated = await translation_manager.translate(
        text="Hello, world!",
        target_language="es",
        source_language="en"  # Optional, auto-detect if not provided
    )
    print(translated)  # "¡Hola, mundo!"

    # With preferred provider
    translated = await translation_manager.translate(
        text="Good morning",
        target_language="fr",
        preferred_provider="deepl"  # Use DeepL specifically
    )
    print(translated)  # "Bonjour"

    # Auto-detect source language
    translated = await translation_manager.translate(
        text="Bonjour le monde",
        target_language="en"
    )
    print(translated)  # "Hello world"
```

### Batch Translation

```python
async def batch_translate_example():
    factory = get_service_factory()
    translation_manager = factory.get_translation_manager()

    texts = [
        "Hello",
        "Goodbye",
        "Thank you",
        "How are you?"
    ]

    # Translate all to Spanish
    translations = await translation_manager.translate_batch(
        texts=texts,
        target_language="es",
        source_language="en"
    )

    for original, translated in zip(texts, translations):
        print(f"{original} → {translated}")

    # Output:
    # Hello → Hola
    # Goodbye → Adiós
    # Thank you → Gracias
    # How are you? → ¿Cómo estás?
```

### Language Detection

```python
async def detect_language_example():
    factory = get_service_factory()
    translation_manager = factory.get_translation_manager()

    text = "Bonjour, comment allez-vous?"
    detected_lang = await translation_manager.detect_language(text)
    print(f"Detected language: {detected_lang}")  # "fr"

    # Get supported languages
    languages = translation_manager.get_supported_languages()
    print(f"Supported languages: {languages}")
    # ['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'zh', ...]
```

### Usage Statistics

```python
async def get_stats_example():
    factory = get_service_factory()
    translation_manager = factory.get_translation_manager()

    # Perform some translations...
    await translation_manager.translate("Hello", "es")
    await translation_manager.translate("Goodbye", "fr")

    # Get stats
    stats = translation_manager.get_stats()
    print(f"Total translations: {stats['total_translations']}")
    print(f"Cache hit rate: {stats['cache_stats']['hit_rate_percent']}%")
    print(f"Provider usage: {stats['provider_usage']}")
    print(f"Provider failures: {stats['provider_failures']}")
```

---

## API Endpoints

### POST /api/v1/translation/translate

Translate single text.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/translation/translate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!",
    "target_language": "es",
    "source_language": "en",
    "preferred_provider": "libretranslate"
  }'
```

**Response:**
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

### POST /api/v1/translation/translate/batch

Translate multiple texts.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/translation/translate/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["Hello", "Goodbye", "Thank you"],
    "target_language": "fr",
    "source_language": "en"
  }'
```

**Response:**
```json
{
  "translations": [
    {
      "original_text": "Hello",
      "translated_text": "Bonjour",
      "source_language": "en",
      "target_language": "fr",
      "provider_used": "batch",
      "cached": false
    },
    ...
  ],
  "total_translations": 3,
  "provider_stats": {
    "libretranslate": 3
  }
}
```

### POST /api/v1/translation/detect-language

Detect text language.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/translation/detect-language?text=Bonjour+le+monde"
```

**Response:**
```json
{
  "text": "Bonjour le monde",
  "detected_language": "fr",
  "confidence": null
}
```

### GET /api/v1/translation/languages

Get supported languages.

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/translation/languages"
```

**Response:**
```json
{
  "languages": ["en", "es", "fr", "de", "it", "pt", "ru", "ja", "zh", "ko", ...],
  "count": 30
}
```

### GET /api/v1/translation/stats

Get translation statistics.

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/translation/stats"
```

**Response:**
```json
{
  "total_translations": 150,
  "cache_hits": 45,
  "cache_hit_rate_percent": 30.0,
  "provider_usage": {
    "libretranslate": 80,
    "openai": 25,
    "deepl": 0
  },
  "provider_failures": {
    "libretranslate": 0,
    "openai": 0,
    "deepl": 0
  }
}
```

---

## Pipeline Integration

### TranslationStage

Automatically translate content during pipeline processing.

```python
from trend_agent.services import get_service_factory
from trend_agent.processing.translation import TranslationStage
from trend_agent.processing.pipeline import ProcessingPipeline

# Get translation manager
factory = get_service_factory()
translation_manager = factory.get_translation_manager()

# Create translation stage
translation_stage = TranslationStage(
    translation_manager=translation_manager,
    target_languages=["es", "fr", "de"],  # Translate to Spanish, French, German
    translate_title=True,
    translate_description=True,
    translate_content=False,  # Skip content (expensive)
    min_text_length=3,
)

# Add to pipeline
pipeline = ProcessingPipeline()
pipeline.add_stage(translation_stage)

# Process items
result = await pipeline.run(items)

# Access translated content
for item in result.metadata['processed_items']:
    print(f"Original: {item.title}")
    print(f"Spanish: {item.metadata.get('translated_title_es')}")
    print(f"French: {item.metadata.get('translated_title_fr')}")
    print(f"German: {item.metadata.get('translated_title_de')}")
```

### Cross-Language Normalization

Enable cross-language deduplication and clustering.

```python
from trend_agent.processing.translation import CrossLanguageNormalizer

# Create normalizer
normalizer = CrossLanguageNormalizer()

# Add to pipeline (before deduplication stage)
pipeline = ProcessingPipeline()
pipeline.add_stage(normalizer)
pipeline.add_stage(deduplication_stage)

# Items now have normalized_title_latin in metadata
# This enables cross-language duplicate detection
```

---

## Caching Strategy

### How Caching Works

1. **Cache Key Generation**
   - MD5 hash of `text + source_lang + target_lang`
   - Example: `translation:en:es:a1b2c3d4e5f6...`

2. **Cache Hit**
   - Check Redis before API call
   - Return immediately if found
   - Update cache hit counter

3. **Cache Miss**
   - Call translation provider
   - Store result in Redis with TTL
   - Return translated text

4. **TTL (Time To Live)**
   - Default: 7 days (604,800 seconds)
   - Configurable via `TRANSLATION_CACHE_TTL`

### Cache Statistics

```python
# Get cache stats
stats = translation_manager.get_stats()
cache_stats = stats['cache_stats']

print(f"Cache hits: {cache_stats['cache_hits']}")
print(f"Cache misses: {cache_stats['cache_misses']}")
print(f"Hit rate: {cache_stats['hit_rate_percent']}%")
```

### Manual Cache Control

```python
# Clear all cached translations
if translation_manager.cache:
    await translation_manager.cache.clear()
    print("Translation cache cleared")

# Check specific translation in cache
cached = await translation_manager.cache.get(
    text="Hello",
    source_lang="en",
    target_lang="es"
)
if cached:
    print(f"Found in cache: {cached}")
```

---

## Cost Optimization

### Strategies

1. **Use Free Provider First**
   ```python
   # Default priority: libretranslate → openai → deepl
   config = {
       "translation_provider_priority": ["libretranslate", "openai", "deepl"]
   }
   ```

2. **Enable Caching**
   - Reduces duplicate translations by 30-50%
   - Set appropriate TTL (default: 7 days)

3. **Batch Translation**
   - More efficient than individual calls
   - Reduces API overhead

4. **Use Cheaper Models**
   ```python
   # Use GPT-3.5-turbo instead of GPT-4
   config = {
       "openai_translation_model": "gpt-3.5-turbo"
   }
   ```

5. **Selective Translation**
   ```python
   # Only translate titles, not full content
   translation_stage = TranslationStage(
       translation_manager=translation_manager,
       target_languages=["es"],
       translate_title=True,
       translate_description=False,
       translate_content=False,  # Save costs
   )
   ```

### Cost Comparison

| Provider | Cost per 1M chars | Quality | Speed |
|----------|------------------|---------|-------|
| LibreTranslate | $0 (self-hosted) | Medium | Fast |
| OpenAI (GPT-3.5) | ~$1.25 | High | Medium |
| OpenAI (GPT-4) | ~$2.50 | Very High | Medium |
| DeepL | $20.00 | Highest | Fast |

### Example Cost Calculation

```python
# 1000 items, average 50 chars per title
# Translate to 3 languages
# Total: 1000 * 50 * 3 = 150,000 chars

# LibreTranslate: $0
# OpenAI GPT-3.5: ~$0.19
# OpenAI GPT-4: ~$0.38
# DeepL: ~$3.00
```

---

## Best Practices

### 1. Use Provider Priority

Start with free/cheap providers, fallback to expensive ones:

```python
config = {
    "translation_provider_priority": [
        "libretranslate",  # Free, try first
        "openai",          # Paid, good quality
        "deepl"            # Paid, best quality (last resort)
    ]
}
```

### 2. Monitor Cache Hit Rate

Aim for >30% cache hit rate:

```python
stats = translation_manager.get_stats()
hit_rate = stats['cache_stats']['hit_rate_percent']

if hit_rate < 30:
    logger.warning(f"Low cache hit rate: {hit_rate}%")
```

### 3. Handle Failures Gracefully

```python
try:
    translated = await translation_manager.translate(text, "es")
except TranslationError as e:
    logger.error(f"Translation failed: {e}")
    # Fallback to original text or default translation
    translated = text
```

### 4. Batch When Possible

```python
# ✅ Good - Single API call
translations = await translation_manager.translate_batch(
    texts=["Hello", "Goodbye", "Thanks"],
    target_language="es"
)

# ❌ Bad - Multiple API calls
translations = []
for text in ["Hello", "Goodbye", "Thanks"]:
    t = await translation_manager.translate(text, "es")
    translations.append(t)
```

### 5. Set Appropriate TTL

```python
# Evergreen content: Long TTL (30 days)
cache = TranslationCache(redis_repo, ttl_seconds=2592000)

# Time-sensitive content: Short TTL (1 day)
cache = TranslationCache(redis_repo, ttl_seconds=86400)
```

### 6. Limit Translation Scope

Don't translate everything:

```python
# Only translate if text is substantial
min_length = 10

if len(text) >= min_length:
    translated = await translation_manager.translate(text, "es")
else:
    translated = text  # Skip short texts
```

---

## Troubleshooting

### LibreTranslate Not Available

```
Error: LibreTranslate not available
```

**Solution**: Start LibreTranslate service:

```bash
docker compose --profile translation up -d libretranslate
```

### API Key Missing

```
Error: OpenAI API key required
```

**Solution**: Set environment variable:

```bash
export OPENAI_API_KEY="sk-..."
```

### Low Quality Translations

**Solution**: Change provider priority:

```bash
# Use DeepL or OpenAI instead of LibreTranslate
export TRANSLATION_PROVIDER_PRIORITY="deepl,openai,libretranslate"
```

### High Costs

**Solution**:
1. Check cache hit rate
2. Use LibreTranslate for high-volume
3. Reduce translation scope
4. Use cheaper models (GPT-3.5)

```python
stats = translation_manager.get_stats()
print(f"Provider usage: {stats['provider_usage']}")
print(f"Cache hit rate: {stats['cache_stats']['hit_rate_percent']}%")
```

---

## Summary

✅ **Implemented**: Production-ready translation services
✅ **Providers**: OpenAI, LibreTranslate, DeepL
✅ **Features**: Caching, fallback, batch translation, cost tracking
✅ **Integration**: API endpoints, pipeline stages, service factory
✅ **Optimization**: Redis caching, provider selection, monitoring

**Next Steps**: See [AI Services Documentation](./AI_SERVICES.md) for related AI capabilities.
