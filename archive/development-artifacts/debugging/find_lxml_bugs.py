#!/usr/bin/env python3
"""Find lxml iterator method calls without parentheses."""
import re
import os
from pathlib import Path

def find_lxml_bugs(directory='core'):
    """Find patterns where lxml methods are used without calling them."""

    patterns = [
        # .attrib.values/keys/items without ()
        (r'\.attrib\.(values|keys|items)\s*[^(]', 'attrib method without ()'),
        # nsmap.values/keys/items without ()
        (r'\.nsmap\.(values|keys|items)\s*[^(]', 'nsmap method without ()'),
        # .iter* methods without ()
        (r'\.iter(children|descendants|siblings|ancestors)?\s+', 'iter method without ()'),
        # Special case: "in obj.iter" pattern
        (r'\bin\s+\w+\.iter\s*[:\n]', 'iter in membership test without ()'),
    ]

    results = []

    for root, dirs, files in os.walk(directory):
        # Skip __pycache__
        dirs[:] = [d for d in dirs if d != '__pycache__']

        for file in files:
            if not file.endswith('.py'):
                continue

            filepath = os.path.join(root, file)

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')

                for line_num, line in enumerate(lines, 1):
                    # Skip comments
                    if line.strip().startswith('#'):
                        continue

                    for pattern, desc in patterns:
                        if re.search(pattern, line):
                            results.append({
                                'file': filepath,
                                'line': line_num,
                                'content': line.strip(),
                                'pattern': desc
                            })
            except Exception as e:
                print(f"Error reading {filepath}: {e}")

    return results

if __name__ == '__main__':
    bugs = find_lxml_bugs()

    if not bugs:
        print("✅ No obvious lxml iterator bugs found with simple patterns")
        print("\nTrying more aggressive search...")

        # Try even more permissive patterns
        for root, dirs, files in os.walk('core'):
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for file in files:
                if not file.endswith('.py'):
                    continue
                filepath = os.path.join(root, file)
                with open(filepath, 'r') as f:
                    content = f.read()
                    # Look for any .iter not followed by (
                    if re.search(r'\.iter\w*\s*[^(]', content):
                        # Check if it's actually a problem
                        for line_num, line in enumerate(content.split('\n'), 1):
                            if '.iter' in line and not line.strip().startswith('#'):
                                # Check if there's a pattern like .iter followed by space or colon
                                if re.search(r'\.iter(children|descendants|siblings)?\s*[:\s]', line):
                                    if '(' not in line or line.find('.iter') < line.find('('):
                                        print(f"\n{filepath}:{line_num}")
                                        print(f"  {line.strip()}")
    else:
        print(f"❌ Found {len(bugs)} potential lxml iterator bugs:\n")
        for bug in bugs:
            print(f"{bug['file']}:{bug['line']}")
            print(f"  Pattern: {bug['pattern']}")
            print(f"  {bug['content']}")
            print()
