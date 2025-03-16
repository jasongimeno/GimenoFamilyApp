from typing import Dict, Any, List
from fastapi import APIRouter, Depends, status, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect, exc
import urllib.parse
import os
import json
import logging
import uuid
import datetime
import time
import traceback

from app.db.database import get_db, engine

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(tags=["diagnostics"])

@router.get("/db/status")
async def check_db_connection(db: Session = Depends(get_db)):
    """
    Check database connection status and return diagnostic information
    """
    logger.info("Diagnostic endpoint called: /db/status")
    
    try:
        # Get database connection parameters from environment variables (mask password)
        db_name = os.getenv("DB_NAME", "fms_prod")
        db_user = os.getenv("DB_USER", "jasonadmin")
        db_host = os.getenv("DB_HOST", "gimenopgsql.postgres.database.azure.com")
        db_port = os.getenv("DB_PORT", "5432")
        db_ssl_mode = os.getenv("DB_SSL_MODE", "require")
        
        # Query to get database version
        result = db.execute(text("SELECT version()")).scalar()
        
        # Get list of tables in the database
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        # Basic query to verify data access - count users
        user_count = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
        
        response_data = {
            "status": "connected",
            "database_info": {
                "version": result,
                "host": db_host,
                "port": db_port,
                "database": db_name,
                "user": db_user,
                "ssl_mode": db_ssl_mode,
            },
            "tables": tables,
            "user_count": user_count
        }
        
        logger.info(f"Database connection successful. User count: {user_count}")
        return response_data
        
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        error_details = {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc()
        }
        
        # Return error with 500 status code
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_details
        )

