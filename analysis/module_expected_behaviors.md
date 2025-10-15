# Expected Behaviors – Module Slicing Targets

## core.parse.parser
- **Fixture:** `testing/fixtures/module_slicing/parser/basic_shapes.svg`
- **Expectations:**
  - Generates IR elements for rectangle, circle (with gradient fill), and path with clip-path applied.
  - Emits hyperlink metadata for the anchor-wrapped text run.
  - Preserves `foreignObject` nodes by flagging them for fallback rendering.
  - Records gradient/pattern definitions in the extracted resources table.
  - Produces navigation annotations for text nodes when hyperlinks are encountered.

## core.utils.enhanced_xml_builder
- **Fixtures:** template stub loader (`core/io/template_loader.py` fallback)
- **Expectations:**
  - `_validate_templates` loads each critical template without raising.
  - `create_presentation_element` rewrites slide and notes dimensions from inputs.
  - `add_slide_to_presentation` appends `<p:sldId>` entries with incrementing IDs.
  - Fluent API (`create_shape(...).position(...).size(...).geometry(...)`) injects geometry into `p:spTree`.
  - Path/text/image generator helpers produce elements containing the appropriate namespace-qualified child nodes (e.g., `<a:custGeom>`, `<a:blip>` placeholders).

## core.viewbox.core
- **Fixture:** `testing/fixtures/module_slicing/viewbox/preserve_aspect_ratio.svg`
- **Expectations:**
  - `parse_viewbox_strings` returns a structured array with the expected aspect ratio (2.0 for 200×100 viewBox).
  - `parse_preserve_aspect_ratio_batch` maps `xMidYMid meet` to alignment index 4 and MEET scaling.
  - `batch_resolve_svg_viewports` converts 400×200 pixel dimensions to EMU using the default `UnitConverter`, preserving center alignment with no clipping.
  - Fluent chain `ViewportEngine().for_svg(svg).with_slide_size(...).center().meet().resolve_single()` yields translate offsets that keep the content centered within the slide bounds.
