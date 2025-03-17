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
                # Allow scripts from self, inline, CDNs, and localhost (for local development viewing)
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net http://localhost:8000",
                # Allow styles from self, inline, CDNs, Google Fonts, and localhost
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net http://localhost:8000",
                # Allow images from any HTTPS source and localhost
                "img-src 'self' data: https: http://localhost:8000",
                # Allow fonts from Google and localhost
                "font-src 'self' https://fonts.gstatic.com http://localhost:8000",
                # Allow connections to self, Azure services, and localhost
                "connect-src 'self' https://*.azure-api.net https://*.azurewebsites.net http://localhost:8000",
                "upgrade-insecure-requests",  # Upgrade HTTP requests to HTTPS
                "block-all-mixed-content"     # Legacy directive for older browsers
            ]
            return "; ".join(directives)
        else:
            # In development, we're more permissive
            directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' http: https:",  # Allow any HTTP/HTTPS scripts
                "style-src 'self' 'unsafe-inline' http: https:",  # Allow any HTTP/HTTPS styles
                "img-src 'self' data: http: https:",  # Allow any HTTP/HTTPS images
                "font-src 'self' http: https:",  # Allow any HTTP/HTTPS fonts
                "connect-src 'self' http: https:"  # Allow connections to any origin for API calls
            ]
            return "; ".join(directives) 