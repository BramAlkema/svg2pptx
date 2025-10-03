# SVG Filter Effects - User Guide

**Welcome to SVG2PPTX Filter Effects!** 🎨

This guide shows you how to use SVG filter effects in your PowerPoint presentations. Filters allow you to add visual effects like blur, shadows, and color transformations to your SVG elements.

---

## Quick Start

### Basic Filter Example

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <defs>
    <filter id="blur">
      <feGaussianBlur stdDeviation="3"/>
    </filter>
  </defs>

  <rect x="10" y="10" width="100" height="50"
        fill="red" filter="url(#blur)"/>
</svg>
```

**Result**: Red rectangle with 3px blur effect in PowerPoint ✓

### Three Simple Steps

1. **Define filter in `<defs>`** - Put your filter definition in the SVG `<defs>` section
2. **Give it an ID** - Use `id="myfilter"` to name your filter
3. **Apply to elements** - Use `filter="url(#myfilter)"` on any shape

That's it! SVG2PPTX handles the rest automatically.

---

## Supported Filter Types

SVG2PPTX supports all 19 standard SVG filter effects:

### Most Common Filters

| Filter | Description | Example Use |
|--------|-------------|-------------|
| `feGaussianBlur` | Blur effect | Soft focus, glowing effects |
| `feDropShadow` | Drop shadow | Adding depth to elements |
| `feColorMatrix` | Color transformations | Sepia, grayscale, color shifts |
| `feOffset` | Position offset | Shadow positioning |
| `feBlend` | Blending modes | Overlay, multiply effects |

### Advanced Filters

| Filter | Description |
|--------|-------------|
| `feComponentTransfer` | Per-channel color adjustments |
| `feComposite` | Layer compositing operations |
| `feConvolveMatrix` | Convolution effects (sharpen, edge detect) |
| `feDiffuseLighting` | Diffuse lighting effects |
| `feDisplacementMap` | Displacement/distortion |
| `feFlood` | Solid color fill |
| `feImage` | Image input for effects |
| `feMerge` | Layer merging |
| `feMorphology` | Dilate/erode operations |
| `feSpecularLighting` | Specular lighting effects |
| `feTile` | Tiling patterns |
| `feTurbulence` | Perlin noise generation |

---

## Common Use Cases

### 1. Blur Effect

**Use**: Soft focus, glowing elements

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">
  <defs>
    <filter id="soft_blur">
      <feGaussianBlur stdDeviation="2"/>
    </filter>
  </defs>

  <circle cx="150" cy="100" r="50"
          fill="#4ECDC4" filter="url(#soft_blur)"/>
</svg>
```

**Tips**:
- `stdDeviation="2"` = light blur
- `stdDeviation="5"` = medium blur
- `stdDeviation="10"` = heavy blur

---

### 2. Drop Shadow

**Use**: Adding depth and dimension

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">
  <defs>
    <filter id="drop_shadow">
      <feDropShadow dx="3" dy="3" stdDeviation="2"
                    flood-color="#000000" flood-opacity="0.5"/>
    </filter>
  </defs>

  <rect x="50" y="50" width="150" height="80"
        fill="#FF6B6B" filter="url(#drop_shadow)"/>
</svg>
```

**Parameters**:
- `dx`, `dy` = shadow offset (pixels)
- `stdDeviation` = shadow blur
- `flood-opacity` = shadow transparency

---

### 3. Grayscale Effect

**Use**: Black and white images, emphasis

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">
  <defs>
    <filter id="grayscale">
      <feColorMatrix type="saturate" values="0"/>
    </filter>
  </defs>

  <image x="10" y="10" width="280" height="180"
         href="photo.jpg" filter="url(#grayscale)"/>
</svg>
```

---

### 4. Glow Effect

