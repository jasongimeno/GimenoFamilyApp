from fastapi.templating import Jinja2Templates
import logging
from app.utils.url_helper import static_url as static_url_func
from app.utils.url_helper import ensure_https_url as ensure_https_url_func

logger = logging.getLogger(__name__)

# Create and configure the templates instance
templates = Jinja2Templates(directory="app/templates")

# Define template filter functions
def template_static_url(path):
    """Template filter to generate URLs for static assets"""
    return static_url_func(path)

def template_secure_url(url):
    """Template filter to ensure URLs are secure in production"""
    return ensure_https_url_func(url)

# Register template filters
templates.env.filters["static_url"] = template_static_url
templates.env.filters["secure_url"] = template_secure_url

logger.info("Template filters registered: static_url, secure_url") 