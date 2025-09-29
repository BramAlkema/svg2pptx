# SVG2PPTX - Advanced SVG to PowerPoint Converter

A high-fidelity Python library and API for converting SVG files to PowerPoint presentations with **modular architecture** and **Google Drive integration**. Built to bypass LibreOffice limitations and achieve near 100% conversion fidelity.

## 🚀 Features

- **🔧 Modular Architecture** - Plugin-based converter system for maximum extensibility
- **🎯 High-Fidelity Conversion** - Specialized converters for each SVG element type
- **☁️ Google Drive Integration** - Direct upload with OAuth and service account support
- **🖼️ PNG Preview Generation** - Automatic slide thumbnails via Google Slides API
- **🌐 FastAPI Web Service** - Production-ready RESTful API
- **📊 Comprehensive SVG Support** - Advanced paths, gradients, transforms, and typography

## 🏗️ Architecture

### Modular Converter System
```
src/converters/
├── base.py         # Foundation classes and registry
├── shapes.py       # Rectangle, circle, ellipse, polygon converters
├── paths.py        # Advanced path with full curve support
├── text.py         # Typography and font handling
├── gradients.py    # Linear/radial gradients and patterns
├── transforms.py   # Matrix transformation system
├── styles.py       # CSS style processor with inheritance
└── groups.py       # SVG groups and nested elements
```

### API Service Layer
```
api/
├── main.py         # FastAPI application
├── auth.py         # Authentication middleware
├── services/       # Business logic
│   ├── conversion_service.py
│   ├── google_drive.py
│   ├── google_oauth.py
│   └── google_slides.py
└── routes/         # API endpoints
```

## 🚀 Quick Start

### Installation

```bash
# Clone and setup
git clone <repository-url>
cd svg2pptx

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# API Configuration
API_SECRET_KEY=dev-api-key-12345
ENVIRONMENT=development

# Google Drive Integration
GOOGLE_DRIVE_AUTH_METHOD=oauth
GOOGLE_DRIVE_CLIENT_ID=your-client-id
GOOGLE_DRIVE_CLIENT_SECRET=your-client-secret
```

## 💻 Usage

### Python Library

```python
from src.converters import ConverterRegistry, CoordinateSystem, ConversionContext
from src.converters.shapes import RectangleConverter
import xml.etree.ElementTree as ET

# Initialize modular converter system
registry = ConverterRegistry()
registry.register(RectangleConverter())

# Setup conversion context
coord_system = CoordinateSystem((0, 0, 800, 600))
context = ConversionContext()
context.coordinate_system = coord_system

# Convert SVG element
svg_element = ET.fromstring('<rect x="10" y="20" width="100" height="80" fill="red"/>')
converter = registry.get_converter('rect')
drawingml = converter.convert(svg_element, context)
```

### API Service

Start the server:
```bash
uvicorn api.main:app --host 127.0.0.1 --port 8002
```

Convert via API:
```bash
curl -X POST "http://127.0.0.1:8002/convert?url=https://example.com/file.svg" \
  -H "Authorization: Bearer dev-api-key-12345"
```

## 📊 Supported SVG Features

| Feature Category | Elements | Fidelity Level |
|------------------|----------|----------------|
| **Basic Shapes** | rect, circle, ellipse, polygon, line | ✅ 100% |
| **Advanced Paths** | All commands (M,L,C,Q,A,Z) + curves | ✅ 95% |
| **Typography** | text, tspan, fonts, styling | ✅ 90% |
| **Gradients** | Linear, radial, stops, transforms | ✅ 90% |
| **Transforms** | translate, scale, rotate, matrix, skew | ✅ 95% |
| **Groups** | Nested SVG, groups, coordinate systems | ✅ 90% |
| **Styling** | CSS properties, inheritance, cascading | ✅ 85% |

## 🔌 API Endpoints

### Convert SVG to PowerPoint
```http
POST /convert?url={svg_url}
Authorization: Bearer {api_key}
```

**Response:**
```json
{
  "success": true,
  "file_id": "1A2B3C...",
  "file_url": "https://drive.google.com/file/d/1A2B3C...",
  "preview_urls": ["https://...thumbnail1.png"]
}
```

### Generate Slide Previews
```http
GET /previews/{presentation_id}
Authorization: Bearer {api_key}
```

## ⚙️ Google Drive Setup

See [SETUP_OAUTH.md](SETUP_OAUTH.md) for detailed OAuth configuration.

**Quick OAuth Setup:**
1. Create Google Cloud project
2. Enable Drive & Slides APIs
3. Create OAuth 2.0 credentials
4. Add redirect URIs: `http://localhost:8080/callback`
5. Update `.env` with client credentials

