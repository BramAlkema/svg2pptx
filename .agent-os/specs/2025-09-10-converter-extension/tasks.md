# Spec Tasks

These are the tasks to be completed for the spec detailed in @.agent-os/specs/2025-09-10-converter-extension/spec.md

> Created: 2025-09-10
> Status: Ready for Implementation

## Phase 1: Shape Extensions (High Priority)

### Task 1.1: Enhance LineConverter
- [ ] 1.1.1 Write comprehensive tests for LineConverter enhancements
  - [ ] Test current LineConverter behavior (baseline tests)
  - [ ] Test coordinate system integration with UnitConverter/ViewportResolver
  - [ ] Test connection shape vs regular shape generation
  - [ ] Test line markers integration
  - [ ] Test edge cases (zero-length, extreme coordinates, invalid points)
- [ ] 1.1.2 Review current LineConverter implementation in shapes.py
- [ ] 1.1.3 Improve coordinate system handling for line elements
- [ ] 1.1.4 Enhance connection shape generation (`<p:cxnSp>` vs `<p:sp>`)
- [ ] 1.1.5 Add support for line markers (arrow heads) if missing
- [ ] 1.1.6 Ensure consistent integration with universal utilities
- [ ] 1.1.7 Run all tests and verify enhancements work correctly

**Acceptance Criteria:**
- LineConverter handles all line positioning scenarios correctly
- Proper integration with UnitConverter for coordinate conversion
- Connection shapes generate valid DrawingML
- Full test coverage including edge cases

### Task 1.2: Improve PolygonConverter/PolylineConverter
- [ ] 1.2.1 Write comprehensive tests for PolygonConverter/PolylineConverter improvements
  - [ ] Test current polygon/polyline behavior (baseline tests)
  - [ ] Test points parsing with various formats (comma/space/mixed separators)
  - [ ] Test custom geometry path generation accuracy
  - [ ] Test polygon vs polyline distinction (closed vs open paths)
  - [ ] Test bounding box calculations for edge cases
  - [ ] Test complex polygon shapes (self-intersecting, concave)
  - [ ] Test performance with large point sets
- [ ] 1.2.2 Review current polygon/polyline implementation
- [ ] 1.2.3 Enhance points parsing for various formats (comma/space separated)
- [ ] 1.2.4 Improve custom geometry path generation
- [ ] 1.2.5 Ensure proper distinction between polygon (closed) and polyline (open)
- [ ] 1.2.6 Optimize bounding box calculations
- [ ] 1.2.7 Add support for complex polygon shapes
- [ ] 1.2.8 Run all tests and verify improvements work correctly

**Acceptance Criteria:**
- Robust points string parsing handles all valid formats
- Custom geometry generation is accurate and efficient
- Clear distinction between polygon and polyline behavior
- Performance optimized for complex shapes

## Phase 2: Reference Elements (High Priority)

### Task 2.1: Implement DefsConverter
- [ ] 2.1.1 Write comprehensive tests for DefsConverter implementation
  - [ ] Test defs element recognition and processing
  - [ ] Test child element dispatching (gradients, patterns, symbols)
  - [ ] Test nested defs elements handling
  - [ ] Test definition storage in ConversionContext
  - [ ] Test integration with ConverterRegistry
  - [ ] Test no visual output from defs processing
  - [ ] Test invalid/empty defs handling
- [ ] 2.1.2 Create new DefsConverter class following BaseConverter pattern
- [ ] 2.1.3 Implement defs container processing logic
- [ ] 2.1.4 Add child element dispatching to appropriate converters
- [ ] 2.1.5 Handle nested defs elements
- [ ] 2.1.6 Integrate with ConverterRegistry system
- [ ] 2.1.7 Update ConversionContext for definition storage
- [ ] 2.1.8 Run all tests and verify DefsConverter works correctly

**File Location:** `src/converters/references.py` (new file)

**Acceptance Criteria:**
- DefsConverter processes all child definition elements
- Proper integration with existing gradient, pattern converters
- No visible output from defs conversion (definitions only)
- Full test coverage including nested scenarios

### Task 2.2: Implement SymbolConverter
- [ ] Create SymbolConverter class in references.py
- [ ] Implement symbol definition storage in ConversionContext
- [ ] Handle viewBox attribute processing for symbols
- [ ] Process nested elements within symbol definitions
- [ ] Add symbol ID registration and lookup system
- [ ] Create test suite for symbol processing

**Acceptance Criteria:**
- Symbols stored correctly in context.symbols
- ViewBox information preserved for scaling
- Nested elements processed and stored
- Symbol resolution system works reliably

### Task 2.3: Implement UseConverter
- [ ] 2.3.1 Write comprehensive tests for UseConverter implementation
  - [ ] Test href/xlink:href reference resolution (valid and invalid)
  - [ ] Test x, y positioning offset handling with various units
  - [ ] Test transform composition (use transform + positioning)
  - [ ] Test circular reference detection and prevention
  - [ ] Test invalid references handling (missing targets, malformed hrefs)
  - [ ] Test use elements referencing different element types (symbols, shapes, groups)
  - [ ] Test nested use elements and complex reference chains
  - [ ] Test error handling and graceful degradation
