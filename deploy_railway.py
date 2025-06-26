#!/usr/bin/env python3
"""
Railway Deployment Script for AI Contract Analyzer
This script helps deploy the application to Railway.
"""

import os
import subprocess
import json

def create_railway_json():
    """Create railway.json configuration"""
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
    print("✅ Created railway.json")

def create_nixpacks_toml():
    """Create nixpacks.toml for Railway"""
    config = """[phases.setup]
nixPkgs = ["tesseract", "poppler_utils"]

[phases.install]
cmds = ["pip install -r requirements.txt"]

[phases.build]
cmds = ["echo 'Build completed'"]

[start]
cmd = "gunicorn app:app --bind 0.0.0.0:$PORT --workers 4 --timeout 120"
"""
    
    with open('nixpacks.toml', 'w') as f:
        f.write(config)
    print("✅ Created nixpacks.toml")

def deploy_to_railway():
    """Deploy to Railway"""
    print("🚀 Deploying to Railway...")
    
    # Check if Railway CLI is installed
    try:
        subprocess.run(['railway', '--version'], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Railway CLI not found. Please install it first:")
        print("   npm install -g @railway/cli")
        return False
    
    # Login to Railway
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
    
    # Set environment variables
    env_vars = {
        'FLASK_ENV': 'production',
        'OFFLINE_MODE': 'False'
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
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Deployment failed: {e}")
        return False

def main():
    """Main deployment function"""
    print("🎯 Railway Deployment Setup")
    print("=" * 40)
    
    # Create necessary files
    create_railway_json()
    create_nixpacks_toml()
    
    print("\n📋 Next steps:")
    print("1. Install Railway CLI: npm install -g @railway/cli")
    print("2. Set your API keys in Railway dashboard:")
    print("   - OPENAI_API_KEY")
    print("   - DEEPSEEK_API_KEY")
    print("   - SECRET_KEY")
    print("3. Deploy: python deploy_railway.py --deploy")
    print("4. Or deploy manually:")
    print("   railway login")
    print("   railway init")
    print("   railway deploy")
    
    # Check if --deploy flag is provided
    if '--deploy' in os.sys.argv:
        deploy_to_railway()

if __name__ == "__main__":
    main() 