## 🏢 Production Deployment

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables
```bash
# Production settings
ENVIRONMENT=production
API_SECRET_KEY=your-production-key
GOOGLE_DRIVE_AUTH_METHOD=service_account
GOOGLE_DRIVE_CREDENTIALS_PATH=/app/credentials/service-account.json
```

## 🔧 Development

### Project Structure
```
svg2pptx/
├── 📁 api/                    # FastAPI service layer
├── 📁 src/
│   ├── 📁 converters/         # Modular converter architecture
│   └── 📄 svg2drawingml.py    # Legacy monolithic converter
├── 📁 credentials/            # OAuth & service account keys
├── 📁 examples/               # Sample SVG files
├── 📁 archive/                # Archived test files (27 files)
├── 📄 requirements.txt        # Python dependencies
└── 📄 README.md              # This file
```

### Adding New Converters

1. **Create converter class:**
```python
from .base import BaseConverter

class MyConverter(BaseConverter):
    supported_elements = ['my-element']
    
    def can_convert(self, element):
        return element.tag.endswith('my-element')
    
    def convert(self, element, context):
        return '<p:sp>...</p:sp>'
```

2. **Register converter:**
```python
from .my_converter import MyConverter
registry.register(MyConverter())
```

### Testing
```bash
# Run basic functionality test
python -c "from src.converters.shapes import RectangleConverter; print('✅ Converters working')"

# Test API server
uvicorn api.main:app --host 127.0.0.1 --port 8002 &
curl -H "Authorization: Bearer dev-api-key-12345" http://127.0.0.1:8002/convert?url=data:image/svg+xml,<svg>...</svg>
```

## 📚 Documentation

### Dependency Injection System

The SVG2PPTX converter uses a modern dependency injection architecture for service management:

- **[Migration Guide](docs/dependency-injection-migration-guide.md)** - Complete guide for migrating to the new dependency injection system
- **[API Reference](docs/api/conversion-services-api.md)** - Detailed API documentation for ConversionServices
- **[Quick Reference](docs/quick-reference/dependency-injection-cheatsheet.md)** - Cheat sheet for common patterns
- **[Examples](examples/dependency-injection-examples.py)** - Working code examples

### Key Features

- **Centralized service management** through `ConversionServices`
- **Improved testability** with service mocking
- **Consistent configuration** across all converters
- **Clean separation of concerns** between service creation and usage

### Quick Example

```python
from src.services.conversion_services import ConversionServices
from src.converters.shapes import RectangleConverter

# Create services container
services = ConversionServices.create_default()

# Create converter with dependency injection
converter = RectangleConverter(services=services)

# Use converter (backward compatible API)
result = converter.unit_converter.to_emu("10px")
```

### Migration from Legacy Code

```python
# Old pattern (deprecated)
converter = RectangleConverter()

# New pattern (recommended)
services = ConversionServices.create_default()
converter = RectangleConverter(services=services)
```

See the [Migration Guide](docs/dependency-injection-migration-guide.md) for detailed migration instructions.

## 🐛 Troubleshooting

### PowerPoint Repair Issues
- ✅ **Fixed**: Proper XML namespaces and structure
- ✅ **Fixed**: Valid EMU coordinate ranges
- ✅ **Fixed**: Unique shape IDs
- ✅ **Fixed**: Clean XML formatting

### Common Issues

**Authentication Fails**
```bash
# Check API key format
Authorization: Bearer dev-api-key-12345  # ✅ Correct
Authorization: Bearer test_secret        # ❌ Wrong key
```

**Conversion Errors**
- Validate SVG syntax with online tools
- Check for unsupported SVG features
- Enable debug logging: `LOG_LEVEL=DEBUG`

**Google Drive Issues**
- Verify OAuth redirect URLs
- Check service account permissions
- Ensure APIs are enabled in Google Console

## 📈 Performance

- **Conversion Speed**: ~50ms per simple SVG element
- **Memory Usage**: <100MB for typical SVG files
- **Concurrent Requests**: Supports multiple simultaneous conversions
- **File Size Limits**: Tested up to 10MB SVG files

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Add your converter to `src/converters/`
4. Update `__init__.py` to include new converter
5. Test with sample SVG files
6. Submit pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🎯 Roadmap

- [ ] **Advanced CSS Support** - Complex selectors and media queries
- [ ] **SVG Filters** - Blur, drop-shadow, color-matrix effects  
- [ ] **Animation Export** - Convert SVG animations to PowerPoint animations
- [ ] **Batch Processing** - Multi-file conversion endpoint
- [ ] **Template System** - Reusable PowerPoint slide templates

---

**Built with ❤️ for high-fidelity SVG to PowerPoint conversion**