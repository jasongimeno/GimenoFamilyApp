from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(tags=["Pages"])

@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """
    Serve the home page
    """
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Serve the login page
    """
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """
    Serve the registration page
    """
    return templates.TemplateResponse("register.html", {"request": request})

@router.get("/checklists", response_class=HTMLResponse)
async def checklists_page(request: Request):
    """
    Serve the checklists page
    """
    return templates.TemplateResponse("checklists.html", {"request": request})

@router.get("/carpool", response_class=HTMLResponse)
async def carpool_page(request: Request):
    """
    Serve the carpool management page
    """
    return templates.TemplateResponse("carpool.html", {"request": request})

@router.get("/meals", response_class=HTMLResponse)
async def meals_page(request: Request):
    """
    Serve the meal planning page
    """
    return templates.TemplateResponse("meals.html", {"request": request}) 