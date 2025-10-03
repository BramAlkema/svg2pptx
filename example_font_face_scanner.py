#!/usr/bin/env python3
"""
Example: Using FontFaceScanner for advanced font extraction

Demonstrates:
1. Scanning inline <style> blocks
2. Scanning external <link rel="stylesheet"> (if file exists)
3. Fallback to multiple src items
4. Indexing fonts by (family, weight, style)
"""

from core.fonts import FontFaceScanner

# Example SVG with inline @font-face
svg = """<svg xmlns="http://www.w3.org/2000/svg">
  <defs>
    <style>
      @font-face {
        font-family: "Inter";
        font-style: normal;
        font-weight: 400;
        src: url("fonts/Inter-Regular.woff2") format("woff2"),
             url("fonts/Inter-Regular.ttf") format("truetype");
      }
      @font-face {
        font-family: "Inter";
        font-style: normal;
        font-weight: 700;
        src: url("fonts/Inter-Bold.woff2") format("woff2"),
             url("fonts/Inter-Bold.ttf") format("truetype");
      }
    </style>
  </defs>
  <text font-family="Inter" font-weight="400">Regular Text</text>
  <text font-family="Inter" font-weight="700">Bold Text</text>
</svg>"""

def main():
    print("=" * 60)
    print("FontFaceScanner Example")
    print("=" * 60)

    # Create scanner (allow_remote=False for safety)
    scanner = FontFaceScanner(allow_remote=False)

    # Scan SVG
    print("\nScanning SVG for @font-face rules...")
    report = scanner.scan_svg_string(svg, base_dir=".")

    # Report findings
    print(f"\nFound {len(report.fonts)} font face(s)")
    print(f"Unique fonts (deduplicated): {len(report.dedup_sha256)}")

    # Show each font
    for i, scanned in enumerate(report.fonts, 1):
        rule = scanned.rule
        asset = scanned.asset
        error = scanned.error

        print(f"\n[{i}] Font Face:")
        print(f"  Family: {rule.family}")
        print(f"  Weight: {rule.weight}")
        print(f"  Style: {rule.style}")
        print(f"  Sources: {len(rule.src_items)}")
        for url, fmt in rule.src_items:
            print(f"    - {url} (format: {fmt or 'auto'})")

        if asset:
            print(f"  ✅ Normalized:")
            print(f"     Format: {asset.flavor} (original: {asset.original_format})")
            print(f"     Size: {len(asset.embeddable_bytes)} bytes")
            print(f"     SHA-256: {asset.sha256[:16]}...")
        else:
            print(f"  ❌ Failed: {error}")

    # Show indexes
    if report.by_key:
        print("\n" + "=" * 60)
        print("Font Index by (family, weight, style)")
        print("=" * 60)
        for key, asset in report.by_key.items():
            fam, weight, style = key
            print(f"  ({fam}, {weight}, {style}) → {asset.flavor} {len(asset.embeddable_bytes)} bytes")

    if report.by_family:
        print("\n" + "=" * 60)
        print("Font Index by Family")
        print("=" * 60)
        for family, assets in report.by_family.items():
            print(f"  {family}: {len(assets)} variant(s)")
            for asset in assets:
                print(f"    - {asset.subfamily or 'Regular'} ({asset.flavor})")

    # Show errors
    if report.errors:
        print("\n" + "=" * 60)
        print("Errors/Warnings")
        print("=" * 60)
        for err in report.errors:
            print(f"  ⚠️  {err}")

    print("\n" + "=" * 60)
    print("Example Complete")
    print("=" * 60)

    # Usage example
    print("\nUsage Example:")
    print("```python")
    print("# Lookup font by (family, weight, style)")
    print("asset = report.by_key.get(('inter', '400', 'normal'))")
    print("if asset:")
    print("    font_bytes = asset.embeddable_bytes  # TTF or OTF")
    print("    embed_into_pptx(font_bytes, asset.family)")
    print("```")


if __name__ == "__main__":
    main()
