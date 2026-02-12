"""
Key Point Extraction Service.

This module provides AI-powered extraction of key points from trends.
It analyzes trend summaries and related items to identify the most important
aspects and generate concise bullet points.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from trend_agent.schemas import Trend, Topic, ProcessedItem
from trend_agent.intelligence.interfaces import BaseLLMService
from trend_agent.storage.interfaces import ItemRepository

logger = logging.getLogger(__name__)


# ============================================================================
# Key Point Extractor
# ============================================================================


class KeyPointExtractor:
    """
    Service for extracting key points from trends using AI.

    Uses LLMs to analyze trend content and extract 3-5 most important points.
    """

    # System prompt for key point extraction
    SYSTEM_PROMPT = """You are an expert analyst extracting key points from trending topics.

Your task is to analyze a trend and its related content to identify the most important points.

Guidelines:
- Extract 3-5 key points maximum
- Each point should be concise (1-2 sentences)
- Focus on the most newsworthy or impactful aspects
- Prioritize facts, statistics, and concrete developments
- Avoid redundancy between points
- Use clear, objective language

Output format: Return ONLY a JSON array of strings, e.g.:
["First key point here", "Second key point here", "Third key point here"]"""

    def __init__(
        self,
        llm_service: BaseLLMService,
        item_repo: Optional[ItemRepository] = None,
        max_items_per_trend: int = 20,
        min_points: int = 3,
        max_points: int = 5,
    ):
        """
        Initialize key point extractor.

        Args:
            llm_service: LLM service for text generation
            item_repo: Optional repository to fetch related items
            max_items_per_trend: Maximum items to include in analysis
            min_points: Minimum number of key points to extract
            max_points: Maximum number of key points to extract
        """
        self._llm_service = llm_service
        self._item_repo = item_repo
        self._max_items_per_trend = max_items_per_trend
        self._min_points = min_points
        self._max_points = max_points

    async def extract_key_points(
        self, trend: Trend, items: Optional[List[ProcessedItem]] = None
    ) -> List[str]:
        """
        Extract key points from a trend.

        Args:
            trend: Trend to analyze
            items: Optional list of related items (fetched if not provided)

        Returns:
            List of key point strings (3-5 points)
        """
        try:
            # Build context from trend and items
            context = await self._build_context(trend, items)

            # Create prompt
            prompt = self._create_extraction_prompt(trend, context)

            # Call LLM
            response = await self._llm_service.generate(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                max_tokens=500,
                temperature=0.3,  # Lower temperature for more focused output
            )

            # Parse response
            key_points = self._parse_response(response)

            # Validate and trim
            key_points = self._validate_key_points(key_points)

            logger.info(
                f"Extracted {len(key_points)} key points for trend '{trend.title[:50]}'"
            )

            return key_points

        except Exception as e:
            logger.error(f"Failed to extract key points for trend {trend.id}: {e}")
            # Return fallback key points
            return self._generate_fallback_key_points(trend)

    async def extract_key_points_batch(
        self, trends: List[Trend]
    ) -> Dict[UUID, List[str]]:
        """
        Extract key points for multiple trends.

        Args:
            trends: List of trends to analyze

        Returns:
            Dictionary mapping trend IDs to key points
        """
        results = {}

        for trend in trends:
            try:
                key_points = await self.extract_key_points(trend)
                results[trend.id] = key_points
            except Exception as e:
                logger.error(
                    f"Failed to extract key points for trend {trend.id}: {e}"
                )
                results[trend.id] = self._generate_fallback_key_points(trend)

        logger.info(f"Extracted key points for {len(results)}/{len(trends)} trends")

        return results

    async def update_trend_key_points(self, trend: Trend) -> Trend:
        """
        Extract and update key points for a trend in-place.

        Args:
            trend: Trend to update

        Returns:
            Updated trend with key_points field populated
        """
        key_points = await self.extract_key_points(trend)
        trend.key_points = key_points
        return trend

    # ========================================================================
    # Private Methods
    # ========================================================================

    async def _build_context(
        self, trend: Trend, items: Optional[List[ProcessedItem]] = None
    ) -> str:
        """
        Build context string from trend and related items.

        Args:
            trend: Trend to analyze
            items: Optional list of items

        Returns:
            Context string for LLM
        """
        context_parts = []

        # Add trend summary
        context_parts.append(f"Trend Title: {trend.title}")
        context_parts.append(f"Trend Summary: {trend.summary}")
        context_parts.append(f"Category: {trend.category.value}")
        context_parts.append(f"Sources: {', '.join(s.value for s in trend.sources)}")

        # Add keywords
        if trend.keywords:
            context_parts.append(f"Keywords: {', '.join(trend.keywords)}")

        # Fetch items if not provided
        if items is None and self._item_repo:
            try:
                # Get items associated with this trend's topic
                items = await self._item_repo.get_by_topic_id(
                    trend.topic_id, limit=self._max_items_per_trend
                )
            except Exception as e:
                logger.warning(f"Failed to fetch items for trend {trend.id}: {e}")
                items = []

        # Add item content
        if items:
            context_parts.append("\nRelated Content:")
            for i, item in enumerate(items[: self._max_items_per_trend], 1):
                # Add title
                context_parts.append(f"\n{i}. {item.title}")

                # Add description if available
                if item.description:
                    desc = item.description[:200]  # Limit length
                    context_parts.append(f"   {desc}")

        return "\n".join(context_parts)

    def _create_extraction_prompt(self, trend: Trend, context: str) -> str:
        """
        Create LLM prompt for key point extraction.

        Args:
            trend: Trend being analyzed
            context: Context string with trend and item info

        Returns:
            Formatted prompt string
        """
        return f"""Analyze this trending topic and extract {self._min_points}-{self._max_points} key points:

