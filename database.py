import os
import time
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def get_db_config():
    """Get database configuration from environment variables or DATABASE_URL"""
    # Prioritize Railway's DATABASE_URL
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

# Database configuration (compute once at module load)
DB_CONFIG = get_db_config()

def get_db_connection():
    """Get a database connection.
    
    This function connects to PostgreSQL and raises an exception if the connection fails.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info("Database connection established.")
        return conn
    except Exception as e:
        logger.critical(f"DATABASE CONNECTION FAILED: {e}")
        raise e

def init_database():
    """Initialize database tables for PostgreSQL with retry logic."""
    retries = 3
    delay = 2
    
    for attempt in range(retries):
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Create users table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            id SERIAL PRIMARY KEY,
                            username VARCHAR(50) UNIQUE NOT NULL,
                            password_hash VARCHAR(255) NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Create documents table
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
            return
        except Exception as e:
            logger.warning(f"Database init attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                logger.error("Could not initialize database after retries. Service will continue with limited functionality.")
                raise e