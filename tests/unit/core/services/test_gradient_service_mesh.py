from lxml import etree as ET

from core.services.gradient_service import GradientService


def test_mesh_gradient_falls_back_to_gradfill_when_engine_missing():
    mesh_svg = """<meshgradient xmlns='http://www.w3.org/2000/svg' id='mesh1'>
      <stop offset='0' stop-color='#ff0000'/>
      <stop offset='1' stop-color='#0000ff'/>
    </meshgradient>"""

    service = GradientService()
    service.register_gradient('mesh1', ET.fromstring(mesh_svg))

    content = service.get_gradient_content('#mesh1')

    assert content is not None
    assert '<a:gradFill>' in content
    assert 'FF0000' in content.upper()
    assert '0000FF' in content.upper()
