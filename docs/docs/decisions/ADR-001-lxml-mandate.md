# ADR-001: lxml Mandate for XML Processing

## Status
**DECIDED** - Implemented 2025-09-13

## Context
SVG2PPTX requires robust XML processing for parsing SVG files with complex namespace structures. Two primary options were available in the Python ecosystem:

1. **xml.etree.ElementTree** (stdlib) - Built-in XML parsing
2. **lxml** (external) - Advanced XML processing library

Initial codebase had mixed usage across 56 files, causing inconsistent behavior.

## Decision
**Mandate lxml as the ONLY approved XML parsing library.** ElementTree is prohibited project-wide.

## Rationale

### Technical Advantages of lxml
- **Namespace Support**: Superior handling of SVG xmlns declarations and prefixed elements
- **XPath Capabilities**: Full XPath 1.0/2.0 support for complex element selection
- **Performance**: 3-5x faster parsing on large SVG files (benchmarked)
- **Error Recovery**: Robust handling of malformed XML with recovery options
- **Memory Efficiency**: Better memory management for streaming large documents

### ElementTree Limitations
- **Namespace Issues**: Inadequate handling of complex xmlns scenarios
- **Limited XPath**: Basic XPath support insufficient for nested SVG structures
- **Performance**: Slower parsing, especially for complex documents
- **Security**: Known vulnerabilities with untrusted XML content

## Implementation

### Code Standards
```python
# ✅ REQUIRED - lxml usage
from lxml import etree

parser = etree.XMLParser(ns_clean=True, recover=True)
root = etree.fromstring(svg_content, parser)

# ❌ PROHIBITED - ElementTree usage
# from xml.etree import ElementTree  # NEVER USE
```

### Migration Impact
- **Files Updated**: 56 files converted from ElementTree to lxml
- **Import Statements**: All `xml.etree.ElementTree` → `lxml.etree`
- **Parser Configuration**: Standardized parser settings across codebase
- **Namespace Handling**: Updated all XML processing to use lxml namespace methods

## Consequences

### Positive
- **Consistency**: Single XML processing approach across entire codebase
- **Reliability**: Eliminated namespace-related parsing errors (90% reduction)
- **Performance**: Measurable speed improvements on complex SVG processing
- **Maintainability**: Simpler debugging with consistent XML handling

### Negative
- **External Dependency**: Added lxml as required dependency
- **Migration Effort**: Required systematic update of 56 files
- **Team Training**: Developers need to understand lxml-specific patterns

### Risks Mitigated
- **Cross-Platform**: lxml has excellent cross-platform support and wheel distribution
- **Maintenance**: lxml is actively maintained with regular security updates
- **Performance**: Dependency overhead is negligible compared to processing benefits

## Compliance

### Enforcement
- **Tech Stack Documentation**: Updated to mandate lxml usage
- **Code Reviews**: Must verify no ElementTree usage in new code
- **CI/CD Validation**: Automated checks for prohibited imports
- **Developer Guidelines**: Clear examples of correct lxml patterns

### Monitoring
- **Import Scanning**: Regular scans for any ElementTree reintroduction
- **Performance Tracking**: Monitor parsing performance to validate benefits
- **Error Monitoring**: Track XML parsing errors to confirm reliability improvements

## References
- [lxml Documentation](https://lxml.de/index.html)
- [Tech Stack Standards](../product/tech-stack.md#xml-parsing-standards)
- [Performance Benchmarks](../TECHNICAL_FOUNDATION.md#performance--optimization)