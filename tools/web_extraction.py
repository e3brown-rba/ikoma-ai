from typing import Dict, Optional, Any, List
import re
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
from datetime import datetime
import logging

try:
    import trafilatura
    from trafilatura.settings import use_config
    from trafilatura.metadata import extract_metadata
except ImportError:
    trafilatura = None

try:
    from selectolax.parser import HTMLParser
except ImportError:
    HTMLParser = None

from bs4 import BeautifulSoup
from bs4.element import Tag


@dataclass
class ExtractedContent:
    """Structured representation of extracted web content."""

    title: str
    content: str
    url: str
    headers: Dict[str, List[str]]  # h1, h2, h3 hierarchy
    metadata: Dict[str, Any]
    extraction_method: str
    word_count: int
    language: Optional[str] = None


class WebContentExtractor:
    """Production-grade HTML content extraction with performance optimization."""

    def __init__(self, prefer_speed: bool = False):
        """
        Initialize extractor with strategy preference.

        Args:
            prefer_speed: If True, prefer selectolax for simple content
        """
        self.prefer_speed = prefer_speed
        self.trafilatura_available = trafilatura is not None
        self.selectolax_available = HTMLParser is not None

        # Configure trafilatura for optimal extraction
        if self.trafilatura_available:
            self.config = use_config()
            self.config.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")
            self.config.set("DEFAULT", "MIN_EXTRACTED_SIZE", "200")
            self.config.set("DEFAULT", "MIN_OUTPUT_SIZE", "100")

        self.logger = logging.getLogger(__name__)

    def extract(self, html: str, url: str) -> ExtractedContent:
        """
        Extract clean text content using optimal strategy.

        Args:
            html: Raw HTML content
            url: Source URL for metadata

        Returns:
            ExtractedContent with structured data
        """
        # Strategy selection based on content complexity and preferences
        if self.prefer_speed and self._is_simple_content(html):
            return self._extract_with_selectolax(html, url)
        elif self.trafilatura_available:
            return self._extract_with_trafilatura(html, url)
        elif self.selectolax_available:
            return self._extract_with_selectolax(html, url)
        else:
            return self._extract_with_beautifulsoup(html, url)

    def _is_simple_content(self, html: str) -> bool:
        """Heuristic to determine if content is simple enough for fast extraction."""
        # Simple heuristics: low script/style ratio, standard structure
        script_style_count = html.lower().count("<script") + html.lower().count(
            "<style"
        )
        total_tags = html.count("<")

        if total_tags == 0:
            return True

        complexity_ratio = script_style_count / total_tags
        return complexity_ratio < 0.1 and len(html) < 100000  # < 100KB

    def _extract_with_trafilatura(self, html: str, url: str) -> ExtractedContent:
        """Primary extraction method using trafilatura."""
        try:
            # Extract main content
            content = trafilatura.extract(
                html,
                config=self.config,
                include_comments=False,
                include_tables=True,
                include_formatting=False,
                url=url,
            )

            if not content:
                raise ValueError("No content extracted by trafilatura")

            # Extract metadata
            metadata_obj = extract_metadata(html, fast=False, url=url)

            # Extract headers for structure
            headers = self._extract_headers_from_html(html)

            # Build metadata dict
            metadata = {
                "extraction_timestamp": datetime.now().isoformat(),
                "domain": urlparse(url).netloc,
                "author": getattr(metadata_obj, "author", None),
                "date": getattr(metadata_obj, "date", None),
                "description": getattr(metadata_obj, "description", None),
                "tags": getattr(metadata_obj, "tags", []),
                "language": getattr(metadata_obj, "language", None),
            }

            title = getattr(
                metadata_obj, "title", None
            ) or self._extract_title_fallback(html)
            return ExtractedContent(
                title=title,
                content=self._clean_text(content),
                url=url,
                headers=headers,
                metadata=metadata,
                extraction_method="trafilatura",
                word_count=len(content.split()),
                language=getattr(metadata_obj, "language", None),
            )

        except Exception as e:
            self.logger.warning(f"Trafilatura extraction failed for {url}: {e}")
            # Fallback to selectolax or BeautifulSoup (they handle title extraction)
            if self.selectolax_available:
                return self._extract_with_selectolax(html, url)
            else:
                return self._extract_with_beautifulsoup(html, url)

    def _extract_with_selectolax(self, html: str, url: str) -> ExtractedContent:
        """Fast extraction using selectolax for simple content."""
        try:
            tree = HTMLParser(html)

            # Remove unwanted elements
            for element in tree.css(
                "script, style, nav, footer, aside, .advertisement"
            ):
                element.decompose()

            # Extract title using the robust fallback logic
            title = self._extract_title_fallback(html)

            # Extract headers
            headers = {"h1": [], "h2": [], "h3": []}
            for level in ["h1", "h2", "h3"]:
                for header in tree.css(level):
                    text = header.text().strip()
                    if text:
                        headers[level].append(text)

            # Extract main content
            # Try common content selectors first
            content_node = (
                tree.css_first("main")
                or tree.css_first("article")
                or tree.css_first(".content")
                or tree.css_first("#content")
                or tree.css_first("body")
            )

            content = (
                content_node.text(separator="\n", strip=True) if content_node else ""
            )

            return ExtractedContent(
                title=title,
                content=self._clean_text(content),
                url=url,
                headers=headers,
                metadata={
                    "extraction_timestamp": datetime.now().isoformat(),
                    "domain": urlparse(url).netloc,
                },
                extraction_method="selectolax",
                word_count=len(content.split()) if content else 0,
            )

        except Exception as e:
            self.logger.warning(f"Selectolax extraction failed for {url}: {e}")
            return self._extract_with_beautifulsoup(html, url)

    def _extract_with_beautifulsoup(self, html: str, url: str) -> ExtractedContent:
        """Fallback extraction using BeautifulSoup."""
        soup = BeautifulSoup(html, "html.parser")

        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "footer", "aside"]):
            element.decompose()

        title = self._extract_title_fallback(html)
        headers = self._extract_headers_bs4(soup)
        content = soup.get_text(separator="\n", strip=True)

        return ExtractedContent(
            title=title,
            content=self._clean_text(content),
            url=url,
            headers=headers,
            metadata={
                "extraction_timestamp": datetime.now().isoformat(),
                "domain": urlparse(url).netloc,
            },
            extraction_method="beautifulsoup",
            word_count=len(content.split()) if content else 0,
        )

    def _extract_headers_from_html(self, html: str) -> Dict[str, List[str]]:
        """Extract headers using BeautifulSoup for structure analysis."""
        soup = BeautifulSoup(html, "html.parser")
        return self._extract_headers_bs4(soup)

    def _extract_headers_bs4(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract h1-h3 headers for content structure."""
        headers = {"h1": [], "h2": [], "h3": []}

        for level in ["h1", "h2", "h3"]:
            for header in soup.find_all(level):
                text = header.get_text().strip()
                if text:
                    headers[level].append(text)

        return headers

    def _extract_title_fallback(self, html: str) -> str:
        """Extract page title using multiple strategies, prioritizing og:title."""
        soup = BeautifulSoup(html, "html.parser")

        # Try meta og:title first (robust extraction)
        og_title = soup.find("meta", attrs={"property": "og:title"})
        if og_title and isinstance(og_title, Tag):
            og_content = og_title.attrs.get("content")
            if isinstance(og_content, str) and og_content.strip():
                return og_content.strip()

        # Try regular title tag
        title_tag = soup.find("title")
        if title_tag and title_tag.get_text():
            return title_tag.get_text().strip()

        # Try first h1
        h1 = soup.find("h1")
        if h1 and h1.get_text():
            return h1.get_text().strip()

        return "Untitled"

    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)

        # Remove common boilerplate patterns
        patterns = [
            r"(?i)(Advertisement|Ad\s+Choice|Sponsored Content|Cookie Notice)",
            r"(?i)(Click here|Read more|Continue reading)",
            r"(?i)(Share on|Follow us|Subscribe)",
        ]

        for pattern in patterns:
            text = re.sub(pattern, "", text)

        return text.strip()
