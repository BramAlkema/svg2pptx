# Systematic Pipeline Flow Verification Methodology

## Overview
This document provides a systematic approach to verify which elements, converters, and filters actually use the production pipeline vs isolated/unused components.

## Verification Methods

### Method 1: Static Code Analysis (Entry Point Tracing)

#### Step 1: Identify Main Entry Points
```python
# Start from known entry points
ENTRY_POINTS = [
    'core/pipeline/converter.py:CleanSlateConverter',
    'api/main.py:convert_svg_to_pptx',
    'src/svg2pptx.py:main',
]
```

#### Step 2: Trace Forward Dependencies
```bash
# Find all direct imports and instantiations
grep -r "from.*import.*Converter" core/pipeline/
grep -r "from.*import.*Mapper" core/pipeline/
grep -r "from.*import.*Filter" core/pipeline/
grep -r "from.*import.*Service" core/pipeline/

# Check what CleanSlateConverter actually uses
grep -n "self\." core/pipeline/converter.py
grep -n "import" core/pipeline/converter.py
```

#### Step 3: Map Initialization Chain
```python
# Trace initialization in CleanSlateConverter._initialize_components()
_initialize_components() → {
    'mappers': {
        'path': PathMapper,      # CHECK: Used?
        'textframe': TextMapper,  # CHECK: Used?
        'group': GroupMapper,     # CHECK: Used?
        'image': ImageMapper,     # CHECK: Used?
    },
    'services': ConversionServices,
    'policy': PolicyEngine,
}
```

### Method 2: Runtime Instrumentation (Execution Tracing)

#### Step 1: Add Logging to Base Classes
```python
# core/converters/base.py
class BaseConverter:
    def convert(self, element):
        logger.info(f"PIPELINE_TRACE: {self.__class__.__name__}.convert() called")
        # ... existing code

# core/map/mapper.py
class Mapper:
    def map(self, ir_element):
        logger.info(f"PIPELINE_TRACE: {self.__class__.__name__}.map() called")
        # ... existing code

# core/filters/base.py
class FilterProcessor:
    def apply(self, element):
        logger.info(f"PIPELINE_TRACE: {self.__class__.__name__}.apply() called")
        # ... existing code
```

#### Step 2: Create Test SVG with All Elements
```xml
<svg xmlns="http://www.w3.org/2000/svg">
    <!-- Basic shapes -->
    <rect id="test-rect"/>
    <circle id="test-circle"/>
    <ellipse id="test-ellipse"/>
    <path id="test-path" d="M10,10 L20,20"/>
    <line id="test-line"/>
    <polyline id="test-polyline"/>
    <polygon id="test-polygon"/>

    <!-- Text elements -->
    <text id="test-text">Hello</text>
    <text id="test-textpath">
        <textPath href="#test-path">Text on path</textPath>
    </text>

    <!-- Groups and structure -->
    <g id="test-group">
        <rect/>
    </g>
    <defs id="test-defs">
        <linearGradient id="grad1"/>
        <pattern id="pattern1"/>
        <clipPath id="clip1"/>
        <mask id="mask1"/>
        <filter id="filter1">
            <feGaussianBlur/>
            <feOffset/>
        </filter>
    </defs>

    <!-- Advanced elements -->
    <image id="test-image"/>
    <switch id="test-switch"/>
    <marker id="test-marker"/>
    <symbol id="test-symbol"/>
    <use href="#test-symbol"/>
    <foreignObject id="test-foreign"/>

    <!-- Animations -->
    <rect>
        <animate attributeName="x" from="0" to="100"/>
    </rect>
</svg>
```

#### Step 3: Run and Collect Traces
```python
# trace_pipeline.py
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.FileHandler('pipeline_trace.log'),
        logging.StreamHandler()
    ]
)

from core.pipeline.converter import CleanSlateConverter
converter = CleanSlateConverter()
result = converter.convert(test_svg_content)

# Analyze log for PIPELINE_TRACE entries
```

### Method 3: Dependency Graph Analysis

