---
sidebar_position: 7
---

# Contributing

Thank you for your interest in contributing to SVG2PPTX! This guide will help you get started with contributing code, documentation, or reporting issues.

## Ways to Contribute

- **🐛 Report bugs** - Help us identify and fix issues
- **✨ Suggest features** - Propose new functionality
- **📝 Improve documentation** - Make our docs better
- **🔧 Submit code** - Fix bugs or implement features
- **🧪 Write tests** - Improve test coverage
- **🎨 Create examples** - Show SVG2PPTX in action

## Getting Started

### Development Environment

1. **Fork and clone** the repository:
```bash
git clone https://github.com/yourusername/svg2pptx.git
cd svg2pptx
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install development dependencies**:
```bash
pip install -e .[dev]
```

4. **Run tests** to verify setup:
```bash
pytest tests/
```

### Development Workflow

1. **Create feature branch**:
```bash
git checkout -b feature/your-feature-name
```

2. **Make changes** following our coding standards

3. **Run tests**:
```bash
# Unit tests
pytest tests/unit/

# Integration tests  
pytest tests/integration/

# All tests with coverage
pytest --cov=src --cov-report=term-missing
```

4. **Commit changes**:
```bash
git add .
git commit -m "feat: add new converter for X"
```

5. **Push and create PR**:
```bash
git push origin feature/your-feature-name
```

## Code Style

### Python Standards

We follow **PEP 8** with these additions:

- **Line length**: 88 characters (Black formatter)
- **Import order**: isort with Black compatibility
- **Type hints**: Required for public APIs
- **Docstrings**: Google style for all public functions

### Formatting Tools

```bash
# Format code
black src/ tests/

# Sort imports  
isort src/ tests/

# Check style
flake8 src/ tests/

# Type checking
mypy src/
```

### Pre-commit Hooks

Install pre-commit hooks:
```bash
pre-commit install
```

This automatically runs formatting and checks before commits.

## Writing Code

### Adding New Converters

To add support for a new SVG element:

1. **Create converter class**:
```python
# src/converters/my_converter.py
from .base import BaseConverter

class MyElementConverter(BaseConverter):
    supported_elements = ['myElement']
    
    def can_convert(self, element, context=None):
        return self.get_element_tag(element) in self.supported_elements
    
    def convert(self, element, context):
        # Convert element to DrawingML
        return "<a:sp>...</a:sp>"
```

2. **Register converter**:
```python
# In src/converters/base.py register_default_converters()
from .my_converter import MyElementConverter
self.register_class(MyElementConverter)
```

3. **Write tests**:
```python
# tests/test_my_converter.py
def test_my_element_conversion():
    converter = MyElementConverter()
    element = ET.fromstring('<myElement attr="value"/>')
    result = converter.convert(element, mock_context)
    assert "<a:sp>" in result
```

### Adding Preprocessing Plugins

1. **Create plugin**:
```python
# src/preprocessing/my_plugin.py
from .base import PreprocessingPlugin

class MyOptimizationPlugin(PreprocessingPlugin):
    name = "myOptimization"
    
    def process(self, element, context):
        # Optimize element
        return modified
```

2. **Register plugin**:
```python
# In src/preprocessing/plugins.py
from .my_plugin import MyOptimizationPlugin
```

### Architecture Guidelines

- **Single responsibility** - Each converter handles one element type
- **Dependency injection** - Use context for shared resources  
- **Error handling** - Graceful degradation, not crashes
- **Performance** - Consider memory and speed implications
- **Testability** - Write code that's easy to test

## Testing

### Test Structure

```
tests/
├── unit/                 # Unit tests
│   ├── converters/      # Converter tests
│   ├── preprocessing/   # Preprocessing tests
│   └── core/           # Core functionality tests
├── integration/         # Integration tests
├── visual/             # Visual regression tests
└── fixtures/           # Test data
```

### Writing Tests

```python
import pytest
from unittest.mock import Mock
from src.converters.shapes import RectangleConverter

