# Architecture Reference Index
> Consolidated Documentation Structure
> Version: 1.0.0

## Primary Foundation Document

**[TECHNICAL_FOUNDATION.md](TECHNICAL_FOUNDATION.md)** - The authoritative reference containing all architectural decisions, specifications, and design rationale in structured chapters.

## Chapter Cross-Reference

### 1. System Overview
- **Executive Summary**: Core value proposition and technical scope
- **Architecture Philosophy**: Bottom-up inheritance model and design principles
- **Technology Stack**: Complete technology decisions with rationale

### 2. Technical Deep-Dive
- **Conversion Engine**: Element-to-converter mapping and processing pipeline
- **Coordinate Systems**: SVG to PowerPoint transformation mathematics
- **Font Strategy**: Three-tier resolution system with embedding and fallbacks

### 3. Implementation Details
- **Performance Benchmarks**: Current metrics and optimization strategies
- **Quality Assurance**: Testing pyramid and coverage requirements
- **Integration Patterns**: API design and deployment architectures

### 4. Evolution Record
- **Decision Log**: Major architectural changes with context and impact
- **Version History**: Key milestones in system development
- **Future Roadmap**: Planned enhancements and expansion areas

## Architectural Decision Records (ADRs)

### Core Technology Decisions
- **[ADR-001: lxml Mandate](decisions/ADR-001-lxml-mandate.md)** - XML processing library standardization
- **[ADR-002: Bottom-Up Architecture](decisions/ADR-002-bottom-up-architecture.md)** - Tool inheritance and converter design
- **[ADR-003: Three-Tier Font Strategy](decisions/ADR-003-three-tier-font-strategy.md)** - Font resolution and embedding approach

### Advanced Optimization Decisions
- **[ADR-004: SVGO Python Port](decisions/ADR-004-svgo-python-port.md)** - Native SVG preprocessing implementation
- **[ADR-005: Advanced Path Optimization](decisions/ADR-005-advanced-path-optimization.md)** - Exhaustive path optimization algorithms
- **[ADR-006: Preprocessing Pipeline Architecture](decisions/ADR-006-preprocessing-pipeline-architecture.md)** - Multi-pass optimization pipeline design

## Supporting Documentation

### Current Specifications
- `../../.agent-os/standards/svg2pptx-architecture-diagram.md` - Visual architecture diagrams
- `../../.agent-os/product/tech-stack.md` - Technology compliance standards
- `../../.agent-os/standards/testing-architecture.md` - Testing framework specifications

### Technical Specifications
- `../specifications/ADVANCED_OPTIMIZATIONS.md` - Complete 25+ plugin implementation
- `../specifications/performance-optimization.md` - Performance optimization results
- `../specifications/METADATA_STRATEGY.md` - Metadata handling approach

### Implementation Guides
- `../guides/oauth-setup.md` - Google Workspace integration setup
- `../guides/batch-processing.md` - Batch processing implementation
- `../guides/EXPANSION_FRAMEWORK.md` - Documentation expansion guidelines

### Historical Context
- `../../tools/archive/REFACTORING_SUMMARY.md` - Major refactoring decisions
- `../../tests/TESTING_CONVENTIONS.md` - Testing methodology evolution
- `../archive/BACKLOG.md` - Legacy backlog items

## Usage Guidelines

1. **For New Developers**: Start with TECHNICAL_FOUNDATION.md Executive Overview
2. **For Architecture Decisions**: Reference Evolution & Decision Log sections
3. **For Implementation**: Use Technical Specifications and Performance sections
4. **For Testing**: Follow Quality Assurance Framework guidelines
5. **For Integration**: Consult Integration Patterns and supporting guides

This index ensures all architectural knowledge remains accessible and properly organized as the system evolves.