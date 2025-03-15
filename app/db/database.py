from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Get database connection parameters from environment variables
DB_NAME = os.getenv("DB_NAME", "fms_prod")
DB_USER = os.getenv("DB_USER", "jasonadmin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "gimenopgsql.postgres.database.azure.com")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_SSL_MODE = os.getenv("DB_SSL_MODE", "require")  # Default to require SSL for Azure

# Construct SQLAlchemy database URL with SSL configuration
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode={DB_SSL_MODE}"

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

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