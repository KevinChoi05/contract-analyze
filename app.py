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
    
    # Create Flask app first
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
    
    # Add health check first (before any heavy initialization)
    @app.route('/health')
    def health_check():
        """Fast health check for Railway - doesn't depend on external services"""
        return {"status": "healthy", "timestamp": datetime.now().isoformat()}, 200
    
    # Initialize database gracefully (non-blocking)
    db_ready = False
    try:
        init_database()
        logger.info("✅ Database initialized successfully")
        db_ready = True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}. App will continue with limited functionality.")

    # Initialize OCR service gracefully (non-blocking)
    ocr_ready = False
    try:
        ocr_service = get_ocr_service()
        if ocr_service:
            logger.info("✅ Google Cloud Document AI initialized successfully")
            ocr_ready = True
        else:
            logger.warning("⚠️ Google Cloud OCR not available, using fallback OCR")
    except Exception as e:
        logger.error(f"OCR service initialization failed: {e}. Using fallback if available.")

    # Store service status in app config for monitoring
    app.config['DB_READY'] = db_ready
    app.config['OCR_READY'] = ocr_ready
    
    # --- Register Blueprints ---
    app.register_blueprint(auth_bp)
    app.register_blueprint(doc_bp)

    # --- Core Routes & Error Handlers ---
    @app.route('/')
    def root():
        if 'user_id' in session:
            return redirect(url_for('doc.dashboard'))
        return redirect(url_for('auth.login'))

    @app.route('/status')
    def status_check():
        """Detailed status check including service dependencies"""
        return {
            "status": "running",
            "services": {
                "database": "ready" if app.config.get('DB_READY') else "unavailable",
                "ocr": "ready" if app.config.get('OCR_READY') else "fallback"
            },
            "timestamp": datetime.now().isoformat()
        }, 200

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
    host = '0.0.0.0' if os.getenv('FLASK_ENV') == 'production' else '127.0.0.1'
    
    logger.info(f"Starting server on {host}:{port}")
    
    if platform.system() == "Windows":
        print("--- Starting Development Server on Windows ---")
        run_simple(
            host, 
            port, 
            app, 
            use_reloader=True, 
            use_debugger=True, 
            threaded=True
        )
    else:
        # Gunicorn will be used in production via Dockerfile
        print("--- Starting Development Server ---")
        app.run(debug=True, host=host, port=port)
