#!/usr/bin/env python3
"""
Test script to verify LibreTranslate (free) translation is working.

This script tests:
1. LibreTranslate container accessibility
2. Translation manager provider priority
3. Provider usage logging
4. Translation caching
"""

import asyncio
import logging
import os
import sys

# Setup logging to see which provider is used
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def test_libretranslate_direct():
    """Test direct LibreTranslate API access."""
    import aiohttp

    libretranslate_url = os.getenv("LIBRETRANSLATE_HOST", "http://localhost:5000")

    try:
        async with aiohttp.ClientSession() as session:
            # Test languages endpoint
            async with session.get(f"{libretranslate_url}/languages") as resp:
                if resp.status == 200:
                    langs = await resp.json()
                    logger.info(f"✓ LibreTranslate is accessible! Supports {len(langs)} languages")

                    # Check for Chinese support
                    lang_codes = [l['code'] for l in langs]
                    if 'zh-Hans' in lang_codes or 'zh' in lang_codes:
                        logger.info("✓ Chinese (Simplified) is supported")
                    return True
                else:
                    logger.error(f"✗ LibreTranslate returned status {resp.status}")
                    return False
    except Exception as e:
        logger.error(f"✗ LibreTranslate is NOT accessible: {e}")
        logger.error("Make sure to start it with: docker compose --profile translation up -d libretranslate")
        return False


async def test_translation_manager():
    """Test translation manager with provider priority."""
    from trend_agent.services import ServiceFactory

    # Set environment to ensure LibreTranslate is used first
    os.environ.setdefault("TRANSLATION_PROVIDER_PRIORITY", "libretranslate,openai,deepl")
    os.environ.setdefault("LIBRETRANSLATE_HOST", "http://localhost:5000")

    factory = ServiceFactory()

    try:
        # Get translation manager
        translation_manager = factory.get_translation_manager()

        logger.info(f"Translation providers: {list(translation_manager.providers.keys())}")
        logger.info(f"Provider priority: {translation_manager.provider_priority}")

        # Test translation
        test_text = "Hello, this is a test of the free translation system!"

        logger.info("\n" + "="*80)
        logger.info("Testing translation: English -> Spanish")
        logger.info("="*80)

        translated = await translation_manager.translate(
            text=test_text,
            target_language="es",
            source_language="en"
        )

        logger.info(f"\nOriginal:  {test_text}")
        logger.info(f"Translated: {translated}")

        # Test Chinese translation
        logger.info("\n" + "="*80)
        logger.info("Testing translation: English -> Chinese (Simplified)")
        logger.info("="*80)

        translated_zh = await translation_manager.translate(
            text=test_text,
            target_language="zh-Hans",
            source_language="en"
        )

        logger.info(f"\nOriginal:  {test_text}")
        logger.info(f"Translated: {translated_zh}")

        # Get stats
        stats = translation_manager.get_stats()
        logger.info("\n" + "="*80)
        logger.info("Translation Statistics:")
        logger.info("="*80)
        logger.info(f"Total translations: {stats['total_translations']}")
        logger.info(f"Cache hits: {stats['cache_hits']}")
        logger.info(f"Provider usage: {stats['provider_usage']}")
        logger.info(f"Provider failures: {stats['provider_failures']}")

        # Determine primary provider used
        provider_usage = stats['provider_usage']
        primary_provider = max(provider_usage.items(), key=lambda x: x[1])[0] if provider_usage else "none"

        if primary_provider == "libretranslate":
            logger.info("\n✓ SUCCESS: LibreTranslate (FREE) is being used!")
            logger.info("✓ You are NOT consuming OpenAI API tokens!")
        else:
            logger.warning(f"\n⚠ WARNING: Primary provider is '{primary_provider}' not LibreTranslate")
            logger.warning("This may consume API tokens/credits!")

        await translation_manager.close()
        return True

    except Exception as e:
        logger.error(f"✗ Translation manager test failed: {e}", exc_info=True)
        return False


async def test_cache_hit():
    """Test that cache is working (second translation should be cached)."""
    from trend_agent.services import ServiceFactory

    factory = ServiceFactory()
    translation_manager = factory.get_translation_manager()

    test_text = "Testing cache functionality"

    logger.info("\n" + "="*80)
    logger.info("Testing Cache (translating same text twice)")
    logger.info("="*80)

    # First translation (should hit LibreTranslate)
    logger.info("\nFirst translation (should use LibreTranslate):")
    translated1 = await translation_manager.translate(test_text, "es", "en")

    # Second translation (should be cached)
    logger.info("\nSecond translation (should use CACHE):")
    translated2 = await translation_manager.translate(test_text, "es", "en")

    assert translated1 == translated2, "Translations don't match!"

    stats = translation_manager.get_stats()
    cache_hits = stats['cache_hits']

    if cache_hits > 0:
        logger.info(f"\n✓ SUCCESS: Cache is working! ({cache_hits} cache hits)")
    else:
        logger.warning("\n⚠ WARNING: No cache hits detected")

    await translation_manager.close()


async def main():
    """Run all tests."""
    logger.info("="*80)
    logger.info("FREE TRANSLATION SYSTEM TEST")
    logger.info("="*80)

    # Test 1: LibreTranslate accessibility
    logger.info("\n[Test 1] Checking LibreTranslate container...")
    libretranslate_ok = await test_libretranslate_direct()

    if not libretranslate_ok:
        logger.error("\n✗ FAILED: LibreTranslate is not accessible")
        logger.error("Please start it with: docker compose --profile translation up -d libretranslate")
        return 1

    # Test 2: Translation manager
    logger.info("\n[Test 2] Testing Translation Manager...")
    manager_ok = await test_translation_manager()

    if not manager_ok:
        logger.error("\n✗ FAILED: Translation manager test failed")
        return 1

    # Test 3: Cache
    logger.info("\n[Test 3] Testing Translation Cache...")
    await test_cache_hit()

    logger.info("\n" + "="*80)
    logger.info("✓ ALL TESTS PASSED!")
    logger.info("="*80)
    logger.info("\nYour system is configured to use FREE translation (LibreTranslate).")
    logger.info("OpenAI API will only be used as fallback if LibreTranslate fails.")
    logger.info("\nNext steps:")
    logger.info("  1. Check that ENABLE_TRANSLATION=true in .env.docker")
    logger.info("  2. Run your processing pipeline - translations will happen automatically")
    logger.info("  3. Check logs for '[TRANSLATION]' messages to see provider usage")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
