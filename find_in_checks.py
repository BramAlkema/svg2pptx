#!/usr/bin/env python3
"""Find 'in' checks that might be using lxml method objects."""
import re
import os

def find_in_checks():
    """Find patterns like 'if x in obj.values' without ()."""

    # Look for: "in" followed by something.values/keys/items NOT followed by (
    pattern = r'\bin\s+[^()\n]*\.(values|keys|items)\s*($|[^(])'

    for root, dirs, files in os.walk('core'):
        dirs[:] = [d for d in dirs if d != '__pycache__']

        for file in files:
            if not file.endswith('.py'):
                continue

            filepath = os.path.join(root, file)

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                for line_num, line in enumerate(lines, 1):
                    # Skip comments
                    if line.strip().startswith('#'):
                        continue

                    match = re.search(pattern, line)
                    if match:
                        # Check if it's NOT followed by ()
                        # Extract the part after 'in '
                        in_idx = line.find(' in ')
                        if in_idx >= 0:
                            after_in = line[in_idx+4:].strip()
                            # Check if values/keys/items appears without ()
                            if re.search(r'\.(values|keys|items)\s*[:\n]', after_in):
                                print(f"{filepath}:{line_num}")
                                print(f"  {line.rstrip()}")
                                print()

            except Exception as e:
                pass

if __name__ == '__main__':
    find_in_checks()
