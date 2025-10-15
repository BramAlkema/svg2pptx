import io
import zipfile

from core.pipeline.converter import CleanSlateConverter


def test_gaussian_blur_converts_to_effect(tmp_path):
    svg = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>
      <defs>
        <filter id='blur1'>
          <feGaussianBlur stdDeviation='2'/>
        </filter>
      </defs>
      <rect id='rect1' x='10' y='10' width='30' height='30' filter='url(#blur1)'/>
    </svg>"""

    converter = CleanSlateConverter()
    result = converter.convert_string(svg)

    pptx_bytes = io.BytesIO(result.output_data)
    with zipfile.ZipFile(pptx_bytes) as pptx:
        slide_xml = pptx.read('ppt/slides/slide1.xml').decode('utf-8')

    assert '<a:effectLst>' in slide_xml
    assert '<a:blur' in slide_xml
