#!/usr/bin/env python3
"""
Test dashboard citation caching functionality.
"""

import time

import requests

from tools.citation_manager import ProductionCitationManager


def add_sample_citations() -> ProductionCitationManager:
    """Add some sample citations for testing."""
    citation_mgr = ProductionCitationManager()

    # Add sample citations
    citation_mgr.add_citation(
        url="https://example.com/article1",
        title="Sample Article 1",
        content_preview="This is a sample article for testing...",
        domain="example.com",
    )

    citation_mgr.add_citation(
        url="https://example.com/article2",
        title="Sample Article 2",
        content_preview="Another sample article for testing...",
        domain="example.com",
    )

    citation_mgr.add_citation(
        url="https://example.com/article3",
        title="Sample Article 3",
        content_preview="Third sample article for testing...",
        domain="example.com",
    )

    print(f"✅ Added {len(citation_mgr.get_all_citations())} sample citations")
    return citation_mgr


def test_dashboard_caching() -> None:
    """Test the dashboard caching functionality."""
    print("🧪 Testing Dashboard Citation Caching")
    print("=" * 50)

    # Add sample citations
    add_sample_citations()

    # Test endpoint
    base_url = "http://localhost:8000"
    conversation_id = "test-conversation"

    print(f"\n📊 Testing endpoint: {base_url}/citations/{conversation_id}")

    try:
        # First request (should be slow, no cache)
        print("\n1️⃣ First request (no cache)...")
        start_time = time.time()
        response1 = requests.get(f"{base_url}/citations/{conversation_id}")
        time1 = time.time() - start_time
        print(f"   Response time: {time1:.4f} seconds")
        print(f"   Status: {response1.status_code}")

        # Second request (should be fast, from cache)
        print("\n2️⃣ Second request (from cache)...")
        start_time = time.time()
        response2 = requests.get(f"{base_url}/citations/{conversation_id}")
        time2 = time.time() - start_time
        print(f"   Response time: {time2:.4f} seconds")
        print(f"   Status: {response2.status_code}")

        # Third request (should be fast, from cache)
        print("\n3️⃣ Third request (from cache)...")
        start_time = time.time()
        response3 = requests.get(f"{base_url}/citations/{conversation_id}")
        time3 = time.time() - start_time
        print(f"   Response time: {time3:.4f} seconds")
        print(f"   Status: {response3.status_code}")

        # Test different conversation ID
        print("\n4️⃣ Different conversation ID (new cache entry)...")
        start_time = time.time()
        response4 = requests.get(f"{base_url}/citations/another-conversation")
        time4 = time.time() - start_time
        print(f"   Response time: {time4:.4f} seconds")
        print(f"   Status: {response4.status_code}")

        # Analysis
        print("\n📈 Performance Analysis:")
        print(f"   First request: {time1:.4f}s (computation)")
        print(f"   Cached requests: {time2:.4f}s, {time3:.4f}s (cache)")
        print(f"   New conversation: {time4:.4f}s (computation)")

        if time2 < time1 * 0.5:  # Cache should be at least 50% faster
            print("   ✅ Caching is working!")
        else:
            print("   ⚠️  Caching may not be working as expected")

        # Show sample response content
        print("\n📄 Sample response content (first 200 chars):")
        print(f"   {response1.text[:200]}...")

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to dashboard server.")
        print(
            "   Make sure the server is running: uvicorn dashboard.app:app --reload --port 8000"
        )
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    test_dashboard_caching()
