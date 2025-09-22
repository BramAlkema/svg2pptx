#!/usr/bin/env python3
"""
W3C Test Suite Manager

Downloads, manages, and organizes W3C SVG test cases for compliance testing.
Provides categorized access to official W3C SVG test suite files.
"""

import os
import json
import logging
import zipfile
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import requests
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


@dataclass
class W3CTestCase:
    """Represents a W3C SVG test case."""
    name: str
    category: str
    svg_path: Path
    reference_image: Optional[Path] = None
    description: str = ""
    tags: Set[str] = field(default_factory=set)
    difficulty: str = "medium"  # basic, medium, advanced
    spec_section: str = ""
    expected_features: Set[str] = field(default_factory=set)
    metadata: Dict[str, any] = field(default_factory=dict)


@dataclass
class TestSuiteInfo:
    """Information about the W3C test suite."""
    version: str
    download_date: datetime
    total_tests: int
    categories: Dict[str, int]
    checksum: str
    source_url: str


class W3CTestSuiteManager:
    """Downloads and manages W3C SVG test cases."""

    # Official W3C SVG test suite URLs
    W3C_SVG_TEST_SUITE_URLS = {
        "1.1": "https://www.w3.org/Graphics/SVG/Test/20110816/archives/W3C_SVG_11_F2_test_suite.zip",
        "2.0": "https://github.com/w3c/svgwg/archive/refs/heads/main.zip",  # SVG 2.0 working group
        "tiny": "https://www.w3.org/Graphics/SVG/Test/20110816/archives/W3C_SVG_11_Tiny_test_suite.zip"
    }

    # Test categories with difficulty levels
    TEST_CATEGORIES = {
        "basic-shapes": {"difficulty": "basic", "description": "Basic geometric shapes"},
        "paths": {"difficulty": "medium", "description": "Path elements and commands"},
        "text": {"difficulty": "medium", "description": "Text rendering and fonts"},
        "gradients": {"difficulty": "medium", "description": "Linear and radial gradients"},
        "patterns": {"difficulty": "advanced", "description": "Pattern fills"},
        "filters": {"difficulty": "advanced", "description": "Filter effects"},
        "animations": {"difficulty": "advanced", "description": "SVG animations"},
        "transforms": {"difficulty": "medium", "description": "Geometric transformations"},
        "clipping": {"difficulty": "medium", "description": "Clipping paths"},
        "masking": {"difficulty": "advanced", "description": "Masking effects"},
        "markers": {"difficulty": "medium", "description": "Marker elements"},
        "color": {"difficulty": "basic", "description": "Color specifications"},
        "coordinates": {"difficulty": "basic", "description": "Coordinate systems"},
        "styling": {"difficulty": "medium", "description": "CSS styling"},
        "scripting": {"difficulty": "advanced", "description": "Script-based interactions"}
    }

    def __init__(self, test_data_dir: Optional[Path] = None):
        """
        Initialize test suite manager.

        Args:
            test_data_dir: Directory for storing test data
        """
        if test_data_dir is None:
            test_data_dir = Path(__file__).parent.parent.parent.parent / "data" / "w3c_tests"

        self.test_data_dir = Path(test_data_dir)
        self.suite_dir = self.test_data_dir / "suites"
        self.cache_dir = self.test_data_dir / "cache"

        # Ensure directories exist
        self.test_data_dir.mkdir(parents=True, exist_ok=True)
        self.suite_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Test case registry
        self._test_cases: Dict[str, W3CTestCase] = {}
        self._categories: Dict[str, List[str]] = {}
        self._suite_info: Optional[TestSuiteInfo] = None

        logger.info(f"W3CTestSuiteManager initialized with data dir: {self.test_data_dir}")

    def download_test_suite(self, version: str = "1.1", force_download: bool = False) -> bool:
        """
        Download W3C SVG test suite.

        Args:
            version: Test suite version (1.1, 2.0, tiny)
            force_download: Force re-download even if exists

        Returns:
            True if successful
        """
        if version not in self.W3C_SVG_TEST_SUITE_URLS:
            logger.error(f"Unknown test suite version: {version}")
            return False

        suite_path = self.suite_dir / f"w3c_svg_{version}"
        zip_path = self.cache_dir / f"w3c_svg_{version}.zip"

        # Check if already downloaded
        if suite_path.exists() and not force_download:
            logger.info(f"Test suite {version} already exists at {suite_path}")
            return True

        try:
            url = self.W3C_SVG_TEST_SUITE_URLS[version]
            logger.info(f"Downloading W3C SVG test suite {version} from {url}")

            # Download with progress
            response = requests.get(url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            logger.debug(f"Download progress: {progress:.1f}%")

            logger.info(f"Downloaded {downloaded_size} bytes to {zip_path}")

            # Extract test suite
            if self._extract_test_suite(zip_path, suite_path, version):
                logger.info(f"Test suite {version} extracted to {suite_path}")
                return True
            else:
                logger.error(f"Failed to extract test suite {version}")
                return False

        except Exception as e:
            logger.error(f"Failed to download test suite {version}: {e}")
            return False

    def load_test_cases(self, version: str = "1.1") -> bool:
        """
        Load test cases from downloaded suite.

        Args:
            version: Test suite version to load

        Returns:
            True if successful
        """
        suite_path = self.suite_dir / f"w3c_svg_{version}"

        if not suite_path.exists():
            logger.warning(f"Test suite {version} not found. Attempting download...")
            if not self.download_test_suite(version):
                return False

        try:
            logger.info(f"Loading test cases from {suite_path}")

            # Clear existing test cases
            self._test_cases.clear()
            self._categories.clear()

            # Scan for SVG files
            svg_files = list(suite_path.rglob("*.svg"))
            logger.info(f"Found {len(svg_files)} SVG files")

            for svg_path in svg_files:
                test_case = self._parse_test_case(svg_path, suite_path)
                if test_case:
                    self._test_cases[test_case.name] = test_case

                    # Add to category
                    if test_case.category not in self._categories:
                        self._categories[test_case.category] = []
                    self._categories[test_case.category].append(test_case.name)

            # Create suite info
            self._suite_info = TestSuiteInfo(
                version=version,
                download_date=datetime.now(),
                total_tests=len(self._test_cases),
                categories={cat: len(tests) for cat, tests in self._categories.items()},
                checksum=self._calculate_suite_checksum(suite_path),
                source_url=self.W3C_SVG_TEST_SUITE_URLS[version]
            )

            logger.info(f"Loaded {len(self._test_cases)} test cases in {len(self._categories)} categories")
            return True

        except Exception as e:
            logger.error(f"Failed to load test cases: {e}")
            return False

    def get_test_cases(self, category: Optional[str] = None,
                      difficulty: Optional[str] = None,
                      tags: Optional[Set[str]] = None,
                      limit: Optional[int] = None) -> List[W3CTestCase]:
        """
        Get test cases with optional filtering.

        Args:
            category: Filter by category
            difficulty: Filter by difficulty (basic, medium, advanced)
            tags: Filter by tags
            limit: Maximum number of test cases to return

        Returns:
            List of matching test cases
        """
        test_cases = list(self._test_cases.values())

        # Apply filters
        if category:
            test_cases = [tc for tc in test_cases if tc.category == category]

        if difficulty:
            test_cases = [tc for tc in test_cases if tc.difficulty == difficulty]

        if tags:
            test_cases = [tc for tc in test_cases if tags.issubset(tc.tags)]

        # Sort by name for consistent ordering
        test_cases.sort(key=lambda tc: tc.name)

        # Apply limit
        if limit:
            test_cases = test_cases[:limit]

        return test_cases

    def get_categories(self) -> Dict[str, Dict[str, any]]:
        """Get available test categories with metadata."""
        categories = {}

        for category_name, test_names in self._categories.items():
            category_info = self.TEST_CATEGORIES.get(category_name, {
                "difficulty": "medium",
                "description": f"Tests for {category_name}"
            })

            categories[category_name] = {
                "test_count": len(test_names),
                "difficulty": category_info.get("difficulty", "medium"),
                "description": category_info.get("description", ""),
                "test_names": test_names
            }

        return categories

    def get_test_case(self, name: str) -> Optional[W3CTestCase]:
        """Get specific test case by name."""
        return self._test_cases.get(name)

    def get_basic_compliance_suite(self) -> List[W3CTestCase]:
        """Get a curated suite for basic compliance testing."""
        basic_tests = [
            # Basic shapes
            "basic-shapes-circle",
            "basic-shapes-ellipse",
            "basic-shapes-rect",
            "basic-shapes-polygon",
            "basic-shapes-polyline",

            # Paths
            "paths-line",
            "paths-curve",
            "paths-arc",

            # Text
            "text-simple",
            "text-font",

            # Colors
            "color-rgb",
            "color-keywords",

            # Transforms
            "transforms-translate",
            "transforms-scale",
            "transforms-rotate"
        ]

        return [tc for name in basic_tests if (tc := self.get_test_case(name))]

    def get_comprehensive_suite(self) -> List[W3CTestCase]:
        """Get comprehensive test suite for full compliance testing."""
        return self.get_test_cases(limit=100)  # Limit for performance

    def export_test_manifest(self, output_path: Path) -> bool:
        """Export test case manifest to JSON."""
        try:
            manifest = {
                "suite_info": {
                    "version": self._suite_info.version if self._suite_info else "unknown",
                    "total_tests": len(self._test_cases),
                    "categories": list(self._categories.keys()),
                    "generated_at": datetime.now().isoformat()
                },
                "categories": self.get_categories(),
                "test_cases": []
            }

            # Add test cases
            for test_case in self._test_cases.values():
                manifest["test_cases"].append({
                    "name": test_case.name,
                    "category": test_case.category,
                    "svg_path": str(test_case.svg_path),
                    "reference_image": str(test_case.reference_image) if test_case.reference_image else None,
                    "description": test_case.description,
                    "tags": list(test_case.tags),
                    "difficulty": test_case.difficulty,
                    "spec_section": test_case.spec_section,
                    "expected_features": list(test_case.expected_features)
                })

            with open(output_path, 'w') as f:
                json.dump(manifest, f, indent=2)

            logger.info(f"Test manifest exported to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export test manifest: {e}")
            return False

    def _extract_test_suite(self, zip_path: Path, extract_path: Path, version: str) -> bool:
        """Extract downloaded test suite."""
        try:
            extract_path.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Extract all files
                zip_ref.extractall(extract_path)

                # For some test suites, files might be in a subdirectory
                # Move them to the root if needed
                subdirs = [d for d in extract_path.iterdir() if d.is_dir()]
                if len(subdirs) == 1:
                    subdir = subdirs[0]
                    # Check if the subdir contains the actual test files
                    svg_files = list(subdir.rglob("*.svg"))
                    if svg_files:
                        # Move contents up one level
                        temp_dir = extract_path.parent / f"temp_{version}"
                        subdir.rename(temp_dir)
                        extract_path.rmdir()
                        temp_dir.rename(extract_path)

            return True

        except Exception as e:
            logger.error(f"Failed to extract test suite: {e}")
            return False

    def _parse_test_case(self, svg_path: Path, suite_root: Path) -> Optional[W3CTestCase]:
        """Parse individual test case from SVG file."""
        try:
            # Extract test name and category from path
            relative_path = svg_path.relative_to(suite_root)
            test_name = svg_path.stem

            # Determine category from directory structure
            category = "misc"
            if len(relative_path.parts) > 1:
                category = relative_path.parts[0]

            # Look for reference image
            reference_image = None
            reference_candidates = [
                svg_path.with_suffix('.png'),
                svg_path.parent / f"{svg_path.stem}-ref.png",
                svg_path.parent / "reference" / f"{svg_path.stem}.png"
            ]

            for candidate in reference_candidates:
                if candidate.exists():
                    reference_image = candidate
                    break

            # Parse SVG content for metadata
            description, tags, features = self._parse_svg_metadata(svg_path)

            # Determine difficulty
            difficulty = self.TEST_CATEGORIES.get(category, {}).get("difficulty", "medium")

            test_case = W3CTestCase(
                name=test_name,
                category=category,
                svg_path=svg_path,
                reference_image=reference_image,
                description=description,
                tags=tags,
                difficulty=difficulty,
                expected_features=features
            )

            return test_case

        except Exception as e:
            logger.warning(f"Failed to parse test case {svg_path}: {e}")
            return None

    def _parse_svg_metadata(self, svg_path: Path) -> Tuple[str, Set[str], Set[str]]:
        """Parse SVG file for metadata, description, and features."""
        description = ""
        tags = set()
        features = set()

        try:
            with open(svg_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Look for title and description in SVG
            if '<title>' in content:
                import re
                title_match = re.search(r'<title>(.*?)</title>', content, re.DOTALL)
                if title_match:
                    description = title_match.group(1).strip()

            # Identify SVG features used
            feature_patterns = {
                'gradients': [r'<linearGradient', r'<radialGradient'],
                'patterns': [r'<pattern'],
                'filters': [r'<filter', r'<feGaussianBlur', r'<feColorMatrix'],
                'animations': [r'<animate', r'<animateTransform'],
                'paths': [r'<path'],
                'text': [r'<text', r'<tspan'],
                'transforms': [r'transform='],
                'clipping': [r'clip-path='],
                'masking': [r'mask='],
                'markers': [r'<marker', r'marker-'],
                'scripting': [r'<script']
            }

            for feature, patterns in feature_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        features.add(feature)
                        tags.add(feature)
                        break

            # Add tags based on filename
            filename_lower = svg_path.name.lower()
            if 'basic' in filename_lower:
                tags.add('basic')
            if 'complex' in filename_lower:
                tags.add('complex')
            if 'edge' in filename_lower or 'corner' in filename_lower:
                tags.add('edge-case')

        except Exception as e:
            logger.warning(f"Failed to parse SVG metadata for {svg_path}: {e}")

        return description, tags, features

    def _calculate_suite_checksum(self, suite_path: Path) -> str:
        """Calculate checksum for test suite integrity."""
        try:
            hasher = hashlib.md5()

            # Hash all SVG files in sorted order for consistency
            svg_files = sorted(suite_path.rglob("*.svg"))
            for svg_file in svg_files:
                with open(svg_file, 'rb') as f:
                    hasher.update(f.read())

            return hasher.hexdigest()

        except Exception as e:
            logger.warning(f"Failed to calculate suite checksum: {e}")
            return "unknown"

    @property
    def suite_info(self) -> Optional[TestSuiteInfo]:
        """Get information about loaded test suite."""
        return self._suite_info

    @property
    def is_loaded(self) -> bool:
        """Check if test cases are loaded."""
        return len(self._test_cases) > 0