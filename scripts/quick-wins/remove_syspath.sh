#!/bin/bash
# Quick Win #1: Remove sys.path manipulation from E2E tests
# Expected: 22 files affected

set -e

echo "=== Quick Win #1: Remove sys.path Manipulation ==="
echo ""

# Find and remove sys.path.insert lines
echo "Finding files with sys.path manipulation..."
files_with_syspath=$(grep -rl "sys\.path\.insert.*src" tests/e2e/ || true)

if [ -z "$files_with_syspath" ]; then
    echo "✅ No sys.path manipulation found"
    exit 0
fi

echo "Found files:"
echo "$files_with_syspath"
echo ""

# Create backups
echo "Creating backups (.bak files)..."
for file in $files_with_syspath; do
    cp "$file" "$file.bak"
done

# Remove sys.path.insert lines
echo "Removing sys.path.insert lines..."
find tests/e2e -name "*.py" -type f -not -name "__init__.py" \
    -exec sed -i.tmp '/sys\.path\.insert.*src/d' {} \;

# Remove orphaned 'import sys' if it's now unused
# (Only if sys is imported alone and has no other usage)
find tests/e2e -name "*.py" -type f -not -name "__init__.py" -exec sh -c '
    file="$1"
    if grep -q "^import sys$" "$file" && ! grep -v "^import sys$" "$file" | grep -q "sys\."; then
        sed -i.tmp2 "/^import sys$/d" "$file"
        rm -f "$file.tmp2"
    fi
' _ {} \;

# Clean up temporary files
find tests/e2e -name "*.tmp" -delete

echo ""
echo "✅ Cleanup complete"
echo ""
echo "Files modified:"
git diff --name-only tests/e2e/

echo ""
echo "To verify: PYTHONPATH=. pytest tests/e2e/ --collect-only"
echo "To rollback: for f in tests/e2e/**/*.bak; do mv \$f \${f%.bak}; done"