#### Step 1: Build Import Graph
```python
# analyze_imports.py
import ast
import os
from pathlib import Path

def analyze_imports(file_path):
    """Extract all imports from a Python file"""
    with open(file_path) as f:
        tree = ast.parse(f.read())

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                imports.append(f"{module}.{alias.name}")
    return imports

def build_dependency_graph(root_dir):
    """Build complete dependency graph"""
    graph = {}
    for py_file in Path(root_dir).rglob('*.py'):
        imports = analyze_imports(py_file)
        graph[str(py_file)] = imports
    return graph

# Generate graph
graph = build_dependency_graph('core/')
```

#### Step 2: Find Reachable Components
```python
def find_reachable_from(graph, start_points):
    """Find all components reachable from entry points"""
    visited = set()
    queue = list(start_points)

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        # Add dependencies to queue
        if current in graph:
            queue.extend(graph[current])

    return visited

# Find what's actually used
reachable = find_reachable_from(graph, [
    'core/pipeline/converter.py',
    'api/main.py'
])

# Find orphaned components
all_files = set(graph.keys())
orphaned = all_files - reachable
```

### Method 4: Test Coverage Analysis

#### Step 1: Run Coverage with Specific Entry Points
```bash
# Test only through main pipeline
PYTHONPATH=. pytest tests/e2e/test_clean_slate_e2e.py \
    --cov=core \
    --cov-report=html \
    --cov-report=term-missing

# Check which files have 0% coverage - likely unused
```

#### Step 2: Analyze Coverage Gaps
```python
# coverage_analyzer.py
import json
from coverage import Coverage

cov = Coverage()
cov.load()

# Get files with no coverage
uncovered = []
for filename in cov.get_data().measured_files():
    stats = cov.analysis2(filename)
    if stats[3] == 0:  # 0% coverage
        uncovered.append(filename)

print("Files never executed:")
for f in uncovered:
    print(f"  - {f}")
```

### Method 5: Integration Point Analysis

#### Step 1: Check Mapper Registration
```python
# Where are mappers registered?
# core/pipeline/converter.py:_initialize_components()
self.mappers = {
    'path': PathMapper(self.policy),
    'textframe': TextMapper(self.policy),  # <- NOT SmartFontConverter!
    'group': GroupMapper(self.policy),
    'image': ImageMapper(self.policy),
}
```

#### Step 2: Check Filter Registration
```python
# core/filters/factory.py
class FilterFactory:
    def __init__(self):
        self.processors = {
            'feGaussianBlur': GaussianBlurProcessor,
            'feOffset': OffsetProcessor,
            # ... check all registered
        }
```

#### Step 3: Check Service Wiring
```python
# core/services/conversion_services.py
@classmethod
def create_default(cls):
    return cls(
        unit_converter=UnitConverter(),
        viewport_handler=ViewportHandler(),
        font_service=FontService(),  # <- Does TextMapper use this?
        # ... check what's wired
    )
```

### Method 6: Call Stack Analysis

#### Step 1: Add Stack Traces
```python
# trace_calls.py
import sys
import traceback

class CallTracer:
    def __init__(self):
        self.call_stacks = {}

    def trace(self, frame, event, arg):
        if event == 'call':
            stack = traceback.extract_stack(frame)
            func_name = frame.f_code.co_name
            class_name = frame.f_locals.get('self', None).__class__.__name__ if 'self' in frame.f_locals else ''
            full_name = f"{class_name}.{func_name}" if class_name else func_name

            if full_name not in self.call_stacks:
                self.call_stacks[full_name] = []
            self.call_stacks[full_name].append(stack)

        return self.trace

# Use tracer
tracer = CallTracer()
sys.settrace(tracer.trace)
# Run conversion
sys.settrace(None)

# Analyze which components were called
```

## Verification Checklist

### For Each Component, Verify:

#### 1. Static Integration
- [ ] Imported by pipeline modules?
- [ ] Instantiated in _initialize_components()?
- [ ] Registered in appropriate factory/registry?
- [ ] Wired through ConversionServices?

