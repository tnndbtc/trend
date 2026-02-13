"""
Free extractive summarization service using classical NLP libraries.

This service provides cost-free summarization using extractive algorithms
from sumy, nltk, and gensim. Works completely offline without API calls.

Supported algorithms:
- TextRank: Graph-based ranking (recommended)
- LexRank: Graph-based with cosine similarity
- LSA: Latent Semantic Analysis
- Luhn: Word frequency based (fastest)
- KL: Kullback-Leibler divergence
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Sumy extractive summarization
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.summarizers.luhn import LuhnSummarizer
from sumy.summarizers.kl import KLSummarizer

# NLTK for tokenization and keywords
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize

# Scikit-learn for TF-IDF keyword extraction
from sklearn.feature_extraction.text import TfidfVectorizer

from trend_agent.intelligence.interfaces import BaseLLMService

logger = logging.getLogger(__name__)


@dataclass
class SummarizationConfig:
    """Configuration for free summarization."""
    algorithm: str = 'textrank'  # textrank, lexrank, lsa
    language: str = 'english'
    min_sentence_length: int = 10
    max_sentences: int = 5
    keyword_count: int = 10


class FreeSummarizationService(BaseLLMService):
    """
    Free extractive summarization service using classical NLP.

    This service provides zero-cost summarization using open-source libraries:
    - sumy: Extractive summarization algorithms
    - nltk: Natural language processing
    - sklearn: TF-IDF for keyword extraction

    All processing happens locally without any API calls.
    """

    # Map algorithm names to summarizer classes
    ALGORITHMS = {
        'textrank': TextRankSummarizer,
        'lexrank': LexRankSummarizer,
        'lsa': LsaSummarizer,
        'luhn': LuhnSummarizer,
        'kl': KLSummarizer,
    }

    def __init__(self, algorithm: str = 'textrank', language: str = 'english'):
        """
        Initialize free summarization service.

        Args:
            algorithm: Summarization algorithm ('textrank', 'lexrank', 'lsa', 'luhn', 'kl')
            language: Language for tokenization ('english', 'spanish', etc.)
        """
        self.config = SummarizationConfig(algorithm=algorithm, language=language)
        self._ensure_nltk_resources()

        logger.info(f"Initialized FreeSummarizationService with {algorithm} algorithm")

    def _ensure_nltk_resources(self):
        """Download required NLTK data if not present."""
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            logger.info("Downloading NLTK punkt tokenizer...")
            nltk.download('punkt', quiet=True)

        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            logger.info("Downloading NLTK stopwords...")
            nltk.download('stopwords', quiet=True)

    def _get_summarizer(self):
        """Get summarizer instance based on configured algorithm."""
        summarizer_class = self.ALGORITHMS.get(self.config.algorithm)
        if not summarizer_class:
            logger.warning(f"Unknown algorithm {self.config.algorithm}, falling back to TextRank")
            summarizer_class = TextRankSummarizer

        return summarizer_class()

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for summarization."""
        if not text:
            return ""

        # Remove extra whitespace
        text = " ".join(text.split())

        # Ensure text ends with period
        if text and not text.endswith('.'):
            text += '.'

        return text

    def _calculate_sentence_count(self, text: str, max_length: int) -> int:
        """Calculate optimal sentence count based on text length and max_length."""
        # Average sentence length in characters
        sentences = sent_tokenize(text)
        if not sentences:
            return 1

        avg_sentence_length = len(text) // len(sentences) if sentences else 50

        # Calculate how many sentences fit in max_length
        optimal_count = max(1, max_length // avg_sentence_length)

        # Cap at configured maximum
        return min(optimal_count, self.config.max_sentences)

    async def summarize(
        self,
        text: str,
        max_length: int = 200,
        style: str = 'concise'
    ) -> str:
        """
        Generate extractive summary of the text.

        Args:
            text: Input text to summarize
            max_length: Maximum length of summary in characters
            style: Summary style (ignored for extractive, kept for compatibility)

        Returns:
            Extractive summary as string
        """
        if not text or len(text.strip()) == 0:
            return ""

        # Clean text
        text = self._clean_text(text)

        # If text is already short enough, return as-is
        if len(text) <= max_length:
            return text

        try:
            # Parse text
            parser = PlaintextParser.from_string(
                text,
                Tokenizer(self.config.language)
            )

            # Get summarizer
            summarizer = self._get_summarizer()

            # Calculate sentence count
            sentences_count = self._calculate_sentence_count(text, max_length)

            # Generate summary
            summary_sentences = summarizer(parser.document, sentences_count)

            # Convert to string
            summary = ' '.join(str(sentence) for sentence in summary_sentences)

            # Truncate if still too long
            if len(summary) > max_length:
                summary = summary[:max_length].rsplit(' ', 1)[0] + '...'

            logger.debug(f"Summarized {len(text)} chars to {len(summary)} chars using {self.config.algorithm}")

            return summary

        except Exception as e:
            logger.error(f"Error in summarization: {e}")
            # Fallback: return first max_length characters
            return text[:max_length].rsplit(' ', 1)[0] + '...' if len(text) > max_length else text

    async def extract_key_points(self, text: str, max_points: int = 5) -> List[str]:
        """
        Extract key points from text as bullet points.

        Args:
            text: Input text
            max_points: Maximum number of key points to extract

        Returns:
            List of key point strings
        """
        if not text or len(text.strip()) == 0:
            return []

        try:
            # Get more sentences than needed, then select best ones
            parser = PlaintextParser.from_string(
                text,
                Tokenizer(self.config.language)
            )

            summarizer = self._get_summarizer()

            # Get 1.5x the requested points
            sentences = summarizer(parser.document, int(max_points * 1.5))

            # Convert to list of strings
            key_points = []
            for sentence in sentences:
                point = str(sentence).strip()
                if point and len(point) > self.config.min_sentence_length:
                    # Ensure it ends with punctuation
                    if not point[-1] in '.!?':
                        point += '.'
                    key_points.append(point)

                if len(key_points) >= max_points:
                    break

            return key_points

        except Exception as e:
            logger.error(f"Error extracting key points: {e}")
            # Fallback: return first few sentences
            sentences = sent_tokenize(text)
            return [s for s in sentences[:max_points] if len(s) > self.config.min_sentence_length]

    async def summarize_topics(
        self,
        topics: List[Dict[str, Any]],
        max_topics: int = 10
    ) -> List[str]:
        """
        Batch summarize multiple topics.

        Args:
            topics: List of topic dictionaries with 'description' or 'title' fields
            max_topics: Maximum number of topics to summarize

        Returns:
            List of summary strings
        """
        summaries = []

        for topic in topics[:max_topics]:
            # Get text from topic
            text = topic.get('description') or topic.get('content') or topic.get('title', '')

            if text:
                summary = await self.summarize(text, max_length=100, style='concise')
                summaries.append(summary)
            else:
                summaries.append("")

        return summaries

    def _extract_keywords_tfidf(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Extract keywords using TF-IDF.

        Args:
            text: Input text
            max_keywords: Maximum number of keywords to extract

        Returns:
            List of keyword strings
        """
        try:
            # Get stopwords for language
            try:
                stop_words = set(stopwords.words(self.config.language))
            except:
                stop_words = set()

            # Use TF-IDF to extract keywords
            vectorizer = TfidfVectorizer(
                max_features=max_keywords,
                stop_words=list(stop_words),
                ngram_range=(1, 2),  # Single words and bigrams
                min_df=1
            )

            # Fit and transform
            try:
                vectors = vectorizer.fit_transform([text])
                keywords = vectorizer.get_feature_names_out().tolist()
                return keywords[:max_keywords]
            except:
                # Fallback: simple word frequency
                words = word_tokenize(text.lower())
                freq_dist = nltk.FreqDist(
                    w for w in words
                    if w.isalnum() and w not in stop_words and len(w) > 2
                )
                return [word for word, _ in freq_dist.most_common(max_keywords)]

        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return []

    async def generate_tags(self, text: str, max_tags: int = 10) -> List[str]:
        """
        Generate tags for text.

        Args:
            text: Input text
            max_tags: Maximum number of tags

        Returns:
            List of tag strings
        """
        return self._extract_keywords_tfidf(text, max_tags)

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """
        Generate text from prompt.

        Note: Extractive summarization doesn't support generative tasks.
        Returns empty string for compatibility.

        Args:
            prompt: Input prompt (ignored)
            max_tokens: Maximum tokens (ignored)
            temperature: Sampling temperature (ignored)

        Returns:
            Empty string
        """
        logger.warning("generate() called on FreeSummarizationService - not supported for extractive methods")
        return ""

    async def analyze_trend(self, trend: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a trend and return structured insights.

        Args:
            trend: Trend dictionary with description/content

        Returns:
            Dictionary with summary, key_points, and tags
        """
        text = trend.get('description') or trend.get('content') or trend.get('summary', '')

        if not text:
            return {
                'summary': '',
                'key_points': [],
                'tags': []
            }

        # Generate analysis components
        summary = await self.summarize(text, max_length=200)
        key_points = await self.extract_key_points(text, max_points=5)
        tags = await self.generate_tags(text, max_tags=10)

        return {
            'summary': summary,
            'key_points': key_points,
            'tags': tags,
            'algorithm': self.config.algorithm
        }

    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """
        Chat interface (not supported for extractive summarization).

        Args:
            messages: List of message dictionaries
            max_tokens: Maximum tokens (ignored)
            temperature: Sampling temperature (ignored)

        Returns:
            Empty string
        """
        logger.warning("chat() called on FreeSummarizationService - not supported")
        return ""

    def get_model_name(self) -> str:
        """Get the model/algorithm name."""
        return f"free-{self.config.algorithm}"

    def get_cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """Get cost estimate (always $0 for free service)."""
        return 0.0

    def __str__(self) -> str:
        return f"FreeSummarizationService(algorithm={self.config.algorithm}, language={self.config.language})"

    def __repr__(self) -> str:
        return self.__str__()
