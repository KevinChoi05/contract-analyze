#!/usr/bin/env python3
"""
Railway startup script for AI Contract Analyzer
Handles environment setup and graceful startup
"""
import os
import sys
import logging
import time
from app import create_app

# Configure logging for Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    """Main startup function for Railway"""
    logger.info("🚀 Starting AI Contract Analyzer on Railway")
    
    # Check required environment variables
    port = os.environ.get('PORT')
    if not port:
        logger.error("PORT environment variable not set by Railway")
        sys.exit(1)
    
    logger.info(f"Starting on port {port}")
    
    # Log environment info (without secrets)
    logger.info(f"Python version: {sys.version}")
    logger.info(f"FLASK_ENV: {os.getenv('FLASK_ENV', 'not set')}")
    logger.info(f"DATABASE_URL: {'set' if os.getenv('DATABASE_URL') else 'not set'}")
    logger.info(f"DEEPSEEK_API_KEY: {'set' if os.getenv('DEEPSEEK_API_KEY') else 'not set'}")
    
    try:
        # Create the Flask app
        app = create_app()
        logger.info("✅ Flask app created successfully")
        
        # Import and run with gunicorn programmatically
        from gunicorn.app.wsgiapp import WSGIApplication
        
        # Configure gunicorn
        sys.argv = [
            'gunicorn',
            '--bind', f'0.0.0.0:{port}',
            '--workers', '2',
            '--timeout', '120',
            '--preload',
            '--access-logfile', '-',
            '--error-logfile', '-',
            'app:create_app()'
        ]
        
        WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]").run()
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 