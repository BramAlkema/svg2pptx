"""
Fixture dependency management and documentation.

This module defines the dependency relationships between fixtures
and provides utilities for managing fixture lifecycles.
"""
from typing import Dict, List, Set
from dataclasses import dataclass


@dataclass
class FixtureDependency:
    """Represents a fixture and its dependencies."""
    name: str
    scope: str
    depends_on: List[str]
    cleanup_required: bool = False
    description: str = ""


# Define fixture dependency graph
FIXTURE_DEPENDENCIES = {
    # File-related fixtures
    "sample_svg_file": FixtureDependency(
        name="sample_svg_file",
        scope="function",
        depends_on=["temp_dir", "sample_svg_content"],
        cleanup_required=False,  # temp_dir handles cleanup
        description="Creates an SVG file in temp directory"
    ),
    
    "batch_input_files": FixtureDependency(
        name="batch_input_files",
        scope="function",
        depends_on=["temp_dir", "sample_svg_content"],
        cleanup_required=False,
        description="Creates multiple SVG files for batch testing"
    ),
    
    "create_test_zip": FixtureDependency(
        name="create_test_zip",
        scope="function",
        depends_on=["temp_dir"],
        cleanup_required=False,
        description="Factory for creating ZIP files"
    ),
    
    "create_pptx_file": FixtureDependency(
        name="create_pptx_file",
        scope="function",
        depends_on=["temp_dir"],
        cleanup_required=False,
        description="Creates a sample PPTX file"
    ),
    
    # Data directory fixtures
    "benchmark_data_dir": FixtureDependency(
        name="benchmark_data_dir",
        scope="function",
        depends_on=["temp_dir"],
        cleanup_required=False,
        description="Directory for benchmark test data"
    ),
    
    "test_data_dir": FixtureDependency(
        name="test_data_dir",
        scope="function",
        depends_on=[],
        cleanup_required=False,
        description="Path to test data directory"
    ),
    
    "expected_output_dir": FixtureDependency(
        name="expected_output_dir",
        scope="function",
        depends_on=["test_data_dir"],
        cleanup_required=False,
        description="Directory for expected test outputs"
    ),
    
    "baseline_dir": FixtureDependency(
        name="baseline_dir",
        scope="function",
        depends_on=["test_data_dir"],
        cleanup_required=False,
        description="Directory for baseline comparisons"
    ),
    
    # API client fixtures
    "client": FixtureDependency(
        name="client",
        scope="function",
        depends_on=[],
        cleanup_required=True,  # Needs to close connections
        description="FastAPI test client"
    ),
    
    "authenticated_client": FixtureDependency(
        name="authenticated_client",
        scope="function",
        depends_on=["client"],
        cleanup_required=False,
        description="Authenticated FastAPI test client"
    ),
    
    "batch_client": FixtureDependency(
        name="batch_client",
        scope="function",
        depends_on=["batch_app"],
        cleanup_required=True,
        description="Test client for batch API"
    ),
    
    # Mock object fixtures
    "mock_conversion_context": FixtureDependency(
        name="mock_conversion_context",
        scope="function",
        depends_on=[],
        cleanup_required=False,
        description="Mock conversion context for testing"
    ),
    
    "mock_svg_document": FixtureDependency(
        name="mock_svg_document",
        scope="function",
        depends_on=[],
        cleanup_required=False,
        description="Mock SVG document tree"
    ),
    
    "mock_presentation": FixtureDependency(
        name="mock_presentation",
        scope="function",
        depends_on=[],
        cleanup_required=False,
        description="Mock PowerPoint presentation"
    ),
    
    # Environment fixtures
    "setup_test_environment": FixtureDependency(
        name="setup_test_environment",
        scope="session",
        depends_on=[],
        cleanup_required=True,
        description="Sets up test environment variables"
    ),
    
    "cleanup_globals": FixtureDependency(
        name="cleanup_globals",
        scope="function",
        depends_on=[],
        cleanup_required=True,
        description="Cleans up global state after tests"
    )
}


def get_fixture_dependencies(fixture_name: str) -> List[str]:
    """Get all dependencies for a fixture.
    
    Args:
        fixture_name: Name of the fixture
        
    Returns:
        List of fixture names that the specified fixture depends on
    """
    if fixture_name in FIXTURE_DEPENDENCIES:
        return FIXTURE_DEPENDENCIES[fixture_name].depends_on
    return []


