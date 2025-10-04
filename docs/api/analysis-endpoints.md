# SVG Analysis & Validation API Endpoints

Comprehensive guide for using svg2pptx analysis, validation, and feature discovery endpoints.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [POST /analyze/svg](#post-analyzesvg)
  - [POST /analyze/validate](#post-analyzevalidate)
  - [GET /analyze/features/supported](#get-analyzefeaturessupported)
- [Response Models](#response-models)
- [Error Handling](#error-handling)
- [curl Examples](#curl-examples)
- [Integration Examples](#integration-examples)
- [Best Practices](#best-practices)

---

## Overview

The analysis endpoints provide pre-flight checking capabilities for SVG files before conversion:

- **Complexity Analysis**: Get complexity scores, feature detection, and policy recommendations
- **Validation**: Check SVG for errors, compatibility issues, and get actionable suggestions
- **Feature Discovery**: Query supported SVG features and capabilities

### Recent Improvements (2025-10-04)

The analysis endpoints have been significantly refactored for better performance and maintainability:

- **50%+ Performance Improvement**: Single-pass element collection reduces validator execution time
- **Dependency Injection with Caching**: Singleton analyzer/validator instances eliminate re-initialization overhead
- **External Feature Registry**: Feature support data moved to JSON for easier updates without code changes
- **Enhanced Type Safety**: Complete type hints with Literal types for better IDE support and validation
- **Complete SVG Color Support**: All 148 SVG named colors now recognized (147 standard + 'transparent')
- **Improved Filter Detection**: All 17 SVG filter primitives correctly mapped and detected
- **Better Error Handling**: Specific exception types with debug logging instead of silent swallowing

### Use Cases

1. **Figma Plugin Integration**: Validate and analyze Figma exports before conversion
2. **Batch Processing**: Pre-screen SVG files for conversion suitability
3. **Quality Assurance**: Detect issues before conversion
4. **Policy Selection**: Get data-driven recommendations for conversion settings

---

## Authentication

All analysis endpoints require API key authentication:

```bash
Authorization: Bearer YOUR_API_KEY
```

Get your API key from the dashboard or contact support.

---

## Endpoints

### POST /analyze/svg

Analyze SVG complexity and get policy recommendations.

**Request:**

```http
POST /analyze/svg HTTP/1.1
Host: your-api-domain.com
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "svg_content": "<svg>...</svg>",
  "analyze_depth": "detailed"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `svg_content` | string | Yes* | SVG XML content |
| `svg_url` | string | Yes* | URL to SVG file (alternative to content) |
| `analyze_depth` | string | No | Analysis depth: `basic`, `detailed`, `comprehensive` (default: `detailed`) |

*One of `svg_content` or `svg_url` is required. You can also upload a file using `multipart/form-data` with the `svg_file` field.

**Response:**

```json
{
  "complexity_score": 45,
  "element_counts": {
    "total_elements": 127,
    "shapes": 23,
    "paths": 45,
    "text": 12,
    "groups": 18,
    "gradients": 3,
    "filters": 2,
    "images": 1,
    "max_nesting_depth": 4
  },
  "features_detected": {
    "has_animations": false,
    "has_clipping": true,
    "has_patterns": false,
    "has_gradients": true,
    "has_filters": true,
    "gradient_types": ["linear", "radial"],
    "filter_types": ["blur", "dropshadow"],
    "has_complex_paths": true,
    "has_complex_transforms": false,
    "has_embedded_images": true
  },
  "recommended_policy": {
    "target": "balanced",
    "confidence": 0.85,
    "reasons": [
      "Moderate complexity (score: 45)",
      "127 elements with some complexity",
      "3 gradients detected",
      "2 filters may need native rendering"
    ]
  },
  "estimated_performance": {
    "conversion_time_ms": 450,
    "output_size_kb": 284,
    "memory_usage_mb": 52
  },
  "warnings": [
    "SVG contains 2 filters that may need EMF fallback"
  ]
}
```

**Status Codes:**

- `200 OK`: Analysis successful
- `400 Bad Request`: Invalid SVG or parameters
- `413 Payload Too Large`: SVG exceeds 10MB limit
- `500 Internal Server Error`: Analysis failed

---

### POST /analyze/validate

Validate SVG content and check compatibility.

**Request:**

```http
POST /analyze/validate HTTP/1.1
Host: your-api-domain.com
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json

{
  "svg_content": "<svg>...</svg>",
  "strict_mode": false
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `svg_content` | string | Yes* | SVG XML content |
| `strict_mode` | boolean | No | Enable strict validation (warnings → errors) (default: `false`) |

*Alternatively, upload a file using `multipart/form-data` with the `svg_file` field.

**Response (Valid SVG):**

```json
{
  "valid": true,
  "version": "1.1",
  "errors": [],
  "warnings": [
    {
      "code": "MISSING_VIEWBOX",
      "message": "SVG lacks viewBox attribute",
      "severity": "warning",
      "element": "svg",
      "suggestion": "Add viewBox for proper scaling (e.g., viewBox='0 0 100 100')"
    },
    {
      "code": "COMPLEX_FILTER",
      "message": "Filter 'blur-shadow' has 6 primitives",
      "severity": "warning",
      "element": "filter",
      "suggestion": "Complex filters may be rasterized - consider 'quality' policy"
    }
  ],
  "compatibility": {
    "powerpoint_2016": "full",
    "powerpoint_2019": "full",
    "powerpoint_365": "full",
    "google_slides": "partial",
    "notes": [
      "2 filters may require EMF fallback"
    ]
  },
  "suggestions": [
    "Use 'quality' policy for better filter rendering"
  ]
}
```

**Response (Invalid SVG):**

```json
{
  "valid": false,
  "version": null,
  "errors": [
    {
      "code": "XML_PARSE_ERROR",
      "message": "Invalid XML: Opening and ending tag mismatch: rect line 3 and svg, line 5",
      "severity": "error",
      "line": 5,
      "suggestion": "Ensure SVG is valid XML with proper closing tags"
    }
  ],
  "warnings": [],
  "compatibility": null,
  "suggestions": []
}
```

**Status Codes:**

- `200 OK`: SVG is valid (even if it has warnings)
- `400 Bad Request`: SVG is invalid (has errors) or malformed request
- `413 Payload Too Large`: SVG exceeds 10MB limit
- `500 Internal Server Error`: Validation failed

**Compatibility Levels:**

- `full`: Fully supported with native PowerPoint rendering
- `partial`: Supported with some limitations
- `limited`: Limited support (may use EMF/raster fallback)
- `none`: Not supported

**Validation Severity:**

- `error`: Prevents conversion (XML errors, invalid structure)
- `warning`: May impact quality but conversion possible
- `info`: Informational only

---

### GET /analyze/features/supported

Get supported SVG features and capabilities.

**Request:**

```http
GET /analyze/features/supported HTTP/1.1
Host: your-api-domain.com
Authorization: Bearer YOUR_API_KEY
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category` | string | No | Filter by category (see available categories below) |

**Available Categories:**

- `basic_shapes`
- `paths`
- `text`
- `gradients`
- `filters`
- `transformations`
- `clipping_masking`
- `patterns`
- `markers`
- `animations`

**Response (All Features):**

```json
{
  "version": "1.0.0",
  "last_updated": "2025-10-04",
  "categories": {
    "basic_shapes": {
      "support_level": "full",
      "elements": ["rect", "circle", "ellipse", "line", "polyline", "polygon"],
      "notes": "All basic shapes fully supported with native PowerPoint rendering"
    },
    "gradients": {
      "support_level": "full",
      "types": {
        "linear": "full",
        "radial": "full",
        "mesh": "partial"
      },
      "limitations": {
        "mesh": "max 400 patches, may use EMF for complex meshes",
        "stops": "recommend ≤10 stops for best compatibility"
      },
      "notes": "Linear and radial gradients fully supported. Mesh gradients supported with patch count limitations."
    },
    "filters": {
      "support_level": "partial",
      "native_support": [
        "feGaussianBlur",
        "feDropShadow",
        "feOffset",
        "feFlood",
        "feBlend",
        "feColorMatrix"
      ],
      "emf_fallback": [
        "feDisplacementMap",
        "feTurbulence",
        "feConvolveMatrix",
        "feDiffuseLighting",
        "feSpecularLighting"
      ],
      "notes": "Common filters have native support. Complex filters use EMF vector fallback."
    }
  },
  "policy_capabilities": {
    "speed": {
      "description": "Fast conversion with basic feature support",
      "features": ["basic shapes", "simple paths", "basic text", "simple gradients"],
      "limitations": ["filters may be simplified", "complex features disabled"]
    },
    "balanced": {
      "description": "Balanced quality and performance",
      "features": ["all shapes", "all paths", "text with formatting", "gradients", "basic filters"],
      "limitations": ["some filter effects simplified", "complex meshes may use EMF"]
    },
    "quality": {
      "description": "Maximum fidelity conversion",
      "features": ["all elements", "all filters", "mesh gradients", "complex transforms"],
      "limitations": ["slower conversion", "larger file sizes"]
    }
  },
  "color_spaces": {
    "support_level": "full",
    "supported": ["sRGB", "linearRGB", "display-p3", "adobe-rgb-1998"],
    "notes": "ICC profile support with LAB color conversion for brand accuracy"
  }
}
```

**Response (Specific Category):**

```http
GET /analyze/features/supported?category=filters
```

```json
{
  "version": "1.0.0",
  "category": "filters",
  "details": {
    "support_level": "partial",
    "native_support": [
      "feGaussianBlur",
      "feDropShadow",
      "feOffset",
      "feFlood",
      "feBlend",
      "feColorMatrix"
    ],
    "emf_fallback": [
      "feDisplacementMap",
      "feTurbulence",
      "feConvolveMatrix",
      "feDiffuseLighting",
      "feSpecularLighting"
    ],
    "notes": "Common filters have native support. Complex filters use EMF vector fallback."
  }
}
```

**Status Codes:**

- `200 OK`: Features retrieved successfully
- `404 Not Found`: Invalid category
- `500 Internal Server Error`: Failed to retrieve features

---

## Response Models

### AnalysisResult

```typescript
{
  complexity_score: number;        // 0-100
  element_counts: ElementCounts;
  features_detected: FeatureSet;
  recommended_policy: PolicyRecommendation;
  estimated_performance: PerformanceEstimate;
  warnings: string[];
}
```

### ValidationResult

```typescript
{
  valid: boolean;
  version: string | null;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
  compatibility: CompatibilityReport | null;
  suggestions: string[];
}
```

### ValidationIssue

```typescript
{
  code: string;
  message: string;
  severity: "error" | "warning" | "info";
  element: string | null;
  line: number | null;
  suggestion: string | null;
}
```

---

## Error Handling

All endpoints follow consistent error response format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Error Codes

| HTTP Code | Meaning | Solution |
|-----------|---------|----------|
| 400 | Bad Request | Check request parameters and SVG validity |
| 401 | Unauthorized | Provide valid API key |
| 413 | Payload Too Large | SVG exceeds 10MB limit - reduce size |
| 429 | Rate Limit Exceeded | Wait before making more requests |
| 500 | Internal Server Error | Contact support if persistent |

---

## curl Examples

### Analyze SVG

```bash
curl -X POST "https://your-api-domain.com/analyze/svg" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "svg_content": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 100 100\"><rect x=\"10\" y=\"10\" width=\"80\" height=\"80\" fill=\"blue\" /></svg>",
    "analyze_depth": "detailed"
  }'
```

### Analyze SVG from File

```bash
curl -X POST "https://your-api-domain.com/analyze/svg" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F "svg_file=@path/to/your/file.svg"
```

### Validate SVG

```bash
curl -X POST "https://your-api-domain.com/analyze/validate" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "svg_content": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 100 100\"><rect x=\"10\" y=\"10\" width=\"80\" height=\"80\" fill=\"blue\" /></svg>",
    "strict_mode": false
  }'
```

### Validate SVG (Strict Mode)

```bash
curl -X POST "https://your-api-domain.com/analyze/validate" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "svg_content": "<svg>...</svg>",
    "strict_mode": true
  }'
```

### Get Supported Features (All)

```bash
curl -X GET "https://your-api-domain.com/analyze/features/supported" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Get Supported Features (Specific Category)

```bash
curl -X GET "https://your-api-domain.com/analyze/features/supported?category=filters" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

---

## Integration Examples

### Python

See [`examples/api/analyze_svg.py`](../../examples/api/analyze_svg.py) for comprehensive Python examples.

**Quick Example:**

```python
import requests

API_BASE_URL = "https://your-api-domain.com"
API_KEY = "your-api-key"

# Analyze SVG
response = requests.post(
    f"{API_BASE_URL}/analyze/svg",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={"svg_content": "<svg>...</svg>"}
)

result = response.json()
print(f"Complexity: {result['complexity_score']}/100")
print(f"Recommended Policy: {result['recommended_policy']['target']}")
```

### JavaScript/Node.js

See [`examples/api/analyze_svg.js`](../../examples/api/analyze_svg.js) for Node.js examples.

**Quick Example:**

```javascript
const response = await fetch('https://your-api-domain.com/analyze/svg', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${API_KEY}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ svg_content: '<svg>...</svg>' }),
});

const result = await response.json();
console.log(`Complexity: ${result.complexity_score}/100`);
```

### Figma Plugin

See [`examples/api/figma_integration_example.js`](../../examples/api/figma_integration_example.js) for complete Figma plugin integration.

---

## Best Practices

### 1. Always Validate Before Conversion

```python
# Bad: Convert without validation
pptx = convert_svg(svg_content)

# Good: Validate first
validation = validate_svg(svg_content)
if validation['valid']:
    pptx = convert_svg(svg_content)
else:
    handle_errors(validation['errors'])
```

### 2. Use Auto-Detected Policy Recommendations

```python
# Analyze and get recommendation
analysis = analyze_svg(svg_content)
recommended_policy = analysis['recommended_policy']['target']

# Use recommended policy
convert_svg(svg_content, target=recommended_policy)
```

### 3. Handle Warnings Appropriately

```python
validation = validate_svg(svg_content)

# Log warnings but don't block
if validation['warnings']:
    for warning in validation['warnings']:
        logger.warning(f"{warning['code']}: {warning['message']}")

# Only block on errors
if not validation['valid']:
    raise ValueError("SVG validation failed")
```

### 4. Cache Feature Support Data

```python
# Cache feature data (changes infrequently)
features = cache.get('svg2pptx_features')
if not features:
    features = get_supported_features()
    cache.set('svg2pptx_features', features, ttl=3600)
```

### 5. Respect Rate Limits

```python
# Use exponential backoff for rate limiting
@retry(tries=3, delay=1, backoff=2)
def analyze_with_retry(svg_content):
    return analyze_svg(svg_content)
```

### 6. Complete Workflow Example

```python
def convert_svg_safely(svg_content):
    """Complete pre-flight check workflow."""

    # 1. Validate
    validation = validate_svg(svg_content)
    if not validation['valid']:
        return {'error': 'Invalid SVG', 'issues': validation['errors']}

    # 2. Analyze
    analysis = analyze_svg(svg_content)

    # 3. Get recommendation
    policy = analysis['recommended_policy']['target']
    complexity = analysis['complexity_score']

    # 4. Warn if high complexity
    if complexity > 70:
        logger.warning(f"High complexity SVG ({complexity}/100) - conversion may be slow")

    # 5. Convert with recommended policy
    pptx = convert_svg(svg_content, target=policy)

    return {
        'success': True,
        'policy_used': policy,
        'complexity': complexity,
        'warnings': analysis['warnings']
    }
```

---

## Rate Limits

- **Default:** 100 requests per minute per API key
- **Burst:** 10 requests per second
- **Headers:**
  - `X-RateLimit-Limit`: Maximum requests per minute
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `X-RateLimit-Reset`: Unix timestamp when limit resets

---

## Support

- **Documentation:** https://docs.svg2pptx.com
- **Issues:** https://github.com/your-org/svg2pptx/issues
- **Email:** support@svg2pptx.com
