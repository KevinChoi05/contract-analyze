import os
import json
import logging
import threading
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, abort, flash
from werkzeug.utils import secure_filename
from psycopg2.extras import RealDictCursor
from database import get_db_connection
from core import extract_text_robust, analyze_contract

logger = logging.getLogger(__name__)
doc_bp = Blueprint('doc', __name__)

def analyze_document(doc_id, app_context):
    """Background function to analyze document with detailed progress updates."""
    with app_context:
        def update_status(status_message, progress_info=None):
            """Helper to update status in the DB with optional progress info."""
            with get_db_connection() as status_conn:
                with status_conn.cursor() as status_cursor:
                    if progress_info:
                        # Store progress info in analysis field temporarily
                        status_cursor.execute(
                            "UPDATE documents SET status = %s, analysis = %s WHERE id = %s", 
                            (status_message, json.dumps(progress_info), doc_id)
                        )
                    else:
                        status_cursor.execute(
                            "UPDATE documents SET status = %s WHERE id = %s", 
                            (status_message, doc_id)
                        )
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

            # Start text extraction with progress
            update_status('extracting_text', {'progress': 30, 'message': 'Extracting text with OCR...'})
            
            try:
                text = extract_text_robust(doc['filepath'])
                if text is None:
                    raise Exception("Could not extract readable text from this document. The file may be corrupted, password-protected, or contain only images without text.")
                
                if len(text.strip()) < 50:
                    raise Exception("Extracted text is too short to analyze. This document may contain mostly images or be in an unsupported format.")
                
                logger.info(f"OCR completed for doc {doc_id}: extracted {len(text)} characters")
                
            except Exception as ocr_error:
                logger.warning(f"OCR issue for doc {doc_id}: {ocr_error}")
                # Update with fallback message
                update_status('extracting_text', {'progress': 35, 'message': 'Fallback OCR activated - continuing...'})
                # Re-raise to handle in outer try-catch
                raise ocr_error
            
            # Start analysis with progress
            update_status('analyzing', {'progress': 70, 'message': 'Analyzing risks with DeepSeek AI...'})
            
            analysis_result = analyze_contract(text)
            
            if analysis_result.get("error"):
                raise Exception(analysis_result["error"])
            
            # Finalizing
            update_status('analyzing', {'progress': 95, 'message': 'Finalizing summary...'})
            
            # Store results
            with get_db_connection() as final_conn:
                with final_conn.cursor() as final_cursor:
                    final_cursor.execute(
                        "UPDATE documents SET analysis = %s, status = 'completed' WHERE id = %s",
                        (json.dumps(analysis_result), doc_id)
                    )
                    final_conn.commit()
            
            logger.info(f"Document analysis completed: {doc['filename']} (ID: {doc_id})")
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"Document analysis failed for doc_id {doc_id}: {error_message}")
            
            # Provide specific error messages for common issues
            if "google" in error_message.lower() and "403" in error_message:
                error_message = "Google Cloud OCR access denied (403). Using fallback OCR method. Please enable Document AI API later."
            elif "ocr" in error_message.lower():
                error_message = "OCR processing failed. The document may be corrupted or in an unsupported format."
            elif "deepseek" in error_message.lower() or "api" in error_message.lower():
                error_message = "AI analysis service temporarily unavailable. Please try again later."
            
            try:
                # Mark as error in the database
                with get_db_connection() as error_conn:
                    with error_conn.cursor() as error_cursor:
                        error_cursor.execute(
                            "UPDATE documents SET status = 'error', analysis = %s WHERE id = %s", 
                            (json.dumps({'error': error_message}), doc_id)
                        )
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
            logger.warning(f"Document {doc_id} not found for user {session.get('user_id')}")
            abort(404)
        
        # Log the document status for debugging
        logger.info(f"Document {doc_id} status: {doc['status']}, has analysis: {bool(doc['analysis'])}")
        
        # Debug: Print raw analysis data
        if doc['analysis']:
            logger.info(f"Raw analysis data for doc {doc_id}: {str(doc['analysis'])[:500]}...")
        
        # Convert analysis from JSON string to dict if needed
        if doc['analysis'] and isinstance(doc['analysis'], str):
            try:
                parsed_analysis = json.loads(doc['analysis'])
                logger.info(f"Parsed analysis type: {type(parsed_analysis)}, keys: {list(parsed_analysis.keys()) if isinstance(parsed_analysis, dict) else 'not dict'}")
                doc['analysis'] = parsed_analysis
            except json.JSONDecodeError as json_error:
                logger.error(f"Failed to parse analysis JSON for document {doc_id}: {json_error}")
                logger.error(f"Raw analysis content: {doc['analysis']}")
                doc['analysis'] = None
        
        # Validate analysis structure for template
        if doc['analysis'] and isinstance(doc['analysis'], dict):
            # Check if this is an error result
            if 'error' in doc['analysis']:
                logger.info(f"Document {doc_id} has error in analysis: {doc['analysis']['error']}")
            else:
                # Validate expected fields for successful analysis
                expected_fields = ['summary', 'clauses']
                missing_fields = [field for field in expected_fields if field not in doc['analysis']]
                if missing_fields:
                    logger.warning(f"Document {doc_id} analysis missing fields: {missing_fields}")
                
                # Validate clauses structure if present
                if 'clauses' in doc['analysis'] and doc['analysis']['clauses']:
                    if isinstance(doc['analysis']['clauses'], list):
                        logger.info(f"Document {doc_id} has {len(doc['analysis']['clauses'])} clauses")
                        # Check first clause structure
                        if doc['analysis']['clauses']:
                            first_clause = doc['analysis']['clauses'][0]
                            logger.info(f"First clause keys: {list(first_clause.keys()) if isinstance(first_clause, dict) else 'not dict'}")
                    else:
                        logger.warning(f"Document {doc_id} clauses is not a list: {type(doc['analysis']['clauses'])}")
        
        # Attempt to render template with comprehensive error handling
        try:
            logger.info(f"Attempting to render template for document {doc_id}")
            return render_template('document.html', document=doc)
        except Exception as template_error:
            logger.error(f"Template rendering failed for document {doc_id}: {template_error}", exc_info=True)
            logger.error(f"Document data structure: {doc}")
            
            # Try to render with a safe fallback
            safe_doc = {
                'id': doc['id'],
                'filename': doc['filename'],
                'status': doc['status'],
                'analysis': None  # Remove problematic analysis data
            }
            try:
                logger.info(f"Attempting fallback render for document {doc_id}")
                flash('Analysis data could not be displayed properly. Please try refreshing the page.', 'warning')
                return render_template('document.html', document=safe_doc)
            except Exception as fallback_error:
                logger.error(f"Fallback template rendering also failed for document {doc_id}: {fallback_error}", exc_info=True)
                raise template_error  # Re-raise original error
            
    except Exception as e:
        logger.error(f"Error fetching document page for doc_id {doc_id}: {e}", exc_info=True)
        flash('An error occurred while loading the document. Please try again.', 'error')
        return redirect(url_for('doc.dashboard'))
    finally:
        if conn:
            conn.close()

