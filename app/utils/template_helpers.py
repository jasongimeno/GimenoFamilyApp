from fastapi.templating import Jinja2Templates
import logging
import os
from app.utils.url_helper import static_url as static_url_func
from app.utils.url_helper import ensure_https_url as ensure_https_url_func

logger = logging.getLogger(__name__)

# Create and configure the templates instance
templates = Jinja2Templates(directory="app/templates")

# Define template filter functions
def template_static_url(path):
    """Template filter to generate URLs for static assets"""
    try:
        return static_url_func(path)
    except Exception as e:
        logger.error(f"Error in static_url filter: {str(e)}")
        # Fallback to basic path
        if path.startswith('/'):
            return f"/static{path}"
        return f"/static/{path}"

def template_secure_url(url):
    """Template filter to ensure URLs are secure in production"""
    try:
        return ensure_https_url_func(url)
    except Exception as e:
        logger.error(f"Error in secure_url filter: {str(e)}")
        # Fallback to original URL
        return url

try:
    # Register template filters with error handling
    templates.env.filters["static_url"] = template_static_url
    templates.env.filters["secure_url"] = template_secure_url
    logger.info("Template filters registered: static_url, secure_url")
except Exception as e:
    logger.error(f"Failed to register template filters: {str(e)}")

# Register a basic filter to check if filters exist (for templates)
templates.env.globals['has_filter'] = lambda name: name in templates.env.filters 