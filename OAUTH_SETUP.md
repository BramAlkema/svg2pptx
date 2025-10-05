# OAuth Setup Guide for svg2pptx (Developer Only)

## One-Time Setup (You Do This Once)

### 1. Create Google Cloud Project
- Go to https://console.cloud.google.com/
- Create new project: "svg2pptx-production"
- Note the project ID

### 2. Enable APIs
- Navigate to: https://console.cloud.google.com/apis/library
- Enable:
  - Google Drive API
  - Google Slides API

### 3. Configure OAuth Consent Screen
- Go to: https://console.cloud.google.com/apis/credentials/consent
- User Type: **External** (allows any Google user)
- App information:
  - App name: "SVG2PPTX"
  - User support email: your-email@example.com
  - Developer contact: your-email@example.com
- Scopes: Add these scopes:
  - `https://www.googleapis.com/auth/drive.file`
  - `https://www.googleapis.com/auth/presentations`
  - `openid`
  - `email`
  - `profile`
- Test users: (Leave empty for now - add later for testing)
- Click "SAVE AND CONTINUE" through all steps
- **Publishing status**: 
  - Initially: "Testing" (max 100 users)
  - Later: Click "PUBLISH APP" for unlimited users

### 4. Create OAuth Client ID
- Go to: https://console.cloud.google.com/apis/credentials
- Click "CREATE CREDENTIALS" → "OAuth client ID"
- Application type: **Web application**
- Name: "SVG2PPTX Web Client"
- Authorized redirect URIs:
  - http://localhost:8080/oauth2/callback (for local dev)
  - https://yourdomain.com/api/oauth2/callback (for production)
- Click "CREATE"
- **COPY the Client ID and Client Secret** - you'll need these

### 5. Configure Your App
```bash
# In your .env file:
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here
GOOGLE_REDIRECT_URI=http://localhost:8080/oauth2/callback
```

## User Flow (Automatic)

1. User clicks "Export to Google Drive" in your app
2. If not connected: User sees Google OAuth consent screen (ONE TIME)
3. User clicks "Allow" - YOUR app gets a refresh token
4. YOUR app stores the refresh token for this user
5. Next time: Silent - no consent screen needed

## Security Notes

- Client Secret goes in YOUR backend .env (never exposed to users)
- Each user's refresh token is stored encrypted in YOUR database
- Users only see the standard Google OAuth consent screen
- Your app name "SVG2PPTX" appears on the consent screen

## Production Checklist

- [ ] Create Google Cloud project
- [ ] Enable Drive & Slides APIs
- [ ] Configure OAuth consent screen
- [ ] Create Web OAuth client
- [ ] Add production redirect URI
- [ ] Publish OAuth consent screen (for >100 users)
- [ ] Add Client ID/Secret to .env
- [ ] Test with your Google account
- [ ] Deploy!
