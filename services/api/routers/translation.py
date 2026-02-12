"""
Translation API endpoints.

Provides REST API for text translation using multiple providers
with automatic caching and fallback.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from trend_agent.services import get_service_factory

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/translation",
    tags=["translation"],
    responses={404: {"description": "Not found"}},
)


# ============================================================================
# Request/Response Models
# ============================================================================


class TranslateRequest(BaseModel):
    """Request model for translation."""

    text: str = Field(..., description="Text to translate", min_length=1, max_length=10000)
    target_language: str = Field(..., description="Target language code (ISO 639-1)", min_length=2, max_length=5)
    source_language: Optional[str] = Field(None, description="Source language code (auto-detect if not provided)")
    preferred_provider: Optional[str] = Field(None, description="Preferred translation provider (openai, libretranslate, deepl)")

    class Config:
        schema_extra = {
            "example": {
                "text": "Hello, world!",
                "target_language": "es",
                "source_language": "en",
                "preferred_provider": "libretranslate",
            }
        }


class BatchTranslateRequest(BaseModel):
    """Request model for batch translation."""

    texts: List[str] = Field(..., description="List of texts to translate", min_items=1, max_items=100)
    target_language: str = Field(..., description="Target language code")
    source_language: Optional[str] = Field(None, description="Source language code")
    preferred_provider: Optional[str] = Field(None, description="Preferred provider")

    class Config:
        schema_extra = {
            "example": {
                "texts": ["Hello", "Goodbye", "Thank you"],
                "target_language": "fr",
                "source_language": "en",
            }
        }


class TranslateResponse(BaseModel):
    """Response model for translation."""

    original_text: str
    translated_text: str
    source_language: Optional[str]
    target_language: str
    provider_used: str
    cached: bool = Field(default=False, description="Whether result was cached")

    class Config:
        schema_extra = {
            "example": {
                "original_text": "Hello, world!",
                "translated_text": "¡Hola, mundo!",
                "source_language": "en",
                "target_language": "es",
                "provider_used": "libretranslate",
                "cached": False,
            }
        }


class BatchTranslateResponse(BaseModel):
    """Response model for batch translation."""

    translations: List[TranslateResponse]
    total_translations: int
    provider_stats: dict = Field(default_factory=dict)


class LanguageDetectionResponse(BaseModel):
    """Response model for language detection."""

    text: str
    detected_language: str
    confidence: Optional[float] = None

    class Config:
        schema_extra = {
            "example": {
                "text": "Bonjour le monde",
                "detected_language": "fr",
                "confidence": 0.95,
            }
        }


class SupportedLanguagesResponse(BaseModel):
    """Response model for supported languages."""

    languages: List[str]
    count: int


class TranslationStatsResponse(BaseModel):
    """Response model for translation statistics."""

    total_translations: int
    cache_hits: int
    cache_hit_rate_percent: float
    provider_usage: dict
    provider_failures: dict


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/translate", response_model=TranslateResponse)
async def translate_text(request: TranslateRequest):
    """
    Translate text to target language.

    Automatically selects the best available translation provider
    and caches results to minimize costs.

    **Providers:**
    - LibreTranslate (free, self-hosted)
    - OpenAI (paid, high quality)
    - DeepL (paid, highest quality)

    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/translation/translate" \\
      -H "Content-Type: application/json" \\
      -d '{
        "text": "Hello, world!",
        "target_language": "es",
        "source_language": "en"
      }'
    ```
    """
    try:
        # Get translation manager from factory
        factory = get_service_factory()
        translation_manager = factory.get_translation_manager()

        # Check cache first
        cache_hit = False
        if translation_manager.cache:
            cached = await translation_manager.cache.get(
                request.text, request.source_language, request.target_language
            )
            if cached:
                cache_hit = True
                return TranslateResponse(
                    original_text=request.text,
                    translated_text=cached,
                    source_language=request.source_language,
                    target_language=request.target_language,
                    provider_used="cache",
                    cached=True,
                )

        # Translate
        translated = await translation_manager.translate(
            text=request.text,
            target_language=request.target_language,
            source_language=request.source_language,
            preferred_provider=request.preferred_provider,
        )

        # Determine which provider was used (from stats)
        stats = translation_manager.get_stats()
        provider_used = "unknown"
        if stats["provider_usage"]:
            # Find provider with most recent increase
            provider_used = max(
                stats["provider_usage"], key=stats["provider_usage"].get
            )

        return TranslateResponse(
            original_text=request.text,
            translated_text=translated,
            source_language=request.source_language,
            target_language=request.target_language,
            provider_used=provider_used,
            cached=cache_hit,
        )

    except Exception as e:
        logger.error(f"Translation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


@router.post("/translate/batch", response_model=BatchTranslateResponse)
async def translate_batch(request: BatchTranslateRequest):
    """
    Translate multiple texts in a batch.

    More efficient than individual translation requests when translating
    multiple texts to the same target language.

    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/translation/translate/batch" \\
      -H "Content-Type: application/json" \\
      -d '{
        "texts": ["Hello", "Goodbye", "Thank you"],
        "target_language": "fr",
        "source_language": "en"
      }'
    ```
    """
    try:
        factory = get_service_factory()
        translation_manager = factory.get_translation_manager()

        # Translate batch
        translations = await translation_manager.translate_batch(
            texts=request.texts,
            target_language=request.target_language,
            source_language=request.source_language,
            preferred_provider=request.preferred_provider,
        )

        # Build response
        translation_responses = []
        for original, translated in zip(request.texts, translations):
            translation_responses.append(
                TranslateResponse(
                    original_text=original,
                    translated_text=translated,
                    source_language=request.source_language,
                    target_language=request.target_language,
                    provider_used="batch",
                    cached=False,  # TODO: Track individual cache hits
                )
            )

        stats = translation_manager.get_stats()

        return BatchTranslateResponse(
            translations=translation_responses,
            total_translations=len(translations),
            provider_stats=stats["provider_usage"],
        )

    except Exception as e:
        logger.error(f"Batch translation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Batch translation failed: {str(e)}"
        )


@router.post("/detect-language", response_model=LanguageDetectionResponse)
async def detect_language(
    text: str = Query(..., description="Text to detect language for", min_length=3)
):
    """
    Detect the language of given text.

    Uses available translation providers to detect the source language.

    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/translation/detect-language?text=Bonjour+le+monde"
    ```
    """
    try:
        factory = get_service_factory()
        translation_manager = factory.get_translation_manager()

        detected_lang = await translation_manager.detect_language(text)

        return LanguageDetectionResponse(
            text=text[:100],  # Limit text in response
            detected_language=detected_lang,
        )

    except Exception as e:
        logger.error(f"Language detection failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Language detection failed: {str(e)}"
        )


@router.get("/languages", response_model=SupportedLanguagesResponse)
async def get_supported_languages():
    """
    Get list of supported language codes.

    Returns the union of all languages supported by available providers.

    **Example:**
    ```bash
    curl -X GET "http://localhost:8000/translation/languages"
    ```
    """
    try:
        factory = get_service_factory()
        translation_manager = factory.get_translation_manager()

        languages = translation_manager.get_supported_languages()

        return SupportedLanguagesResponse(languages=languages, count=len(languages))

    except Exception as e:
        logger.error(f"Failed to get supported languages: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get languages: {str(e)}"
        )


@router.get("/stats", response_model=TranslationStatsResponse)
async def get_translation_stats():
    """
    Get translation service statistics.

    Returns usage statistics including cache hit rate,
    provider usage, and failure counts.

    **Example:**
    ```bash
    curl -X GET "http://localhost:8000/translation/stats"
    ```
    """
    try:
        factory = get_service_factory()
        translation_manager = factory.get_translation_manager()

        stats = translation_manager.get_stats()

        cache_stats = stats.get("cache_stats", {})

        return TranslationStatsResponse(
            total_translations=stats["total_translations"],
            cache_hits=cache_stats.get("cache_hits", 0),
            cache_hit_rate_percent=cache_stats.get("hit_rate_percent", 0.0),
            provider_usage=stats["provider_usage"],
            provider_failures=stats["provider_failures"],
        )

    except Exception as e:
        logger.error(f"Failed to get translation stats: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get stats: {str(e)}"
        )
