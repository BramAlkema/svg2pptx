# Google Drive Service Account Credentials

Place your Google Drive service account JSON file in this directory.

## Quick Setup Instructions

1. **Go to [Google Cloud Console](https://console.cloud.google.com/)**
2. **Create a new project** or select an existing one
3. **Enable the Google Drive API**:
   - Go to APIs & Services → Library
   - Search for "Google Drive API"
   - Click on it and press "Enable"
4. **Create a service account**:
   - Go to IAM & Admin → Service Accounts
   - Click "Create Service Account"
   - Enter name: `svg2pptx-service`
   - Description: `Service account for SVG to PowerPoint conversion`
   - Click "Create and Continue"
   - Grant role: **Editor** (or custom role with Drive permissions)
   - Click "Continue" then "Done"
5. **Create and download the JSON key**:
   - Click on the created service account
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Select **JSON format**
   - Download the file and save it as `service-account.json` in this directory

## Required API Permissions

The service account needs these scopes:
- `https://www.googleapis.com/auth/drive.file` (create and update files)
- `https://www.googleapis.com/auth/drive.metadata` (read file metadata)

## File Structure

```
credentials/
├── README.md                    # This file
├── service-account.json         # Your Google Drive service account key (gitignored)
├── service-account-example.json # Example format (safe to commit)
└── .gitkeep                     # Ensures directory exists in git
```

## Testing the Setup

Once you have `service-account.json` in place, test the connection:

```bash
source venv/bin/activate
python -c "from api.services.google_drive import GoogleDriveService; print('✅ Google Drive connection successful' if GoogleDriveService().test_connection() else '❌ Connection failed')"
```

## Security Note

- The `service-account.json` file contains sensitive credentials and should **never** be committed to version control
- It's already included in `.gitignore`
- The example file shows the format but contains no real credentials

## Environment Variable

Update your `.env` file to point to the credentials:

```
GOOGLE_DRIVE_CREDENTIALS_PATH=credentials/service-account.json
```

## Troubleshooting

- **File not found**: Ensure the JSON file is named exactly `service-account.json`
- **Permission denied**: Verify the service account has Editor role or Drive permissions
- **API not enabled**: Make sure Google Drive API is enabled in Google Cloud Console