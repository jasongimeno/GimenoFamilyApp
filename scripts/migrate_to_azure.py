#!/usr/bin/env python
"""
Azure Database Migration Script

This script supports migrating your database schema and data to Azure PostgreSQL.
It handles both schema creation and data transfer.
"""

import os
import sys
import argparse
import subprocess
from dotenv import load_dotenv

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import app modules
from app.db.database import Base, engine
from app.models import user, checklist, meal, carpool  # Import all your models

# Load environment variables
load_dotenv()

def setup_argparse():
    """Set up command line arguments."""
    parser = argparse.ArgumentParser(description='Migrate database to Azure PostgreSQL')
    parser.add_argument('--create-schema', action='store_true', help='Create database schema')
    parser.add_argument('--dump-data', action='store_true', help='Dump data from local database')
    parser.add_argument('--load-data', action='store_true', help='Load data to Azure PostgreSQL')
    parser.add_argument('--local-dump-file', default='db_dump.sql', help='Path to dump file')
    parser.add_argument('--test-connection', action='store_true', help='Test Azure connection')
    parser.add_argument('--create-all', action='store_true', help='Create schema directly using SQLAlchemy')
    parser.add_argument('--target', choices=['local', 'azure'], default='azure', 
                       help='Target database (local or azure)')
    
    return parser.parse_args()

def get_connection_params(target='azure'):
    """Get database connection parameters based on target."""
    if target == 'local':
        return {
            'db_name': os.getenv("DB_NAME", "fms_dev"),
            'db_user': os.getenv("DB_USER", "postgres"),
            'db_password': os.getenv("DB_PASSWORD", "postgres"),
            'db_host': os.getenv("DB_HOST", "localhost"),
            'db_port': os.getenv("DB_PORT", "5432"),
            'ssl_mode': os.getenv("DB_SSL_MODE", "disable")  # Default to disable for local
        }
    else:  # azure
        return {
            'db_name': os.getenv("DB_NAME", "fms_prod"),
            'db_user': os.getenv("DB_USER", "jasonadmin"),
            'db_password': os.getenv("DB_PASSWORD"),
            'db_host': os.getenv("DB_HOST", "gimenopgsql.postgres.database.azure.com"),
            'db_port': os.getenv("DB_PORT", "5432"),
            'ssl_mode': os.getenv("DB_SSL_MODE", "require")  # Default to require for Azure
        }

def test_connection(target='azure'):
    """Test connection to PostgreSQL database based on target."""
    try:
        import psycopg2
        
        # Get connection parameters
        params = get_connection_params(target)
        db_name = params['db_name']
        db_user = params['db_user']
        db_password = params['db_password']
        db_host = params['db_host']
        db_port = params['db_port']
        ssl_mode = params['ssl_mode']
        
        if not db_password:
            print(f"Error: DB_PASSWORD environment variable is not set for {target}")
            return False
        
        print(f"Connecting to PostgreSQL database: {db_host}:{db_port}/{db_name} as {db_user} (SSL mode: {ssl_mode})")
        
        # Connect to the database with appropriate SSL mode
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
            sslmode=ssl_mode
        )
        
        # Create a cursor
        cur = conn.cursor()
        
        # Execute a simple query
        cur.execute("SELECT version();")
        
        # Fetch the result
        version = cur.fetchone()
        print(f"Connected successfully!")
        print(f"PostgreSQL version: {version[0]}")
        
        # Close the cursor and connection
        cur.close()
        conn.close()
        
        return True
    except Exception as e:
        print(f"Connection error: {str(e)}")
        return False

def test_azure_connection():
    """Test connection to Azure PostgreSQL database."""
    return test_connection(target='azure')

def test_local_connection():
    """Test connection to local PostgreSQL database."""
    return test_connection(target='local')

def create_schema_with_alembic():
    """Create database schema using Alembic migrations."""
    try:
        # Check if we're already connected to Azure
        if not test_azure_connection():
            print("Cannot create schema: Not connected to Azure database.")
            return False
        
        print("Creating schema using Alembic migrations...")
        
        # Use the existing Alembic environment
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        
        print("Schema created successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating schema: {str(e)}")
        return False

