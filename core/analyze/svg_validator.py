"""
SVG Validator for API

Validates SVG content and provides actionable feedback for pre-flight checks.
Leverages existing input validation infrastructure.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from lxml import etree as ET

from core.utils.input_validator import InputValidator, ValidationContext, ValidationError
from .types import CompatibilityLevel, CompatibilityReport
from .constants import SVG_NAMESPACE


class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    ERROR = "error"  # Prevents conversion
    WARNING = "warning"  # May impact quality
    INFO = "info"  # Informational only


@dataclass
class ValidationIssue:
    """Single validation issue."""
    code: str
    message: str
    severity: ValidationSeverity
    element: Optional[str] = None
    line: Optional[int] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "element": self.element,
            "line": self.line,
            "suggestion": self.suggestion
        }


@dataclass
class ValidationResult:
    """SVG validation result."""
    valid: bool
    version: Optional[str] = None
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    compatibility: Optional[CompatibilityReport] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for API response."""
        return {
            "valid": self.valid,
            "version": self.version,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "compatibility": self.compatibility.to_dict() if self.compatibility else None,
            "suggestions": self.suggestions
        }


class SVGValidator:
    """
    SVG Validator using existing input validation infrastructure.

    Provides comprehensive validation including:
    - XML well-formedness
    - SVG semantic validation
    - Attribute validation
    - Feature compatibility checking
    """

    def __init__(self):
        """Initialize validator with input validator."""
        self.input_validator = InputValidator()
        self.svg_ns = SVG_NAMESPACE

    def validate(self, svg_content: str, strict_mode: bool = False) -> ValidationResult:
        """
        Validate SVG content.

        Args:
            svg_content: SVG XML content as string
            strict_mode: Enable strict validation (errors on warnings)

        Returns:
            ValidationResult with errors, warnings, and suggestions
        """
        result = ValidationResult(valid=True)

        # Step 1: XML well-formedness
        try:
            svg_root = ET.fromstring(svg_content.encode('utf-8'))
        except ET.XMLSyntaxError as e:
            result.valid = False
            result.errors.append(ValidationIssue(
                code="XML_PARSE_ERROR",
                message=f"Invalid XML: {str(e)}",
                severity=ValidationSeverity.ERROR,
                line=e.lineno if hasattr(e, 'lineno') else None,
                suggestion="Ensure SVG is valid XML with proper closing tags"
            ))
            return result

        # Step 2: Check SVG root element
        if not self._is_svg_element(svg_root):
            result.errors.append(ValidationIssue(
                code="INVALID_ROOT",
                message="Root element must be <svg>",
                severity=ValidationSeverity.ERROR,
                element=svg_root.tag,
                suggestion="Wrap content in <svg> element"
            ))
            result.valid = False

        # Step 3: Detect SVG version
        result.version = self._detect_svg_version(svg_root)

        # Step 4: Validate viewBox (recommended)
        if not svg_root.get('viewBox'):
            result.warnings.append(ValidationIssue(
                code="MISSING_VIEWBOX",
                message="SVG lacks viewBox attribute",
                severity=ValidationSeverity.WARNING,
                element="svg",
                suggestion="Add viewBox for proper scaling (e.g., viewBox='0 0 100 100')"
            ))

        # Step 5: Collect all elements in single pass (performance optimization)
        elements_by_tag = self._collect_elements(svg_root)

        # Step 6: Validate attributes
        self._validate_attributes(svg_root, result)

        # Step 7: Validate structure
        self._validate_structure(svg_root, result, elements_by_tag)

        # Step 8: Check compatibility
        result.compatibility = self._check_compatibility(svg_root, elements_by_tag)

        # Step 8: Generate suggestions
        result.suggestions = self._generate_suggestions(result)

        # Strict mode: warnings become errors
        if strict_mode and result.warnings:
            result.valid = False

        return result

    def _collect_elements(self, svg_root: ET.Element) -> Dict[str, List[ET.Element]]:
        """
        Collect all elements by tag in a single pass.

        Performance optimization: Single tree traversal instead of multiple findall() calls.
        Reduces O(n*m) to O(n) where n=elements, m=queries.

        Args:
            svg_root: Root SVG element

        Returns:
            Dictionary mapping tag names to lists of elements
        """
        elements = defaultdict(list)

        for elem in svg_root.iter():
            if isinstance(elem.tag, str):
                # Remove namespace prefix if present
                tag = elem.tag.split('}')[-1]
                elements[tag].append(elem)

        return elements

    def _is_svg_element(self, element: ET.Element) -> bool:
        """Check if element is SVG root."""
        return element.tag.endswith('svg') or element.tag == '{%s}svg' % self.svg_ns

    def _detect_svg_version(self, svg_root: ET.Element) -> str:
        """Detect SVG version."""
        version = svg_root.get('version', '1.1')
        return version

    def _validate_attributes(self, svg_root: ET.Element, result: ValidationResult):
        """Validate SVG attributes using input validator."""
        for element in svg_root.iter():
            if not isinstance(element.tag, str):
                continue

            attrs = dict(element.attrib)

            try:
                # Use existing attribute validator
                sanitized = self.input_validator.validate_svg_attributes(attrs)
            except ValidationError as e:
                result.warnings.append(ValidationIssue(
                    code="INVALID_ATTRIBUTE",
                    message=str(e),
                    severity=ValidationSeverity.WARNING,
                    element=element.tag.split('}')[-1]
                ))

            # Validate specific attributes
            self._validate_numeric_attributes(element, result)
            self._validate_color_attributes(element, result)

    def _validate_numeric_attributes(self, element: ET.Element, result: ValidationResult):
        """Validate numeric attributes (width, height, x, y, etc.)."""
        numeric_attrs = ['width', 'height', 'x', 'y', 'cx', 'cy', 'r', 'rx', 'ry']

        for attr in numeric_attrs:
            value = element.get(attr)
            if value:
                try:
                    parsed = self.input_validator.parse_length_safe(value)
                    if parsed is None:
                        result.warnings.append(ValidationIssue(
                            code="INVALID_LENGTH",
                            message=f"Invalid length value: {attr}='{value}'",
                            severity=ValidationSeverity.WARNING,
                            element=element.tag.split('}')[-1],
                            suggestion=f"Use valid length unit (e.g., {attr}='100px')"
                        ))
                except Exception:
                    pass  # Already caught by attribute validator

    def _validate_color_attributes(self, element: ET.Element, result: ValidationResult):
        """Validate color attributes."""
        color_attrs = ['fill', 'stroke', 'stop-color', 'flood-color', 'lighting-color']

        for attr in color_attrs:
            value = element.get(attr)
            if value and value not in ['none', 'currentColor']:
                # Check if it's a valid color (basic check)
                if not (value.startswith('#') or value.startswith('rgb') or
                        value.startswith('url(') or self._is_named_color(value)):
                    result.warnings.append(ValidationIssue(
                        code="INVALID_COLOR",
                        message=f"Potentially invalid color: {attr}='{value}'",
                        severity=ValidationSeverity.WARNING,
                        element=element.tag.split('}')[-1],
                        suggestion="Use hex (#RGB), rgb(), or named colors"
                    ))

    def _validate_structure(self, svg_root: ET.Element, result: ValidationResult,
                           elements_by_tag: Dict[str, List[ET.Element]]):
        """
        Validate SVG structure and element relationships.

        Args:
            svg_root: Root SVG element
            result: Validation result to populate
            elements_by_tag: Pre-collected elements by tag (performance optimization)
        """
        # 1. Check paths with no d attribute
        for path in elements_by_tag.get('path', []):
            if not path.get('d'):
                result.warnings.append(ValidationIssue(
                    code="EMPTY_PATH",
                    message="Path element has no 'd' attribute",
                    severity=ValidationSeverity.WARNING,
                    element="path",
                    suggestion="Add path data or remove empty path element"
                ))

        # 2. Check gradients with too many stops
        for tag in ['linearGradient', 'radialGradient']:
            for gradient in elements_by_tag.get(tag, []):
                # Count stop children
                stops = [child for child in gradient if
                        isinstance(child.tag, str) and child.tag.split('}')[-1] == 'stop']
                if len(stops) > 10:
                    result.suggestions.append(
                        f"Consider simplifying gradient '{gradient.get('id', 'unnamed')}' "
                        f"({len(stops)} stops, recommend ≤10)"
                    )

        # 3. Check for filter complexity
        for filter_elem in elements_by_tag.get('filter', []):
            primitives = [child for child in filter_elem if isinstance(child.tag, str)]
            if len(primitives) > 5:
                result.warnings.append(ValidationIssue(
                    code="COMPLEX_FILTER",
                    message=f"Filter '{filter_elem.get('id', 'unnamed')}' has {len(primitives)} primitives",
                    severity=ValidationSeverity.WARNING,
                    element="filter",
                    suggestion="Complex filters may be rasterized - consider 'quality' policy"
                ))

    def _check_compatibility(self, svg_root: ET.Element,
                            elements_by_tag: Dict[str, List[ET.Element]]) -> CompatibilityReport:
        """
        Check PowerPoint/Google Slides compatibility.

        Args:
            svg_root: Root SVG element
            elements_by_tag: Pre-collected elements by tag (performance optimization)

        Returns:
            CompatibilityReport with platform-specific compatibility levels
        """
        # Default: full compatibility
        powerpoint_2016 = CompatibilityLevel.FULL
        powerpoint_2019 = CompatibilityLevel.FULL
        powerpoint_365 = CompatibilityLevel.FULL
        google_slides = CompatibilityLevel.PARTIAL  # Google Slides has more limitations

        notes = []

        # Check for features that reduce compatibility (using pre-collected elements)
        # Filters
        filters = elements_by_tag.get('filter', [])
        if filters:
            filter_count = len(filters)
            notes.append(f"{filter_count} filters may require EMF fallback")
            google_slides = CompatibilityLevel.LIMITED

        # Mesh gradients
        mesh_gradients = elements_by_tag.get('meshgradient', [])
        if mesh_gradients:
            notes.append("Mesh gradients may have limited compatibility")
            powerpoint_2016 = CompatibilityLevel.PARTIAL
            google_slides = CompatibilityLevel.LIMITED

        # Masks
        masks = elements_by_tag.get('mask', [])
        if masks:
            notes.append("Masks converted to EMF")
            google_slides = CompatibilityLevel.LIMITED

        # Patterns
        patterns = elements_by_tag.get('pattern', [])
        if patterns:
            notes.append("Patterns converted to EMF")

        return CompatibilityReport(
            powerpoint_2016=powerpoint_2016,
            powerpoint_2019=powerpoint_2019,
            powerpoint_365=powerpoint_365,
            google_slides=google_slides,
            notes=notes
        )

    def _generate_suggestions(self, result: ValidationResult) -> List[str]:
        """Generate optimization suggestions based on validation."""
        suggestions = []

        # Suggest policy based on issues
        if result.warnings:
            filter_warnings = [w for w in result.warnings if w.code == "COMPLEX_FILTER"]
            if filter_warnings:
                suggestions.append("Use 'quality' policy for better filter rendering")

        return suggestions

    @staticmethod
    def _is_named_color(color: str) -> bool:
        """Check if color is a named SVG color."""
        from .constants import SVG_NAMED_COLORS
        return color.lower() in SVG_NAMED_COLORS


def create_svg_validator() -> SVGValidator:
    """Factory function to create SVG validator."""
    return SVGValidator()
