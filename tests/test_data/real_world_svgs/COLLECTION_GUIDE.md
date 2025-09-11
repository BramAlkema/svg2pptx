# Real-World SVG Collection Guide

This guide helps you collect SVG files from various design tools for E2E testing.

## Figma Export Process

1. **Access Figma Community Files**:
   - Visit [Figma Community](https://www.figma.com/community)
   - Search for icon sets, illustrations, or UI kits
   - Open files that contain diverse SVG elements

2. **Export SVGs from Figma**:
   - Select individual elements or frames
   - Right-click → "Copy/Paste" → "Copy as SVG"
   - Or use File → Export → SVG
   - Save with descriptive names

3. **Recommended Figma Sources**:
   - Lucide Icons: Clean, minimal icons
   - Heroicons: Tailwind CSS icons
   - Material Design Icons: Google's icon set
   - Feather Icons: Simple, elegant icons

## Adobe Illustrator Export

1. **Create or Open Designs**:
   - Use existing artwork or create test designs
   - Include various shapes, paths, text, and effects

2. **Export Process**:
   - File → Export → Export As
   - Choose SVG format
   - Use "SVG 1.1" profile for compatibility
   - Include CSS properties inline

## Inkscape Export

1. **Community Artwork**:
   - Visit [Inkscape Gallery](https://inkscape.org/gallery/)
   - Download source files
   - Open in Inkscape and export as SVG

2. **Export Settings**:
   - File → Save As → Plain SVG
   - Ensure paths are not simplified
   - Include text as text (not paths)

## Web-Based SVG Sources

1. **Icon Libraries**:
   - [Heroicons](https://heroicons.com/) - Download SVG
   - [Feather Icons](https://feathericons.com/) - Copy SVG code
   - [Material Icons](https://fonts.google.com/icons) - Download SVG

2. **SVG Collections**:
   - [SVG Repo](https://www.svgrepo.com/) - Free SVG downloads
   - [OpenClipart](https://openclipart.org/) - Public domain artwork

## Organization Tips

1. **Categorize by Complexity**:
   - Simple: Basic shapes, single colors
   - Medium: Gradients, text, multiple elements
   - Complex: Filters, animations, complex paths

2. **Name Descriptively**:
   - Include source tool: `figma_icon_home.svg`
   - Include complexity: `complex_illustration_landscape.svg`
   - Include features: `gradient_button_rounded.svg`

3. **Document Sources**:
   - Keep track of original URLs
   - Note licensing information
   - Record export settings used

## Usage with Collection Script

```bash
# Add files from a directory
python tools/collect_real_world_svgs.py --directory ~/Downloads/figma_exports --source figma

# Add individual file
python tools/collect_real_world_svgs.py --file icon.svg --source illustrator --description "Material design icon"

# Collect from GitHub repository
python tools/collect_real_world_svgs.py --github https://github.com/tailwindlabs/heroicons
```

## Target Collection Goals

- **50+ unique SVG files** from different sources
- **Representation from each major tool**: Figma, Illustrator, Inkscape, Web
- **Variety in complexity**: Simple icons to complex illustrations
- **Coverage of all converter modules**: Shapes, paths, text, gradients, etc.

