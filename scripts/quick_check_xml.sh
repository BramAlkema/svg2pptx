#!/bin/bash
# Quick check for forbidden xml.etree.ElementTree imports

echo "🔍 Checking for forbidden ElementTree imports in src/..."

if grep -r --include="*.py" "xml\.etree\.ElementTree" src/ 2>/dev/null; then
    echo "❌ FORBIDDEN: Found ElementTree imports above"
    echo "🔧 Fix: Replace with 'from lxml import etree as ET'"
    exit 1
else
    echo "✅ No forbidden ElementTree imports found"
    exit 0
fi