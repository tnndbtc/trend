# AI Trend Intelligence Platform - Translation Pipeline

## Overview

The translation pipeline enables the platform to:
1. **Ingest content in any language** (176 supported languages)
2. **Process in canonical language** (English) for uniformity
3. **Serve content in user's preferred language** (on-demand translation)
4. **Cache translations** to minimize costs

---

## Translation Strategy

### Canonical Language Approach

```
┌─────────────────────────────────────────────────────────┐
│  Multi-Language Sources                                 │
│  (Japanese YouTube, Spanish news, French Reddit, etc.)  │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 1: Language Detection                            │
│  - Detect source language (fasttext)                    │
│  - Store: language_code, language_confidence            │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
   ┌─────────┐      ┌──────────────┐
   │ English │      │ Non-English  │
   │ Content │      │ Content      │
   └────┬────┘      └──────┬───────┘
        │                  │
        │                  ▼
        │          ┌────────────────────┐
        │          │ STAGE 2: Translate │
        │          │ to English         │
        │          │ (Canonical)        │
        │          └──────┬─────────────┘
        │                 │
        └────────┬────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 3: Process in English                            │
│  - Clustering (embeddings work better in single lang)   │
│  - LLM analysis (prompts in English)                    │
│  - Deduplication (cross-language duplicate detection)   │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 4: Store Multi-Language Data                     │
│  - Original text (any language)                         │
│  - English translation (canonical)                      │
│  - Language metadata                                    │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│  STAGE 5: Serve in User's Language (On-Demand)         │
│  - User requests trend in Spanish                       │
│  - Check cache for EN→ES translation                    │
│  - If not cached: translate + cache                     │
│  - Return translated content                            │
└─────────────────────────────────────────────────────────┘
```

---

## Language Detection

### Library: fastText

**Model:** `lid.176.ftz` (compressed, 917 KB)
**Languages:** 176 languages
**Accuracy:** 93.7% on test set
**Speed:** 1000+ items/second

### Implementation

```python
import fasttext

# Load model (one-time, cache in memory)
model = fasttext.load_model("lid.176.ftz")

def detect_language(text: str) -> tuple[str, float]:
    """
    Detect language from text.

    Returns:
        (language_code, confidence)
        e.g., ("en", 0.95), ("ja", 0.87), ("es", 0.92)
    """
    # fastText expects text without newlines
    text = text.replace("\n", " ").strip()

    if not text:
        return ("unknown", 0.0)

    # Predict
    predictions = model.predict(text, k=1)
    lang_label = predictions[0][0]  # "__label__en"
    confidence = predictions[1][0]  # 0.95

    # Parse language code
    lang_code = lang_label.replace("__label__", "")

    return (lang_code, confidence)
```

### Batch Detection

```python
async def detect_languages_batch(items: List[NormalizedItem]):
    """Detect languages for multiple items efficiently"""

    texts = [f"{item.title} {item.description}" for item in items]

    # Batch predict (much faster than one-by-one)
    predictions = model.predict(texts, k=1)

    for item, (labels, confidences) in zip(items, zip(predictions[0], predictions[1])):
        lang_code = labels[0].replace("__label__", "")
        confidence = confidences[0]

        item.language = lang_code if confidence > 0.7 else "unknown"
        item.language_confidence = confidence

    return items
```

---

## Translation Service

### Provider: Pluggable Architecture

```python
class TranslationProvider(ABC):
    """Abstract interface for translation services"""

    @abstractmethod
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """Translate text from source_lang to target_lang"""
        pass

    @abstractmethod
    async def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str
    ) -> List[str]:
        """Translate multiple texts efficiently"""
        pass

    @property
    @abstractmethod
    def cost_per_char(self) -> float:
        """Cost in USD per character"""
        pass
```

### Provider Implementations

#### 1. OpenAI GPT-4o (High Quality)

