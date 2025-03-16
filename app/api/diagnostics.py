from typing import Dict, Any, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
import traceback
import os

from app.db.database import get_db, engine, DATABASE_URL, DB_HOST, DB_USER, DB_PASSWORD
from app.models.user import User
from app.models.meal import Meal
from app.models.checklist import Checklist

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diagnostics", tags=["System Diagnostics"])

@router.get("/db", response_model=Dict[str, Any])
def test_database_connection(db: Session = Depends(get_db)):
    """
    Test the database connection and return diagnostic information.
    This endpoint is intentionally not protected to allow for troubleshooting.
    """
    results = {
        "connection_successful": False,
        "database_info": {},
        "simple_queries": {},
        "errors": [],
        "connection_details": {
            "host": DB_HOST,
            "user": DB_USER,
            "password_length": len(DB_PASSWORD) if DB_PASSWORD else 0,
            "password_set": bool(DB_PASSWORD),
            "connection_string": DATABASE_URL.replace(DB_PASSWORD, "*****") if DB_PASSWORD else DATABASE_URL,
            "environment": os.getenv("ENVIRONMENT", "unknown")
        }
    }
    
    # Test raw connection
    try:
        # Test with SQLAlchemy engine directly
        with engine.connect() as connection:
            # Get database version
            db_version = connection.execute(text("SELECT version()")).scalar()
            results["database_info"]["version"] = db_version
            
            # Try a simple table count query
            user_count = connection.execute(text("SELECT COUNT(*) FROM users")).scalar()
            results["simple_queries"]["user_count"] = user_count
            
            # Get table names
            table_query = connection.execute(text(
                "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname='public'"
            ))
            results["database_info"]["tables"] = [row[0] for row in table_query]
            
            results["connection_successful"] = True
    except Exception as e:
        error_detail = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc()
        }
        results["errors"].append(error_detail)
    
    # Test ORM queries if basic connection worked
    if results["connection_successful"]:
        try:
            # Try user query
            user_count = db.query(User).count()
            results["simple_queries"]["orm_user_count"] = user_count
            
            # Try meal query
            meal_count = db.query(Meal).count()
            results["simple_queries"]["orm_meal_count"] = meal_count
            
            # Try checklist query
            checklist_count = db.query(Checklist).count()
            results["simple_queries"]["orm_checklist_count"] = checklist_count
            
        except Exception as e:
            error_detail = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "traceback": traceback.format_exc()
            }
            results["errors"].append(error_detail)
    
    return results 