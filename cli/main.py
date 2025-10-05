#!/usr/bin/env python3
"""
SVG2PPTX CLI - Convert SVG files to PowerPoint presentations.
"""

import click
import sys
from pathlib import Path

from .commands.auth import auth


@click.group()
@click.version_option(version="2.0.0", prog_name="svg2pptx")
def cli():
    """SVG to PowerPoint converter with Google Slides export."""
    pass


@cli.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.argument('output_file', type=click.Path(path_type=Path), required=False)
@click.option('--export-slides', is_flag=True, help='Export to Google Slides after conversion')
@click.option('--title', type=str, help='Presentation title for Google Slides export')
@click.option('--folder-id', type=str, help='Google Drive folder ID for export')
def convert(input_file, output_file, export_slides, title, folder_id):
    """
    Convert SVG file to PowerPoint presentation.

    Examples:
        svg2pptx convert input.svg output.pptx
        svg2pptx convert input.svg --export-slides
        svg2pptx convert input.svg --export-slides --title "My Presentation"
    """
    try:
        # Import here to avoid slow imports on --help
        from core.pipeline.converter import CleanSlateConverter

        # Default output filename
        if not output_file:
            output_file = input_file.with_suffix('.pptx')

        click.echo(f"📄 Converting: {input_file}")
        click.echo(f"📦 Output: {output_file}")

        # Read SVG
        with open(input_file, 'r', encoding='utf-8') as f:
            svg_content = f.read()

        # Convert to PPTX
        converter = CleanSlateConverter()
        pptx_bytes = converter.convert(svg_content, str(output_file))

        # Write PPTX file
        with open(output_file, 'wb') as f:
            f.write(pptx_bytes)

        click.echo(f"✅ Conversion complete: {output_file}")

        # Export to Slides if requested
        if export_slides:
            from core.auth import (
                GoogleOAuthService,
                GoogleDriveService,
                get_cli_token_store,
                get_system_username,
                OAuthError,
                DriveError,
            )
            import os

            click.echo()
            click.echo("📤 Exporting to Google Slides...")

            user_id = get_system_username()
            token_store = get_cli_token_store()

            # Check authentication
            if not token_store.has_token(user_id):
                click.echo("❌ Not authenticated with Google.")
                click.echo("   Run: svg2pptx auth google")
                sys.exit(1)

            # Get OAuth credentials
            client_id = os.getenv('GOOGLE_DRIVE_CLIENT_ID')
            client_secret = os.getenv('GOOGLE_DRIVE_CLIENT_SECRET')

            if not client_id or not client_secret:
                click.echo("❌ OAuth not configured. Set GOOGLE_DRIVE_CLIENT_ID and GOOGLE_DRIVE_CLIENT_SECRET")
                sys.exit(1)

            try:
                # Get credentials
                oauth_service = GoogleOAuthService(
                    token_store=token_store,
                    client_id=client_id,
                    client_secret=client_secret,
                )
                credentials = oauth_service.get_credentials(user_id)

                # Upload and convert
                drive_service = GoogleDriveService(credentials)

                presentation_title = title or input_file.stem

                result = drive_service.upload_and_convert_to_slides(
                    pptx_bytes=pptx_bytes,
                    title=presentation_title,
                    parent_folder_id=folder_id
                )

                click.echo(f"✅ Exported to Google Slides!")
                click.echo(f"   Title: {presentation_title}")
                click.echo(f"   URL: {result['slides_url']}")

            except OAuthError as e:
                click.echo(f"❌ OAuth error: {e}")
                click.echo("   Try: svg2pptx auth google --revoke && svg2pptx auth google")
                sys.exit(1)
            except DriveError as e:
                click.echo(f"❌ Drive error: {e}")
                sys.exit(1)

    except FileNotFoundError:
        click.echo(f"❌ File not found: {input_file}")
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Conversion error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


# Register command groups
cli.add_command(auth)


def main():
    """Entry point for CLI."""
    cli()


if __name__ == '__main__':
    main()
