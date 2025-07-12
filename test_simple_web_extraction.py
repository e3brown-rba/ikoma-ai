"""
Simple Test for Web Content Extraction

Tests the core functionality without requiring external dependencies.
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.content_extractor import ContentQualityScorer, ModernContentExtractor
from tools.web_security import FilterConfig, SecureWebFilter


def test_security_filter():
    """Test security filtering functionality."""
    print("Testing security filter...")

    # Test blocked domains
    filter_config = FilterConfig()
    web_filter = SecureWebFilter(filter_config)

    try:
        web_filter.validate_url("http://localhost.localdomain/test")
        raise AssertionError("localhost should be blocked")
    except ValueError as e:
        assert (
            "blocked" in str(e)
            or "not allowed" in str(e)
            or "Invalid URL format" in str(e)
            or "not in allowlist" in str(e)
        )

    # Test Wikipedia (should be allowed)
    try:
        web_filter.validate_url("https://docs.python.org/3/")
        # Should not raise an exception
    except ValueError as e:
        raise AssertionError(f"docs.python.org should be allowed: {e}") from e

    print("✅ Security filtering works correctly")


def test_content_extractor():
    """Test content extraction functionality."""
    print("Testing content extractor...")

    extractor = ModernContentExtractor(min_quality_score=0.5)

    # Test quality scoring
    scorer = ContentQualityScorer()
    good_text = (
        "Python is a high-level programming language known for its simplicity and readability. "
        "It was created by Guido van Rossum and first released in 1991. Python's design philosophy "
        "emphasizes code readability with its notable use of significant whitespace."
    )

    metrics = scorer.calculate_quality_score(good_text)
    assert "overall" in metrics
    assert metrics["overall"] > 0.5
    print(f"✅ Quality scoring works: overall={metrics['overall']:.2f}")

    # Test text chunking
    text = (
        "This is sentence one. This is sentence two. This is sentence three. "
        "This is sentence four. This is sentence five."
    )

    chunks = extractor._intelligent_chunk_text(text, chunk_size=50)
    assert len(chunks) > 0
    print(f"✅ Text chunking works: {len(chunks)} chunks")

    # Test content extraction
    html_content = """
    <html>
    <head><title>Python Documentation</title></head>
    <body>
        <h1>Python Programming Language</h1>
        <p>Python is a high-level programming language known for its simplicity and readability.</p>
        <p>It was created by Guido van Rossum and first released in 1991.</p>
    </body>
    </html>
    """

    extracted = extractor.extract_content(
        "https://docs.python.org/3/", html_content, 1000
    )
    assert extracted.url == "https://docs.python.org/3/"
    assert "Python" in extracted.title
    assert len(extracted.text_chunks) > 0
    assert extracted.quality_score > 0

    print(
        f"✅ Content extraction works: {len(extracted.text_chunks)} chunks, quality={extracted.quality_score:.2f}"
    )


def test_rate_limiting():
    """Test rate limiting functionality."""
    print("Testing rate limiting...")

    filter_config = FilterConfig(rate_limit_delay=0.1)  # Fast rate limit for testing
    web_filter = SecureWebFilter(filter_config)

    # First request should pass
    web_filter.enforce_rate_limit("example.com")

    # Second request should be rate limited
    import time

    start_time = time.time()
    web_filter.enforce_rate_limit("example.com")
    end_time = time.time()

    # Should have taken at least the rate limit delay
    assert (
        end_time - start_time >= web_filter.config.rate_limit_delay * 0.9
    )  # Allow small timing variance

    print("✅ Rate limiting works correctly")


if __name__ == "__main__":
    print("🧪 Running simple web extraction tests...")

    try:
        test_security_filter()
        print("✅ Security filter test passed")
    except Exception as e:
        print(f"❌ Security filter test failed: {e}")
        sys.exit(1)

    try:
        test_content_extractor()
        print("✅ Content extractor test passed")
    except Exception as e:
        print(f"❌ Content extractor test failed: {e}")
        sys.exit(1)

    try:
        test_rate_limiting()
        print("✅ Rate limiting test passed")
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        sys.exit(1)

    print("\n🎉 All tests passed!")
