#!/usr/bin/env python3
"""
Translation Services Demo Script

Demonstrates how to use the multi-provider translation system
with caching, batch processing, and fallback.

Requirements:
- Set environment variables for translation providers
- Have Redis running for caching
- Install required packages: openai, requests, redis

Usage:
    python examples/translation_demo.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from trend_agent.services import get_service_factory


async def demo_single_translation():
    """Demo: Translate a single text."""
    print("\n" + "=" * 80)
    print("DEMO 1: Single Text Translation")
    print("=" * 80)

    factory = get_service_factory()
    translation_manager = factory.get_translation_manager()

    text = "Artificial intelligence is transforming the world of technology."
    target_lang = "es"

    print(f"\n📝 Original (en): {text}")
    print(f"🎯 Target language: {target_lang}")

    translated = await translation_manager.translate(
        text=text,
        target_language=target_lang,
        source_language="en",
    )

    print(f"✅ Translated ({target_lang}): {translated}")


async def demo_batch_translation():
    """Demo: Translate multiple texts efficiently."""
    print("\n" + "=" * 80)
    print("DEMO 2: Batch Translation")
    print("=" * 80)

    factory = get_service_factory()
    translation_manager = factory.get_translation_manager()

    texts = [
        "Machine learning is a subset of artificial intelligence.",
        "Neural networks can recognize patterns in data.",
        "Deep learning models require large amounts of training data.",
    ]
    target_lang = "fr"

    print(f"\n📝 Translating {len(texts)} texts to {target_lang}...")

    translations = await translation_manager.translate_batch(
        texts=texts,
        target_language=target_lang,
        source_language="en",
    )

    for i, (original, translated) in enumerate(zip(texts, translations), 1):
        print(f"\n{i}. Original: {original}")
        print(f"   Translated: {translated}")


async def demo_language_detection():
    """Demo: Detect language of text."""
    print("\n" + "=" * 80)
    print("DEMO 3: Language Detection")
    print("=" * 80)

    factory = get_service_factory()
    translation_manager = factory.get_translation_manager()

    test_texts = {
        "Hello, how are you?": "en",
        "Bonjour, comment allez-vous?": "fr",
        "Hola, ¿cómo estás?": "es",
        "Guten Tag, wie geht es Ihnen?": "de",
        "こんにちは、お元気ですか？": "ja",
    }

    for text, expected_lang in test_texts.items():
        detected = await translation_manager.detect_language(text)
        status = "✅" if detected == expected_lang else "❓"
        print(f"{status} '{text}' → Detected: {detected} (Expected: {expected_lang})")


async def demo_cache_performance():
    """Demo: Cache performance improvement."""
    print("\n" + "=" * 80)
    print("DEMO 4: Cache Performance")
    print("=" * 80)

    factory = get_service_factory()
    translation_manager = factory.get_translation_manager()

    text = "The quick brown fox jumps over the lazy dog."
    target_lang = "es"

    # First translation (cache miss)
    print("\n🔍 First translation (cache miss)...")
    import time
    start = time.time()
    result1 = await translation_manager.translate(text, target_lang, "en")
    duration1 = time.time() - start
    print(f"   Result: {result1}")
    print(f"   Time: {duration1:.3f}s")

    # Second translation (cache hit)
    print("\n🔍 Second translation (cache hit)...")
    start = time.time()
    result2 = await translation_manager.translate(text, target_lang, "en")
    duration2 = time.time() - start
    print(f"   Result: {result2}")
    print(f"   Time: {duration2:.3f}s")

    speedup = duration1 / duration2 if duration2 > 0 else float('inf')
    print(f"\n📊 Cache speedup: {speedup:.1f}x faster")
    print(f"   Same result: {result1 == result2}")


async def demo_provider_fallback():
    """Demo: Provider fallback mechanism."""
    print("\n" + "=" * 80)
    print("DEMO 5: Provider Selection & Fallback")
    print("=" * 80)

    factory = get_service_factory()
    translation_manager = factory.get_translation_manager()

    text = "Quantum computing promises to revolutionize data processing."
    target_lang = "de"

    # Try with preferred provider
    print("\n🎯 Translating with provider priority...")
    translated = await translation_manager.translate(
        text=text,
        target_language=target_lang,
        source_language="en",
    )

    print(f"   Translated: {translated}")

    # Show provider stats
    stats = translation_manager.get_stats()
    print(f"\n📊 Provider usage:")
    for provider, count in stats["provider_usage"].items():
        print(f"   - {provider}: {count} translations")


async def demo_multi_language_translation():
    """Demo: Translate to multiple languages."""
    print("\n" + "=" * 80)
    print("DEMO 6: Multi-Language Translation")
    print("=" * 80)

    factory = get_service_factory()
    translation_manager = factory.get_translation_manager()

    text = "Welcome to the future of artificial intelligence."
    target_languages = ["es", "fr", "de", "ja", "zh"]

    print(f"\n📝 Original (en): {text}")
    print(f"\n🌍 Translating to {len(target_languages)} languages...\n")

    for lang in target_languages:
        try:
            translated = await translation_manager.translate(
                text=text,
                target_language=lang,
                source_language="en",
            )
            print(f"   [{lang}] {translated}")
        except Exception as e:
            print(f"   [{lang}] ❌ Translation failed: {e}")


async def demo_translation_statistics():
    """Demo: View translation statistics."""
    print("\n" + "=" * 80)
    print("DEMO 7: Translation Statistics")
    print("=" * 80)

    factory = get_service_factory()
    translation_manager = factory.get_translation_manager()

    # Perform some translations
    texts = [
        "First translation",
        "Second translation",
        "Third translation",
    ]

    for text in texts:
        await translation_manager.translate(text, "es", "en")

    # Get stats
    stats = translation_manager.get_stats()

    print("\n📊 Translation Statistics:")
    print(f"   Total translations: {stats['total_translations']}")

    if "cache_stats" in stats:
        cache_stats = stats["cache_stats"]
        print(f"\n💾 Cache Statistics:")
        print(f"   Hits: {cache_stats.get('cache_hits', 0)}")
        print(f"   Misses: {cache_stats.get('cache_misses', 0)}")
        print(f"   Hit rate: {cache_stats.get('hit_rate_percent', 0):.1f}%")

    print(f"\n🔧 Provider Usage:")
    for provider, count in stats["provider_usage"].items():
        print(f"   {provider}: {count}")

    if stats.get("provider_failures"):
        print(f"\n❌ Provider Failures:")
        for provider, count in stats["provider_failures"].items():
            if count > 0:
                print(f"   {provider}: {count}")


async def demo_supported_languages():
    """Demo: List supported languages."""
    print("\n" + "=" * 80)
    print("DEMO 8: Supported Languages")
    print("=" * 80)

    factory = get_service_factory()
    translation_manager = factory.get_translation_manager()

    languages = translation_manager.get_supported_languages()

    print(f"\n🌍 Supported languages ({len(languages)} total):")
    print(f"   {', '.join(sorted(languages))}")


async def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("🌍 TRANSLATION SERVICES DEMO")
    print("=" * 80)
    print("\nThis demo showcases the multi-provider translation system")
    print("with intelligent routing, caching, and fallback mechanisms.")

    # Check environment
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_deepl = bool(os.getenv("DEEPL_API_KEY"))
    has_libretranslate = bool(os.getenv("LIBRETRANSLATE_HOST"))

    print(f"\n📋 Available providers:")
    print(f"   OpenAI: {'✅' if has_openai else '❌'}")
    print(f"   DeepL: {'✅' if has_deepl else '❌'}")
    print(f"   LibreTranslate: {'✅' if has_libretranslate else '❌'}")

    if not any([has_openai, has_deepl, has_libretranslate]):
        print("\n⚠️  No translation providers configured!")
        print("   Set OPENAI_API_KEY, DEEPL_API_KEY, or LIBRETRANSLATE_HOST")
        return

    try:
        # Run demos
        await demo_single_translation()
        await demo_batch_translation()
        await demo_language_detection()
        await demo_cache_performance()
        await demo_provider_fallback()
        await demo_multi_language_translation()
        await demo_translation_statistics()
        await demo_supported_languages()

        print("\n" + "=" * 80)
        print("✅ All demos completed successfully!")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
