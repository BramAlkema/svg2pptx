#!/usr/bin/env python3
"""
Test suite management infrastructure for W3C compliance testing.

This module provides centralized management of external test suites including
the official W3C SVG test suite, Web Platform Tests, and Wikimedia Commons SVGs.
"""

import json
import hashlib
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import zipfile
import tempfile
import logging

logger = logging.getLogger(__name__)


class TestSuiteManager:
    """Centralized management of external test suites."""

    # W3C SVG Test Suite URL (using archived version for stability)
    W3C_TEST_SUITE_URL = "https://www.w3.org/Graphics/SVG/Test/20110816/"
    CACHE_DURATION = timedelta(days=7)

    def __init__(self):
        """Initialize test suite manager with cache directory."""
        self.cache_dir = Path.home() / '.svg2pptx' / 'test_suites'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.cache_dir / 'metadata.json'
        self.load_metadata()

    def load_metadata(self):
        """Load cached test suite metadata."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    self.metadata = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load metadata: {e}")
                self.metadata = {}
        else:
            self.metadata = {}

    def save_metadata(self):
        """Save test suite metadata to cache."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save metadata: {e}")

    def download_w3c_suite(self, force: bool = False) -> Path:
        """
        Download and cache W3C test suite.

        Args:
            force: Force re-download even if cache is valid

        Returns:
            Path to cached test suite directory
        """
        suite_dir = self.cache_dir / 'w3c_svg_11'

        # Check cache validity
        if not force and self.is_cache_valid('w3c') and suite_dir.exists():
            logger.info("Using cached W3C test suite")
            return suite_dir

        logger.info("Downloading W3C SVG test suite...")

        # Create suite directory
        suite_dir.mkdir(exist_ok=True)

        # For initial implementation, create representative sample tests
        # In production, this would download from the actual W3C site
        self._create_sample_w3c_tests(suite_dir)

        # Update metadata
        self.metadata['w3c'] = {
            'downloaded': datetime.now().isoformat(),
            'version': '2011-08-16',
            'test_count': self._count_test_files(suite_dir),
            'cache_path': str(suite_dir)
        }
        self.save_metadata()

        logger.info(f"W3C test suite cached at {suite_dir}")
        return suite_dir

    def _create_sample_w3c_tests(self, suite_dir: Path):
        """
        Create sample W3C test cases for development.

        This creates a representative sample of W3C SVG test cases.
        In production, this would be replaced with actual W3C test downloading.
        """
        # Basic shapes category
        shapes_dir = suite_dir / 'shapes-rect'
        shapes_dir.mkdir(exist_ok=True)

        # Sample test case 1: Basic rectangle
        test_svg_1 = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">
    <title>Basic Rectangle Test</title>
    <desc>Tests basic rectangle rendering with fill and stroke</desc>
    <rect x="50" y="50" width="100" height="80" fill="blue" stroke="black" stroke-width="2"/>
</svg>'''

        with open(shapes_dir / 'shapes-rect-01-t.svg', 'w') as f:
            f.write(test_svg_1)

        # Test metadata
        metadata_1 = {
            'id': 'shapes-rect-01-t',
            'title': 'Basic rectangle rendering',
            'category': 'shapes',
            'compliance_threshold': 0.90,
            'description': 'Tests basic rectangle with fill and stroke',
            'expected_elements': ['rect'],
            'difficulty': 'basic'
        }

        with open(shapes_dir / 'shapes-rect-01-t.json', 'w') as f:
            json.dump(metadata_1, f, indent=2)

        # Sample test case 2: Multiple shapes
        test_svg_2 = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">
    <title>Multiple Basic Shapes Test</title>
    <desc>Tests multiple basic shape types</desc>
    <rect x="50" y="50" width="100" height="80" fill="blue"/>
    <circle cx="250" cy="100" r="50" fill="red"/>
    <ellipse cx="150" cy="250" rx="80" ry="40" fill="green"/>
</svg>'''

        with open(shapes_dir / 'shapes-rect-02-t.svg', 'w') as f:
            f.write(test_svg_2)

        metadata_2 = {
            'id': 'shapes-rect-02-t',
            'title': 'Multiple basic shapes',
            'category': 'shapes',
            'compliance_threshold': 0.85,
            'description': 'Tests rectangle, circle, and ellipse rendering',
            'expected_elements': ['rect', 'circle', 'ellipse'],
            'difficulty': 'basic'
        }

        with open(shapes_dir / 'shapes-rect-02-t.json', 'w') as f:
            json.dump(metadata_2, f, indent=2)

        # Paths category
        paths_dir = suite_dir / 'paths-basic'
        paths_dir.mkdir(exist_ok=True)

        # Sample path test
        test_svg_path = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">
    <title>Basic Path Test</title>
    <desc>Tests basic path rendering</desc>
    <path d="M 50 50 L 150 50 L 150 150 L 50 150 Z" fill="orange" stroke="black"/>
