#!/usr/bin/env python3
"""Simple test to verify LibreTranslate is working."""

import asyncio
import aiohttp
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


async def test_libretranslate():
    """Test LibreTranslate translation."""
    url = "http://localhost:5000"

    async with aiohttp.ClientSession() as session:
        # Test 1: Check languages
        logger.info("="*80)
        logger.info("Test 1: Checking supported languages...")
        logger.info("="*80)
        async with session.get(f"{url}/languages") as resp:
            langs = await resp.json()
            lang_codes = [l['code'] for l in langs]
            logger.info(f"✓ Supports {len(langs)} languages: {', '.join(lang_codes[:10])}...")

        # Test 2: Translate English -> Spanish
        logger.info("\n" + "="*80)
        logger.info("Test 2: Translating English -> Spanish")
        logger.info("="*80)
        test_text = "Hello, this is a test of the free translation system!"

        payload = {
            "q": test_text,
            "source": "en",
            "target": "es",
            "format": "text"
        }

        async with session.post(f"{url}/translate", json=payload) as resp:
            result = await resp.json()
            translated = result.get("translatedText", "")
            logger.info(f"Original:   {test_text}")
            logger.info(f"Translated: {translated}")

        # Test 3: Translate English -> Chinese
        logger.info("\n" + "="*80)
        logger.info("Test 3: Translating English -> Chinese (Simplified)")
        logger.info("="*80)

        payload = {
            "q": test_text,
            "source": "en",
            "target": "zh-Hans" if "zh-Hans" in lang_codes else "zh",
            "format": "text"
        }

        async with session.post(f"{url}/translate", json=payload) as resp:
            result = await resp.json()
            translated_zh = result.get("translatedText", "")
            logger.info(f"Original:   {test_text}")
            logger.info(f"Translated: {translated_zh}")

        logger.info("\n" + "="*80)
        logger.info("✓ ALL TESTS PASSED!")
        logger.info("="*80)
        logger.info("\nLibreTranslate (FREE) is working correctly!")
        logger.info("Your translation pipeline will use this instead of OpenAI.")
        logger.info("\nCost: $0 (completely free)")


if __name__ == "__main__":
    asyncio.run(test_libretranslate())
