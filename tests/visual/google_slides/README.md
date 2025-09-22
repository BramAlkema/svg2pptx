# Google Slides Visual Testing

Automated visual testing system for SVG to PPTX conversion using Google Slides as a rendering engine for cross-platform verification.

## Overview

This system provides:

1. **SVG to PPTX Conversion** - Uses the main SVG2PPTX library
2. **Google Slides Conversion** - Uploads PPTX and converts to Google Slides
3. **Publication** - Makes presentations publicly viewable
4. **Screenshot Capture** - Takes high-quality screenshots of all slides
5. **Visual Validation** - Compares screenshots against reference images

## Setup

### 1. Google Cloud Setup

1. Create a Google Cloud Project
2. Enable the Google Drive API and Google Slides API
3. Create service account credentials or OAuth2 credentials
4. Download the credentials JSON file

### 2. Credentials Configuration

Place your credentials file at:
```
~/.config/svg2pptx/google_credentials.json
```

Or specify a custom path in the configuration.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

For Playwright browser automation:
```bash
playwright install chromium
```

## Quick Start

### Basic Usage

```python
import asyncio
from pathlib import Path
from test_runner import GoogleSlidesTestRunner, TestConfig

async def run_visual_test():
    # Configure
    config = TestConfig(
        auth_method='service_account',
        credentials_path='~/.config/svg2pptx/google_credentials.json',
        validation_tolerance=0.95
    )

    # Initialize runner
    runner = GoogleSlidesTestRunner(config)
    await runner.initialize()

    # Run test
    svg_path = Path("my_test.svg")
    result = await runner.run_test(svg_path, "test_name")

    if result.success:
        print(f"✅ Test passed! URL: {result.public_url}")
    else:
        print(f"❌ Test failed: {result.error_message}")

    await runner.cleanup()

# Run the test
asyncio.run(run_visual_test())
```

### Batch Testing

```python
async def run_batch_tests():
    config = TestConfig(
        auth_method='service_account',
        credentials_path='~/.config/svg2pptx/google_credentials.json'
    )

    runner = GoogleSlidesTestRunner(config)
    await runner.initialize()

    # Test multiple SVG files
    svg_files = [Path("test1.svg"), Path("test2.svg")]
    results = await runner.run_batch_tests(svg_files)

    successful = sum(1 for r in results if r.success)
    print(f"Results: {successful}/{len(results)} tests passed")

    await runner.cleanup()
```

## Configuration

### Configuration File

Create `config.yaml`:

```yaml
google_slides:
  auth:
    method: service_account
    credentials_path: ~/.config/svg2pptx/google_credentials.json

  screenshot:
    format: png
    method: hybrid  # api, playwright, hybrid
    size: large

  validation:
    tolerance: 0.95
    generate_diffs: true

  output:
    screenshots_dir: tests/visual/screenshots
    references_dir: tests/visual/references
    reports_dir: tests/visual/reports
```

### TestConfig Options

```python
config = TestConfig(
    # Authentication
    auth_method='service_account',  # or 'oauth2'
    credentials_path='path/to/credentials.json',

    # Screenshot settings
    screenshot_format='png',  # png, jpeg, webp
    screenshot_method='hybrid',  # api, playwright, hybrid

    # Validation
    validation_tolerance=0.95,  # 0.0-1.0
    generate_diffs=True,

    # Cleanup
    cleanup_after_test=True
)
```

## Components

### 1. GoogleSlidesAuthenticator

Handles authentication with Google APIs.

```python
from authenticator import GoogleSlidesAuthenticator, AuthConfig

# Service Account
auth = GoogleSlidesAuthenticator('service_account')
auth.configure(AuthConfig(
    method='service_account',
    credentials_path='path/to/service_account.json'
))

success = auth.authenticate()
```

### 2. SlidesConverter

Converts PPTX files to Google Slides.

```python
from slides_converter import SlidesConverter

converter = SlidesConverter(authenticated_auth)

# Full workflow
result = converter.convert_pptx_full_workflow(
    pptx_path=Path("presentation.pptx"),
    custom_name="My Test Presentation"
)

print(f"Presentation ID: {result.presentation_id}")
print(f"URL: {result.presentation_url}")
```

### 3. SlidesPublisher

Publishes presentations for public viewing.

