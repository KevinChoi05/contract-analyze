#!/usr/bin/env python3
"""
Railway Deployment Script for AI Contract Analyzer
This script helps deploy the application to Railway.
"""

import os
import subprocess
import json
import sys
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(message)s')

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
    logger.info("✅ Created railway.json")

def create_nixpacks_toml():
    """Create nixpacks.toml for Railway"""
    config = """[phases.install]
cmds = ["pip install -r requirements.txt"]

[start]
cmd = "gunicorn app:app --bind 0.0.0.0:$PORT --workers 4 --timeout 120"
"""
    
    with open('nixpacks.toml', 'w') as f:
        f.write(config.strip())
    logger.info("✅ Created nixpacks.toml")

def check_railway_cli():
    """Check if Railway CLI is installed"""
    try:
        result = subprocess.run(['railway', '--version'], capture_output=True, text=True, check=True)
        logger.info(f"✅ Railway CLI version: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("❌ Railway CLI not found. Install it with: npm install -g @railway/cli")
        return False

def deploy_to_railway():
    """Deploy to Railway"""
    if not check_railway_cli():
        return False
    
    try:
        # Login (interactive)
        subprocess.run(['railway', 'login'], check=True)
        logger.info("✅ Logged in to Railway")
    except subprocess.CalledProcessError:
        logger.error("❌ Railway login failed")
        return False
    
    try:
        # Init project if not exists
        subprocess.run(['railway', 'init'], check=True)
        logger.info("✅ Railway project initialized")
    except subprocess.CalledProcessError:
        logger.warning("⚠️ Project might already exist. Continuing...")
    
    # Set environment variables
    env_vars = {
        'FLASK_ENV': 'production',
        'OFFLINE_MODE': 'False',
        # Add project-specific vars with default or empty
        'SECRET_KEY': os.getenv('SECRET_KEY', 'generate_a_secure_key'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', ''),
        'DEEPSEEK_API_KEY': os.getenv('DEEPSEEK_API_KEY', ''),
        'GOOGLE_CLOUD_PROJECT_ID': os.getenv('GOOGLE_CLOUD_PROJECT_ID', ''),
        'DOCUMENT_AI_PROCESSOR_ID': os.getenv('DOCUMENT_AI_PROCESSOR_ID', ''),
        'GOOGLE_APPLICATION_CREDENTIALS_JSON': os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON', '')
    }
    
    for key, value in env_vars.items():
        if value:  # Only set if value present
            try:
                subprocess.run(['railway', 'variables', 'set', f'{key}={value}'], check=True)
                logger.info(f"✅ Set {key}")
            except subprocess.CalledProcessError:
                logger.warning(f"⚠️ Failed to set {key}")
        else:
            logger.info(f"ℹ️ {key} not set (provide via env or dashboard)")
    
    # Deploy using 'railway up' (updated CLI command)
    try:
        subprocess.run(['railway', 'up'], check=True)
        logger.info("✅ Deployed to Railway")
        
        # Get domain
        result = subprocess.run(['railway', 'domain'], capture_output=True, text=True, check=True)
        domain = result.stdout.strip()
        if domain:
            logger.info(f"🌐 App available at: https://{domain}")
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Deployment failed: {e}")
        return False

def main():
    """Main deployment function"""
    logger.info("🎯 Railway Deployment Setup")
    logger.info("=" * 40)
    
    # Create config files
    create_railway_json()
    create_nixpacks_toml()
    
    logger.info("\n📋 Next steps:")
    logger.info("1. Ensure Railway CLI is installed: npm install -g @railway/cli")
    logger.info("2. Set sensitive API keys in Railway dashboard or local env")
    logger.info("3. For database, add a PostgreSQL service via 'railway add'")
    logger.info("4. Deploy with: python deploy_railway.py --deploy")
    logger.info("   Or manually: railway login && railway init && railway up")
    
    if '--deploy' in sys.argv:
        deploy_to_railway()

if __name__ == "__main__":
    main()