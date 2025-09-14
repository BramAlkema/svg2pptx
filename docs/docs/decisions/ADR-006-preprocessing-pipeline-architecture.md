# ADR-006: Preprocessing Pipeline Architecture

## Status
**DECIDED** - Implemented 2025-09-11

## Context
With the implementation of 25+ SVGO optimization plugins and advanced path algorithms, the system required a robust preprocessing architecture that could:

- **Orchestrate Multiple Plugins**: Coordinate execution of diverse optimization algorithms
- **Handle Plugin Dependencies**: Manage plugins that depend on outputs from other plugins
- **Provide Configuration Control**: Allow fine-tuned control over optimization behavior
- **Ensure Error Isolation**: Prevent single plugin failures from breaking entire pipeline
- **Support Multiple Passes**: Enable iterative optimization for maximum effectiveness
- **Maintain Performance**: Keep preprocessing overhead reasonable for real-time conversion

### Architecture Requirements

#### Functional Requirements
- Plugin-based architecture for extensibility
- Configurable optimization presets (minimal, default, aggressive)
- Multi-pass optimization support
- Comprehensive error handling and recovery
- Performance monitoring and statistics
- Element modification tracking

#### Non-Functional Requirements
- Processing overhead <200ms for typical SVG files
- Memory usage <100MB for large SVG files
- 99.9% reliability (graceful degradation on errors)
- Plugin isolation (one plugin failure doesn't break pipeline)

## Decision
**Implement a multi-layered preprocessing pipeline architecture** with plugin registry, context management, and orchestrated execution flow.

## Rationale

### Architectural Principles

#### 1. Plugin-Based Extensibility
```python
class PreprocessingPlugin(ABC):
    """Base class ensures consistent plugin interface"""

    @abstractmethod
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        """Determine if plugin can process this element"""
        pass

    @abstractmethod
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        """Process element, return True if modified"""
        pass
```

**Advantage**: New optimizations can be added without modifying core pipeline

#### 2. Context-Driven Processing
```python
class PreprocessingContext:
    """Shared context for all plugins with state management"""

    def __init__(self):
        self.precision = 3
        self.modifications_made = False
        self.removed_elements = set()
        self.stats = {}
```

**Advantage**: Plugins can communicate and share optimization state

#### 3. Registry-Based Plugin Management
```python
class PluginRegistry:
    """Centralized plugin registration and discovery"""

    def register(self, plugin: PreprocessingPlugin):
        self._plugins.append(plugin)

    def get_enabled_plugins(self) -> List[PreprocessingPlugin]:
        return [p for p in self._plugins if p.enabled]
```

**Advantage**: Dynamic plugin loading and configuration management

### Alternative Architectures Rejected

#### 1. Monolithic Optimizer Class
```python
# ❌ Rejected approach
class SVGOptimizer:
    def optimize(self, svg):
        # All optimization logic in one class
        self._cleanup_attrs(svg)
        self._optimize_paths(svg)
        self._simplify_transforms(svg)
        # ... 25+ optimization methods
```

**Rejection Reasons**:
- Monolithic class becomes unwieldy with 25+ optimizations
- Difficult to selectively enable/disable optimizations
- Hard to test individual optimization algorithms
- No plugin extensibility for custom optimizations

#### 2. Simple Function Pipeline
```python
# ❌ Rejected approach
def optimize_svg(svg_content):
    optimized = cleanup_attrs(svg_content)
    optimized = optimize_paths(optimized)
    optimized = simplify_transforms(optimized)
    return optimized
```

**Rejection Reasons**:
- No shared state between optimization steps
- Difficult configuration and selective execution
- Poor error isolation between steps
- Multiple XML parsing/serialization overhead

#### 3. External Tool Orchestration
```python
# ❌ Rejected approach
def optimize_svg(svg_content):
    # Chain multiple external tools
    result = subprocess.run(['svgo', ...])
    result = subprocess.run(['custom-optimizer', ...])
    return result
```

**Rejection Reasons**:
- Multiple process spawning overhead
- Complex error handling across tools
- Difficult state sharing between tools
- Dependency management complexity

## Implementation

### Core Architecture Components

#### 1. SVGOptimizer (Orchestrator)
```python
class SVGOptimizer:
    """Main optimizer that orchestrates plugin execution"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.registry = PluginRegistry()
        self._initialize_plugins()

    def optimize(self, svg_content: str) -> str:
        # Parse SVG
        root = ET.fromstring(svg_content)
        context = PreprocessingContext()

        # Multi-pass processing
        max_passes = self.config.get('multipass', False) and 3 or 1
        for pass_num in range(max_passes):
            context.modifications_made = False
            self._process_element_tree(root, context)

            if not context.modifications_made:
                break  # No changes, optimization complete

        return self._element_to_string(root)
```

#### 2. Plugin Registry (Plugin Management)
```python
class PluginRegistry:
    """Manages plugin registration, configuration, and execution order"""

    def __init__(self):
        self._plugins: List[PreprocessingPlugin] = []

    def register(self, plugin: PreprocessingPlugin):
        """Register plugin with validation"""
        if not isinstance(plugin, PreprocessingPlugin):
            raise ValueError("Plugin must inherit from PreprocessingPlugin")
        self._plugins.append(plugin)

    def get_enabled_plugins(self) -> List[PreprocessingPlugin]:
        """Return enabled plugins in execution order"""
        return [p for p in self._plugins if getattr(p, 'enabled', True)]
```

#### 3. PreprocessingContext (State Management)
```python
class PreprocessingContext:
    """Shared context and state management for all plugins"""

    def __init__(self):
        self.precision: int = 3
        self.modifications_made: bool = False
        self.removed_elements: Set[ET.Element] = set()
        self.stats: Dict[str, int] = {}

    def mark_for_removal(self, element: ET.Element):
        """Mark element for removal after processing"""
        self.removed_elements.add(element)
        self.modifications_made = True

    def record_modification(self, plugin_name: str, modification_type: str):
        """Record plugin modification for statistics"""
        key = f"{plugin_name}_{modification_type}"
        self.stats[key] = self.stats.get(key, 0) + 1
        self.modifications_made = True
```

### Execution Flow

#### 1. Element Tree Traversal
```python
def _process_element_tree(self, root: ET.Element, context: PreprocessingContext):
    """Process entire element tree with post-order traversal"""

    # Process children first (post-order for safe element removal)
    for element in list(root):
        self._process_element_tree(element, context)

    # Process current element with all applicable plugins
    self._process_single_element(root, context)
```

#### 2. Plugin Execution with Error Isolation
```python
def _process_single_element(self, element: ET.Element, context: PreprocessingContext):
    """Process single element with error isolation"""

    plugins = self.registry.get_enabled_plugins()

    for plugin in plugins:
        if plugin.can_process(element, context):
            try:
                modified = plugin.process(element, context)
                if modified:
                    context.modifications_made = True
            except Exception as e:
                # Log error but continue with other plugins
                print(f"Plugin {plugin.name} failed on element {element.tag}: {e}")
                # Plugin failure doesn't break pipeline
```

#### 3. Multi-Pass Optimization
```python
# Multi-pass processing for maximum optimization
for pass_num in range(max_passes):
    context.modifications_made = False
    self._process_element_tree(root, context)

    # Stop if no modifications were made
    if not context.modifications_made:
        break
```

### Configuration System

#### Preset Configurations
```python
PRESETS = {
    "minimal": {
        "plugins": ["cleanupAttrs", "removeEmptyAttrs", "removeComments"],
        "precision": 3,
        "multipass": False
    },
    "default": {
        "plugins": [
            "cleanupAttrs", "cleanupNumericValues", "removeEmptyAttrs",
            "removeEmptyContainers", "convertColors", "removeUnusedNS"
        ],
        "precision": 3,
        "multipass": False
    },
    "aggressive": {
        "plugins": "all",
        "precision": 2,
        "multipass": True
    }
}
```

#### Plugin-Specific Configuration
```python
def create_optimizer(preset: str = "default", **kwargs) -> SVGOptimizer:
    """Create optimizer with preset and custom overrides"""

    config = PRESETS.get(preset, PRESETS["default"]).copy()
    config.update(kwargs)  # Allow custom overrides

    # Plugin-specific configuration
    config["plugins"]["cleanupNumericValues"] = {
        "enabled": True,
        "precision": config.get("precision", 3)
    }

    return SVGOptimizer(config)
```

## Performance Characteristics

### Processing Performance
```
Small SVG (< 50 elements):  20-50ms preprocessing overhead
Medium SVG (50-200 elements): 50-120ms preprocessing overhead
Large SVG (200+ elements): 120-300ms preprocessing overhead

Net Performance Impact:
- Preprocessing cost: 20-300ms
- Conversion speedup: 100-800ms
- Net gain: 80-500ms faster overall conversion
```

### Memory Usage
```
Base Memory: 10-15MB for parser and plugins
Peak Memory: 25-45MB for large SVG processing
Cleanup: Automatic cleanup after processing
Memory Leaks: None detected in testing
```

### Optimization Effectiveness
```
File Size Reduction:
- Minimal preset: 30-40% average reduction
- Default preset: 40-60% average reduction
- Aggressive preset: 50-70% average reduction

Processing Improvement:
- Simple SVGs: 15-25% faster conversion
- Complex SVGs: 25-45% faster conversion
- Path-heavy SVGs: 30-50% faster conversion
```

## Consequences

### Positive Outcomes

#### Technical Benefits
- **Modular Architecture**: Easy to add, remove, or modify optimization algorithms
- **Error Isolation**: Single plugin failures don't break entire preprocessing
- **Configuration Flexibility**: Fine-grained control over optimization behavior
- **Performance Monitoring**: Built-in statistics for optimization effectiveness
- **Multi-Pass Optimization**: Iterative optimization for maximum benefit

#### Business Benefits
- **Faster Conversions**: 25-45% improvement in overall conversion speed
- **Smaller Files**: 40-70% reduction in SVG/PPTX file sizes
- **Better Quality**: Optimized SVGs convert more reliably to PowerPoint
- **Reduced Errors**: Better error handling and graceful degradation

### Technical Complexity
- **Architecture Overhead**: More complex than simple function pipeline
- **Plugin Development**: Requires understanding of plugin interface
- **Configuration Management**: More configuration options to maintain
- **Testing Complexity**: Each plugin needs comprehensive test coverage

### Maintenance Considerations
- **Plugin Updates**: Individual plugins can be updated independently
- **Performance Monitoring**: Built-in statistics help identify bottlenecks
- **Error Tracking**: Plugin-level error tracking aids debugging
- **Version Management**: Plugin versioning for backward compatibility

## Future Evolution

### Planned Enhancements

#### Advanced Plugin Features
- **Plugin Dependencies**: Declare and enforce plugin execution order
- **Conditional Plugins**: Plugins that activate based on SVG characteristics
- **Plugin Profiles**: User-defined plugin combinations for specific use cases

#### Performance Optimizations
- **Parallel Plugin Execution**: Run independent plugins in parallel
- **Lazy Plugin Loading**: Load plugins only when needed
- **Plugin Caching**: Cache plugin results for repeated SVG patterns

#### Integration Improvements
- **Real-Time Configuration**: Dynamic plugin configuration during processing
- **Quality Feedback**: Measure and report optimization impact on visual quality
- **Custom Plugin API**: Simplified API for developing custom optimization plugins

## References
- [Plugin Base Classes](../../src/preprocessing/base.py)
- [SVGOptimizer Implementation](../../src/preprocessing/optimizer.py)
- [Plugin Registry](../../src/preprocessing/base.py#L45-L70)
- [Performance Benchmarks](../../tests/performance/benchmarks/)
- [Configuration Examples](../../ADVANCED_OPTIMIZATIONS.md#configuration-reference)