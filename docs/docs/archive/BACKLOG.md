# SVG2PPTX Enhancement Backlog

A comprehensive roadmap for achieving near-100% SVG to PowerPoint conversion fidelity through systematic feature implementation.

## 🚀 Quick Wins (High ROI - Ship First)

### Phase 1: Core Foundation (Weeks 1-2)

#### 1. `units.py` - Universal Unit Converter ⭐️⭐️⭐️
**Impact**: Fixes 80% of sizing/positioning issues across all SVG files
- Centralized px/pt/mm/in/em/% → EMU conversion
- DPI heuristics with per-file override support
- Viewport-relative percentage resolution
- **Effort**: 2-3 days
- **ROI**: Very High - enables accurate rendering of most SVGs

#### 2. `viewbox.py` - Viewport & Aspect Ratio Handler ⭐️⭐️⭐️
**Impact**: Proper scaling and cropping for all SVG content
- Robust viewBox/preserveAspectRatio resolver
- EMU viewport mapping with crop/fit modes (meet/slice)
- Transform matrix generation for viewport scaling
- **Effort**: 2-3 days  
- **ROI**: Very High - critical for responsive SVG layouts

### Phase 2: Media & Visuals (Weeks 2-3)

#### 3. `images.py` - Image Embedding System ⭐️⭐️⭐️
**Impact**: Enables SVG files with embedded graphics (very common)
- Support data-URI, relative, absolute image paths
- Image decode, de-duplication, embed as `a:blipFill`
- Transform application to image elements
- **Effort**: 3-4 days
- **ROI**: High - unlocks logos, icons, mixed-media designs

#### 4. `strokes.py` - Advanced Line Styling ⭐️⭐️
**Impact**: Professional line appearance matching design intent
- Dash arrays, line joins/caps, miter limits
- Stroke-to-outline conversion for complex cases
- PPTX line style mapping with fallbacks
- **Effort**: 2-3 days
- **ROI**: High - critical for technical diagrams, wireframes

### Phase 3: Clipping & Style (Weeks 3-4)

#### 5. `clipping.py` - Shape Clipping Engine ⭐️⭐️
**Impact**: Handles cropped/masked content (common in designs)
- `<clipPath>` computation and effective clip shapes
- PPTX fallback via intersected paths
- Node-level raster fallback for complex clips
- **Effort**: 4-5 days
- **ROI**: Medium-High - enables complex layouts

#### 6. `style_inheritance.py` - CSS Resolution ⭐️⭐️⭐️
**Impact**: Accurate style computation (fixes rendering inconsistencies)
- Complete style cascade: inline + class + inheritance + presentation
- Computed style cache with dependency tracking
- Override priority resolution
- **Effort**: 3-4 days
- **ROI**: Very High - foundation for all visual rendering

## 🎯 Heavy Hitters (Unlock "Real" Files - Weeks 5-8)

### Advanced Typography & Graphics

#### 7. `fonts.py` - Font Management System ⭐️⭐️
**Impact**: Proper text rendering with font substitution
- SVG font family → PPTX theme/local font mapping
- Font substitution with fallback chains
- Optional font embedding, feature flags (ligatures, kerning)
- **Effort**: 5-6 days
- **ROI**: Medium-High - critical for text-heavy designs

#### 8. `markers.py` - Arrowheads & Line Markers ⭐️⭐️
**Impact**: Technical diagrams, flowcharts, callouts
- Arrowhead/marker scaling and orientation along paths
- PPTX line end cap mapping with geometry fallbacks
- Custom marker definitions
- **Effort**: 3-4 days
- **ROI**: Medium - specialized but high-value use cases

#### 9. `patterns.py` - Pattern Fill System ⭐️
**Impact**: Textured backgrounds, decorative elements
- Complex `<pattern>` tiling to PPTX
- Vector repeat for simple cases, bitmap fill for complex
- Transform-aware pattern rendering
- **Effort**: 4-5 days
- **ROI**: Medium - adds visual richness

### Advanced Effects & Composition

#### 10. `opacity_blend.py` - Transparency & Blending ⭐️⭐️
**Impact**: Layered designs with transparency effects
- Per-node opacity and basic blend modes
- Group alpha flattening, auto-rasterization decisions
- Blend mode approximation where possible
- **Effort**: 4-5 days
- **ROI**: Medium-High - common in modern designs

#### 11. `masks_filters.py` - Masks & Filter Effects ⭐️
**Impact**: Advanced visual effects (shadows, blur, etc.)
- `<mask>` implementation with alpha channels
- Basic filter graph: blur/drop-shadow/colorMatrix
- Smart rasterization vs OOXML emulation decisions
- **Effort**: 6-8 days
- **ROI**: Medium - high visual impact when needed

