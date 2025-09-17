# Experimental Prototypes and Research Code

This directory contains experimental code, alternative implementations, and research prototypes that are not part of the core production codebase.

## Directory Structure

### `precision-research/`
Advanced precision and coordinate system research:
- **`fractional_emu_numpy.py`** - NumPy-based EMU precision system with 70-100x performance targets
- **`precision_integration.py`** - Integration layer for fractional EMU system
- **`subpixel_shapes.py`** - Subpixel-accurate shape positioning algorithms

### `alternative-approaches/`
Alternative implementation approaches and specialized features:
- **`svg2pptx_json_v2.py`** - JSON-based conversion using svgelements library
- **`pptx_font_embedder.py`** - Font embedding system for PowerPoint presentations

## Why These Files Were Moved

These files were moved from `src/` because they:

1. **Have 0% test coverage** - Indicating they're not part of tested production code
2. **Are experimental/research-focused** - Headers indicate ambitious performance targets and experimental features
3. **Have complex dependencies** - Some depend on external libraries not in core dependencies
4. **Don't integrate with main pipeline** - Not referenced by core conversion workflow

## Usage Guidelines

- These files are **not part of the production codebase**
- They serve as **research references** and **prototype implementations**
- Before integrating any code from here, ensure:
  - Comprehensive test coverage
  - Performance validation
  - Integration with existing architecture
  - Documentation and maintenance plan

## Development Notes

The precision research prototypes represent interesting approaches to coordinate accuracy, but the current production system already achieves excellent results with simpler, well-tested algorithms. Consider these as inspiration for future enhancements rather than immediate integration targets.