@router.get("/db/write-test")
async def test_db_write_operations(request: Request, db: Session = Depends(get_db)):
    """
    Test database write operations by creating and deleting a temporary record
    This endpoint is intentionally unprotected for troubleshooting
    """
    # Get client IP for logging
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Write test called from IP: {client_ip}")
    
    results = {
        "status": "started",
        "timestamp": datetime.datetime.now().isoformat(),
        "tests": [],
        "client_info": {
            "ip": client_ip,
            "user_agent": request.headers.get("user-agent", "unknown")
        }
    }
    
    temp_table_name = f"diagnostics_test_{uuid.uuid4().hex[:8]}"
    start_time = time.time()
    
    try:
        # Test 1: Create temporary table
        logger.info(f"Creating temporary table: {temp_table_name}")
        create_table_query = text(f"""
            CREATE TABLE {temp_table_name} (
                id SERIAL PRIMARY KEY,
                test_data TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        db.execute(create_table_query)
        db.commit()
        
        results["tests"].append({
            "name": "create_table",
            "success": True,
            "time_ms": round((time.time() - start_time) * 1000),
            "table_name": temp_table_name
        })
        
        # Test 2: Insert record
        start_time = time.time()
        test_uuid = str(uuid.uuid4())
        insert_query = text(f"""
            INSERT INTO {temp_table_name} (test_data) 
            VALUES (:test_data)
            RETURNING id
        """)
        result = db.execute(insert_query, {"test_data": f"Test data {test_uuid}"})
        record_id = result.scalar()
        db.commit()
        
        results["tests"].append({
            "name": "insert_record",
            "success": True,
            "time_ms": round((time.time() - start_time) * 1000),
            "record_id": record_id,
            "test_uuid": test_uuid
        })
        
        # Test 3: Verify record exists
        start_time = time.time()
        select_query = text(f"""
            SELECT id, test_data, created_at
            FROM {temp_table_name}
            WHERE id = :id
        """)
        result = db.execute(select_query, {"id": record_id})
        row = result.fetchone()
        
        verify_result = {
            "name": "verify_record",
            "success": row is not None,
            "time_ms": round((time.time() - start_time) * 1000)
        }
        
        if row:
            verify_result["record"] = {
                "id": row[0],
                "test_data": row[1],
                "created_at": row[2].isoformat() if row[2] else None
            }
        
        results["tests"].append(verify_result)
        
        # Test 4: Update record
        start_time = time.time()
        update_value = f"Updated at {datetime.datetime.now().isoformat()}"
        update_query = text(f"""
            UPDATE {temp_table_name}
            SET test_data = :test_data
            WHERE id = :id
            RETURNING id, test_data
        """)
        result = db.execute(update_query, {"id": record_id, "test_data": update_value})
        updated_row = result.fetchone()
        db.commit()
        
        results["tests"].append({
            "name": "update_record",
            "success": updated_row is not None,
            "time_ms": round((time.time() - start_time) * 1000),
            "updated_value": updated_row[1] if updated_row else None
        })
        
        # Test 5: Delete record
        start_time = time.time()
        delete_query = text(f"""
            DELETE FROM {temp_table_name}
            WHERE id = :id
        """)
        db.execute(delete_query, {"id": record_id})
        db.commit()
        
        # Verify deletion
        verify_delete = text(f"""
            SELECT COUNT(*) FROM {temp_table_name}
            WHERE id = :id
        """)
        count = db.execute(verify_delete, {"id": record_id}).scalar()
        
        results["tests"].append({
            "name": "delete_record",
            "success": count == 0,
            "time_ms": round((time.time() - start_time) * 1000)
        })
        
        # Test 6: Drop temporary table
        start_time = time.time()
        drop_table_query = text(f"""
            DROP TABLE {temp_table_name}
        """)
        db.execute(drop_table_query)
        db.commit()
        
        results["tests"].append({
            "name": "drop_table",
            "success": True,
            "time_ms": round((time.time() - start_time) * 1000)
        })
        
        # All tests passed
        results["status"] = "success"
        logger.info(f"Write test completed successfully: {json.dumps(results)}")
        
    except Exception as e:
        error_time = round((time.time() - start_time) * 1000)
        error_details = {
            "error_type": type(e).__name__,
            "error_message": str(e),
            "traceback": traceback.format_exc()
        }
        
        results["status"] = "error"
        results["error"] = error_details
        results["error_time_ms"] = error_time
        
        # Try to clean up the temporary table if it exists
        try:
            cleanup_query = text(f"""
                DROP TABLE IF EXISTS {temp_table_name}
            """)
            db.execute(cleanup_query)
            db.commit()
            results["cleanup_attempted"] = True
        except Exception as cleanup_error:
            results["cleanup_error"] = str(cleanup_error)
        
        logger.error(f"Write test failed: {json.dumps(error_details)}")
    
    # Check for transaction isolation level
    try:
        isolation_level = db.execute(text("SHOW transaction_isolation")).scalar()
        results["transaction_isolation"] = isolation_level
    except:
        results["transaction_isolation"] = "unknown"
    
    # Check for connection parameters
    try:
        conn_params = {}
        params_query = text("""
            SELECT name, setting FROM pg_settings 
            WHERE name IN ('max_connections', 'idle_in_transaction_session_timeout', 'statement_timeout')
        """)
        for row in db.execute(params_query):
            conn_params[row[0]] = row[1]
        results["connection_parameters"] = conn_params
    except:
        pass
    
    return results

@router.get("/request-info")
async def get_request_info(request: Request):
    """
    Return detailed information about the incoming request for troubleshooting
    This endpoint is intentionally unprotected
    """
    logger.info(f"Request info endpoint called from IP: {request.client.host if request.client else 'unknown'}")
    
    # Get headers - convert to dict to make JSON serializable
    headers = dict(request.headers.items())
    
    # Get cookies
    cookies = request.cookies
    
    # Clean sensitive data from authorization headers/cookies
    if "authorization" in headers:
        headers["authorization"] = headers["authorization"][:15] + "..." if headers["authorization"] else None
    
    response = {
        "request_info": {
            "method": request.method,
            "url": str(request.url),
            "client": {
                "host": request.client.host if request.client else None,
                "port": request.client.port if request.client else None
            },
            "headers": headers,
            "cookies": cookies
        },
        "server_info": {
            "environment": os.getenv("ENVIRONMENT", "unknown"),
            "host": os.getenv("HOST", "unknown"),
            "timestamp": datetime.datetime.now().isoformat()
        }
    }
    
    return response 