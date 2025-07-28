"""
Tests for Domain Filter Module

Comprehensive test suite for domain filtering functionality.
Tests exact matching, wildcard matching, validation, and error handling.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.domain_filter import DomainFilter, get_domain_filter, is_domain_allowed


class TestDomainFilter:
    """Test cases for DomainFilter class."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary files for testing
        self.temp_dir = tempfile.mkdtemp()
        self.allow_file = Path(self.temp_dir) / "allow.txt"
        self.deny_file = Path(self.temp_dir) / "deny.txt"

        # Create test allow file
        with open(self.allow_file, "w") as f:
            f.write("""# Test allow list
example.com
*.wikipedia.org
github.com
docs.python.org
""")

        # Create test deny file
        with open(self.deny_file, "w") as f:
            f.write("""# Test deny list
malware.com
*.suspicious.net
phishing.org
""")

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass  # Ignore cleanup errors

    def test_domain_filter_initialization(self):
        """Test domain filter initialization."""
        filter_instance = DomainFilter(
            allow_file=str(self.allow_file),
            deny_file=str(self.deny_file),
            default_policy="deny",
        )

        assert filter_instance.default_policy == "deny"
        assert len(filter_instance.allow_domains) > 0
        assert len(filter_instance.deny_domains) > 0

    def test_exact_domain_matching(self):
        """Test exact domain matching."""
        filter_instance = DomainFilter(
            allow_file=str(self.allow_file), deny_file=str(self.deny_file)
        )

        # Test allowed domains
        assert filter_instance.is_domain_allowed("example.com")[0]
        assert filter_instance.is_domain_allowed("github.com")[0]

        # Test denied domains
        assert not filter_instance.is_domain_allowed("malware.com")[0]
        assert not filter_instance.is_domain_allowed("phishing.org")[0]

        # Test unknown domains (deny by default)
        assert not filter_instance.is_domain_allowed("unknown.com")[0]

    def test_wildcard_domain_matching(self):
        """Test wildcard subdomain matching."""
        filter_instance = DomainFilter(
            allow_file=str(self.allow_file), deny_file=str(self.deny_file)
        )

        # Test allowed wildcards
        assert filter_instance.is_domain_allowed("en.wikipedia.org")[0]
        assert filter_instance.is_domain_allowed("fr.wikipedia.org")[0]
        assert filter_instance.is_domain_allowed("wikipedia.org")[0]

        # Test denied wildcards
        assert not filter_instance.is_domain_allowed("evil.suspicious.net")[0]
        assert not filter_instance.is_domain_allowed("malware.suspicious.net")[0]

    def test_domain_normalization(self):
        """Test domain normalization (lowercase, www removal)."""
        filter_instance = DomainFilter(
            allow_file=str(self.allow_file), deny_file=str(self.deny_file)
        )

        # Test case insensitivity
        assert filter_instance.is_domain_allowed("EXAMPLE.COM")[0]
        assert filter_instance.is_domain_allowed("Example.Com")[0]

        # Test www removal
        assert filter_instance.is_domain_allowed("www.example.com")[0]
        assert filter_instance.is_domain_allowed("www.github.com")[0]

    def test_domain_validation(self):
        """Test domain format validation."""
        filter_instance = DomainFilter(
            allow_file=str(self.allow_file), deny_file=str(self.deny_file)
        )

        # Valid domains
        assert filter_instance._is_valid_domain("example.com")
        assert filter_instance._is_valid_domain("sub.example.com")
        assert filter_instance._is_valid_domain("*.example.com")

        # Invalid domains
        assert not filter_instance._is_valid_domain("")
        assert not filter_instance._is_valid_domain("invalid..domain")
        assert filter_instance._is_valid_domain("domain-with-dash.com")
        assert not filter_instance._is_valid_domain("domain_with_underscore.com")

    def test_deny_precedence(self):
        """Test that deny list takes precedence over allow list."""
        # Create a domain that appears in both lists
        with open(self.allow_file, "a") as f:
            f.write("conflict.com\n")

        with open(self.deny_file, "a") as f:
            f.write("conflict.com\n")

        filter_instance = DomainFilter(
            allow_file=str(self.allow_file), deny_file=str(self.deny_file)
        )

        # Deny should take precedence
        assert not filter_instance.is_domain_allowed("conflict.com")[0]

    def test_default_policy_allow(self):
        """Test allow-by-default policy."""
        filter_instance = DomainFilter(
            allow_file=str(self.allow_file),
            deny_file=str(self.deny_file),
            default_policy="allow",
        )

        # Unknown domains should be allowed
        assert filter_instance.is_domain_allowed("unknown.com")[0]

    def test_missing_files(self):
        """Test behavior when configuration files are missing."""
        # Create filter with non-existent files
        filter_instance = DomainFilter(
            allow_file="nonexistent_allow.txt",
            deny_file="nonexistent_deny.txt",
            default_policy="deny",
        )

        # Should use default policy
        assert not filter_instance.is_domain_allowed("any.com")[0]

    def test_malformed_domain_files(self):
        """Test handling of malformed domain files."""
        # Create file with invalid domains
        with open(self.allow_file, "w") as f:
            f.write("""# Valid domains
example.com
github.com

# Invalid domains
invalid..domain
domain_with_underscore.com
""")

        filter_instance = DomainFilter(
            allow_file=str(self.allow_file), deny_file=str(self.deny_file)
        )

        # Should load valid domains and skip invalid ones
        assert "example.com" in filter_instance.allow_domains
        assert "github.com" in filter_instance.allow_domains
        assert "invalid..domain" not in filter_instance.allow_domains

    def test_config_reload(self):
        """Test configuration reloading."""
        filter_instance = DomainFilter(
            allow_file=str(self.allow_file), deny_file=str(self.deny_file)
        )

        # Add new domain to allow file
        with open(self.allow_file, "a") as f:
            f.write("newdomain.com\n")

        # Reload configuration
        filter_instance.reload_config()

        # New domain should be allowed
        assert filter_instance.is_domain_allowed("newdomain.com")[0]

    def test_cache_functionality(self):
        """Test caching functionality."""
        filter_instance = DomainFilter(
            allow_file=str(self.allow_file), deny_file=str(self.deny_file)
        )

        # First call should populate cache
        result1 = filter_instance.is_domain_allowed("example.com")
        assert len(filter_instance._cache) > 0

        # Second call should use cache
        result2 = filter_instance.is_domain_allowed("example.com")
        assert result1 == result2

    def test_get_status(self):
        """Test status reporting."""
        filter_instance = DomainFilter(
            allow_file=str(self.allow_file), deny_file=str(self.deny_file)
        )

        status = filter_instance.get_status()

        assert "allow_domains_count" in status
        assert "deny_domains_count" in status
        assert "default_policy" in status
        assert status["default_policy"] == "deny"
        assert status["allow_file_exists"]
        assert status["deny_file_exists"]


