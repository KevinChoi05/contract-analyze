# 🚀 AI Contract Analyzer Setup Guide

Welcome to the AI Contract Analyzer! This guide will help you get the application up and running quickly.

## 📋 Prerequisites

- **Python 3.8 or higher**
- **pip** (Python package installer)
- **Web browser** (Chrome, Firefox, Safari, Edge)

### Optional (for enhanced functionality):
- **Tesseract OCR** - for better text extraction from scanned documents
- **Poppler** - for advanced PDF processing

## 🛠️ Quick Start (Windows)

### Method 1: Using the Batch File (Recommended)
1. Double-click `start.bat`
2. The script will automatically:
   - Check Python installation
   - Install dependencies
   - Create configuration files
   - Start the application
3. Open your browser and go to `http://localhost:5001`

### Method 2: Manual Setup
1. Open Command Prompt in the project directory
2. Run: `python install_setup.py`
3. Edit `.env` file with your API keys
4. Run: `python app.py`
5. Open `http://localhost:5001` in your browser

## 🛠️ Quick Start (macOS/Linux)

1. Open Terminal in the project directory
2. Run: `python3 install_setup.py`
3. Edit `.env` file with your API keys
4. Run: `python3 app.py`
5. Open `http://localhost:5001` in your browser

## 🔑 API Keys Setup

### Required API Keys

1. **OpenAI API Key**
   - Visit: https://platform.openai.com/api-keys
   - Create a new API key
   - Add to `.env`: `OPENAI_API_KEY=your_key_here`

2. **DeepSeek API Key**
   - Visit: https://platform.deepseek.com/
   - Create a new API key
   - Add to `.env`: `DEEPSEEK_API_KEY=your_key_here`

### Demo Mode (No API Keys Required)

If you don't have API keys, you can run in demo mode:
1. Edit `.env` file
2. Set: `OFFLINE_MODE=True`
3. The application will use mock data for demonstration

## 📁 Project Structure

```
ai-contract-analyzer/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── install_setup.py      # Setup script
├── test_improvements.py  # Test suite
├── start.bat            # Windows startup script
├── .env                 # Environment variables (create from env.example)
├── env.example          # Example environment file
├── README.md            # Project documentation
├── templates/           # HTML templates
│   ├── base.html       # Base template
│   ├── login.html      # Login page
│   ├── register.html   # Registration page
│   └── index.html      # Main dashboard
└── uploads/            # Uploaded PDF files (auto-created)
```

## 🧪 Testing the Installation

Run the test suite to verify everything is working:

```bash
python test_improvements.py
```

This will test:
- ✅ Python dependencies
- ✅ Flask application
- ✅ Contract analyzer
- ✅ PDF processing
- ✅ Environment configuration

## 🎯 Usage Guide

### 1. Registration/Login
- Create a new account or log in with existing credentials
- User data is stored locally (no external database required)

### 2. Upload Contracts
- Drag & drop PDF files or click to browse
- Supported format: PDF only
- Maximum file size: 50MB

### 3. AI Analysis
- The system automatically extracts text from PDFs
- Uses multiple OCR engines for best results
- Analyzes contracts with GPT-4.1 Mini and DeepSeek v3
- Provides risk scoring and recommendations

### 4. Review Results
- View overall risk score (0-100)
- Examine individual risks with severity levels
- Check financial impact assessment
- Review legal obligations
- Get mitigation recommendations

## 🔧 Configuration Options

### Environment Variables (.env file)

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True
HOST=0.0.0.0
PORT=5001

# AI Models
OPENAI_API_KEY=your_openai_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
OPENAI_VISION_MODEL=gpt-4o-mini

# Application Settings
OFFLINE_MODE=False
MAX_CONTENT_LENGTH=52428800
UPLOAD_FOLDER=uploads
```

### Model Selection

- **gpt-4o-mini**: Fast, cost-effective (recommended)
- **gpt-4o**: Higher accuracy, more expensive
- **gpt-4**: Best accuracy, highest cost

## 🚨 Troubleshooting

### Common Issues

1. **"Module not found" errors**
   - Run: `pip install -r requirements.txt`

2. **"Port already in use" error**
   - Change PORT in .env file
   - Or kill the process using the port

3. **"API key invalid" errors**
   - Check your API keys in .env file
   - Ensure you have sufficient credits

4. **PDF upload fails**
   - Check file size (max 50MB)
   - Ensure file is a valid PDF
   - Try a different PDF file

5. **Analysis takes too long**
   - Large PDFs may take several minutes
   - Check your internet connection
   - Verify API key limits

### Getting Help

- Check the test results: `python test_improvements.py`
- Review the logs in the terminal
- Ensure all dependencies are installed
- Try running in demo mode first

## 🔒 Security Notes

- Change the default SECRET_KEY in production
- Keep your API keys secure
- Don't commit .env file to version control
- Use HTTPS in production environments

## 🚀 Production Deployment

For production use:

1. Set `DEBUG=False` in .env
2. Use a proper WSGI server (Gunicorn, uWSGI)
3. Set up HTTPS/SSL
4. Use a production database
5. Configure proper logging
6. Set up monitoring and backups

## 📞 Support

If you encounter issues:

1. Run the test suite: `python test_improvements.py`
2. Check the troubleshooting section above
3. Review the application logs
4. Try running in demo mode first

---

**Happy Contract Analyzing! 🤖📄** 