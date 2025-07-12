"""
Web Security Module for iKOMA

Provides OWASP-compliant web access filtering with SSRF prevention.
Implements comprehensive URL validation, rate limiting, and content size controls.
Part of Epic E-01: Internet Tooling - Issue #6.
"""

import ipaddress
import logging
import time
from dataclasses import dataclass, field
from threading import Lock
from urllib.parse import urlparse

import validators

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FilterConfig:
    """Configuration for domain filtering and rate limiting."""

    allowed_domains: set[str] = field(default_factory=lambda: {
        "wikipedia.org",
        "*.wikipedia.org",
        "github.com",
        "*.github.com",
        "docs.python.org",
        "pypi.org",
        "stackoverflow.com",
        "*.stackoverflow.com",
        "medium.com",
        "*.medium.com",
        "dev.to",
        "*.dev.to",
        "realpython.com",
        "*.realpython.com",
        "python.org",
        "*.python.org",
    })
    blocked_domains: set[str] = field(default_factory=lambda: {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "*.local",
        "*.internal",
        "*.test",
        "192.168.0.0/16",
        "10.0.0.0/8",
        "172.16.0.0/12",
    })
    rate_limit_delay: float = 0.2  # 5 req/sec
    max_content_size: int = 5_000_000  # 5MB
    allowed_schemes: set[str] = field(default_factory=lambda: {"http", "https"})


class SecureWebFilter:
    """OWASP-compliant web access filter preventing SSRF attacks."""

    def __init__(self, config: FilterConfig | None = None):
        self.config = config if config is not None else FilterConfig()
        self.last_request_times: dict[str, float] = {}
        self.rate_limit_lock = Lock()
        logger.info(
            f"Initialized SecureWebFilter with {len(self.config.allowed_domains)} allowed domains"
        )

    def validate_url(self, url: str) -> None:
        """Comprehensive URL validation with SSRF prevention."""
        parsed = urlparse(url)

        # Quick check for obviously blocked domains before validation
        if parsed.hostname:
            domain = parsed.hostname.lower()
            for blocked in self.config.blocked_domains:
                if blocked.startswith("*."):
                    if domain.endswith(blocked[2:]):
                        raise ValueError(f"Domain blocked: {domain}")
                elif blocked.startswith("*"):
                    if domain.endswith(blocked[1:]):
                        raise ValueError(f"Domain blocked: {domain}")
                elif domain == blocked:
                    raise ValueError(f"Domain blocked: {domain}")

        # Now validate URL format (except for blocked domains)
        if not validators.url(url):
            raise ValueError(f"Invalid URL format: {url}")

        # Scheme validation
        if (
            self.config.allowed_schemes
            and parsed.scheme not in self.config.allowed_schemes
        ):
            raise ValueError(f"Scheme '{parsed.scheme}' not allowed")

        # Hostname validation
        if not parsed.hostname:
            raise ValueError("URL must have a hostname")

        # Block private IP addresses (SSRF prevention)
        try:
            ip = ipaddress.ip_address(parsed.hostname)
            if ip.is_private or ip.is_loopback or ip.is_reserved:
                raise ValueError(f"Private/reserved IP address not allowed: {ip}")
        except ValueError:
            # Not an IP address, continue with domain checking
            pass

        # Domain allow/deny list checking
        domain = parsed.hostname.lower()

        # Check blocked domains (with wildcard support)
        for blocked in self.config.blocked_domains:
            if blocked.startswith("*."):
                if domain.endswith(blocked[2:]):
                    raise ValueError(f"Domain blocked: {domain}")
            elif blocked.startswith("*"):
                if domain.endswith(blocked[1:]):
                    raise ValueError(f"Domain blocked: {domain}")
            elif domain == blocked:
                raise ValueError(f"Domain blocked: {domain}")

        # If allowlist is defined, check it
        if self.config.allowed_domains:
            allowed = False
            for allowed_domain in self.config.allowed_domains:
                if allowed_domain.startswith("*."):
                    if domain.endswith(allowed_domain[2:]):
                        allowed = True
                        break
                elif allowed_domain.startswith("*"):
                    if domain.endswith(allowed_domain[1:]):
                        allowed = True
                        break
                elif domain == allowed_domain:
                    allowed = True
                    break

            if not allowed:
                raise ValueError(f"Domain not in allowlist: {domain}")

    def enforce_rate_limit(self, domain: str) -> None:
        """Token bucket rate limiting per domain."""
        with self.rate_limit_lock:
            now = time.time()
            last_time = self.last_request_times.get(domain, 0)

            time_diff = now - last_time
            if time_diff < self.config.rate_limit_delay:
                sleep_time = self.config.rate_limit_delay - time_diff
                logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s for {domain}")
                time.sleep(sleep_time)

            self.last_request_times[domain] = time.time()

    def validate_content_size(self, content_length: int | None, content: str) -> None:
        """Validate content size against configured limits."""
        if content_length and content_length > self.config.max_content_size:
            raise ValueError(
                f"Content too large: {content_length} bytes > {self.config.max_content_size}"
            )

        if len(content) > self.config.max_content_size:
            raise ValueError(
                f"Content too large: {len(content)} bytes > {self.config.max_content_size}"
            )

    def get_status(self) -> dict:
        """Get current filter status and statistics."""
        return {
            "allowed_domains_count": len(self.config.allowed_domains),
            "blocked_domains_count": len(self.config.blocked_domains),
            "allowed_schemes": list(self.config.allowed_schemes),
            "rate_limit_delay": self.config.rate_limit_delay,
            "max_content_size": self.config.max_content_size,
            "active_domains": len(self.last_request_times),
        }


# Global filter instance
_web_filter = SecureWebFilter()


def get_web_filter() -> SecureWebFilter:
    """Get the global web filter instance."""
    return _web_filter


def validate_web_url(url: str) -> None:
    """Validate a URL using the global web filter."""
    _web_filter.validate_url(url)


def enforce_web_rate_limit(domain: str) -> None:
    """Enforce rate limiting for a domain using the global web filter."""
    _web_filter.enforce_rate_limit(domain)