def create_schema_with_sqlalchemy():
    """Create all tables directly using SQLAlchemy."""
    try:
        # Check if we're already connected to Azure
        if not test_azure_connection():
            print("Cannot create schema: Not connected to Azure database.")
            return False
        
        print("Creating schema using SQLAlchemy...")
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        print("Schema created successfully!")
        return True
    except Exception as e:
        print(f"Error creating schema: {str(e)}")
        return False

def dump_data():
    """Dump data from local database."""
    try:
        # Get local database connection parameters
        params = get_connection_params('local')
        db_name = params['db_name']
        db_user = params['db_user']
        db_password = params['db_password']
        db_host = params['db_host']
        db_port = params['db_port']
        
        dump_file = args.local_dump_file
        
        # Set PGPASSWORD environment variable for the subprocess
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password
        
        print(f"Dumping data from {db_host}:{db_port}/{db_name} to {dump_file}...")
        
        # Use pg_dump to create a dump file
        subprocess.run([
            "pg_dump",
            "-h", db_host,
            "-p", db_port,
            "-U", db_user,
            "-d", db_name,
            "-f", dump_file,
            "--data-only",  # Dump only data, not schema
            "--inserts"     # Use INSERT statements instead of COPY commands
        ], env=env, check=True)
        
        print(f"Data dumped successfully to {dump_file}!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error dumping data: {str(e)}")
        return False
    except FileNotFoundError:
        print("Error: pg_dump command not found. Make sure PostgreSQL client tools are installed.")
        return False

def load_data():
    """Load data to Azure PostgreSQL."""
    try:
        # Get Azure database connection parameters
        params = get_connection_params('azure')
        db_name = params['db_name']
        db_user = params['db_user']
        db_password = params['db_password']
        db_host = params['db_host']
        db_port = params['db_port']
        ssl_mode = params['ssl_mode']
        
        dump_file = args.local_dump_file
        
        if not os.path.exists(dump_file):
            print(f"Error: Dump file {dump_file} not found.")
            return False
        
        # Set PGPASSWORD environment variable for the subprocess
        env = os.environ.copy()
        env["PGPASSWORD"] = db_password
        
        print(f"Loading data from {dump_file} to {db_host}:{db_port}/{db_name}...")
        
        # Use psql to restore the dump file
        psql_cmd = [
            "psql",
            "-h", db_host,
            "-p", db_port,
            "-U", db_user,
            "-d", db_name,
            "-f", dump_file
        ]
        
        # Add SSL mode if required
        if ssl_mode.lower() == 'require':
            psql_cmd.append("--set=sslmode=require")
        
        subprocess.run(psql_cmd, env=env, check=True)
        
        print("Data loaded successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error loading data: {str(e)}")
        return False
    except FileNotFoundError:
        print("Error: psql command not found. Make sure PostgreSQL client tools are installed.")
        return False

if __name__ == "__main__":
    args = setup_argparse()
    
    # Test connection
    if args.test_connection:
        if args.target == 'azure':
            test_azure_connection()
        else:
            test_local_connection()
    
    # Create schema
    if args.create_schema:
        create_schema_with_alembic()
    
    # Create schema directly with SQLAlchemy
    if args.create_all:
        create_schema_with_sqlalchemy()
    
    # Dump data
    if args.dump_data:
        dump_data()
    
    # Load data
    if args.load_data:
        load_data()
    
    # If no specific action was specified, show help
    if not any([args.test_connection, args.create_schema, args.dump_data, args.load_data, args.create_all]):
        print("No action specified. Use --help to see available options.")
        
        # Suggest a complete migration flow
        print("\nSuggested migration flow:")
        print("1. Test local connection: python scripts/migrate_to_azure.py --test-connection --target local")
        print("2. Test Azure connection: python scripts/migrate_to_azure.py --test-connection --target azure")
        print("3. Create schema:         python scripts/migrate_to_azure.py --create-all")
        print("4. Dump local data:       python scripts/migrate_to_azure.py --dump-data")
        print("5. Load data to Azure:    python scripts/migrate_to_azure.py --load-data") 