```python
class OpenAITranslationProvider(TranslationProvider):
    """Use OpenAI GPT-4o for translation"""

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        prompt = f"""
Translate the following text from {source_lang} to {target_lang}.
Preserve the meaning, tone, and formatting. Do not add explanations.

Text:
{text}

Translation:"""

        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=len(text) * 2,  # Estimate
            temperature=0.3  # Low temperature for consistency
        )

        return response.choices[0].message.content.strip()

    @property
    def cost_per_char(self) -> float:
        # gpt-4o-mini: $0.15/1M input tokens, ~4 chars/token
        return 0.15 / 1_000_000 / 4  # ~$0.0000000375 per char
```

#### 2. LibreTranslate (Open Source, Local)

```python
class LibreTranslateProvider(TranslationProvider):
    """Use self-hosted LibreTranslate (free, privacy-friendly)"""

    def __init__(self, api_url: str = "http://localhost:5000"):
        self.api_url = api_url

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.api_url}/translate",
                json={
                    "q": text,
                    "source": source_lang,
                    "target": target_lang,
                    "format": "text"
                }
            ) as response:
                data = await response.json()
                return data["translatedText"]

    @property
    def cost_per_char(self) -> float:
        return 0.0  # Self-hosted, no per-request cost
```

#### 3. DeepL (Best Quality, Paid)

```python
class DeepLTranslationProvider(TranslationProvider):
    """Use DeepL API (highest quality, but costly)"""

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api-free.deepl.com/v2/translate",
                data={
                    "auth_key": os.getenv("DEEPL_API_KEY"),
                    "text": text,
                    "source_lang": source_lang.upper(),
                    "target_lang": target_lang.upper()
                }
            ) as response:
                data = await response.json()
                return data["translations"][0]["text"]

    @property
    def cost_per_char(self) -> float:
        # DeepL: €20/1M characters
        return 22 / 1_000_000  # ~$0.000022 per char (€ to $ ~1.1)
```

### Provider Selection Strategy

```python
class TranslationService:
    """Intelligent provider selection"""

    def __init__(self):
        self.providers = {
            "libre": LibreTranslateProvider(),
            "openai": OpenAITranslationProvider(),
            "deepl": DeepLTranslationProvider()
        }

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        quality: str = "auto"
    ) -> str:
        """
        Translate with automatic provider selection.

        Args:
            quality: "auto", "fast", "balanced", "high"
        """

        # Select provider based on quality preference
        if quality == "fast":
            provider = self.providers["libre"]  # Fastest, free
        elif quality == "high":
            provider = self.providers["deepl"]  # Highest quality
        elif quality == "balanced":
            provider = self.providers["openai"]  # Good quality, moderate cost
        else:  # auto
            # Use libre for common languages, OpenAI for rare ones
            if source_lang in ["es", "fr", "de", "it", "pt"]:
                provider = self.providers["libre"]
            else:
                provider = self.providers["openai"]

        # Translate
        translation = await provider.translate(text, source_lang, target_lang)

        return translation
```

---

## Translation Caching

### Cache Key Design

```python
def translation_cache_key(text: str, source_lang: str, target_lang: str) -> str:
    """Generate cache key for translation"""

    # Hash text for compact key
    text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

    return f"translation:{source_lang}:{target_lang}:{text_hash}"
```

### Cache Implementation

```python
class TranslationCache:
    """Redis-based translation cache"""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = 2592000  # 30 days

    async def get(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """Get cached translation"""

        key = translation_cache_key(text, source_lang, target_lang)
        cached = await self.redis.get(key)

        if cached:
            # Track cache hit
            await self.redis.incr("translation_cache_hits")
            return cached.decode()

        await self.redis.incr("translation_cache_misses")
        return None

    async def set(self, text: str, source_lang: str, target_lang: str, translation: str):
        """Cache translation"""

        key = translation_cache_key(text, source_lang, target_lang)
        await self.redis.setex(key, self.ttl, translation)

    async def get_hit_rate(self) -> float:
        """Calculate cache hit rate"""

        hits = int(await self.redis.get("translation_cache_hits") or 0)
        misses = int(await self.redis.get("translation_cache_misses") or 0)

        if hits + misses == 0:
            return 0.0

        return hits / (hits + misses)
```

