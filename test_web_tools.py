"""
Tests for web search tools.

Tests the SerpAPI integration with proper mocking to avoid
external dependencies during testing.
"""

import sys
import time
from unittest.mock import MagicMock, patch

import pytest

from tools.web_tools import SearchRateLimiter, get_search_status, search_web


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


def test_get_search_status():
    """Test the search status tool."""
    with patch.dict(
        "os.environ",
        {
            "SEARCH_ENABLED": "true",
            "SERPAPI_API_KEY": "test_key",
            "SEARCH_RATE_LIMIT": "3",
        },
    ):
        with patch.dict(sys.modules, {"serpapi": MagicMock()}):
            result = get_search_status.invoke("")

            assert "Search enabled: True" in result
            assert "API key configured: True" in result
            assert "Rate limit: 3" in result
            assert "SerpAPI available: True" in result


def test_get_search_status_disabled():
    """Test search status when search is disabled."""
    with patch.dict(
        "os.environ",
        {"SEARCH_ENABLED": "false", "SERPAPI_API_KEY": "", "SEARCH_RATE_LIMIT": "5"},
    ):
        result = get_search_status.invoke("")

        assert "Search enabled: False" in result
        assert "API key configured: False" in result
        assert "Rate limit: 5" in result


def test_rate_limiter():
    """Test the rate limiter functionality."""
    limiter = SearchRateLimiter(max_requests_per_second=2)

    start_time = time.time()
    limiter.wait_if_needed()
    limiter.wait_if_needed()
    elapsed = time.time() - start_time

    # Should wait at least 0.5s for 2 RPS (1/2 second interval)
    assert elapsed >= 0.4  # Allow some tolerance for timing


def test_rate_limiter_no_wait():
    """Test that rate limiter doesn't wait unnecessarily."""
    limiter = SearchRateLimiter(max_requests_per_second=10)

    start_time = time.time()
    limiter.wait_if_needed()
    elapsed = time.time() - start_time

    # Should not wait significantly for high rate limits
    assert elapsed < 0.1


if __name__ == "__main__":
    pytest.main([__file__])
