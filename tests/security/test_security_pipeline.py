#!/usr/bin/env python3
"""
Security Testing Pipeline
Tests to be integrated into CI/CD to catch security issues early.
"""

import pytest
import tempfile
import os
import subprocess
import ast
from pathlib import Path
from typing import List, Set

# Security patterns that should NOT be found in the codebase
DANGEROUS_PATTERNS = [
    # Insecure file operations
    (r'tempfile\.mkdtemp\(\)', 'Use SecureFileService.create_secure_temp_dir() instead'),
    (r'tempfile\.mkstemp\(\)', 'Use SecureFileService.create_secure_temp_file() instead'),
    (r'open\([^,)]+,\s*["\']w["\']', 'Use secure file operations with proper validation'),

    # Unsafe string operations
    (r'\.replace\(["\']px["\'],\s*["\']["\']\)', 'Use InputValidator.parse_length_safe() instead'),
    (r'\.replace\(["\']pt["\'],\s*["\']["\']\)', 'Use InputValidator.parse_length_safe() instead'),
    (r'float\([^)]*\.replace\(', 'Use InputValidator for safe parsing'),
    (r'int\([^)]*\.replace\(', 'Use InputValidator for safe parsing'),

    # SQL injection patterns
    (r'execute\(\s*["\'][^"\']*%[^"\']*["\']', 'Use parameterized queries'),
    (r'cursor\.execute\(\s*f["\']', 'Use parameterized queries, not f-strings'),

    # Command injection patterns
    (r'os\.system\(', 'Use subprocess with proper input validation'),
    (r'subprocess\.[^(]*\(\s*["\'][^"\']*{[^"\']*["\']', 'Avoid string formatting in subprocess calls'),

    # Path traversal patterns
    (r'open\([^)]*\.\.[/\\]', 'Potential path traversal - validate paths first'),
    (r'os\.path\.join\([^)]*\.\.[^)]*\)', 'Potential path traversal - validate paths first'),
]

# Required security imports that should be present
REQUIRED_SECURITY_IMPORTS = [
    'src.services.secure_file_service',
    'src.utils.input_validator',
]


class SecurityTestFailure(Exception):
    """Exception raised when security tests fail."""
    pass


def find_python_files() -> List[Path]:
    """Find all Python files in the source directory."""
    src_dir = Path(__file__).parent.parent.parent / 'src'
    return list(src_dir.rglob('*.py'))


def find_security_violations(file_path: Path) -> List[tuple]:
    """Find security violations in a Python file."""
    violations = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        import re
        for pattern, description in DANGEROUS_PATTERNS:
            matches = re.findall(pattern, content, re.MULTILINE)
            if matches:
                violations.append((str(file_path), pattern, description, len(matches)))

    except Exception as e:
        # Don't fail the entire test for read errors
        pass

    return violations


def check_security_imports(file_path: Path) -> List[str]:
    """Check if file uses security patterns but doesn't import security modules."""
    missing_imports = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if file has patterns that should use security modules
        uses_file_ops = any(pattern in content.lower() for pattern in
                           ['tempfile', 'mkdtemp', 'mkstemp', 'temp_file', 'temp_dir'])
        uses_parsing = any(pattern in content for pattern in
                          ['replace(\'px\'', 'replace("px"', '.replace(\'pt\'', '.replace("pt"'])

        if uses_file_ops and 'secure_file_service' not in content:
            missing_imports.append('secure_file_service for safe file operations')

        if uses_parsing and 'input_validator' not in content:
            missing_imports.append('input_validator for safe parsing')

    except Exception:
        pass

    return missing_imports


