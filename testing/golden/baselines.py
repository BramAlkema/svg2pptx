#!/usr/bin/env python3
"""
Baseline Management for Golden Testing

Handles creation, storage, and validation of golden baselines.
"""

import logging
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from .framework import GoldenTestCase


class BaselineStrategy(Enum):
    """Strategy for baseline management."""
    STRICT = "strict"           # Exact byte-for-byte match required
    STRUCTURAL = "structural"   # XML structure must match, ignore formatting
    SEMANTIC = "semantic"       # Semantic equivalence (most lenient)


@dataclass
class GoldenBaseline:
    """
    Represents a stored golden baseline.

    Contains the expected output and metadata for validation.
    """
    name: str
    test_case_hash: str
    output_hash: str
    created_at: str
    implementation: str
    strategy: BaselineStrategy
    metadata: Dict[str, Any]

    @classmethod
    def create(cls, test_case: GoldenTestCase, output: Any,
              implementation: str, strategy: BaselineStrategy) -> 'GoldenBaseline':
        """Create baseline from test case and output."""
        test_hash = hashlib.md5(test_case.svg_content.encode()).hexdigest()
        output_hash = hashlib.md5(str(output).encode()).hexdigest()

        return cls(
            name=test_case.name,
            test_case_hash=test_hash,
            output_hash=output_hash,
            created_at=datetime.now().isoformat(),
            implementation=implementation,
            strategy=strategy,
            metadata={
                'tags': test_case.tags,
                'complexity_score': test_case.complexity_score,
                'expected_elements': test_case.expected_elements,
                'description': test_case.description
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GoldenBaseline':
        """Create from dictionary."""
        return cls(**data)


class BaselineManager:
    """
    Manages golden baselines for test validation.

    Provides functionality to create, store, load, and validate baselines
    with support for different comparison strategies.
    """

    def __init__(self, baseline_dir: Path):
        """
        Initialize baseline manager.

        Args:
            baseline_dir: Directory for storing baselines
        """
        self.baseline_dir = Path(baseline_dir)
        self.baseline_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(__name__)
        self._manifest_path = self.baseline_dir / "manifest.json"
        self._manifest: Dict[str, GoldenBaseline] = {}
        self._load_manifest()

    def create_baseline(self, test_case: GoldenTestCase, output: Any,
                       implementation: str = "legacy",
                       strategy: BaselineStrategy = BaselineStrategy.STRICT) -> GoldenBaseline:
        """
        Create and store new baseline.

        Args:
            test_case: Test case to create baseline for
            output: Expected output
            implementation: Implementation that generated output
            strategy: Comparison strategy for this baseline

        Returns:
            Created baseline object
        """
        baseline = GoldenBaseline.create(test_case, output, implementation, strategy)

        # Store output data
        output_path = self._get_output_path(baseline.name, implementation)
        self._store_output(output, output_path)

        # Update manifest
        key = f"{baseline.name}_{implementation}_{strategy.value}"
        self._manifest[key] = baseline
        self._save_manifest()

        self.logger.info(f"Created baseline: {key}")
        return baseline

    def get_baseline(self, test_name: str, implementation: str = "legacy",
                    strategy: BaselineStrategy = BaselineStrategy.STRICT) -> Optional[GoldenBaseline]:
        """
        Get stored baseline.

        Args:
            test_name: Name of test case
            implementation: Implementation type
            strategy: Comparison strategy

        Returns:
            Baseline object or None if not found
        """
        key = f"{test_name}_{implementation}_{strategy.value}"
        return self._manifest.get(key)

    def load_baseline_output(self, baseline: GoldenBaseline) -> Any:
        """
        Load the stored output for a baseline.

        Args:
            baseline: Baseline to load output for

        Returns:
            Stored output data
        """
        output_path = self._get_output_path(baseline.name, baseline.implementation)
        return self._load_output(output_path)

    def validate_test_case(self, test_case: GoldenTestCase, output: Any,
                          implementation: str = "clean",
                          strategy: BaselineStrategy = BaselineStrategy.STRICT) -> Tuple[bool, List[str]]:
        """
        Validate test case output against baseline.

        Args:
            test_case: Test case being validated
            output: Output to validate
            implementation: Implementation being tested
            strategy: Comparison strategy

        Returns:
            Tuple of (is_valid, differences)
        """
        # Get baseline (use legacy as reference)
        baseline = self.get_baseline(test_case.name, "legacy", strategy)
        if not baseline:
            return False, [f"No baseline found for {test_case.name}"]

        # Verify test case hasn't changed
        test_hash = hashlib.md5(test_case.svg_content.encode()).hexdigest()
        if test_hash != baseline.test_case_hash:
            return False, ["Test case has changed since baseline creation"]

        # Load expected output
        try:
            expected_output = self.load_baseline_output(baseline)
        except Exception as e:
            return False, [f"Failed to load baseline output: {e}"]

        # Compare based on strategy
        if strategy == BaselineStrategy.STRICT:
            return self._strict_comparison(expected_output, output)
        elif strategy == BaselineStrategy.STRUCTURAL:
            return self._structural_comparison(expected_output, output)
        elif strategy == BaselineStrategy.SEMANTIC:
            return self._semantic_comparison(expected_output, output)
        else:
            return False, [f"Unknown baseline strategy: {strategy}"]

    def list_baselines(self, test_name_filter: str = None) -> List[GoldenBaseline]:
        """
        List stored baselines.

        Args:
            test_name_filter: Optional filter for test names

        Returns:
            List of matching baselines
        """
        baselines = list(self._manifest.values())

        if test_name_filter:
            baselines = [b for b in baselines if test_name_filter in b.name]

        return sorted(baselines, key=lambda x: x.name)

    def delete_baseline(self, test_name: str, implementation: str = "legacy",
                       strategy: BaselineStrategy = BaselineStrategy.STRICT) -> bool:
        """
        Delete stored baseline.

        Args:
            test_name: Name of test case
            implementation: Implementation type
            strategy: Comparison strategy

        Returns:
            True if baseline was deleted
        """
        key = f"{test_name}_{implementation}_{strategy.value}"
        baseline = self._manifest.get(key)

        if not baseline:
            return False

        # Remove output file
        output_path = self._get_output_path(baseline.name, baseline.implementation)
        try:
            if output_path.exists():
                output_path.unlink()
        except Exception as e:
            self.logger.warning(f"Failed to delete output file {output_path}: {e}")

        # Remove from manifest
        del self._manifest[key]
        self._save_manifest()

        self.logger.info(f"Deleted baseline: {key}")
        return True

    def update_baseline(self, test_case: GoldenTestCase, output: Any,
                       implementation: str = "legacy",
                       strategy: BaselineStrategy = BaselineStrategy.STRICT) -> GoldenBaseline:
        """
        Update existing baseline with new output.

        Args:
            test_case: Test case to update
            output: New expected output
            implementation: Implementation type
            strategy: Comparison strategy

        Returns:
            Updated baseline
        """
        # Delete existing baseline
        self.delete_baseline(test_case.name, implementation, strategy)

        # Create new baseline
        return self.create_baseline(test_case, output, implementation, strategy)

    def export_baselines(self, export_path: Path) -> None:
        """
        Export all baselines to archive.

        Args:
            export_path: Path for export archive
        """
        import tarfile

        with tarfile.open(export_path, 'w:gz') as tar:
            # Add manifest
            tar.add(self._manifest_path, arcname="manifest.json")

            # Add all output files
            for baseline in self._manifest.values():
                output_path = self._get_output_path(baseline.name, baseline.implementation)
                if output_path.exists():
                    arcname = f"outputs/{baseline.name}_{baseline.implementation}"
                    tar.add(output_path, arcname=arcname)

        self.logger.info(f"Exported {len(self._manifest)} baselines to {export_path}")

    def import_baselines(self, import_path: Path) -> int:
        """
        Import baselines from archive.

        Args:
            import_path: Path to import archive

        Returns:
            Number of baselines imported
        """
        import tarfile

        imported_count = 0

        with tarfile.open(import_path, 'r:gz') as tar:
            # Extract manifest
            manifest_member = tar.getmember("manifest.json")
            manifest_data = tar.extractfile(manifest_member).read()
            imported_manifest = json.loads(manifest_data.decode())

            # Extract output files and update manifest
            for key, baseline_data in imported_manifest.items():
                baseline = GoldenBaseline.from_dict(baseline_data)

                # Extract output file
                output_arcname = f"outputs/{baseline.name}_{baseline.implementation}"
                try:
                    output_member = tar.getmember(output_arcname)
                    output_data = tar.extractfile(output_member).read()

                    # Store output
                    output_path = self._get_output_path(baseline.name, baseline.implementation)
                    with open(output_path, 'wb') as f:
                        f.write(output_data)

                    # Update manifest
                    self._manifest[key] = baseline
                    imported_count += 1

                except KeyError:
                    self.logger.warning(f"Output file missing for baseline {key}")

        self._save_manifest()
        self.logger.info(f"Imported {imported_count} baselines from {import_path}")
        return imported_count

    def _get_output_path(self, test_name: str, implementation: str) -> Path:
        """Get path for storing output data."""
        return self.baseline_dir / f"{test_name}_{implementation}.output"

    def _store_output(self, output: Any, path: Path) -> None:
        """Store output data to file."""
        if isinstance(output, bytes):
            with open(path, 'wb') as f:
                f.write(output)
        elif isinstance(output, str):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(output)
        else:
            # Convert to string and store
            with open(path, 'w', encoding='utf-8') as f:
                f.write(str(output))

    def _load_output(self, path: Path) -> Any:
        """Load output data from file."""
        if not path.exists():
            raise FileNotFoundError(f"Output file not found: {path}")

        # Try binary first
        try:
            with open(path, 'rb') as f:
                data = f.read()
            # Check if it's text
            try:
                return data.decode('utf-8')
            except UnicodeDecodeError:
                return data
        except Exception:
            # Fallback to text
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()

    def _load_manifest(self) -> None:
        """Load manifest from disk."""
        if not self._manifest_path.exists():
            self._manifest = {}
            return

        try:
            with open(self._manifest_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._manifest = {
                key: GoldenBaseline.from_dict(baseline_data)
                for key, baseline_data in data.items()
            }

        except Exception as e:
            self.logger.error(f"Failed to load manifest: {e}")
            self._manifest = {}

    def _save_manifest(self) -> None:
        """Save manifest to disk."""
        try:
            data = {
                key: baseline.to_dict()
                for key, baseline in self._manifest.items()
            }

            with open(self._manifest_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save manifest: {e}")

    def _strict_comparison(self, expected: Any, actual: Any) -> Tuple[bool, List[str]]:
        """Perform strict byte-for-byte comparison."""
        differences = []

        if type(expected) != type(actual):
            differences.append(f"Type mismatch: {type(expected)} vs {type(actual)}")
            return False, differences

        if expected != actual:
            if isinstance(expected, bytes) and isinstance(actual, bytes):
                if len(expected) != len(actual):
                    differences.append(f"Size mismatch: {len(expected)} vs {len(actual)} bytes")
                else:
                    # Find first difference
                    for i, (a, b) in enumerate(zip(expected, actual)):
                        if a != b:
                            differences.append(f"First difference at byte {i}: 0x{a:02x} vs 0x{b:02x}")
                            break
            else:
                differences.append("Content differs")

        return len(differences) == 0, differences

    def _structural_comparison(self, expected: Any, actual: Any) -> Tuple[bool, List[str]]:
        """Compare XML structure, ignoring formatting differences."""
        differences = []

        try:
            from lxml import etree as ET

            # Convert to XML if needed
            expected_xml = self._extract_xml_for_comparison(expected)
            actual_xml = self._extract_xml_for_comparison(actual)

            if not expected_xml or not actual_xml:
                return self._strict_comparison(expected, actual)

            # Parse and normalize
            expected_tree = ET.fromstring(expected_xml.encode())
            actual_tree = ET.fromstring(actual_xml.encode())

            # Compare structure recursively
            differences = self._compare_xml_elements(expected_tree, actual_tree)

        except Exception as e:
            differences.append(f"Structural comparison failed: {e}")

        return len(differences) == 0, differences

    def _semantic_comparison(self, expected: Any, actual: Any) -> Tuple[bool, List[str]]:
        """Compare semantic meaning, most lenient."""
        # For now, use structural comparison
        # In the future, could implement more sophisticated semantic analysis
        return self._structural_comparison(expected, actual)

    def _extract_xml_for_comparison(self, data: Any) -> Optional[str]:
        """Extract XML content for comparison."""
        if isinstance(data, str):
            return data
        elif isinstance(data, bytes):
            try:
                return data.decode('utf-8')
            except UnicodeDecodeError:
                # Try to extract from PPTX
                try:
                    import zipfile
                    import io

                    with zipfile.ZipFile(io.BytesIO(data)) as zf:
                        slide_files = [f for f in zf.namelist() if 'slide' in f and f.endswith('.xml')]
                        if slide_files:
                            return zf.read(slide_files[0]).decode('utf-8')
                except Exception:
                    pass
        return None

    def _compare_xml_elements(self, elem1, elem2, path: str = "root") -> List[str]:
        """Compare XML elements structurally."""
        differences = []

        # Compare tags
        if elem1.tag != elem2.tag:
            differences.append(f"{path}: tag mismatch ({elem1.tag} vs {elem2.tag})")

        # Compare children count
        if len(elem1) != len(elem2):
            differences.append(f"{path}: child count mismatch ({len(elem1)} vs {len(elem2)})")

        # Recursively compare children
        for i, (child1, child2) in enumerate(zip(elem1, elem2)):
            child_path = f"{path}[{i}]"
            child_diffs = self._compare_xml_elements(child1, child2, child_path)
            differences.extend(child_diffs[:5])  # Limit differences

            if len(differences) > 20:
                differences.append("... (more differences truncated)")
                break

        return differences