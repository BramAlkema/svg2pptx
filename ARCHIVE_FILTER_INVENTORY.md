# Archive Filter Inventory

## ✅ Complete Filter Implementations Found in Archive

### Image Filters (`/archive/legacy-src/converters/filters/image/`)

1. **blur.py**
   - `GaussianBlurFilter` - feGaussianBlur implementation
   - `MotionBlurFilter` - Motion blur variant

2. **color.py**
   - `ColorMatrixFilter` - feColorMatrix implementation
   - `FloodFilter` - feFlood implementation ✨
   - `LightingFilter` - Base lighting filter

3. **convolve_matrix.py**
   - `ConvolveMatrixFilter` - feConvolveMatrix implementation

### Geometric Filters (`/archive/legacy-src/converters/filters/geometric/`)

4. **component_transfer.py**
   - `ComponentTransferFilter` - feComponentTransfer implementation

5. **composite.py**
   - `CompositeFilter` - feComposite implementation
   - `MergeFilter` - feMerge implementation
   - `BlendFilter` - feBlend implementation

6. **diffuse_lighting.py**
   - `DiffuseLightingFilter` - feDiffuseLighting implementation

7. **displacement_map.py**
   - `DisplacementMapFilter` - feDisplacementMap implementation

8. **morphology.py**
   - `MorphologyFilter` - feMorphology implementation

9. **specular_lighting.py**
   - `SpecularLightingFilter` - feSpecularLighting implementation

10. **tile.py**
    - `TileFilter` - feTile implementation

11. **transforms.py**
    - `OffsetFilter` - feOffset implementation ✨
    - `TurbulenceFilter` - feTurbulence implementation ✨

### Core Infrastructure (`/archive/legacy-src/converters/filters/core/`)

- **base.py** - Base Filter class and FilterContext
- **registry.py** - FilterRegistry for managing filters
- **chain.py** - FilterChain for composing filters
- **converter.py** - FilterConverter for integration

### Utilities (`/archive/legacy-src/converters/filters/utils/`)

- **parsing.py** - FilterPrimitiveParser for SVG parsing

## Coverage Summary

### ✅ **Found in Archive (15/16)**
1. feBlend ✅ (BlendFilter)
2. feColorMatrix ✅ (ColorMatrixFilter)
3. feComponentTransfer ✅ (ComponentTransferFilter)
4. feComposite ✅ (CompositeFilter)
5. feConvolveMatrix ✅ (ConvolveMatrixFilter)
6. feDiffuseLighting ✅ (DiffuseLightingFilter)
7. feDisplacementMap ✅ (DisplacementMapFilter)
8. feFlood ✅ (FloodFilter)
9. feGaussianBlur ✅ (GaussianBlurFilter)
10. feMerge ✅ (MergeFilter)
11. feMorphology ✅ (MorphologyFilter)
12. feOffset ✅ (OffsetFilter)
13. feSpecularLighting ✅ (SpecularLightingFilter)
14. feTile ✅ (TileFilter)
15. feTurbulence ✅ (TurbulenceFilter)

### ❌ **Not Found (1/16)**
16. feImage - No dedicated class found (likely needs implementation)

## Key Discoveries

1. **feFlood IS implemented** - Found `FloodFilter` class in color.py
2. **feOffset IS implemented** - Found `OffsetFilter` class in transforms.py
3. **feTurbulence IS implemented** - Found `TurbulenceFilter` class in transforms.py
4. **Only feImage is missing** - No dedicated implementation found

## Migration Priority (Revised)

### Immediate Quick Wins (Simple)
1. **feOffset** - Already in archive, simple transform
2. **feFlood** - Already in archive, solid color fill

### High Priority (Common Usage)
3. **feBlend** - Critical for layer compositing
4. **feColorMatrix** - Color adjustments
5. **feComposite** - Advanced compositing

### Medium Priority
6. **feMorphology** - Erosion/dilation effects
7. **feComponentTransfer** - Color curves
8. **feConvolveMatrix** - Kernel filters

### Low Priority (Complex/Rare)
9. **feDisplacementMap** - Complex warping
10. **feTurbulence** - Noise generation
11. **feTile** - Pattern tiling
12. **feImage** - Needs new implementation

## Actual Coverage

- **Currently in Core**: 5/16 (31.25%)
- **Available in Archive**: 15/16 (93.75%) 🎉
- **Total Achievable**: 15/16 (93.75%) with migrations
- **Needs Implementation**: 1/16 (6.25%) - only feImage