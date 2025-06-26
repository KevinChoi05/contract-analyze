# 🚀 AI Contract Analyzer Deployment Guide

This guide covers deploying the AI Contract Analyzer to various platforms so people can use it online.

## 📋 Prerequisites

- **Git repository** with your code
- **API keys** for OpenAI and DeepSeek
- **Domain name** (optional but recommended)

## 🎯 Quick Deployment Options

### 1. Railway (Recommended - Free Tier Available)
**Best for: Quick deployment, free tier, automatic scaling**

```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
python deploy_railway.py --deploy
```

**Pros:**
- ✅ Free tier available
- ✅ Automatic HTTPS
- ✅ Built-in database and Redis
- ✅ Easy environment variable management
- ✅ Automatic deployments from Git

**Cons:**
- ❌ Limited free tier resources
- ❌ Requires credit card for verification

### 2. Heroku (Popular - Paid)
**Best for: Enterprise, reliability, extensive add-ons**

```bash
# Install Heroku CLI
# Download from: https://devcenter.heroku.com/articles/heroku-cli

# Deploy
python deploy_heroku.py --deploy
```

**Pros:**
- ✅ Very reliable
- ✅ Extensive add-on ecosystem
- ✅ Good documentation
- ✅ Automatic scaling

**Cons:**
- ❌ No free tier (discontinued)
- ❌ Can be expensive for high traffic

### 3. Docker + VPS (Most Control)
**Best for: Full control, cost-effective, custom domains**

```bash
# Build and run with Docker Compose
docker-compose up -d
```

**Pros:**
- ✅ Full control over infrastructure
- ✅ Cost-effective for high traffic
- ✅ Custom domain and SSL
- ✅ No platform limitations

**Cons:**
- ❌ Requires server management
- ❌ More complex setup
- ❌ Need to handle SSL manually

## 🐳 Docker Deployment

### Local Docker Setup

1. **Build the image:**
```bash
docker build -t ai-contract-analyzer .
```

2. **Run with Docker Compose:**
```bash
docker-compose up -d
```

3. **Access the application:**
```
http://localhost:5001
```

### Production Docker Deployment

1. **Set up a VPS** (DigitalOcean, AWS, Google Cloud, etc.)

2. **Install Docker and Docker Compose:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker
```

3. **Clone your repository:**
```bash
git clone https://github.com/yourusername/ai-contract-analyzer.git
cd ai-contract-analyzer
```

4. **Create production environment file:**
```bash
cp env.example .env
# Edit .env with your production settings
```

5. **Set up SSL with Let's Encrypt:**
```bash
# Install Certbot
sudo apt install certbot

# Get SSL certificate
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates to ssl directory
sudo mkdir -p ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem
sudo chown -R $USER:$USER ssl/
```

6. **Deploy:**
```bash
docker-compose up -d
```

## ☁️ Cloud Platform Deployments

### Railway Deployment

1. **Create Railway account** at https://railway.app

2. **Install Railway CLI:**
```bash
npm install -g @railway/cli
```

3. **Deploy:**
```bash
python deploy_railway.py --deploy
```

4. **Set environment variables in Railway dashboard:**
- `OPENAI_API_KEY`
- `DEEPSEEK_API_KEY`
- `SECRET_KEY`
- `FLASK_ENV=production`

### Heroku Deployment

1. **Create Heroku account** at https://heroku.com

2. **Install Heroku CLI:**
```bash
# Download from: https://devcenter.heroku.com/articles/heroku-cli
```

3. **Deploy:**
```bash
python deploy_heroku.py --deploy
```

4. **Set environment variables:**
```bash
heroku config:set OPENAI_API_KEY=your_key
heroku config:set DEEPSEEK_API_KEY=your_key
heroku config:set SECRET_KEY=your_secret
```

### Render Deployment

1. **Create Render account** at https://render.com

2. **Connect your GitHub repository**

3. **Create a new Web Service**

4. **Configure:**
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 4 --timeout 120`
- **Environment Variables:**
  - `OPENAI_API_KEY`
  - `DEEPSEEK_API_KEY`
  - `SECRET_KEY`
  - `FLASK_ENV=production`

### DigitalOcean App Platform

1. **Create DigitalOcean account**

2. **Create a new App**

3. **Connect your GitHub repository**

