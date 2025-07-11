"""
Web Search Tools Module for iKOMA

Provides web search capabilities using SerpAPI with rate limiting and safety controls.
Part of Epic E-01: Internet Tooling - Issue #2.
"""

import json
import os
import time
from datetime import datetime
from typing import Any

from langchain.tools import tool


class SearchRateLimiter:
    """Rate limiter for SerpAPI requests to prevent API quota exhaustion."""

    def __init__(self, max_requests_per_second: int = 5):
        self.max_rps = max_requests_per_second
        self.last_request_time = 0.0
        self.request_interval = 1.0 / max_requests_per_second

    def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_interval:
            time.sleep(self.request_interval - time_since_last)
        self.last_request_time = time.time()


# Global rate limiter instance
_rate_limiter = SearchRateLimiter(int(os.getenv("SEARCH_RATE_LIMIT", "5")))


@tool
def search_web(query: str) -> str:
    """
    Search the web using SerpAPI and return top-5 results with titles and URLs.

    Args:
        query: Search query string

    Returns:
        JSON string with search results including titles, URLs, and snippets
    """
    # Check if search is enabled
    if not os.getenv("SEARCH_ENABLED", "false").lower() == "true":
        return (
            "Web search is disabled. Enable with SEARCH_ENABLED=true in your .env file."
        )

    # Check for API key
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return "SerpAPI key not configured. Set SERPAPI_API_KEY in your .env file."

    try:
        # Import SerpAPI client (lazy import to avoid dependency issues)
        try:
            from serpapi import GoogleSearch
        except ImportError:
            return (
                "SerpAPI client not installed. Run: pip install google-search-results"
            )

        # Rate limiting
        _rate_limiter.wait_if_needed()

        # Perform search with safety settings
        search = GoogleSearch(
            {
                "q": query,
                "api_key": api_key,
                "num": 5,  # Top 5 results
                "safe": "active",  # Safe search enabled
                "gl": "us",  # Geographic location (can be made configurable)
                "hl": "en",  # Language (can be made configurable)
            }
        )

        results = search.get_dict()

        # Extract organic results
        organic_results = results.get("organic_results", [])

        if not organic_results:
            return f"No search results found for query: '{query}'"

        # Format results for easy consumption
        formatted_results: dict[str, Any] = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "total_results": len(organic_results),
            "results": [],
        }

        for i, result in enumerate(organic_results[:5], 1):
            formatted_results["results"].append(
                {
                    "rank": i,
                    "title": result.get("title", ""),
                    "url": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "displayed_link": result.get("displayed_link", ""),
                }
            )

        # Return formatted JSON string
        return json.dumps(formatted_results, indent=2)

    except Exception as e:
        return f"Search failed: {str(e)}"


@tool
def get_search_status() -> str:
    """
    Get the current status of web search functionality.

    Returns:
        String with search configuration and status information
    """
    status = {
        "search_enabled": os.getenv("SEARCH_ENABLED", "false").lower() == "true",
        "api_key_configured": bool(os.getenv("SERPAPI_API_KEY")),
        "rate_limit": int(os.getenv("SEARCH_RATE_LIMIT", "5")),
        "serpapi_available": False,
    }

    # Check if SerpAPI is available
    try:
        __import__("serpapi")
        status["serpapi_available"] = True
    except ImportError:
        pass

    result = "Web Search Status:\n"
    result += f"- Search enabled: {status['search_enabled']}\n"
    result += f"- API key configured: {status['api_key_configured']}\n"
    result += f"- Rate limit: {status['rate_limit']} req/s\n"
    result += f"- SerpAPI available: {status['serpapi_available']}\n"

    if not status["search_enabled"]:
        result += "\nTo enable search, set SEARCH_ENABLED=true in your .env file"
    if not status["api_key_configured"]:
        result += "\nTo configure API key, set SERPAPI_API_KEY in your .env file"
    if not status["serpapi_available"]:
        result += "\nTo install SerpAPI, run: pip install google-search-results"

    return result
