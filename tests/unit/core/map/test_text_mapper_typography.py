from core.ir.font_metadata import create_font_metadata
from core.ir.text import EnhancedRun
from core.map.text_mapper import TextMapper
from core.policy.engine import Policy
from core.services.conversion_services import ConversionServices


def test_text_mapper_applies_typography_metadata():
    policy = Policy()
    services = ConversionServices.create_default()
    policy.services = services
    mapper = TextMapper(policy, services=services)

    metadata = create_font_metadata(
        'Inter',
        size_pt=14,
        variation_settings={'wght': 500},
        feature_settings=['liga', 'kern'],
        kerning=False,
    )

    run = EnhancedRun(
        text='Test',
        font_family='Inter',
        font_size_pt=14,
        font_metadata=metadata,
        letter_spacing=0.2,
    )

    xml = mapper._generate_run_xml(run)

    assert 'kern="0"' in xml
    assert "spc=" in xml
    assert 'svg2pptx:variations' in xml
    assert 'svg2pptx:features' in xml