- [ ] 2.3.2 Create UseConverter class in references.py
- [ ] 2.3.3 Implement href/xlink:href reference resolution
- [ ] 2.3.4 Add x, y positioning offset handling
- [ ] 2.3.5 Implement transform composition (use transform + positioning)
- [ ] 2.3.6 Create circular reference detection system
- [ ] 2.3.7 Handle invalid references gracefully
- [ ] 2.3.8 Run all tests and verify UseConverter works correctly

**Acceptance Criteria:**
- Reference resolution works for all symbol/element types
- Positioning offsets applied correctly
- Transform composition handles all cases
- Circular references detected and handled gracefully
- Invalid references fail gracefully with appropriate warnings

### Task 2.4: Extend ConversionContext for References
- [ ] Add symbols storage dictionary to ConversionContext
- [ ] Add uses tracking for circular reference detection
- [ ] Implement helper methods for symbol storage/retrieval
- [ ] Add circular reference detection methods
- [ ] Update context initialization
- [ ] Create unit tests for context extensions

**Acceptance Criteria:**
- Context properly stores and retrieves symbol definitions
- Circular reference detection is reliable
- Helper methods provide clean API for converters
- Backward compatibility maintained

## Phase 3: Media Elements (Medium Priority)

### Task 3.1: Implement ImageConverter
- [ ] 3.1.1 Write comprehensive tests for ImageConverter implementation
  - [ ] Test href/xlink:href image source resolution
  - [ ] Test base64 embedded images (PNG, JPEG, SVG data: URLs)
  - [ ] Test external image file references (relative and absolute paths)
  - [ ] Test image data embedding in PowerPoint format
  - [ ] Test x, y, width, height positioning with various units
  - [ ] Test transform and style integration (rotation, scaling, opacity)
  - [ ] Test image caching for duplicate references
  - [ ] Test error handling (invalid images, missing files, corrupted data)
  - [ ] Test image format support (PNG, JPEG, GIF, SVG)
  - [ ] Test memory management for large images
  - [ ] Test aspect ratio preservation and scaling
- [ ] 3.1.2 Create new ImageConverter class
- [ ] 3.1.3 Implement href/xlink:href image source resolution
- [ ] 3.1.4 Add support for base64 embedded images (data: URLs)
- [ ] 3.1.5 Add support for external image file references
- [ ] 3.1.6 Implement image data embedding in PowerPoint
- [ ] 3.1.7 Handle x, y, width, height positioning with units
- [ ] 3.1.8 Add transform and style integration
- [ ] 3.1.9 Implement image caching for duplicate references
- [ ] 3.1.10 Run all tests and verify ImageConverter works correctly

**File Location:** `src/converters/images.py` (new file)

**Acceptance Criteria:**
- Base64 images decode and embed correctly
- External image references load and embed
- Image positioning uses universal unit conversion
- Caching prevents duplicate image processing
- Error handling for invalid/missing images

### Task 3.2: Extend ConversionContext for Images
- [ ] Add images storage dictionary to ConversionContext
- [ ] Implement image storage and retrieval methods
- [ ] Add image caching mechanism
- [ ] Handle image metadata storage
- [ ] Create unit tests for image context extensions

**Acceptance Criteria:**
- Images stored with proper metadata
- Caching prevents duplicate processing
- Memory efficient image handling

## Phase 4: Advanced Features (Lower Priority)

### Task 4.1: Implement PatternConverter
- [ ] Create PatternConverter class
- [ ] Implement pattern definition storage
- [ ] Handle patternUnits and patternContentUnits
- [ ] Add pattern transform support
- [ ] Implement DrawingML pattern fill generation (with fallbacks)
- [ ] Process nested pattern content
- [ ] Create comprehensive test suite

**File Location:** `src/converters/effects.py` (new file)

**Acceptance Criteria:**
- Pattern definitions stored and processed correctly
- Pattern fills generate valid DrawingML (or fallbacks)
- Transform integration works properly
- Fallback strategies for unsupported patterns

### Task 4.2: Implement ClipPathConverter
- [ ] Create ClipPathConverter class in effects.py
- [ ] Implement clip path definition storage
- [ ] Handle clipPathUnits attribute
- [ ] Add path-based and shape-based clipping support
- [ ] Implement PowerPoint masking integration (limited)
- [ ] Create fallback strategies for unsupported clipping
- [ ] Add comprehensive test coverage

**Acceptance Criteria:**
- Clip path definitions stored properly
- Basic PowerPoint masking works where supported
- Graceful fallbacks for unsupported clipping
- Clear documentation of limitations

### Task 4.3: Implement FilterConverter
- [ ] Create FilterConverter class in effects.py
- [ ] Implement basic filter effects (drop shadows, blur)
- [ ] Add filter definition storage
- [ ] Handle filterUnits and primitiveUnits
- [ ] Create fallback strategies for unsupported effects
- [ ] Add comprehensive test suite with fallback testing

