#!/usr/bin/env python3
"""
Google Slides Publisher Module

Publishes Google Slides presentations for public/link viewing and manages
sharing permissions for automated screenshot capture and visual testing.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# Google API imports
try:
    from googleapiclient.errors import HttpError
    GOOGLE_APIS_AVAILABLE = True
except ImportError:
    GOOGLE_APIS_AVAILABLE = False

from .authenticator import GoogleSlidesAuthenticator

logger = logging.getLogger(__name__)


class AccessLevel(Enum):
    """Access levels for published presentations."""
    ANYONE_WITH_LINK = "anyone"
    ANYONE_CAN_FIND = "anyone"
    DOMAIN_WITH_LINK = "domain"
    RESTRICTED = "private"


class PublishFormat(Enum):
    """Publication formats for presentations."""
    VIEW_ONLY = "view"
    COMMENT = "comment"
    EDIT = "edit"


@dataclass
class PublishedPresentation:
    """Information about a published presentation."""
    presentation_id: str
    title: str
    public_url: str
    embed_url: str
    access_level: str
    permissions: List[Dict[str, Any]]
    published_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SlidesPublisher:
    """Publish Google Slides for public/link viewing."""

    def __init__(self, auth: GoogleSlidesAuthenticator):
        """
        Initialize publisher.

        Args:
            auth: Authenticated GoogleSlidesAuthenticator instance
        """
        if not GOOGLE_APIS_AVAILABLE:
            raise ImportError("Google API libraries not available")

        if not auth.is_authenticated:
            raise ValueError("Authenticator must be authenticated before use")

        self.auth = auth
        self.drive_service = auth.get_drive_service()
        self.slides_service = auth.get_slides_service()

        logger.info("SlidesPublisher initialized")

    def publish_presentation(self, presentation_id: str,
                           access_level: AccessLevel = AccessLevel.ANYONE_WITH_LINK,
                           role: PublishFormat = PublishFormat.VIEW_ONLY) -> PublishedPresentation:
        """
        Publish presentation and get public URL.

        Args:
            presentation_id: Google Slides presentation ID
            access_level: Who can access the presentation
            role: What level of access they have

        Returns:
            PublishedPresentation object with URLs and permissions

        Raises:
            HttpError: If publishing fails
        """
        try:
            # Get presentation info first
            presentation_info = self._get_presentation_info(presentation_id)

            # Set sharing permissions
            permission_result = self._set_sharing_permissions(
                presentation_id, access_level, role
            )

            # Generate URLs
            public_url = self._get_public_url(presentation_id)
            embed_url = self._get_embed_url(presentation_id)

            # Create PublishedPresentation object
            published = PublishedPresentation(
                presentation_id=presentation_id,
                title=presentation_info.get('title', 'Untitled'),
                public_url=public_url,
                embed_url=embed_url,
                access_level=access_level.value,
                permissions=permission_result,
                published_at=datetime.now(),
                metadata=presentation_info
            )

            logger.info(f"Presentation published: {presentation_id}")
            return published

        except HttpError as e:
            logger.error(f"Failed to publish presentation {presentation_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error publishing presentation {presentation_id}: {e}")
            raise

    def get_embed_url(self, presentation_id: str, slide_id: Optional[str] = None) -> str:
        """
        Get embeddable iframe URL.

        Args:
            presentation_id: Presentation ID
            slide_id: Optional specific slide ID

        Returns:
            Embeddable URL
        """
        base_url = f"https://docs.google.com/presentation/d/{presentation_id}/embed"

        if slide_id:
            base_url += f"?slide=id.{slide_id}"

        return base_url

    def get_screenshot_url(self, presentation_id: str, slide_index: int = 0,
                         format: str = "png", size: str = "large") -> str:
        """
        Get URL for slide screenshot.

        Args:
            presentation_id: Presentation ID
            slide_index: Slide index (0-based)
            format: Image format (png, jpeg)
            size: Image size (small, medium, large)

        Returns:
            Screenshot URL
        """
        # Google Slides export URL format
        base_url = f"https://docs.google.com/presentation/d/{presentation_id}/export/{format}"

        # Size mapping
        size_map = {
            'small': '480',
            'medium': '960',
            'large': '1440',
            'xlarge': '1920'
        }

        size_param = size_map.get(size, '1440')
        return f"{base_url}?pageid=slide_{slide_index}&size={size_param}"

    def create_shareable_link(self, presentation_id: str,
                            expires_hours: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a time-limited shareable link.

        Args:
            presentation_id: Presentation ID
            expires_hours: Hours until link expires (None for permanent)

        Returns:
            Dictionary with link information
        """
        try:
            # For Google Drive, we can't set expiration directly through API
            # This would typically be done through advanced sharing settings

            result = self.publish_presentation(presentation_id)

            link_info = {
                'url': result.public_url,
                'embed_url': result.embed_url,
                'created_at': datetime.now().isoformat(),
                'expires_at': None,  # Would need enterprise features for expiration
                'presentation_id': presentation_id,
                'access_type': 'view_only'
            }

            if expires_hours:
                # Note: Actual expiration would need to be implemented separately
                # or through enterprise Google Workspace features
                logger.warning("Link expiration not supported in basic Google Drive API")
                link_info['requested_expiry_hours'] = expires_hours

            logger.info(f"Shareable link created for {presentation_id}")
            return link_info

        except Exception as e:
            logger.error(f"Failed to create shareable link: {e}")
            raise

    def revoke_public_access(self, presentation_id: str) -> bool:
        """
        Revoke public access to a presentation.

        Args:
            presentation_id: Presentation ID

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current permissions
            permissions = self.drive_service.permissions().list(
                fileId=presentation_id
            ).execute()

            # Remove public permissions
            for permission in permissions.get('permissions', []):
                if permission.get('type') == 'anyone':
                    self.drive_service.permissions().delete(
                        fileId=presentation_id,
                        permissionId=permission['id']
                    ).execute()
                    logger.info(f"Removed public permission: {permission['id']}")

            logger.info(f"Public access revoked for {presentation_id}")
            return True

        except HttpError as e:
            logger.error(f"Failed to revoke public access: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error revoking access: {e}")
            return False

    def get_publication_status(self, presentation_id: str) -> Dict[str, Any]:
        """
        Get current publication status of a presentation.

        Args:
            presentation_id: Presentation ID

        Returns:
            Dictionary with publication status
        """
        try:
            # Get file permissions
            permissions = self.drive_service.permissions().list(
                fileId=presentation_id,
                fields='permissions(id,type,role,domain)'
            ).execute()

            # Get file metadata
            file_info = self.drive_service.files().get(
                fileId=presentation_id,
                fields='id,name,webViewLink,shared'
            ).execute()

            # Analyze permissions
            is_public = False
            access_level = 'private'
            public_permissions = []

            for permission in permissions.get('permissions', []):
                if permission.get('type') == 'anyone':
                    is_public = True
                    access_level = 'public'
                    public_permissions.append(permission)

            status = {
                'presentation_id': presentation_id,
                'title': file_info.get('name', 'Untitled'),
                'is_public': is_public,
                'access_level': access_level,
                'shared': file_info.get('shared', False),
                'web_view_link': file_info.get('webViewLink'),
                'permissions_count': len(permissions.get('permissions', [])),
                'public_permissions': public_permissions,
                'embed_url': self.get_embed_url(presentation_id)
            }

            return status

        except Exception as e:
            logger.error(f"Failed to get publication status: {e}")
            return {'error': str(e)}

    def batch_publish_presentations(self, presentation_ids: List[str],
                                  access_level: AccessLevel = AccessLevel.ANYONE_WITH_LINK,
                                  progress_callback: Optional[callable] = None) -> List[Dict[str, Any]]:
        """
        Publish multiple presentations in batch.

        Args:
            presentation_ids: List of presentation IDs
            access_level: Access level for all presentations
            progress_callback: Optional progress callback

        Returns:
            List of results for each presentation
        """
        results = []
        total_count = len(presentation_ids)

        logger.info(f"Starting batch publication of {total_count} presentations")

        for i, presentation_id in enumerate(presentation_ids):
            try:
                if progress_callback:
                    progress_callback(i, total_count, presentation_id)

                published = self.publish_presentation(presentation_id, access_level)

                result = {
                    'success': True,
                    'presentation_id': presentation_id,
                    'public_url': published.public_url,
                    'embed_url': published.embed_url
                }
                results.append(result)

                logger.info(f"Batch {i+1}/{total_count}: Published {presentation_id}")

            except Exception as e:
                result = {
                    'success': False,
                    'presentation_id': presentation_id,
                    'error': str(e)
                }
                results.append(result)

                logger.error(f"Batch {i+1}/{total_count}: Failed {presentation_id}: {e}")

        successful = sum(1 for r in results if r['success'])
        logger.info(f"Batch publication completed: {successful}/{total_count} successful")

        return results

    def _set_sharing_permissions(self, presentation_id: str,
                               access_level: AccessLevel,
                               role: PublishFormat) -> List[Dict[str, Any]]:
        """Set sharing permissions for presentation."""
        try:
            permission_body = {
                'type': access_level.value,
                'role': role.value
            }

            # Add domain for domain-restricted access
            if access_level == AccessLevel.DOMAIN_WITH_LINK:
                # Would need to specify domain - using anyone for now
                permission_body['type'] = 'anyone'

            permission = self.drive_service.permissions().create(
                fileId=presentation_id,
                body=permission_body,
                fields='id,type,role'
            ).execute()

            logger.info(f"Sharing permission set: {permission}")
            return [permission]

        except HttpError as e:
            logger.error(f"Failed to set sharing permissions: {e}")
            raise

    def _get_presentation_info(self, presentation_id: str) -> Dict[str, Any]:
        """Get presentation information."""
        try:
            presentation = self.slides_service.presentations().get(
                presentationId=presentation_id
            ).execute()

            return {
                'title': presentation.get('title', 'Untitled'),
                'slide_count': len(presentation.get('slides', [])),
                'page_size': presentation.get('pageSize', {}),
                'revision_id': presentation.get('revisionId')
            }

        except Exception as e:
            logger.warning(f"Could not get presentation info: {e}")
            return {}

    def _get_public_url(self, presentation_id: str) -> str:
        """Get public viewing URL."""
        try:
            file_info = self.drive_service.files().get(
                fileId=presentation_id,
                fields='webViewLink'
            ).execute()

            return file_info.get('webViewLink',
                               f"https://docs.google.com/presentation/d/{presentation_id}/edit")

        except Exception as e:
            logger.warning(f"Could not get web view link: {e}")
            return f"https://docs.google.com/presentation/d/{presentation_id}/edit"

    def _get_embed_url(self, presentation_id: str) -> str:
        """Get embeddable URL."""
        return f"https://docs.google.com/presentation/d/{presentation_id}/embed"