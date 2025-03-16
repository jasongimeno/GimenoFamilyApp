import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")  # dev, test, or prod

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"postgresql://postgres:postgres@localhost:5432/fms_{ENVIRONMENT}")

# Application URL settings
APP_HOST = os.getenv("APP_HOST", "localhost:8000")  # For production, set to your domain

# Search configuration
# Common setting to enable/disable search functionality
ENABLE_SEARCH = os.getenv("ENABLE_SEARCH", "true").lower() == "true"

# Elasticsearch (legacy) settings
ENABLE_ELASTICSEARCH = os.getenv("ENABLE_ELASTICSEARCH", "false").lower() == "true"
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
ELASTICSEARCH_API_KEY = os.getenv("ELASTICSEARCH_API_KEY", "")
ELASTICSEARCH_INDEX_PREFIX = f"fms-{ENVIRONMENT}"

# Azure Cognitive Search settings
SEARCH_SERVICE_NAME = os.getenv("SEARCH_SERVICE_NAME", "")
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY", "")
SEARCH_INDEX_PREFIX = f"fms-{ENVIRONMENT}"

# JWT Authentication
SECRET_KEY = os.getenv("SECRET_KEY", "development_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Email Configuration
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "noreply@familymanagement.app")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")

# Application Settings
APP_NAME = "Family Management Solution"
APP_VERSION = "1.0.0"

# Create a settings object for easier imports
class Settings:
    ENVIRONMENT = ENVIRONMENT
    DATABASE_URL = DATABASE_URL
    APP_HOST = APP_HOST
    ENABLE_SEARCH = ENABLE_SEARCH
    ENABLE_ELASTICSEARCH = ENABLE_ELASTICSEARCH
    ELASTICSEARCH_HOST = ELASTICSEARCH_HOST
    ELASTICSEARCH_API_KEY = ELASTICSEARCH_API_KEY
    ELASTICSEARCH_INDEX_PREFIX = ELASTICSEARCH_INDEX_PREFIX
    SEARCH_SERVICE_NAME = SEARCH_SERVICE_NAME
    SEARCH_API_KEY = SEARCH_API_KEY
    SEARCH_INDEX_PREFIX = SEARCH_INDEX_PREFIX
    SECRET_KEY = SECRET_KEY
    ALGORITHM = ALGORITHM
    ACCESS_TOKEN_EXPIRE_MINUTES = ACCESS_TOKEN_EXPIRE_MINUTES
    EMAIL_SENDER = EMAIL_SENDER
    SENDGRID_API_KEY = SENDGRID_API_KEY
    APP_NAME = APP_NAME
    APP_VERSION = APP_VERSION

settings = Settings() 