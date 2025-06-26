#!/usr/bin/env python3
"""
Simple Railway Deployment Guide
This script will guide you through deploying your AI Contract Analyzer to Railway.
"""

import os
import subprocess
import sys
import time

def print_step(step_num, title, description):
    print(f"\n{'='*60}")
    print(f"STEP {step_num}: {title}")
    print(f"{'='*60}")
    print(description)
    print()

def check_git():
    """Check if Git is installed and configured"""
    try:
        result = subprocess.run(['git', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Git is installed")
            return True
        else:
            print("✗ Git is not installed")
            return False
    except FileNotFoundError:
        print("✗ Git is not installed")
        return False

def init_git_repo():
    """Initialize Git repository if not already done"""
    if not os.path.exists('.git'):
        print("Initializing Git repository...")
        subprocess.run(['git', 'init'])
        subprocess.run(['git', 'add', '.'])
        subprocess.run(['git', 'commit', '-m', 'Initial commit'])
        print("✓ Git repository initialized")
    else:
        print("✓ Git repository already exists")

def main():
    print("🚀 Railway Deployment Guide for AI Contract Analyzer")
    print("This will guide you through deploying your app to Railway.")
    
    # Check prerequisites
    print_step(1, "Check Prerequisites", 
               "Let's make sure you have everything needed for deployment.")
    
    if not check_git():
        print("❌ Git is required for deployment.")
        print("Please install Git from: https://git-scm.com/downloads")
        print("After installing Git, run this script again.")
        return
    
    # Initialize Git
    print_step(2, "Initialize Git Repository",
               "Setting up Git repository for deployment...")
    init_git_repo()
    
    # Create GitHub repository
    print_step(3, "Create GitHub Repository",
               "You need to create a GitHub repository to host your code.")
    print("1. Go to https://github.com/new")
    print("2. Choose a repository name (e.g., 'ai-contract-analyzer')")
    print("3. Make it PUBLIC (Railway needs access)")
    print("4. Don't initialize with README (we already have files)")
    print("5. Click 'Create repository'")
    
    repo_name = input("\nEnter your GitHub repository name: ").strip()
    if not repo_name:
        print("❌ Repository name is required.")
        return
    
    github_username = input("Enter your GitHub username: ").strip()
    if not github_username:
        print("❌ GitHub username is required.")
        return
    
    # Add remote and push
    print_step(4, "Push Code to GitHub",
               "Pushing your code to GitHub...")
    
    remote_url = f"https://github.com/{github_username}/{repo_name}.git"
    
    try:
        # Remove existing remote if any
        subprocess.run(['git', 'remote', 'remove', 'origin'], 
                      capture_output=True)
        
        # Add new remote
        subprocess.run(['git', 'remote', 'add', 'origin', remote_url])
        print(f"✓ Added remote: {remote_url}")
        
        # Push to GitHub
        print("Pushing code to GitHub...")
        subprocess.run(['git', 'push', '-u', 'origin', 'main'])
        print("✓ Code pushed to GitHub successfully!")
        
    except Exception as e:
        print(f"❌ Error pushing to GitHub: {e}")
        print("Please make sure:")
        print("1. The repository exists on GitHub")
        print("2. You have the correct permissions")
        print("3. You're authenticated with GitHub")
        return
    
    # Railway deployment
    print_step(5, "Deploy to Railway",
               "Now let's deploy your app to Railway.")
    print("1. Go to https://railway.app/")
    print("2. Sign in with your GitHub account")
    print("3. Click 'New Project'")
    print("4. Select 'Deploy from GitHub repo'")
    print("5. Choose your repository:", repo_name)
    print("6. Railway will automatically detect it's a Python app")
    print("7. Click 'Deploy Now'")
    
    input("\nPress Enter when you've started the Railway deployment...")
    
    # Environment variables
    print_step(6, "Configure Environment Variables",
               "You need to set up environment variables in Railway.")
    print("In your Railway project dashboard:")
    print("1. Go to the 'Variables' tab")
    print("2. Add the following environment variables:")
    print()
    print("   SECRET_KEY=your-secret-key-here")
    print("   FLASK_ENV=production")
    print("   OFFLINE_MODE=true")
    print()
    print("Optional (for full AI functionality):")
    print("   OPENAI_API_KEY=your-openai-api-key")
    print("   DEEPSEEK_API_KEY=your-deepseek-api-key")
    print()
    print("Note: Set OFFLINE_MODE=true for demo mode (no API keys needed)")
    
    input("\nPress Enter when you've configured the environment variables...")
    
    # Wait for deployment
    print_step(7, "Wait for Deployment",
               "Railway is now building and deploying your app...")
    print("This usually takes 2-5 minutes.")
    print("You can monitor the progress in your Railway dashboard.")
    
    # Final instructions
    print_step(8, "Access Your App",
               "Once deployment is complete:")
    print("1. Go to your Railway project dashboard")
    print("2. Click on your deployed service")
    print("3. You'll see a URL like: https://your-app-name.railway.app")
    print("4. Click the URL to access your AI Contract Analyzer!")
    print()
    print("🎉 Your AI Contract Analyzer is now live!")
    print()
    print("Demo Features:")
    print("- Upload PDF contracts")
    print("- Get AI-powered risk analysis")
    print("- User authentication system")
    print("- Modern web interface")
    print()
    print("To enable full AI functionality:")
    print("1. Get API keys from OpenAI and DeepSeek")
    print("2. Add them to Railway environment variables")
    print("3. Set OFFLINE_MODE=false")
    print("4. Redeploy your app")

if __name__ == "__main__":
    main() 