from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from pathlib import Path
import logging
from app.utils.template_helpers import templates

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Pages"])

def get_template_context(request: Request):
    """
    Get the base context for all templates, including filter information
    """
    try:
        # Create a base context with request and filter information
        filters = list(templates.env.filters.keys())
        logger.debug(f"Template filters available: {filters}")
        
        context = {
            "request": request,
            "filters": filters
        }
        
        logger.debug(f"Template context prepared with filters: {filters}")
        return context
    except Exception as e:
        # Fallback context with just request - minimal viable context
        logger.error(f"Error preparing template context: {str(e)}")
        return {"request": request}

@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """
    Serve the home page
    """
    context = get_template_context(request)
    return templates.TemplateResponse("index.html", context)

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Serve the login page
    """
    context = get_template_context(request)
    return templates.TemplateResponse("login.html", context)

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """
    Serve the registration page
    """
    context = get_template_context(request)
    return templates.TemplateResponse("register.html", context)

@router.get("/checklists", response_class=HTMLResponse)
async def checklists_page(request: Request):
    """
    Serve the checklists page
    """
    context = get_template_context(request)
    return templates.TemplateResponse("checklists.html", context)

@router.get("/carpool", response_class=HTMLResponse)
async def carpool_page(request: Request):
    """
    Serve the carpool management page
    """
    context = get_template_context(request)
    return templates.TemplateResponse("carpool.html", context)

@router.get("/meals", response_class=HTMLResponse)
async def meals_page(request: Request):
    """
    Serve the meal planning page
    """
    context = get_template_context(request)
    return templates.TemplateResponse("meals.html", context) 