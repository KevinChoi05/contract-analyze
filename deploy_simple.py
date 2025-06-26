#!/usr/bin/env python3
"""
Simple Deployment Guide for AI Contract Analyzer
This script guides you through manual deployment to Railway.
"""

import os
import subprocess
import webbrowser
import json

def check_git():
    """Check if Git is working"""
    try:
        subprocess.run(['git', '--version'], check=True, capture_output=True)
        return True
    except:
        return False

def setup_git_repo():
    """Set up Git repository"""
    print("📁 Setting up Git repository...")
    
    try:
        # Initialize Git if not already done
        if not os.path.exists('.git'):
            subprocess.run(['git', 'init'], check=True)
        
        # Add all files
        subprocess.run(['git', 'add', '.'], check=True)
        
        # Commit
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], check=True)
        
        print("✅ Git repository ready")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Git setup failed: {e}")
        return False

def create_railway_files():
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

def create_github_repo():
    """Guide user to create GitHub repository"""
    print("\n🌐 Step 1: Create GitHub Repository")
    print("=" * 40)
    print("1. Go to: https://github.com/new")
    print("2. Repository name: ai-contract-analyzer")
    print("3. Make it Public")
    print("4. Don't initialize with README (we already have files)")
    print("5. Click 'Create repository'")
    
    input("\nPress Enter when you've created the repository...")
    
    # Get repository URL
    repo_url = input("Enter your GitHub repository URL (e.g., https://github.com/username/ai-contract-analyzer): ")
    
    if repo_url:
        try:
            # Add remote and push
            subprocess.run(['git', 'remote', 'add', 'origin', repo_url], check=True)
            subprocess.run(['git', 'branch', '-M', 'main'], check=True)
            subprocess.run(['git', 'push', '-u', 'origin', 'main'], check=True)
            print("✅ Code pushed to GitHub")
            return repo_url
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to push to GitHub: {e}")
            return None
    
    return None

def deploy_to_railway():
    """Guide user through Railway deployment"""
    print("\n🚀 Step 2: Deploy to Railway")
    print("=" * 40)
    print("1. Go to: https://railway.app")
    print("2. Sign up with GitHub")
    print("3. Click 'New Project'")
    print("4. Select 'Deploy from GitHub repo'")
    print("5. Choose your 'ai-contract-analyzer' repository")
    print("6. Click 'Deploy Now'")
    
    print("\n⚙️ Environment Variables to set in Railway:")
    print("- FLASK_ENV = production")
    print("- OFFLINE_MODE = True")
    print("- SECRET_KEY = (Railway will generate this)")
    
    print("\n📋 To set environment variables:")
    print("1. Click on your project in Railway")
    print("2. Go to 'Variables' tab")
    print("3. Add each variable")
    
    input("\nPress Enter when you've started the deployment...")
    
    print("\n⏳ Railway will now:")
    print("- Build your application")
    print("- Install dependencies")
    print("- Start your server")
    print("- Give you a public URL")
    
    return True

def main():
    """Main deployment guide"""
    print("🎯 AI Contract Analyzer - Simple Deployment Guide")
    print("=" * 50)
    print("This will guide you through deploying to Railway manually")
    print()
    
    # Check Git
    if not check_git():
        print("❌ Git is not working. Please install Git first.")
        return
    
    # Setup Git repository
    if not setup_git_repo():
        print("❌ Git setup failed.")
        return
    
    # Create Railway files
    create_railway_files()
    
    # Create GitHub repository
    repo_url = create_github_repo()
    if not repo_url:
        print("❌ GitHub setup failed.")
        return
    
    # Deploy to Railway
    deploy_to_railway()
    
    print("\n🎉 Deployment Guide Complete!")
    print("\n📋 What happens next:")
    print("1. Railway will build your app (takes 2-5 minutes)")
    print("2. You'll get a URL like: https://your-app.railway.app")
    print("3. Share this URL with others!")
    
    print("\n💡 Your app will start in demo mode (no API keys needed)")
    print("   Users can test the interface with mock data")
    
    print("\n🔑 To enable full AI analysis later:")
    print("1. Get API keys from OpenAI and DeepSeek")
    print("2. Add them to Railway environment variables")
    print("3. Set OFFLINE_MODE = False")
    
    print("\n🌐 Your app will be live at the Railway URL!")
    print("   Check Railway dashboard for the exact URL")

if __name__ == "__main__":
    main() 