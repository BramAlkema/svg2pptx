#!/usr/bin/env python3
"""
Comparison Strategies for Golden Testing

Different ways to compare legacy vs clean implementation outputs.
"""

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
import difflib
import hashlib

from lxml import etree as ET

from .framework import ComparisonResult, ComparisonType, TestResult, GoldenTestCase


class BaseComparator(ABC):
    """Base class for all comparison strategies."""

    def __init__(self, comparison_type: ComparisonType):
        self.comparison_type = comparison_type
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def compare(self, test_case: GoldenTestCase,
               legacy_output: Any, clean_output: Any,
               legacy_duration: float, clean_duration: float,
               temp_dir: Path) -> ComparisonResult:
        """Compare outputs and return result."""
        pass

    def _create_result(self, test_case: GoldenTestCase,
                      legacy_output: Any, clean_output: Any,
                      differences: List[str], metrics: Dict[str, Any],
                      duration: float, error: str = None) -> ComparisonResult:
        """Helper to create comparison result."""
        if error:
            result = TestResult.ERROR
        elif not differences:
            result = TestResult.PASS
        else:
            result = TestResult.FAIL

        return ComparisonResult(
            test_name=test_case.name,
            comparison_type=self.comparison_type,
            result=result,
            legacy_output=legacy_output,
            clean_output=clean_output,
            differences=differences,
            metrics=metrics,
            duration_sec=duration,
            error_message=error
        )


