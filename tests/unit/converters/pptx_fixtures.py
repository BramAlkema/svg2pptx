#!/usr/bin/env python3
"""
PPTX validation fixtures for missing SVG elements testing.

Provides expected PPTX output structures and validation schemas for testing
the conversion of missing SVG elements to PowerPoint DrawingML format.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import json


class PPTXShapeType(Enum):
    """PPTX shape types for DrawingML elements"""
    FREEFORM = "freeform"
    PICTURE = "picture" 
    TEXTBOX = "textbox"
    SHAPE_WITH_EFFECT = "shape_with_effect"
    GROUP = "group"
    CONNECTOR = "connector"


class PPTXEffectType(Enum):
    """PPTX effect types"""
    DROP_SHADOW = "drop_shadow"
    GLOW = "glow"
    BLUR = "blur"
    REFLECTION = "reflection"


@dataclass
class PPTXColor:
    """PPTX color specification"""
    type: str  # "rgb", "theme", "scheme"
    value: str
    alpha: Optional[float] = None


@dataclass
class PPTXStroke:
    """PPTX stroke properties"""
    color: PPTXColor
    width: float
    dash_type: Optional[str] = None
    cap_type: Optional[str] = None
    join_type: Optional[str] = None


@dataclass
class PPTXFill:
    """PPTX fill properties"""
    type: str  # "solid", "gradient", "pattern", "picture", "none"
    color: Optional[PPTXColor] = None
    pattern_type: Optional[str] = None
    gradient_stops: Optional[List[Dict[str, Any]]] = None


@dataclass
class PPTXPosition:
    """PPTX position coordinates"""
    x: float
    y: float


@dataclass
class PPTXSize:
    """PPTX size dimensions"""
    width: float
    height: float


@dataclass
class PPTXEffect:
    """PPTX effect properties"""
    type: PPTXEffectType
    properties: Dict[str, Any]


@dataclass
class PPTXTextRun:
    """PPTX text run properties"""
    text: str
    font_family: Optional[str] = None
    font_size: Optional[float] = None
    font_weight: Optional[str] = None
    font_style: Optional[str] = None
    color: Optional[PPTXColor] = None


@dataclass
class PPTXShape:
    """Expected PPTX shape output structure"""
    shape_type: PPTXShapeType
    position: PPTXPosition
    size: PPTXSize
    stroke: Optional[PPTXStroke] = None
    fill: Optional[PPTXFill] = None
    effects: List[PPTXEffect] = field(default_factory=list)
    text_runs: List[PPTXTextRun] = field(default_factory=list)
    path_data: Optional[str] = None
    image_data: Optional[str] = None
    transform: Optional[Dict[str, float]] = None
    custom_properties: Dict[str, Any] = field(default_factory=dict)


class PPTXFixtures:
    """PPTX validation fixtures for missing SVG elements"""
    
    @staticmethod
    def polyline_basic() -> PPTXShape:
        """Expected PPTX output for basic polyline"""
        return PPTXShape(
            shape_type=PPTXShapeType.FREEFORM,
            position=PPTXPosition(x=10, y=10),
            size=PPTXSize(width=140, height=30),
            stroke=PPTXStroke(
                color=PPTXColor(type="rgb", value="0000FF"),
                width=2.0,
                cap_type="round",
                join_type="round"
            ),
            fill=PPTXFill(type="none"),
            path_data="M10,10 L50,25 L90,10 L120,40 L150,20"
        )
    
    @staticmethod
    def polyline_complex() -> PPTXShape:
        """Expected PPTX output for complex polyline with styling"""
        return PPTXShape(
            shape_type=PPTXShapeType.FREEFORM,
            position=PPTXPosition(x=0, y=0),
            size=PPTXSize(width=220, height=70),
            stroke=PPTXStroke(
                color=PPTXColor(type="rgb", value="008000"),
                width=3.0,
                cap_type="round",
                join_type="round"
            ),
            fill=PPTXFill(type="none"),
            path_data="M0,0 L10,20 L30,15 L50,40 L80,25 L100,50 L130,35 L160,60 L190,45 L220,70"
        )
    
    @staticmethod
    def tspan_styling() -> PPTXShape:
        """Expected PPTX output for tspan with styling"""
        return PPTXShape(
            shape_type=PPTXShapeType.TEXTBOX,
            position=PPTXPosition(x=50, y=34),
            size=PPTXSize(width=120, height=32),
            text_runs=[
                PPTXTextRun(
                    text="Bold Red",
                    font_family="Arial",
                    font_size=16,
                    font_weight="bold",
                    color=PPTXColor(type="rgb", value="FF0000")
                ),
                PPTXTextRun(
                    text="Italic Blue",
                    font_family="Arial", 
                    font_size=16,
                    font_style="italic",
                    color=PPTXColor(type="rgb", value="0000FF")
                )
            ]
        )
    
    @staticmethod
    def tspan_nested() -> PPTXShape:
        """Expected PPTX output for nested tspan elements"""
        return PPTXShape(
            shape_type=PPTXShapeType.TEXTBOX,
            position=PPTXPosition(x=20, y=24),
            size=PPTXSize(width=160, height=32),
            text_runs=[
                PPTXTextRun(
                    text="Normal ",
                    font_family="Times New Roman",
                    font_size=12
                ),
                PPTXTextRun(
                    text="nested bold red",
                    font_family="Times New Roman",
                    font_size=12,
                    font_weight="bold",
                    color=PPTXColor(type="rgb", value="FF0000")
                ),
                PPTXTextRun(
                    text=" text",
                    font_family="Times New Roman",
                    font_size=12
                )
            ]
        )
    
    @staticmethod
    def image_embedded() -> PPTXShape:
        """Expected PPTX output for embedded image"""
        return PPTXShape(
            shape_type=PPTXShapeType.PICTURE,
            position=PPTXPosition(x=10, y=10),
            size=PPTXSize(width=100, height=80),
            image_data="test.jpg"
        )
    
    @staticmethod
    def image_base64() -> PPTXShape:
        """Expected PPTX output for base64 encoded image"""
        return PPTXShape(
            shape_type=PPTXShapeType.PICTURE,
            position=PPTXPosition(x=50, y=50),
            size=PPTXSize(width=50, height=50),
            image_data="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        )
    
    @staticmethod
    def symbol_use_reusable() -> List[PPTXShape]:
        """Expected PPTX output for symbol with use elements"""
        return [
            PPTXShape(
                shape_type=PPTXShapeType.FREEFORM,
                position=PPTXPosition(x=50, y=50),
                size=PPTXSize(width=30, height=30),
                fill=PPTXFill(
                    type="solid",
                    color=PPTXColor(type="rgb", value="FFD700")
                ),
                path_data="M10,2 L12,8 L18,8 L13,12 L15,18 L10,14 L5,18 L7,12 L2,8 L8,8 Z",
                custom_properties={"symbol_id": "star", "use_instance": 1}
            ),
            PPTXShape(
                shape_type=PPTXShapeType.FREEFORM,
                position=PPTXPosition(x=100, y=100),
                size=PPTXSize(width=20, height=20),
                fill=PPTXFill(
                    type="solid",
                    color=PPTXColor(type="rgb", value="FFD700")
                ),
                path_data="M10,2 L12,8 L18,8 L13,12 L15,18 L10,14 L5,18 L7,12 L2,8 L8,8 Z",
                custom_properties={"symbol_id": "star", "use_instance": 2}
            )
        ]
    
    @staticmethod
    def pattern_dots() -> PPTXShape:
        """Expected PPTX output for dot pattern fill"""
        return PPTXShape(
            shape_type=PPTXShapeType.FREEFORM,
            position=PPTXPosition(x=50, y=50),
            size=PPTXSize(width=100, height=80),
            fill=PPTXFill(
                type="pattern",
                pattern_type="dots",
                color=PPTXColor(type="rgb", value="000000")
            ),
            custom_properties={
                "pattern_width": 20,
                "pattern_height": 20,
                "pattern_units": "userSpaceOnUse"
            }
        )
    
    @staticmethod
    def pattern_stripes() -> PPTXShape:
        """Expected PPTX output for stripe pattern fill"""
        return PPTXShape(
            shape_type=PPTXShapeType.FREEFORM,
            position=PPTXPosition(x=40, y=60),
            size=PPTXSize(width=120, height=80),
            fill=PPTXFill(
                type="pattern", 
                pattern_type="stripes",
                gradient_stops=[
                    {"position": 0, "color": PPTXColor(type="rgb", value="FF0000")},
                    {"position": 0.5, "color": PPTXColor(type="rgb", value="FF0000")},
                    {"position": 0.5, "color": PPTXColor(type="rgb", value="0000FF")},
                    {"position": 1, "color": PPTXColor(type="rgb", value="0000FF")}
                ]
            ),
            custom_properties={
                "pattern_width": 10,
                "pattern_height": 10
            }
        )
    
    @staticmethod
    def filter_gaussian_blur() -> PPTXShape:
        """Expected PPTX output for Gaussian blur filter"""
        return PPTXShape(
            shape_type=PPTXShapeType.SHAPE_WITH_EFFECT,
            position=PPTXPosition(x=60, y=60),
            size=PPTXSize(width=80, height=80),
            fill=PPTXFill(
                type="solid",
                color=PPTXColor(type="rgb", value="0000FF")
            ),
            effects=[
                PPTXEffect(
                    type=PPTXEffectType.BLUR,
                    properties={
                        "radius": 3.0,
                        "type": "gaussian"
                    }
                )
            ]
        )
    
    @staticmethod
    def filter_drop_shadow() -> PPTXShape:
        """Expected PPTX output for drop shadow filter"""
        return PPTXShape(
            shape_type=PPTXShapeType.SHAPE_WITH_EFFECT,
            position=PPTXPosition(x=50, y=50),
            size=PPTXSize(width=100, height=60),
            fill=PPTXFill(
                type="solid",
                color=PPTXColor(type="rgb", value="FF0000")
            ),
            effects=[
                PPTXEffect(
                    type=PPTXEffectType.DROP_SHADOW,
                    properties={
                        "offset_x": 3.0,
                        "offset_y": 3.0,
                        "blur_radius": 2.0,
                        "color": PPTXColor(type="rgb", value="000000", alpha=0.3)
                    }
                )
            ]
        )
    
    @staticmethod
    def style_css_classes() -> List[PPTXShape]:
        """Expected PPTX output for CSS styled elements"""
        return [
            PPTXShape(
                shape_type=PPTXShapeType.FREEFORM,
                position=PPTXPosition(x=70, y=20),
                size=PPTXSize(width=60, height=60),
                fill=PPTXFill(
                    type="solid",
                    color=PPTXColor(type="rgb", value="FF0000")
                ),
                stroke=PPTXStroke(
                    color=PPTXColor(type="rgb", value="000000"),
                    width=2.0
                ),
                custom_properties={"css_class": "red-circle"}
            ),
            PPTXShape(
                shape_type=PPTXShapeType.FREEFORM,
                position=PPTXPosition(x=50, y=100),
                size=PPTXSize(width=60, height=40),
                fill=PPTXFill(
                    type="solid",
                    color=PPTXColor(type="rgb", value="0000FF", alpha=0.7)
                ),
                custom_properties={"css_class": "blue-rect"}
            ),
            PPTXShape(
                shape_type=PPTXShapeType.FREEFORM,
                position=PPTXPosition(x=170, y=135),
                size=PPTXSize(width=40, height=30),
                fill=PPTXFill(
                    type="solid",
                    color=PPTXColor(type="rgb", value="008000")
                ),
                transform={"rotation": 45},
                custom_properties={"css_id": "special"}
            )
        ]
    
    @staticmethod
    def nested_svg() -> List[PPTXShape]:
        """Expected PPTX output for nested SVG elements"""
        return [
            PPTXShape(
                shape_type=PPTXShapeType.GROUP,
                position=PPTXPosition(x=50, y=50),
                size=PPTXSize(width=100, height=100),
                custom_properties={"nested_svg": True, "viewBox": "0 0 50 50"}
            ),
            PPTXShape(
                shape_type=PPTXShapeType.FREEFORM,
                position=PPTXPosition(x=60, y=60),
                size=PPTXSize(width=30, height=30),
                fill=PPTXFill(
                    type="solid",
                    color=PPTXColor(type="rgb", value="0000FF")
                ),
                custom_properties={"parent_group": True}
            ),
            PPTXShape(
                shape_type=PPTXShapeType.FREEFORM,
                position=PPTXPosition(x=130, y=130),
                size=PPTXSize(width=40, height=40),
                fill=PPTXFill(
                    type="solid",
                    color=PPTXColor(type="rgb", value="008000")
                )
            )
        ]


class PPTXFixtureValidator:
    """Validates actual PPTX output against expected fixtures"""
    
    def __init__(self):
        self.tolerance = 1.0  # Pixel tolerance for position/size comparisons
        
    def validate_shape(self, expected: PPTXShape, actual: Dict[str, Any]) -> Dict[str, bool]:
        """Validate actual shape against expected fixture"""
        validation_results = {}
        
        # Validate shape type
        validation_results['shape_type'] = (
            actual.get('shape_type') == expected.shape_type.value
        )
        
        # Validate position
        if expected.position:
            actual_pos = actual.get('position', {})
            validation_results['position_x'] = abs(
                actual_pos.get('x', 0) - expected.position.x
            ) <= self.tolerance
            validation_results['position_y'] = abs(
                actual_pos.get('y', 0) - expected.position.y
            ) <= self.tolerance
        
        # Validate size
        if expected.size:
            actual_size = actual.get('size', {})
            validation_results['size_width'] = abs(
                actual_size.get('width', 0) - expected.size.width
            ) <= self.tolerance
            validation_results['size_height'] = abs(
                actual_size.get('height', 0) - expected.size.height
            ) <= self.tolerance
        
        # Validate stroke properties
        if expected.stroke:
            actual_stroke = actual.get('stroke', {})
            validation_results['stroke_color'] = (
                actual_stroke.get('color', {}).get('value') == expected.stroke.color.value
            )
            validation_results['stroke_width'] = abs(
                actual_stroke.get('width', 0) - expected.stroke.width
            ) <= 0.1
        
        # Validate fill properties
        if expected.fill:
            actual_fill = actual.get('fill', {})
            validation_results['fill_type'] = (
                actual_fill.get('type') == expected.fill.type
            )
            if expected.fill.color:
                validation_results['fill_color'] = (
                    actual_fill.get('color', {}).get('value') == expected.fill.color.value
                )
        
        # Validate effects
        if expected.effects:
            actual_effects = actual.get('effects', [])
            validation_results['effects_count'] = (
                len(actual_effects) == len(expected.effects)
            )
            for i, expected_effect in enumerate(expected.effects):
                if i < len(actual_effects):
                    validation_results[f'effect_{i}_type'] = (
                        actual_effects[i].get('type') == expected_effect.type.value
                    )
        
        # Validate text runs
        if expected.text_runs:
            actual_text_runs = actual.get('text_runs', [])
            validation_results['text_runs_count'] = (
                len(actual_text_runs) == len(expected.text_runs)
            )
            for i, expected_run in enumerate(expected.text_runs):
                if i < len(actual_text_runs):
                    actual_run = actual_text_runs[i]
                    validation_results[f'text_run_{i}_text'] = (
                        actual_run.get('text') == expected_run.text
                    )
                    validation_results[f'text_run_{i}_font_weight'] = (
                        actual_run.get('font_weight') == expected_run.font_weight
                    )
        
        return validation_results
    
    def validate_shape_list(self, expected: List[PPTXShape], actual: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate list of shapes"""
        if len(expected) != len(actual):
            return {
                'valid': False,
                'error': f'Shape count mismatch: expected {len(expected)}, got {len(actual)}'
            }
        
        validation_results = {'valid': True, 'shapes': []}
        for i, (exp_shape, act_shape) in enumerate(zip(expected, actual)):
            shape_validation = self.validate_shape(exp_shape, act_shape)
            validation_results['shapes'].append({
                'shape_index': i,
                'validations': shape_validation,
                'all_valid': all(shape_validation.values())
            })
        
        validation_results['all_shapes_valid'] = all(
            shape_result['all_valid'] for shape_result in validation_results['shapes']
        )
        
        return validation_results


