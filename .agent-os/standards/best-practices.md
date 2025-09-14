# Development Best Practices

## Context

Global development guidelines for Agent OS projects.

<conditional-block context-check="core-principles">
IF this Core Principles section already read in current context:
  SKIP: Re-reading this section
  NOTE: "Using Core Principles already in context"
ELSE:
  READ: The following principles

## Core Principles

### Keep It Simple
- Implement code in the fewest lines possible
- Avoid over-engineering solutions
- Choose straightforward approaches over clever ones

### Optimize for Readability
- Prioritize code clarity over micro-optimizations
- Write self-documenting code with clear variable names
- Add comments for "why" not "what"

### DRY (Don't Repeat Yourself)
- Extract repeated business logic to private methods
- Extract repeated UI markup to reusable components
- Create utility functions for common operations

### File Structure
- Keep files focused on a single responsibility
- Group related functionality together
- Use consistent naming conventions

## 🚨 MANDATORY TESTING STANDARDS (Updated 2025-09-13)

### Unified Testing System - NO EXCEPTIONS
- ✅ **MANDATORY**: `source venv/bin/activate` before ALL test operations
- ✅ **ONLY** use `/tests/` unified structure with systematic templates
- ✅ **ONLY** execute tests via `./venv/bin/python tests/run_tests.py`
- ❌ **FORBIDDEN**: Adhoc test scripts anywhere in project
- ❌ **FORBIDDEN**: Root directory test clutter or scattered test files
- ❌ **FORBIDDEN**: Custom test runners or direct pytest calls
- ❌ **FORBIDDEN**: System Python or non-venv test execution

### Template-Based Development
- **MANDATORY**: Use `/tests/templates/` for all new test creation
- **MANDATORY**: Follow TODO placeholder structure in templates
- **MANDATORY**: Validate structure with `--check-structure` before development
- **MANDATORY**: Place tests in correct category directories

### Zero Tolerance Policy
Any violations result in immediate cleanup:
- Adhoc test scripts → **DELETED**
- Root directory clutter → **REMOVED**
- Non-unified testing → **RESTRUCTURED**

### Current Standards
- 155 organized test files (consolidated from 273 scattered)
- Systematic templates for consistent development
- Tool-standardized architecture maintained
- Unified execution system enforced
</conditional-block>

<conditional-block context-check="dependencies" task-condition="choosing-external-library">
IF current task involves choosing an external library:
  IF Dependencies section already read in current context:
    SKIP: Re-reading this section
    NOTE: "Using Dependencies guidelines already in context"
  ELSE:
    READ: The following guidelines
ELSE:
  SKIP: Dependencies section not relevant to current task

## Dependencies

### Choose Libraries Wisely
When adding third-party dependencies:
- Select the most popular and actively maintained option
- Check the library's GitHub repository for:
  - Recent commits (within last 6 months)
  - Active issue resolution
  - Number of stars/downloads
  - Clear documentation
</conditional-block>