class TestRectangleConverter:
    def setup_method(self):
        self.converter = RectangleConverter()
        self.context = Mock()
    
    def test_basic_rectangle(self):
        element = ET.fromstring('<rect x="0" y="0" width="100" height="50"/>')
        result = self.converter.convert(element, self.context)
        
        assert '<a:rect>' in result
        assert 'w="100"' in result
        assert 'h="50"' in result
    
    @pytest.mark.parametrize("x,y,expected", [
        (0, 0, "0,0"),
        (10, 20, "10,20"),
        (-5, 15, "-5,15")
    ])
    def test_position_handling(self, x, y, expected):
        # Test with parameters
        pass
```

### Test Categories

- **Unit tests**: Test individual functions/classes
- **Integration tests**: Test component interactions  
- **Visual tests**: Compare visual output
- **Performance tests**: Measure speed and memory
- **Regression tests**: Prevent bugs from returning

## Documentation

### Writing Documentation

- **Clear examples** - Show real usage
- **Complete coverage** - Document all public APIs
- **User focus** - Write for users, not developers
- **Up to date** - Update docs with code changes

### Building Docs

```bash
cd docs/
npm start  # Development server
npm run build  # Production build
```

### Documentation Standards

- **Markdown** for content
- **Code examples** for every feature
- **Screenshots** for visual features  
- **API docs** generated from docstrings

## Submitting Changes

### Pull Request Process

1. **Create descriptive PR title**:
   - `feat:` for new features
   - `fix:` for bug fixes  
   - `docs:` for documentation
   - `test:` for tests
   - `refactor:` for code improvements

2. **Write good PR description**:
```markdown
## Description
Brief description of changes

## Changes
- Added X converter
- Fixed Y bug  
- Updated Z documentation

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Screenshots
(if applicable)
```

3. **Link related issues**: "Fixes #123"

4. **Request review** from maintainers

### Code Review

Reviewers will check:
- **Functionality** - Does it work as intended?
- **Code quality** - Is it well-written and maintainable?
- **Tests** - Are there adequate tests?
- **Documentation** - Is it properly documented?
- **Performance** - Does it impact speed/memory?

## Issue Reporting

### Bug Reports

Include:
- **SVG file** that causes the issue (if possible)
- **Python version** and operating system
- **Complete error message** and stack trace
- **Expected vs actual behavior**
- **Steps to reproduce**

### Feature Requests  

Include:
- **Use case** - What problem does this solve?
- **Proposed solution** - How should it work?
- **Examples** - Show SVG input and expected output
- **Alternative solutions** - Other ways to solve this

## Community Guidelines

### Code of Conduct

- **Be respectful** - Treat everyone with kindness
- **Be inclusive** - Welcome all backgrounds and experience levels
- **Be collaborative** - Work together constructively  
- **Be professional** - Keep discussions focused and productive

### Getting Help

- **GitHub Discussions** for questions and ideas
- **GitHub Issues** for bugs and feature requests
- **Discord/Slack** for real-time chat (if available)
- **Documentation** for usage questions

## Release Process

### Versioning

We use **Semantic Versioning**:
- **Major** (1.0.0): Breaking changes
- **Minor** (0.1.0): New features, backward compatible
- **Patch** (0.0.1): Bug fixes, backward compatible

### Release Checklist

1. Update version in `setup.py`
2. Update `CHANGELOG.md`
3. Run full test suite
4. Create release tag
5. Build and upload to PyPI
6. Update documentation
7. Announce release

## Development Roadmap

See our [Project Board](https://github.com/svg2pptx/svg2pptx/projects) for:
- **Current priorities**
- **Planned features**  
- **Known issues**
- **Help wanted** items

## Recognition

Contributors are recognized in:
- **CONTRIBUTORS.md** file
- **Release notes**
- **Documentation credits**

Thank you for helping make SVG2PPTX better! 🎉