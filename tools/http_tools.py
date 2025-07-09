"""
HTTP Tools Module for iKOMA

Provides rate-limited HTTP request tools with domain filtering integration.
Part of Epic E-01: Internet Tooling - Issue #5.
"""

from typing import Dict, Optional
from langchain.tools import tool
from .http_client import get_http_client, RateLimitConfig


@tool
def make_http_request(url: str, method: str = "GET", headers: str = "", use_cache: bool = True) -> str:
    """
    Make a rate-limited HTTP request with domain filtering and safety checks.
    
    Args:
        url: The URL to request (e.g., "https://example.com/api/data")
        method: HTTP method (GET, POST, etc.) - defaults to GET
        headers: Optional JSON string of headers to include
        use_cache: Whether to use cached responses (default: True)
        
    Returns:
        String with response data or error information
    """
    try:
        # Parse headers if provided
        request_headers: Optional[Dict[str, str]] = None
        if headers.strip():
            import json
            request_headers = json.loads(headers)
        
        # Get HTTP client
        client = get_http_client()
        
        # Make request
        if method.upper() == "GET":
            response = client.get(url, headers=request_headers, use_cache=use_cache)
        elif method.upper() == "POST":
            response = client.post(url, headers=request_headers)
        else:
            return f"Error: Unsupported HTTP method '{method}'. Only GET and POST are supported."
        
        # Format response
        if response["success"]:
            result = "✅ Request successful\n"
            result += f"URL: {response['url']}\n"
            result += f"Method: {response['method']}\n"
            result += f"Status: {response['status_code']}\n"
            result += f"Content Length: {response['content_length']} bytes\n"
            result += f"Cached: {'Yes' if response.get('cached', False) else 'No'}\n"
            result += f"Domain: {response['domain']}\n"
            result += f"Timestamp: {response['timestamp']}\n\n"
            
            # Include content (truncated if too long)
            content = response['content']
            if len(content) > 2000:
                result += f"Content (truncated):\n{content[:2000]}...\n[Content truncated - {len(content)} total characters]"
            else:
                result += f"Content:\n{content}"
            
            return result
        else:
            return f"❌ Request failed\nURL: {response['url']}\nError: {response['error']}\nTimestamp: {response['timestamp']}"
            
    except Exception as e:
        return f"❌ Error making HTTP request: {str(e)}"


@tool
def get_http_client_stats() -> str:
    """
    Get comprehensive statistics about HTTP client usage and rate limiting.
    
    Returns:
        String with detailed HTTP client statistics
    """
    try:
        client = get_http_client()
        stats = client.get_stats()
        
        result = "📊 HTTP Client Statistics\n"
        result += f"Total Domains: {stats['total_domains']}\n"
        result += f"Total Requests: {stats['total_requests']}\n"
        result += f"Rate Limit Hits: {stats['rate_limit_hits']}\n"
        result += f"Cache Files: {stats['cache_info']['cache_files']}\n"
        result += f"Cache Directory: {stats['cache_info']['cache_dir']}\n\n"
        
        # Configuration
        config = stats['config']
        result += "⚙️ Configuration:\n"
        result += f"- Requests per second: {config['default_rate_limit']['requests_per_second']}\n"
        result += f"- Bucket capacity: {config['default_rate_limit']['bucket_capacity']} tokens\n"
        result += f"- Backoff base: {config['default_rate_limit']['backoff_base']}s\n"
        result += f"- Backoff max: {config['default_rate_limit']['backoff_max']}s\n"
        result += f"- Timeout: {config['timeout']} seconds\n"
        result += f"- User agents: {config['user_agents_count']}\n\n"
        
        # Per-domain statistics
        if stats['domains']:
            result += "🌐 Domain Statistics:\n"
            for domain, domain_stats in stats['domains'].items():
                result += f"\n{domain}:\n"
                result += f"  - Total requests: {domain_stats['total_requests']}\n"
                result += f"  - Current tokens: {domain_stats['current_tokens']}\n"
                result += f"  - Rate limit hits: {domain_stats['rate_limit_hits']}\n"
                result += f"  - Backoff attempts: {domain_stats['backoff_attempts']}\n"
                if domain_stats['backoff_until']:
                    result += f"  - Backoff until: {domain_stats['backoff_until']}\n"
                if domain_stats['last_request']:
                    result += f"  - Last request: {domain_stats['last_request']}\n"
        else:
            result += "🌐 No domain statistics available\n"
        
        return result
        
    except Exception as e:
        return f"❌ Error getting HTTP client stats: {str(e)}"


@tool
def set_domain_rate_limit(domain: str, requests_per_second: float = 5.0, bucket_capacity: int = 10, backoff_base: float = 1.0) -> str:
    """
    Set custom rate limit configuration for a specific domain using token bucket algorithm.
    
    Args:
        domain: The domain to configure (e.g., "api.example.com")
        requests_per_second: Token bucket refill rate (default: 5.0 req/s)
        bucket_capacity: Maximum tokens in bucket (default: 10)
        backoff_base: Base backoff time for 429/503 responses (default: 1.0 seconds)
        
    Returns:
        String indicating the result of the configuration
    """
    try:
        client = get_http_client()
        
        # Create rate limit configuration
        config = RateLimitConfig(
            requests_per_second=requests_per_second,
            bucket_capacity=bucket_capacity,
            backoff_base=backoff_base
        )
        
        # Set the configuration
        client.set_domain_rate_limit(domain, config)
        
        return f"✅ Rate limit configured for '{domain}':\n" \
               f"- Requests per second: {requests_per_second}\n" \
               f"- Bucket capacity: {bucket_capacity} tokens\n" \
               f"- Backoff base: {backoff_base} seconds"
               
    except Exception as e:
        return f"❌ Error setting rate limit for '{domain}': {str(e)}"


@tool
def clear_http_cache() -> str:
    """
    Clear all cached HTTP responses.
    
    Returns:
        String indicating the result of the cache clearing operation
    """
    try:
        client = get_http_client()
        result = client.clear_cache()
        return f"✅ {result}"
    except Exception as e:
        return f"❌ Error clearing HTTP cache: {str(e)}"


@tool
def reset_http_stats() -> str:
    """
    Reset all HTTP client request statistics.
    
    Returns:
        String indicating the result of the reset operation
    """
    try:
        client = get_http_client()
        result = client.reset_stats()
        return f"✅ {result}"
    except Exception as e:
        return f"❌ Error resetting HTTP stats: {str(e)}"


@tool
def test_http_connection(url: str = "https://httpbin.org/get") -> str:
    """
    Test HTTP connectivity with a simple request to verify the client is working.
    
    Args:
        url: URL to test (default: httpbin.org)
        
    Returns:
        String with test results
    """
    try:
        client = get_http_client()
        response = client.get(url, use_cache=False)
        
        if response["success"]:
            return f"✅ HTTP connection test successful\n" \
                   f"URL: {response['url']}\n" \
                   f"Status: {response['status_code']}\n" \
                   f"Content Length: {response['content_length']} bytes\n" \
                   f"Domain: {response['domain']}"
        else:
            return f"❌ HTTP connection test failed\n" \
                   f"URL: {response['url']}\n" \
                   f"Error: {response['error']}"
                   
    except Exception as e:
        return f"❌ HTTP connection test error: {str(e)}" 