import io
import zipfile

from lxml import etree as ET

from core.pipeline.converter import CleanSlateConverter


def test_pipeline_embeds_animation_timing_xml(tmp_path):
    svg = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>
      <style>
        @keyframes slide {
          from { transform: translate(0,0); }
          to { transform: translate(30,0); }
        }
        #rect2 { animation-name: slide; animation-duration: 1s; }
      </style>
      <rect id='rect1' x='10' y='10' width='20' height='20'>
        <animate attributeName='opacity' values='0;1' dur='2s'/>
        <animateMotion dur='2s' values='0,0;100,0;100,100'/>
      </rect>
      <rect id='rect2' x='40' y='40' width='20' height='20'>
        <animate attributeName='fill' values='#ff0000;#00ff00;#0000ff' dur='3s'/>
      </rect>
    </svg>"""

    converter = CleanSlateConverter()
    result = converter.convert_string(svg)

    pptx_bytes = io.BytesIO(result.output_data)
    with zipfile.ZipFile(pptx_bytes) as pptx:
        slide_xml = pptx.read('ppt/slides/slide1.xml').decode('utf-8')

    assert '<p:timing' in slide_xml
    assert result.animation_count == 4

    ns = {
        'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    }
    root = ET.fromstring(slide_xml)

    sp_tgts = {elem.get('spid') for elem in root.findall('.//a:spTgt', ns)}
    shape_ids = {elem.get('id') for elem in root.findall('.//p:cNvPr', ns)}

    assert sp_tgts
    assert sp_tgts.issubset(shape_ids)
    assert '<a:srgbClr' in slide_xml
    assert '<a:ptLst>' in slide_xml
