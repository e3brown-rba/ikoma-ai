"""
Rate-Limited HTTP Client Wrapper for iKOMA

Provides safe HTTP requests with rate limiting, domain filtering, and comprehensive error handling.
Part of Epic E-01: Internet Tooling - Issue #5.

Features:
- Rate limiting with configurable limits per domain
- Domain filtering integration for security
- Comprehensive error handling and logging
- Request/response caching for performance
- User-Agent rotation for polite web scraping
- Timeout and retry logic
"""

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for token bucket rate limiting per domain."""

    requests_per_second: float = (
        5.0  # Token bucket refill rate (5 req/s as per requirements)
    )
    bucket_capacity: int = 10  # Maximum tokens in bucket (burst capacity)
    backoff_base: float = 1.0  # Base backoff time in seconds for 429/503
    backoff_max: float = 60.0  # Maximum backoff time in seconds
    backoff_multiplier: float = 2.0  # Exponential backoff multiplier


@dataclass
class RequestStats:
    """Token bucket based statistics for tracking requests to a domain."""

    domain: str
    tokens: float = field(default_factory=lambda: 10.0)  # Start with full bucket
    last_refill: datetime = field(default_factory=datetime.now)
    total_requests: int = 0
    rate_limit_hits: int = 0
    backoff_until: datetime | None = None
    backoff_attempts: int = 0
    last_request: datetime | None = None

    def _refill_tokens(self, config: RateLimitConfig) -> None:
        """Refill tokens based on elapsed time since last refill."""
        now = datetime.now()
        elapsed = (now - self.last_refill).total_seconds()

        # Add tokens based on elapsed time and refill rate
        tokens_to_add = elapsed * config.requests_per_second
        self.tokens = min(config.bucket_capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def is_rate_limited(self, config: RateLimitConfig) -> tuple[bool, str]:
        """Check if domain is currently rate limited using token bucket algorithm."""
        now = datetime.now()

        # Check if we're in backoff period
        if self.backoff_until and now < self.backoff_until:
            remaining = (self.backoff_until - now).total_seconds()
            return True, f"In backoff period for {remaining:.1f} more seconds"

        # Refill tokens
        self._refill_tokens(config)

        # Check if we have tokens available
        if self.tokens < 1.0:
            return True, f"Token bucket empty (has {self.tokens:.2f} tokens)"

        return False, "OK"

    def consume_token(self, config: RateLimitConfig) -> bool:
        """Consume a token if available. Returns True if successful."""
        self._refill_tokens(config)

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            self.total_requests += 1
            self.last_request = datetime.now()
            # Reset backoff on successful request
            self.backoff_until = None
            self.backoff_attempts = 0
            return True

        self.rate_limit_hits += 1
        return False

    def trigger_backoff(self, config: RateLimitConfig, status_code: int) -> None:
        """Trigger exponential backoff for 429/503 responses."""
        now = datetime.now()
        self.backoff_attempts += 1

        # Calculate backoff time with exponential increase
        backoff_time = min(
            config.backoff_max,
            config.backoff_base
            * (config.backoff_multiplier ** (self.backoff_attempts - 1)),
        )

        self.backoff_until = now + timedelta(seconds=backoff_time)
        logger.warning(
            f"HTTP {status_code} response for {self.domain}, backing off for {backoff_time:.1f}s"
        )

    def get_stats(self) -> dict[str, Any]:
        """Get current statistics for this domain."""
        return {
            "domain": self.domain,
            "total_requests": self.total_requests,
            "current_tokens": round(self.tokens, 2),
            "rate_limit_hits": self.rate_limit_hits,
            "backoff_attempts": self.backoff_attempts,
            "backoff_until": self.backoff_until.isoformat()
            if self.backoff_until
            else None,
            "last_request": self.last_request.isoformat()
            if self.last_request
            else None,
        }


class RateLimitedHTTPClient:
    """
    Rate-limited HTTP client with domain filtering and comprehensive error handling.

    Features:
    - Per-domain rate limiting with configurable limits
    - Domain filtering integration for security
    - Request/response caching
    - User-Agent rotation
    - Comprehensive error handling and logging
    """

    def __init__(
        self,
        default_rate_limit: RateLimitConfig | None = None,
        cache_dir: str = "agent/memory/http_cache",
        user_agents: list[str] | None = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize the rate-limited HTTP client.

        Args:
            default_rate_limit: Default rate limiting configuration
            cache_dir: Directory for caching responses
            user_agents: List of User-Agent strings to rotate
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
        """
        self.default_rate_limit = default_rate_limit or RateLimitConfig()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # User-Agent rotation
        self.user_agents = user_agents or [
            "Mozilla/5.0 (compatible; iKOMA-Bot/1.0; +https://github.com/e3brown-rba/ikoma-ai)",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        self.current_user_agent_index = 0

        self.timeout = timeout
        self.max_retries = max_retries

        # Domain-specific rate limits
        self.domain_configs: dict[str, RateLimitConfig] = {}
        self.request_stats: dict[str, RequestStats] = {}

        # Thread safety
        self._lock = threading.Lock()

        # Import domain filter
        try:
            from .domain_filter import is_domain_allowed

            self.is_domain_allowed = is_domain_allowed
        except ImportError:
            logger.warning("Domain filter not available, allowing all domains")
            self.is_domain_allowed = lambda domain: (
                True,
                "Domain filter not available",
            )

    def set_domain_rate_limit(self, domain: str, config: RateLimitConfig) -> None:
        """Set custom rate limit configuration for a specific domain."""
        with self._lock:
            self.domain_configs[domain] = config

    def get_domain_config(self, domain: str) -> RateLimitConfig:
        """Get rate limit configuration for a domain."""
        return self.domain_configs.get(domain, self.default_rate_limit)

    def _get_next_user_agent(self) -> str:
        """Get next User-Agent from rotation."""
        user_agent = self.user_agents[self.current_user_agent_index]
        self.current_user_agent_index = (self.current_user_agent_index + 1) % len(
            self.user_agents
        )
        return user_agent

    def _get_cache_key(self, url: str, method: str = "GET") -> str:
        """Generate cache key for URL and method."""
        import hashlib

        key_data = f"{method}:{url}".encode()
        return hashlib.md5(key_data, usedforsecurity=False).hexdigest()

    def _get_cached_response(
        self, url: str, method: str = "GET"
    ) -> dict[str, Any] | None:
        """Get cached response if available and not expired."""
        try:
            cache_key = self._get_cache_key(url, method)
            cache_file = self.cache_dir / f"{cache_key}.json"

            if not cache_file.exists():
                return None

            with open(cache_file) as f:
                cached: dict[str, Any] = json.load(f)

            # Check if cache is expired (1 hour default)
            cache_time = datetime.fromisoformat(cached["timestamp"])
            if datetime.now() - cache_time > timedelta(hours=1):
                cache_file.unlink()  # Remove expired cache
                return None

            return cached
        except Exception as e:
            logger.warning(f"Error reading cache for {url}: {e}")
            return None

    def _cache_response(
        self, url: str, method: str, response_data: dict[str, Any]
    ) -> None:
        """Cache response data."""
        try:
            cache_key = self._get_cache_key(url, method)
            cache_file = self.cache_dir / f"{cache_key}.json"

            response_data["timestamp"] = datetime.now().isoformat()
            response_data["url"] = url
            response_data["method"] = method

            with open(cache_file, "w") as f:
                json.dump(response_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Error caching response for {url}: {e}")

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Remove port if present
        if ":" in domain:
            domain = domain.split(":")[0]

        return domain

    def _check_rate_limit(self, domain: str) -> tuple[bool, str]:
        """Check if domain is rate limited."""
        with self._lock:
            if domain not in self.request_stats:
                self.request_stats[domain] = RequestStats(domain)

            stats = self.request_stats[domain]
            config = self.get_domain_config(domain)

            is_limited, reason = stats.is_rate_limited(config)

            if is_limited:
                stats.rate_limit_hits += 1
                return True, reason

            return False, "OK"

    def _consume_token(self, domain: str) -> bool:
        """Consume a token for the domain. Returns True if successful."""
        with self._lock:
            if domain not in self.request_stats:
                self.request_stats[domain] = RequestStats(domain)

            config = self.get_domain_config(domain)
            return self.request_stats[domain].consume_token(config)

    def get(
        self, url: str, headers: dict[str, str] | None = None, use_cache: bool = True
    ) -> dict[str, Any]:
        """
        Make a rate-limited GET request.

        Args:
            url: URL to request
            headers: Additional headers to include
            use_cache: Whether to use cached responses

        Returns:
            Dictionary with response data and metadata
        """
        return self._make_request(url, "GET", headers=headers, use_cache=use_cache)

    def post(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Make a rate-limited POST request.

        Args:
            url: URL to request
            data: POST data to send
            headers: Additional headers to include

        Returns:
            Dictionary with response data and metadata
        """
        return self._make_request(
            url, "POST", data=data, headers=headers, use_cache=False
        )

    def _make_request(
        self,
        url: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """
        Make a rate-limited HTTP request.

        Args:
            url: URL to request
            method: HTTP method (GET, POST, etc.)
            data: Request data for POST requests
            headers: Additional headers
            use_cache: Whether to use cached responses (GET only)

        Returns:
            Dictionary with response data and metadata
        """
        # Extract domain for rate limiting and filtering
        domain = self._extract_domain(url)

        # Check domain filtering
        is_allowed, reason = self.is_domain_allowed(domain)
        if not is_allowed:
            return {
                "success": False,
                "error": f"Domain not allowed: {reason}",
                "url": url,
                "domain": domain,
                "method": method,
                "timestamp": datetime.now().isoformat(),
            }

        # Check rate limiting and consume token
        is_rate_limited, rate_limit_reason = self._check_rate_limit(domain)
        if is_rate_limited:
            return {
                "success": False,
                "error": f"Rate limited: {rate_limit_reason}",
                "url": url,
                "domain": domain,
                "method": method,
                "timestamp": datetime.now().isoformat(),
            }

        # Try to consume a token
        if not self._consume_token(domain):
            return {
                "success": False,
                "error": "Rate limited: No tokens available",
                "url": url,
                "domain": domain,
                "method": method,
                "timestamp": datetime.now().isoformat(),
            }

        # Check cache for GET requests
        if method == "GET" and use_cache:
            cached = self._get_cached_response(url, method)
            if cached:
                cached["cached"] = True
                return cached

        # Prepare headers
        request_headers = {
            "User-Agent": self._get_next_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

        if headers:
            request_headers.update(headers)

        # Make the request
        try:
            response = requests.request(
                method=method,
                url=url,
                data=data,
                headers=request_headers,
                timeout=self.timeout,
                allow_redirects=True,
            )

            # Handle rate limiting responses (429) and service unavailable (503)
            if response.status_code in [429, 503]:
                with self._lock:
                    if domain in self.request_stats:
                        config = self.get_domain_config(domain)
                        self.request_stats[domain].trigger_backoff(
                            config, response.status_code
                        )

                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.reason}",
                    "url": url,
                    "domain": domain,
                    "method": method,
                    "status_code": response.status_code,
                    "timestamp": datetime.now().isoformat(),
                }

            # Prepare response data
            response_data = {
                "success": True,
                "url": url,
                "domain": domain,
                "method": method,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": response.text,
                "content_length": len(response.content),
                "encoding": response.encoding,
                "timestamp": datetime.now().isoformat(),
                "cached": False,
            }

            # Cache successful GET responses
            if method == "GET" and response.status_code == 200 and use_cache:
                self._cache_response(url, method, response_data)

            return response_data

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": f"Request timeout after {self.timeout} seconds",
                "url": url,
                "domain": domain,
                "method": method,
                "timestamp": datetime.now().isoformat(),
            }
        except requests.exceptions.ConnectionError as e:
            return {
                "success": False,
                "error": f"Connection error: {str(e)}",
                "url": url,
                "domain": domain,
                "method": method,
                "timestamp": datetime.now().isoformat(),
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Request error: {str(e)}",
                "url": url,
                "domain": domain,
                "method": method,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "url": url,
                "domain": domain,
                "method": method,
                "timestamp": datetime.now().isoformat(),
            }

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive statistics about HTTP client usage."""
        with self._lock:
            stats: dict[str, Any] = {
                "total_domains": len(self.request_stats),
                "total_requests": sum(
                    domain_stats.total_requests
                    for domain_stats in self.request_stats.values()
                ),
                "rate_limit_hits": sum(
                    domain_stats.rate_limit_hits
                    for domain_stats in self.request_stats.values()
                ),
                "domains": {},
                "cache_info": {
                    "cache_dir": str(self.cache_dir),
                    "cache_files": len(list(self.cache_dir.glob("*.json"))),
                },
                "config": {
                    "default_rate_limit": {
                        "requests_per_second": self.default_rate_limit.requests_per_second,
                        "bucket_capacity": self.default_rate_limit.bucket_capacity,
                        "backoff_base": self.default_rate_limit.backoff_base,
                        "backoff_max": self.default_rate_limit.backoff_max,
                        "backoff_multiplier": self.default_rate_limit.backoff_multiplier,
                    },
                    "timeout": self.timeout,
                    "max_retries": self.max_retries,
                    "user_agents_count": len(self.user_agents),
                },
            }

            # Add per-domain statistics
            for domain, domain_stats in self.request_stats.items():
                stats["domains"][domain] = domain_stats.get_stats()

            return stats

    def clear_cache(self) -> str:
        """Clear all cached responses."""
        try:
            cache_files = list(self.cache_dir.glob("*.json"))
            for cache_file in cache_files:
                cache_file.unlink()
            return f"Cleared {len(cache_files)} cached responses"
        except Exception as e:
            return f"Error clearing cache: {str(e)}"

    def reset_stats(self) -> str:
        """Reset all request statistics."""
        with self._lock:
            self.request_stats.clear()
            return "Request statistics reset"


# Global instance for easy access
http_client: RateLimitedHTTPClient | None = None


def get_http_client() -> RateLimitedHTTPClient:
    """Get or create the global HTTP client instance."""
    global http_client
    if http_client is None:
        http_client = RateLimitedHTTPClient()
    return http_client