#### 2. Runtime Execution
- [ ] Shows up in execution traces?
- [ ] Has non-zero test coverage?
- [ ] Appears in call stacks during conversion?
- [ ] Logs indicate it's processing elements?

#### 3. Data Flow
- [ ] Receives input from previous stage?
- [ ] Produces output consumed by next stage?
- [ ] Errors if removed from pipeline?
- [ ] Test fails if mocked incorrectly?

#### 4. Configuration
- [ ] Configurable through pipeline config?
- [ ] Policy engine makes decisions about it?
- [ ] Has fallback behavior defined?

## Automated Verification Script

```python
#!/usr/bin/env python3
# verify_pipeline_integration.py

import logging
import sys
from pathlib import Path
from typing import Dict, Set, List

class PipelineVerifier:
    def __init__(self, project_root: Path):
        self.root = project_root
        self.results = {
            'integrated': [],
            'isolated': [],
            'partial': [],
            'unknown': []
        }

    def verify_static_integration(self, component: str) -> bool:
        """Check if component is imported by pipeline"""
        pipeline_file = self.root / 'core/pipeline/converter.py'
        content = pipeline_file.read_text()
        return component in content

    def verify_runtime_execution(self, component: str) -> bool:
        """Check if component has test coverage"""
        # Run coverage and check
        # ...
        pass

    def verify_data_flow(self, component: str) -> bool:
        """Check if component participates in data flow"""
        # Analyze inputs/outputs
        # ...
        pass

    def categorize_component(self, component: str):
        """Categorize component integration status"""
        static = self.verify_static_integration(component)
        runtime = self.verify_runtime_execution(component)
        dataflow = self.verify_data_flow(component)

        if all([static, runtime, dataflow]):
            self.results['integrated'].append(component)
        elif any([static, runtime, dataflow]):
            self.results['partial'].append(component)
        elif not any([static, runtime, dataflow]):
            self.results['isolated'].append(component)
        else:
            self.results['unknown'].append(component)

    def generate_report(self):
        """Generate verification report"""
        print("Pipeline Integration Verification Report")
        print("=" * 50)

        for category, components in self.results.items():
            print(f"\n{category.upper()} ({len(components)} components)")
            for comp in components:
                print(f"  - {comp}")

if __name__ == "__main__":
    verifier = PipelineVerifier(Path.cwd())

    # List all components to verify
    components = [
        'PathMapper', 'TextMapper', 'GroupMapper', 'ImageMapper',
        'SmartFontConverter', 'WordArtHandler', 'SystemFontHandler',
        'GaussianBlurProcessor', 'OffsetProcessor', 'BlendProcessor',
        # ... add all components
    ]

    for component in components:
        verifier.categorize_component(component)

    verifier.generate_report()
```

## Red Flags Indicating Isolation

1. **No imports from core/pipeline/**
2. **Only imported by test files**
3. **0% coverage in E2E tests**
4. **No registration in factories/registries**
5. **Missing from ConversionServices**
6. **No policy decisions about it**
7. **No error when deleted**
8. **Different API than integrated components**

## Green Flags Indicating Integration

1. **Imported by CleanSlateConverter**
2. **Instantiated in _initialize_components()**
3. **Registered in appropriate factory**
4. **Wired through services**
5. **Non-zero E2E test coverage**
6. **Appears in production logs**
7. **Policy engine knows about it**
8. **Breaking it breaks conversions**

## Quick Verification Commands

```bash
# Check what CleanSlateConverter uses
grep -n "import\|from" core/pipeline/converter.py

# Check what's registered in mappers
grep -n "self.mappers\[" core/pipeline/converter.py

# Check filter registration
grep -n "register\|processors\[" core/filters/

# Find unused imports
vulture core/ --min-confidence 100

# Find orphaned files
find core/ -name "*.py" | xargs -I {} sh -c 'grep -r $(basename {} .py) core/ --include="*.py" | grep -v "{}" | wc -l'

# Check coverage for specific module
PYTHONPATH=. pytest tests/e2e/ --cov=core.converters.font --cov-report=term-missing
```

This methodology provides multiple approaches to systematically verify which components are actually integrated into the production pipeline.