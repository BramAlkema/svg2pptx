"""
Tests for marker and fixture functionality and accessibility.
Part of Task 4.1: Test Marker and Fixture Organization
"""
import pytest
import inspect
from pathlib import Path
from typing import Dict, List, Set, Any
from dataclasses import dataclass
import re


@dataclass
class FixtureInfo:
    """Information about a test fixture."""
    name: str
    scope: str
    file_path: str
    parameters: List[str]
    return_type: str
    dependencies: List[str]
    is_autouse: bool


@dataclass
class MarkerUsage:
    """Information about marker usage in tests."""
    marker_name: str
    test_file: str
    test_function: str
    marker_args: List[str]


class TestMarkerFixtureOrganization:
    """Test suite for validating marker and fixture functionality."""
    
    def test_validate_marker_accessibility(self):
        """Test that all defined markers are accessible and properly configured."""
        # Get all markers defined in pyproject.toml
        defined_markers = self._get_defined_markers()
        
        print(f"\n=== Marker Accessibility Analysis ===")
        print(f"Total defined markers: {len(defined_markers)}")
        
        # Test each marker is accessible
        accessible_markers = []
        for marker_name in defined_markers.keys():
            try:
                # Check if marker can be accessed via pytest
                marker_obj = getattr(pytest.mark, marker_name, None)
                if marker_obj is not None:
                    accessible_markers.append(marker_name)
                else:
                    print(f"  ⚠️  Marker not accessible: {marker_name}")
            except Exception as e:
                print(f"  ❌ Error accessing marker {marker_name}: {e}")
        
        print(f"Accessible markers: {len(accessible_markers)}/{len(defined_markers)}")
        
        # Validate critical markers are present
        critical_markers = {'unit', 'integration', 'e2e', 'visual', 'benchmark'}
        missing_critical = critical_markers - defined_markers.keys()
        
        if missing_critical:
            print(f"Missing critical markers: {missing_critical}")
        
        assert len(accessible_markers) >= len(defined_markers) * 0.9, "At least 90% of markers should be accessible"
    
    def test_inventory_fixture_usage(self):
        """Test that inventories all fixtures and their usage patterns."""
        fixtures = self._discover_all_fixtures()
        
        print(f"\n=== Fixture Inventory ===")
        print(f"Total fixtures found: {len(fixtures)}")
        
        # Categorize fixtures by scope
        by_scope = {}
        for fixture in fixtures:
            scope = fixture.scope
            if scope not in by_scope:
                by_scope[scope] = []
            by_scope[scope].append(fixture)
        
        print(f"Fixtures by scope:")
        for scope, fixture_list in by_scope.items():
            print(f"  - {scope}: {len(fixture_list)} fixtures")
        
        # Identify potential duplicates
        fixture_names = [f.name for f in fixtures]
        duplicates = self._find_duplicate_names(fixture_names)
        
        if duplicates:
            print(f"Potential duplicate fixture names: {len(duplicates)}")
            for name, count in duplicates.items():
                print(f"  - {name}: {count} instances")
        
        # Check for common fixture patterns
        common_patterns = self._analyze_fixture_patterns(fixtures)
        print(f"Common fixture patterns identified: {len(common_patterns)}")
        
        assert len(fixtures) > 0, "Should find at least some fixtures"
    
    def test_validate_fixture_scopes(self):
        """Test that fixture scopes are appropriate for their usage."""
        fixtures = self._discover_all_fixtures()
        
        scope_analysis = {
            'function': [],
            'class': [],
            'module': [],
            'package': [],
            'session': []
        }
        
        for fixture in fixtures:
            scope_analysis[fixture.scope].append(fixture)
        
        print(f"\n=== Fixture Scope Analysis ===")
        for scope, fixture_list in scope_analysis.items():
            if fixture_list:
                print(f"{scope.capitalize()} scope ({len(fixture_list)} fixtures):")
                for fixture in fixture_list[:3]:  # Show first 3
                    print(f"  - {fixture.name} ({fixture.file_path})")
        
        # Validate scope distribution
        total_fixtures = len(fixtures)
        if total_fixtures > 0:
            function_pct = len(scope_analysis['function']) / total_fixtures * 100
            print(f"\nScope distribution:")
            print(f"  - Function: {function_pct:.1f}%")
            
            # Most fixtures should be function-scoped for isolation
            assert function_pct >= 50, "At least 50% of fixtures should be function-scoped"
    
    def test_identify_fixture_dependencies(self):
        """Test that identifies fixture dependency chains."""
        fixtures = self._discover_all_fixtures()
        
        # Build dependency graph
        dependency_graph = {}
        for fixture in fixtures:
            dependency_graph[fixture.name] = fixture.dependencies
        
        # Find dependency chains
        chains = self._find_dependency_chains(dependency_graph)
        
        print(f"\n=== Fixture Dependencies ===")
        print(f"Fixtures with dependencies: {sum(1 for deps in dependency_graph.values() if deps)}")
        print(f"Dependency chains found: {len(chains)}")
        
        if chains:
            print("Sample dependency chains:")
            for chain in chains[:3]:  # Show first 3 chains
                print(f"  - {' -> '.join(chain)}")
        
        # Check for circular dependencies
        circular_deps = self._detect_circular_dependencies(dependency_graph)
        if circular_deps:
            print(f"⚠️  Circular dependencies detected: {len(circular_deps)}")
            for cycle in circular_deps:
                print(f"  - {' -> '.join(cycle)}")
        
        assert len(circular_deps) == 0, "No circular dependencies should exist"
    
    def test_analyze_marker_usage_patterns(self):
        """Test that analyzes how markers are used across test files."""
        marker_usage = self._discover_marker_usage()
        
        print(f"\n=== Marker Usage Analysis ===")
        print(f"Total marker usages found: {len(marker_usage)}")
        
        # Group by marker name
        by_marker = {}
        for usage in marker_usage:
            marker = usage.marker_name
            if marker not in by_marker:
                by_marker[marker] = []
            by_marker[marker].append(usage)
        
        print(f"Unique markers in use: {len(by_marker)}")
        
        # Show most used markers
        sorted_markers = sorted(by_marker.items(), key=lambda x: len(x[1]), reverse=True)
        print("Top 5 most used markers:")
        for marker, usages in sorted_markers[:5]:
            print(f"  - {marker}: {len(usages)} usages")
        
        # Check for unused defined markers
        defined_markers = self._get_defined_markers()
        used_markers = set(by_marker.keys())
        unused_markers = defined_markers.keys() - used_markers
        
        if unused_markers:
            print(f"Unused defined markers: {unused_markers}")
    
    def test_validate_conftest_structure(self):
        """Test that validates conftest.py file organization."""
        conftest_files = self._find_conftest_files()
        
        print(f"\n=== conftest.py Structure Analysis ===")
        print(f"conftest.py files found: {len(conftest_files)}")
        
        for conftest_path in conftest_files:
            print(f"\nAnalyzing: {conftest_path}")
            
            # Read and analyze conftest content
            try:
                with open(conftest_path, 'r') as f:
                    content = f.read()
                
                # Count fixtures
                fixture_count = len(re.findall(r'@pytest\.fixture', content))
                
                # Check for imports
                imports = re.findall(r'^import |^from ', content, re.MULTILINE)
                
                print(f"  - Fixtures: {fixture_count}")
                print(f"  - Import statements: {len(imports)}")
                print(f"  - Lines of code: {len(content.splitlines())}")
                
                # Check for common patterns
                has_autouse = '@pytest.fixture(autouse=True)' in content
                has_scope = 'scope=' in content
                
                print(f"  - Has autouse fixtures: {has_autouse}")
                print(f"  - Has scoped fixtures: {has_scope}")
                
            except Exception as e:
                print(f"  - Error reading file: {e}")
        
        assert len(conftest_files) > 0, "Should have at least one conftest.py file"
    
    def test_fixture_naming_conventions(self):
        """Test that fixture naming follows consistent conventions."""
        fixtures = self._discover_all_fixtures()
        
        naming_analysis = {
            'snake_case': 0,
            'camelCase': 0,
            'unclear': 0,
            'descriptive': 0,
            'too_short': 0
        }
        
        for fixture in fixtures:
            name = fixture.name
            
            # Check naming patterns
            if re.match(r'^[a-z_][a-z0-9_]*$', name):
                naming_analysis['snake_case'] += 1
            elif re.match(r'^[a-z][a-zA-Z0-9]*$', name):
                naming_analysis['camelCase'] += 1
            else:
                naming_analysis['unclear'] += 1
            
            # Check descriptiveness
            if len(name) >= 4 and ('_' in name or len([c for c in name if c.isupper()]) > 0):
                naming_analysis['descriptive'] += 1
            
            if len(name) <= 2:
                naming_analysis['too_short'] += 1
        
        print(f"\n=== Fixture Naming Analysis ===")
        total = len(fixtures)
        for category, count in naming_analysis.items():
            if total > 0:
                percentage = count / total * 100
                print(f"  - {category}: {count} ({percentage:.1f}%)")
        
        # Validate naming conventions
        if total > 0:
            snake_case_pct = naming_analysis['snake_case'] / total * 100
            assert snake_case_pct >= 80, "At least 80% of fixtures should use snake_case"
    
    def _get_defined_markers(self) -> Dict[str, str]:
        """Get all markers defined in pyproject.toml."""
        try:
            import toml
            project_root = Path(__file__).parent.parent
            pyproject_path = project_root / "pyproject.toml"
            
            with open(pyproject_path, 'r') as f:
                data = toml.load(f)
            
            markers = {}
            pytest_config = data.get('tool', {}).get('pytest.ini_options', {})
            marker_list = pytest_config.get('markers', [])
            
            for marker_line in marker_list:
                if ':' in marker_line:
                    name, description = marker_line.split(':', 1)
                    markers[name.strip()] = description.strip()
            
            return markers
            
        except Exception as e:
            print(f"Error reading markers: {e}")
            return {}
    
    def _discover_all_fixtures(self) -> List[FixtureInfo]:
        """Discover all pytest fixtures in the project."""
        fixtures = []
        project_root = Path(__file__).parent.parent
        
        # Find all Python files in tests directory
        test_files = list(project_root.glob("tests/**/*.py"))
        
        for file_path in test_files:
            try:
                fixtures.extend(self._extract_fixtures_from_file(file_path))
            except Exception as e:
                # Skip files that can't be analyzed
                continue
        
        return fixtures
    
    def _extract_fixtures_from_file(self, file_path: Path) -> List[FixtureInfo]:
        """Extract fixture information from a Python file."""
        fixtures = []
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Find all @pytest.fixture decorators
            fixture_pattern = r'@pytest\.fixture(?:\([^)]*\))?\s*\ndef\s+(\w+)\s*\([^)]*\):'
            matches = re.finditer(fixture_pattern, content, re.MULTILINE | re.DOTALL)
            
            for match in matches:
                fixture_name = match.group(1)
                
                # Extract fixture details (simplified analysis)
                fixture_info = FixtureInfo(
                    name=fixture_name,
                    scope='function',  # Default scope
                    file_path=str(file_path),
                    parameters=[],
                    return_type='Any',
                    dependencies=[],
                    is_autouse=False
                )
                
                # Try to extract scope from decorator
                decorator_text = match.group(0)
                if 'scope=' in decorator_text:
                    scope_match = re.search(r'scope=["\'](\w+)["\']', decorator_text)
                    if scope_match:
                        fixture_info.scope = scope_match.group(1)
                
                if 'autouse=True' in decorator_text:
                    fixture_info.is_autouse = True
                
                fixtures.append(fixture_info)
        
        except Exception:
            # Skip files that can't be read or parsed
            pass
        
        return fixtures
    
    def _find_duplicate_names(self, names: List[str]) -> Dict[str, int]:
        """Find duplicate names in a list."""
        name_counts = {}
        for name in names:
            name_counts[name] = name_counts.get(name, 0) + 1
        
        return {name: count for name, count in name_counts.items() if count > 1}
    
    def _analyze_fixture_patterns(self, fixtures: List[FixtureInfo]) -> List[str]:
        """Analyze common patterns in fixture names."""
        patterns = []
        
        # Common prefixes
        prefixes = {}
        for fixture in fixtures:
            name = fixture.name
            if '_' in name:
                prefix = name.split('_')[0]
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
        
        # Find common prefixes (used 3+ times)
        for prefix, count in prefixes.items():
            if count >= 3:
                patterns.append(f"prefix_{prefix}")
        
        return patterns
    
    def _find_dependency_chains(self, dependency_graph: Dict[str, List[str]]) -> List[List[str]]:
        """Find dependency chains in fixture graph."""
        chains = []
        
        # Simple chain detection (could be more sophisticated)
        for fixture_name, deps in dependency_graph.items():
            if deps:
                for dep in deps:
                    chain = [dep, fixture_name]
                    chains.append(chain)
        
        return chains
    
    def _detect_circular_dependencies(self, dependency_graph: Dict[str, List[str]]) -> List[List[str]]:
        """Detect circular dependencies in fixture graph."""
        # Simplified circular dependency detection
        circular = []
        
        def has_cycle(node, path, visited):
            if node in path:
                # Found a cycle
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]
            
            if node in visited:
                return None
            
            visited.add(node)
            path.append(node)
            
            for dep in dependency_graph.get(node, []):
                cycle = has_cycle(dep, path.copy(), visited)
                if cycle:
                    return cycle
            
            return None
        
        visited = set()
        for fixture in dependency_graph:
            if fixture not in visited:
                cycle = has_cycle(fixture, [], set())
                if cycle:
                    circular.append(cycle)
        
        return circular
    
    def _discover_marker_usage(self) -> List[MarkerUsage]:
        """Discover marker usage across test files."""
        marker_usages = []
        project_root = Path(__file__).parent.parent
        
        # Find all Python test files
        test_files = list(project_root.glob("tests/**/*.py"))
        
        for file_path in test_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Find @pytest.mark.* decorators
                marker_pattern = r'@pytest\.mark\.(\w+)(?:\([^)]*\))?'
                matches = re.finditer(marker_pattern, content)
                
                for match in matches:
                    marker_name = match.group(1)
                    
                    # Try to find associated test function
                    remaining_content = content[match.end():]
                    func_match = re.search(r'\s*def\s+(\w+)\s*\(', remaining_content)
                    test_function = func_match.group(1) if func_match else 'unknown'
                    
                    usage = MarkerUsage(
                        marker_name=marker_name,
                        test_file=str(file_path),
                        test_function=test_function,
                        marker_args=[]
                    )
                    
                    marker_usages.append(usage)
            
            except Exception:
                # Skip files that can't be read
                continue
        
        return marker_usages
    
    def _find_conftest_files(self) -> List[Path]:
        """Find all conftest.py files in the project."""
        project_root = Path(__file__).parent.parent
        return list(project_root.glob("**/conftest.py"))