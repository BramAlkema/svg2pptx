#!/usr/bin/env python3
"""
Version management for SVG2PPTX CLI.

Provides dynamic detection of package versions, LibreOffice version,
and other environment information for visual reports and debugging.
"""

import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class VersionInfo:
    """Container for all version information."""
    package_version: str
    cli_version: str
    python_version: str
    libreoffice_version: Optional[str]
    platform_info: str
    working_directory: str

    @classmethod
    def gather(cls) -> 'VersionInfo':
        """
        Gather all version information from the system.

        Returns:
            VersionInfo object with all detected versions
        """
        return cls(
            package_version=get_package_version(),
            cli_version=get_cli_version(),
            python_version=platform.python_version(),
            libreoffice_version=get_libreoffice_version(),
            platform_info=platform.platform(),
            working_directory=str(Path.cwd())
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            'version': self.package_version,
            'cli_version': self.cli_version,
            'python_version': self.python_version,
            'libreoffice_version': self.libreoffice_version or 'Not detected',
            'platform': self.platform_info,
            'working_directory': self.working_directory
        }


def get_package_version() -> str:
    """
    Get SVG2PPTX package version.

    Returns:
        Package version string, with fallback to development version
    """
    try:
        # Try to get version from installed package
        import pkg_resources
        return pkg_resources.get_distribution('svg2pptx').version
    except ImportError:
        pass
    except Exception:
        pass

    try:
        # Try to get version from pyproject.toml
        project_root = Path(__file__).parent.parent.parent
        pyproject_path = project_root / 'pyproject.toml'

        if pyproject_path.exists():
            content = pyproject_path.read_text()
            for line in content.split('\n'):
                if line.strip().startswith('version = '):
                    # Extract version from line like: version = "2.0.0"
                    version = line.split('=')[1].strip().strip('"\'')
                    return version
    except Exception:
        pass

    try:
        # Try to get version from git tag
        project_root = Path(__file__).parent.parent.parent
        result = subprocess.run(
            ['git', 'describe', '--tags', '--abbrev=0'],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            tag = result.stdout.strip()
            # Remove 'v' prefix if present
            if tag.startswith('v'):
                tag = tag[1:]
            return tag
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Fallback version
    return '2.0.0-dev'


def get_cli_version() -> str:
    """
    Get CLI version (same as package version for now).

    Returns:
        CLI version string
    """
    return get_package_version()


def get_libreoffice_version() -> Optional[str]:
    """
    Detect LibreOffice version by calling soffice --version.

    Returns:
        LibreOffice version string, or None if not detected
    """
    # Try different LibreOffice executable names
    executables = [
        'soffice',
        'libreoffice',
        '/Applications/LibreOffice.app/Contents/MacOS/soffice',  # macOS
        'C:\\Program Files\\LibreOffice\\program\\soffice.exe',  # Windows
        '/usr/bin/soffice',  # Linux
        '/opt/libreoffice/program/soffice'  # Alternative Linux path
    ]

    for executable in executables:
        try:
            result = subprocess.run(
                [executable, '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout:
                # Parse version from output like "LibreOffice 7.5.8.2 40(Build:2)"
                version_line = result.stdout.strip().split('\n')[0]
                if 'LibreOffice' in version_line:
                    return version_line

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError,
                FileNotFoundError, PermissionError):
            continue

    return None


def get_version_summary() -> str:
    """
    Get a concise version summary for logging.

    Returns:
        Single-line version summary
    """
    info = VersionInfo.gather()
    libre_status = "with LibreOffice" if info.libreoffice_version else "no LibreOffice"
    return f"SVG2PPTX {info.package_version} (Python {info.python_version}, {libre_status})"


def print_version_info():
    """Print detailed version information to console."""
    info = VersionInfo.gather()

    print("SVG2PPTX Version Information")
    print("=" * 40)
    print(f"Package Version: {info.package_version}")
    print(f"CLI Version:     {info.cli_version}")
    print(f"Python Version:  {info.python_version}")
    print(f"Platform:        {info.platform_info}")
    print(f"Working Dir:     {info.working_directory}")

    if info.libreoffice_version:
        print(f"LibreOffice:     {info.libreoffice_version}")
    else:
        print("LibreOffice:     Not detected")


if __name__ == "__main__":
    # Command-line usage: python -m src.cli.version
    print_version_info()