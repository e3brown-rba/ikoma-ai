# mypy: disable-error-code=index
"""
Enhanced Web Tools Module for iKOMA

Provides high-quality web content extraction with security validation and ChromaDB storage.
Implements OWASP-compliant security, trafilatura-based extraction, and quality assessment.
Part of Epic E-01: Internet Tooling - Issue #6.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any

import requests
from langchain.tools import tool

from .citation_manager import CitationSource
from .content_extractor import get_content_extractor
from .vector_store import get_vector_store, store_citation_with_metadata
from .web_security import enforce_web_rate_limit, get_web_filter, validate_web_url

# Global instances for performance
_web_filter = get_web_filter()
_content_extractor = get_content_extractor()


@tool
def extract_web_content(url_and_options: str) -> str:
    """Extract and store high-quality web content with security validation.
    Format: 'url|||chunk_size|||store_in_memory|||min_quality'"""

    parts = url_and_options.split("|||")
    url = parts[0].strip()
    chunk_size = int(parts[1]) if len(parts) > 1 and parts[1].strip() else 1000
    store_in_memory = parts[2].lower() == "true" if len(parts) > 2 else True
    min_quality = float(parts[3]) if len(parts) > 3 and parts[3].strip() else 0.6

    try:
        # Security validation
        validate_web_url(url)
        domain = url.split("/")[2] if "/" in url else url
        enforce_web_rate_limit(domain)

        # Fetch content with safety limits
        headers = {
            "User-Agent": "iKOMA/2.0 AI Assistant",
            "Accept": "text/html,application/xhtml+xml",
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=10,
            allow_redirects=False,  # Prevent redirect-based bypasses
            stream=True,
        )
        response.raise_for_status()

        # Size validation
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) > _web_filter.config.max_content_size:
            return f"Error: Content too large ({content_length} bytes)"

        html_content = response.text
        if len(html_content) > _web_filter.config.max_content_size:
            return f"Error: Content too large ({len(html_content)} bytes)"

        # Extract and assess content
        extracted = _content_extractor.extract_content(url, html_content, chunk_size)

        # Quality gate
        if extracted.quality_score < min_quality:
            return f"Content quality too low: {extracted.quality_score:.2f} < {min_quality} (extracted via {extracted.extraction_method})"

        # Store in ChromaDB if requested
        citation_id = None
        if store_in_memory:
            store = get_vector_store()
            namespace = ("web_content", "default")  # Separate collection

            for i, chunk in enumerate(extracted.text_chunks):
                memory_id = f"{uuid.uuid4()}_{i}"
                memory_entry = {
                    "content": chunk,
                    "url": extracted.url,
                    "title": extracted.title,
                    "chunk_index": i,
                    "total_chunks": len(extracted.text_chunks),
                    "quality_score": extracted.quality_score,
                    "readability_score": extracted.readability_score,
                    "extraction_method": extracted.extraction_method,
                    "domain": extracted.metadata["domain"],
                    "timestamp": extracted.timestamp,
                    "content_type": "web_content",
                }
                store.put(namespace, memory_id, memory_entry)

            # Register citation for the extraction (first chunk as canonical)
            citation = CitationSource(
                id=uuid.uuid4().int % 10**8,  # 8-digit int for display
                url=extracted.url,
                title=extracted.title or "Untitled Web Page",
                timestamp=extracted.timestamp,
                domain=extracted.metadata["domain"],
                confidence_score=extracted.quality_score,
                content_preview=extracted.text_chunks[0][:200] if extracted.text_chunks else "",
                source_type="web",
            )
            store_citation_with_metadata(citation, extracted.text_chunks[0] if extracted.text_chunks else "")
            citation_id = citation.id

        # Success response with quality metrics and citation ID
        return f"""🔍 **Web Content Extraction Results**

📊 Quality Metrics:
• Overall Score: {extracted.quality_score:.2f}/1.0
• Readability: {extracted.readability_score:.2f}/1.0
• Method: {extracted.extraction_method}
• Chunks: {len(extracted.text_chunks)}

📝 Preview: {extracted.text_chunks[0][:200]}...

