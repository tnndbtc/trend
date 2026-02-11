"""
Advanced Text Processing for Multi-Language Support.

Provides:
- CJK (Chinese, Japanese, Korean) text segmentation
- Romanization for non-Latin scripts
- Script detection and handling
- Special handling for mixed scripts
"""

import logging
import re
from typing import List, Optional, Dict, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# CJK Text Segmentation
# ============================================================================


class CJKSegmenter:
    """
    Segmenter for CJK (Chinese, Japanese, Korean) text.

    Handles word segmentation for languages without clear word boundaries.
    """

    def __init__(self):
        """Initialize CJK segmenter."""
        self._jieba = None  # Chinese segmenter (lazy load)
        self._mecab = None  # Japanese segmenter (lazy load)

    def segment_chinese(self, text: str) -> List[str]:
        """
        Segment Chinese text into words.

        Args:
            text: Chinese text to segment

        Returns:
            List of word tokens
        """
        try:
            # Lazy import jieba
            if self._jieba is None:
                import jieba
                self._jieba = jieba

            # Segment text
            words = list(self._jieba.cut(text))
            return [w.strip() for w in words if w.strip()]

        except ImportError:
            logger.warning("jieba not installed, using character-level segmentation")
            # Fallback: character-level segmentation
            return list(text)
        except Exception as e:
            logger.error(f"Failed to segment Chinese text: {e}")
            return [text]

    def segment_japanese(self, text: str) -> List[str]:
        """
        Segment Japanese text into words.

        Args:
            text: Japanese text to segment

        Returns:
            List of word tokens
        """
        try:
            # Lazy import MeCab
            if self._mecab is None:
                import MeCab
                self._mecab = MeCab.Tagger()

            # Parse and segment
            parsed = self._mecab.parse(text)
            words = []

            for line in parsed.split("\n"):
                if line == "EOS" or not line:
                    continue

                parts = line.split("\t")
                if len(parts) >= 1:
                    word = parts[0]
                    if word.strip():
                        words.append(word)

            return words

        except ImportError:
            logger.warning("MeCab not installed, using basic segmentation")
            # Fallback: split on spaces and punctuation
            return re.findall(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+", text)
        except Exception as e:
            logger.error(f"Failed to segment Japanese text: {e}")
            return [text]

    def segment_korean(self, text: str) -> List[str]:
        """
        Segment Korean text into words.

        Args:
            text: Korean text to segment

        Returns:
            List of word tokens
        """
        try:
            # Korean often has spaces between words already
            # But we can use konlpy for better segmentation
            from konlpy.tag import Okt

            okt = Okt()
            words = okt.morphs(text)
            return words

        except ImportError:
            logger.warning("konlpy not installed, using space-based segmentation")
            # Fallback: split on spaces
            return text.split()
        except Exception as e:
            logger.error(f"Failed to segment Korean text: {e}")
            return text.split()

    def segment(self, text: str, language: str) -> List[str]:
        """
        Segment text based on detected language.

        Args:
            text: Text to segment
            language: Language code (zh, ja, ko)

        Returns:
            List of segmented tokens
        """
        if language == "zh" or language.startswith("zh-"):
            return self.segment_chinese(text)
        elif language == "ja":
            return self.segment_japanese(text)
        elif language == "ko":
            return self.segment_korean(text)
        else:
            # Default: split on whitespace
            return text.split()


# ============================================================================
# Romanization
# ============================================================================


class Romanizer:
    """
    Romanizer for non-Latin scripts.

    Converts text from various scripts to Latin alphabet (romanization).
    """

    def romanize(self, text: str, script: str) -> str:
        """
        Romanize text from specified script.

        Args:
            text: Text to romanize
            script: Script type (chinese, japanese, korean, arabic, cyrillic, etc.)

        Returns:
            Romanized text
        """
        script_lower = script.lower()

        if script_lower in ["chinese", "zh"]:
            return self.romanize_chinese(text)
        elif script_lower in ["japanese", "ja"]:
            return self.romanize_japanese(text)
        elif script_lower in ["korean", "ko"]:
            return self.romanize_korean(text)
        elif script_lower in ["arabic", "ar"]:
            return self.romanize_arabic(text)
        elif script_lower in ["cyrillic", "russian", "ru"]:
            return self.romanize_cyrillic(text)
        else:
            return text  # Already Latin or unsupported

    def romanize_chinese(self, text: str) -> str:
        """
        Romanize Chinese to Pinyin.

        Args:
            text: Chinese text

        Returns:
            Pinyin romanization
        """
        try:
            from pypinyin import pinyin, Style

            # Convert to pinyin with tone marks
            result = pinyin(text, style=Style.TONE)
            return " ".join([item[0] for item in result])

        except ImportError:
            logger.warning("pypinyin not installed, skipping Chinese romanization")
            return text
        except Exception as e:
            logger.error(f"Failed to romanize Chinese: {e}")
            return text

    def romanize_japanese(self, text: str) -> str:
        """
        Romanize Japanese to Romaji.

        Args:
            text: Japanese text

        Returns:
            Romaji romanization
        """
        try:
            import pykakasi

            kakasi = pykakasi.kakasi()
            result = kakasi.convert(text)
            return " ".join([item["hepburn"] for item in result])

        except ImportError:
            logger.warning("pykakasi not installed, skipping Japanese romanization")
            return text
        except Exception as e:
            logger.error(f"Failed to romanize Japanese: {e}")
            return text

    def romanize_korean(self, text: str) -> str:
        """
        Romanize Korean to Revised Romanization.

        Args:
            text: Korean text

        Returns:
            Romanized text
        """
        try:
            from hangul_romanize import Transliter
            from hangul_romanize.rule import academic

            transliter = Transliter(academic)
            return transliter.translit(text)

        except ImportError:
            logger.warning("hangul-romanize not installed, skipping Korean romanization")
            return text
        except Exception as e:
            logger.error(f"Failed to romanize Korean: {e}")
            return text

    def romanize_arabic(self, text: str) -> str:
        """
        Romanize Arabic text.

        Args:
            text: Arabic text

        Returns:
            Romanized text
        """
        # Simple transliteration mapping
        arabic_to_latin = {
            "ا": "a",
            "ب": "b",
            "ت": "t",
            "ث": "th",
            "ج": "j",
            "ح": "h",
            "خ": "kh",
            "د": "d",
            "ذ": "dh",
            "ر": "r",
            "ز": "z",
            "س": "s",
            "ش": "sh",
            "ص": "s",
            "ض": "d",
            "ط": "t",
            "ظ": "z",
            "ع": "'",
            "غ": "gh",
            "ف": "f",
            "ق": "q",
            "ك": "k",
            "ل": "l",
            "م": "m",
            "ن": "n",
            "ه": "h",
            "و": "w",
            "ي": "y",
        }

        result = []
        for char in text:
            result.append(arabic_to_latin.get(char, char))

        return "".join(result)

    def romanize_cyrillic(self, text: str) -> str:
        """
        Romanize Cyrillic text (Russian, etc.).

        Args:
            text: Cyrillic text

        Returns:
            Romanized text
        """
        try:
            from transliterate import translit

            return translit(text, "ru", reversed=True)

        except ImportError:
            logger.warning("transliterate not installed, using basic romanization")
            # Basic mapping
            cyrillic_to_latin = {
                "а": "a", "б": "b", "в": "v", "г": "g", "д": "d",
                "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i",
                "й": "y", "к": "k", "л": "l", "м": "m", "н": "n",
                "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
                "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch",
                "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "",
                "э": "e", "ю": "yu", "я": "ya",
            }

            result = []
            for char in text.lower():
                result.append(cyrillic_to_latin.get(char, char))

            return "".join(result)
        except Exception as e:
            logger.error(f"Failed to romanize Cyrillic: {e}")
            return text


# ============================================================================
# Script Detection
# ============================================================================


class ScriptDetector:
    """
    Detect script types in text.

    Identifies: Latin, CJK, Arabic, Cyrillic, etc.
    """

    # Unicode ranges for different scripts
    SCRIPT_RANGES = {
        "latin": [(0x0041, 0x007A), (0x00C0, 0x00FF), (0x0100, 0x017F)],
        "chinese": [(0x4E00, 0x9FFF)],  # CJK Unified Ideographs
        "japanese_hiragana": [(0x3040, 0x309F)],
        "japanese_katakana": [(0x30A0, 0x30FF)],
        "korean": [(0xAC00, 0xD7AF)],  # Hangul Syllables
        "arabic": [(0x0600, 0x06FF), (0x0750, 0x077F)],
        "cyrillic": [(0x0400, 0x04FF)],
        "thai": [(0x0E00, 0x0E7F)],
        "devanagari": [(0x0900, 0x097F)],  # Hindi, Sanskrit
    }

    def detect_script(self, text: str) -> str:
        """
        Detect the primary script in text.

        Args:
            text: Text to analyze

        Returns:
            Script name (latin, chinese, japanese, etc.)
        """
        if not text:
            return "latin"

        script_counts = {script: 0 for script in self.SCRIPT_RANGES}

        for char in text:
            char_code = ord(char)

            for script, ranges in self.SCRIPT_RANGES.items():
                for start, end in ranges:
                    if start <= char_code <= end:
                        script_counts[script] += 1
                        break

        # Return script with highest count
        if max(script_counts.values()) == 0:
            return "latin"  # Default

        return max(script_counts, key=script_counts.get)

    def get_script_composition(self, text: str) -> Dict[str, float]:
        """
        Get script composition of text.

        Args:
            text: Text to analyze

        Returns:
            Dictionary of script -> percentage
        """
        if not text:
            return {"latin": 1.0}

        script_counts = {script: 0 for script in self.SCRIPT_RANGES}
        total_chars = 0

        for char in text:
            if not char.isspace():
                total_chars += 1
                char_code = ord(char)

                for script, ranges in self.SCRIPT_RANGES.items():
                    for start, end in ranges:
                        if start <= char_code <= end:
                            script_counts[script] += 1
                            break

        if total_chars == 0:
            return {"latin": 1.0}

        # Calculate percentages
        composition = {}
        for script, count in script_counts.items():
            if count > 0:
                composition[script] = count / total_chars

        return composition


# ============================================================================
# Factory Functions
# ============================================================================


def get_cjk_segmenter() -> CJKSegmenter:
    """Get CJK segmenter instance."""
    return CJKSegmenter()


def get_romanizer() -> Romanizer:
    """Get romanizer instance."""
    return Romanizer()


def get_script_detector() -> ScriptDetector:
    """Get script detector instance."""
    return ScriptDetector()
