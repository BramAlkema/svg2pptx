# License Attribution for SVG Preprocessing Components

## SVGO Attribution

This preprocessing system includes algorithms and approaches ported from the SVGO project.

### Original SVGO Project
- **Repository**: https://github.com/svg/svgo
- **License**: MIT License
- **Copyright**: SVG Working Group Community
- **Version Referenced**: 4.0.0+

### MIT License (SVGO)
```
MIT License

Copyright (c) 2012-2024 SVG Working Group Community

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### Ported Components

The following components in our preprocessing system are directly ported or heavily inspired by SVGO plugins:

#### Core Plugins (from SVGO)
- `CleanupAttrsPlugin` ← `cleanupAttrs`
- `CleanupNumericValuesPlugin` ← `cleanupNumericValues`
- `RemoveEmptyAttrsPlugin` ← `removeEmptyAttrs`
- `RemoveEmptyContainersPlugin` ← `removeEmptyContainers`
- `RemoveCommentsPlugin` ← `removeComments`
- `ConvertColorsPlugin` ← `convertColors`
- `RemoveUnusedNamespacesPlugin` ← `removeUnusedNS`
- `ConvertShapeToPathPlugin` ← `convertShapeToPath`

#### Advanced Plugins (from SVGO)
- `ConvertPathDataPlugin` ← `convertPathData`
- `MergePathsPlugin` ← `mergePaths`
- `ConvertTransformPlugin` ← `convertTransform`
- `RemoveUselessStrokeAndFillPlugin` ← `removeUselessStrokeAndFill`
- `RemoveHiddenElementsPlugin` ← `removeHiddenElems`
- `MinifyStylesPlugin` ← `minifyStyles`
- `SortAttributesPlugin` ← `sortAttrs`
- `RemoveUnknownsAndDefaultsPlugin` ← `removeUnknownsAndDefaults`

#### Geometry Plugins (from SVGO)
- `ConvertEllipseToCirclePlugin` ← `convertEllipseToCircle`
- `CollapseGroupsPlugin` ← `collapseGroups`
- `ConvertStyleToAttrsPlugin` ← `convertStyleToAttrs`
- `RemoveEmptyDefsPlugin` ← `removeUselessDefs`
- `SimplifyPolygonPlugin` ← Enhanced from SVGO polygon handling

### Our Enhancements

The following components are original implementations that extend beyond SVGO:

#### Advanced Geometry Processing (Original)
- `geometry_simplify.py` - Ramer-Douglas-Peucker algorithm implementation
- `AdvancedPathSimplificationPlugin` - RDP-based path optimization
- `AdvancedPolygonSimplificationPlugin` - Enhanced polygon processing
- `CubicSmoothingPlugin` - Catmull-Rom curve generation
- `GeometryOptimizationStatsPlugin` - Performance monitoring

#### PowerPoint-Specific Optimizations (Original)
- EMU coordinate system integration
- PowerPoint compatibility enhancements
- Modular converter architecture integration
- API configuration system

### Acknowledgment

We gratefully acknowledge the SVGO project and its contributors for establishing the industry standards and best practices for SVG optimization that our system builds upon. SVGO's open-source approach has enabled the entire web development community to benefit from sophisticated SVG optimization techniques.

Our implementation adapts these proven algorithms for the specific use case of SVG-to-PowerPoint conversion while adding advanced geometry processing capabilities that go beyond traditional web optimization needs.