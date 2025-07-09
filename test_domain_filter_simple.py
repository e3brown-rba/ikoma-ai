#!/usr/bin/env python3
"""
Simple test script for domain filter functionality.
Run with: python3 test_domain_filter_simple.py
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.domain_filter import DomainFilter, get_domain_filter, is_domain_allowed


def test_domain_filter():
    """Test basic domain filter functionality."""
    print("🧪 Testing Domain Filter Implementation...")

    # Test 1: Basic initialization
    print("\n1. Testing initialization...")
    try:
        filter_instance = DomainFilter()
        print("✅ Domain filter initialized successfully")
        print(f"   Default policy: {filter_instance.default_policy}")
        print(f"   Allow domains loaded: {len(filter_instance.allow_domains)}")
        print(f"   Deny domains loaded: {len(filter_instance.deny_domains)}")
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False

    # Test 2: Domain checking
    print("\n2. Testing domain checking...")
    test_domains = ["wikipedia.org", "github.com", "malware.com", "unknown.com"]

    for domain in test_domains:
        try:
            is_allowed, reason = filter_instance.is_domain_allowed(domain)
            status = "✅ ALLOWED" if is_allowed else "❌ DENIED"
            print(f"   {domain}: {status} - {reason}")
        except Exception as e:
            print(f"   ❌ Error checking {domain}: {e}")

    # Test 3: Wildcard matching
    print("\n3. Testing wildcard matching...")
    wildcard_tests = ["en.wikipedia.org", "fr.wikipedia.org", "www.wikipedia.org"]

    for domain in wildcard_tests:
        try:
            is_allowed, reason = filter_instance.is_domain_allowed(domain)
            status = "✅ ALLOWED" if is_allowed else "❌ DENIED"
            print(f"   {domain}: {status} - {reason}")
        except Exception as e:
            print(f"   ❌ Error checking {domain}: {e}")

    # Test 4: URL validation
    print("\n4. Testing URL validation...")
    from tools.internet_tools import validate_url_for_access

    test_urls = [
        "https://wikipedia.org/page",
        "https://github.com/user/repo",
        "https://malware.com/evil",
        "https://unknown.com/page",
    ]

    for url in test_urls:
        try:
            result = validate_url_for_access(url)
            print(f"   {url}: {result}")
        except Exception as e:
            print(f"   ❌ Error validating {url}: {e}")

    # Test 5: Status reporting
    print("\n5. Testing status reporting...")
    try:
        status = filter_instance.get_status()
        print("   Domain Filter Status:")
        for key, value in status.items():
            print(f"     {key}: {value}")
    except Exception as e:
        print(f"   ❌ Error getting status: {e}")

    # Test 6: Convenience functions
    print("\n6. Testing convenience functions...")
    try:
        result = is_domain_allowed("wikipedia.org")
        print(f"   is_domain_allowed('wikipedia.org'): {result}")

        filter_instance = get_domain_filter()
        print(f"   get_domain_filter(): {type(filter_instance)}")
    except Exception as e:
        print(f"   ❌ Error with convenience functions: {e}")

    print("\n🎉 Domain filter tests completed!")
    return True


if __name__ == "__main__":
    success = test_domain_filter()
    sys.exit(0 if success else 1)
