#!/bin/bash
# Quick Win #2: Fix legacy src/ imports → core/ imports
# Expected: 20 files, 75+ import statements

set -e

echo "=== Quick Win #2: Fix Legacy src/ Imports ==="
echo ""

# Find files with src/ imports
echo "Finding files with legacy src/ imports..."
files_with_src=$(grep -rl "from src\." tests/e2e/ 2>/dev/null || true)

if [ -z "$files_with_src" ]; then
    echo "✅ No legacy src/ imports found"
    exit 0
fi

echo "Found files:"
echo "$files_with_src"
echo ""

# Count total import statements
total_imports=$(grep -r "from src\." tests/e2e/ 2>/dev/null | wc -l || echo "0")
echo "Total legacy import statements: $total_imports"
echo ""

# Create backups
echo "Creating backups (.legacy.bak files)..."
for file in $files_with_src; do
    cp "$file" "$file.legacy.bak"
done

# Fix src/ → core/ imports
echo "Replacing 'from src.' with 'from core.'..."
find tests/e2e -name "*.py" -type f -not -name "__init__.py" \
    -exec sed -i.tmp 's/from src\./from core./g' {} \;

# Clean up temporary files
find tests/e2e -name "*.tmp" -delete

echo ""
echo "✅ Import migration complete"
echo ""

# Show changes
echo "Modified imports (sample):"
git diff tests/e2e/ | grep "^[-+].*from.*import" | head -20

echo ""
echo "Files modified:"
git diff --name-only tests/e2e/

echo ""
echo "⚠️  IMPORTANT: Some imports may need manual review:"
echo "   - src.svg2pptx → may be in api/ or archive/legacy-src/"
echo "   - Validate with: PYTHONPATH=. pytest tests/e2e/ --collect-only"
echo ""
echo "To rollback: for f in tests/e2e/**/*.legacy.bak; do mv \$f \${f%.legacy.bak}; done"
