from lxml import etree as ET

from core.services.pattern_service import PatternService


def test_pattern_service_detects_image_pattern():
    pattern_xml = """<pattern xmlns='http://www.w3.org/2000/svg' id='p' width='10' height='10'>
      <image xmlns:xlink='http://www.w3.org/1999/xlink' xlink:href='rIdImg' width='10' height='10'/>
    </pattern>"""
    pattern_service = PatternService()
    pattern_service.register_pattern('p', ET.fromstring(pattern_xml))

    content = pattern_service.get_pattern_content('#p')

    assert content is not None
    assert '<a:blipFill' in content
    assert 'rIdImg' in content


def test_pattern_service_detects_vertical_lines():
    pattern_xml = """<pattern xmlns='http://www.w3.org/2000/svg' id='p' width='10' height='10'>
      <line x1='5' y1='0' x2='5' y2='10' stroke='#112233'/>
    </pattern>"""
    pattern_service = PatternService()
    pattern_service.register_pattern('p', ET.fromstring(pattern_xml))

    content = pattern_service.get_pattern_content('#p')

    assert content is not None
    assert "prst='vert'" in content
    assert '112233' in content