class PPTXComparator(BaseComparator):
    """
    Compares PPTX outputs at binary and structural levels.

    Performs byte-level comparison but also analyzes structural differences
    in the XML content to provide meaningful feedback.
    """

    def __init__(self, ignore_timestamps: bool = True):
        super().__init__(ComparisonType.PPTX_BINARY)
        self.ignore_timestamps = ignore_timestamps

    def compare(self, test_case: GoldenTestCase,
               legacy_output: Any, clean_output: Any,
               legacy_duration: float, clean_duration: float,
               temp_dir: Path) -> ComparisonResult:
        """Compare PPTX binary outputs."""
        start_time = time.perf_counter()

        try:
            # Handle missing outputs
            if legacy_output is None and clean_output is None:
                return self._create_result(
                    test_case, None, None, [], {},
                    time.perf_counter() - start_time,
                    "Both outputs are None"
                )

            if legacy_output is None:
                return self._create_result(
                    test_case, None, clean_output, ["Legacy output is None"], {},
                    time.perf_counter() - start_time
                )

            if clean_output is None:
                return self._create_result(
                    test_case, legacy_output, None, ["Clean output is None"], {},
                    time.perf_counter() - start_time
                )

            # Convert to bytes if needed
            legacy_bytes = self._to_bytes(legacy_output)
            clean_bytes = self._to_bytes(clean_output)

            differences = []
            metrics = {
                'legacy_size': len(legacy_bytes),
                'clean_size': len(clean_bytes),
                'size_difference': len(clean_bytes) - len(legacy_bytes)
            }

            # Size comparison
            if len(legacy_bytes) != len(clean_bytes):
                size_diff = len(clean_bytes) - len(legacy_bytes)
                differences.append(f"Size difference: {size_diff:+} bytes ({len(legacy_bytes)} vs {len(clean_bytes)})")

            # Binary comparison
            if legacy_bytes != clean_bytes:
                # Try to extract and compare XML structure
                try:
                    structural_diff = self._compare_pptx_structure(legacy_bytes, clean_bytes, temp_dir)
                    if structural_diff:
                        differences.extend(structural_diff)
                    else:
                        differences.append("Binary content differs but structure is identical")
                except Exception as e:
                    self.logger.debug(f"Structural comparison failed: {e}")
                    differences.append("Binary content differs (structural analysis failed)")

                # Sample binary differences
                binary_diffs = self._find_binary_differences(legacy_bytes, clean_bytes)
                differences.extend(binary_diffs[:3])  # Limit to first 3 differences

            duration = time.perf_counter() - start_time
            return self._create_result(test_case, legacy_output, clean_output,
                                     differences, metrics, duration)

        except Exception as e:
            return self._create_result(
                test_case, legacy_output, clean_output, [], {},
                time.perf_counter() - start_time, str(e)
            )

    def _to_bytes(self, output: Any) -> bytes:
        """Convert output to bytes."""
        if isinstance(output, bytes):
            return output
        elif isinstance(output, str):
            return output.encode('utf-8')
        elif hasattr(output, 'read'):
            # File-like object
            return output.read()
        else:
            return str(output).encode('utf-8')

    def _compare_pptx_structure(self, legacy_bytes: bytes, clean_bytes: bytes,
                              temp_dir: Path) -> List[str]:
        """Compare PPTX internal structure."""
        differences = []

        try:
            import zipfile
            import io

            # Extract both PPTX files
            legacy_zip = zipfile.ZipFile(io.BytesIO(legacy_bytes))
            clean_zip = zipfile.ZipFile(io.BytesIO(clean_bytes))

            legacy_files = set(legacy_zip.namelist())
            clean_files = set(clean_zip.namelist())

            # Compare file lists
            missing_in_clean = legacy_files - clean_files
            extra_in_clean = clean_files - legacy_files

            if missing_in_clean:
                differences.append(f"Files missing in clean: {', '.join(missing_in_clean)}")
            if extra_in_clean:
                differences.append(f"Extra files in clean: {', '.join(extra_in_clean)}")

            # Compare XML files
            xml_files = [f for f in legacy_files & clean_files if f.endswith('.xml')]
            for xml_file in xml_files[:5]:  # Limit to first 5 XML files
                try:
                    legacy_xml = legacy_zip.read(xml_file).decode('utf-8')
                    clean_xml = clean_zip.read(xml_file).decode('utf-8')

                    if self.ignore_timestamps:
                        legacy_xml = self._remove_timestamps(legacy_xml)
                        clean_xml = self._remove_timestamps(clean_xml)

                    if legacy_xml != clean_xml:
                        differences.append(f"XML difference in {xml_file}")

                        # Try to parse and compare structure
                        try:
                            legacy_tree = ET.fromstring(legacy_xml.encode())
                            clean_tree = ET.fromstring(clean_xml.encode())

                            structural_diff = self._compare_xml_structure(legacy_tree, clean_tree)
                            if structural_diff:
                                differences.extend([f"  {xml_file}: {diff}" for diff in structural_diff[:2]])
                        except Exception:
                            differences.append(f"  {xml_file}: Parse error")

                except Exception as e:
                    differences.append(f"Error comparing {xml_file}: {str(e)}")

        except Exception as e:
            differences.append(f"PPTX structure analysis failed: {str(e)}")

        return differences

    def _remove_timestamps(self, xml_content: str) -> str:
        """Remove timestamp-like content from XML."""
        import re
        # Remove creation/modification dates
        xml_content = re.sub(r'created="[^"]*"', 'created=""', xml_content)
        xml_content = re.sub(r'modified="[^"]*"', 'modified=""', xml_content)
        # Remove random IDs that might differ
        xml_content = re.sub(r'id="[^"]*"', 'id=""', xml_content)
        return xml_content

    def _compare_xml_structure(self, tree1: ET.Element, tree2: ET.Element) -> List[str]:
        """Compare XML element structure."""
        differences = []

        if tree1.tag != tree2.tag:
            differences.append(f"Tag mismatch: {tree1.tag} vs {tree2.tag}")

        # Compare attributes (ignoring order)
        attrs1 = dict(tree1.attrib)
        attrs2 = dict(tree2.attrib)

        if attrs1 != attrs2:
            missing = set(attrs1.keys()) - set(attrs2.keys())
            extra = set(attrs2.keys()) - set(attrs1.keys())
            if missing:
                differences.append(f"Missing attributes: {missing}")
            if extra:
                differences.append(f"Extra attributes: {extra}")

        # Compare child count
        if len(tree1) != len(tree2):
            differences.append(f"Child count mismatch: {len(tree1)} vs {len(tree2)}")

        return differences[:3]  # Limit differences

    def _find_binary_differences(self, data1: bytes, data2: bytes) -> List[str]:
        """Find sample binary differences."""
        differences = []
        max_check = min(len(data1), len(data2), 1000)  # Check first 1KB

        for i in range(max_check):
            if data1[i] != data2[i]:
                differences.append(f"Byte {i}: 0x{data1[i]:02x} vs 0x{data2[i]:02x}")
                if len(differences) >= 3:
                    break

        return differences


