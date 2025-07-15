#!/usr/bin/env python3
"""
Test that web extraction registers a citation and stores it in ChromaDB.
"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.vector_store import get_citation_metadata
from tools.web_tools import extract_web_content


# We'll patch requests.get to return a local HTML string
class MockResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code
        self.headers = {"content-length": str(len(text))}

    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception("HTTP error")


MOCK_HTML = """
<html><head><title>Test Page</title></head><body><h1>Hello World</h1><p>This is a test page for extraction.</p></body></html>
"""


@patch("tools.web_tools.validate_web_url", lambda url: None)
@patch("tools.web_tools.requests.get", return_value=MockResponse(MOCK_HTML))
def test_web_extraction_registers_citation(mock_get):
    print("🧪 Testing web extraction citation registration...")
    os.environ["OPENAI_API_KEY"] = "sk-dummy"
    # Use a fake URL and options
    url = "https://example.com/test"
    options = f"{url}|||1000|||true|||0.0"  # chunk_size, store_in_memory, min_quality
    result = extract_web_content(options)
    print("Extraction result:\n", result)
    # Parse citation ID from result
    import re

    match = re.search(r"\[\[(\d+)\]\]", result)
    assert match, "No citation ID found in extraction result."
    citation_id = int(match.group(1))
    print(f"Found citation ID: {citation_id}")
    # Retrieve citation metadata
    metadata = get_citation_metadata(citation_id)
    assert metadata is not None, "Citation metadata not found in ChromaDB."
    print("✅ Citation metadata found:", metadata)
    assert metadata["url"] == url, "Citation URL mismatch."
    title = str(metadata["title"])
    # The title should be either extracted from HTML or fallback to URL
    # In CI environment, trafilatura metadata extraction might fail
    assert (
        "Hello World" in title 
        or "Test Page" in title 
        or title == url
    ), f"Citation title should contain extracted content or be URL: {title}"
    print("🎉 Web extraction citation registration test passed!")


if __name__ == "__main__":
    test_web_extraction_registers_citation()