**Use**: Highlighting, neon effects

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">
  <defs>
    <filter id="glow">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feFlood flood-color="#FFD700" flood-opacity="0.8"/>
      <feComposite in2="blur" operator="in"/>
      <feMerge>
        <feMergeNode/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <text x="150" y="100" text-anchor="middle"
        font-size="48" fill="white" filter="url(#glow)">
    GLOW
  </text>
</svg>
```

---

## Filter Application Rules

### What Gets Filtered

✅ **Supported Elements**:
- Rectangles (`<rect>`)
- Circles (`<circle>`)
- Ellipses (`<ellipse>`)
- Paths (`<path>`)
- Polygons (`<polygon>`)
- Polylines (`<polyline>`)
- Lines (`<line>`)
- Text (`<text>`)
- Groups (`<g>`)
- Images (`<image>`)

### Group Filters

When you apply a filter to a group, **each child inherits the filter**:

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">
  <defs>
    <filter id="shadow">
      <feDropShadow dx="2" dy="2" stdDeviation="1"/>
    </filter>
  </defs>

  <g filter="url(#shadow)">
    <rect x="10" y="10" width="50" height="50" fill="red"/>
    <circle cx="100" cy="35" r="25" fill="blue"/>
    <text x="150" y="35">Text</text>
  </g>
</svg>
```

**Result**: All three elements (rect, circle, text) have drop shadows ✓

**Note**: This is by design - PowerPoint doesn't support group-level filters, so we apply to each child individually.

### Child Overrides Parent

Child elements can override their parent's filter:

```xml
<g filter="url(#blur)">
  <rect x="10" y="10" width="50" height="50" fill="red"/>
  <!-- This rect uses shadow instead of blur -->
  <rect x="70" y="10" width="50" height="50" fill="blue"
        filter="url(#shadow)"/>
</g>
```

---

## Best Practices

### ✅ DO

1. **Keep it simple** - Use common filters (blur, shadow) for best compatibility
2. **Test in PowerPoint** - Check how your filters render
3. **Use reasonable values** - Extreme blur values may not render well
4. **Reuse filters** - Define once, apply to multiple elements

### ❌ DON'T

1. **Over-filter** - Too many filters can slow rendering
2. **Extreme parameters** - `stdDeviation="100"` will look bad
3. **Nest too deeply** - Avoid filter chains longer than 3-4 primitives
4. **Forget fallbacks** - Not all PowerPoint versions support all filters

---

## Troubleshooting

### Filter Not Appearing?

**Check these**:
1. ✅ Filter defined in `<defs>` section
2. ✅ Filter has unique `id` attribute
3. ✅ Element references filter with `filter="url(#id)"`
4. ✅ Filter ID matches reference (case-sensitive!)

### Filter Looks Different?

**Common causes**:
- PowerPoint may approximate complex filters
- Some filters use EMF fallback for best fidelity
- Color spaces may differ slightly

### Performance Issues?

**Tips**:
- Reduce `stdDeviation` values (< 10 is usually fine)
- Simplify filter chains
- Use simpler filters (blur, shadow) instead of complex chains

---

## Advanced Techniques

### Filter Chains

Combine multiple filter primitives for complex effects:

```xml
<filter id="emboss">
  <feGaussianBlur stdDeviation="1" result="blur"/>
  <feColorMatrix type="matrix"
                 values="1 0 0 0 0
                         0 1 0 0 0
                         0 0 1 0 0
                         0 0 0 18 -7" result="matrix"/>
  <feComposite in="SourceGraphic" in2="matrix"
               operator="arithmetic" k1="1" k2="0" k3="0" k4="0"/>
</filter>
```

### Lighting Effects

Create 3D-style lighting:

```xml
<filter id="diffuse_light">
  <feDiffuseLighting lighting-color="white" surfaceScale="10">
    <fePointLight x="50" y="50" z="100"/>
  </feDiffuseLighting>
  <feComposite in="SourceGraphic" operator="arithmetic"
               k1="1" k2="0" k3="0" k4="0"/>
</filter>
```

---

## Filter Gallery

### Sepia Effect

