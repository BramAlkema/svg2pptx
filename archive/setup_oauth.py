#!/usr/bin/env python3
"""
OAuth setup script for Google Drive integration.

This script helps users set up OAuth authentication for Google Drive.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from api.services.google_oauth import setup_oauth_credentials, test_oauth_setup


def main():
    """Main setup function."""
    print("🚀 SVG to Google Drive API - OAuth Setup")
    print("=" * 50)
    
    print("\nThis script will help you set up OAuth authentication for Google Drive.")
    print("OAuth authentication is recommended for development and personal use.")
    print("For production servers, consider using service account authentication.\n")
    
    choice = input("Do you want to set up OAuth credentials? (y/n): ").lower().strip()
    
    if choice in ['y', 'yes']:
        print("\n" + "="*50)
        if setup_oauth_credentials():
            print("\n" + "="*50)
            print("🎉 OAuth setup completed!")
            
            test_choice = input("\nWould you like to test the OAuth authentication now? (y/n): ").lower().strip()
            if test_choice in ['y', 'yes']:
                print("\n" + "="*50)
                if test_oauth_setup():
                    print("\n✅ OAuth authentication is working perfectly!")
                    print("\nYour API is now ready to upload files to Google Drive.")
                    print("\nNext steps:")
                    print("1. Start the API: python -m uvicorn api.main:app --reload")
                    print("2. Test the /convert endpoint with an SVG URL")
                    print("3. Check your Google Drive for the converted PPTX file")
                else:
                    print("\n❌ OAuth test failed. Please check your credentials and try again.")
            else:
                print("\n💡 You can test OAuth later by running:")
                print("   python -c \"from api.services.google_oauth import test_oauth_setup; test_oauth_setup()\"")
        else:
            print("\n❌ OAuth setup failed. Please try again.")
    else:
        print("\n📝 To set up OAuth later, run this script again or:")
        print("   python api/services/google_oauth.py setup")
        
        print("\n🔧 Alternative: Service Account Authentication")
        print("   1. Set GOOGLE_DRIVE_AUTH_METHOD=service_account in .env")
        print("   2. Follow the instructions in credentials/README.md")


if __name__ == "__main__":
    main()