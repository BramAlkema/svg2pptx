#!/bin/bash
# Quick Win #3: Add usedforsecurity=False to MD5 usage
# Expected: 9 files in core/

set -e

echo "=== Quick Win #3: Add MD5 Security Flags ==="
echo ""

# Find files with MD5 usage (any form)
echo "Finding files with hashlib.md5 calls..."
files_with_md5=$(grep -rl "hashlib\.md5" core/ 2>/dev/null || true)

if [ -z "$files_with_md5" ]; then
    echo "✅ No MD5 calls without security flag found"
    exit 0
fi

echo "Found files:"
echo "$files_with_md5"
echo ""

# Count occurrences
total_md5=$(grep -r "hashlib\.md5" core/ 2>/dev/null | wc -l || echo "0")
echo "Total MD5 calls: $total_md5"
echo ""

# First show what we'll change
echo "Preview of changes:"
grep -rn "hashlib\.md5" core/ | head -5
echo ""

# Create backups
echo "Creating backups (.md5.bak files)..."
for file in $files_with_md5; do
    cp "$file" "$file.md5.bak"
done

# Fix MD5 calls: hashlib.md5(X) → hashlib.md5(X, usedforsecurity=False)
echo "Adding usedforsecurity=False flag..."
find core/ -name "*.py" -type f \
    -exec sed -i.tmp 's/hashlib\.md5(\([^)]*\))/hashlib.md5(\1, usedforsecurity=False)/g' {} \;

# Clean up temporary files
find core/ -name "*.tmp" -delete

echo ""
echo "✅ Security flags added"
echo ""

# Show changes
echo "Modified lines:"
git diff core/ | grep "hashlib\.md5"

echo ""
echo "Files modified:"
git diff --name-only core/

echo ""
echo "Verify security warnings cleared:"
echo "  bandit -r core/ -lll"
echo ""
echo "To rollback: for f in core/**/*.md5.bak; do mv \$f \${f%.md5.bak}; done"
