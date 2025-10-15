from pipeline.path_pipeline import PathPipeline


def test_path_pipeline_generates_pptx():
    svg_content = """
    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32">
        <path d="M4 4 L28 4 L28 28 L4 28 Z" fill="none" stroke="black" />
    </svg>
    """

    pipeline = PathPipeline()
    result = pipeline.convert_svg_to_pptx(svg_content)

    assert result.success is True
    assert result.pptx_bytes
    assert len(result.pptx_bytes) > 0
    assert result.element_count > 0