def get_fixture_scope(fixture_name: str) -> str:
    """Get the scope of a fixture.
    
    Args:
        fixture_name: Name of the fixture
        
    Returns:
        Scope of the fixture (function, class, module, package, session)
    """
    if fixture_name in FIXTURE_DEPENDENCIES:
        return FIXTURE_DEPENDENCIES[fixture_name].scope
    return "function"  # Default scope


def get_fixtures_requiring_cleanup() -> List[str]:
    """Get list of fixtures that require explicit cleanup.
    
    Returns:
        List of fixture names that need cleanup
    """
    return [
        name for name, dep in FIXTURE_DEPENDENCIES.items()
        if dep.cleanup_required
    ]


def validate_fixture_dependencies() -> Dict[str, List[str]]:
    """Validate fixture dependency graph for issues.
    
    Returns:
        Dictionary of issues found, keyed by fixture name
    """
    issues = {}
    
    for fixture_name, dependency in FIXTURE_DEPENDENCIES.items():
        fixture_issues = []
        
        # Check for circular dependencies
        if has_circular_dependency(fixture_name, set()):
            fixture_issues.append("Circular dependency detected")
        
        # Check for scope violations
        fixture_scope = dependency.scope
        for dep_name in dependency.depends_on:
            if dep_name in FIXTURE_DEPENDENCIES:
                dep_scope = FIXTURE_DEPENDENCIES[dep_name].scope
                if is_scope_violation(fixture_scope, dep_scope):
                    fixture_issues.append(
                        f"Scope violation: {fixture_scope} fixture depends on {dep_scope} fixture {dep_name}"
                    )
        
        # Check for missing dependencies
        for dep_name in dependency.depends_on:
            if dep_name not in FIXTURE_DEPENDENCIES:
                # This is okay - dependency might be defined elsewhere
                pass
        
        if fixture_issues:
            issues[fixture_name] = fixture_issues
    
    return issues


def has_circular_dependency(fixture_name: str, visited: Set[str]) -> bool:
    """Check if a fixture has circular dependencies.
    
    Args:
        fixture_name: Name of the fixture to check
        visited: Set of already visited fixtures
        
    Returns:
        True if circular dependency exists
    """
    if fixture_name in visited:
        return True
    
    if fixture_name not in FIXTURE_DEPENDENCIES:
        return False
    
    visited.add(fixture_name)
    
    for dep_name in FIXTURE_DEPENDENCIES[fixture_name].depends_on:
        if has_circular_dependency(dep_name, visited.copy()):
            return True
    
    return False


def is_scope_violation(fixture_scope: str, dependency_scope: str) -> bool:
    """Check if there's a scope violation.
    
    A fixture cannot depend on a fixture with a narrower scope.
    
    Args:
        fixture_scope: Scope of the fixture
        dependency_scope: Scope of the dependency
        
    Returns:
        True if there's a scope violation
    """
    scope_order = ["session", "package", "module", "class", "function"]
    
    try:
        fixture_index = scope_order.index(fixture_scope)
        dependency_index = scope_order.index(dependency_scope)
        
        # Violation if dependency has narrower scope (higher index)
        return dependency_index > fixture_index
    except ValueError:
        # Unknown scope, assume no violation
        return False


def get_fixture_cleanup_order() -> List[str]:
    """Get the order in which fixtures should be cleaned up.
    
    Returns:
        List of fixture names in cleanup order (reverse dependency order)
    """
    cleanup_order = []
    visited = set()
    
    def visit(fixture_name: str):
        if fixture_name in visited:
            return
        
        visited.add(fixture_name)
        
        if fixture_name in FIXTURE_DEPENDENCIES:
            # Visit dependencies first
            for dep in FIXTURE_DEPENDENCIES[fixture_name].depends_on:
                visit(dep)
            
            # Add fixture after its dependencies
            if FIXTURE_DEPENDENCIES[fixture_name].cleanup_required:
                cleanup_order.append(fixture_name)
    
    for fixture_name in FIXTURE_DEPENDENCIES:
        visit(fixture_name)
    
    # Reverse to get cleanup order (opposite of setup order)
    return list(reversed(cleanup_order))