from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass
class Citation:
    """Represents a single citation with source information."""

    id: int
    url: str
    title: str
    timestamp: str
    content_preview: str
    source_type: str = "web"  # web, memory, file, etc.


class CitationManager:
    """Manages citations and their formatting for the agent system."""

    def __init__(self) -> None:
        self.citations: dict[int, Citation] = {}
        self.counter = 1

    def add_citation(
        self, url: str, title: str, content_preview: str = "", source_type: str = "web"
    ) -> int:
        """Add a citation and return its ID."""
        citation = Citation(
            id=self.counter,
            url=url,
            title=title,
            timestamp=datetime.now().isoformat(),
            content_preview=content_preview[:200],
            source_type=source_type,
        )
        self.citations[self.counter] = citation
        self.counter += 1
        return citation.id

    def get_citation_text(self, citation_id: int) -> str:
        """Format citation for display."""
        if citation_id in self.citations:
            c = self.citations[citation_id]
            return f"[{c.id}] {c.title} - {c.url} (accessed {c.timestamp})"
        return f"[{citation_id}] Citation not found"

    def get_citation_details(self, citation_id: int) -> Citation | None:
        """Get full citation details."""
        return self.citations.get(citation_id)

    def get_all_citations(self) -> list[Citation]:
        """Get all citations as a list."""
        return list(self.citations.values())

    def to_dict(self) -> dict[str, Any]:
        """Convert citations to dictionary format for state storage."""
        return {
            "citations": [asdict(citation) for citation in self.citations.values()],
            "counter": self.counter,
        }

    def from_dict(self, data: dict[str, Any]) -> None:
        """Load citations from dictionary format."""
        self.citations.clear()
        self.counter = data.get("counter", 1)

        for citation_data in data.get("citations", []):
            citation = Citation(**citation_data)
            self.citations[citation.id] = citation

    def extract_citations_from_text(self, text: str) -> list[int]:
        """Extract citation IDs from text containing [[n]] markers."""
        import re

        pattern = r"\[\[(\d+)\]\]"
        matches = re.findall(pattern, text)
        return [int(match) for match in matches]

    def replace_citations_with_text(self, text: str) -> str:
        """Replace [[n]] markers with formatted citation text."""
        import re

        def replace_citation(match: Any) -> str:
            citation_id = int(match.group(1))
            return self.get_citation_text(citation_id)

        pattern = r"\[\[(\d+)\]\]"
        return re.sub(pattern, replace_citation, text)

    def clear(self) -> None:
        """Clear all citations."""
        self.citations.clear()
        self.counter = 1