**Acceptance Criteria:**
- Basic filter effects convert to PowerPoint equivalents
- Unsupported filters have appropriate fallbacks
- Filter definitions stored for application
- Clear warnings for unsupported filter types

## Phase 5: Integration and Testing

### Task 5.1: Update ConverterRegistry
- [ ] Register all new converters in ConverterRegistry
- [ ] Update __init__.py imports and exports
- [ ] Add element type mapping for new converters
- [ ] Test converter dispatch for new element types
- [ ] Verify no conflicts with existing converters

**Acceptance Criteria:**
- All new converters register and dispatch correctly
- No conflicts or regressions in existing functionality
- Element mapping works efficiently

### Task 5.2: Create Integration Tests
- [ ] 5.2.1 Build comprehensive integration test suite
  - [ ] Test converter chains (defs -> symbol -> use -> reference resolution)
  - [ ] Test universal utility integration across all new converters
  - [ ] Test complex SVG files with multiple new element types
  - [ ] Test interaction between new converters and existing ones
  - [ ] Test error propagation through converter chains
  - [ ] Test memory usage and performance with large SVG files
  - [ ] Test real-world SVG samples from design tools (Illustrator, Inkscape)
- [ ] 5.2.2 Build regression test suite
  - [ ] Test all existing converter functionality remains intact
  - [ ] Test existing SVG files still convert correctly
  - [ ] Test no performance degradation in existing converters
  - [ ] Test backward compatibility of API changes
- [ ] 5.2.3 Build end-to-end validation tests
  - [ ] Test generated PowerPoint files open correctly in PowerPoint
  - [ ] Test visual fidelity of converted elements
  - [ ] Test PowerPoint file structure integrity
  - [ ] Test file size optimization
- [ ] 5.2.4 Run full integration test suite and verify all tests pass

**File Location:** `tests/integration/test_converter_extensions.py`

**Acceptance Criteria:**
- Complex SVG files with multiple element types convert correctly
- No performance regressions in existing converters
- Universal utilities integrate seamlessly
- Real-world SVG samples convert successfully

### Task 5.3: Documentation and Guidelines
- [ ] Create converter implementation guidelines document
- [ ] Update API documentation for new converters
- [ ] Add code examples for each new converter
- [ ] Document integration patterns with universal utilities
- [ ] Create troubleshooting guide for common issues

**File Location:** `docs/converter_extensions.md`

**Acceptance Criteria:**
- Clear guidelines for implementing future converters
- Complete API documentation for all new converters
- Code examples demonstrate proper usage patterns
- Troubleshooting guide covers common scenarios

## Phase 6: Validation and Polish

### Task 6.1: Comprehensive Testing
- [ ] 6.1.1 Build comprehensive test coverage
  - [ ] Achieve 90%+ code coverage for all new converters
  - [ ] Build unit tests for every public method in new converters
  - [ ] Build tests for all error handling paths and edge cases
  - [ ] Build parametrized tests for various input formats
  - [ ] Build mock tests for external dependencies (file system, network)
  - [ ] Build property-based tests for complex data transformations
- [ ] 6.1.2 Build validation test suite
  - [ ] Build tests to validate DrawingML output with PowerPoint
  - [ ] Build tests with wide variety of SVG files (simple to complex)
  - [ ] Build visual regression tests comparing before/after outputs
  - [ ] Build tests for PowerPoint file integrity and structure
- [ ] 6.1.3 Build performance test suite  
  - [ ] Build performance benchmarks for all new converters
  - [ ] Build memory usage tests for large files
  - [ ] Build scalability tests with increasing complexity
  - [ ] Build comparative performance tests vs existing converters
- [ ] 6.1.4 Run all test suites and verify 90%+ coverage achieved

**Acceptance Criteria:**
- High test coverage across all new code
- All error scenarios handled gracefully
- Generated PowerPoint files open correctly
- Performance meets existing standards

### Task 6.2: Code Review and Refinement
- [ ] Internal code review of all new converters
- [ ] Refactor for consistency with existing codebase
- [ ] Optimize performance bottlenecks
- [ ] Ensure consistent error handling patterns
- [ ] Validate integration with universal utilities

**Acceptance Criteria:**
- Code follows existing patterns and conventions
- Performance optimized for common use cases
- Consistent error handling across all converters
- Clean integration with existing systems

## Implementation Notes

### Dependencies
- All tasks depend on existing BaseConverter pattern
- Universal utilities (UnitConverter, ColorParser, TransformParser, ViewportResolver)
- Existing ConverterRegistry system
- PowerPoint DrawingML generation framework

### Ordering Constraints
- DefsConverter must be implemented before other reference converters
- ConversionContext extensions needed before converters that use them
- Registry updates should happen after converter implementation
- Integration testing requires all converters to be complete

### Risk Mitigation
- Start with shape extensions (lower risk, build confidence)
- Implement comprehensive error handling early
- Create fallback strategies for PowerPoint limitations
- Maintain backward compatibility throughout

### Success Metrics
- All basic SVG shape elements supported
- Major SVG element types (image, use, symbol, defs) converted
- No regressions in existing functionality
- 90%+ test coverage for new code
- Real-world SVG files convert with high fidelity