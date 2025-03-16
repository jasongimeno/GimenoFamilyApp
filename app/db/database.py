from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import urllib.parse

# Get database connection parameters from environment variables
DB_NAME = os.getenv("DB_NAME", "fms_prod")
DB_USER = os.getenv("DB_USER", "jasonadmin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "gimenopgsql.postgres.database.azure.com")
DB_PORT = os.getenv("DB_PORT", "5432")

# Clean up SSL mode value to avoid issues with comments in .env file
raw_ssl_mode = os.getenv("DB_SSL_MODE", "require")
# Extract just the first word to remove any comments
DB_SSL_MODE = raw_ssl_mode.strip().split()[0]

# Use a safer approach with explicit connection parameters
# This avoids issues with special characters in passwords
# Base connection URL without password
base_url = f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create SQLAlchemy engine with explicit connect_args
engine = create_engine(
    base_url,
    connect_args={
        "password": DB_PASSWORD,
        "sslmode": DB_SSL_MODE
    }
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Database session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 