#### 12. `text_on_path.py` - Curved Text Layout ⭐️
**Impact**: Logos, decorative text, artistic layouts
- `textPath` layout with accurate baseline offsets
- Polyline approximation fallbacks
- Character spacing and orientation
- **Effort**: 5-6 days
- **ROI**: Low-Medium - specialized but distinctive feature

## 🔧 OOXML Integration (Weeks 9-10)

### PowerPoint-Specific Optimizations

#### 13. `theme_map.py` - Brand Consistency ⭐️⭐️
**Impact**: Corporate templates, brand-compliant exports
- Map SVG colors to PPTX themes (Accent1-6, Text/Background)
- Tint/shade generation, brand color preservation
- **Effort**: 2-3 days
- **ROI**: High - critical for corporate use cases

#### 14. `shape_writer.py` - Optimized Shape Output ⭐️⭐️
**Impact**: Cleaner PPTX files, better performance
- Clean `p:sp`, `p:grpSp` writers with preset geometry
- Smart `a:custGeom` vs `a:prstGeom` decisions
- **Effort**: 3-4 days
- **ROI**: Medium-High - improves output quality

#### 15. `zorder.py` - Layer Management ⭐️
**Impact**: Accurate stacking order in complex designs
- Deterministic z-order across groups
- PPTX `spTree` insertion utilities
- **Effort**: 2-3 days
- **ROI**: Medium - critical for layered designs

## 🛠️ Developer Experience & Tooling (Weeks 11-12)

### CLI & Development Tools

#### 16. `cli/` - Command Line Interface ⭐️⭐️⭐️
**Impact**: Production deployment, batch processing
- Flags: `--rasterize`, `--font-map`, `--dpi`, `--theme-map`, `--simplify`
- Batch conversion, progress reporting
- **Effort**: 3-4 days
- **ROI**: Very High - essential for production use

#### 17. `lint/` - Conversion Linter ⭐️⭐️
**Impact**: Proactive quality assurance, user education
- "Why this will look different" analysis
- Unsupported feature detection with suggestions
- **Effort**: 3-4 days
- **ROI**: High - improves user experience

#### 18. `report/` - Export Analytics ⭐️⭐️
**Impact**: Debugging, quality tracking, user transparency
- HTML/PPTX conversion reports
- Font substitutions, rasterization decisions, performance metrics
- **Effort**: 2-3 days
- **ROI**: Medium-High - valuable for debugging

### Quality Assurance

#### 19. `fixtures/` - Comprehensive Test Suite ⭐️⭐️
**Impact**: Regression prevention, edge case coverage
- Nasty SVG corpus: nested clips, transforms, giant paths
- Real-world file collection from various sources
- **Effort**: 2-3 days setup + ongoing
- **ROI**: High - prevents quality regressions

#### 20. `golden_tests/` - Visual Regression Testing ⭐️
**Impact**: Automated quality validation
- SVG raster reference vs PPTX slide raster comparison
- Pixel-diff with configurable tolerance
- **Effort**: 4-5 days
- **ROI**: Medium - catches visual regressions

## 🚀 Performance & Optimization (Weeks 13-14)

### Algorithmic Improvements

#### 21. `geometry_simplify.py` - Advanced Path Optimization ⭐️⭐️⭐️ **✅ COMPLETED**
**Impact**: Revolutionary geometry processing with 50-90% path reduction
- ✅ **Implemented**: Ramer-Douglas-Peucker algorithm with force indices
- ✅ **Implemented**: Catmull-Rom cubic smoothing for natural curves  
- ✅ **Implemented**: Collinear point merging with angle tolerance
- ✅ **Implemented**: Advanced path simplification plugin
- ✅ **Implemented**: Enhanced polygon simplification with RDP
- ✅ **Implemented**: Cubic smoothing plugin for organic shapes
- **Effort**: 3-4 days → **COMPLETED**
- **ROI**: Very High - provides industry-leading geometry optimization

#### 22. `boolean_ops.py` - Path Boolean Operations ⭐️
**Impact**: Advanced shape combinations
- Union/intersect/subtract for clips/masks/compound paths
- PPTX single outline materialization
- **Effort**: 5-6 days
- **ROI**: Low-Medium - specialized geometric operations

#### 23. `cache/` - Performance Caching ⭐️
**Impact**: Faster repeated conversions
- Memoize gradients, images, font metrics
- Content-based hashing for deduplication
- **Effort**: 2-3 days
- **ROI**: Medium - improves batch processing

