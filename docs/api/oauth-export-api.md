# OAuth & Export to Google Slides API

## Overview

The OAuth & Export API provides secure Google authentication and seamless export of PowerPoint presentations to Google Slides.

**Key Features:**
- Browser-based OAuth 2.0 authentication
- Secure token storage with encryption
- Single-call PPTX → Slides conversion
- Multi-user support
- Token auto-refresh

## Authentication Flow

### Developer Setup (One-Time)

1. Create OAuth credentials in Google Cloud Console
2. Configure environment variables:

```bash
GOOGLE_DRIVE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_DRIVE_CLIENT_SECRET=your-client-secret
```

### User Authentication (Once Per User)

1. **Start OAuth Flow**: Call `/oauth2/start` with user ID
2. **User Authorizes**: User visits returned URL and grants permission
3. **Callback**: Google redirects to `/oauth2/callback` with code
4. **Token Storage**: Refresh token encrypted and stored in `.env`
5. **Silent Operation**: All future exports use stored token

## API Endpoints

### OAuth Endpoints

#### POST /oauth2/start

Start OAuth flow for a user.

**Request Body:**
```json
{
  "user_id": "alice"
}
```

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
  "user_id": "alice",
  "message": "Visit auth_url to authorize access"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/oauth2/start \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice"}'
```

---

#### GET /oauth2/callback

Handle OAuth callback from Google (called automatically by browser).

**Query Parameters:**
- `code`: Authorization code from Google
- `state`: CSRF protection token

**Response:**
```json
{
  "success": true,
  "message": "Authentication successful",
  "user_id": "alice",
  "email": "alice@example.com"
}
```

**Note:** This endpoint is called by Google's OAuth flow. Users should not call it directly.

---

#### GET /oauth2/status/{user_id}

Check OAuth authentication status for a user.

**Path Parameters:**
- `user_id`: User identifier

**Response (Authenticated):**
```json
{
  "authenticated": true,
  "user_id": "alice",
  "email": "alice@example.com",
  "google_sub": "1234567890",
  "scopes": "openid email profile https://www.googleapis.com/auth/drive.file...",
  "created_at": "2025-10-05T10:30:00",
  "last_used": "2025-10-05T14:22:00"
}
```

**Response (Not Authenticated):**
```json
{
  "authenticated": false,
  "user_id": "alice"
}
```

**Example:**
```bash
curl http://localhost:8000/oauth2/status/alice
```

---

#### DELETE /oauth2/revoke/{user_id}

Revoke OAuth access for a user (deletes stored token).

**Path Parameters:**
- `user_id`: User identifier

**Response:**
```json
{
  "success": true,
  "message": "OAuth access revoked for user: alice"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:8000/oauth2/revoke/alice
```

---

### Export Endpoints

#### POST /export/to-slides

Export PPTX to Google Slides.

**Request Body:**
```json
{
  "user_id": "alice",
  "pptx_url": "https://example.com/presentation.pptx",
  "title": "My Presentation",
  "parent_folder_id": "1a2b3c4d5e6f7g8h9i"
}
```

**Or with base64-encoded PPTX:**
```json
{
  "user_id": "alice",
  "pptx_base64": "UEsDBBQAAAAIA...",
  "title": "My Presentation"
}
```

**Request Fields:**
- `user_id` (required): User identifier (must be authenticated)
- `pptx_url` (optional): URL to download PPTX from
- `pptx_base64` (optional): Base64-encoded PPTX data
- `title` (optional): Presentation title (default: "SVG Presentation")
- `parent_folder_id` (optional): Google Drive folder ID to save in

**Note:** Provide exactly one of `pptx_url` or `pptx_base64`.

**Response:**
```json
{
  "success": true,
  "slides_id": "1a2b3c4d5e6f7g8h9i",
  "slides_url": "https://docs.google.com/presentation/d/1a2b3c4d5e6f7g8h9i/edit",
  "web_view_link": "https://docs.google.com/presentation/d/1a2b3c4d5e6f7g8h9i/preview",
  "title": "My Presentation"
}
```

**Error Responses:**

**400 - Bad Request:**
```json
{
  "detail": "Either pptx_url or pptx_base64 must be provided"
}
```

**401 - Unauthorized:**
```json
{
  "detail": "User not authenticated with Google. Please authenticate first: ..."
}
```

**500 - Internal Server Error:**
```json
{
  "detail": "Failed to export to Slides: ..."
}
```

**Example (URL):**
```bash
curl -X POST http://localhost:8000/export/to-slides \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "user_id": "alice",
    "pptx_url": "https://example.com/presentation.pptx",
    "title": "My SVG Presentation"
  }'
```

**Example (Base64):**
```bash
# Encode PPTX to base64
BASE64_PPTX=$(base64 -i presentation.pptx)

