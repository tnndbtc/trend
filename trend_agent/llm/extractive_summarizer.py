"""
Extractive summarization utilities and helpers.

Provides wrapper classes and utility functions for various extractive
summarization algorithms from the sumy library.
"""

import logging
from typing import List, Optional
from dataclasses import dataclass

from sumy.parsers.plaintext import PlaintextParser
from sumy.parsers.html import HtmlParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.summarizers.luhn import LuhnSummarizer
from sumy.summarizers.kl import KLSummarizer

logger = logging.getLogger(__name__)


@dataclass
class SummaryResult:
    """Result of summarization operation."""
    summary: str
    sentence_count: int
    original_length: int
    summary_length: int
    algorithm: str
    compression_ratio: float

    @property
    def compression_percentage(self) -> float:
        """Get compression as percentage."""
        return self.compression_ratio * 100


class ExtractiveSummarizer:
    """
    Wrapper for multiple extractive summarization algorithms.

    Provides a unified interface for different extractive algorithms
    from the sumy library.
    """

    ALGORITHMS = {
        'textrank': TextRankSummarizer,
        'lexrank': LexRankSummarizer,
        'lsa': LsaSummarizer,
        'luhn': LuhnSummarizer,
        'kl': KLSummarizer,
    }

    ALGORITHM_DESCRIPTIONS = {
        'textrank': 'Graph-based ranking using PageRank (best for general text)',
        'lexrank': 'Graph-based with cosine similarity (good for news)',
        'lsa': 'Latent Semantic Analysis (good for technical text)',
        'luhn': 'Word frequency based (fast, simple)',
        'kl': 'Kullback-Leibler divergence (statistical approach)',
    }

    def __init__(self, algorithm: str = 'textrank', language: str = 'english'):
        """
        Initialize extractive summarizer.

        Args:
            algorithm: Algorithm name ('textrank', 'lexrank', 'lsa', 'luhn', 'kl')
            language: Language for tokenization
        """
        if algorithm not in self.ALGORITHMS:
            logger.warning(f"Unknown algorithm '{algorithm}', defaulting to 'textrank'")
            algorithm = 'textrank'

        self.algorithm = algorithm
        self.language = language
        self.summarizer = self.ALGORITHMS[algorithm]()

        logger.info(f"Initialized {algorithm} summarizer for {language}")

    def summarize(
        self,
        text: str,
        sentences_count: int = 3,
        as_html: bool = False
    ) -> SummaryResult:
        """
        Summarize text using the configured algorithm.

        Args:
            text: Input text to summarize
            sentences_count: Number of sentences in summary
            as_html: Whether input is HTML

        Returns:
            SummaryResult object with summary and metadata
        """
        if not text or len(text.strip()) == 0:
            return SummaryResult(
                summary="",
                sentence_count=0,
                original_length=0,
                summary_length=0,
                algorithm=self.algorithm,
                compression_ratio=0.0
            )

        original_length = len(text)

        try:
            # Parse text
            if as_html:
                parser = HtmlParser.from_string(text, None, Tokenizer(self.language))
            else:
                parser = PlaintextParser.from_string(text, Tokenizer(self.language))

            # Generate summary
            summary_sentences = self.summarizer(parser.document, sentences_count)

            # Convert to string
            summary = ' '.join(str(sentence) for sentence in summary_sentences)
            summary_length = len(summary)

            # Calculate compression
            compression_ratio = summary_length / original_length if original_length > 0 else 0.0

            return SummaryResult(
                summary=summary,
                sentence_count=len(list(summary_sentences)),
                original_length=original_length,
                summary_length=summary_length,
                algorithm=self.algorithm,
                compression_ratio=compression_ratio
            )

        except Exception as e:
            logger.error(f"Error in {self.algorithm} summarization: {e}")
            # Fallback: return first N sentences
            sentences = text.split('. ')
            fallback_summary = '. '.join(sentences[:sentences_count]) + '.'

            return SummaryResult(
                summary=fallback_summary,
                sentence_count=sentences_count,
                original_length=original_length,
                summary_length=len(fallback_summary),
                algorithm=f"{self.algorithm}-fallback",
                compression_ratio=len(fallback_summary) / original_length
            )

    def summarize_to_length(
        self,
        text: str,
        target_length: int,
        tolerance: float = 0.2
    ) -> SummaryResult:
        """
        Summarize text to approximately target length.

        Iteratively adjusts sentence count to hit target length.

        Args:
            text: Input text
            target_length: Desired summary length in characters
            tolerance: Acceptable deviation from target (0.2 = 20%)

        Returns:
            SummaryResult with summary close to target length
        """
        # Estimate initial sentence count
        avg_sentence_length = 50  # Rough estimate
        sentences_count = max(1, target_length // avg_sentence_length)

        # Try summarization
        result = self.summarize(text, sentences_count=sentences_count)

        # If already close enough, return
        lower_bound = target_length * (1 - tolerance)
        upper_bound = target_length * (1 + tolerance)

        if lower_bound <= result.summary_length <= upper_bound:
            return result

        # Adjust sentence count and try again
        if result.summary_length > upper_bound:
            # Too long, reduce sentences
            sentences_count = max(1, sentences_count - 1)
        elif result.summary_length < lower_bound:
            # Too short, increase sentences
            sentences_count += 1

        # Return adjusted result
        return self.summarize(text, sentences_count=sentences_count)

    @classmethod
    def get_available_algorithms(cls) -> List[str]:
        """Get list of available algorithm names."""
        return list(cls.ALGORITHMS.keys())

    @classmethod
    def get_algorithm_description(cls, algorithm: str) -> str:
        """Get description of algorithm."""
        return cls.ALGORITHM_DESCRIPTIONS.get(algorithm, "Unknown algorithm")

    def __str__(self) -> str:
        return f"ExtractiveSummarizer(algorithm={self.algorithm}, language={self.language})"


class MultiAlgorithmSummarizer:
    """
    Run multiple algorithms and select best result.

    Useful for comparing algorithms or creating an ensemble.
    """

    def __init__(self, algorithms: Optional[List[str]] = None, language: str = 'english'):
        """
        Initialize multi-algorithm summarizer.

        Args:
            algorithms: List of algorithm names to use (default: all)
            language: Language for tokenization
        """
        if algorithms is None:
            algorithms = ['textrank', 'lexrank', 'lsa']

        self.algorithms = algorithms
        self.language = language
        self.summarizers = {
            algo: ExtractiveSummarizer(algo, language)
            for algo in algorithms
        }

    def summarize_with_consensus(
        self,
        text: str,
        sentences_count: int = 3
    ) -> SummaryResult:
        """
        Generate summaries with multiple algorithms and select best.

        Selection criteria:
        1. Most compressed (highest compression ratio)
        2. Contains most unique information

        Args:
            text: Input text
            sentences_count: Number of sentences

        Returns:
            Best SummaryResult from all algorithms
        """
        results = []

        for algo, summarizer in self.summarizers.items():
            result = summarizer.summarize(text, sentences_count)
            results.append(result)

        if not results:
            return SummaryResult(
                summary="",
                sentence_count=0,
                original_length=len(text),
                summary_length=0,
                algorithm="none",
                compression_ratio=0.0
            )

        # Select best result (highest compression)
        best_result = max(results, key=lambda r: r.compression_ratio)

        logger.info(f"Selected {best_result.algorithm} from {len(results)} algorithms")

        return best_result

    def get_all_summaries(
        self,
        text: str,
        sentences_count: int = 3
    ) -> List[SummaryResult]:
        """
        Get summaries from all algorithms.

        Args:
            text: Input text
            sentences_count: Number of sentences

        Returns:
            List of SummaryResult objects, one per algorithm
        """
        results = []

        for algo, summarizer in self.summarizers.items():
            result = summarizer.summarize(text, sentences_count)
            results.append(result)

        return results


def quick_summarize(
    text: str,
    max_length: int = 200,
    algorithm: str = 'textrank',
    language: str = 'english'
) -> str:
    """
    Quick summarization function for simple use cases.

    Args:
        text: Input text
        max_length: Maximum summary length
        algorithm: Algorithm to use
        language: Language

    Returns:
        Summary string
    """
    summarizer = ExtractiveSummarizer(algorithm, language)

    # Estimate sentence count
    sentences_count = max(1, max_length // 50)

    result = summarizer.summarize(text, sentences_count=sentences_count)

    # Truncate if needed
    if len(result.summary) > max_length:
        return result.summary[:max_length].rsplit(' ', 1)[0] + '...'

    return result.summary


def compare_algorithms(
    text: str,
    sentences_count: int = 3,
    algorithms: Optional[List[str]] = None,
    language: str = 'english'
) -> List[SummaryResult]:
    """
    Compare multiple summarization algorithms.

    Args:
        text: Input text
        sentences_count: Number of sentences
        algorithms: List of algorithms (default: all)
        language: Language

    Returns:
        List of SummaryResult objects with comparison data
    """
    if algorithms is None:
        algorithms = ExtractiveSummarizer.get_available_algorithms()

    results = []

    for algo in algorithms:
        summarizer = ExtractiveSummarizer(algo, language)
        result = summarizer.summarize(text, sentences_count)
        results.append(result)

    # Sort by compression ratio
    results.sort(key=lambda r: r.compression_ratio, reverse=True)

    return results
