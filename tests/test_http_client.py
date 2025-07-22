#!/usr/bin/env python3
"""
Test HTTP Client Implementation for Issue #5

Tests the rate-limited HTTP client wrapper with domain filtering and caching.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# Import the HTTP client
from tools.http_client import (
    RateLimitConfig,
    RateLimitedHTTPClient,
    RequestStats,
    get_http_client,
)
from tools.http_tools import (
    get_http_client_stats,
    make_http_request,
)


class TestRateLimitConfig:
    """Test rate limit configuration."""

    def test_default_config(self):
        """Test default rate limit configuration."""
        config = RateLimitConfig()
        assert config.requests_per_second == 5.0
        assert config.bucket_capacity == 10
        assert config.backoff_base == 1.0
        assert config.backoff_max == 60.0
        assert config.backoff_multiplier == 2.0

    def test_custom_config(self):
        """Test custom rate limit configuration."""
        config = RateLimitConfig(
            requests_per_second=3.0,
            bucket_capacity=5,
            backoff_base=2.0,
            backoff_max=120.0,
            backoff_multiplier=1.5,
        )
        assert config.requests_per_second == 3.0
        assert config.bucket_capacity == 5
        assert config.backoff_base == 2.0
        assert config.backoff_max == 120.0
        assert config.backoff_multiplier == 1.5


class TestRequestStats:
    """Test token bucket based request statistics tracking."""

    def test_initial_state(self):
        """Test initial state of request statistics."""
        stats = RequestStats("example.com")
        assert stats.domain == "example.com"
        assert stats.tokens == 10.0  # Full bucket
        assert stats.total_requests == 0
        assert stats.rate_limit_hits == 0
        assert stats.backoff_until is None
        assert stats.backoff_attempts == 0

    def test_token_consumption(self):
        """Test token consumption."""
        config = RateLimitConfig(requests_per_second=5.0, bucket_capacity=10)
        stats = RequestStats("example.com")

        # Consume a token
        success = stats.consume_token(config)
        assert success
        assert stats.tokens == 9.0
        assert stats.total_requests == 1
        assert stats.last_request is not None

    def test_token_bucket_empty(self):
        """Test behavior when token bucket is empty."""
        config = RateLimitConfig(requests_per_second=5.0, bucket_capacity=2)
        stats = RequestStats("example.com")
        stats.tokens = 0.5  # Less than 1 token

        is_limited, reason = stats.is_rate_limited(config)
        assert is_limited
        assert "Token bucket empty" in reason

    def test_token_refill(self):
        """Test token bucket refill over time."""
        config = RateLimitConfig(requests_per_second=5.0, bucket_capacity=10)
        stats = RequestStats("example.com")
        stats.tokens = 5.0

        # Simulate time passage by manually setting last_refill
        stats.last_refill = datetime.now() - timedelta(seconds=1)

        # Refill should add 5 tokens (5 req/s * 1 second)
        stats._refill_tokens(config)
        assert stats.tokens == 10.0  # Capped at bucket capacity

    def test_backoff_trigger(self):
        """Test exponential backoff triggering."""
        config = RateLimitConfig(backoff_base=1.0, backoff_multiplier=2.0)
        stats = RequestStats("example.com")

        # Trigger first backoff
        stats.trigger_backoff(config, 429)
        assert stats.backoff_attempts == 1
        assert stats.backoff_until is not None

        # Check if in backoff period
        is_limited, reason = stats.is_rate_limited(config)
        assert is_limited
        assert "backoff period" in reason

    def test_get_stats(self):
        """Test getting statistics."""
        stats = RequestStats("example.com")
        config = RateLimitConfig()
        stats.consume_token(config)

        stats_data = stats.get_stats()
        assert stats_data["domain"] == "example.com"
        assert stats_data["total_requests"] == 1
        assert stats_data["current_tokens"] == 9.0
        assert stats_data["rate_limit_hits"] == 0
        assert stats_data["backoff_attempts"] == 0


class TestRateLimitedHTTPClient:
    """Test the rate-limited HTTP client."""

    def test_init(self):
        """Test client initialization."""
        client = RateLimitedHTTPClient()
        assert client.timeout == 30
        assert client.max_retries == 3
        assert len(client.user_agents) > 0
        assert client.cache_dir.exists()

    def test_extract_domain(self):
        """Test domain extraction from URLs."""
        client = RateLimitedHTTPClient()

        assert client._extract_domain("https://example.com/page") == "example.com"
        assert (
            client._extract_domain("http://api.example.com:8080/v1")
            == "api.example.com"
        )
        assert client._extract_domain("https://www.example.com") == "www.example.com"

    def test_set_domain_rate_limit(self):
        """Test setting custom rate limits for domains."""
        client = RateLimitedHTTPClient()
        config = RateLimitConfig(requests_per_second=3.0)

        client.set_domain_rate_limit("api.example.com", config)
        retrieved_config = client.get_domain_config("api.example.com")

        assert retrieved_config.requests_per_second == 3.0
        assert retrieved_config.bucket_capacity == 10  # Default

    def test_user_agent_rotation(self):
        """Test User-Agent rotation."""
        client = RateLimitedHTTPClient()
        user_agents = set()

        # Get multiple user agents
        for _ in range(5):
            user_agents.add(client._get_next_user_agent())

        # Should have multiple different user agents
        assert len(user_agents) > 1

    @patch("tools.http_client.requests.request")
    def test_successful_request(self, mock_request):
        """Test successful HTTP request."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Hello, World!"
        mock_response.content = b"Hello, World!"
        mock_response.encoding = "utf-8"
        mock_response.headers = {"content-type": "text/plain"}
        mock_request.return_value = mock_response

        client = RateLimitedHTTPClient()

        # Mock domain filtering to allow the request
        with patch.object(client, "is_domain_allowed", return_value=(True, "Allowed")):
            response = client.get("https://example.com/test")

        assert response["success"] is True
        assert response["status_code"] == 200
        assert response["content"] == "Hello, World!"
        assert response["domain"] == "example.com"

    @patch("tools.http_client.requests.request")
    def test_domain_filtered_request(self, mock_request):
        """Test request blocked by domain filtering."""
        client = RateLimitedHTTPClient()

        # Mock domain filtering to deny the request
        with patch.object(
            client, "is_domain_allowed", return_value=(False, "Domain not allowed")
        ):
            response = client.get("https://blocked.com/test")

        assert response["success"] is False
        assert "Domain not allowed" in response["error"]
        mock_request.assert_not_called()

    @patch("tools.http_client.requests.request")
    def test_rate_limited_request(self, mock_request):
        """Test request blocked by rate limiting."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_response.content = b"OK"
        mock_response.encoding = "utf-8"
        mock_response.headers = {}
        mock_request.return_value = mock_response

        # Create client with small bucket capacity
        client = RateLimitedHTTPClient(
            default_rate_limit=RateLimitConfig(bucket_capacity=2)
        )

        # Mock domain filtering to allow the request
        with patch.object(client, "is_domain_allowed", return_value=(True, "Allowed")):
            # Make requests to exhaust token bucket
            response1 = client.get("https://example.com/test1")
            assert response1["success"] is True

            response2 = client.get("https://example.com/test2")
            assert response2["success"] is True

            # Third request should be rate limited (no tokens left)
            response3 = client.get("https://example.com/test3")
            assert response3["success"] is False
            assert "Rate limited" in response3["error"]

    @patch("tools.http_client.requests.request")
    def test_429_503_backoff(self, mock_request):
        """Test exponential backoff for 429/503 responses."""
        # Mock 429 response
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.reason = "Too Many Requests"
        mock_request.return_value = mock_response

        client = RateLimitedHTTPClient()
        # Clear any existing cache to ensure fresh requests
        client.clear_cache()

        # Mock domain filtering to allow the request
        with patch.object(client, "is_domain_allowed", return_value=(True, "Allowed")):
            # First request should get 429 and trigger backoff
            response = client.get("https://example.com/test")
            assert response["success"] is False
            assert response["status_code"] == 429
            assert "HTTP 429" in response["error"]

            # Immediate second request should be blocked by backoff
            response2 = client.get("https://example.com/test")
            assert response2["success"] is False
            assert (
                "backoff period" in response2["error"]
                or "Rate limited" in response2["error"]
            )

    def test_cache_functionality(self):
        """Test response caching."""
        client = RateLimitedHTTPClient()

        # Test cache key generation
        key1 = client._get_cache_key("https://example.com/test", "GET")
        key2 = client._get_cache_key("https://example.com/test", "GET")
        assert key1 == key2

        key3 = client._get_cache_key("https://example.com/test", "POST")
        assert key1 != key3

    def test_get_stats(self):
        """Test getting client statistics."""
        client = RateLimitedHTTPClient()
        stats = client.get_stats()

        assert "total_domains" in stats
        assert "total_requests" in stats
        assert "rate_limit_hits" in stats
        assert "cache_info" in stats
        assert "config" in stats
        assert "domains" in stats


class TestHTTPTools:
    """Test HTTP tools integration."""

    def test_make_http_request_success(self):
        """Test successful HTTP request tool."""
        with patch("tools.http_tools.get_http_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = {
                "success": True,
                "url": "https://example.com/test",
                "method": "GET",
                "status_code": 200,
                "content": "Hello, World!",
                "content_length": 13,
                "domain": "example.com",
                "timestamp": "2024-01-01T00:00:00",
                "cached": False,
            }
            mock_get_client.return_value = mock_client

            result = make_http_request.invoke({"url": "https://example.com/test"})

            assert "✅ Request successful" in result
            assert "Hello, World!" in result

    def test_make_http_request_failure(self):
        """Test failed HTTP request tool."""
        with patch("tools.http_tools.get_http_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = {
                "success": False,
                "url": "https://example.com/test",
                "error": "Connection timeout",
                "timestamp": "2024-01-01T00:00:00",
            }
            mock_get_client.return_value = mock_client

            result = make_http_request("https://example.com/test")

            assert "❌ Request failed" in result
            assert "Connection timeout" in result

    def test_get_http_client_stats(self):
        """Test getting HTTP client statistics tool."""
        with patch("tools.http_tools.get_http_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_stats.return_value = {
                "total_domains": 2,
                "total_requests": 10,
                "rate_limit_hits": 1,
                "cache_info": {"cache_files": 5, "cache_dir": "/tmp/cache"},
                "config": {
                    "default_rate_limit": {
                        "requests_per_second": 5.0,
                        "bucket_capacity": 10,
                        "backoff_base": 1.0,
                        "backoff_max": 60.0,
                        "backoff_multiplier": 2.0,
                    },
                    "timeout": 30,
                    "user_agents_count": 3,
                },
                "domains": {},
            }
            mock_get_client.return_value = mock_client

            result = get_http_client_stats.invoke({})

            assert "📊 HTTP Client Statistics" in result
            assert "Total Domains: 2" in result
            assert "Total Requests: 10" in result


def test_get_http_client_singleton():
    """Test that get_http_client returns a singleton instance."""
    client1 = get_http_client()
    client2 = get_http_client()

    assert client1 is client2
    assert isinstance(client1, RateLimitedHTTPClient)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
