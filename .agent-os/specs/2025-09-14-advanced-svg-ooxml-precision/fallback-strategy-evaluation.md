# SVG to OOXML Fallback Strategy Evaluation

This document evaluates fallback strategies for unsupported SVG elements when converting to PowerPoint OOXML format.

## Strategy Classification

- **Route A (Vector-Priority)**: Maintains vector format using creative OOXML workarounds
- **Route B (Bitmap-Priority)**: Renders unsupported elements to raster images
- **Native DML**: Direct OOXML DrawingML equivalent exists

## Conditional Content Elements

| Element | Reason | Route A (Vector-Priority) | Route B (Bitmap-Priority) |
|---------|--------|---------------------------|---------------------------|
| `switch` | Conditional content | Evaluate conditions → include matching child only | Rasterise selected branch |
| `script` | No scripting | Ignore, pre-evaluate scripted results | Rasterise post-script DOM |
| `link` | No live links | Convert to external hyperlink on shape (`a:hlinkClick`) | Omit link |

**Implementation Priority**: Medium
**Route A Complexity**: Low-Medium (condition evaluation logic needed)
**Route B Complexity**: Low (straightforward rasterization)

## Filter Effects Elements

| Element | Reason | Route A (Vector-Priority) | Route B (Bitmap-Priority) |
|---------|--------|---------------------------|---------------------------|
| `feBlend` | Blend modes not supported | Simulate with two overlapping shapes using opacity tricks (multiply ≈ darken duotone, screen ≈ light clone) | Pre-blend layers to bitmap |
| `feColorMatrix` | Only hue/sat/lum mods | Approx hueRotate → `a:hueMod`, sat/lum → `a:satMod/lumMod`; ignore rest | Flatten colour-matrix result to bitmap |
| `feComponentTransfer` | No LUT/gamma | Approx threshold via `a:biLevel`, grayscale/duotone for others | Precompose LUT on pixels |
| `feComposite` | No arithmetic/porter-duff | Rebuild logical shape ops (in, out, atop) as geometry booleans | Pre-flatten |
| `feConvolveMatrix` | No convolution | Edge/Sobel: rebuild with dashed stroked paths | Render kernel effect to bitmap |
| `feDiffuseLighting` | No height map | Use `a:sp3d/a:bevelT` + inner shadow to fake diffuse | Bake diffuse-lighting pass |
| `feDisplacementMap` | No warp | Subdivide path and nudge nodes along normals | Flatten warp result to bitmap |
| `feMerge` | No input layering | Emit groups as separate shapes, group them | Preflatten all merged inputs |
| `feMorphology` | No erode/dilate | Stroke-to-outline expand/contract then boolean union/subtract | Render morphology result |
| `feSpecularLighting` | No height map | Use 3D bevel + highlight outer shadow | Bake specular pass to bitmap |
| `feTile` | No filter-space tiling | Export region as PNG tile and `a:blipFill/a:tile` | Flatten |
| `feTurbulence` | No procedural noise | Precompute tileable noise to vector hatch fill | Render noise as bitmap |
| `feDistantLight`/`fePointLight`/`feSpotLight` | Only inside lighting filters | Map to scene3d/lightRig when used with bevel | Rasterise lighting pass |

**Implementation Priority**: High (core filter functionality)
**Route A Complexity**: High (requires creative DML manipulation)
**Route B Complexity**: Medium (requires filter pipeline rendering)

## Advanced Graphics Elements

