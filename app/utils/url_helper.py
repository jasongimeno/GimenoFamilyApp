from fastapi import Request
import os
from urllib.parse import urlparse, urlunparse
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def get_base_url(request=None) -> str:
    """
    Get the base URL for the application based on environment settings.
    
    In production, this will always use HTTPS.
    In development, it will use the request scheme or HTTP as fallback.
    
    Returns:
        str: The base URL (e.g., https://example.com)
    """
    # Get the host from environment variables with fallbacks
    host = os.getenv("APP_HOST", settings.APP_HOST)
    
    # Determine scheme based on environment
    if settings.ENVIRONMENT == "production":
        scheme = "https"
    else:
        # In development, use the request scheme if available
        scheme = request.url.scheme if request else "http"
    
    return f"{scheme}://{host}"

def ensure_https_url(url: str) -> str:
    """
    Ensure a URL uses HTTPS in production.
    
    Args:
        url (str): The URL to check and potentially modify
        
    Returns:
        str: The URL with https:// in production, or unchanged in development
    """
    if not url:
        return url
        
    if settings.ENVIRONMENT != "production":
        return url
        
    parsed = urlparse(url)
    if parsed.scheme == "http":
        # Replace http with https and reconstruct the URL
        parts = list(parsed)
        parts[0] = "https"
        return urlunparse(parts)
    
    return url

def make_absolute_url(path: str, request=None) -> str:
    """
    Convert a relative path to an absolute URL.
    
    Args:
        path (str): The relative path (e.g., /api/endpoint)
        request (Request, optional): The current request object
        
    Returns:
        str: The absolute URL (e.g., https://example.com/api/endpoint)
    """
    if path.startswith(("http://", "https://")):
        # Already an absolute URL, just ensure HTTPS in production
        return ensure_https_url(path)
    
    # Make sure path starts with a slash
    if not path.startswith("/"):
        path = f"/{path}"
    
    base_url = get_base_url(request)
    return f"{base_url}{path}"

def static_url(path: str, request=None) -> str:
    """
    Generate a URL for a static asset.
    
    Args:
        path (str): The path to the static asset (e.g., /js/app.js)
        request (Request, optional): The current request object
        
    Returns:
        str: The absolute URL to the static asset in production,
             or a relative URL in development
    """
    # Make sure path doesn't start with a slash for joining
    if path.startswith("/"):
        path = path[1:]
    
    # In development, use relative URLs for better local testing
    if settings.ENVIRONMENT != "production":
        return f"/static/{path}"
    
    # In production, use absolute URLs with HTTPS
    return make_absolute_url(f"/static/{path}", request) 