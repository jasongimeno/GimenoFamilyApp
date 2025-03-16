import logging
import os
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.core.config import settings

logger = logging.getLogger(__name__)

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce HTTPS and set security headers
    
    This middleware:
    1. Redirects HTTP requests to HTTPS in production
    2. Sets Content Security Policy headers to prevent mixed content
    3. Sets other security headers like X-Content-Type-Options
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.environment = os.getenv("ENVIRONMENT", "development")
        logger.info(f"Security middleware initialized in {self.environment} environment")
    
    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            # Skip for static files and favicon to avoid unnecessary overhead or redirect loops
            if request.url.path.startswith("/static") or request.url.path == "/favicon.ico":
                return await call_next(request)
            
            # Redirect to HTTPS if in production and using HTTP
            if settings.ENVIRONMENT == "production" and request.url.scheme == "http":
                # Prevent redirect loops
                if "x-forwarded-proto" in request.headers and request.headers["x-forwarded-proto"] == "https":
                    logger.debug("Request appears to be HTTPS via proxy, skipping redirect")
                    response = await call_next(request)
                else:
                    https_url = str(request.url).replace("http://", "https://")
                    logger.info(f"Redirecting HTTP request to HTTPS: {https_url}")
                    return Response(
                        status_code=301,
                        headers={"Location": https_url}
                    )
            else:
                # Get the response for non-redirect scenarios
                response = await call_next(request)
            
            # Set security headers
            try:
                # Content Security Policy to prevent mixed content
                csp_value = self._get_csp_header()
                logger.debug(f"Setting CSP header: {csp_value}")
                response.headers["Content-Security-Policy"] = csp_value
                
                # Prevent browsers from interpreting files as a different MIME type
                response.headers["X-Content-Type-Options"] = "nosniff"
                
                # Disable browser's built-in XSS protection
                # (we use CSP instead, which is more effective)
                response.headers["X-XSS-Protection"] = "0"
                
                # Set HSTS header in production
                if settings.ENVIRONMENT == "production":
                    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            except Exception as e:
                logger.error(f"Error setting security headers: {str(e)}")
            
            return response
        except Exception as e:
            logger.error(f"Unhandled exception in security middleware: {str(e)}")
            # Fallback to original call
            return await call_next(request)
    
    def _get_csp_header(self) -> str:
        """Generate the Content Security Policy header value"""
        
        # In production, we want to be more strict
        if settings.ENVIRONMENT == "production":
            # Allow loading resources only from the same origin and trusted external sources
            directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",  # Allow CDNs
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",  # Allow Google Fonts and CDNs
                "img-src 'self' data: https:",  # Allow images from any HTTPS source
                "font-src 'self' https://fonts.gstatic.com",  # Allow Google Font files
                "connect-src 'self'",
                "upgrade-insecure-requests",  # Upgrade HTTP requests to HTTPS
                "block-all-mixed-content"     # Legacy directive for older browsers
            ]
            return "; ".join(directives)
        else:
            # In development, we're more permissive
            directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
                "img-src 'self' data: https:",
                "font-src 'self' https://fonts.gstatic.com",
                "connect-src 'self'"
            ]
            return "; ".join(directives) 