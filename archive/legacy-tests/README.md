# Legacy Tests Archive

This directory contains tests from the pre-Clean Slate architecture.

## Why Archived

These tests targeted the old converter-based architecture that has been replaced
by the Clean Slate IR→Analyze→Map→Embed→Package pipeline.

## Contents

- `converters/` - Old BaseConverter and converter system tests
- `integration/` - Old integration and hybrid mode tests
- `filters/` - Outdated filter system tests (pre-refactor)

## Historical Value

Kept for reference in case we need to understand old behavior or recover
test patterns for new implementations.

**DO NOT RUN THESE TESTS** - They will fail against current codebase.

Last archived: 2025-10-03