| Element | Reason | Route A (Vector-Priority) | Route B (Bitmap-Priority) |
|---------|--------|---------------------------|---------------------------|
| `textPath` | Only basic WordArt on path | Convert glyphs to positioned tspans along sampled path | Convert text to outlines (paths) and place along path |
| `foreignObject` | HTML not supported | Render HTML fragment via headless browser to SVG/EMF and embed | Rasterise region as PNG and place as `a:pic` |
| `meshGradient` | No mesh support | Sample mesh into dense stop grid → convert to many blended radial fills | Flatten to high-DPI raster image fill |
| `hatch` | No hatch support | Procedurally draw stroked lines pattern as repeated group | Render pattern tile to PNG + `a:blipFill/a:tile` |
| `marker` (paint role) | Only preset arrows | Convert markers to explicit small shapes at each vertex | Bake path+marker combo as a single vector shape |
| `clipPath` | No live clipping | Boolean-intersect target geometry with clip geometry → single path | Pre-clip to bitmap mask and place as `a:pic` |
| `mask` | No alpha masking | Split fills and strokes; intersect with mask shape geometry | Pre-mask composition and place as flattened `a:pic` |
| `filter` (container) | Most filter primitives unsupported | Expand supported subset (blur, shadow) as DML effects, others as baked layers | Flatten whole filter result as bitmap and embed |
| `style` (CSS) | CSS unsupported | Parse CSS → inline attributes before export | Render styled element to bitmap |

**Implementation Priority**: Medium-High
**Route A Complexity**: Very High (requires geometry processing, path manipulation)
**Route B Complexity**: Medium (requires rendering pipeline)

## Native DML Support (Priority Implementation)

These elements have direct OOXML equivalents and should be implemented first:

### Filter Primitives with Direct DML Mapping
- `feDropShadow` → `a:outerShdw` (outer shadow)
- `feFlood` → Solid color fill
- `feGaussianBlur` → `a:blur` (blur effect)
- `feImage` → `a:blipFill` (image fill)
- `feOffset` → Shadow/glow distance/direction parameters

### Basic Gradients and Effects
- Linear gradients → `a:gradFill` with `a:lin`
- Radial gradients → `a:gradFill` with `a:path`
- Basic shadows → `a:outerShdw`, `a:innerShdw`
- Basic blur → `a:blur`

## Implementation Strategy

### Phase 1: Native DML Support
1. Implement direct mappings for supported filter primitives
2. Basic gradient conversion
3. Simple shadow and blur effects

### Phase 2: Vector-Priority Fallbacks
1. Color matrix approximations using DML color modifications
2. Composite operations using shape layering
3. Basic lighting effects using 3D bevels

### Phase 3: Bitmap Fallbacks
1. Complex filter chains requiring rasterization
2. Advanced lighting and distortion effects
3. Procedural content (turbulence, complex patterns)

## Quality vs Performance Trade-offs

### Vector-Priority Benefits
- Maintains scalability
- Smaller file sizes
- Editable in PowerPoint
- Better performance in presentations

### Vector-Priority Costs
- Complex implementation
- Approximate results only
- May not match SVG exactly
- Higher development time

### Bitmap-Priority Benefits
- Exact visual fidelity
- Simpler implementation
- Handles any complexity
- Predictable results

### Bitmap-Priority Costs
- Fixed resolution
- Larger file sizes
- Not editable in PowerPoint
- Performance impact on complex slides

## Recommended Implementation Order

1. **feGaussianBlur, feDropShadow, feOffset** - Direct DML mapping (S1)
2. **feFlood, feImage** - Simple fills and images (S1)
3. **feColorMatrix** - DML color modifications approximation (S2)
4. **feComposite** - Shape layering and grouping (S2)
5. **feMerge** - Multiple shape emission (S2)
6. **Complex filters** - Rasterization fallback (S3)
7. **Lighting effects** - 3D bevel approximation or rasterization (S2/S3)
8. **Distortion effects** - Geometry manipulation or rasterization (S2/S3)

## Success Metrics

- **Coverage**: Percentage of SVG filter effects successfully converted
- **Fidelity**: Visual similarity to original SVG (measured via image comparison)
- **Performance**: Conversion speed and output file size
- **Editability**: Percentage of effects remaining editable in PowerPoint
- **Compatibility**: PowerPoint version support and rendering consistency