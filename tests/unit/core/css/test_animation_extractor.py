from lxml import etree as ET

from core.css import StyleResolver, StyleContext
from core.css.animation_extractor import CSSAnimationExtractor
from core.units.core import UnitConverter


def _make_context() -> StyleContext:
    converter = UnitConverter()
    conversion = converter.create_context(
        width=200.0,
        height=100.0,
        font_size=12.0,
        dpi=96.0,
        parent_width=200.0,
        parent_height=100.0,
    )
    return StyleContext(
        conversion=conversion,
        viewport_width=200.0,
        viewport_height=100.0,
    )


def test_extracts_opacity_animation_from_css():
    svg = """<svg xmlns='http://www.w3.org/2000/svg'>
      <style>
      @keyframes fade {
        from { opacity: 0; }
        to { opacity: 1; }
      }
      rect { animation-name: fade; animation-duration: 2s; }
      </style>
      <rect id='box' x='0' y='0' width='10' height='10'/>
    </svg>"""

    root = ET.fromstring(svg)
    context = _make_context()
    extractor = CSSAnimationExtractor(StyleResolver(UnitConverter()))

    animations = extractor.extract(root, context)

    opacity_anim = next((a for a in animations if a.target_attribute == "opacity"), None)
    assert opacity_anim is not None
    assert opacity_anim.element_id == "box"
    assert opacity_anim.values == ["0.0", "1.0"]
    assert opacity_anim.timing.duration == 2.0


def test_extracts_transform_animation_from_css():
    svg = """<svg xmlns='http://www.w3.org/2000/svg'>
      <style>
      @keyframes move {
        from { transform: translate(0,0); }
        to { transform: translate(100,50); }
      }
      rect { animation-name: move; animation-duration: 1s; }
      </style>
      <rect id='box' x='0' y='0' width='10' height='10'/>
    </svg>"""

    root = ET.fromstring(svg)
    context = _make_context()
    extractor = CSSAnimationExtractor(StyleResolver(UnitConverter()))

    animations = extractor.extract(root, context)

    transform_anim = next((a for a in animations if a.target_attribute == "transform"), None)
    assert transform_anim is not None
    assert transform_anim.transform_type is not None
    assert transform_anim.values == ["0 0", "100 50"]


def test_extracts_multiple_properties_when_keyframes_have_both():
    svg = """<svg xmlns='http://www.w3.org/2000/svg'>
      <style>
      @keyframes moveAndFade {
        from { transform: translate(0,0); opacity: 0; }
        to { transform: translate(50,0); opacity: 1; }
      }
      rect { animation-name: moveAndFade; animation-duration: 1s; }
      </style>
      <rect id='box' x='0' y='0' width='10' height='10'/>
    </svg>"""

    root = ET.fromstring(svg)
    context = _make_context()
    extractor = CSSAnimationExtractor(StyleResolver(UnitConverter()))

    animations = extractor.extract(root, context)

    assert any(a.target_attribute == "opacity" for a in animations)
    transform_anims = [a for a in animations if a.target_attribute == "transform"]
    assert len(transform_anims) == 1
    assert transform_anims[0].values == ["0 0", "50 0"]
