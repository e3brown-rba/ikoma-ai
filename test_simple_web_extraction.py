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
    """Test the security filter functionality."""
    print("Testing security filter...")

    # Test blocked domains
    filter_config = FilterConfig()
    web_filter = SecureWebFilter(filter_config)

    # Test localhost (should be blocked)
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
        web_filter.validate_url("https://en.wikipedia.org/wiki/Python")
        print("✅ Security filter allows Wikipedia")
    except ValueError as e:
        print(f"❌ Security filter blocked Wikipedia: {e}")
        return False

    print("✅ Security filter tests passed")
    return True


def test_content_extractor():
    """Test the content extractor functionality."""
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
    assert "readability" in metrics
    assert "length" in metrics
    assert "vocabulary" in metrics
    assert "structure" in metrics
    assert 0 <= metrics["overall"] <= 1

    print(f"✅ Quality scoring works: overall={metrics['overall']:.2f}")

    # Test text chunking
    text = (
        "This is sentence one. This is sentence two. This is sentence three. "
        "This is sentence four. This is sentence five."
    )

    chunks = extractor._intelligent_chunk_text(text, chunk_size=50)
    assert len(chunks) > 0
    for chunk in chunks:
        assert len(chunk) <= 50

    print(f"✅ Text chunking works: {len(chunks)} chunks created")

    # Test content extraction
    html_content = """
    <html>
    <body>
        <h1>Python Programming Guide</h1>
        <p>Python is a high-level programming language known for its simplicity and readability.
        It was created by Guido van Rossum and first released in 1991. Python's design philosophy
        emphasizes code readability with its notable use of significant whitespace.</p>
        <p>Python features a dynamic type system and automatic memory management. It supports multiple
        programming paradigms, including structured, object-oriented, and functional programming.</p>
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

    return True


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
    assert end_time - start_time >= 0.1

    print("✅ Rate limiting works")
    return True


if __name__ == "__main__":
    print("🧪 Running simple web extraction tests...")

    success = True

    try:
        success &= test_security_filter()
    except Exception as e:
        print(f"❌ Security filter test failed: {e}")
        success = False

    try:
        success &= test_content_extractor()
    except Exception as e:
        print(f"❌ Content extractor test failed: {e}")
        success = False

    try:
        success &= test_rate_limiting()
    except Exception as e:
        print(f"❌ Rate limiting test failed: {e}")
        success = False

    if success:
        print("\n🎉 All tests passed!")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)
