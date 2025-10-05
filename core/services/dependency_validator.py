#!/usr/bin/env python3
"""
Dependency Injection Validator

Validates ConversionServices dependencies, identifies missing imports,
circular dependencies, and method signature mismatches.
"""

import importlib
import sys
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum


class DependencyIssueType(Enum):
    """Types of dependency issues."""
    MISSING_IMPORT = "missing_import"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    METHOD_MISMATCH = "method_mismatch"
    MISSING_ATTRIBUTE = "missing_attribute"
    INITIALIZATION_FAILURE = "initialization_failure"


@dataclass
class DependencyIssue:
    """Represents a dependency issue."""
    issue_type: DependencyIssueType
    service_name: str
    description: str
    suggested_fix: str
    severity: str  # "critical", "high", "medium", "low"


@dataclass
class ServiceSpec:
    """Specification for a service dependency."""
    name: str
    import_path: str
    class_name: str
    required_methods: List[str]
    initialization_args: Dict[str, Any]


class DependencyValidator:
    """Validates ConversionServices dependencies and identifies issues."""

    def __init__(self):
        """Initialize dependency validator."""
        self.issues: List[DependencyIssue] = []
        self.resolved_imports: Dict[str, Any] = {}

        # Define expected service specifications
        self.service_specs = {
            'unit_converter': ServiceSpec(
                name='unit_converter',
                import_path='src.units',
                class_name='UnitConverter',
                required_methods=['to_emu', 'to_pixels'],
                initialization_args={'context': 'ConversionContext'}
            ),
            'color_factory': ServiceSpec(
                name='color_factory',
                import_path='src.color',
                class_name='Color',
                required_methods=['__init__', 'from_hex'],
                initialization_args={}
            ),
            'transform_parser': ServiceSpec(
                name='transform_parser',
                import_path='src.transforms.engine',
                class_name='TransformEngine',
                required_methods=['parse_to_matrix', 'apply_combined_transforms'],
                initialization_args={}
            ),
            'viewport_resolver': ServiceSpec(
                name='viewport_resolver',
                import_path='src.viewbox',
                class_name='ViewportEngine',
                required_methods=['parse_viewbox', 'calculate_viewport'],
                initialization_args={'unit_engine': 'unit_converter'}
            ),
            'path_system': ServiceSpec(
                name='path_system',
                import_path='src.paths',
                class_name='PathSystem',
                required_methods=['create_path_system'],
                initialization_args={}
            ),
            'style_parser': ServiceSpec(
                name='style_parser',
                import_path='src.utils.style_parser',
                class_name='StyleParser',
                required_methods=['parse_style_string', 'parse_style_attribute'],
                initialization_args={}
            ),
            'coordinate_transformer': ServiceSpec(
                name='coordinate_transformer',
                import_path='src.utils.coordinate_transformer',
                class_name='CoordinateTransformer',
                required_methods=['parse_coordinate_string', 'transform_coordinates'],
                initialization_args={}
            ),
            'font_processor': ServiceSpec(
                name='font_processor',
                import_path='src.utils.font_processor',
                class_name='FontProcessor',
                required_methods=['get_font_family', 'process_font_attributes'],
                initialization_args={}
            ),
            'path_processor': ServiceSpec(
                name='path_processor',
                import_path='src.utils.path_processor',
                class_name='PathProcessor',
                required_methods=['parse_path_string', 'optimize_path'],
                initialization_args={}
            ),
            'pptx_builder': ServiceSpec(
                name='pptx_builder',
                import_path='src.core.pptx_builder',
                class_name='PPTXBuilder',
                required_methods=['create_presentation', 'add_slide'],
                initialization_args={}
            ),
            'gradient_service': ServiceSpec(
                name='gradient_service',
                import_path='src.services.gradient_service',
                class_name='GradientService',
                required_methods=['get_gradient_content', 'create_gradient'],
                initialization_args={}
            ),
            'pattern_service': ServiceSpec(
                name='pattern_service',
                import_path='src.services.pattern_service',
                class_name='PatternService',
                required_methods=['get_pattern_content', 'create_pattern'],
                initialization_args={}
            ),
            'filter_service': ServiceSpec(
                name='filter_service',
                import_path='src.services.filter_service',
                class_name='FilterService',
                required_methods=['get_filter_content', 'apply_filter'],
                initialization_args={}
            ),
            'image_service': ServiceSpec(
                name='image_service',
                import_path='src.services.image_service',
                class_name='ImageService',
                required_methods=['get_image_info', 'process_image'],
                initialization_args={'enable_caching': True}
            )
        }

    def validate_all_dependencies(self) -> List[DependencyIssue]:
        """Validate all ConversionServices dependencies."""
        self.issues = []

        print("🔍 Starting dependency validation...")

        # Step 1: Validate imports
        self._validate_imports()

        # Step 2: Validate method signatures
        self._validate_method_signatures()

        # Step 3: Check for circular dependencies
        self._check_circular_dependencies()

        # Step 4: Test initialization
        self._test_service_initialization()

        return self.issues

    def _validate_imports(self):
        """Validate that all required imports are available."""
        print("📦 Validating imports...")

        for service_name, spec in self.service_specs.items():
            try:
                # Try to import the module
                module = importlib.import_module(spec.import_path)

                # Try to get the class
                if hasattr(module, spec.class_name):
                    service_class = getattr(module, spec.class_name)
                    self.resolved_imports[service_name] = service_class
                    print(f"  ✅ {service_name}: {spec.import_path}.{spec.class_name}")
                else:
                    self.issues.append(DependencyIssue(
                        issue_type=DependencyIssueType.MISSING_IMPORT,
                        service_name=service_name,
                        description=f"Class {spec.class_name} not found in {spec.import_path}",
                        suggested_fix=f"Create {spec.class_name} class in {spec.import_path}",
                        severity="critical"
                    ))
                    print(f"  ❌ {service_name}: Missing class {spec.class_name}")

            except ImportError as e:
                self.issues.append(DependencyIssue(
                    issue_type=DependencyIssueType.MISSING_IMPORT,
                    service_name=service_name,
                    description=f"Cannot import {spec.import_path}: {e}",
                    suggested_fix=f"Create missing module {spec.import_path}",
                    severity="critical"
                ))
                print(f"  ❌ {service_name}: Import failed - {e}")

    def _validate_method_signatures(self):
        """Validate that services have required methods."""
        print("🔧 Validating method signatures...")

        for service_name, service_class in self.resolved_imports.items():
            spec = self.service_specs[service_name]

            for method_name in spec.required_methods:
                if hasattr(service_class, method_name):
                    print(f"  ✅ {service_name}.{method_name}")
                else:
                    # Check for similar method names
                    similar_methods = [m for m in dir(service_class)
                                     if not m.startswith('_') and method_name.lower() in m.lower()]

                    suggested_fix = f"Add {method_name} method to {service_class.__name__}"
                    if similar_methods:
                        suggested_fix += f" (similar methods found: {similar_methods})"

                    self.issues.append(DependencyIssue(
                        issue_type=DependencyIssueType.METHOD_MISMATCH,
                        service_name=service_name,
                        description=f"Missing method {method_name}",
                        suggested_fix=suggested_fix,
                        severity="high"
                    ))
                    print(f"  ❌ {service_name}.{method_name} - Missing")

    def _check_circular_dependencies(self):
        """Check for circular import dependencies."""
        print("🔄 Checking for circular dependencies...")

        # Build dependency graph
        dependency_graph = {}

        for service_name, spec in self.service_specs.items():
            dependencies = []
            for arg_name, arg_value in spec.initialization_args.items():
                if isinstance(arg_value, str) and arg_value in self.service_specs:
                    dependencies.append(arg_value)
            dependency_graph[service_name] = dependencies

        # Check for cycles using DFS
        visited = set()
        rec_stack = set()

        def has_cycle(service):
            visited.add(service)
            rec_stack.add(service)

            for dependency in dependency_graph.get(service, []):
                if dependency not in visited:
                    if has_cycle(dependency):
                        return True
                elif dependency in rec_stack:
                    return True

            rec_stack.remove(service)
            return False

        for service in dependency_graph:
            if service not in visited:
                if has_cycle(service):
                    self.issues.append(DependencyIssue(
                        issue_type=DependencyIssueType.CIRCULAR_DEPENDENCY,
                        service_name=service,
                        description="Circular dependency detected",
                        suggested_fix="Refactor to remove circular dependency",
                        severity="high"
                    ))
                    print(f"  ❌ Circular dependency involving {service}")

        if not any(issue.issue_type == DependencyIssueType.CIRCULAR_DEPENDENCY for issue in self.issues):
            print("  ✅ No circular dependencies found")

    def _test_service_initialization(self):
        """Test that services can be initialized."""
        print("🚀 Testing service initialization...")

        # Try to initialize services in dependency order
        initialized_services = {}

        for service_name, service_class in self.resolved_imports.items():
            try:
                spec = self.service_specs[service_name]
                init_args = {}

                # Resolve initialization arguments
                for arg_name, arg_value in spec.initialization_args.items():
                    if isinstance(arg_value, str) and arg_value in initialized_services:
                        init_args[arg_name] = initialized_services[arg_value]
                    elif arg_value == 'ConversionContext':
                        # Special case for ConversionContext
                        from ..units import ConversionContext
                        init_args[arg_name] = ConversionContext(dpi=96.0)
                    elif isinstance(arg_value, bool):
                        init_args[arg_name] = arg_value

                # Try to initialize
                instance = service_class(**init_args)
                initialized_services[service_name] = instance
                print(f"  ✅ {service_name}: Initialized successfully")

            except Exception as e:
                self.issues.append(DependencyIssue(
                    issue_type=DependencyIssueType.INITIALIZATION_FAILURE,
                    service_name=service_name,
                    description=f"Failed to initialize: {e}",
                    suggested_fix="Fix initialization parameters or constructor",
                    severity="high"
                ))
                print(f"  ❌ {service_name}: Initialization failed - {e}")

    def generate_report(self) -> str:
        """Generate dependency validation report."""
        if not self.issues:
            return "✅ All dependencies validated successfully!"

        report = ["🔍 Dependency Validation Report"]
        report.append("=" * 40)

        # Group issues by type
        issues_by_type = {}
        for issue in self.issues:
            if issue.issue_type not in issues_by_type:
                issues_by_type[issue.issue_type] = []
            issues_by_type[issue.issue_type].append(issue)

        # Generate report for each issue type
        for issue_type, issues in issues_by_type.items():
            report.append(f"\n{issue_type.value.upper()} ({len(issues)} issues):")
            report.append("-" * 30)

            for issue in issues:
                report.append(f"Service: {issue.service_name}")
                report.append(f"Issue: {issue.description}")
                report.append(f"Fix: {issue.suggested_fix}")
                report.append(f"Severity: {issue.severity}")
                report.append("")

        # Summary
        critical_issues = len([i for i in self.issues if i.severity == "critical"])
        high_issues = len([i for i in self.issues if i.severity == "high"])

        report.append("SUMMARY:")
        report.append(f"Total issues: {len(self.issues)}")
        report.append(f"Critical: {critical_issues}")
        report.append(f"High: {high_issues}")
        report.append(f"Other: {len(self.issues) - critical_issues - high_issues}")

        return "\n".join(report)

    def generate_fixes(self) -> Dict[str, str]:
        """Generate code fixes for dependency issues."""
        fixes = {}

        for issue in self.issues:
            if issue.issue_type == DependencyIssueType.METHOD_MISMATCH:
                # Generate method signature fix
                spec = self.service_specs[issue.service_name]
                service_class = self.resolved_imports.get(issue.service_name)

                if service_class:
                    missing_method = None
                    for method in spec.required_methods:
                        if not hasattr(service_class, method):
                            missing_method = method
                            break

                    if missing_method:
                        fixes[f"{issue.service_name}_{missing_method}"] = self._generate_method_stub(
                            service_class, missing_method
                        )

        return fixes

    def _generate_method_stub(self, service_class, method_name: str) -> str:
        """Generate method stub for missing method."""
        return f'''
    def {method_name}(self, *args, **kwargs):
        """
        {method_name} method for {service_class.__name__}.

        TODO: Implement actual functionality.
        """
        raise NotImplementedError("Method {method_name} not implemented")
'''


def main():
    """Run dependency validation."""
    validator = DependencyValidator()
    issues = validator.validate_all_dependencies()

    print("\n" + validator.generate_report())

    if issues:
        print("\n🔧 Suggested fixes:")
        fixes = validator.generate_fixes()
        for fix_name, fix_code in fixes.items():
            print(f"{fix_name}:{fix_code}")

    return len(issues) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)