```xml
<filter id="sepia">
  <feColorMatrix type="matrix"
                 values="0.393 0.769 0.189 0 0
                         0.349 0.686 0.168 0 0
                         0.272 0.534 0.131 0 0
                         0 0 0 1 0"/>
</filter>
```

### Edge Detection

```xml
<filter id="edges">
  <feConvolveMatrix
    kernelMatrix="1 0 -1
                  0 0 0
                  -1 0 1"/>
</filter>
```

### Motion Blur

```xml
<filter id="motion_blur">
  <feGaussianBlur stdDeviation="10 0"/>
</filter>
```

---

## Performance Tips

### Recommended Values

| Filter | Parameter | Light | Medium | Heavy |
|--------|-----------|-------|--------|-------|
| Blur | `stdDeviation` | 1-2 | 3-5 | 6-10 |
| Shadow | `dx`, `dy` | 1-2 | 3-5 | 6-10 |
| Shadow | `stdDeviation` | 1 | 2-3 | 4-5 |

### Optimization

- **Pre-filter when possible** - Apply filters in your design tool before export
- **Use native effects** - PowerPoint native effects (blur, shadow) are fastest
- **Batch elements** - Group similar elements with same filter

---

## Examples Collection

### Business Card with Shadow

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="400" height="250">
  <defs>
    <filter id="card_shadow">
      <feDropShadow dx="4" dy="4" stdDeviation="3"
                    flood-color="#000000" flood-opacity="0.3"/>
    </filter>
  </defs>

  <rect x="50" y="50" width="300" height="150"
        fill="white" stroke="#CCCCCC" stroke-width="2"
        filter="url(#card_shadow)"/>
  <text x="200" y="110" text-anchor="middle"
        font-size="24" font-weight="bold">
    Your Name
  </text>
  <text x="200" y="140" text-anchor="middle"
        font-size="16" fill="#666666">
    your.email@example.com
  </text>
</svg>
```

### Glowing Button

```xml
<svg xmlns="http://www.w3.org/2000/svg" width="300" height="150">
  <defs>
    <filter id="button_glow">
      <feGaussianBlur stdDeviation="5" result="blur"/>
      <feFlood flood-color="#00BFFF" flood-opacity="0.6"/>
      <feComposite in2="blur" operator="in"/>
      <feMerge>
        <feMergeNode/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <rect x="75" y="50" width="150" height="50" rx="10"
        fill="#0099FF" filter="url(#button_glow)"/>
  <text x="150" y="82" text-anchor="middle"
        font-size="20" font-weight="bold" fill="white">
    CLICK ME
  </text>
</svg>
```

---

## FAQ

### Q: Do I need to do anything special to enable filters?

**A**: No! Filters work automatically. Just include them in your SVG and SVG2PPTX handles the rest.

### Q: Will my filters work in all PowerPoint versions?

**A**: Most common filters (blur, shadow) work in PowerPoint 2016+. Complex filters may use approximations.

### Q: Can I use filters with animations?

**A**: Yes! Filters and animations work together. Apply filters first, animate second.

### Q: How do I debug filters?

**A**: Enable element tracer for detailed pipeline tracking:
```python
from core.debug.element_tracer import enable_tracing
enable_tracing()
```

### Q: What if a filter doesn't render?

**A**: Check logs for warnings. Some complex filters may fall back to simpler approximations.

---

## Next Steps

- **Try Examples**: Start with the simple examples above
- **Experiment**: Adjust parameters to see what works best
- **Test**: Always test in PowerPoint to verify results
- **Share**: Found a cool filter effect? Share it with the community!

---

## Additional Resources

- [SVG Filter Effects Specification](https://www.w3.org/TR/filter-effects/)
- [MDN Web Docs: SVG Filters](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/filter)
- [Filter Effects Cheat Sheet](https://yoksel.github.io/svg-filters/)

---

**Happy Filtering!** 🎨✨

*SVG2PPTX - Transform your SVGs into beautiful presentations*