@doc_bp.route('/document/<int:doc_id>/delete', methods=['POST'])
def delete_document(doc_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # First, find the document to get its filepath
        cursor.execute("SELECT filepath FROM documents WHERE id = %s AND user_id = %s", (doc_id, session['user_id']))
        doc = cursor.fetchone()
        
        if not doc:
            flash('Document not found or you do not have permission', 'error')
            return redirect(url_for('doc.dashboard'))

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
        flash('Document deleted successfully', 'success')
        return redirect(url_for('doc.dashboard'))

    except Exception as e:
        logger.error(f"Error deleting document {doc_id}: {e}")
        flash('An error occurred while deleting the document.', 'error')
        return redirect(url_for('doc.dashboard'))
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
            flash('File uploaded successfully. Analysis in progress.', 'success')
            return redirect(url_for('doc.document_page', doc_id=doc_id))

        except Exception as e:
            logger.error(f"Upload error for user {session.get('username', 'unknown')}: {e}")
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except: pass
            flash('Failed to upload file. Please try again.', 'error')
            return redirect(url_for('doc.dashboard'))
        finally:
            if conn:
                conn.close()
    
    flash('Invalid file type. Please upload a PDF file.', 'error')
    return redirect(url_for('doc.dashboard'))

@doc_bp.route('/status/<int:doc_id>')
def status(doc_id):
    """Get document status for polling - enhanced with progress details"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT status, analysis FROM documents WHERE id = %s AND user_id = %s", (doc_id, session['user_id']))
        doc = cursor.fetchone()
        
        if doc:
            # Log current status for debugging
            logger.info(f"Status check for doc {doc_id}: {doc['status']}")
            
            # Enhanced progress mapping with detailed stages
            progress_map = {
                'processing': {
                    'progress': 10,
                    'stage': 'upload',
                    'message': 'Reading the file...',
                    'stage_text': 'Initializing processing'
                },
                'extracting_text': {
                    'progress': 40,
                    'stage': 'ocr',
                    'message': 'Extracting text with OCR (fallback activated)...',
                    'stage_text': 'Converting document to text'
                },
                'analyzing': {
                    'progress': 80,
                    'stage': 'analysis',
                    'message': 'Analyzing risks with DeepSeek AI...',
                    'stage_text': 'Identifying contract risks'
                },
                'completed': {
                    'progress': 100,
                    'stage': 'complete',
                    'message': 'Analysis complete!',
                    'stage_text': 'Finalizing results'
                },
                'error': {
                    'progress': 100,
                    'stage': 'error',
                    'message': 'Analysis failed',
                    'stage_text': 'Error occurred'
                }
            }
            
            status_info = progress_map.get(doc['status'], {
                'progress': 0,
                'stage': 'upload',
                'message': f'Status: {doc["status"]}',
                'stage_text': 'Processing document'
            })
            
            response = {
                'status': doc['status'],
                'progress': status_info['progress'],
                'stage': status_info['stage'],
                'message': status_info['message'],
                'stage_text': status_info['stage_text'],
                'analysis': None
            }
            
            # Parse analysis JSON if it's a string
            if doc['analysis'] and isinstance(doc['analysis'], str):
                try:
                    parsed_analysis = json.loads(doc['analysis'])
                    
                    # If status is in progress and analysis contains progress info, use it
                    if doc['status'] in ['processing', 'extracting_text', 'analyzing'] and isinstance(parsed_analysis, dict) and 'progress' in parsed_analysis:
                        response['progress'] = parsed_analysis['progress']
                        response['message'] = parsed_analysis.get('message', status_info['message'])
                        logger.info(f"Using dynamic progress for doc {doc_id}: {response['progress']}% - {response['message']}")
                    elif doc['status'] == 'completed':
                        response['analysis'] = parsed_analysis
                        logger.info(f"Returning completed analysis for doc {doc_id}")
                    elif doc['status'] == 'error':
                        response['error_message'] = parsed_analysis.get('error', 'Unknown error occurred')
                        logger.info(f"Returning error for doc {doc_id}: {response['error_message']}")
                        
                except json.JSONDecodeError as json_error:
                    logger.error(f"Failed to parse analysis JSON for document {doc_id}: {json_error}")
                    response['analysis'] = None
            
            logger.info(f"Status response for doc {doc_id}: {response['status']} ({response['progress']}%) - {response['message']}")
            return jsonify(response)
        else:
            logger.warning(f"Document {doc_id} not found for user {session.get('user_id')}")
            return jsonify({'error': 'Document not found'}), 404
    except Exception as e:
        logger.error(f"Database status error for doc {doc_id}: {e}", exc_info=True)
        return jsonify({'error': 'Could not retrieve status.'}), 500
    finally:
        if conn:
            conn.close()

@doc_bp.route('/progress/<int:doc_id>')
def progress(doc_id):
    """Get document progress for progress bar updates - enhanced with detailed stages"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT status, analysis FROM documents WHERE id = %s AND user_id = %s", (doc_id, session['user_id']))
        doc = cursor.fetchone()
        
        if doc:
            # Enhanced progress mapping with detailed stages
            progress_map = {
                'processing': {
                    'progress': 10,
                    'stage': 'upload',
                    'message': 'Reading the file...',
                    'description': 'Initializing document processing'
                },
                'extracting_text': {
                    'progress': 40,
                    'stage': 'ocr',
                    'message': 'Extracting text with OCR...',
                    'description': 'Converting document to readable text'
                },
                'analyzing': {
                    'progress': 80,
                    'stage': 'analysis',
                    'message': 'Analyzing risks with DeepSeek AI...',
                    'description': 'Identifying contract risks and clauses'
                },
                'completed': {
                    'progress': 100,
                    'stage': 'complete',
                    'message': 'Analysis complete!',
                    'description': 'Contract analysis finished successfully'
                },
                'error': {
                    'progress': 100,
                    'stage': 'error',
                    'message': 'Analysis failed',
                    'description': 'An error occurred during processing'
                }
            }
            
            status_info = progress_map.get(doc['status'], {
                'progress': 0,
                'stage': 'upload',
                'message': f'Status: {doc["status"]}',
                'description': 'Processing document'
            })
            
            response = {
                'status': doc['status'],
                'progress': status_info['progress'],
                'stage': status_info['stage'],
                'message': status_info['message'],
                'description': status_info['description']
            }
            
            # If analysis contains specific progress info, use it
            if doc['analysis'] and isinstance(doc['analysis'], str):
                try:
                    analysis_data = json.loads(doc['analysis'])
                    if isinstance(analysis_data, dict) and 'progress' in analysis_data:
                        response['progress'] = analysis_data['progress']
                        response['message'] = analysis_data.get('message', status_info['message'])
                except json.JSONDecodeError:
                    pass
            
            return jsonify(response)
        else:
            return jsonify({'error': 'Document not found'}), 404
    except Exception as e:
        logger.error(f"Database progress error: {e}")
        return jsonify({'error': 'Could not retrieve progress.'}), 500
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
    """Retry document analysis - renamed from retry_document to match frontend URL"""
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
    
    search_term = request.args.get('search', '').strip()
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    if search_term:
        cursor.execute(
            "SELECT id, filename, status, created_at FROM documents WHERE user_id = %s AND filename ILIKE %s ORDER BY created_at DESC",
            (session['user_id'], f'%{search_term}%')
        )
    else:
        cursor.execute(
            "SELECT id, filename, status, created_at FROM documents WHERE user_id = %s ORDER BY created_at DESC",
            (session['user_id'],)
        )
    
    documents = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', documents=documents) 