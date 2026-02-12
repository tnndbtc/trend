#!/usr/bin/env python3
"""
AI Services Demo Script

Demonstrates how to use the embedding, LLM, and semantic search services
through the ServiceFactory.

Requirements:
- Set OPENAI_API_KEY or ANTHROPIC_API_KEY
- Have PostgreSQL, Redis, and Qdrant running
- Install required packages: openai, anthropic

Usage:
    python examples/ai_services_demo.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from trend_agent.services import get_service_factory
from trend_agent.services.search import SemanticSearchRequest, SemanticSearchFilter
from trend_agent.schemas import Category


async def demo_embeddings():
    """Demo: Generate embeddings for text."""
    print("\n" + "=" * 80)
    print("DEMO 1: Text Embeddings")
    print("=" * 80)

    factory = get_service_factory()
    embedding_service = factory.get_embedding_service()

    text = "Artificial intelligence is revolutionizing technology."
    print(f"\n📝 Text: {text}")

    # Generate embedding
    embedding = await embedding_service.embed(text)

    print(f"✅ Generated embedding:")
    print(f"   Dimension: {len(embedding)}")
    print(f"   First 5 values: {embedding[:5]}")
    print(f"   Vector norm: {sum(x**2 for x in embedding)**0.5:.4f}")


async def demo_batch_embeddings():
    """Demo: Generate embeddings for multiple texts."""
    print("\n" + "=" * 80)
    print("DEMO 2: Batch Embeddings")
    print("=" * 80)

    factory = get_service_factory()
    embedding_service = factory.get_embedding_service()

    texts = [
        "Machine learning models learn from data.",
        "Neural networks mimic the human brain.",
        "Deep learning uses multiple layers.",
    ]

    print(f"\n📝 Embedding {len(texts)} texts...")

    embeddings = await embedding_service.embed_batch(texts)

    print(f"✅ Generated {len(embeddings)} embeddings:")
    for i, (text, emb) in enumerate(zip(texts, embeddings), 1):
        print(f"   {i}. {text[:50]}... → {len(emb)}D vector")


async def demo_llm_summarization():
    """Demo: Summarize text with LLM."""
    print("\n" + "=" * 80)
    print("DEMO 3: Text Summarization")
    print("=" * 80)

    factory = get_service_factory()
    llm_service = factory.get_llm_service(provider="openai")

    long_text = """
    Artificial intelligence (AI) is intelligence demonstrated by machines,
    in contrast to the natural intelligence displayed by humans and animals.
    Leading AI textbooks define the field as the study of "intelligent agents":
    any device that perceives its environment and takes actions that maximize
    its chance of successfully achieving its goals. Colloquially, the term
    "artificial intelligence" is often used to describe machines (or computers)
    that mimic "cognitive" functions that humans associate with the human mind,
    such as "learning" and "problem solving".
    """

    print("\n📝 Original text (length: {} chars)".format(len(long_text)))
    print(f"   {long_text.strip()[:100]}...")

    # Concise summary
    summary = await llm_service.summarize(
        text=long_text,
        max_length=100,
        style="concise"
    )

    print(f"\n✅ Concise summary:")
    print(f"   {summary}")


async def demo_key_point_extraction():
    """Demo: Extract key points from text."""
    print("\n" + "=" * 80)
    print("DEMO 4: Key Point Extraction")
    print("=" * 80)

    factory = get_service_factory()
    llm_service = factory.get_llm_service(provider="openai")

    text = """
    Quantum computing uses quantum-mechanical phenomena such as superposition
    and entanglement to perform operations on data. Unlike classical computers
    which use bits (0 or 1), quantum computers use quantum bits or qubits,
    which can exist in multiple states simultaneously. This allows quantum
    computers to solve certain types of problems exponentially faster than
    classical computers. Applications include cryptography, drug discovery,
    and optimization problems.
    """

    print(f"\n📝 Text: {text.strip()[:100]}...")

    key_points = await llm_service.extract_key_points(text, num_points=3)

    print(f"\n✅ Key points extracted:")
    for i, point in enumerate(key_points, 1):
        print(f"   {i}. {point}")


async def demo_tag_generation():
    """Demo: Generate tags for content."""
    print("\n" + "=" * 80)
    print("DEMO 5: Tag Generation")
    print("=" * 80)

    factory = get_service_factory()
    llm_service = factory.get_llm_service(provider="openai")

    text = """
    A new breakthrough in renewable energy technology has been announced.
    Scientists have developed solar panels with 50% efficiency, doubling
    the current industry standard. This could accelerate the transition
    to clean energy and reduce carbon emissions significantly.
    """

    print(f"\n📝 Text: {text.strip()[:100]}...")

    tags = await llm_service.generate_tags(text, num_tags=5)

    print(f"\n✅ Generated tags:")
    print(f"   {', '.join(tags)}")


async def demo_trend_analysis():
    """Demo: Analyze trend with LLM."""
    print("\n" + "=" * 80)
    print("DEMO 6: Trend Analysis")
    print("=" * 80)

    factory = get_service_factory()
    llm_service = factory.get_llm_service(provider="openai")

    title = "AI Startup Raises $100M in Series A Funding"
    description = """
    A leading AI startup focused on healthcare applications has secured
    $100 million in Series A funding. The company plans to use the investment
    to expand its AI-powered diagnostic tools and enter new markets.
    """
    metrics = {
        "upvotes": 2500,
        "comments": 450,
        "views": 50000,
        "shares": 320,
    }

    print(f"\n📝 Analyzing trend...")
    print(f"   Title: {title}")
    print(f"   Metrics: {metrics}")

    analysis = await llm_service.analyze_trend(
        title=title,
        description=description,
        metrics=metrics,
    )

    print(f"\n✅ Trend analysis:")
    if isinstance(analysis, dict):
        for key, value in analysis.items():
            print(f"   {key}: {value}")
    else:
        print(f"   {analysis}")


async def demo_semantic_search():
    """Demo: Semantic search for similar content."""
    print("\n" + "=" * 80)
    print("DEMO 7: Semantic Search")
    print("=" * 80)

    factory = get_service_factory()

    # Note: This requires vector repository and trend repository to be set up
    try:
        search_service = factory.get_search_service()

        query = "artificial intelligence breakthroughs"
        print(f"\n🔍 Searching for: '{query}'")

        request = SemanticSearchRequest(
            query=query,
            limit=5,
            min_similarity=0.7,
        )

        results = await search_service.search(request)

        print(f"\n✅ Found {len(results)} results:")
        for i, trend in enumerate(results, 1):
            print(f"   {i}. {trend.title}")
            print(f"      Category: {trend.category.value}")
            print(f"      Score: {trend.score:.1f}")

    except Exception as e:
        print(f"\n⚠️  Semantic search requires database setup: {e}")


async def demo_provider_comparison():
    """Demo: Compare OpenAI vs Anthropic LLM."""
    print("\n" + "=" * 80)
    print("DEMO 8: Provider Comparison (OpenAI vs Anthropic)")
    print("=" * 80)

    factory = get_service_factory()

    prompt = "Explain quantum computing in one sentence."
    print(f"\n📝 Prompt: {prompt}\n")

    # OpenAI
    if os.getenv("OPENAI_API_KEY"):
        try:
            openai_llm = factory.get_llm_service(provider="openai")
            openai_response = await openai_llm.generate(prompt)
            print(f"🤖 OpenAI (GPT):")
            print(f"   {openai_response}\n")
        except Exception as e:
            print(f"⚠️  OpenAI error: {e}\n")
    else:
        print("⚠️  OpenAI not configured (set OPENAI_API_KEY)\n")

    # Anthropic
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            anthropic_llm = factory.get_llm_service(provider="anthropic")
            anthropic_response = await anthropic_llm.generate(prompt)
            print(f"🤖 Anthropic (Claude):")
            print(f"   {anthropic_response}")
        except Exception as e:
            print(f"⚠️  Anthropic error: {e}")
    else:
        print("⚠️  Anthropic not configured (set ANTHROPIC_API_KEY)")


async def demo_service_statistics():
    """Demo: View service usage statistics."""
    print("\n" + "=" * 80)
    print("DEMO 9: Service Statistics")
    print("=" * 80)

    factory = get_service_factory()

    # Get embedding service stats
    embedding_service = factory.get_embedding_service()
    embed_stats = embedding_service.get_stats()

    print(f"\n📊 Embedding Service:")
    print(f"   Model: {embed_stats.get('model', 'N/A')}")
    print(f"   Total requests: {embed_stats.get('total_requests', 0)}")
    print(f"   Total tokens: {embed_stats.get('total_tokens', 0)}")
    print(f"   Total cost: ${embed_stats.get('total_cost_usd', 0):.4f}")

    # Get LLM service stats
    llm_service = factory.get_llm_service(provider="openai")
    llm_stats = llm_service.get_stats()

    print(f"\n📊 LLM Service:")
    print(f"   Model: {llm_stats.get('model', 'N/A')}")
    print(f"   Total requests: {llm_stats.get('total_requests', 0)}")
    print(f"   Input tokens: {llm_stats.get('total_input_tokens', 0)}")
    print(f"   Output tokens: {llm_stats.get('total_output_tokens', 0)}")
    print(f"   Total cost: ${llm_stats.get('total_cost_usd', 0):.4f}")


async def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("🤖 AI SERVICES DEMO")
    print("=" * 80)
    print("\nThis demo showcases the AI service factory including")
    print("embeddings, LLMs, and semantic search capabilities.")

    # Check environment
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

    print(f"\n📋 Available AI providers:")
    print(f"   OpenAI: {'✅' if has_openai else '❌'}")
    print(f"   Anthropic: {'✅' if has_anthropic else '❌'}")

    if not has_openai and not has_anthropic:
        print("\n⚠️  No AI providers configured!")
        print("   Set OPENAI_API_KEY or ANTHROPIC_API_KEY")
        return

    try:
        # Run demos (only if OpenAI is available)
        if has_openai:
            await demo_embeddings()
            await demo_batch_embeddings()
            await demo_llm_summarization()
            await demo_key_point_extraction()
            await demo_tag_generation()
            await demo_trend_analysis()
            await demo_semantic_search()

        # Provider comparison (if both available)
        if has_openai or has_anthropic:
            await demo_provider_comparison()
            await demo_service_statistics()

        print("\n" + "=" * 80)
        print("✅ All demos completed successfully!")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
