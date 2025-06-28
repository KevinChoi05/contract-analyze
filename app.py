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

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Production settings
if os.getenv('FLASK_ENV') == 'production':
    app.config['DEBUG'] = False
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
else:
    app.config['DEBUG'] = True

Session(app)

# Configure API keys
openai.api_key = os.getenv('OPENAI_API_KEY')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')

# Redis configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
try:
    redis_client = redis.from_url(REDIS_URL)
    redis_client.ping()
    logger.info("Redis connection established")
except:
    redis_client = None
    logger.warning("Redis not available, using in-memory storage")

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'contract_analyzer'),
    'user': os.getenv('DB_USER', 'contract_user'),
    'password': os.getenv('DB_PASSWORD', 'contract_password')
}

# Create necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('logs', exist_ok=True)
os.makedirs('flask_session', exist_ok=True)

# Initialize OCR service
ocr_service = get_ocr_service()
logger.info("OCR service initialized")

# In-memory storage (fallback) - REMOVED FOR PRODUCTION
# users = {}
# documents = {}

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
    """Initialize database tables for PostgreSQL with retry logic."""
    conn = None
    retries = 5
    delay = 5  # seconds
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
                logger.critical("Could not connect to the database after several retries. Exiting.")
                raise  # Re-raise the exception after the last attempt
        finally:
            if conn:
                conn.close()

# Initialize database on startup
init_database()

# --- Advanced Document Processing Engine ---

def extract_text_robust(filepath):
    """
    Unified text extraction using Google Cloud Document AI or fallback
    This replaces all the complex OCR logic with a single, reliable method
    """
    logger.info(f"Starting unified text extraction for: {filepath}")
    
    try:
        # Use unified OCR service
        text = extract_text_unified(filepath)
        
        if text and len(text.strip()) > 10:
            logger.info(f"✅ Unified OCR extraction successful: {len(text)} characters")
            return text
        else:
            logger.warning("Unified OCR extracted minimal or no text")
            return None
            
    except Exception as e:
        logger.error(f"Unified OCR extraction failed: {e}")
        return None

def analyze_contract(text_content):
    """Analyzes contract text using DeepSeek and returns structured JSON."""
    if not DEEPSEEK_API_KEY:
        return {"error": "DeepSeek API Key not configured."}
    
    system_message = """You are an expert contract risk analyst. Your job is to identify business risks and provide EXACT SOURCE LOCATIONS.
CRITICAL REQUIREMENTS:
1. For each risk you identify, you MUST provide the exact sentence number where it appears
2. Use the [number] format from the text to reference source locations
3. Copy the EXACT text phrase that contains the risk (for highlighting)
4. Calculate precise 0-100 risk scores using the methodology below
RISK SCORING (0-100 Scale):
• 0-30: SAFE - Minimal impact, routine terms
• 31-69: WARNING - Moderate concern, needs attention  
• 70-100: UNSAFE - Critical threat, immediate action required
SCORING CRITERIA (weighted average):
1. Financial Impact (30%): 0-100 based on potential costs
2. Business Disruption (25%): 0-100 based on operational impact
3. Legal/Compliance Risk (20%): 0-100 based on legal exposure
4. Likelihood (15%): 0-100 based on probability of occurrence
5. Mitigation Difficulty (10%): 0-100 based on how hard to resolve
JSON RESPONSE FORMAT:
```json
{
  "summary": "A brief, one-paragraph executive summary of the contract's purpose and key risks.",
  "clauses": [
    {
      "id": 1,
      "exact_text": "Late payment will incur 5% monthly penalty plus immediate acceleration",
      "type": "Payment Default Penalties", 
      "risk_score": 75,
      "risk_category": "Unsafe",
      "clause": "Business-friendly description of the risk",
      "consequences": "What could happen to the business",
      "mitigation": "How to reduce this risk"
    }
  ]
}
```"""
    prompt = f"ANALYZE this contract and identify the TOP 8-10 MOST CRITICAL business risks. Return a valid JSON object.\n\nCONTRACT TEXT:\n{text_content[:24000]}"
    
    try:
        client = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4096,
            temperature=0.1
        )
        response_text = response.choices[0].message.content
        # Extract JSON from markdown code block
        match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
        if match:
            return json.loads(match.group(1))
        else:
            return json.loads(response_text) # Fallback to parsing the whole string
    except Exception as e:
        logger.error(f"Error in analyze_contract: {e}")
        return {"error": f"Failed to analyze contract: {e}"}

# --- End of Advanced Engine ---

