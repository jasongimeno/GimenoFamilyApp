from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import urllib.parse
import logging
import time

# Set up logging
logger = logging.getLogger(__name__)

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
logger.info(f"Connecting to database: {masked_url}")
print(f"Connecting to database: {masked_url}")

# Configure SQLAlchemy engine with some debugging options
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Check connection before using from pool
    pool_recycle=300,    # Recycle connections after 5 minutes
    connect_args={
        "application_name": f"FMS_{os.getenv('ENVIRONMENT', 'unknown')}",  # Identify app in DB logs
    }
)

# Add event listeners for debugging
@event.listens_for(engine, "connect")
def on_connect(dbapi_connection, connection_record):
    logger.info(f"New database connection established. Connection ID: {id(connection_record)}")

@event.listens_for(engine, "checkout")
def on_checkout(dbapi_connection, connection_record, connection_proxy):
    logger.debug(f"Database connection checked out from pool. Connection ID: {id(connection_record)}")

@event.listens_for(engine, "checkin")
def on_checkin(dbapi_connection, connection_record):
    logger.debug(f"Database connection returned to pool. Connection ID: {id(connection_record)}")

@event.listens_for(engine, "before_execute")
def before_execute(conn, clauseelement, multiparams, params, execution_options):
    conn.info.setdefault('query_start_time', []).append(time.time())
    logger.debug(f"Executing query: {clauseelement}")

@event.listens_for(engine, "after_execute")
def after_execute(conn, clauseelement, multiparams, params, result):
    query_time = time.time() - conn.info['query_start_time'].pop(-1)
    if query_time > 0.5:  # Log slow queries (>500ms)
        logger.warning(f"Slow query ({query_time:.2f}s): {clauseelement}")
    else:
        logger.debug(f"Query completed in {query_time:.4f}s")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Database session dependency with error logging
def get_db():
    db = SessionLocal()
    try:
        logger.debug("DB session created")
        yield db
    except Exception as e:
        logger.error(f"DB session error: {str(e)}")
        raise
    finally:
        logger.debug("DB session closed")
        db.close() 