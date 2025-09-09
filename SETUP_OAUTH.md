# OAuth Setup Guide for SVG2PPTX API

This guide will help you set up Google OAuth authentication for the SVG2PPTX API, enabling the system to access Google Drive and Google Slides on behalf of users.

## Prerequisites

- Google Cloud Platform account
- Python 3.9+ with virtual environment
- SVG2PPTX API codebase

## Step 1: Google Cloud Console Setup

### 1.1 Create or Select a Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your project ID for reference

### 1.2 Enable Required APIs

Navigate to **APIs & Services → Library** and enable these APIs:

- ✅ **Google Drive API** - For file upload and management
- ✅ **Google Slides API** - For PNG preview generation
- ✅ **Google Sheets API** (optional) - For future features

```bash
# You can also enable via gcloud CLI:
gcloud services enable drive.googleapis.com
gcloud services enable slides.googleapis.com
```

### 1.3 Configure OAuth Consent Screen

1. Go to **APIs & Services → OAuth consent screen**
2. Choose **External** (unless you have Google Workspace)
3. Fill in required information:
   - **App name**: SVG2PPTX Converter
   - **User support email**: Your email
   - **Developer contact**: Your email
4. Add scopes:
   - `https://www.googleapis.com/auth/drive.file`
   - `https://www.googleapis.com/auth/drive.metadata`
   - `https://www.googleapis.com/auth/presentations.readonly`
5. Add test users (your email and any other testers)

### 1.4 Create OAuth Credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. Choose **Desktop application**
4. Name it: **SVG2PPTX Desktop Client**
5. Click **Create**
6. Download the JSON file or copy the Client ID and Secret

## Step 2: Environment Configuration

### 2.1 Create .env File

Create a `.env` file in your project root:

```bash
# API Configuration
API_SECRET_KEY=your-secure-api-key-here

# Google OAuth Configuration
GOOGLE_DRIVE_AUTH_METHOD=oauth
GOOGLE_DRIVE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_DRIVE_CLIENT_SECRET=your-client-secret

# Optional: Customize token storage
GOOGLE_DRIVE_TOKEN_FILE=./credentials/token.json
```

### 2.2 Secure Your Credentials

```bash
# Create credentials directory
mkdir -p credentials

# Set appropriate permissions
chmod 700 credentials
chmod 600 .env

# Add to .gitignore
echo "credentials/" >> .gitignore
echo ".env" >> .gitignore
```

## Step 3: Setup Script

We provide an interactive setup script:

```bash
# Run the OAuth setup wizard
source venv/bin/activate
python -c "from api.services.google_oauth import setup_oauth_credentials; setup_oauth_credentials()"
```

The script will:
1. Guide you through the Google Cloud Console setup
2. Prompt for your OAuth credentials
3. Update your `.env` file automatically
4. Test the OAuth flow

## Step 4: Test Authentication

### 4.1 Test OAuth Flow

```bash
# Test the complete OAuth setup
source venv/bin/activate
python -c "from api.services.google_oauth import test_oauth_setup; test_oauth_setup()"
```

This will:
- Open a browser for OAuth authentication
- Save the token for future use
- Display your authenticated user info

### 4.2 Manual Testing

```python
from api.services.google_oauth import GoogleOAuthService

# Initialize OAuth service
oauth_service = GoogleOAuthService()

# Test credentials
if oauth_service.test_credentials():
    print("✅ OAuth setup successful!")
    user_info = oauth_service.get_user_info()
    print(f"Authenticated as: {user_info['displayName']}")
else:
    print("❌ OAuth setup failed")
```

## Step 5: API Server Startup

### 5.1 Start the Development Server

```bash
# Activate virtual environment
source venv/bin/activate

# Set environment variables (if not using .env file)
export API_SECRET_KEY=your-api-key
export GOOGLE_DRIVE_AUTH_METHOD=oauth
export GOOGLE_DRIVE_CLIENT_ID=your-client-id
export GOOGLE_DRIVE_CLIENT_SECRET=your-client-secret

# Start the server
uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
```

### 5.2 Test API Endpoints

Visit: http://localhost:8001/docs

Test with curl:

```bash
# Test health endpoint
curl -X GET "http://localhost:8001/health"

# Test conversion (replace with your API key and a real SVG URL)
curl -X POST "http://localhost:8001/convert" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/test.svg"}'
```

## Troubleshooting

### Common Issues

#### 1. "Address already in use" Error
```bash
# Check what's using port 8080 (OAuth callback)
lsof -i :8080

# Kill the process or use a different port
# Modify the OAuth redirect URI in Google Cloud Console
```

#### 2. "Access denied" or "unauthorized_client"
- Verify OAuth consent screen is properly configured
- Check that your email is added as a test user
- Ensure all required scopes are added

#### 3. "Token refresh failed"
```bash
# Delete the token file and re-authenticate
rm credentials/token.json
python -c "from api.services.google_oauth import test_oauth_setup; test_oauth_setup()"
```

#### 4. "API not enabled" Error
```bash
# Enable required APIs
gcloud services enable drive.googleapis.com
gcloud services enable slides.googleapis.com
```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Then run your tests
```

### Getting Help

- Check the [Google Drive API Documentation](https://developers.google.com/drive/api)
- Review [OAuth 2.0 Setup Guide](https://developers.google.com/identity/protocols/oauth2)
- Examine application logs for detailed error messages

## Production Deployment

### Security Considerations

1. **Environment Variables**: Use secure environment variable management
2. **HTTPS Only**: Ensure all production URLs use HTTPS
3. **Token Storage**: Store tokens securely with proper encryption
4. **API Keys**: Use strong, unique API keys for each environment
5. **CORS**: Configure CORS appropriately for production domains

### OAuth Redirect URIs

For production, update your OAuth client in Google Cloud Console:

1. Go to **APIs & Services → Credentials**
2. Edit your OAuth client
3. Add production redirect URIs:
   - `https://your-domain.com/oauth/callback`
   - `http://localhost:8080` (keep for development)

## Summary

After completing this setup:

✅ Google Cloud project configured with required APIs  
✅ OAuth consent screen configured  
✅ OAuth credentials created  
✅ Environment variables set  
✅ Authentication tested  
✅ API server running  

Your SVG2PPTX API is now ready for use with Google Drive and Slides integration!