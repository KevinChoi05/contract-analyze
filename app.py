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

# Optional imports with graceful fallbacks
try:
    import easyocr
    EASYOCR_AVAILABLE = True
    print("✅ EasyOCR is available")
except ImportError:
    EASYOCR_AVAILABLE = False
    easyocr = None
    print("❌ EasyOCR is not installed - OCR functionality will be limited")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
    print("✅ Tesseract is available")
except ImportError:
    TESSERACT_AVAILABLE = False
    pytesseract = None
    print("❌ Tesseract is not installed - OCR functionality will be limited")

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
OFFLINE_MODE = os.getenv('OFFLINE_MODE', 'False').lower() == 'true'

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

# Initialize OCR reader
if EASYOCR_AVAILABLE:
    try:
        reader = easyocr.Reader(['en'])
        logger.info("EasyOCR initialized successfully")
    except Exception as e:
        reader = None
        logger.warning(f"EasyOCR not available: {e}")
else:
    reader = None
    logger.warning("EasyOCR not installed")

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

class ContractAnalyzer:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=openai.api_key) if openai.api_key else None
        
    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF using multiple methods"""
        try:
            # Method 1: PyMuPDF
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            
            if len(text.strip()) > 100:  # If we got substantial text
                return text
                
            # Method 2: OCR with EasyOCR (if available)
            if reader and EASYOCR_AVAILABLE:
                doc = fitz.open(pdf_path)
                ocr_text = ""
                for page in doc:
                    pix = page.get_pixmap()
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    results = reader.readtext(img)
                    for (bbox, text, prob) in results:
                        if prob > 0.5:  # Confidence threshold
                            ocr_text += text + " "
                doc.close()
                
                if len(ocr_text.strip()) > 100:
                    return ocr_text
                    
            # Method 3: Tesseract OCR (if available)
            if TESSERACT_AVAILABLE:
                doc = fitz.open(pdf_path)
                tesseract_text = ""
                for page in doc:
                    pix = page.get_pixmap()
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    tesseract_text += pytesseract.image_to_string(img) + " "
                doc.close()
                
                return tesseract_text
            
            return text
            
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return ""
    
    def analyze_contract_with_openai(self, text):
        """Analyze contract using OpenAI GPT-4.1 Mini"""
        if not self.openai_client or OFFLINE_MODE:
            return self.get_mock_analysis()
            
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": """You are a world-class expert contract analyst AI. Your task is to conduct a comprehensive risk analysis of the provided legal document.

Analyze the following contract and identify:
1.  **Key Risk Clauses:** Identify clauses that pose a financial, legal, operational, or compliance risk.
2.  **Be Selective:** Based on the document's length and complexity, decide how many risk clauses are truly significant. Focus only on the most critical issues that require attention. Do not list minor or standard clauses.
3.  **Provide Analysis in JSON format:**

