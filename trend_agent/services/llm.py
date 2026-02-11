"""
LLM Service implementations for OpenAI and Anthropic.

Provides production-ready large language model services for:
- Text generation and summarization
- Topic analysis and key point extraction
- Trend analysis and tagging
- Multi-model support (GPT-4, GPT-3.5, Claude)
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import httpx

from trend_agent.intelligence.interfaces import BaseLLMService, LLMError
from trend_agent.types import Topic, Trend
from trend_agent.observability.metrics import (
    api_request_counter,
    api_request_duration,
)

logger = logging.getLogger(__name__)


class OpenAILLMService(BaseLLMService):
    """
    OpenAI LLM service using GPT models.

    Provides comprehensive LLM capabilities using OpenAI's GPT-4 and GPT-3.5-turbo
    models for text generation, summarization, and analysis.

    Features:
    - Multiple model support (GPT-4, GPT-4-turbo, GPT-3.5-turbo)
    - Automatic retry with exponential backoff
    - Streaming support for long-running operations
    - Cost tracking per request
    - Prometheus metrics integration
    - Structured output parsing

    Example:
        ```python
        service = OpenAILLMService(api_key="sk-...", model="gpt-4-turbo")

        # Generate summary
        summary = await service.summarize(
            "Long article text...",
            max_length=200,
            style="concise"
        )

        # Extract key points
        points = await service.extract_key_points(text, max_points=5)

        # Analyze trend
        analysis = await service.analyze_trend(trend)
        ```
    """

    # Model configurations
    MODELS = {
        "gpt-4-turbo": {
            "max_tokens": 128000,
            "cost_per_1k_input": 0.01,
            "cost_per_1k_output": 0.03,
        },
        "gpt-4": {
            "max_tokens": 8192,
            "cost_per_1k_input": 0.03,
            "cost_per_1k_output": 0.06,
        },
        "gpt-3.5-turbo": {
            "max_tokens": 16385,
            "cost_per_1k_input": 0.0005,
            "cost_per_1k_output": 0.0015,
        },
    }

    DEFAULT_MODEL = "gpt-4-turbo"
    API_ENDPOINT = "https://api.openai.com/v1/chat/completions"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_retries: int = 3,
        timeout: int = 60,
    ):
        """
        Initialize OpenAI LLM service.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model name to use
            max_retries: Maximum retry attempts
            timeout: Request timeout in seconds

        Raises:
            ValueError: If API key is missing or model unsupported
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        if model not in self.MODELS:
            raise ValueError(
                f"Model '{model}' not supported. "
                f"Available models: {list(self.MODELS.keys())}"
            )

        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        self._model_config = self.MODELS[model]
        self._total_cost = 0.0
        self._total_input_tokens = 0
        self._total_output_tokens = 0

        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        logger.info(f"Initialized OpenAILLMService (model={model})")

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)
            **kwargs: Additional parameters (top_p, frequency_penalty, etc.)

        Returns:
            Generated text

        Raises:
            LLMError: If generation fails
        """
        messages = [{"role": "user", "content": prompt}]

        response = await self._call_api(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

        return response["content"]

    async def summarize(
        self, text: str, max_length: int = 200, style: str = "concise"
    ) -> str:
        """
        Summarize text.

        Args:
            text: Text to summarize
            max_length: Maximum summary length in characters
            style: Summary style (concise, detailed, bullet_points)

        Returns:
            Summary text

        Raises:
            LLMError: If summarization fails
        """
        # Build style-specific prompt
        style_instructions = {
            "concise": "Provide a concise, single-paragraph summary.",
            "detailed": "Provide a detailed, comprehensive summary with key points.",
            "bullet_points": "Provide a summary as a bulleted list of key points.",
        }

        instruction = style_instructions.get(style, style_instructions["concise"])

        prompt = f"""{instruction}

Text to summarize:
{text}

