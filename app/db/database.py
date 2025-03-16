from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import urllib.parse

# Get database connection parameters from environment variables
DB_NAME = os.getenv("DB_NAME", "fms_prod")
DB_USER = os.getenv("DB_USER", "jasonadmin")
DB_PASSWORD = "Thisisfortigraandtaz!"  # Hardcoded for now to ensure it matches exactly
DB_HOST = os.getenv("DB_HOST", "gimenopgsql.postgres.database.azure.com")
DB_PORT = os.getenv("DB_PORT", "5432")

# Clean up SSL mode value to avoid issues with comments in .env file
raw_ssl_mode = os.getenv("DB_SSL_MODE", "require")
# Extract just the first word to remove any comments
DB_SSL_MODE = raw_ssl_mode.strip().split()[0]

# Create a clean connection URL with the verified password
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode={DB_SSL_MODE}"

# Log the connection URL (with password masked) for debugging
masked_url = DATABASE_URL.replace(DB_PASSWORD, "*****")
print(f"Connecting to database: {masked_url}")

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