🔗 Citation ID: [[{citation_id}]]"""

    except ValueError as e:
        return f"❌ Security validation failed: {e}"
    except requests.RequestException as e:
        return f"❌ Network error: {e}"
    except Exception as e:
        return f"❌ Content extraction error: {e}"


@tool
def search_web_memories(query_and_filters: str) -> str:
    """Search stored web content with quality and domain filtering.
    Format: 'query|||min_quality|||domain_filter|||max_results'"""

    parts = query_and_filters.split("|||")
    query = parts[0].strip()
    min_quality = float(parts[1]) if len(parts) > 1 and parts[1].strip() else 0.6
    domain_filter = parts[2].strip() if len(parts) > 2 and parts[2].strip() else None
    max_results = int(parts[3]) if len(parts) > 3 and parts[3].strip() else 5

    try:
        store = get_vector_store()
        namespace = ("web_content", "default")

        # Search with quality filtering
        search_results = store.search(namespace, query=query, limit=max_results * 2)
        memories: list[dict[str, Any]] = []

        # Convert search results to list with proper typing
        if hasattr(search_results, "__iter__"):
            try:
                memories = list(search_results)
            except (TypeError, ValueError):
                memories = []
        else:
            memories = []

        # Apply filters
        filtered_results = []
        for memory in memories:
            if isinstance(memory, dict):
                content = memory
            # No else/continue needed

            # Quality filter
            if content.get("quality_score", 0) < min_quality:
                continue

            # Domain filter
            if (
                domain_filter
                and domain_filter.lower() not in content.get("domain", "").lower()
            ):
                continue

            filtered_results.append(content)
            if len(filtered_results) >= max_results:
                break

        if not filtered_results:
            return f"No web content found for '{query}' (min quality: {min_quality})"

        # Format results
        results = []
        for content in filtered_results:
            results.append(
                f"📄 {content.get('title', 'Untitled')}\n"
                f"🔗 {content.get('url', 'Unknown URL')}\n"
                f"⭐ Quality: {content.get('quality_score', 0):.2f}"
                f"\n📝 {content.get('content', '')[:150]}..."
            )

        return f"🔍 Found {len(results)} high-quality results:\n\n" + "\n\n".join(
            results
        )

    except Exception as e:
        return f"❌ Search error: {e}"


@tool
def get_web_extraction_status() -> str:
    """Get the current status of web content extraction functionality."""

    status = {
        "security_filter": _web_filter.get_status(),
        "content_extractor": {
            "min_quality_score": _content_extractor.min_quality_score,
            "trafilatura_available": hasattr(_content_extractor, "trafilatura_config")
            and _content_extractor.trafilatura_config is not None,
        },
        "vector_store": "available",  # Assuming it's available if we can import it
    }

    result = "Web Content Extraction Status:\n"
    result += f"- Security filter: {status['security_filter']['allowed_domains_count']} allowed domains\n"
    result += f"- Content extractor: min quality {status['content_extractor']['min_quality_score']}\n"
    result += f"- Vector store: {status['vector_store']}\n"
    result += f"- Trafilatura available: {status['content_extractor']['trafilatura_available']}\n"

    return result


# Legacy search function for backward compatibility
@tool
def search_web(query: str) -> str:
    """
    Search the web using SerpAPI and return top-5 results with titles and URLs.
    (Legacy function - consider using extract_web_content for better results)

    Args:
        query: Search query string

    Returns:
        JSON string with search results including titles, URLs, and snippets
    """
    # Check if search is enabled
    if not os.getenv("SEARCH_ENABLED", "false").lower() == "true":
        return (
            "Web search is disabled. Enable with SEARCH_ENABLED=true in your .env file."
        )

    # Check for API key
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return "SerpAPI key not configured. Set SERPAPI_API_KEY in your .env file."

    try:
        # Import SerpAPI client (lazy import to avoid dependency issues)
        try:
            from serpapi import GoogleSearch
        except ImportError:
            return (
                "SerpAPI client not installed. Run: pip install google-search-results"
            )

        # Perform search with safety settings
        search = GoogleSearch(
            {
                "q": query,
                "api_key": api_key,
                "num": 5,  # Top 5 results
                "safe": "active",  # Safe search enabled
                "gl": "us",  # Geographic location (can be made configurable)
                "hl": "en",  # Language (can be made configurable)
            }
        )

        results = search.get_dict()

        # Extract organic results
        organic_results = results.get("organic_results", [])

        if not organic_results:
            return f"No search results found for query: '{query}'"

        # Format results for easy consumption
        formatted_results: dict[str, Any] = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "total_results": len(organic_results),
            "results": [],
        }

        for i, result in enumerate(organic_results[:5], 1):
            formatted_results["results"].append(
                {
                    "rank": i,
                    "title": result.get("title", ""),
                    "url": result.get("link", ""),
                    "snippet": result.get("snippet", ""),
                    "displayed_link": result.get("displayed_link", ""),
                }
            )

        # Return formatted JSON string
        return json.dumps(formatted_results, indent=2)

    except Exception as e:
        return f"Search failed: {str(e)}"
