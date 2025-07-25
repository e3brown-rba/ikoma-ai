"""
Content Extractor Module for iKOMA

Provides high-quality HTML→text extraction with trafilatura and quality assessment.
Implements multi-factor content quality scoring and intelligent text chunking.
Part of Epic E-01: Internet Tooling - Issue #6.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import trafilatura

    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    logger.warning("trafilatura not available, falling back to basic extraction")

try:
    import textstat

    TEXTSTAT_AVAILABLE = True
except ImportError:
    TEXTSTAT_AVAILABLE = False
    logger.warning("textstat not available, quality scoring will be limited")

try:
    from bs4 import BeautifulSoup

    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False
    logger.warning("beautifulsoup4 not available, fallback extraction may fail")


@dataclass
class ExtractedContent:
    """High-quality extracted web content with metadata."""

    url: str
    title: str
    text_chunks: list[str]
    quality_score: float
    readability_score: float
    metadata: dict[str, Any]
    extraction_method: str
    timestamp: str


class ContentQualityScorer:
    """Multi-factor content quality assessment."""

    @staticmethod
    def calculate_quality_score(text: str) -> dict[str, float]:
        """Calculate comprehensive quality metrics."""
        if not text or len(text.strip()) < 50:
            return {
                "overall": 0.0,
                "readability": 0.0,
                "length": 0.0,
                "vocabulary": 0.0,
                "structure": 0.0,
            }

        # Readability (30% weight)
        if TEXTSTAT_AVAILABLE:
            try:
                flesch_score = textstat.flesch_reading_ease(text)
                readability = max(0, min(1, flesch_score / 100))
            except Exception:
                readability = 0.5  # Fallback if textstat fails
        else:
            # Simple readability approximation
            sentence_count: int = len(re.split(r"[.!?]+", text))
            word_count: int = len(re.findall(r"\b\w+\b", text))
            avg_sentence_length = (
                word_count / sentence_count if sentence_count > 0 else 0
            )
            readability = max(0, min(1, 1 - abs(avg_sentence_length - 15) / 20))

        # Content length (20% weight) - optimal 500-2000 chars
        length = len(text)
        length_score = (
            min(1.0, length / 2000) if length <= 2000 else max(0.5, 2000 / length)
        )

        # Vocabulary diversity (20% weight)
        words: list[str] = re.findall(r"\b\w+\b", text.lower())
        unique_words: set[str] = set(words)
        vocab_diversity = len(unique_words) / len(words) if words else 0
        vocab_score = min(1.0, vocab_diversity * 2)  # Normalize to 0-1

        # Sentence structure (15% weight)
        sentence_count = len(re.split(r"[.!?]+", text))
        avg_sentence_length = len(words) / sentence_count if sentence_count > 0 else 0
        structure_score = (
            1.0
            if 10 <= avg_sentence_length <= 20
            else max(0.3, 1 - abs(avg_sentence_length - 15) / 15)
        )

        # Calculate weighted overall score
        overall = (
            readability * 0.30
            + length_score * 0.20
            + vocab_score * 0.20
            + structure_score * 0.15
            + 0.15
        )  # 15% base score

        return {
            "overall": round(overall, 3),
            "readability": round(readability, 3),
            "length": round(length_score, 3),
            "vocabulary": round(vocab_score, 3),
            "structure": round(structure_score, 3),
        }


class ModernContentExtractor:
    """State-of-the-art content extraction with quality assessment."""

    def __init__(self, min_quality_score: float = 0.6):
        self.min_quality_score = min_quality_score
        self.quality_scorer = ContentQualityScorer()

        # Configure trafilatura for optimal extraction if available
        if TRAFILATURA_AVAILABLE:
            self.trafilatura_config = trafilatura.settings.use_config()
            self.trafilatura_config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")
            self.trafilatura_config.set("DEFAULT", "MIN_EXTRACTED_SIZE", "200")
        else:
            self.trafilatura_config = None  # type: ignore

    def extract_content(
        self, url: str, html_content: str, chunk_size: int = 1000
    ) -> ExtractedContent:
        """Extract and assess content quality using modern techniques."""

        # Primary extraction with trafilatura (best performance)
        extracted_text = ""
        extraction_method = "unknown"

        if TRAFILATURA_AVAILABLE:
            try:
                extracted_result = trafilatura.extract(
                    html_content,
                    config=self.trafilatura_config,
                    include_comments=False,
                    include_tables=True,
                    include_formatting=False,
                )
                if extracted_result is not None:
                    extracted_text = extracted_result
                    extraction_method = "trafilatura"
            except Exception as e:
                logger.warning(f"Trafilatura extraction failed: {e}")

        # Fallback to bare extraction if primary fails
        if not extracted_text or len(extracted_text.strip()) < 100:
            if TRAFILATURA_AVAILABLE:
                try:
                    extracted_result = trafilatura.extract(
                        html_content,
                        config=self.trafilatura_config,
                        favor_precision=False,
                        favor_recall=True,
                    )
                    if extracted_result is not None:
                        extracted_text = extracted_result
                        extraction_method = "trafilatura_fallback"
                except Exception as e:
                    logger.warning(f"Trafilatura fallback failed: {e}")

        # Final fallback to basic extraction
        if not extracted_text and BEAUTIFULSOUP_AVAILABLE:
            try:
                soup = BeautifulSoup(html_content, "html.parser")
                # Remove unwanted elements
                for element in soup(
                    ["script", "style", "nav", "footer", "header", "aside"]
                ):
                    element.decompose()
                extracted_text = soup.get_text(separator=" ", strip=True)
                extraction_method = "beautifulsoup_fallback"
            except Exception as e:
                logger.warning(f"BeautifulSoup fallback failed: {e}")

        # If still no text, use basic regex extraction
        if not extracted_text:
            # Very basic text extraction
            text_match = re.search(
                r"<body[^>]*>(.*?)</body>", html_content, re.DOTALL | re.IGNORECASE
            )
            if text_match:
                body_content = text_match.group(1)
                # Remove HTML tags
                extracted_text = re.sub(r"<[^>]+>", " ", body_content)
                extracted_text = re.sub(r"\s+", " ", extracted_text).strip()
                extraction_method = "regex_fallback"

        # Extract title
        title: str = url
        if TRAFILATURA_AVAILABLE:
            try:
                metadata_obj = trafilatura.extract_metadata(html_content)
                if metadata_obj and metadata_obj.title:
                    extracted_title = metadata_obj.title
                    if extracted_title is not None:
                        title = str(extracted_title)
            except Exception as e:
                logger.debug(f"Title extraction failed: {e}")

        # Quality assessment
        quality_metrics = self.quality_scorer.calculate_quality_score(
            extracted_text or ""
        )

        # Text chunking for embedding
        chunks = self._intelligent_chunk_text(extracted_text or "", chunk_size)

        # Metadata compilation
        metadata: dict[str, Any] = {
            "extraction_method": extraction_method,
            "content_length": len(extracted_text or ""),
            "chunk_count": len(chunks),
            "quality_metrics": quality_metrics,
            "domain": url.split("/")[2] if "/" in url else url,
            "language": "unknown",  # Could be enhanced with language detection
        }

        # Try to get language from trafilatura metadata
        if TRAFILATURA_AVAILABLE:
            try:
                metadata_obj = trafilatura.extract_metadata(html_content)
                if metadata_obj and metadata_obj.language:
                    extracted_language = metadata_obj.language
                    if extracted_language is not None:
                        metadata["language"] = str(extracted_language)
            except Exception as e:
                logger.debug(f"Language extraction failed: {e}")

        return ExtractedContent(
            url=url,
            title=title.strip(),
            text_chunks=chunks,
            quality_score=quality_metrics["overall"],
            readability_score=quality_metrics["readability"],
            metadata=metadata,
            extraction_method=extraction_method,
            timestamp=datetime.now().isoformat(),
        )

    def _intelligent_chunk_text(self, text: str, chunk_size: int) -> list[str]:
        """Intelligent text chunking preserving sentence boundaries."""
        if not text:
            return []

        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= chunk_size:
                current_chunk += sentence + " "
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks


# Global extractor instance
_content_extractor = ModernContentExtractor(min_quality_score=0.6)


def get_content_extractor() -> ModernContentExtractor:
    """Get the global content extractor instance."""
    return _content_extractor


def extract_web_content(
    url: str, html_content: str, chunk_size: int = 1000
) -> ExtractedContent:
    """Extract content from HTML using the global extractor."""
    return _content_extractor.extract_content(url, html_content, chunk_size)
