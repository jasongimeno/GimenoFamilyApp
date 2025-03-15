from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
import logging

from app.api.auth import router as auth_router
from app.api.checklists import router as checklists_router
from app.api.carpool import router as carpool_router
from app.api.meals import router as meals_router
from app.api.pages import router as pages_router
from app.db.database import Base, engine
from app.core.config import ENVIRONMENT, ENABLE_ELASTICSEARCH, ENABLE_SEARCH
from app.utils.elastic import setup_elasticsearch_indices
from app.utils.azure_search import setup_azure_search_indices

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
logger.info("Creating database tables...")
Base.metadata.create_all(bind=engine)

# Initialize search indices
if ENABLE_ELASTICSEARCH:
    logger.info("Setting up Elasticsearch indices (legacy mode)...")
    setup_elasticsearch_indices()

if ENABLE_SEARCH:
    logger.info("Setting up Azure Cognitive Search indices...")
    setup_azure_search_indices()

# Create FastAPI app
app = FastAPI(
    title="Family Management Solution",
    description="Web application for family organizational tools",
    version="1.0.0"
)

# CORS middleware
origins = ["*"]
if ENVIRONMENT == "prod":
    # In production, specify the actual origin
    origins = ["https://yourdomain.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Template engine
templates = Jinja2Templates(directory="app/templates")

# Include routers
app.include_router(auth_router)
app.include_router(checklists_router)
app.include_router(carpool_router)
app.include_router(meals_router)
app.include_router(pages_router)

# Remove the default root endpoint since we have a pages router now
# @app.get("/")
# async def root():
#     return {"message": "Welcome to Family Management Solution API"}

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting application in {ENVIRONMENT} environment")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 