### Translation with Caching

```python
async def translate_with_cache(
    text: str,
    source_lang: str,
    target_lang: str
) -> str:
    """Translate text, using cache when possible"""

    # Check cache
    cached = await translation_cache.get(text, source_lang, target_lang)
    if cached:
        return cached

    # Translate
    translation = await translation_service.translate(text, source_lang, target_lang)

    # Cache result
    await translation_cache.set(text, source_lang, target_lang, translation)

    return translation
```

---

## Batch Translation

### Why Batch?

- **Cost reduction:** Some providers charge per request, not per character
- **Latency reduction:** One API call instead of N calls
- **Rate limit efficiency:** Use quota more effectively

### Implementation

```python
async def translate_batch(
    items: List[NormalizedItem],
    source_lang: str,
    target_lang: str
) -> List[NormalizedItem]:
    """Translate multiple items efficiently"""

    # Separate cached vs uncached
    cached_items = []
    uncached_items = []

    for item in items:
        cached_translation = await translation_cache.get(
            item.title + " " + item.description,
            source_lang,
            target_lang
        )

        if cached_translation:
            item.translated_text = cached_translation
            cached_items.append(item)
        else:
            uncached_items.append(item)

    if not uncached_items:
        return items  # All cached!

    # Batch translate uncached items
    texts_to_translate = [
        f"{item.title}\n\n{item.description}"
        for item in uncached_items
    ]

    # Use OpenAI for batch translation (supports multiple texts in one prompt)
    prompt = f"""
Translate the following {len(texts_to_translate)} texts from {source_lang} to {target_lang}.
Separate translations with "---".

{chr(10).join([f"Text {i+1}:\n{text}\n" for i, text in enumerate(texts_to_translate)])}

Translations:
"""

    response = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=sum(len(t) for t in texts_to_translate) * 2
    )

    translations = response.choices[0].message.content.split("---")

    # Assign translations and cache
    for item, translation in zip(uncached_items, translations):
        item.translated_text = translation.strip()

        # Cache
        await translation_cache.set(
            item.title + " " + item.description,
            source_lang,
            target_lang,
            item.translated_text
        )

    return cached_items + uncached_items
```

---

## On-Demand Translation API

### API Endpoint

```python
@app.get("/api/v1/trends/{trend_id}")
async def get_trend(
    trend_id: str,
    lang: str = "en",  # Target language (ISO 639-1)
    translate: bool = True  # Whether to translate
):
    """
    Get trend with optional translation.

    Examples:
    - /api/v1/trends/123?lang=es&translate=true  → Translate to Spanish
    - /api/v1/trends/123?lang=en&translate=false → Return English (canonical)
    """

    # Fetch trend from database
    trend = await trend_repository.get_by_id(trend_id)

    if not trend:
        raise HTTPException(status_code=404, detail="Trend not found")

    # If requesting English or no translation, return as-is
    if lang == "en" or not translate:
        return trend

    # Translate to requested language
    trend.title = await translate_with_cache(trend.title, "en", lang)
    trend.summary = await translate_with_cache(trend.summary, "en", lang)

    # Translate sample topics
    for topic in trend.topics[:5]:  # Limit to avoid huge translation costs
        topic.title = await translate_with_cache(topic.title, topic.language, lang)

    return trend
```

---

## Cross-Language Duplicate Detection

### Challenge

Same story in different languages should be detected as duplicates:
- English: "OpenAI releases GPT-5"
- Spanish: "OpenAI lanza GPT-5"
- Japanese: "OpenAIがGPT-5をリリース"

### Solution: Translate Before Embedding

