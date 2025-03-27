import os
import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import sys

# Import config
from app.core.config import settings, ENVIRONMENT

# Import middleware
from app.middleware.security import SecurityMiddleware

# Import routers
from app.api.auth import router as auth_router
from app.api.meals import router as meals_router
from app.api.checklists import router as checklists_router
from app.api.carpool import router as carpool_router
from app.api.pages import router as pages_router
from app.api.diagnostics import router as diagnostics_router
from app.api.meal_planning import router as meal_planning_router

# Import centralized templates
from app.utils.template_helpers import templates

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.ENVIRONMENT != "production" else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app.log")
    ]
)

# Create specific loggers for key components
db_logger = logging.getLogger("app.db")
api_logger = logging.getLogger("app.api")
auth_logger = logging.getLogger("app.auth")

# Set more verbose logging in development
if settings.ENVIRONMENT != "production":
    db_logger.setLevel(logging.DEBUG)
    api_logger.setLevel(logging.DEBUG)
    auth_logger.setLevel(logging.DEBUG)
else:
    db_logger.setLevel(logging.INFO)
    api_logger.setLevel(logging.INFO)
    auth_logger.setLevel(logging.INFO)

logger = logging.getLogger("main")
logger.info(f"Starting application in {settings.ENVIRONMENT} environment")

# Create FastAPI app
app = FastAPI()

# Add security middleware - THIS IS THE NEW ADDITION
app.add_middleware(SecurityMiddleware)

# Add CORS middleware - wide open for testing in Azure/troubleshooting
# This allows any origin to access the API for debugging purposes
# TODO: Restrict to specific origins after troubleshooting
origins = ["*"]
logger.info(f"CORS setup with origins: {origins} in {settings.ENVIRONMENT} environment")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows all origins for troubleshooting
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
    expose_headers=["*"],  # Expose all headers in response
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Template engine setup is now handled in app.utils.template_helpers

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Include routers
app.include_router(auth_router)
app.include_router(checklists_router)
app.include_router(meals_router)
app.include_router(carpool_router)
app.include_router(pages_router)
app.include_router(diagnostics_router, prefix="/api/diagnostics")
app.include_router(meal_planning_router, prefix="/api/meal-planning")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    error_msg = f"Unhandled exception: {str(exc)}"
    logger.error(error_msg, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "An internal server error occurred", "detail": str(exc)}
    )

# Set up Azure Search indices if enabled
if settings.ENABLE_SEARCH:
    from app.utils.azure_search import setup_azure_search_indices
    logger.info("Setting up Azure Search indices...")
    setup_azure_search_indices()
    logger.info("Azure Search indices setup complete")

if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.getenv("PORT", 8000))
    
    # Log startup information
    logger.info(f"Starting server on port {port}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    # Run with uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True) 