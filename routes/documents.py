import os
import json
import logging
import threading
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, abort
from werkzeug.utils import secure_filename
from psycopg2.extras import RealDictCursor
from database import get_db_connection
from core import extract_text_robust, analyze_contract

logger = logging.getLogger(__name__)
doc_bp = Blueprint('doc', __name__)

def analyze_document(doc_id, app_context):
    """Background function to analyze document with progress updates."""
    with app_context:
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


@doc_bp.route('/document/<int:doc_id>')
def document_page(doc_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
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

@doc_bp.route('/document/<int:doc_id>', methods=['DELETE'])
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

@doc_bp.route('/upload', methods=['POST'])
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{timestamp}{ext}"
        
        # Use current_app's config
        from flask import current_app
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        conn = None
        doc_id = None
        try:
            file.save(filepath)
            logger.info(f"File saved to: {filepath}")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO documents (user_id, filename, filepath, status) VALUES (%s, %s, %s, %s) RETURNING id",
                (session['user_id'], filename, filepath, 'processing')
            )
            doc_id = cursor.fetchone()[0]
            conn.commit()

            # Start analysis in background
            thread = threading.Thread(target=analyze_document, args=(doc_id, current_app.app_context()))
            thread.start()
            
            logger.info(f"Document uploaded successfully: {filename} (ID: {doc_id}) by user {session.get('username', 'unknown')}")
            return jsonify({
                'doc_id': doc_id,
                'message': 'File uploaded successfully. Analysis in progress.',
                'redirect_url': url_for('doc.document_page', doc_id=doc_id)
            })

        except Exception as e:
            logger.error(f"Upload error for user {session.get('username', 'unknown')}: {e}")
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except: pass
            return jsonify({'error': "Failed to upload file. Please try again."}), 500
        finally:
            if conn:
                conn.close()
    
    return jsonify({'error': 'Invalid file type. Please upload a PDF file.'}), 400

@doc_bp.route('/status/<int:doc_id>')
def get_status(doc_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT status, analysis FROM documents WHERE id = %s AND user_id = %s", (doc_id, session['user_id']))
        doc = cursor.fetchone()
        
        if doc:
            return jsonify({
                'status': doc['status'],
                'analysis': doc['analysis']
            })
        else:
            return jsonify({'error': 'Document not found'}), 404
    except Exception as e:
        logger.error(f"Database status error: {e}")
        return jsonify({'error': 'Could not retrieve status.'}), 500
    finally:
        if conn:
            conn.close()

@doc_bp.route('/documents')
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
            if doc['status'] == 'error' and doc['analysis']:
                doc_info['error_message'] = doc['analysis'].get('error', 'Unknown error')
            user_docs.append(doc_info)
            
        return jsonify(user_docs)
    except Exception as e:
        logger.error(f"Database documents error: {e}")
        return jsonify({'error': 'Could not retrieve documents.'}), 500
    finally:
        if conn:
            conn.close()

@doc_bp.route('/retry/<int:doc_id>', methods=['POST'])
def retry_document(doc_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = None
    try:
        from flask import current_app
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT id FROM documents WHERE id = %s AND user_id = %s", (doc_id, session['user_id']))
        doc = cursor.fetchone()
        
        if not doc:
            return jsonify({'error': 'Document not found'}), 404
        
        cursor.execute("UPDATE documents SET status = 'processing', analysis = NULL WHERE id = %s", (doc_id,))
        conn.commit()
        
        thread = threading.Thread(target=analyze_document, args=(doc_id, current_app.app_context()))
        thread.start()
        
        return jsonify({'message': 'Document processing restarted'}), 200
        
    except Exception as e:
        logger.error(f"Error retrying document {doc_id}: {e}")
        return jsonify({'error': 'Failed to retry document processing'}), 500
    finally:
        if conn:
            conn.close()

@doc_bp.route('/')
@doc_bp.route('/index')
def index():
    """Index route that redirects to dashboard"""
    return redirect(url_for('doc.dashboard'))

@doc_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute(
        "SELECT id, filename, status, created_at FROM documents WHERE user_id = %s ORDER BY created_at DESC",
        (session['user_id'],)
    )
    documents = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', documents=documents) 