curl -X POST http://localhost:8000/export/to-slides \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d "{
    \"user_id\": \"alice\",
    \"pptx_base64\": \"$BASE64_PPTX\",
    \"title\": \"My Presentation\"
  }"
```

## Complete Workflow Example

### 1. Check Authentication Status

```bash
curl http://localhost:8000/oauth2/status/alice
```

If `authenticated: false`, proceed to step 2.

### 2. Start OAuth Flow

```bash
curl -X POST http://localhost:8000/oauth2/start \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice"}'
```

Response:
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?client_id=...",
  "user_id": "alice",
  "message": "Visit auth_url to authorize access"
}
```

### 3. User Authorizes

User visits the `auth_url` in browser and grants permission. Google redirects to `/oauth2/callback` automatically.

### 4. Verify Authentication

```bash
curl http://localhost:8000/oauth2/status/alice
```

Response:
```json
{
  "authenticated": true,
  "user_id": "alice",
  "email": "alice@example.com",
  ...
}
```

### 5. Export to Slides

```bash
curl -X POST http://localhost:8000/export/to-slides \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "user_id": "alice",
    "pptx_url": "https://example.com/presentation.pptx",
    "title": "Alice's Presentation"
  }'
```

Response:
```json
{
  "success": true,
  "slides_id": "1a2b3c4d5e6f7g8h9i",
  "slides_url": "https://docs.google.com/presentation/d/1a2b3c4d5e6f7g8h9i/edit",
  ...
}
```

### 6. Future Exports (Silent)

All subsequent exports for Alice happen automatically without re-authentication:

```bash
curl -X POST http://localhost:8000/export/to-slides \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "user_id": "alice",
    "pptx_url": "https://example.com/another.pptx",
    "title": "Another Presentation"
  }'
```

## Security

### Token Storage

- Refresh tokens encrypted with Fernet (AES-128)
- Stored in `.env` file with 600 permissions (user-only read/write)
- Encryption key auto-generated and stored separately
- Per-user token isolation with prefixed keys

### CSRF Protection

- State tokens generated with `secrets.token_urlsafe(32)`
- State validated in OAuth callback
- Invalid state → 400 error

### Token Refresh

- Access tokens auto-refreshed when expired
- Invalid/revoked tokens automatically deleted
- User must re-authenticate if refresh token revoked

## Environment Variables

```bash
# OAuth Credentials (required)
GOOGLE_DRIVE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_DRIVE_CLIENT_SECRET=your-client-secret

# Optional Configuration
GOOGLE_DRIVE_AUTH_METHOD=oauth  # Default
```

## Error Handling

### Common Errors

**500 - OAuth Not Configured:**
```json
{
  "detail": "OAuth credentials not configured. Set GOOGLE_DRIVE_CLIENT_ID and GOOGLE_DRIVE_CLIENT_SECRET"
}
```

**401 - User Not Authenticated:**
```json
{
  "detail": "User alice not authenticated. Run OAuth flow first."
}
```

**400 - Invalid State:**
```json
{
  "detail": "Invalid state parameter - possible CSRF attack"
}
```

**400 - Invalid Grant (Revoked Token):**
```json
{
  "detail": "Refresh token revoked. Please reconnect Google account."
}
```

### Error Recovery

1. **Token Revoked**: User must re-authenticate via `/oauth2/start`
2. **OAuth Not Configured**: Admin must set environment variables
3. **Invalid PPTX**: Check PPTX URL or base64 encoding
4. **Drive API Error**: Check Google API quotas and permissions

## Testing

### Test OAuth Flow

```bash
# 1. Start flow
AUTH_RESPONSE=$(curl -s -X POST http://localhost:8000/oauth2/start \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-user"}')

AUTH_URL=$(echo $AUTH_RESPONSE | jq -r '.auth_url')

echo "Visit this URL: $AUTH_URL"

# 2. After authorization, check status
curl http://localhost:8000/oauth2/status/test-user | jq

# 3. Export test presentation
curl -X POST http://localhost:8000/export/to-slides \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-api-key-12345" \
  -d '{
    "user_id": "test-user",
    "pptx_url": "https://example.com/test.pptx",
    "title": "Test Export"
  }' | jq

# 4. Revoke access
curl -X DELETE http://localhost:8000/oauth2/revoke/test-user | jq
```

## Rate Limits

Google Drive API quotas:
- 1,000 requests per 100 seconds per user
- 10,000 requests per 100 seconds per project

Token refresh does not count against file upload quotas.

## Scopes

The following OAuth scopes are requested:

- `openid`: User identity
- `email`: User email address
- `profile`: Basic profile information
- `https://www.googleapis.com/auth/drive.file`: Access to files created by this app
- `https://www.googleapis.com/auth/presentations`: Access to Google Slides

## See Also

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Drive API Reference](https://developers.google.com/drive/api/v3/reference)
- [Google Slides API Reference](https://developers.google.com/slides/api/reference/rest)