class XMLStructureComparator(BaseComparator):
    """
    Compares XML structure of DrawingML content.

    Focuses on semantic equivalence rather than exact byte matching.
    """

    def __init__(self, normalize_whitespace: bool = True):
        super().__init__(ComparisonType.XML_STRUCTURE)
        self.normalize_whitespace = normalize_whitespace

    def compare(self, test_case: GoldenTestCase,
               legacy_output: Any, clean_output: Any,
               legacy_duration: float, clean_duration: float,
               temp_dir: Path) -> ComparisonResult:
        """Compare XML structure."""
        import time
        start_time = time.perf_counter()

        try:
            # Extract XML from outputs
            legacy_xml = self._extract_xml(legacy_output)
            clean_xml = self._extract_xml(clean_output)

            if not legacy_xml or not clean_xml:
                return self._create_result(
                    test_case, legacy_output, clean_output,
                    ["Could not extract XML from outputs"], {},
                    time.perf_counter() - start_time
                )

            # Parse XML
            try:
                legacy_tree = ET.fromstring(legacy_xml.encode())
                clean_tree = ET.fromstring(clean_xml.encode())
            except ET.XMLSyntaxError as e:
                return self._create_result(
                    test_case, legacy_output, clean_output,
                    [f"XML parsing failed: {e}"], {},
                    time.perf_counter() - start_time
                )

            # Compare structure
            differences = self._compare_elements(legacy_tree, clean_tree, path="root")

            metrics = {
                'legacy_elements': self._count_elements(legacy_tree),
                'clean_elements': self._count_elements(clean_tree),
                'legacy_text_length': len(legacy_xml),
                'clean_text_length': len(clean_xml)
            }

            duration = time.perf_counter() - start_time
            return self._create_result(test_case, legacy_output, clean_output,
                                     differences, metrics, duration)

        except Exception as e:
            return self._create_result(
                test_case, legacy_output, clean_output, [], {},
                time.perf_counter() - start_time, str(e)
            )

    def _extract_xml(self, output: Any) -> Optional[str]:
        """Extract XML content from output."""
        if isinstance(output, str):
            if output.strip().startswith('<?xml') or output.strip().startswith('<'):
                return output
        elif isinstance(output, bytes):
            try:
                text = output.decode('utf-8')
                if text.strip().startswith('<?xml') or text.strip().startswith('<'):
                    return text
            except UnicodeDecodeError:
                pass

        # Try to extract from PPTX
        if isinstance(output, bytes):
            try:
                import zipfile
                import io

                with zipfile.ZipFile(io.BytesIO(output)) as zf:
                    # Look for slide XML
                    slide_files = [f for f in zf.namelist() if 'slide' in f and f.endswith('.xml')]
                    if slide_files:
                        return zf.read(slide_files[0]).decode('utf-8')
            except Exception:
                pass

        return None

    def _compare_elements(self, elem1: ET.Element, elem2: ET.Element,
                         path: str = "", max_depth: int = 10) -> List[str]:
        """Recursively compare XML elements."""
        differences = []

        if max_depth <= 0:
            return differences

        # Compare tags
        if elem1.tag != elem2.tag:
            differences.append(f"{path}: tag mismatch ({elem1.tag} vs {elem2.tag})")
            return differences  # Stop if tags don't match

        # Compare attributes
        attrs1 = dict(elem1.attrib)
        attrs2 = dict(elem2.attrib)

        # Remove timestamps and IDs that commonly differ
        ignore_attrs = {'id', 'created', 'modified'}
        for attr in ignore_attrs:
            attrs1.pop(attr, None)
            attrs2.pop(attr, None)

        if attrs1 != attrs2:
            missing = set(attrs1.keys()) - set(attrs2.keys())
            extra = set(attrs2.keys()) - set(attrs1.keys())
            different = {k for k in attrs1.keys() & attrs2.keys() if attrs1[k] != attrs2[k]}

            if missing:
                differences.append(f"{path}: missing attributes {missing}")
            if extra:
                differences.append(f"{path}: extra attributes {extra}")
            if different:
                for attr in list(different)[:2]:  # Limit to 2 differences
                    differences.append(f"{path}@{attr}: '{attrs1[attr]}' vs '{attrs2[attr]}'")

        # Compare text content
        text1 = (elem1.text or "").strip() if self.normalize_whitespace else (elem1.text or "")
        text2 = (elem2.text or "").strip() if self.normalize_whitespace else (elem2.text or "")

        if text1 != text2:
            differences.append(f"{path}: text mismatch ('{text1}' vs '{text2}')")

        # Compare children
        if len(elem1) != len(elem2):
            differences.append(f"{path}: child count mismatch ({len(elem1)} vs {len(elem2)})")

        # Recursively compare children
        for i, (child1, child2) in enumerate(zip(elem1, elem2)):
            child_path = f"{path}/[{i}]{child1.tag.split('}')[-1]}"
            child_diffs = self._compare_elements(child1, child2, child_path, max_depth - 1)
            differences.extend(child_diffs)

            if len(differences) > 20:  # Limit total differences
                differences.append("... (more differences truncated)")
                break

        return differences

    def _count_elements(self, tree: ET.Element) -> int:
        """Count total elements in tree."""
        count = 1  # Count self
        for child in tree:
            count += self._count_elements(child)
        return count