```python
from publisher import SlidesPublisher, AccessLevel

publisher = SlidesPublisher(authenticated_auth)

published = publisher.publish_presentation(
    presentation_id="your_presentation_id",
    access_level=AccessLevel.ANYONE_WITH_LINK
)

print(f"Public URL: {published.public_url}")
print(f"Embed URL: {published.embed_url}")
```

### 4. SlidesScreenshotCapture

Captures screenshots of slides.

```python
from screenshot_capture import SlidesScreenshotCapture, CaptureMethod

capture = SlidesScreenshotCapture(authenticated_auth)

# Capture all slides
screenshots = await capture.capture_all_slides(
    presentation_id="your_presentation_id",
    output_dir=Path("screenshots"),
    method=CaptureMethod.HYBRID
)

for screenshot in screenshots:
    if screenshot.success:
        print(f"Screenshot: {screenshot.output_path}")
```

### 5. VisualValidator

Compares screenshots with reference images.

```python
from visual_validator import VisualValidator

validator = VisualValidator(tolerance=0.95)

# Compare single image pair
result = validator.validate_image_pair(
    reference_path=Path("reference.png"),
    test_path=Path("screenshot.png")
)

print(f"Similarity: {result.similarity_score:.3f}")
print(f"Passes threshold: {result.meets_threshold}")

# Validate entire presentation
report = validator.validate_presentation(
    reference_images=[Path("ref1.png"), Path("ref2.png")],
    test_images=[Path("test1.png"), Path("test2.png")]
)

print(f"Overall: {report.threshold_passed}/{report.total_comparisons} passed")
```

## Screenshot Methods

### API Method
- Uses Google Slides thumbnail API
- Fast and reliable
- Lower resolution
- Good for basic validation

### Playwright Method
- Uses browser automation
- High resolution and quality
- Slower
- Better for detailed validation

### Hybrid Method (Recommended)
- Tries API first, falls back to Playwright
- Best balance of speed and quality
- Recommended for most use cases

## Testing

### Unit Tests

```bash
# Run unit tests
pytest tests/visual/google_slides/test_integration.py::TestGoogleSlidesAuthenticator -v
pytest tests/visual/google_slides/test_integration.py::TestVisualValidator -v
```

### Integration Tests

```bash
# Set up credentials
export GOOGLE_SLIDES_TEST_CREDENTIALS=~/.config/svg2pptx/google_credentials.json

# Run integration tests
pytest tests/visual/google_slides/test_integration.py -m integration -v
```

### Performance Tests

```bash
# Run performance tests (requires credentials)
pytest tests/visual/google_slides/test_integration.py -m performance -v
```

## CI/CD Integration

### GitHub Actions

The included workflow file `.github/workflows/visual-tests.yml` provides:

- Automated testing on push/PR
- Multiple Python versions
- Artifact upload for test results
- PR comments with test summaries

### Environment Variables

Set these secrets in your repository:

- `GOOGLE_SERVICE_ACCOUNT_KEY`: Your service account JSON key content

## Troubleshooting

### Authentication Issues

```python
# Test authentication
auth = GoogleSlidesAuthenticator('service_account')
auth.authenticate('path/to/credentials.json')

test_result = auth.test_authentication()
print(test_result)
```

### Permission Errors

Ensure your service account has:
- Google Drive API access
- Google Slides API access
- Ability to create/delete files

### Screenshot Failures

1. Check if presentation is publicly accessible
2. Try different screenshot methods
3. Increase wait times for page loading

### Validation Failures

1. Check similarity threshold (try lowering)
2. Verify reference images exist
3. Check image dimensions match

## Best Practices

1. **Create Reference Baselines**: Always create reference images before validation
2. **Use Hybrid Screenshots**: Best balance of speed and quality
3. **Cleanup After Tests**: Enable cleanup to avoid quota issues
4. **Monitor API Usage**: Google APIs have rate limits
5. **Organize Test Data**: Use clear naming for test files and results

## Example Files

- `example_usage.py` - Complete usage examples
- `config.yaml` - Configuration template
- `test_integration.py` - Test suite

## Support

For issues and questions:

1. Check the logs in `tests/visual/logs/`
2. Review test reports in `tests/visual/reports/`
3. Verify Google Cloud setup and permissions
4. Check example usage in `example_usage.py`