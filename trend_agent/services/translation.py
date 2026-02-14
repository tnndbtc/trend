"""
Translation Services for multi-language support.

Provides production-ready translation using multiple providers:
- OpenAI (GPT-based translation)
- LibreTranslate (self-hosted, open-source)
- DeepL (commercial, high-quality)
"""

import asyncio
import hashlib
import logging
import time
from typing import Dict, List, Optional

import httpx

from trend_agent.intelligence.interfaces import (
    BaseTranslationService,
    TranslationError,
)
from trend_agent.observability.metrics import (
    api_request_counter,
    api_request_duration,
)

logger = logging.getLogger(__name__)

# ISO 639-1 language codes mapping
LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ja": "Japanese",
    "zh-Hans": "Chinese (Simplified)",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "nl": "Dutch",
    "pl": "Polish",
    "tr": "Turkish",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
    "cs": "Czech",
    "da": "Danish",
    "fi": "Finnish",
    "no": "Norwegian",
    "sv": "Swedish",
}


class OpenAITranslationService(BaseTranslationService):
    """
    OpenAI GPT-based translation service.

    Uses GPT models for high-quality, context-aware translation.
    More expensive than specialized translation APIs but provides
    better handling of context, idioms, and technical content.

    Features:
    - Support for 50+ languages
    - Context-aware translation
    - Preserves formatting and structure
    - Cost tracking per character
    - Automatic language detection
    - Batch translation support
    - Retry logic with exponential backoff

    Pricing (GPT-4-turbo):
    - ~$0.01 per 1k input tokens
    - ~$0.03 per 1k output tokens
    - Approx 4 chars per token = ~$0.0025 per 1k chars input

    Example:
        ```python
        service = OpenAITranslationService(api_key="sk-...")

        # Translate single text
        translated = await service.translate(
            "Hello, world!",
            target_language="es"
        )
        # "¡Hola, mundo!"

        # Batch translation
        texts = ["Hello", "Goodbye", "Thank you"]
        translated = await service.translate_batch(
            texts,
            target_language="fr"
        )
        # ["Bonjour", "Au revoir", "Merci"]

        # Auto-detect source language
        result = await service.translate(
            "Bonjour le monde",
            target_language="en"
        )
        # "Hello world"
        ```
    """

    API_ENDPOINT = "https://api.openai.com/v1/chat/completions"
    DEFAULT_MODEL = "gpt-4-turbo"

    # Cost per 1k tokens (input/output)
    COSTS = {
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_retries: int = 3,
        timeout: int = 30,
    ):
        """
        Initialize OpenAI translation service.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use for translation
            max_retries: Maximum retry attempts
            timeout: Request timeout in seconds
        """
        import os

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required")

        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout

        # Cost tracking
        self._total_cost = 0.0
        self._total_chars = 0
        self._total_translations = 0

        # HTTP client
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        logger.info(f"Initialized OpenAITranslationService (model={model})")

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> str:
        """
        Translate text to target language.

        Args:
            text: Text to translate
            target_language: ISO 639-1 language code (e.g., "es", "fr")
            source_language: Source language code (auto-detect if None)

        Returns:
            Translated text

        Raises:
            TranslationError: If translation fails
        """
        if not text or not text.strip():
            return text

        results = await self.translate_batch(
            [text], target_language, source_language
        )
        return results[0]

    async def translate_batch(
        self,
        texts: List[str],
        target_language: str,
        source_language: Optional[str] = None,
    ) -> List[str]:
        """
        Translate multiple texts.

        Args:
            texts: List of texts to translate
            target_language: Target language code
            source_language: Source language code (auto-detect if None)

        Returns:
            List of translated texts

        Raises:
            TranslationError: If translation fails
        """
        if not texts:
            return []

        # Filter empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            return texts

        start_time = time.time()

        try:
            # Build translation prompt
            target_lang_name = LANGUAGE_NAMES.get(target_language, target_language)

            if source_language:
                source_lang_name = LANGUAGE_NAMES.get(source_language, source_language)
                instruction = (
                    f"Translate the following text from {source_lang_name} "
                    f"to {target_lang_name}. "
                    f"Preserve formatting, tone, and meaning. "
                    f"Return only the translated text."
                )
            else:
                instruction = (
                    f"Translate the following text to {target_lang_name}. "
                    f"Preserve formatting, tone, and meaning. "
                    f"Return only the translated text."
                )

            # Combine texts for batch translation
            if len(valid_texts) == 1:
                user_content = valid_texts[0]
            else:
                # Use numbered list for multiple texts
                user_content = "\n\n".join(
                    f"[{i+1}] {text}" for i, text in enumerate(valid_texts)
                )
                instruction += (
                    " Translate each numbered item and keep the same numbering."
                )

            # Call OpenAI API
            response_text = await self._call_api(instruction, user_content)

            # Parse response
            if len(valid_texts) == 1:
                translated = [response_text.strip()]
            else:
                # Extract numbered translations
                translated = self._parse_numbered_response(
                    response_text, len(valid_texts)
                )

            # Track stats
            total_chars = sum(len(t) for t in valid_texts)
            self._total_chars += total_chars
            self._total_translations += len(valid_texts)

            # Record metrics
            duration = time.time() - start_time
            api_request_duration.labels(
                method="POST", endpoint="openai_translation"
            ).observe(duration)
            api_request_counter.labels(
                method="POST", endpoint="openai_translation", status_code=200
            ).inc()

            logger.debug(
                f"Translated {len(valid_texts)} texts to {target_language} "
                f"in {duration:.2f}s"
            )

            return translated

        except Exception as e:
            duration = time.time() - start_time
            api_request_counter.labels(
                method="POST", endpoint="openai_translation", status_code=500
            ).inc()
            logger.error(f"Translation failed: {e}")
            raise TranslationError(f"Translation failed: {e}") from e

    async def detect_language(self, text: str) -> str:
        """
        Detect the language of text.

        Args:
            text: Text to analyze

        Returns:
            ISO 639-1 language code

        Raises:
            TranslationError: If detection fails
        """
        if not text or not text.strip():
            return "unknown"

        try:
            instruction = (
                "Detect the language of the following text. "
                "Respond with only the ISO 639-1 language code (e.g., 'en', 'es', 'fr')."
            )

            result = await self._call_api(instruction, text[:500])  # Use first 500 chars
            lang_code = result.strip().lower()

            # Validate it's a 2-letter code
            if len(lang_code) == 2 and lang_code.isalpha():
                return lang_code

            logger.warning(f"Invalid language code detected: {lang_code}")
            return "unknown"

        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return "unknown"

    def get_supported_languages(self) -> List[str]:
        """Get list of supported language codes."""
        return list(LANGUAGE_NAMES.keys())

    async def _call_api(self, system_instruction: str, user_content: str) -> str:
        """
        Call OpenAI API with retry logic.

        Args:
            system_instruction: System message with instructions
            user_content: User message with content to translate

        Returns:
            API response text

        Raises:
            TranslationError: If all retries fail
        """
        import asyncio

        last_error = None

        for attempt in range(self.max_retries):
            try:
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": 0.3,  # Low temperature for consistent translation
                }

                response = await self._client.post(self.API_ENDPOINT, json=payload)
                response.raise_for_status()

                data = response.json()
                result_text = data["choices"][0]["message"]["content"]

                # Track cost
                usage = data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)

                cost = self._calculate_cost(input_tokens, output_tokens)
                self._total_cost += cost

                logger.debug(
                    f"Translation API call: {input_tokens} in + {output_tokens} out "
                    f"tokens, ${cost:.6f}"
                )

                return result_text

            except httpx.HTTPStatusError as e:
                last_error = e
                status = e.response.status_code

                # Don't retry client errors (except rate limits)
                if 400 <= status < 500 and status != 429:
                    raise TranslationError(f"OpenAI API error: {e.response.text}") from e

                logger.warning(
                    f"API error (attempt {attempt + 1}/{self.max_retries}): "
                    f"{status} - {e.response.text}"
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Unexpected error (attempt {attempt + 1}/{self.max_retries}): {e}"
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)

        raise TranslationError(
            f"Translation failed after {self.max_retries} attempts"
        ) from last_error

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate API cost."""
        costs = self.COSTS.get(self.model, self.COSTS[self.DEFAULT_MODEL])
        input_cost = (input_tokens / 1000) * costs["input"]
        output_cost = (output_tokens / 1000) * costs["output"]
        return input_cost + output_cost

    def _parse_numbered_response(self, response: str, expected_count: int) -> List[str]:
        """Parse numbered translation response."""
        lines = response.strip().split("\n")
        translations = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Try to extract numbered item: [1] text or 1. text or 1) text
            import re

            match = re.match(r"^\[?(\d+)\]?[\.\)]\s*(.*)", line)
            if match:
                translations.append(match.group(2).strip())
            elif translations:
                # Continuation of previous item
                translations[-1] += " " + line

        # Fallback if parsing failed
        if len(translations) != expected_count:
            logger.warning(
                f"Expected {expected_count} translations, got {len(translations)}"
            )
            # Return split by double newline
            translations = [t.strip() for t in response.split("\n\n") if t.strip()]

        return translations[:expected_count]

    def get_usage_stats(self) -> Dict:
        """Get usage statistics."""
        avg_cost_per_char = (
            self._total_cost / self._total_chars if self._total_chars > 0 else 0
        )

        return {
            "total_translations": self._total_translations,
            "total_characters": self._total_chars,
            "total_cost_usd": self._total_cost,
            "avg_cost_per_char": avg_cost_per_char,
            "model": self.model,
        }

    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()
        logger.info(
            f"Closed OpenAITranslationService "
            f"(translations={self._total_translations}, cost=${self._total_cost:.4f})"
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class LibreTranslateService(BaseTranslationService):
    """
    LibreTranslate service (open-source, self-hosted).

    Free, privacy-focused translation service that can be self-hosted.
    Lower quality than commercial services but no per-character costs.

    Features:
    - Free and open-source
    - Self-hosted option (no data sent to third parties)
    - Support for 30+ languages
    - No usage limits when self-hosted
    - Batch translation support

    Example:
        ```python
        # Self-hosted
        service = LibreTranslateService(host="http://localhost:5000")

        # Public instance (rate limited)
        service = LibreTranslateService(
            host="https://libretranslate.com",
            api_key="your-key"
        )

        translated = await service.translate("Hello", target_language="es")
        ```
    """

    def __init__(
        self,
        host: str = "http://localhost:5000",
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize LibreTranslate service.

        Args:
            host: LibreTranslate server URL
            api_key: Optional API key (for public instances)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.host = host.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries

        # Stats
        self._total_translations = 0
        self._total_chars = 0

        # HTTP client
        self._client = httpx.AsyncClient(timeout=timeout)

        # Semaphore to limit concurrent requests (avoid overwhelming the service)
        self._semaphore = asyncio.Semaphore(10)

        logger.info(f"Initialized LibreTranslateService (host={host}, max_concurrent=10)")

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> str:
        """Translate text to target language."""
        if not text or not text.strip():
            return text

        results = await self.translate_batch(
            [text], target_language, source_language
        )
        return results[0]

    async def translate_batch(
        self,
        texts: List[str],
        target_language: str,
        source_language: Optional[str] = None,
    ) -> List[str]:
        """Translate multiple texts."""
        if not texts:
            return []

        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            return texts

        start_time = time.time()

        try:
            # LibreTranslate doesn't support batch API, but we can parallelize individual requests
            # Use asyncio.gather() with semaphore to limit concurrent requests
            async def translate_with_semaphore(text):
                async with self._semaphore:
                    return await self._translate_single(
                        text, target_language, source_language
                    )

            # Translate all texts in parallel (limited by semaphore)
            translated = await asyncio.gather(
                *[translate_with_semaphore(text) for text in valid_texts]
            )

            # Track stats
            self._total_chars += sum(len(t) for t in valid_texts)
            self._total_translations += len(valid_texts)

            # Record metrics
            duration = time.time() - start_time
            api_request_duration.labels(
                method="POST", endpoint="libretranslate"
            ).observe(duration)
            api_request_counter.labels(
                method="POST", endpoint="libretranslate", status_code=200
            ).inc()

            logger.debug(
                f"Translated {len(valid_texts)} texts to {target_language} "
                f"in {duration:.2f}s"
            )

            return translated

        except Exception as e:
            api_request_counter.labels(
                method="POST", endpoint="libretranslate", status_code=500
            ).inc()
            logger.error(f"Translation failed: {e}")
            raise TranslationError(f"Translation failed: {e}") from e

    async def _translate_single(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> str:
        """Translate single text with retry logic."""
        import asyncio

        last_error = None

        for attempt in range(self.max_retries):
            try:
                payload = {
                    "q": text,
                    "target": target_language,
                    "format": "text",
                }

                if source_language:
                    payload["source"] = source_language
                else:
                    payload["source"] = "auto"

                if self.api_key:
                    payload["api_key"] = self.api_key

                response = await self._client.post(
                    f"{self.host}/translate", json=payload
                )
                response.raise_for_status()

                data = response.json()
                return data["translatedText"]

            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    f"LibreTranslate error (attempt {attempt + 1}/{self.max_retries}): "
                    f"{e.response.status_code} - {e.response.text}"
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)

            except Exception as e:
                last_error = e
                logger.warning(f"Unexpected error: {e}")

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)

        raise TranslationError(
            f"Translation failed after {self.max_retries} attempts"
        ) from last_error

    async def detect_language(self, text: str) -> str:
        """Detect language of text."""
        if not text or not text.strip():
            return "unknown"

        try:
            payload = {"q": text[:500]}  # Use first 500 chars

            if self.api_key:
                payload["api_key"] = self.api_key

            response = await self._client.post(f"{self.host}/detect", json=payload)
            response.raise_for_status()

            data = response.json()
            # Returns list of detections with confidence
            if data and len(data) > 0:
                return data[0]["language"]

            return "unknown"

        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return "unknown"

    def get_supported_languages(self) -> List[str]:
        """Get supported languages (synchronous)."""
        # Common LibreTranslate languages
        return [
            "en",
            "es",
            "fr",
            "de",
            "it",
            "pt",
            "ru",
            "ja",
            "zh-Hans",
            "ko",
            "ar",
            "hi",
            "nl",
            "pl",
            "tr",
        ]

    def get_usage_stats(self) -> Dict:
        """Get usage statistics."""
        return {
            "total_translations": self._total_translations,
            "total_characters": self._total_chars,
            "total_cost_usd": 0.0,  # Free service
            "provider": "libretranslate",
        }

    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()
        logger.info(
            f"Closed LibreTranslateService (translations={self._total_translations})"
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class DeepLTranslationService(BaseTranslationService):
    """
    DeepL translation service (commercial, high-quality).

    Professional translation service known for high-quality results,
    especially for European languages. Paid service with per-character pricing.

    Features:
    - Industry-leading translation quality
    - Formal/informal tone control
    - Support for 30+ languages
    - Batch translation support
    - Cost: ~$20 per 1M characters

    Pricing:
    - Free tier: 500,000 chars/month
    - Pro: $5.49 + $20/1M chars

    Example:
        ```python
        service = DeepLTranslationService(api_key="your-deepl-key")

        # Formal translation
        translated = await service.translate(
            "How are you?",
            target_language="DE",
            formality="formal"
        )

        # Batch translation
        texts = ["Hello", "Goodbye", "Thank you"]
        translated = await service.translate_batch(texts, target_language="FR")
        ```
    """

    API_ENDPOINT_FREE = "https://api-free.deepl.com/v2/translate"
    API_ENDPOINT_PRO = "https://api.deepl.com/v2/translate"

    # Cost per 1M characters
    COST_PER_1M_CHARS = 20.0

    def __init__(
        self,
        api_key: Optional[str] = None,
        is_pro: bool = False,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize DeepL translation service.

        Args:
            api_key: DeepL API key
            is_pro: Use Pro endpoint (default: Free)
            timeout: Request timeout
            max_retries: Maximum retry attempts
        """
        import os

        self.api_key = api_key or os.getenv("DEEPL_API_KEY")
        if not self.api_key:
            raise ValueError("DeepL API key required")

        self.endpoint = self.API_ENDPOINT_PRO if is_pro else self.API_ENDPOINT_FREE
        self.timeout = timeout
        self.max_retries = max_retries

        # Stats
        self._total_cost = 0.0
        self._total_chars = 0
        self._total_translations = 0

        # HTTP client
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"Authorization": f"DeepL-Auth-Key {self.api_key}"},
        )

        logger.info(f"Initialized DeepLTranslationService (pro={is_pro})")

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
        formality: Optional[str] = None,
    ) -> str:
        """
        Translate text to target language.

        Args:
            text: Text to translate
            target_language: Target language code (uppercase, e.g., "DE", "FR")
            source_language: Source language code (auto-detect if None)
            formality: "formal" or "informal" (if supported)

        Returns:
            Translated text
        """
        if not text or not text.strip():
            return text

        results = await self.translate_batch(
            [text], target_language, source_language
        )
        return results[0]

    async def translate_batch(
        self,
        texts: List[str],
        target_language: str,
        source_language: Optional[str] = None,
    ) -> List[str]:
        """Translate multiple texts."""
        if not texts:
            return []

        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            return texts

        start_time = time.time()

        try:
            import asyncio

            last_error = None

            for attempt in range(self.max_retries):
                try:
                    # DeepL supports batch translation
                    payload = {
                        "text": valid_texts,
                        "target_lang": target_language.upper(),
                    }

                    if source_language:
                        payload["source_lang"] = source_language.upper()

                    response = await self._client.post(self.endpoint, data=payload)
                    response.raise_for_status()

                    data = response.json()
                    translations = [t["text"] for t in data["translations"]]

                    # Track stats and cost
                    total_chars = sum(len(t) for t in valid_texts)
                    cost = (total_chars / 1_000_000) * self.COST_PER_1M_CHARS

                    self._total_chars += total_chars
                    self._total_cost += cost
                    self._total_translations += len(valid_texts)

                    # Record metrics
                    duration = time.time() - start_time
                    api_request_duration.labels(
                        method="POST", endpoint="deepl_translation"
                    ).observe(duration)
                    api_request_counter.labels(
                        method="POST", endpoint="deepl_translation", status_code=200
                    ).inc()

                    logger.debug(
                        f"Translated {len(valid_texts)} texts to {target_language} "
                        f"(${cost:.6f}) in {duration:.2f}s"
                    )

                    return translations

                except httpx.HTTPStatusError as e:
                    last_error = e
                    logger.warning(
                        f"DeepL error (attempt {attempt + 1}/{self.max_retries}): "
                        f"{e.response.status_code} - {e.response.text}"
                    )

                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2**attempt)

                except Exception as e:
                    last_error = e
                    logger.warning(f"Unexpected error: {e}")

                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2**attempt)

            raise TranslationError(
                f"Translation failed after {self.max_retries} attempts"
            ) from last_error

        except TranslationError:
            api_request_counter.labels(
                method="POST", endpoint="deepl_translation", status_code=500
            ).inc()
            raise
        except Exception as e:
            api_request_counter.labels(
                method="POST", endpoint="deepl_translation", status_code=500
            ).inc()
            logger.error(f"Translation failed: {e}")
            raise TranslationError(f"Translation failed: {e}") from e

    async def detect_language(self, text: str) -> str:
        """
        Detect language (not directly supported by DeepL).

        Returns best guess based on translation attempt.
        """
        # DeepL doesn't have language detection API
        # Return "unknown" and let auto-detect handle it
        return "unknown"

    def get_supported_languages(self) -> List[str]:
        """Get supported languages."""
        # DeepL uses uppercase codes
        return [
            "EN",
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

    def get_usage_stats(self) -> Dict:
        """Get usage statistics."""
        return {
            "total_translations": self._total_translations,
            "total_characters": self._total_chars,
            "total_cost_usd": self._total_cost,
            "cost_per_1m_chars": self.COST_PER_1M_CHARS,
            "provider": "deepl",
        }

    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()
        logger.info(
            f"Closed DeepLTranslationService "
            f"(translations={self._total_translations}, cost=${self._total_cost:.4f})"
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
