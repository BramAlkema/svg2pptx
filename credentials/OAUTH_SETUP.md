# Google Drive OAuth Setup 🔐

This guide helps you set up **OAuth authentication** for Google Drive integration. OAuth is the **recommended method** for development and personal use as it's much easier to set up than service accounts.

## Quick Setup (Automated)

```bash
python setup_oauth.py
```

The script will guide you through the entire process!

## Manual Setup

### Step 1: Create OAuth Credentials

1. **Go to [Google Cloud Console](https://console.cloud.google.com/)**
2. **Create or select a project**
3. **Enable Google Drive API**:
   - Navigate to `APIs & Services` → `Library`
   - Search for "Google Drive API"
   - Click on it and press `Enable`

4. **Create OAuth Client ID**:
   - Go to `APIs & Services` → `Credentials`
   - Click `Create Credentials` → `OAuth client ID`
   - Choose `Desktop application`
   - Name: `SVG2PPTX Desktop Client`
   - Click `Create`

5. **Get Client ID and Secret**:
   - Copy the `Client ID` (ends with `.apps.googleusercontent.com`)
   - Copy the `Client Secret`

### Step 2: Configure Environment

Update your `.env` file with the OAuth credentials:

```bash
# Google Drive Configuration
GOOGLE_DRIVE_AUTH_METHOD=oauth
GOOGLE_DRIVE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_DRIVE_CLIENT_SECRET=your-client-secret
```

### Step 3: Test Authentication

```bash
python -c "from api.services.google_oauth import test_oauth_setup; test_oauth_setup()"
```

This will:
1. Open your web browser
2. Prompt you to sign in to Google
3. Ask for permission to access Google Drive
4. Save the authentication token automatically

## How OAuth Works

1. **First time**: Browser opens → Sign in to Google → Grant permissions → Token saved
2. **Subsequent uses**: Token automatically refreshed when needed
3. **Token storage**: Saved in `credentials/oauth-token.json` (gitignored)

## OAuth vs Service Account

| Feature | OAuth | Service Account |
|---------|--------|----------------|
| **Setup Complexity** | ✅ Easy | ❌ Complex |
| **Browser Required** | ✅ Yes (first time only) | ❌ No |
| **User Files Access** | ✅ Your Google Drive | ❌ Service account Drive |
| **Best For** | Development, Personal | Production, Servers |
| **File Sharing** | ✅ Files appear in your Drive | ❌ Need explicit sharing |

## Troubleshooting

### "OAuth client ID not configured"
- Make sure `GOOGLE_DRIVE_CLIENT_ID` and `GOOGLE_DRIVE_CLIENT_SECRET` are set in `.env`
- Verify the client ID ends with `.apps.googleusercontent.com`

### "Browser doesn't open"
- The authentication URL will be printed in the console
- Copy and paste it into your browser manually

### "Permission denied"
- Make sure you granted all requested permissions
- Try running: `python -c "from api.services.google_oauth import GoogleOAuthService; GoogleOAuthService().revoke_token()"` to reset

### "Token expired"
- Tokens automatically refresh, but if issues persist:
- Delete `credentials/oauth-token.json` and re-authenticate

## Security Notes

- ✅ OAuth tokens are stored locally and encrypted
- ✅ Tokens have limited scope (Google Drive access only)
- ✅ Tokens can be revoked anytime
- ✅ No sensitive credentials in your code

## Testing

After setup, test the full integration:

```bash
# Test OAuth authentication
python api/services/google_oauth.py

# Test Google Drive service
python api/services/google_drive.py

# Test full API
python -m uvicorn api.main:app --reload
# Then visit: http://localhost:8000/docs
```

## Next Steps

Once OAuth is working:
1. ✅ Your API can upload files to Google Drive
2. ✅ Files will appear in your personal Google Drive
3. ✅ Files are automatically shared with public view links
4. ✅ Ready to convert SVG files to PowerPoint presentations!

---

💡 **Tip**: OAuth setup is a one-time process. Once configured, the API will work seamlessly without requiring browser authentication for each request.