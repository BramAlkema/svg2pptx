---
sidebar_position: 1
---

# SVG2PPTX Documentation

Welcome to **SVG2PPTX** - a comprehensive Python library for converting SVG graphics to PowerPoint presentations with advanced features and intelligent preprocessing.

## What is SVG2PPTX?

SVG2PPTX is a powerful conversion tool that transforms SVG (Scalable Vector Graphics) files into PowerPoint presentations (.pptx). Unlike simple converters, SVG2PPTX provides:

- **Intelligent Preprocessing**: SVGO-based optimization pipeline
- **Multi-slide Support**: Automatic detection of slide boundaries
- **Advanced Features**: Filters, patterns, symbols, and animations
- **High Fidelity**: Preserves visual appearance and structure
- **Extensive Customization**: Plugin system and configuration options

## Key Features

### 🎨 **Comprehensive SVG Support**
- Basic shapes (rectangles, circles, paths, polygons)
- Advanced graphics (gradients, patterns, filters)
- Text rendering with font support
- Symbol definitions and reuse
- Transform matrices and coordinate systems

### 🚀 **Multi-slide Generation**
- Animation sequences → Slide sequences
- Nested SVG pages → Separate slides
- Layer groups → Individual slides
- Section markers → Slide boundaries

### ⚡ **Intelligent Preprocessing**
- Path optimization and simplification
- Redundant element removal
- Coordinate system normalization
- Performance optimization
- PowerPoint compatibility fixes

### 🔧 **Developer-Friendly**
- Extensible converter system
- Custom preprocessing plugins
- Comprehensive test suite
- Type hints and documentation
- Performance monitoring tools

## Quick Example

```python
from svg2pptx import convert_svg_to_pptx

# Basic conversion
convert_svg_to_pptx('input.svg', 'output.pptx')

# Multi-slide conversion with options
from svg2pptx import MultiSlideConverter

converter = MultiSlideConverter(enable_multislide_detection=True)
result = converter.convert_svg_to_pptx(
    'complex.svg', 
    'presentation.pptx',
    options={'title': 'My Presentation'}
)

print(f"Created {result['slide_count']} slides")
```

## Architecture Overview

SVG2PPTX follows a modular architecture:

```
SVG Input → Preprocessing → Conversion → PowerPoint Output
    ↓           ↓              ↓            ↓
 Parser    Optimization   DrawingML    PPTX File
          Simplification  Generation
```

1. **Preprocessing**: SVG optimization and simplification
2. **Parsing**: Element-by-element analysis
3. **Conversion**: Transform to PowerPoint equivalents
4. **Generation**: Create final PPTX file

## Getting Started

Choose your path:

- **[Installation](installation)** - Install SVG2PPTX
- **[Quick Start](quick-start)** - Basic usage examples
- **[User Guide](user-guide/basic-usage)** - Comprehensive usage
- **[API Reference](api/core-functions)** - Function documentation
- **[Contributing Guide](contributing)** - Extending SVG2PPTX

## Community & Support

- **GitHub**: [svg2pptx/svg2pptx](https://github.com/svg2pptx/svg2pptx)
- **Issues**: [Report bugs or request features](https://github.com/svg2pptx/svg2pptx/issues)
- **Discussions**: [Community discussions](https://github.com/svg2pptx/svg2pptx/discussions)
- **PyPI**: [svg2pptx package](https://pypi.org/project/svg2pptx/)

## What Makes SVG2PPTX Special?

Unlike other SVG converters, SVG2PPTX is specifically designed for PowerPoint:

- **PowerPoint-First**: Optimized for PowerPoint's capabilities and limitations
- **Preprocessing Pipeline**: Intelligent simplification before conversion
- **Multi-slide Intelligence**: Automatic slide boundary detection
- **High Compatibility**: Extensive testing with real-world SVG files
- **Performance Focused**: Optimized for large and complex documents

Ready to get started? Head to the [Installation](installation) guide!
