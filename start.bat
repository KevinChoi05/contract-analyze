@echo off
echo 🤖 AI Contract Analyzer
echo ======================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

REM Check if requirements are installed
echo 🔍 Checking dependencies...
python -c "import flask, openai" >nul 2>&1
if errorlevel 1 (
    echo 📦 Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Check if .env exists
if not exist .env (
    echo ⚙️ Creating .env file...
    if exist env.example (
        copy env.example .env
        echo ✅ Created .env from env.example
        echo 📝 Please edit .env file with your API keys
    ) else (
        echo ⚠️ env.example not found, creating basic .env
        echo SECRET_KEY=your-secret-key-here > .env
        echo OPENAI_API_KEY=your_openai_api_key_here >> .env
        echo DEEPSEEK_API_KEY=your_deepseek_api_key_here >> .env
        echo OFFLINE_MODE=False >> .env
        echo DEBUG=True >> .env
    )
)

REM Create uploads directory if it doesn't exist
if not exist uploads mkdir uploads

echo.
echo 🚀 Starting AI Contract Analyzer...
echo 📍 Server will be available at: http://localhost:5001
echo 💡 Press Ctrl+C to stop the server
echo.

python app.py

pause 