import json

from core.pipeline.config import PipelineConfig, OutputFormat
from core.pipeline.converter import CleanSlateConverter


def test_clean_slate_converter_debug_json():
    config = PipelineConfig.create_debug()
    config.output_format = OutputFormat.DEBUG_JSON
    converter = CleanSlateConverter(config=config)

    svg_content = """
    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48">
        <rect x="4" y="4" width="40" height="40" fill="#0080ff" stroke="#000000" />
        <circle cx="24" cy="24" r="12" fill="#ffffff" />
    </svg>
    """

    result = converter.convert_string(svg_content)
    assert result.output_data
    payload = json.loads(result.output_data.decode("utf-8"))
    assert payload["analysis"]["element_count"] >= 1
    assert payload["embedding"]["elements_embedded"] >= 1
