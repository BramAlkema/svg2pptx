"""
Tests for documentation completeness and accuracy validation.
Part of Task 5.1: Documentation and Validation
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass

import pytest


@dataclass
class DocumentationCheck:
    """Represents a documentation validation check."""
    name: str
    passed: bool
    message: str
    severity: str  # 'error', 'warning', 'info'


class TestDocumentationValidation:
    """Test suite for validating testing infrastructure documentation."""
    
    def test_required_documentation_files_exist(self):
        """Test that all required documentation files exist."""
        project_root = Path(__file__).parent.parent
        tests_dir = Path(__file__).parent
        
        required_docs = {
            "README.md": project_root / "README.md",
            "Testing Conventions": tests_dir / "TESTING_CONVENTIONS.md",
            "Fixture Guide": tests_dir / "FIXTURE_AND_MARKER_GUIDE.md",
            "Directory Structure": tests_dir / "DIRECTORY_STRUCTURE.md",
            "Naming Audit": tests_dir / "CURRENT_NAMING_AUDIT.md"
        }
        
        missing_docs = []
        for doc_name, doc_path in required_docs.items():
            if not doc_path.exists():
                missing_docs.append(doc_name)
                print(f"  ❌ Missing: {doc_name} at {doc_path}")
            else:
                print(f"  ✓ Found: {doc_name}")
        
        assert len(missing_docs) == 0, f"Missing documentation files: {missing_docs}"
    
    def test_fixture_documentation_completeness(self):
        """Test that all fixtures are documented."""
        # Get all defined fixtures
        fixtures_dir = Path(__file__).parent / "fixtures"
        documented_fixtures = self._extract_documented_fixtures()
        actual_fixtures = self._extract_actual_fixtures(fixtures_dir)
        
        print(f"\n=== Fixture Documentation Analysis ===")
        print(f"Actual fixtures: {len(actual_fixtures)}")
        print(f"Documented fixtures: {len(documented_fixtures)}")
        
        # Find undocumented fixtures
        undocumented = actual_fixtures - documented_fixtures
        if undocumented:
            print(f"\nUndocumented fixtures ({len(undocumented)}):")
            for fixture in sorted(undocumented)[:10]:  # Show first 10
                print(f"  - {fixture}")
        
        # Find documented but non-existent fixtures
        non_existent = documented_fixtures - actual_fixtures
        if non_existent:
            print(f"\nDocumented but non-existent ({len(non_existent)}):")
            for fixture in sorted(non_existent)[:10]:
                print(f"  - {fixture}")
        
        coverage = len(documented_fixtures & actual_fixtures) / len(actual_fixtures) * 100 if actual_fixtures else 0
        print(f"\nDocumentation coverage: {coverage:.1f}%")
        
        assert coverage >= 80, f"Fixture documentation coverage {coverage:.1f}% is below 80%"
    
    def test_marker_documentation_completeness(self):
        """Test that all markers are documented."""
        project_root = Path(__file__).parent.parent
        
        # Get markers from pyproject.toml
        defined_markers = self._extract_markers_from_pyproject(project_root / "pyproject.toml")
        
        # Get documented markers
        documented_markers = self._extract_documented_markers()
        
        print(f"\n=== Marker Documentation Analysis ===")
        print(f"Defined markers: {len(defined_markers)}")
        print(f"Documented markers: {len(documented_markers)}")
        
        # Find undocumented markers
        undocumented = defined_markers - documented_markers
        if undocumented:
            print(f"\nUndocumented markers:")
            for marker in sorted(undocumented):
                print(f"  - {marker}")
        
        coverage = len(documented_markers & defined_markers) / len(defined_markers) * 100 if defined_markers else 0
        print(f"\nMarker documentation coverage: {coverage:.1f}%")
        
        assert coverage >= 90, f"Marker documentation coverage {coverage:.1f}% is below 90%"
    
    def test_test_execution_procedures_documented(self):
        """Test that test execution procedures are documented."""
        docs_to_check = [
            Path(__file__).parent / "FIXTURE_AND_MARKER_GUIDE.md",
            Path(__file__).parent / "TESTING_CONVENTIONS.md"
        ]
        
        required_sections = [
            "Running Tests",
            "Usage Examples",
            "Best Practices",
            "Troubleshooting"
        ]
        
        print(f"\n=== Test Execution Documentation ===")
        
        for doc_path in docs_to_check:
            if doc_path.exists():
                with open(doc_path, 'r') as f:
                    content = f.read()
                
                print(f"\nChecking {doc_path.name}:")
                found_sections = []
                for section in required_sections:
                    if section.lower() in content.lower():
                        found_sections.append(section)
                        print(f"  ✓ {section}")
                    else:
                        print(f"  ❌ {section}")
                
                coverage = len(found_sections) / len(required_sections) * 100
                assert coverage >= 75, f"{doc_path.name} missing required sections"
    
    def test_code_examples_in_documentation(self):
        """Test that documentation includes code examples."""
        docs_to_check = [
            Path(__file__).parent / "FIXTURE_AND_MARKER_GUIDE.md",
            Path(__file__).parent / "TESTING_CONVENTIONS.md"
        ]
        
        print(f"\n=== Code Examples in Documentation ===")
        
        for doc_path in docs_to_check:
            if doc_path.exists():
                with open(doc_path, 'r') as f:
                    content = f.read()
                
                # Count code blocks
                code_blocks = re.findall(r'```python[\s\S]*?```', content)
                inline_code = re.findall(r'`[^`]+`', content)
                
                print(f"\n{doc_path.name}:")
                print(f"  - Code blocks: {len(code_blocks)}")
                print(f"  - Inline code: {len(inline_code)}")
                
                assert len(code_blocks) >= 3, f"{doc_path.name} should have at least 3 code examples"
    
    def test_documentation_internal_links(self):
        """Test that documentation has proper internal links."""
        guide_path = Path(__file__).parent / "FIXTURE_AND_MARKER_GUIDE.md"
        
        if guide_path.exists():
            with open(guide_path, 'r') as f:
                content = f.read()
            
            # Extract internal links
            internal_links = re.findall(r'\[([^\]]+)\]\(#([^)]+)\)', content)
            
            # Extract headers
            headers = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
            header_anchors = {self._make_anchor(h) for h in headers}
            
            print(f"\n=== Internal Links Validation ===")
            print(f"Headers found: {len(headers)}")
            print(f"Internal links: {len(internal_links)}")
            
            broken_links = []
            for link_text, anchor in internal_links:
                if anchor not in header_anchors:
                    broken_links.append((link_text, anchor))
            
            if broken_links:
                print(f"\nBroken internal links:")
                for text, anchor in broken_links[:5]:
                    print(f"  - [{text}](#{anchor})")
            
            assert len(broken_links) == 0, f"Found {len(broken_links)} broken internal links"
    
    def test_documentation_consistency(self):
        """Test consistency across documentation files."""
        tests_dir = Path(__file__).parent
        
        # Check for consistent terminology
        docs = [
            tests_dir / "FIXTURE_AND_MARKER_GUIDE.md",
            tests_dir / "TESTING_CONVENTIONS.md",
            tests_dir / "DIRECTORY_STRUCTURE.md"
        ]
        
        terminology_checks = {
            "fixture": ["fixture", "fixtures"],
            "marker": ["marker", "markers", "@pytest.mark"],
            "test": ["test", "tests", "testing"]
        }
        
        print(f"\n=== Documentation Consistency ===")
        
        for doc_path in docs:
            if doc_path.exists():
                with open(doc_path, 'r') as f:
                    content = f.read().lower()
                
                print(f"\n{doc_path.name}:")
                for term, variations in terminology_checks.items():
                    count = sum(content.count(var) for var in variations)
                    print(f"  - {term}: {count} occurrences")
    
    def test_readme_testing_section(self):
        """Test that README has a testing section."""
        readme_path = Path(__file__).parent.parent / "README.md"
        
        if readme_path.exists():
            with open(readme_path, 'r') as f:
                content = f.read()
            
            # Check for testing section
            has_testing_section = any(
                section in content.lower() 
                for section in ["## testing", "## tests", "## running tests"]
            )
            
            # Check for test commands
            has_pytest_command = "pytest" in content
            has_test_script = "test" in content.lower()
            
            print(f"\n=== README Testing Section ===")
            print(f"Has testing section: {has_testing_section}")
            print(f"Has pytest command: {has_pytest_command}")
            print(f"Mentions test script: {has_test_script}")
            
            assert has_testing_section or has_pytest_command, "README should document testing"
    
    def test_migration_documentation(self):
        """Test that migration steps are documented."""
        migration_docs = [
            Path(__file__).parent / "CURRENT_NAMING_AUDIT.md",
            Path(__file__).parent / "DIRECTORY_STRUCTURE.md"
        ]
        
        print(f"\n=== Migration Documentation ===")
        
        for doc_path in migration_docs:
            if doc_path.exists():
                with open(doc_path, 'r') as f:
                    content = f.read()
                
                # Check for migration-related content
                has_before_after = "before" in content.lower() and "after" in content.lower()
                has_migration_steps = "migrat" in content.lower()
                has_statistics = bool(re.search(r'\d+\s*(files?|tests?|fixtures?)', content))
                
                print(f"\n{doc_path.name}:")
                print(f"  - Before/After comparison: {has_before_after}")
                print(f"  - Migration mentioned: {has_migration_steps}")
                print(f"  - Has statistics: {has_statistics}")
    
    def test_changelog_or_history(self):
        """Test for documentation of changes."""
        project_root = Path(__file__).parent.parent
        
        changelog_candidates = [
            "CHANGELOG.md",
            "HISTORY.md",
            "CHANGES.md",
            "NEWS.md"
        ]
        
        found_changelog = None
        for candidate in changelog_candidates:
            if (project_root / candidate).exists():
                found_changelog = candidate
                break
        
        print(f"\n=== Change Documentation ===")
        if found_changelog:
            print(f"Found: {found_changelog}")
        else:
            print("No formal changelog found")
            
            # Check if changes are documented elsewhere
            readme_path = project_root / "README.md"
            if readme_path.exists():
                with open(readme_path, 'r') as f:
                    content = f.read().lower()
                
                has_version = "version" in content or "v1." in content or "v0." in content
                has_changes = "change" in content or "update" in content
                
                print(f"README has version info: {has_version}")
                print(f"README mentions changes: {has_changes}")
    
    # Helper methods
    
    def _extract_documented_fixtures(self) -> Set[str]:
        """Extract fixture names from documentation."""
        guide_path = Path(__file__).parent / "FIXTURE_AND_MARKER_GUIDE.md"
        fixtures = set()
        
        if guide_path.exists():
            with open(guide_path, 'r') as f:
                content = f.read()
            
            # Extract fixtures from markdown tables
            table_pattern = r'\|\s*`([^`]+)`\s*\|'
            matches = re.findall(table_pattern, content)
            fixtures.update(matches)
        
        return fixtures
    
    def _extract_actual_fixtures(self, fixtures_dir: Path) -> Set[str]:
        """Extract actual fixture names from code."""
        fixtures = set()
        
        if fixtures_dir.exists():
            for py_file in fixtures_dir.glob("*.py"):
                if py_file.name == "__init__.py":
                    continue
                    
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Find fixture definitions
                pattern = r'@pytest\.fixture.*?\ndef\s+(\w+)\s*\('
                matches = re.findall(pattern, content, re.DOTALL)
                fixtures.update(matches)
        
        return fixtures
    
    def _extract_markers_from_pyproject(self, pyproject_path: Path) -> Set[str]:
        """Extract marker names from pyproject.toml."""
        markers = set()
        
        if pyproject_path.exists():
            with open(pyproject_path, 'r') as f:
                content = f.read()
            
            # Find markers section
            in_markers = False
            for line in content.split('\n'):
                if 'markers = [' in line:
                    in_markers = True
                elif in_markers:
                    if ']' in line:
                        break
                    # Extract marker name from line like: "unit: Unit tests..."
                    match = re.match(r'\s*"(\w+):', line)
                    if match:
                        markers.add(match.group(1))
        
        return markers
    
    def _extract_documented_markers(self) -> Set[str]:
        """Extract marker names from documentation."""
        guide_path = Path(__file__).parent / "FIXTURE_AND_MARKER_GUIDE.md"
        markers = set()
        
        if guide_path.exists():
            with open(guide_path, 'r') as f:
                content = f.read()
            
            # Extract markers from documentation
            pattern = r'@pytest\.mark\.(\w+)'
            matches = re.findall(pattern, content)
            markers.update(matches)
        
        return markers
    
    def _make_anchor(self, header: str) -> str:
        """Convert header text to markdown anchor format."""
        # Remove special characters and convert to lowercase
        anchor = re.sub(r'[^\w\s-]', '', header)
        anchor = re.sub(r'\s+', '-', anchor)
        return anchor.lower()