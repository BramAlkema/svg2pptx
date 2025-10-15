from lxml import etree as ET

from core.converters.animation_converter import AnimationConverter


def test_animation_converter_generates_timing_xml():
    svg = """<svg xmlns='http://www.w3.org/2000/svg'>
      <rect id='r1' x='0' y='0' width='10' height='10'>
        <animate attributeName='opacity' values='0;1' dur='2s'/>
      </rect>
    </svg>"""

    converter = AnimationConverter()
    result = converter.convert_svg_animations(ET.fromstring(svg))

    assert result.success is True
    assert result.summary.total_animations == 1
    assert '<p:timing' in result.powerpoint_xml
    assert result.timeline_scenes

    ppt_with_mapping = converter.build_powerpoint_xml(result, {'r1': ['5']})
    assert '<a:spTgt spid="5"' in ppt_with_mapping
    assert '<a:tav' in ppt_with_mapping


def test_animation_converter_color_uses_keyframes():
    svg = """<svg xmlns='http://www.w3.org/2000/svg'>
      <rect id='c1' x='0' y='0' width='10' height='10'>
        <animate attributeName='fill' values='#ff0000;#00ff00;#0000ff' dur='3s'/>
      </rect>
    </svg>"""

    converter = AnimationConverter()
    result = converter.convert_svg_animations(ET.fromstring(svg))

    ppt_xml = converter.build_powerpoint_xml(result, {'c1': ['7']})
    assert '<a:spTgt spid="7"' in ppt_xml
    assert ppt_xml.count('<a:srgbClr') >= 3
    assert ppt_xml.count('<a:tav tm="') >= 3


def test_animation_converter_motion_builds_point_list():
    svg = """<svg xmlns='http://www.w3.org/2000/svg'>
      <rect id='m1' x='0' y='0' width='10' height='10'>
        <animateMotion dur='2s' values='0,0;100,0;100,100'/>
      </rect>
    </svg>"""

    converter = AnimationConverter()
    result = converter.convert_svg_animations(ET.fromstring(svg))

    ppt_xml = converter.build_powerpoint_xml(result, {'m1': ['9']})
    assert '<a:spTgt spid="9"' in ppt_xml
    assert '<a:ptLst>' in ppt_xml
    assert ppt_xml.count('<a:pt tm="') >= 2
