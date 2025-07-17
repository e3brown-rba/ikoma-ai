#!/usr/bin/env python3
"""
Demo script for SerpAPI search integration.

This script demonstrates the web search functionality and helps verify
that the SerpAPI integration is working correctly.
"""

import importlib.util
import os
import sys

from dotenv import load_dotenv


def main():
    """Main demo function."""
    print("🔍 iKOMA SerpAPI Search Demo")
    print("=" * 50)

    # Load environment variables
    load_dotenv()

    # Check configuration
    api_key = os.getenv("SERPAPI_API_KEY")
    search_enabled = os.getenv("SEARCH_ENABLED", "false").lower() == "true"

    print("Configuration:")
    print(f"- API Key configured: {'Yes' if api_key else 'No'}")
    print(f"- Search enabled: {'Yes' if search_enabled else 'No'}")
    print(f"- Rate limit: {os.getenv('SEARCH_RATE_LIMIT', '5')} req/s")
    print()

    if not api_key:
        print("❌ SerpAPI key not found. Set SERPAPI_API_KEY in .env file")
        print("   Get your free key at: https://serpapi.com/")
        return 1

    if not search_enabled:
        print("❌ Search is disabled. Set SEARCH_ENABLED=true in .env file")
        return 1

    # Test SerpAPI availability
    if importlib.util.find_spec("serpapi") is not None:
        print("✅ SerpAPI client available")
    else:
        print("❌ SerpAPI client not installed. Run: pip install google-search-results")
        return 1

    # Import and test our search tool
    try:
        from tools.web_tools import get_search_status, search_web

        print("✅ Web search tools loaded")
    except ImportError as e:
        print(f"❌ Error loading web tools: {e}")
        return 1

    # Test search status
    print("\n📊 Search Status:")
    status = get_search_status.invoke("")
    print(status)

    # Test search functionality
    test_queries = [
        "latest AI news 2025",
        "Python langchain tutorial",
        "local AI assistant projects",
    ]

    print("\n🔎 Testing search functionality:")
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Searching: '{query}'")
        try:
            result = search_web.invoke(query)
            print("Result:")
            print(result[:500] + "..." if len(result) > 500 else result)
        except Exception as e:
            print(f"❌ Search failed: {e}")

        print("-" * 50)

    print("\n✅ Demo completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