```python
async def generate_embedding(item: NormalizedItem) -> np.ndarray:
    """Generate embedding for item (translate if needed)"""

    # Prepare text
    text = f"{item.title} {item.description}"

    # If not English, translate first
    if item.language != "en":
        text = await translate_with_cache(text, item.language, "en")

    # Generate embedding (in English)
    embedding = await embedding_service.embed(text)

    return embedding
```

**Benefit:** Embeddings are in same semantic space, enabling cross-language deduplication

---

## Language-Specific Considerations

### Right-to-Left Languages (Arabic, Hebrew)

**Store:** Store text in original direction
**Render:** Let frontend handle directionality (CSS `direction: rtl`)

### CJK Languages (Chinese, Japanese, Korean)

**Issue:** Character count != semantic length
**Solution:** Use word segmentation for length limits

```python
import jieba  # Chinese
import fugashi  # Japanese
from konlpy.tag import Okt  # Korean

def segment_cjk(text: str, language: str) -> List[str]:
    """Segment CJK text into words"""

    if language == "zh":
        return list(jieba.cut(text))
    elif language == "ja":
        tagger = fugashi.Tagger()
        return [word.surface for word in tagger(text)]
    elif language == "ko":
        okt = Okt()
        return okt.morphs(text)
    else:
        return text.split()
```

### Romanization (Cyrillic, Greek, etc.)

**Use case:** Make non-Latin scripts searchable by Latin keyboard users

```python
from unidecode import unidecode

def romanize(text: str) -> str:
    """Convert to Latin alphabet"""
    # "Привет" → "Privet"
    # "Γεια σου" → "Geia sou"
    return unidecode(text)
```

**Storage:**
```python
item.title_romanized = romanize(item.title)  # Store both original and romanized
```

---

## Translation Quality Monitoring

### Metrics

**Translation Coverage:**
```python
coverage = (items_with_translation / total_items) * 100
```

**Cache Hit Rate:**
```python
hit_rate = (cache_hits / (cache_hits + cache_misses)) * 100
```

**Cost Tracking:**
```python
# Track per provider
cost_openai = chars_translated_openai * openai_provider.cost_per_char
cost_deepl = chars_translated_deepl * deepl_provider.cost_per_char
total_cost = cost_openai + cost_deepl
```

### Quality Checks

**Back-Translation Test:**
```python
async def test_translation_quality(text: str, source_lang: str, target_lang: str) -> float:
    """
    Measure translation quality via back-translation.

    Returns:
        Similarity score (0.0 - 1.0)
    """

    # Translate forward
    translation = await translation_service.translate(text, source_lang, target_lang)

    # Translate back
    back_translation = await translation_service.translate(translation, target_lang, source_lang)

    # Compute similarity
    from difflib import SequenceMatcher
    similarity = SequenceMatcher(None, text, back_translation).ratio()

    return similarity
```

---

## Cost Optimization

### Strategies

1. **Cache aggressively** (30-day TTL)
2. **Use cheap providers for common languages** (LibreTranslate for ES, FR, DE)
3. **Translate on-demand**, not proactively
4. **Limit translation scope** (title + summary only, not full content)
5. **Batch requests** to reduce overhead

### Cost Estimation

**Assumptions:**
- 10,000 items/day
- Average title + description: 200 characters
- 50% non-English items → 5,000 need translation
- Cache hit rate: 30%

**Daily Translations:**
- 5,000 items × 70% (cache miss) = 3,500 translations
- 3,500 × 200 chars = 700,000 characters/day

**Monthly Cost:**
- OpenAI: 700k chars/day × 30 days × $0.0000000375/char = **$0.79/month**
- DeepL: 700k chars/day × 30 days × $0.000022/char = **$462/month**
- LibreTranslate: **$0/month** (self-hosted)

**Recommendation:** Use LibreTranslate for most languages, OpenAI for rare ones

---

## Next Steps

- [AI Agent Integration](./architecture-ai-agents.md) - How agents consume multi-language trends
- [Scaling Roadmap](./architecture-scaling.md) - Scaling translation infrastructure
- [Tech Stack](./architecture-techstack.md) - Translation library choices