@app.route('/health')
def health_check():
    """A simple and reliable health check endpoint."""
    return jsonify({'status': 'healthy'}), 200

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = username
                logger.info(f"User {username} logged in successfully")
                return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Database login error: {e}")
            flash('An error occurred during login. Please try again.', 'error')
        finally:
            if conn:
                conn.close()
        
        flash('Invalid username or password')
        logger.warning(f"Failed login attempt for user: {username}")
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long', 'error')
            return render_template('register.html')
        
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Check if user exists
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                flash('Username already exists', 'error')
                return render_template('register.html')
            
            # Insert new user
            password_hash = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
                (username, password_hash)
            )
            user_id = cursor.fetchone()['id']
            conn.commit()
            
            # Log the user in
            session['user_id'] = user_id
            session['username'] = username
            
            flash('Registration successful! You are now logged in.', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            logger.error(f"Database registration error: {e}")
            flash('Registration failed due to a database error. Please try again.', 'error')
            return render_template('register.html')
        finally:
            if conn:
                conn.close()

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/document/<int:doc_id>')
def document_page(doc_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, filename, status, analysis FROM documents WHERE id = %s AND user_id = %s", (doc_id, session['user_id']))
        doc = cursor.fetchone()
        
        if not doc:
            abort(404)
            
        return render_template('document.html', doc=doc)
    except Exception as e:
        logger.error(f"Error fetching document page for doc_id {doc_id}: {e}")
        abort(500)
    finally:
        if conn:
            conn.close()

@app.route('/document/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # First, find the document to get its filepath
        cursor.execute("SELECT filepath FROM documents WHERE id = %s AND user_id = %s", (doc_id, session['user_id']))
        doc = cursor.fetchone()
        
        if not doc:
            return jsonify({'error': 'Document not found or you do not have permission'}), 404

        # Delete the record from the database
        cursor.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
        conn.commit()

        # Delete the physical file
        try:
            if os.path.exists(doc['filepath']):
                os.remove(doc['filepath'])
                logger.info(f"Deleted physical file: {doc['filepath']}")
        except Exception as e:
            # Log this error, but don't fail the request since the DB record is gone.
            logger.error(f"Could not delete physical file {doc['filepath']}: {e}")
            
        logger.info(f"User {session['username']} deleted document with ID {doc_id}")
        return jsonify({'message': 'Document deleted successfully'}), 200

    except Exception as e:
        logger.error(f"Error deleting document {doc_id}: {e}")
        return jsonify({'error': 'An error occurred while deleting the document.'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate file size (50MB limit)
    if file.content_length and file.content_length > 50 * 1024 * 1024:
        return jsonify({'error': 'File size exceeds 50MB limit'}), 400
    
    if file and file.filename.lower().endswith('.pdf'):
        filename = secure_filename(file.filename)
        # Add timestamp to avoid filename conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{timestamp}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        conn = None
        doc_id = None
        try:
            # Save file first
            file.save(filepath)
            logger.info(f"File saved to: {filepath}")
            
            # Verify file was saved and is readable
            if not os.path.exists(filepath):
                raise Exception("File was not saved properly")
            
            # Test basic file operations
            file_size = os.path.getsize(filepath)
            if file_size == 0:
                raise Exception("Uploaded file is empty")
            
            logger.info(f"File verified: {filename} ({file_size} bytes)")
            
            # Save to database
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO documents (user_id, filename, filepath, status) VALUES (%s, %s, %s, %s) RETURNING id",
                (session['user_id'], filename, filepath, 'processing')
            )
            doc_id = cursor.fetchone()[0]
            conn.commit()

            # Start analysis in background
            thread = threading.Thread(target=analyze_document, args=(doc_id,))
            thread.start()
            
            logger.info(f"Document uploaded successfully: {filename} (ID: {doc_id}) by user {session.get('username', 'unknown')}")
            return jsonify({
                'doc_id': doc_id,
                'message': 'File uploaded successfully. Analysis in progress.',
                'redirect_url': url_for('document_page', doc_id=doc_id)
            })

        except Exception as e:
            logger.error(f"Upload error for user {session.get('username', 'unknown')}: {e}")
            
            # Clean up file if it was saved but database failed
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    logger.info(f"Cleaned up file after error: {filepath}")
                except:
                    pass
            
            # Return user-friendly error message
            error_msg = "Failed to upload file. Please try again."
            if "database" in str(e).lower():
                error_msg = "Database error. Please try again later."
            elif "file" in str(e).lower():
                error_msg = "File processing error. Please check your PDF file."
            
            return jsonify({'error': error_msg}), 500
        finally:
            if conn:
                conn.close()
    
    return jsonify({'error': 'Invalid file type. Please upload a PDF file.'}), 400

def analyze_document(doc_id):
    """Background function to analyze document with progress updates."""
    
    def update_status(status_message):
        """Helper to update status in the DB."""
        with get_db_connection() as status_conn:
            with status_conn.cursor() as status_cursor:
                status_cursor.execute("UPDATE documents SET status = %s WHERE id = %s", (status_message, doc_id))
                status_conn.commit()

    try:
        # Get document from database
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM documents WHERE id = %s", (doc_id,))
                doc = cursor.fetchone()
        
        if not doc:
            logger.error(f"Analysis failed: Document with ID {doc_id} not found.")
            return

        # Start text extraction
        update_status('extracting_text')
        text = extract_text_robust(doc['filepath'])
        if text is None:
            raise Exception("Could not extract readable text from this document. The file may be corrupted, password-protected, or contain only images without text.")
        
        if len(text.strip()) < 50:
            raise Exception("Extracted text is too short to analyze. This document may contain mostly images or be in an unsupported format.")
        
        # Start analysis
        update_status('analyzing')
        analysis_result = analyze_contract(text)
        
        if analysis_result.get("error"):
            raise Exception(analysis_result["error"])

        # Store results
        update_status('completed')
        with get_db_connection() as final_conn:
            with final_conn.cursor() as final_cursor:
                final_cursor.execute(
                    "UPDATE documents SET analysis = %s, status = 'completed' WHERE id = %s",
                    (json.dumps(analysis_result), doc_id)
                )
                final_conn.commit()
        
        logger.info(f"Document analysis completed: {doc['filename']} (ID: {doc_id})")
        
    except Exception as e:
        logger.error(f"Document analysis failed for doc_id {doc_id}: {e}")
        try:
            # Mark as error in the database
            with get_db_connection() as error_conn:
                with error_conn.cursor() as error_cursor:
                    error_cursor.execute("UPDATE documents SET status = 'error', analysis = %s WHERE id = %s", (json.dumps({'error': str(e)}), doc_id))
                    error_conn.commit()
        except Exception as final_e:
            logger.error(f"Failed to even update status to error for doc_id {doc_id}: {final_e}")

@app.route('/status/<doc_id>')
def get_status(doc_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM documents WHERE id = %s AND user_id = %s", (doc_id, session['user_id']))
        doc = cursor.fetchone()
        
        if doc:
            analysis = doc['analysis'] if doc['analysis'] else None
            return jsonify({
                'status': doc['status'],
                'analysis': analysis
            })
        else:
            return jsonify({'error': 'Document not found'}), 404
    except Exception as e:
        logger.error(f"Database status error: {e}")
        return jsonify({'error': 'Could not retrieve status.'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/documents')
def get_documents():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, filename, status, created_at, analysis FROM documents WHERE user_id = %s ORDER BY created_at DESC", (session['user_id'],))
        docs = cursor.fetchall()
        
        user_docs = []
        for doc in docs:
            doc_info = {
                'id': doc['id'],
                'filename': doc['filename'],
                'status': doc['status'],
                'created_at': doc['created_at'].isoformat()
            }
            
            # Add error message if status is error
            if doc['status'] == 'error' and doc['analysis']:
                try:
                    analysis = json.loads(doc['analysis']) if isinstance(doc['analysis'], str) else doc['analysis']
                    if 'error' in analysis:
                        doc_info['error_message'] = analysis['error']
                except:
                    doc_info['error_message'] = 'Unknown error occurred'
            
            user_docs.append(doc_info)
            
        return jsonify(user_docs)
    except Exception as e:
        logger.error(f"Database documents error: {e}")
        return jsonify({'error': 'Could not retrieve documents.'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/retry/<int:doc_id>', methods=['POST'])
def retry_document(doc_id):
    """Retry processing a failed document."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if document exists and belongs to user
        cursor.execute("SELECT * FROM documents WHERE id = %s AND user_id = %s", (doc_id, session['user_id']))
        doc = cursor.fetchone()
        
        if not doc:
            return jsonify({'error': 'Document not found'}), 404
        
        if doc['status'] not in ['error', 'completed']:
            return jsonify({'error': 'Document is currently being processed'}), 400
        
        # Reset status to processing
        cursor.execute("UPDATE documents SET status = 'processing', analysis = NULL WHERE id = %s", (doc_id,))
        conn.commit()
        
        # Start analysis in background
        thread = threading.Thread(target=analyze_document, args=(doc_id,))
        thread.start()
        
        logger.info(f"Retrying document analysis for doc_id {doc_id} by user {session.get('username', 'unknown')}")
        return jsonify({'message': 'Document processing restarted'}), 200
        
    except Exception as e:
        logger.error(f"Error retrying document {doc_id}: {e}")
        return jsonify({'error': 'Failed to retry document processing'}), 500
    finally:
        if conn:
            conn.close()

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    
    # Use Werkzeug's development server on Windows for local testing
    if platform.system() == "Windows":
        print("--- Starting Development Server on Windows ---")
        print(f"Listening on: http://127.0.0.1:{port}")
        print("-------------------------------------------")
        run_simple(
            '127.0.0.1', 
            port, 
            app, 
            use_reloader=True, 
            use_debugger=True, 
            threaded=True
        )
    else:
        # On other systems (like Railway), this script can be run with Gunicorn directly.
        # The Dockerfile CMD ["gunicorn", "app:app", ...] will handle this in production.
        print("--- Starting Development Server ---")
        print(f"Listening on: http://0.0.0.0:{port}")
        print("For production, run with a WSGI server like Gunicorn.")
        print("---------------------------------")
        app.run(debug=True, host='0.0.0.0', port=port)
