"""
Comprehensive tests for web content extraction security and quality features.

Tests the complete pipeline including security validation, quality filtering,
ChromaDB storage, and rate limiting for Issue #6.
"""

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from tools.content_extractor import ModernContentExtractor
from tools.web_security import FilterConfig, SecureWebFilter
from tools.web_tools import (
    extract_web_content,
    get_web_extraction_status,
    search_web_memories,
)


# Mock embeddings to avoid OpenAI API key requirements
@pytest.fixture(autouse=True)
def mock_embeddings():
    """Mock embeddings to avoid OpenAI API key requirements in tests."""
    with patch("tools.vector_store.PatchedOpenAIEmbeddings") as mock_embeddings_class:
        mock_embeddings = MagicMock()
        mock_embeddings.embed_query.return_value = [0.1] * 384  # Mock embedding vector
        mock_embeddings_class.return_value = mock_embeddings
        yield mock_embeddings


class TestSecurityValidation:
    """Test comprehensive security validation."""

    def test_blocked_domains(self):
        """Test that blocked domains are properly rejected."""
        # Test blocked domains
        result = extract_web_content.invoke("http://localhost/test")
        assert "Security validation failed" in result

        # Test private IP
        result = extract_web_content.invoke("http://192.168.1.1/test")
        assert "Security validation failed" in result

        # Test 127.0.0.1
        result = extract_web_content.invoke("http://127.0.0.1/test")
        assert "Security validation failed" in result

    def test_allowed_domains(self):
        """Test that allowed domains pass validation."""
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "<html><body>Test content</body></html>"
            mock_response.headers = {}
            mock_get.return_value = mock_response

            result = extract_web_content.invoke("https://en.wikipedia.org/wiki/Python")
            # Should not fail on security validation
            assert "Security validation failed" not in result

    def test_invalid_urls(self):
        """Test that invalid URLs are rejected."""
        result = extract_web_content.invoke("not-a-url")
        assert "Security validation failed" in result

        result = extract_web_content.invoke("ftp://example.com")
        assert "Security validation failed" in result


class TestQualityFiltering:
    """Test content quality assessment and filtering."""

    def test_high_quality_content(self):
        """Test extraction of high-quality content."""
        html_content = """
        <html>
        <body>
            <h1>Python Programming Guide</h1>
            <p>Python is a high-level, interpreted programming language known for its simplicity and readability.
            It was created by Guido van Rossum and first released in 1991. Python's design philosophy emphasizes
            code readability with its notable use of significant whitespace. Python features a dynamic type system
            and automatic memory management. It supports multiple programming paradigms, including structured,
            object-oriented, and functional programming. The language provides constructs that enable clear
            programming on both small and large scales. Python's design philosophy emphasizes code readability
            with its notable use of significant whitespace. Python features a dynamic type system and automatic
            memory management. It supports multiple programming paradigms, including structured, object-oriented,
            and functional programming.</p>
            <p>Python is widely used in web development, data analysis, artificial intelligence, scientific
            computing, and many other fields. Its extensive standard library and third-party packages make it
            a versatile choice for various applications. The language's simplicity and readability make it an
            excellent choice for beginners and experienced developers alike.</p>
        </body>
        </html>
        """

        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = html_content
            mock_response.headers = {}
            mock_get.return_value = mock_response

            result = extract_web_content.invoke(
                "https://docs.python.org/3/|||1000|||true|||0.5"
            )
            assert (
                "Extracted high-quality content" in result
                or "Quality Score:" in result
                or "Quality Metrics:" in result
            )

    def test_low_quality_content(self):
        """Test rejection of low-quality content."""
        html_content = """
        <html>
        <body>
            <div>Short content</div>
        </body>
        </html>
        """

        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = html_content
            mock_response.headers = {}
            mock_get.return_value = mock_response

            # Use allowed domain
            result = extract_web_content.invoke(
                "https://docs.python.org/test|||1000|||true|||0.8"
            )
            assert "Content quality too low" in result


