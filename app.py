import os
import json
import base64
import tempfile
import threading
import time
import logging
import secrets
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, abort
from flask_session import Session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
import openai
import requests
from dotenv import load_dotenv
import fitz  # PyMuPDF
from PIL import Image
import io
import re
import redis
import psycopg2
from psycopg2.extras import RealDictCursor
import sqlite3
from werkzeug.serving import run_simple
import platform
# Import unified OCR module
from cloud_ocr import extract_text_unified, get_ocr_service

# Import blueprints and db functions
from database import init_database
from routes.auth import auth_bp
from routes.documents import doc_bp

# Load environment variables
if os.getenv('FLASK_ENV') != 'production':
    load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log') if os.path.exists('logs') else logging.StreamHandler(),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- App Initialization ---

def create_app():
    """Application factory function."""
    
    # Create necessary directories
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('flask_session', exist_ok=True)
    
    # Initialize database
    try:

====================


Path: /health

Retry window: 5m0s

 

Attempt #1 failed with service unavailable. Continuing to retry for 4m59s

Attempt #2 failed with service unavailable. Continuing to retry for 4m56s

Attempt #3 failed with service unavailable. Continuing to retry for 4m53s

Attempt #4 failed with service unavailable. Continuing to retry for 4m48s

Attempt #5 failed with service unavailable. Continuing to retry for 4m39s

Attempt #6 failed with service unavailable. Continuing to retry for 4m23s

Attempt #7 failed with service unavailable. Continuing to retry for 3m53s

Attempt #8 failed with service unavailable. Continuing to retry for 3m23s

Attempt #9 failed with service unavailable. Continuing to retry for 2m53s

Attempt #10 failed with service unavailable. Continuing to retry for 2m23s

Attempt #11 failed with service unavailable. Continuing to retry for 1m53s

Attempt #12 failed with service unavailable. Continuing to retry for 1m23s

Attempt #13 failed with service unavailable. Continuing to retry for 53s

Attempt #14 failed with service unavailable. Continuing to retry for 23s

 

1/1 replicas never became healthy!

Healthcheck failed!
        init_database()
    except Exception as e:
        logger.critical(f"FATAL: Could not initialize database. Application cannot start. Error: {e}")
        # In a real scenario, this would likely cause the app container to exit and restart.
        # For now, we exit explicitly if running locally.
        if platform.system() == "Windows":
             exit(1) # Or handle more gracefully

    # Initialize OCR service (with fallback support)
    try:
        ocr_service = get_ocr_service()
        if ocr_service:
            logger.info("✅ Google Cloud Document AI initialized successfully")
        else:
            logger.warning("⚠️ Google Cloud OCR not available, using fallback OCR")
    except Exception as e:
        logger.warning(f"OCR service initialization failed, using fallback: {e}")

    # Create Flask app
    app = Flask(__name__)
    
    # --- Configuration ---
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

    if os.getenv('FLASK_ENV') == 'production':
        app.config['DEBUG'] = False
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    else:
        app.config['DEBUG'] = True

    Session(app)
    
    # --- Register Blueprints ---
    app.register_blueprint(auth_bp)
    app.register_blueprint(doc_bp)

    # --- Core Routes & Error Handlers ---
    @app.route('/')
    def root():
        if 'user_id' in session:
            return redirect(url_for('doc.dashboard'))
        return redirect(url_for('auth.login'))

    @app.route('/health')
    def health_check():
        return "OK", 200

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('500.html'), 500
        
    return app

# --- Main Execution ---

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get("PORT", 5001))
    
    if platform.system() == "Windows":
        print("--- Starting Development Server on Windows ---")
        run_simple(
            '127.0.0.1', 
            port, 
            app, 
            use_reloader=True, 
            use_debugger=True, 
            threaded=True
        )
    else:
        # Gunicorn will be used in production via Dockerfile
        print("--- Starting Development Server ---")
        app.run(debug=True, host='0.0.0.0', port=port)
