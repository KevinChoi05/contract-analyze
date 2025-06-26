#!/usr/bin/env python3
"""
Quick Deployment Script for AI Contract Analyzer
This script helps you deploy your application quickly to Railway (recommended).
"""

import os
import subprocess
import sys
import json

def check_prerequisites():
    """Check if required tools are installed"""
    print("🔍 Checking prerequisites...")
    
    # Check Python
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Check Git
    try:
        subprocess.run(['git', '--version'], check=True, capture_output=True)
        print("✅ Git is installed")
    except:
        print("❌ Git is not installed. Please install Git first.")
        return False
    
    # Check Node.js (for Railway CLI)
    try:
        subprocess.run(['node', '--version'], check=True, capture_output=True)
        print("✅ Node.js is installed")
    except:
        print("❌ Node.js is not installed. Please install Node.js first.")
        print("   Download from: https://nodejs.org/")
        return False
    
    return True

def setup_git():
    """Set up Git repository if not already done"""
    if not os.path.exists('.git'):
        print("📁 Initializing Git repository...")
        try:
            subprocess.run(['git', 'init'], check=True)
            subprocess.run(['git', 'add', '.'], check=True)
            subprocess.run(['git', 'commit', '-m', 'Initial commit'], check=True)
            print("✅ Git repository initialized")
        except subprocess.CalledProcessError as e:
            print(f"❌ Git setup failed: {e}")
            return False
    else:
        print("✅ Git repository already exists")
    
    return True

def install_railway_cli():
    """Install Railway CLI"""
    print("📦 Installing Railway CLI...")
    try:
        subprocess.run(['npm', 'install', '-g', '@railway/cli'], check=True)
        print("✅ Railway CLI installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Railway CLI installation failed: {e}")
        return False

def create_railway_config():
    """Create Railway configuration files"""
    print("⚙️ Creating Railway configuration...")
    
    # Create railway.json
    config = {
        "$schema": "https://railway.app/railway.schema.json",
        "build": {
            "builder": "NIXPACKS"
        },
        "deploy": {
            "startCommand": "gunicorn app:app --bind 0.0.0.0:$PORT --workers 4 --timeout 120",
            "healthcheckPath": "/health",
            "healthcheckTimeout": 300,
            "restartPolicyType": "ON_FAILURE",
            "restartPolicyMaxRetries": 10
        }
    }
    
    with open('railway.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    # Create nixpacks.toml
    nixpacks_config = """[phases.setup]
nixPkgs = ["tesseract", "poppler_utils"]

[phases.install]
cmds = ["pip install -r requirements.txt"]

[phases.build]
cmds = ["echo 'Build completed'"]

[start]
cmd = "gunicorn app:app --bind 0.0.0.0:$PORT --workers 4 --timeout 120"
"""
    
    with open('nixpacks.toml', 'w') as f:
        f.write(nixpacks_config)
    
    print("✅ Railway configuration created")

def deploy_to_railway():
    """Deploy to Railway"""
    print("🚀 Deploying to Railway...")
    
    # Login to Railway
    print("🔐 Please log in to Railway...")
    try:
        subprocess.run(['railway', 'login'], check=True)
        print("✅ Logged in to Railway")
    except subprocess.CalledProcessError:
        print("❌ Railway login failed")
        return False
    
    # Initialize Railway project
    try:
        subprocess.run(['railway', 'init'], check=True)
        print("✅ Railway project initialized")
    except subprocess.CalledProcessError:
        print("⚠️ Railway project initialization failed (might already exist)")
    
    # Set basic environment variables
    env_vars = {
        'FLASK_ENV': 'production',
        'OFFLINE_MODE': 'True'  # Start in demo mode
    }
    
    for key, value in env_vars.items():
        try:
            subprocess.run(['railway', 'variables', 'set', f'{key}={value}'], check=True)
            print(f"✅ Set {key}={value}")
        except subprocess.CalledProcessError:
            print(f"⚠️ Failed to set {key}")
    
    # Deploy
    try:
        subprocess.run(['railway', 'deploy'], check=True)
        print("✅ Deployed to Railway")
        
        # Get the URL
        result = subprocess.run(['railway', 'domain'], check=True, capture_output=True, text=True)
        domain = result.stdout.strip()
        if domain:
            print(f"🌐 Your app is available at: https://{domain}")
            print(f"📧 Share this URL with others: https://{domain}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Deployment failed: {e}")
        return False

def main():
    """Main deployment function"""
    print("🎯 AI Contract Analyzer - Quick Deployment")
    print("=" * 50)
    print("This script will deploy your app to Railway (free tier available)")
    print()
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Please install the required tools.")
        return
    
    # Setup Git
    if not setup_git():
        print("\n❌ Git setup failed.")
        return
    
    # Install Railway CLI
    if not install_railway_cli():
        print("\n❌ Railway CLI installation failed.")
        return
    
    # Create Railway config
    create_railway_config()
    
    # Deploy
    if deploy_to_railway():
        print("\n🎉 Deployment successful!")
        print("\n📋 Next steps:")
        print("1. Your app is now live and accessible to everyone!")
        print("2. To enable full AI analysis, set your API keys in Railway dashboard:")
        print("   - OPENAI_API_KEY")
        print("   - DEEPSEEK_API_KEY")
        print("3. To add a custom domain, use: railway domain")
        print("4. To view logs: railway logs")
        print("5. To update the app: git push && railway deploy")
        
        print("\n💡 The app is currently running in demo mode (no API keys required)")
        print("   Users can test the interface with mock data")
    else:
        print("\n❌ Deployment failed. Please check the errors above.")

if __name__ == "__main__":
    main() 