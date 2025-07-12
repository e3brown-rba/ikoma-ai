"""
Tests for web search tools.

Tests the SerpAPI integration with proper mocking to avoid
external dependencies during testing.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tools.web_tools import search_web


def test_search_web_disabled():
    """Test that search is disabled when SEARCH_ENABLED=false."""
    with patch.dict("os.environ", {"SEARCH_ENABLED": "false"}):
        result = search_web.invoke("test query")
        assert "Web search is disabled" in result


def test_search_web_no_api_key():
    """Test that search fails when no API key is configured."""
    with patch.dict("os.environ", {"SEARCH_ENABLED": "true", "SERPAPI_API_KEY": ""}):
        result = search_web.invoke("test query")
        assert "SerpAPI key not configured" in result


def test_search_web_serpapi_not_installed():
    """Test that search fails gracefully when SerpAPI is not installed."""
    with patch.dict(
        "os.environ", {"SEARCH_ENABLED": "true", "SERPAPI_API_KEY": "test_key"}
    ):
        with patch.dict(sys.modules, {"serpapi": None}):
            result = search_web.invoke("test query")
            assert "SerpAPI client not installed" in result


def test_search_web_success():
    """Test successful search with mocked SerpAPI response."""
    mock_results = {
        "organic_results": [
            {
                "title": "Test Result 1",
                "link": "https://example.com/1",
                "snippet": "This is a test snippet",
                "displayed_link": "example.com",
            },
            {
                "title": "Test Result 2",
                "link": "https://example.com/2",
                "snippet": "Another test snippet",
                "displayed_link": "example.com",
            },
        ]
    }

    with patch.dict(
        "os.environ", {"SEARCH_ENABLED": "true", "SERPAPI_API_KEY": "test_key"}
    ):
        mock_serpapi = MagicMock()
        mock_search_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.get_dict.return_value = mock_results
        mock_search_class.return_value = mock_instance
        mock_serpapi.GoogleSearch = mock_search_class

        with patch.dict(sys.modules, {"serpapi": mock_serpapi}):
            result = search_web.invoke("test query")

            # Verify the result contains expected data
            assert "Test Result 1" in result
            assert "https://example.com/1" in result
            assert "test query" in result
            assert "timestamp" in result


def test_search_web_no_results():
    """Test search when no results are returned."""
    mock_results = {"organic_results": []}

    with patch.dict(
        "os.environ", {"SEARCH_ENABLED": "true", "SERPAPI_API_KEY": "test_key"}
    ):
        mock_serpapi = MagicMock()
        mock_search_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.get_dict.return_value = mock_results
        mock_search_class.return_value = mock_instance
        mock_serpapi.GoogleSearch = mock_search_class

        with patch.dict(sys.modules, {"serpapi": mock_serpapi}):
            result = search_web.invoke("test query")
            assert "No search results found" in result


def test_search_web_exception():
    """Test that search handles exceptions gracefully."""
    with patch.dict(
        "os.environ", {"SEARCH_ENABLED": "true", "SERPAPI_API_KEY": "test_key"}
    ):
        mock_serpapi = MagicMock()
        mock_search_class = MagicMock(side_effect=Exception("API Error"))
        mock_serpapi.GoogleSearch = mock_search_class

        with patch.dict(sys.modules, {"serpapi": mock_serpapi}):
            result = search_web.invoke("test query")
            assert "Search failed" in result


if __name__ == "__main__":
    pytest.main([__file__])
