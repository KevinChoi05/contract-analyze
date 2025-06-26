#!/usr/bin/env python3
"""
AI Contract Analyzer Setup Script
This script helps you set up the AI Contract Analyzer application.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible")
    return True

def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    
    # Check if pip is available
    if not shutil.which('pip'):
        print("❌ pip is not installed. Please install pip first.")
        return False
    
    # Install requirements
    if os.path.exists('requirements.txt'):
        return run_command('pip install -r requirements.txt', 'Installing requirements')
    else:
        print("❌ requirements.txt not found")
        return False

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    
    directories = ['uploads', 'templates', 'static']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")

def setup_environment():
    """Set up environment file"""
    print("⚙️ Setting up environment...")
    
    if not os.path.exists('.env'):
        if os.path.exists('env.example'):
            shutil.copy('env.example', '.env')
            print("✅ Created .env file from env.example")
            print("📝 Please edit .env file with your API keys")
        else:
            print("⚠️ env.example not found, creating basic .env file")
            with open('.env', 'w') as f:
                f.write("""# AI Contract Analyzer Environment Variables
SECRET_KEY=your-secret-key-here-change-this-in-production
OPENAI_API_KEY=your_openai_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
OPENAI_VISION_MODEL=gpt-4o-mini
OFFLINE_MODE=False
DEBUG=True
HOST=0.0.0.0
PORT=5001
""")
            print("✅ Created basic .env file")
            print("📝 Please edit .env file with your API keys")
    else:
        print("✅ .env file already exists")

def check_optional_dependencies():
    """Check for optional system dependencies"""
    print("🔍 Checking optional dependencies...")
    
    # Check for Tesseract
    if shutil.which('tesseract'):
        print("✅ Tesseract OCR is available")
    else:
        print("⚠️ Tesseract OCR not found (optional for OCR functionality)")
        print("   Install with: brew install tesseract (macOS) or apt-get install tesseract-ocr (Ubuntu)")
    
    # Check for Poppler
    if shutil.which('pdftoppm'):
        print("✅ Poppler is available")
    else:
        print("⚠️ Poppler not found (optional for PDF processing)")
        print("   Install with: brew install poppler (macOS) or apt-get install poppler-utils (Ubuntu)")

def main():
    """Main setup function"""
    print("🤖 AI Contract Analyzer Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        sys.exit(1)
    
    # Setup environment
    setup_environment()
    
    # Check optional dependencies
    check_optional_dependencies()
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Edit .env file with your API keys")
    print("2. Run: python app.py")
    print("3. Open http://localhost:5001 in your browser")
    print("\n💡 For demo mode without API keys, set OFFLINE_MODE=True in .env")

if __name__ == "__main__":
    main() 