Your output must be a valid JSON object with the following structure:
{
    "overall_risk_score": "A score from 0 (no risk) to 100 (extreme risk), representing your overall assessment of the document.",
    "executive_summary": "A brief, high-level summary of the contract's purpose and most critical risks. This should be easy for a non-lawyer to understand.",
    "identified_risks": [
        {
            "clause_type": "Financial | Legal | Operational | Compliance | etc.",
            "risk_severity": "A score from 0 to 100 for this specific clause.",
            "clause_quote": "The exact, verbatim text from the contract that constitutes the risk. This is critical for highlighting.",
            "risk_explanation": "In simple terms, explain what this clause means and why it's a risk. Describe the potential negative impact or 'damage' it could cause.",
            "mitigation_recommendation": "Suggest a concrete action or negotiation point to reduce this specific risk."
        }
    ]
}"""},
                    {"role": "user", "content": f"Please analyze this contract:\n\n{text[:12000]}"}
                ],
                max_tokens=4000
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return self.get_mock_analysis()
    
    def analyze_contract_with_deepseek(self, text):
        """Analyze contract using DeepSeek v3"""
        if OFFLINE_MODE or not DEEPSEEK_API_KEY:
            return self.get_mock_analysis()
            
        try:
            headers = {
                'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "You are an expert contract analyst. Provide detailed risk analysis."},
                    {"role": "user", "content": f"Analyze this contract for risks:\n\n{text[:8000]}"}
                ],
                "max_tokens": 2000
            }
            
            response = requests.post(
                'https://api.deepseek.com/v1/chat/completions',
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                return json.loads(response.json()['choices'][0]['message']['content'])
            else:
                return self.get_mock_analysis()
                
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            return self.get_mock_analysis()
    
    def get_mock_analysis(self):
        """Return mock analysis for demo mode"""
        return {
            "overall_risk_score": 65,
            "executive_summary": "This is a mock analysis. The contract contains several high-risk clauses requiring immediate attention, particularly regarding liability and termination.",
            "identified_risks": [
                {
                    "clause_type": "Financial",
                    "risk_severity": 85,
                    "clause_quote": "The party of the first part shall hold unlimited liability for any and all damages arising from the execution of this agreement.",
                    "risk_explanation": "This clause exposes the company to unlimited financial risk. In a worst-case scenario, this could lead to bankruptcy as there is no cap on the amount of damages that can be claimed.",
                    "mitigation_recommendation": "Negotiate a liability cap, ideally equal to the contract value or covered by your insurance policy."
                },
                {
                    "clause_type": "Legal",
                    "risk_severity": 70,
                    "clause_quote": "This agreement shall be governed by the laws of the state of utopia, without regard to its conflict of law provisions.",
                    "risk_explanation": "The governing law is set to a potentially unfavorable or unfamiliar jurisdiction, which could create legal challenges and increase litigation costs if a dispute arises.",
                    "mitigation_recommendation": "Amend the governing law to a more favorable and familiar jurisdiction, such as the state where your company is headquartered."
                }
            ]
        }

analyzer = ContractAnalyzer()

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
        cursor.execute("SELECT id, filename FROM documents WHERE id = %s AND user_id = %s", (doc_id, session['user_id']))
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

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and file.filename.lower().endswith('.pdf'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        conn = None
        doc_id = None
        try:
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
            
            logger.info(f"Document uploaded: {filename} (ID: {doc_id}) by user {session['username']}")
            return jsonify({
                'doc_id': doc_id,
                'message': 'File uploaded successfully. Analysis in progress.',
                'redirect_url': url_for('document_page', doc_id=doc_id)
            })

        except Exception as e:
            logger.error(f"Database upload error: {e}")
            return jsonify({'error': 'Failed to record document in database.'}), 500
        finally:
            if conn:
                conn.close()
    
    return jsonify({'error': 'Invalid file type. Please upload a PDF.'}), 400

def analyze_document(doc_id):
    """Background function to analyze document with progress updates."""
    conn = None
    try:
        # Get document from database
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM documents WHERE id = %s", (doc_id,))
        doc = cursor.fetchone()
        if not doc:
            logger.error(f"Analysis failed: Document with ID {doc_id} not found.")
            return

        def update_status(status):
            """Helper to update status in the DB."""
            with get_db_connection() as status_conn:
                with status_conn.cursor() as status_cursor:
                    status_cursor.execute("UPDATE documents SET status = %s WHERE id = %s", (status, doc_id))
                    status_conn.commit()

        # Start text extraction
        update_status('extracting_text')
        text = analyzer.extract_text_from_pdf(doc['filepath'])
        
        # Start OpenAI analysis
        update_status('analyzing_openai')
        openai_analysis = analyzer.analyze_contract_with_openai(text)
        
        # Start DeepSeek analysis
        update_status('analyzing_deepseek')
        deepseek_analysis = analyzer.analyze_contract_with_deepseek(text)
        
        # Combine analyses
        update_status('combining_results')
        combined_analysis = {
            'openai': openai_analysis,
            'deepseek': deepseek_analysis,
            'text': text[:1000] + "..." if len(text) > 1000 else text,
            'analyzed_at': datetime.now().isoformat()
        }
        
        # Store results
        with get_db_connection() as final_conn:
            with final_conn.cursor() as final_cursor:
                final_cursor.execute(
                    "UPDATE documents SET status = %s, analysis = %s WHERE id = %s",
                    ('completed', json.dumps(combined_analysis), doc_id)
                )
                final_conn.commit()
        
        logger.info(f"Document analysis completed: {doc['filename']} (ID: {doc_id})")
        
    except Exception as e:
        logger.error(f"Document analysis failed for doc_id {doc_id}: {e}")
        try:
            with get_db_connection() as error_conn:
                with error_conn.cursor() as error_cursor:
                    error_cursor.execute("UPDATE documents SET status = %s WHERE id = %s", ('error', doc_id))
                    error_conn.commit()
        except Exception as final_e:
            logger.error(f"Failed to even update status to error for doc_id {doc_id}: {final_e}")
    finally:
        # The main connection is no longer needed as we use with-statements
        pass

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
        cursor.execute("SELECT id, filename, status, created_at FROM documents WHERE user_id = %s ORDER BY created_at DESC", (session['user_id'],))
        docs = cursor.fetchall()
        
        user_docs = [
            {
                'id': doc['id'],
                'filename': doc['filename'],
                'status': doc['status'],
                'created_at': doc['created_at'].isoformat()
            }
            for doc in docs
        ]
        return jsonify(user_docs)
    except Exception as e:
        logger.error(f"Database documents error: {e}")
        return jsonify({'error': 'Could not retrieve documents.'}), 500
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