def get_fixture_by_name(fixture_name: str) -> Any:
    """Get fixture by name for dynamic testing"""
    fixtures_map = {
        'polyline_basic': PPTXFixtures.polyline_basic,
        'polyline_complex': PPTXFixtures.polyline_complex,
        'tspan_styling': PPTXFixtures.tspan_styling,
        'tspan_nested': PPTXFixtures.tspan_nested,
        'image_embedded': PPTXFixtures.image_embedded,
        'image_base64': PPTXFixtures.image_base64,
        'symbol_use_reusable': PPTXFixtures.symbol_use_reusable,
        'pattern_dots': PPTXFixtures.pattern_dots,
        'pattern_stripes': PPTXFixtures.pattern_stripes,
        'filter_gaussian_blur': PPTXFixtures.filter_gaussian_blur,
        'filter_drop_shadow': PPTXFixtures.filter_drop_shadow,
        'style_css_classes': PPTXFixtures.style_css_classes,
        'nested_svg': PPTXFixtures.nested_svg
    }
    
    return fixtures_map.get(fixture_name)


if __name__ == "__main__":
    # Demonstrate fixture usage
    fixture = PPTXFixtures.polyline_basic()
    print(f"Sample fixture: {fixture}")
    
    validator = PPTXFixtureValidator()
    
    # Mock actual output for demonstration
    mock_actual = {
        'shape_type': 'freeform',
        'position': {'x': 10, 'y': 10},
        'size': {'width': 140, 'height': 30},
        'stroke': {
            'color': {'value': '0000FF'},
            'width': 2.0
        },
        'fill': {'type': 'none'}
    }
    
    validation = validator.validate_shape(fixture, mock_actual)
    print(f"Validation results: {validation}")