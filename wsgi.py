#!/usr/bin/env python3
"""
WSGI entry point for Railway deployment
"""
import os
import logging
from app import create_app

# Configure logging for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Create the Flask application
application = create_app()

# For debugging
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    application.run(host='0.0.0.0', port=port) 