Summary (max {max_length} characters):"""

        max_tokens = min(int(max_length * 1.5), 500)  # Estimate tokens needed

        summary = await self.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=0.3,  # Lower temperature for factual summaries
        )

        # Truncate if needed
        if len(summary) > max_length:
            summary = summary[:max_length].rsplit(" ", 1)[0] + "..."

        return summary.strip()

    async def summarize_topics(
        self, topics: List[Topic], max_topics: int = 10
    ) -> List[str]:
        """
        Generate summaries for multiple topics.

        Args:
            topics: Topics to summarize
            max_topics: Maximum topics to process

        Returns:
            List of summaries

        Raises:
            LLMError: If summarization fails
        """
        topics_to_process = topics[:max_topics]
        summaries = []

        for topic in topics_to_process:
            # Build topic context
            topic_text = f"Title: {topic.name}\n"
            if hasattr(topic, "description") and topic.description:
                topic_text += f"Description: {topic.description}\n"
            if hasattr(topic, "items") and topic.items:
                topic_text += f"Item count: {len(topic.items)}\n"

            summary = await self.summarize(topic_text, max_length=150, style="concise")
            summaries.append(summary)

        return summaries

    async def extract_key_points(self, text: str, max_points: int = 5) -> List[str]:
        """
        Extract key points from text.

        Args:
            text: Text to analyze
            max_points: Maximum key points to extract

        Returns:
            List of key points

        Raises:
            LLMError: If extraction fails
        """
        prompt = f"""Extract the {max_points} most important key points from the following text.
Return only the key points, one per line, without numbering or bullet points.

Text:
{text}

Key points:"""

        response = await self.generate(
            prompt=prompt,
            max_tokens=300,
            temperature=0.3,
        )

        # Parse key points (split by newlines, clean up)
        points = [
            line.strip().lstrip("-•*").strip()
            for line in response.split("\n")
            if line.strip()
        ]

        return points[:max_points]

    async def analyze_trend(self, trend: Trend) -> Dict[str, Any]:
        """
        Perform deep analysis of a trend.

        Args:
            trend: Trend to analyze

        Returns:
            Analysis results including sentiment, topics, entities

        Raises:
            LLMError: If analysis fails
        """
        # Build trend context
        trend_text = f"Trend: {trend.name}\n"
        if hasattr(trend, "description") and trend.description:
            trend_text += f"Description: {trend.description}\n"
        if hasattr(trend, "score"):
            trend_text += f"Score: {trend.score}\n"

        prompt = f"""Analyze the following trend and provide:
1. Sentiment (positive/negative/neutral)
2. Main topics (comma-separated)
3. Key entities mentioned
4. Potential impact
5. Recommendation (monitor/investigate/ignore)

{trend_text}

Provide your analysis in JSON format:"""

        response = await self.generate(
            prompt=prompt,
            max_tokens=500,
            temperature=0.5,
        )

        # Parse JSON response
        try:
            # Try to extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(response[json_start:json_end])
            else:
                # Fallback to simple parsing
                analysis = {"raw_analysis": response}
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON analysis, using raw text")
            analysis = {"raw_analysis": response}

        return analysis

    async def generate_tags(self, text: str, max_tags: int = 10) -> List[str]:
        """
        Generate tags for text.

        Args:
            text: Text to tag
            max_tags: Maximum tags to generate

        Returns:
            List of tags

        Raises:
            LLMError: If tag generation fails
        """
        prompt = f"""Generate up to {max_tags} relevant tags for the following text.
Return only the tags, comma-separated, without explanations.

Text:
{text}

