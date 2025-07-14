#!/usr/bin/env python3
"""
Integration test for citation storage and retrieval in ChromaDB.
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.citation_manager import CitationSource
from tools.vector_store import get_citation_metadata, store_citation_with_metadata


def test_citation_storage_and_retrieval():
    print("🧪 Testing citation storage and retrieval in ChromaDB...")
    # Create a test citation source
    citation = CitationSource(
        id=123,
        url="https://example.com/test-citation",
        title="Test Citation Title",
        timestamp=datetime.now().isoformat(),
        domain="example.com",
        confidence_score=0.99,
        content_preview="This is a preview of the citation content.",
        source_type="web",
    )
    content = "This is the full content of the citation for embedding and retrieval."

    # Store the citation
    store_citation_with_metadata(citation, content)
    print("✅ Citation stored.")

    # Retrieve the citation metadata
    metadata = get_citation_metadata(123)
    assert metadata is not None, "Failed to retrieve citation metadata."
    print("✅ Citation metadata retrieved.")

    # Check that metadata matches what was stored
    assert metadata["url"] == citation.url, "URL mismatch."
    assert metadata["title"] == citation.title, "Title mismatch."
    assert metadata["domain"] == citation.domain, "Domain mismatch."
    assert metadata["confidence_score"] == citation.confidence_score, "Confidence score mismatch."
    assert metadata["source_type"] == citation.source_type, "Source type mismatch."
    assert metadata["content_preview"] == citation.content_preview, "Content preview mismatch."
    print("✅ Metadata fields match.")

    print("\n🎉 Citation ChromaDB integration test passed!")

if __name__ == "__main__":
    test_citation_storage_and_retrieval()
