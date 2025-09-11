---
sidebar_position: 2
---

# Installation

Learn how to install SVG2PPTX and set up your development environment.

## Requirements

SVG2PPTX requires Python 3.8 or higher and has the following dependencies:

### System Requirements
- **Python**: 3.8+
- **Operating System**: Windows, macOS, or Linux
- **Memory**: Minimum 512MB RAM for basic conversions
- **Disk Space**: 100MB for installation

### Required Dependencies
- `lxml` - XML processing
- `python-pptx` - PowerPoint file generation
- `Pillow` - Image processing
- `numpy` - Numerical computations

### Optional Dependencies
- `fonttools` - Advanced font processing
- `uharfbuzz` - Text shaping (for complex scripts)
- `cairosvg` - SVG rasterization fallback

## Installation Methods

### Option 1: Install from PyPI (Recommended)

The easiest way to install SVG2PPTX is using pip:

```bash
pip install svg2pptx
```

For the latest features, install the pre-release version:

```bash
pip install --pre svg2pptx
```

### Option 2: Install with Optional Dependencies

For full functionality including advanced text processing:

```bash
# Install with font processing support
pip install svg2pptx[fonts]

# Install with all optional dependencies
pip install svg2pptx[all]
```

### Option 3: Development Installation

For contributors and developers:

```bash
# Clone the repository
git clone https://github.com/svg2pptx/svg2pptx.git
cd svg2pptx

# Install in development mode
pip install -e .

# Install with development dependencies
pip install -e .[dev]
```

### Option 4: Install from Source

To install the latest development version directly:

```bash
pip install git+https://github.com/svg2pptx/svg2pptx.git
```

## Verify Installation

Test your installation:

```python
import svg2pptx
print(svg2pptx.__version__)

# Run a basic conversion test
from svg2pptx import convert_svg_to_pptx
print("SVG2PPTX is ready!")
```

If successful, you should see the version number and confirmation message.

## Troubleshooting Common Issues

### Issue: `lxml` Installation Fails

**Problem**: XML processing dependency fails to install.

**Solution**:
```bash
# On Ubuntu/Debian
sudo apt-get install libxml2-dev libxslt-dev python3-dev

# On macOS with Homebrew
brew install libxml2 libxslt

# On Windows, try:
pip install --only-binary=lxml lxml
```

### Issue: Font Processing Not Available

**Problem**: Advanced font features don't work.

**Solution**: Install font processing dependencies:
```bash
pip install fonttools uharfbuzz
```

### Issue: Memory Errors with Large SVGs

**Problem**: Conversion fails with large or complex SVG files.

**Solutions**:
1. **Increase memory**: Use preprocessing to simplify SVGs
2. **Enable streaming**: Use batch processing mode
3. **Reduce precision**: Lower numerical precision in preprocessing

```python
from svg2pptx.preprocessing import create_optimizer

# Create optimized converter
optimizer = create_optimizer(precision=2)
optimized_svg = optimizer.optimize_svg_file('large_file.svg')
```

### Issue: PowerPoint Compatibility Problems

**Problem**: Generated PPTX files don't open properly.

**Solutions**:
1. **Check PowerPoint version**: Ensure you have PowerPoint 2010+
2. **Validate output**: Use built-in validation
3. **Enable strict mode**: More compatible output

```python
convert_svg_to_pptx(
    'input.svg', 
    'output.pptx',
    strict_mode=True  # Better compatibility
)
```

## Platform-Specific Notes

### Windows

- Use **Windows Subsystem for Linux (WSL)** for better compatibility
- Install **Microsoft Visual C++ Build Tools** if compilation fails
- Consider using **conda** instead of pip for complex dependencies

### macOS

- Install **Xcode Command Line Tools**: `xcode-select --install`
- Use **Homebrew** for system dependencies
- **Apple Silicon (M1/M2)**: All dependencies have native support

### Linux

- Install development packages: `build-essential`, `python3-dev`
- Use distribution package manager for system libraries
- **Alpine Linux**: Use `apk add --no-cache gcc musl-dev libxml2-dev libxslt-dev`

## Docker Installation

Use the official Docker image:

```bash
# Pull the image
docker pull svg2pptx/svg2pptx:latest

# Run conversion
docker run --rm -v $(pwd):/workspace svg2pptx/svg2pptx:latest \
    python -m svg2pptx input.svg output.pptx
```

Create your own Dockerfile:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libxml2-dev libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Install SVG2PPTX
RUN pip install svg2pptx[all]

WORKDIR /workspace
CMD ["python", "-m", "svg2pptx", "--help"]
```

## Virtual Environment Setup

Recommended for project isolation:

```bash
# Create virtual environment
python -m venv svg2pptx-env

# Activate (Linux/macOS)
source svg2pptx-env/bin/activate

# Activate (Windows)
svg2pptx-env\Scripts\activate

# Install SVG2PPTX
pip install svg2pptx
```

## Conda Installation

Using conda-forge channel:

```bash
# Install from conda-forge
conda install -c conda-forge svg2pptx

# Or create environment with dependencies
conda create -n svg2pptx python=3.11 svg2pptx -c conda-forge
conda activate svg2pptx
```

## Next Steps

- **[Quick Start](quick-start)** - Your first conversion
- **[Basic Usage](user-guide/basic-usage)** - Common patterns
- **[API Reference](api/core-functions)** - Customize behavior
- **[Contributing](contributing)** - Development setup

## Getting Help

If you encounter installation issues:

1. **Check the logs**: Look for specific error messages
2. **Search issues**: Check [GitHub Issues](https://github.com/svg2pptx/svg2pptx/issues)
3. **Ask for help**: Create a new issue with:
   - Your operating system and Python version
   - Complete error message
   - Steps you've already tried

Happy converting! 🎉