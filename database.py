import os
import time
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def get_db_config():
    """Get database configuration from environment variables or DATABASE_URL"""
    # Check for Railway's DATABASE_URL first
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        try:
            parsed = urlparse(database_url)
            return {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'database': parsed.path[1:],  # Remove leading slash
                'user': parsed.username,
                'password': parsed.password
            }
        except Exception as e:
            logger.warning(f"Failed to parse DATABASE_URL: {e}")
    
    # Fallback to individual environment variables
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'contract_analyzer'),
        'user': os.getenv('DB_USER', 'contract_user'),
        'password': os.getenv('DB_PASSWORD', 'contract_password')
    }

# Database configuration
DB_CONFIG = get_db_config()

def get_db_connection():
    """Get a persistent database connection.
    This function now exclusively connects to PostgreSQL and raises
    an exception if the connection fails, ensuring the database is
    a hard dependency for the application.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("Database connection established.")
        return conn
    except Exception as e:
        logger.critical(f"DATABASE CONNECTION FAILED: {e}")
        # In a production environment, you might want the app to fail fast
        # if it can't connect to the database.
        raise e

def init_database():
    """Initialize database tables for PostgreSQL with Railway-optimized retry logic."""
    conn = None
    retries = 3  # Reduced from 5 for faster startup
    delay = 2   # Reduced from 5 seconds
    
    for i in range(retries):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # User table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Document table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    filename VARCHAR(255) NOT NULL,
                    filepath VARCHAR(500) NOT NULL,
                    status VARCHAR(20) DEFAULT 'processing',
                    analysis JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            logger.info("Database initialized successfully for PostgreSQL")
            return  # Exit the function on success
        except Exception as e:
            logger.warning(f"Database connection attempt {i+1}/{retries} failed: {e}")
            if i < retries - 1:
                time.sleep(delay)
            else:
                logger.error("Could not connect to the database after retries. Service will continue with limited functionality.")
                raise  # Re-raise the exception after the last attempt
        finally:
            if conn:
                conn.close() 