{context}

Extract the most important points about this trend. Focus on:
- What is happening (the core story)
- Why it matters (impact, significance)
- Key facts, statistics, or developments
- Notable reactions or implications

Return your response as a JSON array of {self._min_points}-{self._max_points} strings."""

    def _parse_response(self, response: str) -> List[str]:
        """
        Parse LLM response into key points list.

        Args:
            response: LLM response text

        Returns:
            List of key point strings
        """
        import json
        import re

        # Try to extract JSON array from response
        try:
            # Look for JSON array in response
            match = re.search(r'\[.*\]', response, re.DOTALL)
            if match:
                json_str = match.group(0)
                key_points = json.loads(json_str)

                if isinstance(key_points, list):
                    return [str(point).strip() for point in key_points if point]

        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from LLM response, trying fallback")

        # Fallback: Split by newlines and extract bullet points
        lines = response.strip().split('\n')
        key_points = []

        for line in lines:
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Remove common bullet point markers
            line = re.sub(r'^[-*•]\s*', '', line)
            line = re.sub(r'^\d+\.\s*', '', line)

            # Remove quotes
            line = line.strip('"\'')

            if line and len(line) > 10:  # Minimum length
                key_points.append(line)

        return key_points

    def _validate_key_points(self, key_points: List[str]) -> List[str]:
        """
        Validate and clean key points.

        Args:
            key_points: Raw key points from LLM

        Returns:
            Cleaned and validated key points
        """
        validated = []

        for point in key_points:
            # Clean whitespace
            point = point.strip()

            # Skip empty or too short
            if len(point) < 10:
                continue

            # Skip too long (probably not a key point)
            if len(point) > 500:
                point = point[:497] + "..."

            # Ensure it ends with punctuation
            if point and point[-1] not in '.!?':
                point += '.'

            validated.append(point)

        # Ensure we have between min and max points
        if len(validated) < self._min_points:
            logger.warning(
                f"Only extracted {len(validated)} key points (min: {self._min_points})"
            )

        if len(validated) > self._max_points:
            validated = validated[: self._max_points]

        return validated

    def _generate_fallback_key_points(self, trend: Trend) -> List[str]:
        """
        Generate fallback key points from trend data.

        Used when LLM extraction fails.

        Args:
            trend: Trend to generate points from

        Returns:
            List of fallback key points
        """
        points = []

        # Point 1: Basic description
        points.append(
            f"Trending in {trend.category.value} with {trend.item_count} related items."
        )

        # Point 2: Engagement
        if trend.total_engagement.score > 0:
            points.append(
                f"High engagement with {trend.total_engagement.upvotes} upvotes "
                f"and {trend.total_engagement.comments} comments."
            )

        # Point 3: Sources
        if len(trend.sources) > 1:
            points.append(
                f"Covered across {len(trend.sources)} sources: "
                f"{', '.join(s.value for s in trend.sources[:3])}."
            )

        # Point 4: Keywords
        if trend.keywords:
            top_keywords = ", ".join(trend.keywords[:5])
            points.append(f"Related to: {top_keywords}.")

        return points[: self._max_points]


# ============================================================================
# Topic Key Points (for topics before they become trends)
# ============================================================================


class TopicKeyPointExtractor:
    """
    Extractor for key points from topics (before ranking).

    Simpler version that doesn't require full trend analysis.
    """

    def __init__(self, llm_service: BaseLLMService, max_points: int = 3):
        """
        Initialize topic key point extractor.

        Args:
            llm_service: LLM service for text generation
            max_points: Maximum number of key points
        """
        self._llm_service = llm_service
        self._max_points = max_points

    async def extract_from_topic(self, topic: Topic) -> List[str]:
        """
        Extract key points from a topic.

        Args:
            topic: Topic to analyze

        Returns:
            List of key point strings
        """
        prompt = f"""Extract {self._max_points} key points from this topic:

Title: {topic.title}
Summary: {topic.summary}
Keywords: {', '.join(topic.keywords)}

Return as JSON array of strings."""

        try:
            response = await self._llm_service.generate(
                prompt=prompt,
                system_prompt=KeyPointExtractor.SYSTEM_PROMPT,
                max_tokens=300,
                temperature=0.3,
            )

            # Parse similar to KeyPointExtractor
            extractor = KeyPointExtractor(self._llm_service)
            key_points = extractor._parse_response(response)
            key_points = extractor._validate_key_points(key_points)

            return key_points[: self._max_points]

        except Exception as e:
            logger.error(f"Failed to extract key points from topic {topic.id}: {e}")
            return [topic.summary]  # Fallback to summary


# ============================================================================
# Factory Function
# ============================================================================


def get_key_point_extractor(
    llm_service: BaseLLMService,
    item_repo: Optional[ItemRepository] = None,
) -> KeyPointExtractor:
    """
    Factory function to create KeyPointExtractor.

    Args:
        llm_service: LLM service for extraction
        item_repo: Optional item repository

    Returns:
        KeyPointExtractor instance
    """
    return KeyPointExtractor(llm_service=llm_service, item_repo=item_repo)
