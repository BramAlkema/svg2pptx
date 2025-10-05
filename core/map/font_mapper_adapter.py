"""
FontMapperAdapter - Bridge between TextMapper interface and SmartFontConverter
Integrates the isolated FontHandler system into the main pipeline.
"""

from ..ir import IRElement
from .base import Mapper, MapperResult

try:
    from ..converters.font.smart_converter import SmartFontConverter
    SMART_CONVERTER_AVAILABLE = True
except ImportError:
    SMART_CONVERTER_AVAILABLE = False
    SmartFontConverter = None

class FontMapperAdapter(Mapper):
    """Adapter that integrates SmartFontConverter into the mapper interface"""

    def __init__(self, policy, services=None):
        super().__init__(policy)
        self.services = services

        if SMART_CONVERTER_AVAILABLE and services:
            try:
                self.smart_converter = SmartFontConverter(services, policy)
                self.use_smart_converter = True
            except Exception as e:
                print(f"Warning: Could not initialize SmartFontConverter: {e}")
                self.use_smart_converter = False
        else:
            self.use_smart_converter = False

        # Always create fallback mapper for robustness
        from .text_mapper import TextMapper
        self.fallback_mapper = TextMapper(policy, services)

    def can_map(self, ir_element: IRElement) -> bool:
        """Check if this mapper can handle the element"""
        return hasattr(ir_element, 'element_type') and ir_element.element_type == 'textframe'

    def map(self, ir_element: IRElement) -> MapperResult:
        """Map TextFrame using SmartFontConverter or fallback"""

        if self.use_smart_converter:
            try:
                # Convert RichTextFrame to TextFrame if needed
                from ..ir import RichTextFrame
                if isinstance(ir_element, RichTextFrame):
                    ir_element = ir_element.to_text_frame()

                # Use advanced font processing
                # SmartFontConverter expects TextFrame and context dict
                context = {'services': self.services, 'policy': self.policy}
                result = self.smart_converter.convert(ir_element, context)
                # Convert FontConversionResult to MapperResult
                from ..policy import DecisionReason, PolicyDecision
                from .base import OutputFormat

                return MapperResult(
                    element=ir_element,
                    output_format=OutputFormat.NATIVE_DML,
                    xml_content=result.drawingml_xml,
                    policy_decision=PolicyDecision(
                        use_native=True,
                        reasons=[DecisionReason.SIMPLE_SHAPE],  # Using simple shape as default
                        confidence=result.confidence,
                    ),
                    metadata={
                        'strategy': str(result.strategy_used),
                        'confidence': result.confidence,
                        'complexity': str(result.complexity) if result.complexity else None,
                        'font_available': result.font_available,
                    },
                    estimated_quality=result.confidence,
                    processing_time_ms=result.total_time_ms,
                )
            except Exception as e:
                print(f"SmartFontConverter failed, using fallback: {e}")
                # Fall through to fallback

        # Use fallback TextMapper
        return self.fallback_mapper.map(ir_element)
