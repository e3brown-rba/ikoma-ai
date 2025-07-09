"""
Domain Filter Module for iKOMA Internet Safety

Provides domain allow/deny filtering functionality with file-based configuration.
Implements security-first design with deny-by-default and deny precedence.
"""

import re
import logging
from pathlib import Path
from typing import Set, Tuple, Optional, Dict, Any
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DomainFilter:
    """
    Domain filtering system with allow/deny list management.

    Features:
    - File-based configuration with automatic reloading
    - Support for exact domains and wildcard subdomains
    - Security-first design (deny-by-default, deny precedence)
    - Comprehensive validation and error handling
    """

    def __init__(
        self,
        allow_file: str = ".allow_domains.txt",
        deny_file: str = ".deny_domains.txt",
        default_policy: str = "deny",
        reload_interval: int = 300,
    ):
        """
        Initialize domain filter with configuration files.

        Args:
            allow_file: Path to allow list file
            deny_file: Path to deny list file
            default_policy: Default policy when no lists exist ("allow" or "deny")
            reload_interval: Seconds between config reloads
        """
        self.allow_file = Path(allow_file)
        self.deny_file = Path(deny_file)
        self.default_policy = default_policy.lower()
        self.reload_interval = reload_interval

        # Domain storage
        self.allow_domains: Set[str] = set()
        self.deny_domains: Set[str] = set()
        self.allow_wildcards: Set[str] = set()
        self.deny_wildcards: Set[str] = set()

        # Cache for performance
        self.last_reload = 0
        self._cache: Dict[str, Tuple[bool, str]] = {}

        # Validation
        if self.default_policy not in ["allow", "deny"]:
            raise ValueError("default_policy must be 'allow' or 'deny'")

        # Load initial configuration
        self.reload_config()

    def is_domain_allowed(self, domain: str) -> Tuple[bool, str]:
        """
        Check if a domain is allowed based on current configuration.

        Args:
            domain: Domain to check (e.g., "example.com", "blog.example.com")

        Returns:
            Tuple of (is_allowed: bool, reason: str)
        """
        # Check cache first
        if domain in self._cache:
            return self._cache[domain]

        # Validate domain format
        if not self._is_valid_domain(domain):
            result = (False, f"Invalid domain format: {domain}")
            self._cache[domain] = result
            return result

        # Normalize domain (lowercase, remove www)
        normalized_domain = self._normalize_domain(domain)

        # Check if reload is needed
        self._check_reload()

        # Security-first: Check deny list first
        if self._is_domain_denied(normalized_domain):
            result = (False, f"Domain explicitly denied: {normalized_domain}")
            self._cache[normalized_domain] = result
            return result

        # Check allow list
        if self._is_domain_allowed_explicit(normalized_domain):
            result = (True, f"Domain explicitly allowed: {normalized_domain}")
            self._cache[normalized_domain] = result
            return result

        # Apply default policy
        if self.default_policy == "deny":
            result = (False, "Domain not in allow list, default policy: deny")
        else:
            result = (True, "Domain not in deny list, default policy: allow")

        self._cache[normalized_domain] = result
        return result

    def reload_config(self) -> None:
        """Reload configuration from files."""
        try:
            # Clear cache on reload
            self._cache.clear()

            # Load allow list
            self.allow_domains, self.allow_wildcards = self._parse_domain_file(
                self.allow_file
            )
            logger.info(
                f"Loaded {len(self.allow_domains)} allow domains, {len(self.allow_wildcards)} allow wildcards"
            )

            # Load deny list
            self.deny_domains, self.deny_wildcards = self._parse_domain_file(
                self.deny_file
            )
            logger.info(
                f"Loaded {len(self.deny_domains)} deny domains, {len(self.deny_wildcards)} deny wildcards"
            )

            self.last_reload = time.time()

        except Exception as e:
            logger.error(f"Error reloading domain configuration: {e}")
            # Keep existing configuration on error

    def get_status(self) -> Dict[str, Any]:
        """Get current filter status and statistics."""
        return {
            "allow_domains_count": len(self.allow_domains),
            "deny_domains_count": len(self.deny_domains),
            "allow_wildcards_count": len(self.allow_wildcards),
            "deny_wildcards_count": len(self.deny_wildcards),
            "default_policy": self.default_policy,
            "last_reload": self.last_reload,
            "cache_size": len(self._cache),
            "allow_file_exists": self.allow_file.exists(),
            "deny_file_exists": self.deny_file.exists(),
        }

    def list_allowed_domains(self) -> Set[str]:
        """Get set of explicitly allowed domains."""
        return self.allow_domains.copy()

    def list_denied_domains(self) -> Set[str]:
        """Get set of explicitly denied domains."""
        return self.deny_domains.copy()

    def _is_valid_domain(self, domain: str) -> bool:
        """Validate domain format."""
        if not domain or len(domain) > 253:
            return False

        # Handle wildcard domains
        if domain.startswith("*."):
            # Remove wildcard prefix for validation
            domain = domain[2:]

        # Basic domain regex pattern
        pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
        return bool(re.match(pattern, domain))

    def _normalize_domain(self, domain: str) -> str:
        """Normalize domain (lowercase, remove www)."""
        domain = domain.lower().strip()

        # Remove www prefix if present
        if domain.startswith("www."):
            domain = domain[4:]

        return domain

    def _is_domain_denied(self, domain: str) -> bool:
        """Check if domain is explicitly denied."""
        # Check exact match
        if domain in self.deny_domains:
            return True

        # Check wildcard matches
        for wildcard in self.deny_wildcards:
            if self._matches_wildcard(domain, wildcard):
                return True

        return False

    def _is_domain_allowed_explicit(self, domain: str) -> bool:
        """Check if domain is explicitly allowed."""
        # Check exact match
        if domain in self.allow_domains:
            return True

        # Check wildcard matches
        for wildcard in self.allow_wildcards:
            if self._matches_wildcard(domain, wildcard):
                return True

        return False

    def _matches_wildcard(self, domain: str, wildcard: str) -> bool:
        """Check if domain matches wildcard pattern."""
        if not wildcard.startswith("*."):
            return False

        # Extract base domain from wildcard
        base_domain = wildcard[2:]  # Remove "*. "

        # Check if domain ends with base domain
        if domain == base_domain:
            return True

        # Check subdomain matches
        if domain.endswith("." + base_domain):
            return True

        return False

    def _parse_domain_file(self, filepath: Path) -> Tuple[Set[str], Set[str]]:
        """Parse domain file and return (exact_domains, wildcard_domains)."""
        exact_domains = set()
        wildcard_domains = set()

        if not filepath.exists():
            logger.warning(f"Domain file not found: {filepath}")
            return exact_domains, wildcard_domains

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Validate domain format
                    if not self._is_valid_domain(line):
                        logger.warning(
                            f"Invalid domain in {filepath}:{line_num}: {line}"
                        )
                        continue

                    # Categorize as exact or wildcard
                    if line.startswith("*."):
                        wildcard_domains.add(line)
                    else:
                        exact_domains.add(line)

        except Exception as e:
            logger.error(f"Error reading domain file {filepath}: {e}")

        return exact_domains, wildcard_domains

    def _check_reload(self) -> None:
        """Check if configuration should be reloaded."""
        if time.time() - self.last_reload > self.reload_interval:
            self.reload_config()


# Global instance for singleton pattern
_domain_filter: Optional[DomainFilter] = None


def get_domain_filter() -> DomainFilter:
    """Get global domain filter instance."""
    global _domain_filter
    if _domain_filter is None:
        _domain_filter = DomainFilter()
    return _domain_filter


def is_domain_allowed(domain: str) -> Tuple[bool, str]:
    """Convenience function to check if domain is allowed."""
    return get_domain_filter().is_domain_allowed(domain)


def reload_domain_config() -> None:
    """Convenience function to reload domain configuration."""
    get_domain_filter().reload_config()