class PerformanceComparator(BaseComparator):
    """
    Compares performance metrics between implementations.

    Tracks conversion time, memory usage, and other performance indicators.
    """

    def __init__(self, time_tolerance_percent: float = 20.0):
        super().__init__(ComparisonType.PERFORMANCE)
        self.time_tolerance_percent = time_tolerance_percent

    def compare(self, test_case: GoldenTestCase,
               legacy_output: Any, clean_output: Any,
               legacy_duration: float, clean_duration: float,
               temp_dir: Path) -> ComparisonResult:
        """Compare performance metrics."""
        import time
        start_time = time.perf_counter()

        differences = []
        metrics = {
            'legacy_duration_sec': legacy_duration,
            'clean_duration_sec': clean_duration,
            'speedup_factor': legacy_duration / max(clean_duration, 0.001),
            'complexity_score': test_case.complexity_score
        }

        # Performance regression check
        time_ratio = clean_duration / max(legacy_duration, 0.001)
        slowdown_percent = (time_ratio - 1.0) * 100

        if slowdown_percent > self.time_tolerance_percent:
            differences.append(f"Performance regression: {slowdown_percent:.1f}% slower ({clean_duration:.3f}s vs {legacy_duration:.3f}s)")
        elif slowdown_percent < -self.time_tolerance_percent:
            differences.append(f"Performance improvement: {-slowdown_percent:.1f}% faster")

        # Timeout check
        if clean_duration > test_case.timeout_sec:
            differences.append(f"Timeout exceeded: {clean_duration:.1f}s > {test_case.timeout_sec}s")

        # Memory estimation (simplified)
        legacy_size = len(str(legacy_output)) if legacy_output else 0
        clean_size = len(str(clean_output)) if clean_output else 0

        metrics.update({
            'legacy_output_size': legacy_size,
            'clean_output_size': clean_size,
            'memory_ratio': clean_size / max(legacy_size, 1)
        })

        duration = time.perf_counter() - start_time
        return self._create_result(test_case, legacy_output, clean_output,
                                 differences, metrics, duration)


class MetricsComparator(BaseComparator):
    """
    Compares high-level conversion metrics.

    Validates that both implementations produce equivalent results
    in terms of element counts, error rates, etc.
    """

    def __init__(self):
        super().__init__(ComparisonType.METRICS)

    def compare(self, test_case: GoldenTestCase,
               legacy_output: Any, clean_output: Any,
               legacy_duration: float, clean_duration: float,
               temp_dir: Path) -> ComparisonResult:
        """Compare conversion metrics."""
        import time
        start_time = time.perf_counter()

        differences = []

        # Basic output comparison
        legacy_success = legacy_output is not None
        clean_success = clean_output is not None

        metrics = {
            'legacy_success': legacy_success,
            'clean_success': clean_success,
            'both_succeeded': legacy_success and clean_success,
            'both_failed': not legacy_success and not clean_success
        }

        if legacy_success != clean_success:
            if legacy_success:
                differences.append("Legacy succeeded but clean failed")
            else:
                differences.append("Clean succeeded but legacy failed")

        # If both succeeded, compare output characteristics
        if legacy_success and clean_success:
            legacy_hash = hashlib.md5(str(legacy_output).encode()).hexdigest()
            clean_hash = hashlib.md5(str(clean_output).encode()).hexdigest()

            metrics.update({
                'outputs_identical': legacy_hash == clean_hash,
                'legacy_hash': legacy_hash[:8],
                'clean_hash': clean_hash[:8]
            })

            if legacy_hash != clean_hash:
                differences.append("Output hashes differ (content not identical)")

        duration = time.perf_counter() - start_time
        return self._create_result(test_case, legacy_output, clean_output,
                                 differences, metrics, duration)