#!/usr/bin/env python3
"""
Heroku Deployment Script for AI Contract Analyzer
This script helps deploy the application to Heroku.
"""

import os
import subprocess
import json

def create_procfile():
    """Create Procfile for Heroku"""
    with open('Procfile', 'w') as f:
        f.write('web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 4 --timeout 120\n')
    print("✅ Created Procfile")

def create_runtime_txt():
    """Create runtime.txt for Heroku"""
    with open('runtime.txt', 'w') as f:
        f.write('python-3.11.7\n')
    print("✅ Created runtime.txt")

def create_app_json():
    """Create app.json for Heroku"""
    app_config = {
        "name": "AI Contract Analyzer",
        "description": "AI-powered contract risk analysis using GPT-4.1 Mini & DeepSeek v3",
        "repository": "https://github.com/yourusername/ai-contract-analyzer",
        "logo": "https://raw.githubusercontent.com/yourusername/ai-contract-analyzer/main/logo.png",
        "keywords": ["python", "flask", "ai", "contract", "analysis", "openai", "deepseek"],
        "env": {
            "SECRET_KEY": {
                "description": "Flask secret key",
                "generator": "secret"
            },
            "OPENAI_API_KEY": {
                "description": "OpenAI API key for GPT-4.1 Mini",
                "required": True
            },
            "DEEPSEEK_API_KEY": {
                "description": "DeepSeek API key for analysis",
                "required": True
            },
            "OFFLINE_MODE": {
                "description": "Run in demo mode without API keys",
                "value": "False"
            },
            "FLASK_ENV": {
                "description": "Flask environment",
                "value": "production"
            }
        },
        "formation": {
            "web": {
                "quantity": 1,
                "size": "basic"
            }
        },
        "addons": [
            {
                "plan": "heroku-postgresql:mini"
            },
            {
                "plan": "heroku-redis:mini"
            }
        ],
        "buildpacks": [
            {
                "url": "heroku/python"
            }
        ]
    }
    
    with open('app.json', 'w') as f:
        json.dump(app_config, f, indent=2)
    print("✅ Created app.json")

def create_heroku_ignore():
    """Create .herokuignore file"""
    ignore_content = """# Development files
*.pyc
__pycache__/
*.pyo
*.pyd
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt

# IDE files
.vscode/
.idea/
*.swp
*.swo
*~

# OS files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs
*.log
logs/

# Uploads (will be handled by cloud storage in production)
uploads/

# Test files
test_*.py
*_test.py

# Documentation
README.md
SETUP_GUIDE.md
docs/

# Local configuration
.env
.env.local
"""
    
    with open('.herokuignore', 'w') as f:
        f.write(ignore_content)
    print("✅ Created .herokuignore")

def deploy_to_heroku():
    """Deploy to Heroku"""
    print("🚀 Deploying to Heroku...")
    
    # Check if Heroku CLI is installed
    try:
        subprocess.run(['heroku', '--version'], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Heroku CLI not found. Please install it first:")
        print("   https://devcenter.heroku.com/articles/heroku-cli")
        return False
    
    # Create Heroku app
    try:
        subprocess.run(['heroku', 'create'], check=True)
        print("✅ Heroku app created")
    except subprocess.CalledProcessError:
        print("⚠️ Heroku app creation failed (might already exist)")
    
    # Set environment variables
    env_vars = [
        'FLASK_ENV=production',
        'OFFLINE_MODE=False'
    ]
    
    for var in env_vars:
        try:
            subprocess.run(['heroku', 'config:set', var], check=True)
            print(f"✅ Set {var}")
        except subprocess.CalledProcessError:
            print(f"⚠️ Failed to set {var}")
    
    # Add PostgreSQL addon
    try:
        subprocess.run(['heroku', 'addons:create', 'heroku-postgresql:mini'], check=True)
        print("✅ Added PostgreSQL addon")
    except subprocess.CalledProcessError:
        print("⚠️ PostgreSQL addon creation failed")
    
    # Add Redis addon
    try:
        subprocess.run(['heroku', 'addons:create', 'heroku-redis:mini'], check=True)
        print("✅ Added Redis addon")
    except subprocess.CalledProcessError:
        print("⚠️ Redis addon creation failed")
    
    # Deploy
    try:
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Deploy to Heroku'], check=True)
        subprocess.run(['git', 'push', 'heroku', 'main'], check=True)
        print("✅ Deployed to Heroku")
        
        # Open the app
        subprocess.run(['heroku', 'open'], check=True)
        print("✅ Opened app in browser")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Deployment failed: {e}")
        return False

def main():
    """Main deployment function"""
    print("🎯 Heroku Deployment Setup")
    print("=" * 40)
    
    # Create necessary files
    create_procfile()
    create_runtime_txt()
    create_app_json()
    create_heroku_ignore()
    
    print("\n📋 Next steps:")
    print("1. Set your API keys:")
    print("   heroku config:set OPENAI_API_KEY=your_key")
    print("   heroku config:set DEEPSEEK_API_KEY=your_key")
    print("2. Deploy: python deploy_heroku.py --deploy")
    print("3. Or deploy manually:")
    print("   git add .")
    print("   git commit -m 'Deploy to Heroku'")
    print("   git push heroku main")
    
    # Check if --deploy flag is provided
    if '--deploy' in os.sys.argv:
        deploy_to_heroku()

if __name__ == "__main__":
    main() 