4. **Configure:**
- **Build Command:** `pip install -r requirements.txt`
- **Run Command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 4 --timeout 120`
- **Environment Variables:** Set all required variables

## 🔧 Environment Configuration

### Required Environment Variables

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=production
DEBUG=False

# AI API Keys
OPENAI_API_KEY=your_openai_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
OPENAI_VISION_MODEL=gpt-4o-mini

# Database Configuration (for production)
DB_TYPE=postgres  # or sqlite
DB_HOST=localhost
DB_PORT=5432
DB_NAME=contract_analyzer
DB_USER=contract_user
DB_PASSWORD=contract_password

# Redis Configuration (optional)
REDIS_URL=redis://localhost:6379/0

# Application Settings
OFFLINE_MODE=False
MAX_CONTENT_LENGTH=52428800
UPLOAD_FOLDER=uploads
```

### Demo Mode (No API Keys)

For demonstration purposes, you can run without API keys:

```bash
OFFLINE_MODE=True
```

This will use mock data for analysis.

## 🔒 Security Considerations

### Production Security Checklist

- [ ] **Change default SECRET_KEY**
- [ ] **Use HTTPS/SSL**
- [ ] **Set up proper CORS headers**
- [ ] **Implement rate limiting**
- [ ] **Use environment variables for secrets**
- [ ] **Set up proper logging**
- [ ] **Configure backup strategy**
- [ ] **Set up monitoring**

### SSL/HTTPS Setup

**For Docker deployment:**
```bash
# Use Let's Encrypt
sudo certbot certonly --standalone -d yourdomain.com
```

**For cloud platforms:**
- Railway: Automatic HTTPS
- Heroku: Automatic HTTPS
- Render: Automatic HTTPS
- DigitalOcean: Automatic HTTPS

## 📊 Monitoring and Logging

### Application Logs

The application logs to `logs/app.log` and stdout. In production:

```bash
# View logs
docker-compose logs -f web

# Or for cloud platforms
railway logs
heroku logs --tail
```

### Health Checks

The application includes a health check endpoint:

```
GET /health
```

Returns:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00",
  "version": "1.0.0"
}
```

## 🔄 Continuous Deployment

### GitHub Actions (Example)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Railway

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
        with:
          node-version: '16'
      - run: npm install -g @railway/cli
      - run: railway login --token ${{ secrets.RAILWAY_TOKEN }}
      - run: railway deploy
```

## 💰 Cost Estimation

### Monthly Costs (Approximate)

| Platform | Free Tier | Paid Tier | Notes |
|----------|-----------|-----------|-------|
| Railway | ✅ Yes | $5-20/month | Good for small to medium traffic |
| Heroku | ❌ No | $7-25/month | Reliable, good support |
| Render | ✅ Yes | $7-25/month | Good free tier |
| DigitalOcean | ❌ No | $5-20/month | Full control |
| VPS + Docker | ❌ No | $5-50/month | Most cost-effective for high traffic |

### API Costs

- **OpenAI GPT-4o-mini:** ~$0.15 per 1M tokens
- **DeepSeek:** ~$0.14 per 1M tokens
- **Typical contract analysis:** $0.01-0.05 per document

## 🚨 Troubleshooting

### Common Deployment Issues

1. **"Module not found" errors**
   - Ensure all dependencies are in `requirements.txt`
   - Check Python version compatibility

2. **"Port already in use"**
   - Change PORT environment variable
   - Check if another service is using the port

3. **"API key invalid"**
   - Verify API keys are correct
   - Check API key permissions and credits

4. **"Database connection failed"**
   - Verify database credentials
   - Check if database service is running

5. **"SSL certificate errors"**
   - Ensure SSL certificates are properly configured
   - Check domain DNS settings

### Getting Help

- Check application logs
- Verify environment variables
- Test locally first
- Use demo mode for testing

## 📈 Scaling Considerations

### For High Traffic

1. **Database scaling:**
   - Use managed PostgreSQL (AWS RDS, Google Cloud SQL)
   - Implement connection pooling

2. **Caching:**
   - Use Redis for session storage
   - Implement result caching

3. **File storage:**
   - Use cloud storage (AWS S3, Google Cloud Storage)
   - Implement CDN for static files

4. **Load balancing:**
   - Use multiple application instances
   - Implement health checks

## 🎉 Success Metrics

After deployment, monitor:

- **Uptime:** >99.9%
- **Response time:** <2 seconds
- **Error rate:** <1%
- **User satisfaction:** High ratings
- **API usage:** Within limits

---

**Your AI Contract Analyzer is now ready for the world! 🌍**

For support, check the troubleshooting section or create an issue in the repository. 