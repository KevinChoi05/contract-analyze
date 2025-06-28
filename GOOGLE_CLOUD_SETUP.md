# Google Cloud Document AI Setup Guide

This guide will help you set up Google Cloud Document AI for enterprise-grade OCR in your contract analyzer.

## 🎯 Benefits of Google Cloud Document AI

- **200+ languages** supported (vs. limited language support in open-source OCR)
- **Enterprise accuracy** (90%+ vs. 60-80% with basic OCR)
- **Handles complex documents** (forms, tables, handwriting)
- **Built-in preprocessing** (no manual image enhancement needed)
- **Scalable and reliable** (99.9% uptime SLA)
- **Cost-effective** (first 1000 pages/month free)

## 📋 Prerequisites

1. Google Cloud Platform account
2. Credit card for verification (free tier available)
3. Basic understanding of environment variables

## 🚀 Step-by-Step Setup

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click "Create Project"
3. Enter project name: `contract-analyzer-ocr`
4. Note your **Project ID** (needed for environment variables)

### Step 2: Enable Document AI API

1. In your project, go to **APIs & Services > Library**
2. Search for "Document AI API"
3. Click **Enable**

### Step 3: Create Document AI Processor

1. Go to **Document AI > Processors**
2. Click **Create Processor**
3. Select **Document OCR** (general text extraction)
4. Choose location: **us-central1** (recommended)
5. Name it: `contract-ocr-processor`
6. Note the **Processor ID** from the URL

### Step 4: Create Service Account

1. Go to **IAM & Admin > Service Accounts**
2. Click **Create Service Account**
3. Name: `contract-analyzer-ocr`
4. Grant role: **Document AI API User**
5. Click **Create and Continue**
6. Click **Done**

### Step 5: Generate Service Account Key

1. Click on your service account
2. Go to **Keys** tab
3. Click **Add Key > Create New Key**
4. Choose **JSON** format
5. Download the JSON file
6. **Keep this file secure!**

### Step 6: Configure Environment Variables

Add these to your Railway environment variables:

```bash
# Required
GOOGLE_CLOUD_PROJECT_ID=your-actual-project-id
GOOGLE_CLOUD_LOCATION=us
DOCUMENT_AI_PROCESSOR_ID=your-processor-id

# Service Account JSON (copy entire content)
GOOGLE_APPLICATION_CREDENTIALS_JSON={
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "...",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

## 🔧 Railway Deployment Configuration

### Option 1: Environment Variables (Recommended)

1. In Railway dashboard, go to your app
2. Click **Variables** tab
3. Add the variables above
4. Railway will automatically redeploy

### Option 2: Service Account File Upload

If you prefer uploading the JSON file:

1. Upload `service-account.json` to your repository
2. Set environment variable:
   ```bash
   GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
   ```
3. **⚠️ Security Warning**: Add to `.gitignore` to avoid committing credentials

## 💰 Pricing Information

- **Free Tier**: 1,000 pages per month
- **Paid Tier**: $1.50 per 1,000 pages
- **Typical Usage**: Small business processes ~100-500 documents/month
- **Cost Estimate**: $5-15/month for most users

## 🧪 Testing the Setup

After deployment, check your Railway logs for:

```
✅ Google Cloud Document AI initialized successfully
🚀 Using Google Cloud Document AI for OCR
```

If you see this instead:
```
❌ Google Cloud Document AI not available
📄 Using fallback OCR (PyMuPDF only)
```

Check your environment variables and service account permissions.

## 🔍 Troubleshooting

### Common Issues

1. **"Permission denied"**
   - Check service account has "Document AI API User" role
   - Verify processor ID is correct

2. **"Project not found"**
   - Ensure Project ID matches exactly
   - Check API is enabled

3. **"Invalid credentials"**
   - Verify JSON format is correct
   - Check for extra spaces or line breaks

4. **"Processor not found"**
   - Confirm processor ID from the URL
   - Ensure location matches (us, eu, asia)

### Debug Steps

1. Check Railway logs for specific error messages
2. Verify all environment variables are set
3. Test with a simple PDF first
4. Contact support if issues persist

## 🎉 Success!

Once configured, your app will:
- Handle **any document type** (scanned, digital, handwritten)
- Process **multiple languages** automatically
- Provide **enterprise-grade accuracy**
- Work reliably at scale

Your mom's W-4 and I-9 forms should now process perfectly! 🚀

## 📞 Support

- [Google Cloud Documentation](https://cloud.google.com/document-ai/docs)
- [Railway Support](https://railway.app/help)
- [GitHub Issues](https://github.com/your-repo/issues) 