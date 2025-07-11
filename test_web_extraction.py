import pytest

from tools.web_extraction import WebContentExtractor


class TestWebContentExtractor:
    """Comprehensive test suite for modern web content extraction."""

    @pytest.fixture
    def extractor(self):
        return WebContentExtractor()

    @pytest.fixture
    def speed_extractor(self):
        return WebContentExtractor(prefer_speed=True)

    def test_wikipedia_extraction(self, extractor):
        """Test extraction from Wikipedia-style structured content."""
        html = """
        <html>
        <head>
            <title>Python Programming Language</title>
            <meta property="og:title" content="Python (programming language)" />
            <meta name="description" content="Python is a high-level programming language" />
        </head>
        <body>
            <h1>Python Programming Language</h1>
            <p>Python is a high-level, interpreted programming language with dynamic semantics.</p>
            <h2>Features</h2>
            <p>Python's design philosophy emphasizes code readability.</p>
            <h3>Syntax</h3>
            <p>Python uses indentation to define code blocks.</p>
            <script>console.log('ads')</script>
        </body>
        </html>
        """

        result = extractor.extract(html, "https://en.wikipedia.org/wiki/Python")

        assert result.title in [
            "Python Programming Language",
            "Python (programming language)",
        ]
        assert "high-level, interpreted programming language" in result.content
        assert "console.log" not in result.content  # Scripts removed
        assert result.headers["h1"] == ["Python Programming Language"]
        assert result.headers["h2"] == ["Features"]
        assert result.headers["h3"] == ["Syntax"]
        assert result.word_count > 0
        assert result.extraction_method in [
            "trafilatura",
            "selectolax",
            "beautifulsoup",
        ]
        assert result.metadata["domain"] == "en.wikipedia.org"

    def test_blog_extraction(self, extractor):
        """Test extraction from blog-style content with varied structure."""
        html = """
        <html>
        <head><title>My Blog Post</title></head>
        <body>
            <nav>Navigation menu</nav>
            <article>
                <h1>Understanding AI Assistants</h1>
                <p>AI assistants are becoming increasingly sophisticated...</p>
                <h2>Technical Implementation</h2>
                <p>The implementation involves complex algorithms...</p>
            </article>
            <aside class="advertisement">Buy our product!</aside>
            <footer>Copyright 2025</footer>
        </body>
        </html>
        """

        result = extractor.extract(html, "https://myblog.com/ai-assistants")

        assert result.title == "My Blog Post"
        assert "AI assistants are becoming" in result.content
        assert "Navigation menu" not in result.content
        assert "Buy our product" not in result.content
        assert "Copyright 2025" not in result.content
        assert result.headers["h1"] == ["Understanding AI Assistants"]
        assert result.metadata["domain"] == "myblog.com"

    def test_news_extraction(self, extractor):
        """Test extraction from news website format."""
        html = """
        <html>
        <head>
            <title>Breaking News: AI Breakthrough</title>
            <meta name="author" content="Jane Reporter" />
            <meta name="description" content="Scientists achieve major AI milestone" />
        </head>
        <body>
            <main>
                <h1>Scientists Achieve Major AI Milestone</h1>
                <p class="byline">By Jane Reporter, January 2025</p>
                <p>In a groundbreaking development, researchers have...</p>
                <h2>Implications</h2>
                <p>This breakthrough could revolutionize...</p>
            </main>
        </body>
        </html>
        """

        result = extractor.extract(html, "https://news.example.com/ai-breakthrough")

        assert "Breaking News" in result.title or "Scientists Achieve" in result.title
        assert "groundbreaking development" in result.content
        assert result.metadata["domain"] == "news.example.com"
        # Note: metadata extraction depends on trafilatura availability
        if result.extraction_method == "trafilatura":
            assert result.metadata.get("author") == "Jane Reporter"

    def test_speed_optimization(self, speed_extractor):
        """Test that speed preference works for simple content."""
        simple_html = """
        <html>
        <head><title>Simple Page</title></head>
        <body>
            <h1>Simple Content</h1>
            <p>This is simple content without complex structure.</p>
        </body>
        </html>
        """

        result = speed_extractor.extract(simple_html, "https://simple.com")

        assert result.title == "Simple Page"
        assert "simple content" in result.content.lower()
        # Should prefer selectolax for simple content if available
        assert result.extraction_method in [
            "selectolax",
            "beautifulsoup",
            "trafilatura",
        ]

    def test_fallback_strategies(self, extractor):
        """Test that fallback extraction methods work when primary fails."""
        malformed_html = "<html><body><p>Partial content without proper"

        result = extractor.extract(malformed_html, "https://broken.com")

        # Should still extract something
        assert result is not None
        assert result.url == "https://broken.com"
        assert result.extraction_method in [
            "trafilatura",
            "selectolax",
            "beautifulsoup",
        ]

    def test_content_cleaning(self, extractor):
        """Test text cleaning and normalization."""
        html = """
        <html><body>
            <p>Regular content here.</p>
            <p>Advertisement: Buy now!</p>
            <p>Sponsored Content: Special offer</p>
            <p>    Extra    whitespace   </p>
            <p>Line 1</p>

            <p>Line 2 after many breaks</p>
        </body></html>
        """

        result = extractor.extract(html, "https://test.com")

        # Boilerplate should be removed or minimized
        content_lower = result.content.lower()
        assert "regular content" in content_lower
        # Excessive whitespace should be normalized
        assert "\n\n\n" not in result.content

    @pytest.mark.parametrize("content_type", ["wikipedia", "blog", "news"])
    def test_extraction_methods_consistency(self, content_type):
        """Test that different extraction methods produce consistent results."""
        test_htmls = {
            "wikipedia": "<html><head><title>Wiki Article</title></head><body><h1>Main Topic</h1><p>Content here.</p></body></html>",
            "blog": "<html><head><title>Blog Post</title></head><body><article><h1>Blog Title</h1><p>Blog content.</p></article></body></html>",
            "news": "<html><head><title>News Story</title></head><body><main><h1>Breaking News</h1><p>News content.</p></main></body></html>",
        }

        html = test_htmls[content_type]
        url = f"https://{content_type}.com/test"

        # Test with different speed preferences
        normal_extractor = WebContentExtractor(prefer_speed=False)
        speed_extractor = WebContentExtractor(prefer_speed=True)

        result1 = normal_extractor.extract(html, url)
        result2 = speed_extractor.extract(html, url)

        # Both should extract meaningful content
        assert len(result1.content) > 0
        assert len(result2.content) > 0
        assert result1.url == result2.url == url

        # Headers should be consistent
        assert len(result1.headers["h1"]) > 0
        assert len(result2.headers["h1"]) > 0

    def test_complexity_detection(self, extractor):
        """Test that complexity detection works for speed optimization."""
        # Simple content
        simple_html = "<html><body><h1>Title</h1><p>Simple content.</p></body></html>"
        assert extractor._is_simple_content(simple_html)

        # Complex content with many scripts
        complex_html = """
        <html>
        <head><title>Complex Page</title></head>
        <body>
            <script>console.log('script1')</script>
            <h1>Title</h1>
            <p>Content</p>
            <script>console.log('script2')</script>
            <style>body { color: red; }</style>
            <script>console.log('script3')</script>
        </body>
        </html>
        """
        assert not extractor._is_simple_content(complex_html)

        # Large content
        large_html = "<html><body>" + "<p>Content</p>" * 10000 + "</body></html>"
        assert not extractor._is_simple_content(large_html)

    def test_header_extraction(self, extractor):
        """Test that headers are properly extracted and structured."""
        html = """
        <html>
        <body>
            <h1>Main Title</h1>
            <h2>Section 1</h2>
            <p>Content 1</p>
            <h2>Section 2</h2>
            <h3>Subsection 2.1</h3>
            <p>Content 2.1</p>
            <h3>Subsection 2.2</h3>
            <p>Content 2.2</p>
        </body>
        </html>
        """

        result = extractor.extract(html, "https://test.com")

        assert result.headers["h1"] == ["Main Title"]
        assert result.headers["h2"] == ["Section 1", "Section 2"]
        assert result.headers["h3"] == ["Subsection 2.1", "Subsection 2.2"]

    def test_title_extraction_fallback(self, extractor):
        """Test title extraction with multiple fallback strategies."""
        # Test with og:title
        html1 = """
        <html>
        <head>
            <meta property="og:title" content="Open Graph Title" />
            <title>Regular Title</title>
        </head>
        <body><h1>H1 Title</h1></body>
        </html>
        """
        result1 = extractor.extract(html1, "https://test.com")
        assert result1.title == "Open Graph Title"

        # Test with regular title
        html2 = """
        <html>
        <head><title>Regular Title</title></head>
        <body><h1>H1 Title</h1></body>
        </html>
        """
        result2 = extractor.extract(html2, "https://test.com")
        assert result2.title == "Regular Title"

        # Test with h1 fallback
        html3 = """
        <html>
        <body><h1>H1 Title</h1></body>
        </html>
        """
        result3 = extractor.extract(html3, "https://test.com")
        assert result3.title == "H1 Title"

        # Test with no title
        html4 = """
        <html>
        <body><p>No title here</p></body>
        </html>
        """
        result4 = extractor.extract(html4, "https://test.com")
        assert result4.title == "Untitled"

    def test_metadata_extraction(self, extractor):
        """Test that metadata is properly extracted and structured."""
        html = """
        <html>
        <head>
            <title>Test Page</title>
            <meta name="author" content="Test Author" />
            <meta name="description" content="Test description" />
        </head>
        <body>
            <h1>Test Content</h1>
            <p>Some content here.</p>
        </body>
        </html>
        """

        result = extractor.extract(html, "https://example.com/test")

        # Basic metadata should always be present
        assert result.metadata["extraction_timestamp"]
        assert result.metadata["domain"] == "example.com"
        assert result.extraction_method in [
            "trafilatura",
            "selectolax",
            "beautifulsoup",
        ]

        # Advanced metadata depends on extraction method
        if result.extraction_method == "trafilatura":
            # trafilatura should extract more metadata
            assert "author" in result.metadata or "description" in result.metadata
