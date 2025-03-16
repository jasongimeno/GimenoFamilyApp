import psycopg2
import os
from dotenv import load_dotenv
import sys

# Add the parent directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file if it exists
load_dotenv()

def test_connection(explicit_password=None):
    """Test connection to Azure PostgreSQL database."""
    try:
        # Get connection parameters from environment variables
        db_name = os.getenv("DB_NAME", "fms_prod")
        db_user = os.getenv("DB_USER", "jasonadmin")
        db_password = explicit_password or os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST", "gimenopgsql.postgres.database.azure.com")
        db_port = os.getenv("DB_PORT", "5432")
        
        # Check if password is set
        if not db_password:
            print("Error: DB_PASSWORD environment variable is not set")
            return False
        
        print(f"Connecting to PostgreSQL database: {db_host}:{db_port}/{db_name} as {db_user}")
        
        # Connect to the database with SSL enabled
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
            sslmode='require'  # Enable SSL connection required by Azure
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

if __name__ == "__main__":
    # First try with environment variable password
    print("Attempting connection with password from environment variables...")
    if not test_connection():
        # If that fails, try with explicit password
        print("\nTrying with explicit password...")
        if not test_connection("Thisisfortigraandtaz!"):
            # Try an alternative format for the password
            print("\nTrying with URL encoded password...")
            import urllib.parse
            encoded_password = urllib.parse.quote_plus("Thisisfortigraandtaz!")
            test_connection(encoded_password) 