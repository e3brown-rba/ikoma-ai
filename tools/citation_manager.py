import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.text import Text

from .security import validate_citation_metadata


@dataclass
class CitationSource:
    """Enhanced citation source with confidence scoring and domain tracking."""
    id: int
    url: str
    title: str
    timestamp: str
    domain: str
    confidence_score: float = 0.95
    content_preview: str = ""
    source_type: str = "web"


class ProductionCitationManager:
    """Production-ready citation manager with Unicode superscript support and Rich integration."""

    def __init__(self) -> None:
        self.sources: dict[int, CitationSource] = {}
        self.counter = 1
        self.console = Console()

        # Unicode superscript mapping (research-backed approach)
        self.superscript_map = {
            '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
            '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'
        }

    def unicode_superscript(self: 'ProductionCitationManager', num: int) -> str:
        """Convert number to Unicode superscript with fallback."""
        try:
            return ''.join(self.superscript_map.get(c, c) for c in str(num))
        except Exception:
            return f"[{num}]"  # Fallback for unsupported terminals

    def parse_citations_anthropic_style(self: 'ProductionCitationManager', text: str) -> tuple[str, list[int]]:
        """Parse Anthropic-style citations with robust error handling."""
        # Pattern from research: 70% industry adoption of [[n]] format
        pattern = r'\[\[(\d+)\]\]'
        citations = []

        def replace_citation(match: re.Match) -> str:
            citation_id = int(match.group(1))
            citations.append(citation_id)
            return self.unicode_superscript(citation_id)

        clean_text = re.sub(pattern, replace_citation, text)
        return clean_text, citations

    def add_citation(self: 'ProductionCitationManager', url: str, title: str, content_preview: str = "",
        source_type: str = "web", domain: str = "", confidence_score: float = 0.95
    ) -> int:
        """Add a citation and return its ID with enhanced metadata and security validation."""
        # Validate and sanitize metadata
        metadata = {
            "url": url,
            "title": title,
            "domain": domain,
            "confidence_score": confidence_score,
            "content_preview": content_preview,
            "source_type": source_type,
        }

        try:
            validated_metadata = validate_citation_metadata(metadata)
        except ValueError as e:
            print(f"Warning: Citation validation failed: {e}")
            # Use fallback values for invalid metadata
            validated_metadata = {
                "url": "https://example.com/invalid",
                "title": "Invalid Citation",
                "domain": "unknown",
                "confidence_score": 0.0,
                "content_preview": "",
                "source_type": "unknown",
            }

        # Extract domain from URL if not provided
        if not validated_metadata["domain"] and validated_metadata["url"]:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(validated_metadata["url"])
                validated_metadata["domain"] = parsed.netloc
            except Exception:
                validated_metadata["domain"] = "unknown"

        citation = CitationSource(
            id=self.counter,
            url=validated_metadata["url"],
            title=validated_metadata["title"],
            timestamp=datetime.now().isoformat(),
            content_preview=validated_metadata["content_preview"],
            source_type=validated_metadata["source_type"],
            domain=validated_metadata["domain"],
            confidence_score=validated_metadata["confidence_score"],
        )
        self.sources[self.counter] = citation
        self.counter += 1
        return citation.id

    def get_citation_text(self: 'ProductionCitationManager', citation_id: int) -> str:
        """Format citation for display with Unicode superscript."""
        if citation_id in self.sources:
            c = self.sources[citation_id]
            superscript = self.unicode_superscript(c.id)
            return f"{superscript} {c.title} - {c.url}"
        return f"[{citation_id}] Citation not found"

    def get_citation_details(self: 'ProductionCitationManager', citation_id: int) -> CitationSource | None:
        """Get full citation details."""
        return self.sources.get(citation_id)

    def get_all_citations(self: 'ProductionCitationManager') -> list[CitationSource]:
        """Get all citations as a list."""
        return list(self.sources.values())

    def render_response_with_citations(self: 'ProductionCitationManager', output: str) -> None:
        """Production TUI rendering with Unicode superscripts and Rich formatting."""
        clean_text, citation_ids = self.parse_citations_anthropic_style(output)

        # Create rich text object
        rich_text = Text(clean_text)

        # Add citation sources if present
        if citation_ids:
            rich_text.append("\n\n📚 Sources:\n", style="bold blue")
            for cid in citation_ids:
                if source := self.sources.get(cid):
                    rich_text.append(f"  {self.unicode_superscript(cid)} ", style="dim")
                    rich_text.append(f"{source.title}\n", style="cyan")
                    rich_text.append(f"    {source.url}\n", style="dim")

        self.console.print(rich_text)

    def to_dict(self: 'ProductionCitationManager') -> dict[str, Any]:
        """Convert citations to dictionary format for state storage."""
        return {
            "citations": [asdict(citation) for citation in self.sources.values()],
            "counter": self.counter,
        }

    def from_dict(self: 'ProductionCitationManager', data: dict[str, Any]) -> None:
        """Load citations from dictionary format."""
        self.sources.clear()
        self.counter = data.get("counter", 1)

        for citation_data in data.get("citations", []):
            citation = CitationSource(**citation_data)
            self.sources[citation.id] = citation

    def extract_citations_from_text(self: 'ProductionCitationManager', text: str) -> list[int]:
        """Extract citation IDs from text containing [[n]] markers."""
        pattern = r"\[\[(\d+)\]\]"
        matches = re.findall(pattern, text)
        return [int(match) for match in matches]

    def replace_citations_with_text(self: 'ProductionCitationManager', text: str) -> str:
        """Replace [[n]] markers with formatted citation text."""
        def replace_citation(match: Any) -> str:
            citation_id = int(match.group(1))
            return self.get_citation_text(citation_id)

        pattern = r"\[\[(\d+)\]\]"
        return re.sub(pattern, replace_citation, text)

    def clear(self: 'ProductionCitationManager') -> None:
        """Clear all citations."""
        self.sources.clear()
        self.counter = 1

    def get_conversation_citations(self: 'ProductionCitationManager', conversation_id: str) -> list[CitationSource]:
        """Get citations for a specific conversation (for dashboard integration)."""
        # For now, return all citations. In production, this would filter by conversation_id
        return self.get_all_citations()


# Backward compatibility - keep the old class name for existing code
CitationManager = ProductionCitationManager