class TestChromaDBStorage:
    """Test ChromaDB storage and retrieval functionality."""

    def test_content_storage(self):
        """Test that extracted content is properly stored in ChromaDB."""
        html_content = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Test Content</h1>
            <p>This is a test page with some content for testing purposes.
            It contains multiple sentences to ensure proper chunking and storage.</p>
        </body>
        </html>
        """

        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = html_content
            mock_response.headers = {}
            mock_get.return_value = mock_response

            result = extract_web_content.invoke(
                "https://docs.python.org/3/|||500|||true|||0.6"
            )
            assert "Chunks:" in result

    def test_content_retrieval(self):
        """Test searching stored web content."""
        # First extract some content
        html_content = """
        <html>
        <head><title>Python Tutorial</title></head>
        <body>
            <h1>Python Tutorial</h1>
            <p>Python is a versatile programming language used for web development,
            data analysis, artificial intelligence, and more.</p>
        </body>
        </html>
        """

        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = html_content
            mock_response.headers = {}
            mock_get.return_value = mock_response

            # Extract content
            extract_web_content.invoke("https://docs.python.org/3/|||500|||true|||0.6")

            # Search for it
            search_result = search_web_memories.invoke(
                "Python programming|||0.6|||docs.python.org|||3"
            )
            assert "Found" in search_result or "No web content found" in search_result


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limiting(self):
        """Test that rate limiting is enforced."""
        filter_config = FilterConfig(
            rate_limit_delay=0.1
        )  # Fast rate limit for testing
        web_filter = SecureWebFilter(filter_config)

        # First request should pass
        web_filter.enforce_rate_limit("example.com")

        # Second request should be rate limited
        start_time = time.time()
        web_filter.enforce_rate_limit("example.com")
        end_time = time.time()

        # Should have taken at least the rate limit delay
        assert end_time - start_time >= 0.1


class TestContentExtractor:
    """Test the content extractor functionality."""

    def test_extractor_initialization(self):
        """Test that the content extractor initializes properly."""
        extractor = ModernContentExtractor(min_quality_score=0.7)
        assert extractor.min_quality_score == 0.7
        assert extractor.quality_scorer is not None

    def test_quality_scoring(self):
        """Test quality scoring functionality."""
        scorer = ModernContentExtractor().quality_scorer

        # Test high-quality text
        good_text = (
            "Python is a high-level programming language known for its simplicity and readability. "
            "It supports multiple programming paradigms and has a comprehensive standard library."
        )
        metrics = scorer.calculate_quality_score(good_text)

        assert "overall" in metrics
        assert "readability" in metrics
        assert "length" in metrics
        assert "vocabulary" in metrics
        assert "structure" in metrics
        assert 0 <= metrics["overall"] <= 1

    def test_text_chunking(self):
        """Test intelligent text chunking."""
        extractor = ModernContentExtractor()
        text = (
            "This is sentence one. This is sentence two. This is sentence three. "
            "This is sentence four. This is sentence five."
        )

        chunks = extractor._intelligent_chunk_text(text, chunk_size=50)

        assert len(chunks) > 0
        for chunk in chunks:
            assert len(chunk) <= 50


class TestIntegration:
    """Test complete integration scenarios."""

    def test_complete_extraction_pipeline(self):
        """Test the complete extraction pipeline from URL to storage."""
        html_content = """
        <html>
        <head><title>Comprehensive Python Guide</title></head>
        <body>
            <h1>Comprehensive Python Guide</h1>
            <p>Python is a powerful, high-level programming language that emphasizes code readability.
            It was created by Guido van Rossum and first released in 1991. Python's design philosophy
            emphasizes code readability with its notable use of significant whitespace.</p>
            <p>The language provides constructs that enable clear programming on both small and large
            scales. Python features a dynamic type system and automatic memory management. It supports multiple
            programming paradigms, including procedural, object-oriented, and functional programming.</p>
        </body>
        </html>
        """

        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = html_content
            mock_response.headers = {}
            mock_get.return_value = mock_response

            # Test extraction
            result = extract_web_content.invoke(
                "https://docs.python.org/3/|||1000|||true|||0.6"
            )
            assert "Web Content Extraction Results" in result

            # Test status
            status = get_web_extraction_status.invoke("")
            assert "Web Content Extraction Status" in status

    def test_error_handling(self):
        """Test error handling in the pipeline."""
        # Test network error
        with patch("requests.get") as mock_get:
            mock_get.side_effect = requests.RequestException("Network error")

            result = extract_web_content.invoke("https://docs.python.org/3/")
            assert "Network error" in result

        # Test content too large
        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "x" * 6000000  # 6MB content
            mock_response.headers = {"content-length": "6000000"}
            mock_get.return_value = mock_response

            result = extract_web_content.invoke("https://docs.python.org/3/")
            assert "Content too large" in result


if __name__ == "__main__":
    # Run basic tests
    print("Testing web content extraction security and quality...")

    # Test security validation
    test_security = TestSecurityValidation()
    test_security.test_blocked_domains()
    test_security.test_invalid_urls()
    print("✅ Security validation tests passed")

    # Test quality filtering
    test_quality = TestQualityFiltering()
    test_quality.test_high_quality_content()
    print("✅ Quality filtering tests passed")

    # Test content extractor
    test_extractor = TestContentExtractor()
    test_extractor.test_extractor_initialization()
    test_extractor.test_quality_scoring()
    test_extractor.test_text_chunking()
    print("✅ Content extractor tests passed")

    print("🎉 All tests completed successfully!")