## 🔌 Advanced Integrations (Weeks 15-16)

### External Library Integration

#### 24. `raster_fallback.py` - Headless Rendering ⭐️
**Impact**: Perfect fallback for unsupported features
- Pillow/Cairo/Playwright node-scoped rasterization
- Smart decision tree for raster vs vector
- **Effort**: 4-5 days
- **ROI**: Medium - handles edge cases gracefully

#### 25. `harfbuzz_adapter.py` - Advanced Typography ⭐️
**Impact**: Professional text rendering quality
- Accurate text shaping, kerning, ligatures
- Complex script support (Arabic, Devanagari, etc.)
- **Effort**: 6-8 days
- **ROI**: Low - specialized typography use cases

#### 26. `python_pptx_bridge.py` - High-Level API ⭐️
**Impact**: Easier integration for Python developers
- python-pptx compatibility layer
- Maintains pristine OOXML output
- **Effort**: 3-4 days
- **ROI**: Medium - improves developer adoption

## 🎨 Nice-to-Haves (Future Enhancements)

### Advanced Features

#### 27. `master_layout.py` - Slide Template Integration
**Impact**: Corporate template compliance
- Master/Layout vs Slide placement
- Title-safe/content-safe margin respect
- **Effort**: 3-4 days
- **ROI**: Low-Medium - corporate template scenarios

#### 28. `guides_grid.py` - Design Grid Support
**Impact**: Designer-friendly output
- PPTX guides from SVG grids
- Snap-to-grid during export
- **Effort**: 2-3 days
- **ROI**: Low - design workflow enhancement

#### 29. `blend_expand.py` - Advanced Blend Modes
**Impact**: Sophisticated visual effects
- Multiply/screen/overlay approximation
- Pre-composition against backdrop colors
- **Effort**: 4-5 days
- **ROI**: Low - advanced visual effects

#### 30. `anim_stub.py` - Animation Handling
**Impact**: Animated SVG support
- Parse `<animate>` for representative frames
- Multi-slide sequence export
- **Effort**: 5-6 days
- **ROI**: Low - specialized animation scenarios

#### 31. `perf_profiler.py` - Performance Analysis
**Impact**: Optimization guidance
- Flame graphs for pathological SVGs
- Automatic `--simplify` threshold suggestions
- **Effort**: 3-4 days
- **ROI**: Low - development tool

## 🎯 Recommended Implementation Order

### Sprint 1-2 (Foundation) - 4 weeks
1. **units.py** ⭐️⭐️⭐️
2. **viewbox.py** ⭐️⭐️⭐️  
3. **images.py** ⭐️⭐️⭐️
4. **style_inheritance.py** ⭐️⭐️⭐️

### Sprint 3-4 (Visual Quality) - 4 weeks  
5. **strokes.py** ⭐️⭐️
6. **clipping.py** ⭐️⭐️
7. **markers.py** ⭐️⭐️
8. **fonts.py** ⭐️⭐️

### Sprint 5-6 (Advanced Features) - 4 weeks
9. **patterns.py** ⭐️
10. **opacity_blend.py** ⭐️⭐️
11. **masks_filters.py** ⭐️
12. **theme_map.py** ⭐️⭐️

### Sprint 7-8 (Production Ready) - 4 weeks
13. **cli/** ⭐️⭐️⭐️
14. **lint/** ⭐️⭐️
15. **report/** ⭐️⭐️
16. **fixtures/** ⭐️⭐️

### Sprint 9+ (Polish & Performance) - As needed
17. **shape_writer.py** ⭐️⭐️
18. **geometry_simplify.py** ⭐️
19. **boolean_ops.py** ⭐️
20. **raster_fallback.py** ⭐️

## 📊 Success Metrics

- **Conversion Fidelity**: Target 95%+ visual accuracy on standard test suite
- **Performance**: <200ms per typical SVG element, <2GB memory for large files
- **Coverage**: Handle 90%+ of real-world SVG features without rasterization
- **Usability**: CLI tool with comprehensive linting and reporting
- **Maintainability**: Modular architecture with >90% test coverage

## 🔄 Continuous Integration

- **Golden test suite**: Run visual regression tests on every commit
- **Performance benchmarks**: Track conversion speed and memory usage
- **Feature coverage**: Automated detection of newly supported SVG features
- **User feedback loop**: Collection and analysis of conversion quality reports

---

**Next Steps**: Begin with Phase 1 foundation modules (`units.py` → `viewbox.py` → `images.py` → `style_inheritance.py`) to establish the core infrastructure that all subsequent features will build upon.