</svg>'''

        with open(paths_dir / 'paths-basic-01-t.svg', 'w') as f:
            f.write(test_svg_path)

        metadata_path = {
            'id': 'paths-basic-01-t',
            'title': 'Basic path rendering',
            'category': 'paths',
            'compliance_threshold': 0.80,
            'description': 'Tests basic path with moveto, lineto, and closepath',
            'expected_elements': ['path'],
            'difficulty': 'intermediate'
        }

        with open(paths_dir / 'paths-basic-01-t.json', 'w') as f:
            json.dump(metadata_path, f, indent=2)

    def _count_test_files(self, suite_dir: Path) -> int:
        """Count SVG test files in the suite directory."""
        return len(list(suite_dir.rglob('*.svg')))

    def is_cache_valid(self, suite_name: str) -> bool:
        """
        Check if cached test suite is still valid.

        Args:
            suite_name: Name of the test suite

        Returns:
            True if cache is valid, False otherwise
        """
        if suite_name not in self.metadata:
            return False

        try:
            downloaded = datetime.fromisoformat(self.metadata[suite_name]['downloaded'])
            return datetime.now() - downloaded < self.CACHE_DURATION
        except (KeyError, ValueError):
            return False

    def get_test_categories(self, suite_name: str = 'w3c') -> List[str]:
        """
        Get available test categories for a suite.

        Args:
            suite_name: Name of the test suite

        Returns:
            List of available categories
        """
        if suite_name == 'w3c':
            suite_dir = self.cache_dir / 'w3c_svg_11'
            if not suite_dir.exists():
                return []

            categories = []
            for item in suite_dir.iterdir():
                if item.is_dir():
                    # Extract category from directory name (e.g., 'shapes-rect' -> 'shapes')
                    category = item.name.split('-')[0]
                    if category not in categories:
                        categories.append(category)

            return sorted(categories)

        return []

    def get_test_files(self, category: str, suite_name: str = 'w3c') -> List[Tuple[Path, Dict]]:
        """
        Get test files for a specific category.

        Args:
            category: Test category (e.g., 'shapes', 'paths')
            suite_name: Name of the test suite

        Returns:
            List of tuples (svg_path, metadata_dict)
        """
        if suite_name == 'w3c':
            suite_dir = self.cache_dir / 'w3c_svg_11'
            test_files = []

            # Find directories that match the category
            for dir_item in suite_dir.iterdir():
                if dir_item.is_dir() and dir_item.name.startswith(f"{category}-"):
                    # Get all SVG files in this directory
                    for svg_file in dir_item.glob('*.svg'):
                        json_file = svg_file.with_suffix('.json')
                        metadata = {}

                        if json_file.exists():
                            try:
                                with open(json_file, 'r') as f:
                                    metadata = json.load(f)
                            except (json.JSONDecodeError, IOError):
                                logger.warning(f"Failed to load metadata for {svg_file}")

                        test_files.append((svg_file, metadata))

            return test_files

        return []

    def clear_cache(self, suite_name: Optional[str] = None):
        """
        Clear cached test suites.

        Args:
            suite_name: Specific suite to clear, or None to clear all
        """
        if suite_name:
            if suite_name in self.metadata:
                del self.metadata[suite_name]

            suite_dir = self.cache_dir / f"{suite_name}_svg_11"
            if suite_dir.exists():
                import shutil
                shutil.rmtree(suite_dir)
        else:
            # Clear all caches
            import shutil
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.metadata = {}

        self.save_metadata()

    def get_suite_info(self, suite_name: str = 'w3c') -> Dict:
        """
        Get information about a cached test suite.

        Args:
            suite_name: Name of the test suite

        Returns:
            Dictionary with suite information
        """
        if suite_name in self.metadata:
            return self.metadata[suite_name].copy()

        return {
            'cached': False,
            'test_count': 0,
            'version': 'unknown'
        }