#!/usr/bin/env python3
"""
Local test script for progress bar fix
Uses SQLite instead of PostgreSQL for easy local testing
"""

import os
import sqlite3
from flask import Flask, render_template, jsonify, request, session
from datetime import datetime
import json

# Create Flask app
app = Flask(__name__)
app.secret_key = 'test-secret-key'

# Create SQLite database
def init_db():
    conn = sqlite3.connect('test_contracts.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create documents table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'processing',
            analysis TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Insert test user
    cursor.execute("INSERT OR IGNORE INTO users (username, password_hash) VALUES ('test', 'test')")
    
    # Insert test documents with different statuses
    test_docs = [
        (1, 'processing_document.pdf', 'uploads/processing_document.pdf', 'processing', None),
        (1, 'extracting_document.pdf', 'uploads/extracting_document.pdf', 'extracting_text', None),
        (1, 'analyzing_document.pdf', 'uploads/analyzing_document.pdf', 'analyzing', None),
        (1, 'completed_document.pdf', 'uploads/completed_document.pdf', 'completed', json.dumps({
            'summary': 'This is a test contract analysis summary. The document contains several important clauses that require attention.',
            'clauses': [
                {
                    'id': 1,
                    'type': 'Financial Limitation',
                    'risk_score': 45,
                    'clause': 'Limited financial liability clause',
                    'consequences': 'Potential financial exposure',
                    'mitigation': 'Review and negotiate terms',
                    'exact_text': 'The company liability shall not exceed $10,000'
                },
                {
                    'id': 2,
                    'type': 'Termination Clause',
                    'risk_score': 70,
                    'clause': 'Immediate termination without cause',
                    'consequences': 'Contract can be terminated without notice',
                    'mitigation': 'Negotiate notice period',
                    'exact_text': 'Either party may terminate this agreement immediately'
                }
            ]
        })),
        (1, 'error_document.pdf', 'uploads/error_document.pdf', 'error', json.dumps({
            'error': 'Failed to process document. The file may be corrupted or in an unsupported format.'
        }))
    ]
    
    for doc in test_docs:
        cursor.execute('''
            INSERT OR IGNORE INTO documents (user_id, filename, filepath, status, analysis)
            VALUES (?, ?, ?, ?, ?)
        ''', doc)
    
    conn.commit()
    conn.close()

@app.route('/')
def root():
    return dashboard()

@app.route('/dashboard')
def dashboard():
    session['user_id'] = 1  # Auto-login as test user
    session['username'] = 'test'
    
    conn = sqlite3.connect('test_contracts.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, filename, status, created_at FROM documents WHERE user_id = 1 ORDER BY id DESC')
    documents = cursor.fetchall()
    conn.close()
    
    # Convert to dict format
    docs = []
    for doc in documents:
        docs.append({
            'id': doc[0],
            'filename': doc[1],
            'status': doc[2],
            'created_at': datetime.fromisoformat(doc[3]) if doc[3] else datetime.now()
        })
    
    return render_template('index.html', documents=docs)

@app.route('/document/<int:doc_id>')
def document_page(doc_id):
    session['user_id'] = 1  # Auto-login as test user
    
    conn = sqlite3.connect('test_contracts.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, filename, status, analysis FROM documents WHERE id = ? AND user_id = 1', (doc_id,))
    doc = cursor.fetchone()
    conn.close()
    
    if not doc:
        return "Document not found", 404
    
    # Convert to dict format
    document = {
        'id': doc[0],
        'filename': doc[1],
        'status': doc[2],
        'analysis': json.loads(doc[3]) if doc[3] else None
    }
    
    return render_template('document.html', document=document)

@app.route('/status/<int:doc_id>')
def status(doc_id):
    session['user_id'] = 1  # Auto-login as test user
    
    conn = sqlite3.connect('test_contracts.db')
    cursor = conn.cursor()
    cursor.execute('SELECT status, analysis FROM documents WHERE id = ? AND user_id = 1', (doc_id,))
    doc = cursor.fetchone()
    conn.close()
    
    if not doc:
        return jsonify({'error': 'Document not found'}), 404
    
    status_val = doc[0]
    analysis = json.loads(doc[1]) if doc[1] else None
    
    # Progress mapping
    progress_map = {
        'processing': {'progress': 15, 'stage': 'upload', 'message': 'Reading and processing the file...'},
        'extracting_text': {'progress': 45, 'stage': 'ocr', 'message': 'Extracting text with OCR...'},
        'analyzing': {'progress': 85, 'stage': 'analysis', 'message': 'Analyzing risks with DeepSeek AI...'},
        'completed': {'progress': 100, 'stage': 'complete', 'message': 'Analysis complete!'},
        'error': {'progress': 100, 'stage': 'error', 'message': 'Analysis failed'}
    }
    
    status_info = progress_map.get(status_val, {'progress': 0, 'stage': 'upload', 'message': f'Status: {status_val}'})
    
    response = {
        'status': status_val,
        'progress': status_info['progress'],
        'stage': status_info['stage'],
        'message': status_info['message'],
        'analysis': analysis if status_val == 'completed' else None
    }
    
    if status_val == 'error' and analysis:
        response['error_message'] = analysis.get('error', 'Unknown error occurred')
    
    return jsonify(response)

# Add missing routes that templates expect
@app.route('/login')
def login():
    return "Login not needed for test", 200

@app.route('/logout')
def logout():
    return "Logout not needed for test", 200

@app.route('/upload', methods=['POST'])
def upload():
    return "Upload not implemented in test", 200

@app.route('/document/<int:doc_id>/delete', methods=['POST'])
def delete_document(doc_id):
    return "Delete not implemented in test", 200

@app.route('/document/<int:doc_id>/retry', methods=['POST'])
def retry_document(doc_id):
    return "Retry not implemented in test", 200

if __name__ == '__main__':
    print("🚀 Setting up local test environment...")
    init_db()
    print("✅ Test database created with sample data")
    print("📊 Test documents available:")
    print("   - ID 1: processing_document.pdf (processing)")
    print("   - ID 2: extracting_document.pdf (extracting_text)")
    print("   - ID 3: analyzing_document.pdf (analyzing)")
    print("   - ID 4: completed_document.pdf (completed) ← Test this one!")
    print("   - ID 5: error_document.pdf (error)")
    print()
    print("🌐 Starting test server...")
    print("📱 Open: http://127.0.0.1:5000")
    print("🎯 Test URL: http://127.0.0.1:5000/document/4 (completed document)")
    print()
    
    app.run(debug=True, port=5000) 