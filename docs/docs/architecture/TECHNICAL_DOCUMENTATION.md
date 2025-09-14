# SVG2PPTX Technical Documentation

> Comprehensive technical documentation for the SVG2PPTX conversion system

## 📚 Documentation Structure

### 🏗️ Foundation Reference
- **[TECHNICAL_FOUNDATION.md](../TECHNICAL_FOUNDATION.md)** - Complete system architecture, design decisions, and implementation guide
- **[ARCHITECTURE_REFERENCE.md](ARCHITECTURE_REFERENCE.md)** - Documentation index and navigation guide

### 🎯 Decision Records (ADRs)
- **[ADR-001: lxml Mandate](decisions/ADR-001-lxml-mandate.md)** - XML processing library standardization
- **[ADR-002: Bottom-Up Architecture](decisions/ADR-002-bottom-up-architecture.md)** - Tool inheritance and converter design
- **[ADR-003: Three-Tier Font Strategy](decisions/ADR-003-three-tier-font-strategy.md)** - Font resolution and embedding approach

### 📋 Specifications
- **[specifications/](specifications/)** - Detailed technical specifications (planned)
- **[guides/](guides/)** - Implementation and integration guides (planned)

### 🧭 Quick Navigation

| Need | Document | Section |
|------|----------|---------|
| **System Overview** | [TECHNICAL_FOUNDATION.md](../TECHNICAL_FOUNDATION.md) | § 1-2 Executive Overview & Architecture |
| **Implementation Details** | [TECHNICAL_FOUNDATION.md](../TECHNICAL_FOUNDATION.md) | § 4-6 Conversion Engine & Specifications |
| **Performance & Quality** | [TECHNICAL_FOUNDATION.md](../TECHNICAL_FOUNDATION.md) | § 7-8 Performance & QA Framework |
| **Integration Patterns** | [TECHNICAL_FOUNDATION.md](../TECHNICAL_FOUNDATION.md) | § 9 Integration Patterns |
| **Historical Context** | [TECHNICAL_FOUNDATION.md](../TECHNICAL_FOUNDATION.md) | § 10 Evolution & Decision Log |

## 🎯 Documentation Philosophy

This documentation follows a **foundation-first approach**:

1. **Single Source of Truth**: TECHNICAL_FOUNDATION.md contains all core knowledge
2. **Structured ADRs**: Major decisions documented with context and rationale
3. **Expandable Framework**: Modular structure supports future additions
4. **Developer-Focused**: Emphasis on architectural understanding over user instructions

## 🔄 Maintenance

### Update Triggers
- Major architecture changes → Update TECHNICAL_FOUNDATION.md
- Significant decisions → Create new ADR
- New components → Expand specifications/
- Integration patterns → Add to guides/

### Review Schedule
- **Monthly**: Review TECHNICAL_FOUNDATION.md for accuracy
- **Per Major Release**: Update decision records and specifications
- **Quarterly**: Validate documentation structure and navigation

## 📈 Expansion Areas

Planned documentation additions:

### Specifications (docs/specifications/)
- SVG parsing specification
- DrawingML generation specification
- Font embedding specification
- Performance benchmarking specification

### Guides (docs/guides/)
- New developer onboarding
- Testing strategy implementation
- Deployment and operations
- Integration patterns and examples

### Advanced Topics
- Performance optimization deep-dive
- Advanced SVG features support
- Custom converter development
- Enterprise deployment patterns

---

*This documentation structure ensures comprehensive coverage while remaining maintainable and navigable as the system evolves.*