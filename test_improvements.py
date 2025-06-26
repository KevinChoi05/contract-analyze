#!/usr/bin/env python3
"""
Test script for AI Contract Analyzer
This script tests the core functionality of the application.
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test if all required modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        import flask
        print("✅ Flask imported successfully")
    except ImportError as e:
        print(f"❌ Flask import failed: {e}")
        return False
    
    try:
        import openai
        print("✅ OpenAI imported successfully")
    except ImportError as e:
        print(f"❌ OpenAI import failed: {e}")
        return False
    
    try:
        import fitz  # PyMuPDF
        print("✅ PyMuPDF imported successfully")
    except ImportError as e:
        print(f"❌ PyMuPDF import failed: {e}")
        return False
    
    try:
        import easyocr
        print("✅ EasyOCR imported successfully")
    except ImportError as e:
        print(f"❌ EasyOCR import failed: {e}")
        return False
    
    try:
        import pytesseract
        print("✅ PyTesseract imported successfully")
    except ImportError as e:
        print(f"❌ PyTesseract import failed: {e}")
        return False
    
    return True

def test_contract_analyzer():
    """Test the ContractAnalyzer class"""
    print("\n🔍 Testing ContractAnalyzer...")
    
    try:
        from app import ContractAnalyzer
        analyzer = ContractAnalyzer()
        print("✅ ContractAnalyzer instantiated successfully")
        
        # Test mock analysis
        mock_analysis = analyzer.get_mock_analysis()
        if isinstance(mock_analysis, dict) and 'overall_risk_score' in mock_analysis:
            print("✅ Mock analysis working correctly")
            return True
        else:
            print("❌ Mock analysis format incorrect")
            return False
            
    except Exception as e:
        print(f"❌ ContractAnalyzer test failed: {e}")
        return False

def test_flask_app():
    """Test Flask app creation"""
    print("\n🔍 Testing Flask app...")
    
    try:
        from app import app
        print("✅ Flask app created successfully")
        
        # Test basic routes
        with app.test_client() as client:
            # Test login page
            response = client.get('/login')
            if response.status_code == 200:
                print("✅ Login route working")
            else:
                print(f"❌ Login route failed: {response.status_code}")
                return False
            
            # Test register page
            response = client.get('/register')
            if response.status_code == 200:
                print("✅ Register route working")
            else:
                print(f"❌ Register route failed: {response.status_code}")
                return False
            
            # Test protected route (should redirect to login)
            response = client.get('/')
            if response.status_code == 302:  # Redirect
                print("✅ Authentication protection working")
            else:
                print(f"❌ Authentication protection failed: {response.status_code}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Flask app test failed: {e}")
        return False

def test_environment():
    """Test environment configuration"""
    print("\n🔍 Testing environment...")
    
    # Check if .env exists
    if os.path.exists('.env'):
        print("✅ .env file exists")
    else:
        print("⚠️ .env file not found (create one from env.example)")
    
    # Check if uploads directory exists
    if os.path.exists('uploads'):
        print("✅ uploads directory exists")
    else:
        print("⚠️ uploads directory not found")
    
    # Check if templates directory exists
    if os.path.exists('templates'):
        print("✅ templates directory exists")
    else:
        print("⚠️ templates directory not found")
    
    return True

def test_pdf_processing():
    """Test PDF processing capabilities"""
    print("\n🔍 Testing PDF processing...")
    
    try:
        from app import ContractAnalyzer
        analyzer = ContractAnalyzer()
        
        # Create a simple test PDF
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "This is a test contract for analysis purposes.")
        page.insert_text((50, 100), "It contains sample text to test the AI analysis.")
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            doc.save(tmp_file.name)
            doc.close()
            
            # Test text extraction
            text = analyzer.extract_text_from_pdf(tmp_file.name)
            
            # Clean up
            os.unlink(tmp_file.name)
            
            if text and len(text.strip()) > 0:
                print("✅ PDF text extraction working")
                return True
            else:
                print("❌ PDF text extraction failed")
                return False
                
    except Exception as e:
        print(f"❌ PDF processing test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 AI Contract Analyzer Test Suite")
    print("=" * 40)
    
    tests = [
        ("Import Test", test_imports),
        ("Contract Analyzer Test", test_contract_analyzer),
        ("Flask App Test", test_flask_app),
        ("Environment Test", test_environment),
        ("PDF Processing Test", test_pdf_processing)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")
        if test_func():
            passed += 1
        print()
    
    print("=" * 40)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The application is ready to use.")
        print("\n🚀 To start the application:")
        print("1. Set your API keys in .env file")
        print("2. Run: python app.py")
        print("3. Open http://localhost:5001 in your browser")
    else:
        print("⚠️ Some tests failed. Please check the errors above.")
        print("\n💡 For demo mode without API keys, set OFFLINE_MODE=True in .env")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 