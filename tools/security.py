# mypy: disable-error-code=unreachable

"""
Security utilities for citation system.
Implements OWASP-compliant sanitization and validation.
"""

import re
from typing import Any
from urllib.parse import urlparse

from markupsafe import escape


def sanitize_citation_url(url: str) -> str | None:
    """
    OWASP-compliant URL sanitization for citations.
    Args:
        url: The URL to sanitize
    Returns:
        Sanitized URL or None if invalid
    Raises:
        ValueError: If URL is malformed or contains dangerous content
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")

    if len(url) > 2000:
        raise ValueError("URL too long (max 2000 characters)")

    # Remove dangerous protocols
    dangerous_protocols = ["javascript:", "data:", "vbscript:", "file:"]
    url_lower = url.lower()
    for protocol in dangerous_protocols:
        if url_lower.startswith(protocol):
            raise ValueError(f"Dangerous protocol detected: {protocol}")

    # Validate URL structure
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ["http", "https"]:
            raise ValueError("Only HTTP and HTTPS protocols are allowed")

        if not parsed.netloc:
            raise ValueError("URL must have a valid domain")

        # Basic domain validation (prevent localhost, private IPs in production)
        netloc = parsed.netloc.lower()
        if netloc in ["localhost", "127.0.0.1", "::1"]:
            raise ValueError("Localhost URLs are not allowed")

    except Exception as e:
        raise ValueError(f"Malformed URL: {e}") from e

    return url


def sanitize_citation_title(title: str) -> str:
    """
    Sanitize citation title to prevent XSS.
    Args:
        title: The title to sanitize
    Returns:
        Sanitized title
    """
    if not title:
        return "Untitled"

    if not isinstance(title, str):
        title = str(title)

    # Remove HTML tags and dangerous content
    title = re.sub(r"<[^>]*>", "", title)
    title = re.sub(r"javascript:", "", title, flags=re.IGNORECASE)
    title = re.sub(r"data:", "", title, flags=re.IGNORECASE)

    # Limit length
    if len(title) > 500:
        title = title[:497] + "..."

    return escape(title.strip())


def validate_citation_metadata(metadata: dict) -> dict:
    """
    Validate and sanitize citation metadata.
    Args:
        metadata: Citation metadata dictionary
    Returns:
        Validated and sanitized metadata
    Raises:
        ValueError: If metadata is invalid
    """
    if not isinstance(metadata, dict):
        raise ValueError("Metadata must be a dictionary")

    validated: dict[str, Any] = {}

    # Validate required fields
    required_fields = ["url", "title"]
    for field in required_fields:
        if field not in metadata:
            raise ValueError(f"Missing required field: {field}")

    # Sanitize URL
    validated["url"] = sanitize_citation_url(metadata["url"])

    # Sanitize title
    validated["title"] = sanitize_citation_title(metadata["title"])

    # Validate optional fields
    if "domain" in metadata:
        domain = str(metadata["domain"]).strip()
        if len(domain) > 100:
            domain = domain[:97] + "..."
        validated["domain"] = escape(domain)

    if "content_preview" in metadata:
        preview = str(metadata["content_preview"])
        if len(preview) > 1000:
            preview = preview[:997] + "..."
        validated["content_preview"] = escape(preview)

    if "confidence_score" in metadata:
        try:
            score = float(metadata["confidence_score"])
            if not 0 <= score <= 1:
                raise ValueError("Confidence score must be between 0 and 1")
            validated["confidence_score"] = score
        except (ValueError, TypeError):
            validated["confidence_score"] = 0.5  # Default fallback
    else:
        validated["confidence_score"] = 0.5

    if "source_type" in metadata:
        source_type = str(metadata["source_type"]).strip()
        if len(source_type) > 50:
            source_type = source_type[:47] + "..."
        validated["source_type"] = escape(source_type)

    return validated


def is_safe_citation_content(content: str) -> bool:
    """
    Check if citation content is safe for storage.
    Args:
        content: The content to check
    Returns:
        True if content is safe, False otherwise
    """
    if not content or not isinstance(content, str):
        return False

    # Check for dangerous patterns
    dangerous_patterns = [
        r"<script[^>]*>",
        r"javascript:",
        r"data:text/html",
        r"vbscript:",
        r"on\w+\s*=",
    ]

    content_lower = content.lower()
    for pattern in dangerous_patterns:
        if re.search(pattern, content_lower):
            return False

    # Check content length
    if len(content) > 10000:  # 10KB limit
        return False

    return True


def sanitize_citation_content(content: str) -> str:
    """
    Sanitize citation content for safe storage.
    Args:
        content: The content to sanitize
    Returns:
        Sanitized content
    """
    if not content:
        return ""

    if not isinstance(content, str):
        content = str(content)

    # Remove dangerous HTML
    content = re.sub(
        r"<script[^>]*>.*?</script>", "", content, flags=re.IGNORECASE | re.DOTALL
    )
    content = re.sub(
        r"<iframe[^>]*>.*?</iframe>", "", content, flags=re.IGNORECASE | re.DOTALL
    )
    content = re.sub(
        r"<object[^>]*>.*?</object>", "", content, flags=re.IGNORECASE | re.DOTALL
    )

    # Remove event handlers
    content = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', "", content, flags=re.IGNORECASE)

    # Remove dangerous protocols
    content = re.sub(r"javascript:", "", content, flags=re.IGNORECASE)
    content = re.sub(r"data:", "", content, flags=re.IGNORECASE)
    content = re.sub(r"vbscript:", "", content, flags=re.IGNORECASE)

    # Limit length
    if len(content) > 10000:
        content = content[:9997] + "..."

    return escape(content.strip())