class TestDomainFilterFunctions:
    """Test cases for convenience functions."""

    def test_is_domain_allowed_function(self):
        """Test the convenience function."""
        # Mock the global domain filter
        with patch("tools.domain_filter.get_domain_filter") as mock_get_filter:
            mock_filter = DomainFilter()
            mock_filter.is_domain_allowed = lambda domain: (True, "test")
            mock_get_filter.return_value = mock_filter

            result = is_domain_allowed("test.com")
            assert result == (True, "test")

    def test_get_domain_filter_singleton(self):
        """Test singleton pattern."""
        # Reset global instance
        import tools.domain_filter

        tools.domain_filter._domain_filter = None

        # First call should create instance
        filter1 = get_domain_filter()
        assert filter1 is not None

        # Second call should return same instance
        filter2 = get_domain_filter()
        assert filter1 is filter2


class TestDomainFilterIntegration:
    """Integration tests for domain filter with real files."""

    def test_real_file_parsing(self):
        """Test parsing of real domain files."""
        # Create realistic domain files
        allow_content = """# Educational sites
wikipedia.org
*.wikipedia.org
stackoverflow.com
github.com

# Documentation
docs.python.org
developer.mozilla.org
"""

        deny_content = """# Dangerous sites
*.malware.com
phishing-site.org
suspicious.net
"""

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as allow_file:
            allow_file.write(allow_content)
            allow_path = allow_file.name

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as deny_file:
            deny_file.write(deny_content)
            deny_path = deny_file.name

        try:
            filter_instance = DomainFilter(allow_file=allow_path, deny_file=deny_path)

            # Test allowed domains
            assert filter_instance.is_domain_allowed("wikipedia.org")[0]
            assert filter_instance.is_domain_allowed("en.wikipedia.org")[0]
            assert filter_instance.is_domain_allowed("github.com")[0]

            # Test denied domains
            assert not filter_instance.is_domain_allowed("evil.malware.com")[0]
            assert not filter_instance.is_domain_allowed("phishing-site.org")[0]

            # Test unknown domains
            assert not filter_instance.is_domain_allowed("unknown.com")[0]

        finally:
            os.unlink(allow_path)
            os.unlink(deny_path)


if __name__ == "__main__":
    pytest.main([__file__])
