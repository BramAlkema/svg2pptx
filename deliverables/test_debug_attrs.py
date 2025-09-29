#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.svg2pptx import convert_svg_to_pptx

result = convert_svg_to_pptx('deliverables/test_complex_paths.svg', 'deliverables/debug_attrs_output.pptx')
print('Conversion completed')