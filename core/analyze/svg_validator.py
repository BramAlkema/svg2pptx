"""
SVG Validator for API

Validates SVG content and provides actionable feedback for pre-flight checks.
Leverages existing input validation infrastructure.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum
from lxml import etree as ET

from core.utils.input_validator import InputValidator, ValidationContext, ValidationError
from .types import CompatibilityLevel, CompatibilityReport


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
        self.svg_ns = "http://www.w3.org/2000/svg"

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

        # Step 5: Validate attributes
        self._validate_attributes(svg_root, result)

        # Step 6: Validate structure
        self._validate_structure(svg_root, result)

        # Step 7: Check compatibility
        result.compatibility = self._check_compatibility(svg_root)

        # Step 8: Generate suggestions
        result.suggestions = self._generate_suggestions(result)

        # Strict mode: warnings become errors
        if strict_mode and result.warnings:
            result.valid = False

        return result

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

    def _validate_structure(self, svg_root: ET.Element, result: ValidationResult):
        """Validate SVG structure and element relationships."""
        # Check for common issues

        # 1. Empty elements
        for element in svg_root.iter():
            if not isinstance(element.tag, str):
                continue

            tag = element.tag.split('}')[-1]

            # Check paths with no d attribute
            if tag == 'path' and not element.get('d'):
                result.warnings.append(ValidationIssue(
                    code="EMPTY_PATH",
                    message="Path element has no 'd' attribute",
                    severity=ValidationSeverity.WARNING,
                    element="path",
                    suggestion="Add path data or remove empty path element"
                ))

            # Check gradients with too many stops
            if tag in ['linearGradient', 'radialGradient']:
                stops = element.findall(f'{{{self.svg_ns}}}stop')
                if len(stops) > 10:
                    result.suggestions.append(
                        f"Consider simplifying gradient '{element.get('id', 'unnamed')}' "
                        f"({len(stops)} stops, recommend ≤10)"
                    )

        # 2. Check for filter complexity
        filters = svg_root.findall(f'.//{{{self.svg_ns}}}filter')
        for filter_elem in filters:
            primitives = [child for child in filter_elem if isinstance(child.tag, str)]
            if len(primitives) > 5:
                result.warnings.append(ValidationIssue(
                    code="COMPLEX_FILTER",
                    message=f"Filter '{filter_elem.get('id', 'unnamed')}' has {len(primitives)} primitives",
                    severity=ValidationSeverity.WARNING,
                    element="filter",
                    suggestion="Complex filters may be rasterized - consider 'quality' policy"
                ))

    def _check_compatibility(self, svg_root: ET.Element) -> CompatibilityReport:
        """Check PowerPoint/Google Slides compatibility."""
        # Default: full compatibility
        powerpoint_2016 = CompatibilityLevel.FULL
        powerpoint_2019 = CompatibilityLevel.FULL
        powerpoint_365 = CompatibilityLevel.FULL
        google_slides = CompatibilityLevel.PARTIAL  # Google Slides has more limitations

        notes = []

        # Check for features that reduce compatibility
        # Filters
        filters = svg_root.findall(f'.//{{{self.svg_ns}}}filter')
        if filters:
            filter_count = len(filters)
            if filter_count > 0:
                notes.append(f"{filter_count} filters may require EMF fallback")
                google_slides = CompatibilityLevel.LIMITED

        # Mesh gradients
        mesh_gradients = svg_root.findall(f'.//{{{self.svg_ns}}}meshgradient')
        if mesh_gradients:
            notes.append("Mesh gradients may have limited compatibility")
            powerpoint_2016 = CompatibilityLevel.PARTIAL
            google_slides = CompatibilityLevel.LIMITED

        # Masks
        masks = svg_root.findall(f'.//{{{self.svg_ns}}}mask')
        if masks:
            notes.append("Masks converted to EMF")
            google_slides = CompatibilityLevel.LIMITED

        # Patterns
        patterns = svg_root.findall(f'.//{{{self.svg_ns}}}pattern')
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
        named_colors = {
            'black', 'white', 'red', 'green', 'blue', 'yellow', 'cyan', 'magenta',
            'gray', 'grey', 'silver', 'maroon', 'olive', 'lime', 'aqua', 'teal',
            'navy', 'fuchsia', 'purple', 'orange', 'pink', 'brown', 'transparent'
        }
        return color.lower() in named_colors


def create_svg_validator() -> SVGValidator:
    """Factory function to create SVG validator."""
    return SVGValidator()