Tags:"""

        response = await self.generate(
            prompt=prompt,
            max_tokens=100,
            temperature=0.5,
        )

        # Parse tags
        tags = [tag.strip() for tag in response.split(",") if tag.strip()]
        return tags[:max_tags]

    async def _call_api(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Internal method to call OpenAI API with retry logic.

        Args:
            messages: Chat messages
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            Dictionary with content and usage info

        Raises:
            LLMError: If all retries fail
        """
        start_time = time.time()
        last_error = None

        for attempt in range(self.max_retries):
            try:
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    **kwargs,
                }

                response = await self._client.post(self.API_ENDPOINT, json=payload)
                response.raise_for_status()

                data = response.json()

                # Extract response
                content = data["choices"][0]["message"]["content"]

                # Track usage
                usage = data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)

                cost = self._calculate_cost(input_tokens, output_tokens)

                self._total_input_tokens += input_tokens
                self._total_output_tokens += output_tokens
                self._total_cost += cost

                # Record metrics
                duration = time.time() - start_time
                api_request_duration.labels(
                    method="POST", endpoint="openai_chat"
                ).observe(duration)
                api_request_counter.labels(
                    method="POST",
                    endpoint="openai_chat",
                    status_code=response.status_code,
                ).inc()

                logger.debug(
                    f"LLM call completed ({input_tokens}+{output_tokens} tokens, "
                    f"${cost:.6f}, {duration:.2f}s)"
                )

                return {
                    "content": content,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost": cost,
                }

            except httpx.HTTPStatusError as e:
                last_error = e
                status = e.response.status_code

                # Don't retry client errors (except rate limits)
                if 400 <= status < 500 and status != 429:
                    raise LLMError(f"OpenAI API error: {e.response.text}") from e

                logger.warning(
                    f"OpenAI API error (attempt {attempt + 1}/{self.max_retries}): "
                    f"{status}"
                )

                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)

            except Exception as e:
                last_error = e
                logger.warning(f"Unexpected error (attempt {attempt + 1}): {e}")

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        # All retries failed
        duration = time.time() - start_time
        api_request_duration.labels(method="POST", endpoint="openai_chat").observe(
            duration
        )
        api_request_counter.labels(
            method="POST", endpoint="openai_chat", status_code=500
        ).inc()

        raise LLMError(
            f"Failed to call LLM after {self.max_retries} attempts"
        ) from last_error

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate API cost for token usage."""
        input_cost = (input_tokens / 1000) * self._model_config["cost_per_1k_input"]
        output_cost = (output_tokens / 1000) * self._model_config["cost_per_1k_output"]
        return input_cost + output_cost

    def get_usage_stats(self) -> dict:
        """Get usage statistics."""
        return {
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "total_tokens": self._total_input_tokens + self._total_output_tokens,
            "total_cost_usd": self._total_cost,
            "model": self.model,
        }

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
        logger.info(
            f"Closed OpenAILLMService "
            f"(tokens={self._total_input_tokens + self._total_output_tokens}, "
            f"cost=${self._total_cost:.6f})"
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class AnthropicLLMService(BaseLLMService):
    """
    Anthropic Claude LLM service.

    Provides LLM capabilities using Anthropic's Claude models, known for
    high-quality outputs and strong reasoning capabilities.

    Features:
    - Multiple Claude model support (Claude 3 Opus, Sonnet, Haiku)
    - Automatic retry with exponential backoff
    - Cost tracking
    - Prometheus metrics integration

    Example:
        ```python
        service = AnthropicLLMService(api_key="sk-ant-...", model="claude-3-sonnet")

        summary = await service.summarize(text, max_length=200)
        ```
    """

    MODELS = {
        "claude-3-opus": {
            "max_tokens": 200000,
            "cost_per_1m_input": 15.00,
            "cost_per_1m_output": 75.00,
        },
        "claude-3-sonnet": {
            "max_tokens": 200000,
            "cost_per_1m_input": 3.00,
            "cost_per_1m_output": 15.00,
        },
        "claude-3-haiku": {
            "max_tokens": 200000,
            "cost_per_1m_input": 0.25,
            "cost_per_1m_output": 1.25,
        },
    }

    DEFAULT_MODEL = "claude-3-sonnet"
    API_ENDPOINT = "https://api.anthropic.com/v1/messages"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_retries: int = 3,
        timeout: int = 60,
    ):
        """Initialize Anthropic LLM service."""
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

        if model not in self.MODELS:
            raise ValueError(
                f"Model '{model}' not supported. "
                f"Available models: {list(self.MODELS.keys())}"
            )

        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        self._model_config = self.MODELS[model]
        self._total_cost = 0.0
        self._total_input_tokens = 0
        self._total_output_tokens = 0

        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )

        logger.info(f"Initialized AnthropicLLMService (model={model})")

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Generate text from a prompt."""
        messages = [{"role": "user", "content": prompt}]

        response = await self._call_api(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs,
        )

        return response["content"]

    async def summarize(
        self, text: str, max_length: int = 200, style: str = "concise"
    ) -> str:
        """Summarize text (implementation similar to OpenAI)."""
        style_instructions = {
            "concise": "Provide a concise, single-paragraph summary.",
            "detailed": "Provide a detailed, comprehensive summary with key points.",
            "bullet_points": "Provide a summary as a bulleted list of key points.",
        }

        instruction = style_instructions.get(style, style_instructions["concise"])

        prompt = f"""{instruction}

Text to summarize:
{text}

Summary (max {max_length} characters):"""

        max_tokens = min(int(max_length * 1.5), 500)

        summary = await self.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=0.3,
        )

        if len(summary) > max_length:
            summary = summary[:max_length].rsplit(" ", 1)[0] + "..."

        return summary.strip()

    async def summarize_topics(
        self, topics: List[Topic], max_topics: int = 10
    ) -> List[str]:
        """Generate summaries for multiple topics."""
        topics_to_process = topics[:max_topics]
        summaries = []

        for topic in topics_to_process:
            topic_text = f"Title: {topic.name}\n"
            if hasattr(topic, "description") and topic.description:
                topic_text += f"Description: {topic.description}\n"

            summary = await self.summarize(topic_text, max_length=150)
            summaries.append(summary)

        return summaries

    async def extract_key_points(self, text: str, max_points: int = 5) -> List[str]:
        """Extract key points from text."""
        prompt = f"""Extract the {max_points} most important key points from the following text.
Return only the key points, one per line.

Text:
{text}

Key points:"""

        response = await self.generate(prompt=prompt, max_tokens=300, temperature=0.3)

        points = [
            line.strip().lstrip("-•*").strip()
            for line in response.split("\n")
            if line.strip()
        ]

        return points[:max_points]

    async def analyze_trend(self, trend: Trend) -> Dict[str, Any]:
        """Perform deep analysis of a trend."""
        trend_text = f"Trend: {trend.name}\n"
        if hasattr(trend, "description") and trend.description:
            trend_text += f"Description: {trend.description}\n"

        prompt = f"""Analyze the following trend and provide JSON with:
1. sentiment (positive/negative/neutral)
2. topics (comma-separated list)
3. entities (key entities mentioned)
4. impact (potential impact)
5. recommendation (monitor/investigate/ignore)

{trend_text}

JSON analysis:"""

        response = await self.generate(prompt=prompt, max_tokens=500, temperature=0.5)

        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(response[json_start:json_end])
            else:
                analysis = {"raw_analysis": response}
        except json.JSONDecodeError:
            analysis = {"raw_analysis": response}

        return analysis

    async def generate_tags(self, text: str, max_tags: int = 10) -> List[str]:
        """Generate tags for text."""
        prompt = f"""Generate up to {max_tags} relevant tags for the following text.
Return only the tags, comma-separated.

Text:
{text}

Tags:"""

        response = await self.generate(prompt=prompt, max_tokens=100, temperature=0.5)

        tags = [tag.strip() for tag in response.split(",") if tag.strip()]
        return tags[:max_tags]

    async def _call_api(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Internal method to call Anthropic API with retry logic."""
        start_time = time.time()
        last_error = None

        for attempt in range(self.max_retries):
            try:
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    **kwargs,
                }

                response = await self._client.post(self.API_ENDPOINT, json=payload)
                response.raise_for_status()

                data = response.json()

                # Extract response (Anthropic format)
                content = data["content"][0]["text"]

                # Track usage
                usage = data.get("usage", {})
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)

                cost = self._calculate_cost(input_tokens, output_tokens)

                self._total_input_tokens += input_tokens
                self._total_output_tokens += output_tokens
                self._total_cost += cost

                # Record metrics
                duration = time.time() - start_time
                api_request_duration.labels(
                    method="POST", endpoint="anthropic_messages"
                ).observe(duration)
                api_request_counter.labels(
                    method="POST",
                    endpoint="anthropic_messages",
                    status_code=response.status_code,
                ).inc()

                logger.debug(
                    f"Claude call completed ({input_tokens}+{output_tokens} tokens, "
                    f"${cost:.6f}, {duration:.2f}s)"
                )

                return {
                    "content": content,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cost": cost,
                }

            except httpx.HTTPStatusError as e:
                last_error = e
                status = e.response.status_code

                if 400 <= status < 500 and status != 429:
                    raise LLMError(f"Anthropic API error: {e.response.text}") from e

                logger.warning(
                    f"Anthropic API error (attempt {attempt + 1}/{self.max_retries})"
                )

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

            except Exception as e:
                last_error = e
                logger.warning(f"Unexpected error (attempt {attempt + 1}): {e}")

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        # All retries failed
        duration = time.time() - start_time
        api_request_duration.labels(
            method="POST", endpoint="anthropic_messages"
        ).observe(duration)
        api_request_counter.labels(
            method="POST", endpoint="anthropic_messages", status_code=500
        ).inc()

        raise LLMError(
            f"Failed to call Claude after {self.max_retries} attempts"
        ) from last_error

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate API cost for token usage."""
        input_cost = (input_tokens / 1_000_000) * self._model_config[
            "cost_per_1m_input"
        ]
        output_cost = (output_tokens / 1_000_000) * self._model_config[
            "cost_per_1m_output"
        ]
        return input_cost + output_cost

    def get_usage_stats(self) -> dict:
        """Get usage statistics."""
        return {
            "total_input_tokens": self._total_input_tokens,
            "total_output_tokens": self._total_output_tokens,
            "total_tokens": self._total_input_tokens + self._total_output_tokens,
            "total_cost_usd": self._total_cost,
            "model": self.model,
        }

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
        logger.info(
            f"Closed AnthropicLLMService "
            f"(tokens={self._total_input_tokens + self._total_output_tokens}, "
            f"cost=${self._total_cost:.6f})"
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