@pytest.mark.security
class TestSecurityPipeline:
    """Security tests to be run in CI/CD pipeline."""

    def test_no_dangerous_patterns_in_codebase(self):
        """Ensure no dangerous security patterns exist in the codebase."""
        all_violations = []

        python_files = find_python_files()
        for file_path in python_files:
            violations = find_security_violations(file_path)
            all_violations.extend(violations)

        if all_violations:
            violation_report = "\n".join([
                f"File: {file_path}\n"
                f"Pattern: {pattern}\n"
                f"Issue: {description}\n"
                f"Occurrences: {count}\n"
                for file_path, pattern, description, count in all_violations
            ])

            pytest.fail(
                f"Security violations found in {len(all_violations)} locations:\n\n"
                f"{violation_report}\n\n"
                "Please fix these security issues before committing."
            )

    def test_secure_file_service_integration(self):
        """Test that SecureFileService is properly integrated."""
        from src.services import default_secure_file_service

        # Test basic functionality
        with default_secure_file_service.secure_temp_file_context('.txt') as temp_path:
            assert temp_path is not None
            assert os.path.exists(temp_path)

        # File should be cleaned up
        assert not os.path.exists(temp_path)

        # Test directory creation
        with default_secure_file_service.secure_temp_dir_context() as temp_dir:
            assert temp_dir is not None
            assert os.path.isdir(temp_dir)

        # Directory should be cleaned up
        assert not os.path.exists(temp_dir)

    def test_input_validator_integration(self):
        """Test that InputValidator is properly integrated."""
        from src.utils.input_validator import InputValidator

        validator = InputValidator()

        # Test safe parsing
        assert validator.parse_length_safe('100px') == 100.0
        assert validator.parse_length_safe('invalid') is None

        # Test bounds checking - should raise NumericOverflowError
        with pytest.raises(Exception):  # NumericOverflowError is expected for extremely large numbers
            validator.parse_numeric_safe('999999999999999999999')

        # Test attribute sanitization
        unsafe_attrs = {'onload': 'javascript:alert("xss")'}
        safe_attrs = validator.validate_svg_attributes(unsafe_attrs)
        assert 'javascript:' not in str(safe_attrs.values())

    def test_path_traversal_protection(self):
        """Test that path traversal attacks are prevented."""
        from src.services import default_secure_file_service

        from src.services.secure_file_service import PathTraversalError

        # Test various path traversal attempts
        traversal_attempts = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\config\\sam',
            '%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd',  # URL encoded
        ]

        for attempt in traversal_attempts:
            with pytest.raises(PathTraversalError):
                default_secure_file_service.validate_output_path(attempt)

        # Test system directory protection
        system_paths = ['/etc/shadow', '/proc/version']
        for sys_path in system_paths:
            with pytest.raises(PathTraversalError):
                default_secure_file_service.validate_output_path(sys_path)

    def test_no_hardcoded_secrets(self):
        """Ensure no hardcoded secrets exist in the codebase."""
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']{8,}["\']',
            r'api_key\s*=\s*["\'][^"\']{16,}["\']',
            r'secret\s*=\s*["\'][^"\']{16,}["\']',
            r'token\s*=\s*["\'][^"\']{16,}["\']',
        ]

        violations = []
        python_files = find_python_files()

        import re
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for pattern in secret_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        violations.append((str(file_path), pattern, matches))
            except Exception:
                continue

        if violations:
            violation_report = "\n".join([
                f"File: {file_path}\nPattern: {pattern}\nMatches: {matches}"
                for file_path, pattern, matches in violations
            ])
            pytest.fail(f"Hardcoded secrets found:\n{violation_report}")

    def test_security_headers_present(self):
        """Test that security-related docstrings and comments are present."""
        critical_files = [
            'src/services/secure_file_service.py',
            'src/utils/input_validator.py',
        ]

        for file_path in critical_files:
            full_path = Path(__file__).parent.parent.parent / file_path
            if not full_path.exists():
                pytest.fail(f"Critical security file missing: {file_path}")

            with open(full_path, 'r') as f:
                content = f.read()

            # Check for security-related documentation
            security_keywords = ['security', 'safe', 'validation', 'sanitiz']
            if not any(keyword in content.lower() for keyword in security_keywords):
                pytest.fail(f"Security documentation missing in {file_path}")


@pytest.mark.security
@pytest.mark.slow
def test_comprehensive_security_audit():
    """Run a comprehensive security audit of the entire codebase."""
    python_files = find_python_files()
    audit_results = {
        'files_checked': len(python_files),
        'violations_found': 0,
        'missing_imports': 0,
        'files_with_issues': set()
    }

    for file_path in python_files:
        violations = find_security_violations(file_path)
        missing_imports = check_security_imports(file_path)

        if violations or missing_imports:
            audit_results['files_with_issues'].add(str(file_path))
            audit_results['violations_found'] += len(violations)
            audit_results['missing_imports'] += len(missing_imports)

    # Generate audit report
    audit_report = f"""
Security Audit Results:
======================
Files checked: {audit_results['files_checked']}
Security violations: {audit_results['violations_found']}
Missing security imports: {audit_results['missing_imports']}
Files with issues: {len(audit_results['files_with_issues'])}

Security Score: {(1 - (audit_results['violations_found'] + audit_results['missing_imports']) / max(audit_results['files_checked'], 1)) * 100:.1f}%
"""

    print(audit_report)

    # Fail if critical issues found
    if audit_results['violations_found'] > 0:
        pytest.fail(f"Security audit failed: {audit_results['violations_found']} violations found")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])