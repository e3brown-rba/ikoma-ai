#!/usr/bin/env python3
"""
Simple test script for domain filter functionality.
Run with: python3 test_domain_filter_simple.py
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.internet_tools import validate_url_for_access


def test_domain_filter():
    """Test domain filtering functionality."""
    # Test blocked domains
    result = validate_url_for_access.invoke("http://localhost.localdomain/test")
    assert "DENIED" in result or "blocked" in result or "not allowed" in result

    # Test Wikipedia (should be allowed)
    result = validate_url_for_access.invoke(
        "https://en.wikipedia.org/wiki/Python_(programming_language)"
    )
    assert "ALLOWED" in result or "allowed" in result

    # Test GitHub (should be allowed)
    result = validate_url_for_access.invoke("https://github.com/python/cpython")
    assert "ALLOWED" in result or "allowed" in result

    print("✅ Domain filtering works correctly")


if __name__ == "__main__":
    success = test_domain_filter()
    sys.exit(0 if success else 1)
