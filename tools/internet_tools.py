"""
Internet Tools Module for iKOMA

Provides safe internet access tools with domain filtering integration.
Part of Epic E-01: Internet Tooling.
"""

from langchain.tools import tool

from .domain_filter import get_domain_filter, is_domain_allowed, reload_domain_config


@tool
def check_domain_allowed(domain: str) -> str:
    """
    Check if a domain is allowed based on the current domain filter configuration.

    Args:
        domain: The domain to check (e.g., "example.com", "blog.example.com")

    Returns:
        String indicating whether the domain is allowed and the reason
    """
    try:
        is_allowed, reason = is_domain_allowed(domain)
        status = "ALLOWED" if is_allowed else "DENIED"
        return f"Domain '{domain}': {status} - {reason}"
    except Exception as e:
        return f"Error checking domain '{domain}': {str(e)}"


@tool
def get_domain_filter_status() -> str:
    """
    Get the current status and statistics of the domain filter.

    Returns:
        String with domain filter status information
    """
    try:
        filter_instance = get_domain_filter()
        status = filter_instance.get_status()

        result = "Domain Filter Status:\n"
        result += f"- Allow domains: {status['allow_domains_count']}\n"
        result += f"- Deny domains: {status['deny_domains_count']}\n"
        result += f"- Allow wildcards: {status['allow_wildcards_count']}\n"
        result += f"- Deny wildcards: {status['deny_wildcards_count']}\n"
        result += f"- Default policy: {status['default_policy']}\n"
        result += f"- Cache size: {status['cache_size']}\n"
        result += f"- Allow file exists: {status['allow_file_exists']}\n"
        result += f"- Deny file exists: {status['deny_file_exists']}\n"

        return result
    except Exception as e:
        return f"Error getting domain filter status: {str(e)}"


@tool
def list_allowed_domains() -> str:
    """
    List all explicitly allowed domains from the domain filter.

    Returns:
        String with list of allowed domains
    """
    try:
        filter_instance = get_domain_filter()
        allowed_domains = filter_instance.list_allowed_domains()

        if not allowed_domains:
            return "No domains are explicitly allowed."

        result = "Explicitly Allowed Domains:\n"
        for domain in sorted(allowed_domains):
            result += f"- {domain}\n"

        return result
    except Exception as e:
        return f"Error listing allowed domains: {str(e)}"


@tool
def list_denied_domains() -> str:
    """
    List all explicitly denied domains from the domain filter.

    Returns:
        String with list of denied domains
    """
    try:
        filter_instance = get_domain_filter()
        denied_domains = filter_instance.list_denied_domains()

        if not denied_domains:
            return "No domains are explicitly denied."

        result = "Explicitly Denied Domains:\n"
        for domain in sorted(denied_domains):
            result += f"- {domain}\n"

        return result
    except Exception as e:
        return f"Error listing denied domains: {str(e)}"


@tool
def reload_domain_filter_config() -> str:
    """
    Reload the domain filter configuration from files.

    Returns:
        String indicating the result of the reload operation
    """
    try:
        reload_domain_config()
        return "Domain filter configuration reloaded successfully."
    except Exception as e:
        return f"Error reloading domain filter configuration: {str(e)}"


@tool
def validate_url_for_access(url: str) -> str:
    """
    Validate a URL to check if its domain is allowed for internet access.

    Args:
        url: The URL to validate (e.g., "https://example.com/page")

    Returns:
        String indicating whether the URL's domain is allowed
    """
    try:
        from urllib.parse import urlparse

        # Parse the URL to extract the domain
        parsed = urlparse(url)
        domain = parsed.netloc

        if not domain:
            return f"Invalid URL format: {url}"

        # Check if domain is allowed
        is_allowed, reason = is_domain_allowed(domain)
        status = "ALLOWED" if is_allowed else "DENIED"

        return f"URL '{url}' domain '{domain}': {status} - {reason}"
    except Exception as e:
        return f"Error validating URL '{url}': {str(e)}"


# Utility function for other modules to use
def is_url_allowed(url: str) -> tuple[bool, str]:
    """
    Check if a URL's domain is allowed (for use by other modules).

    Args:
        url: The URL to check

    Returns:
        Tuple of (is_allowed: bool, reason: str)
    """
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc

        if not domain:
            return False, "Invalid URL format"

        return is_domain_allowed(domain)
    except Exception as e:
        return False, f"Error parsing URL: {str(e)}"
