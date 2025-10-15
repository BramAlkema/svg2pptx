from lxml import etree as ET

from core.ir.geometry import Point, Rect
from core.ir.text import Run, TextAnchor, TextFrame
from core.map.text_mapper import TextMapper
from core.policy.engine import Policy
from core.policy.targets import TextDecision
from core.services.conversion_services import ConversionServices


import pytest


@pytest.fixture(scope="module")
def services():
    return ConversionServices.create_default()


def _build_text_frame() -> TextFrame:
    return TextFrame(
        origin=Point(0, 0),
        anchor=TextAnchor.START,
        bbox=Rect(0, 0, 200000, 50000),
        runs=[Run(text="Hello", font_family="Arial", font_size_pt=18)],
    )


def test_apply_warp_preset_injects_prst_element(services):
    policy = Policy()
    policy.services = services
    mapper = TextMapper(policy, services=services)
    frame = _build_text_frame()
    xml = mapper._generate_standard_text_xml(frame)

    decision = TextDecision.wordart(
        preset="textWave1",
        parameters={},
        confidence=0.9,
    )

    warped_xml = mapper._apply_warp_preset(xml, decision)

    root = ET.fromstring(warped_xml)
    ns = {'a': "http://schemas.openxmlformats.org/drawingml/2006/main"}
    warp = root.find('.//a:prstTxWarp', ns)

    assert warp is not None
    assert warp.get('prst') == 'textWave1'


def test_apply_warp_preset_writes_parameters(services):
    policy = Policy()
    policy.services = services
    mapper = TextMapper(policy, services=services)
    frame = _build_text_frame()
    xml = mapper._generate_standard_text_xml(frame)

    decision = TextDecision.wordart(
        preset="textArchUp",
        parameters={'warpT': 12000},
        confidence=0.9,
    )

    warped_xml = mapper._apply_warp_preset(xml, decision)

    root = ET.fromstring(warped_xml)
    ns = {'a': "http://schemas.openxmlformats.org/drawingml/2006/main"}
    gd = root.find('.//a:prstTxWarp/a:avLst/a:gd', ns)

    assert gd is not None
    assert gd.get('name') == 'warpT'
    assert gd.get('fmla') == 'val 12000'
