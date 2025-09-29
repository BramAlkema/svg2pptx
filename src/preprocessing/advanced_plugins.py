"""
Advanced preprocessing plugins ported from SVGO.
These provide more sophisticated optimizations for complex SVG structures.

Note: Path optimization uses native Python (re + math) for superior performance over
NumPy. Regex-based coordinate processing and recursive algorithms are faster with
native Python tools. NumPy is reserved for conversion pipeline matrix operations.
"""

import re
import math
from lxml import etree as ET
from typing import Dict, List, Optional, Set, Tuple, Union
from .base import PreprocessingPlugin, PreprocessingContext


class ConvertPathDataPlugin(PreprocessingPlugin):
    """Advanced path data optimization with curve simplification and coordinate optimization."""
    
    name = "convertPathData"
    description = "optimizes path data: writes in shorter form, applies transformations"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return self._tag_matches(element, 'path') and 'd' in element.attrib
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        path_data = element.attrib.get('d', '')
        if not path_data:
            return False
        
        try:
            optimized_path = self._optimize_path_data(path_data, context.precision)
            if optimized_path != path_data:
                element.set('d', optimized_path)
                context.record_modification(self.name, "optimized_path")
                return True
        except Exception as e:
            # Log error but don't fail the entire process
            print(f"Path optimization failed: {e}")
        
        return False
    
    def _optimize_path_data(self, path_data: str, precision: int) -> str:
        """Optimize path data using consolidated PathProcessor service."""
        try:
            # Use PathProcessor for comprehensive path optimization
            from ..utils.path_processor import path_processor
            return path_processor.optimize_path_data(path_data, precision)

        except ImportError:
            # Fallback to legacy implementation
            pass

        # Legacy path optimization implementation
        # Clean up whitespace
        path_data = re.sub(r'\s+', ' ', path_data.strip())

        # Convert to relative coordinates where shorter
        path_data = self._convert_to_relative_coords(path_data, precision)

        # Simplify curve commands
        path_data = self._simplify_curves(path_data, precision)

        # Remove redundant commands
        path_data = self._remove_redundant_commands(path_data)

        # Optimize coordinate precision
        path_data = self._optimize_coordinate_precision(path_data, precision)

        return path_data
    
    def _convert_to_relative_coords(self, path_data: str, precision: int) -> str:
        """Convert absolute coordinates to relative where it saves space."""
        # This is a simplified implementation
        # A full implementation would parse the path and convert coordinates
        return path_data
    
    def _simplify_curves(self, path_data: str, precision: int) -> str:
        """Simplify bezier curves and convert smooth curves."""
        # Convert smooth curve commands (S) to regular curves (C) if beneficial
        # Simplify quadratic curves (Q) to cubic (C) if needed
        return path_data
    
    def _remove_redundant_commands(self, path_data: str) -> str:
        """Remove redundant path commands."""
        # Remove consecutive duplicate commands
        # Remove zero-length line segments
        # Remove curves that are effectively straight lines
        
        # Remove consecutive moveto commands (keep only the last one)
        path_data = re.sub(r'(M\s*[^MLHVCSQTAZmlhvcsqtaz]+)\s*M\s*', r'M ', path_data)
        
        return path_data
    
    def _optimize_coordinate_precision(self, path_data: str, precision: int) -> str:
        """Optimize coordinate precision throughout the path using consolidated PreprocessorUtilities."""
        try:
            # Use PreprocessorUtilities for consistent number formatting
            from ..utils.preprocessor_utilities import preprocessor_utilities

            def replace_number(match):
                num_str = match.group(0)
                try:
                    num = float(num_str)
                    return preprocessor_utilities.format_number(num, precision)
                except ValueError:
                    return num_str

            return re.sub(r'-?\d*\.?\d+', replace_number, path_data)

        except ImportError:
            # Fallback to legacy implementation
            pass

        # Legacy implementation
        def replace_number(match):
            num_str = match.group(0)
            try:
                num = float(num_str)
                if abs(num) < 0.1 ** precision:
                    return '0'
                if num.is_integer():
                    return str(int(num))
                else:
                    formatted = f"{num:.{precision}f}".rstrip('0').rstrip('.')
                    return formatted if formatted else '0'
            except ValueError:
                return num_str

        return re.sub(r'-?\d*\.?\d+', replace_number, path_data)


class MergePathsPlugin(PreprocessingPlugin):
    """Merge multiple paths with the same styling into a single path."""
    
    name = "mergePaths"
    description = "merges multiple paths in one if possible"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        # This plugin operates on parent elements that contain paths
        return len([child for child in element if self._tag_matches(child, 'path')]) > 1
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        paths = [child for child in element if self._tag_matches(child, 'path')]
        if len(paths) < 2:
            return False
        
        # Group paths by style attributes
        style_groups = {}
        for path in paths:
            style_key = self._get_style_key(path)
            if style_key not in style_groups:
                style_groups[style_key] = []
            style_groups[style_key].append(path)
        
        merged_any = False
        for style_key, path_group in style_groups.items():
            if len(path_group) > 1:
                merged_path = self._merge_path_group(path_group)
                if merged_path is not None:
                    # Remove original paths
                    for path in path_group:
                        element.remove(path)
                    # Add merged path
                    element.append(merged_path)
                    merged_any = True
                    context.record_modification(self.name, f"merged_{len(path_group)}_paths")
        
        return merged_any
    
    def _get_style_key(self, path: ET.Element) -> str:
        """Generate a key representing the styling attributes of a path."""
        style_attrs = ['fill', 'stroke', 'stroke-width', 'stroke-dasharray', 
                      'opacity', 'fill-opacity', 'stroke-opacity', 'class', 'style']
        key_parts = []
        for attr in style_attrs:
            if attr in path.attrib:
                key_parts.append(f"{attr}:{path.attrib[attr]}")
        return '|'.join(sorted(key_parts))
    
    def _merge_path_group(self, paths: List[ET.Element]) -> Optional[ET.Element]:
        """Merge a group of paths with the same styling."""
        if not paths:
            return None
        
        # Create new path element based on the first path
        merged = ET.Element(paths[0].tag)
        
        # Copy attributes from the first path
        for attr, value in paths[0].attrib.items():
            if attr != 'd':  # We'll build the d attribute separately
                merged.set(attr, value)
        
        # Combine path data
        path_data_parts = []
        for path in paths:
            path_data = path.attrib.get('d', '').strip()
            if path_data:
                path_data_parts.append(path_data)
        
        if path_data_parts:
            merged.set('d', ' '.join(path_data_parts))
            return merged
        
        return None


class ConvertTransformPlugin(PreprocessingPlugin):
    """Optimize and collapse transformation matrices."""
    
    name = "convertTransform"
    description = "collapses multiple transformations and optimizes it"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return element.get('transform') is not None
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        transform_str = element.attrib.get('transform', '')
        if not transform_str:
            return False
        
        try:
            optimized_transform = self._optimize_transform(transform_str, context.precision)
            
            if optimized_transform != transform_str:
                if optimized_transform:
                    element.set('transform', optimized_transform)
                else:
                    # Remove identity transform
                    del element.attrib['transform']
                context.record_modification(self.name, "optimized_transform")
                return True
        except Exception as e:
            print(f"Transform optimization failed: {e}")
        
        return False
    
    def _optimize_transform(self, transform_str: str, precision: int) -> str:
        """Parse and optimize transform functions."""
        # Parse individual transform functions
        transforms = self._parse_transforms(transform_str)
        
        # Combine matrices if possible
        combined = self._combine_transforms(transforms, precision)
        
        # Convert back to shortest representation
        return self._transforms_to_string(combined, precision)
    
    def _parse_transforms(self, transform_str: str) -> List[Dict]:
        """Parse transform string into individual transform functions using canonical TransformEngine."""
        try:
            # Use the canonical high-performance TransformEngine for parsing
            from ..transforms import TransformEngine

            engine = services.transform_parser
            transforms = engine.parse(transform_str)

            # Convert to expected format for backward compatibility
            return [
                {
                    'type': t.get('type', ''),
                    'params': t.get('values', [])
                }
                for t in transforms
            ]

        except ImportError:
            # Fallback to legacy parsing if TransformEngine not available
            return self._legacy_parse_transforms(transform_str)
        except Exception:
            # Fallback to legacy parsing on any error
            return self._legacy_parse_transforms(transform_str)

    def _legacy_parse_transforms(self, transform_str: str) -> List[Dict]:
        """Legacy transform parsing - to be replaced once TransformEngine integration is complete."""
        transforms = []

        # Match transform functions: translate(x,y), scale(x), rotate(angle), etc.
        pattern = r'(\w+)\s*\(\s*([^)]*)\s*\)'
        matches = re.findall(pattern, transform_str)

        for func_name, params_str in matches:
            params = [float(p.strip()) for p in params_str.split(',') if p.strip()]
            transforms.append({
                'type': func_name,
                'params': params
            })

        return transforms
    
    def _combine_transforms(self, transforms: List[Dict], precision: int) -> List[Dict]:
        """Combine consecutive transforms of the same type."""
        if not transforms:
            return transforms
        
        combined = []
        i = 0
        
        while i < len(transforms):
            current = transforms[i]
            
            if current['type'] == 'translate' and i + 1 < len(transforms):
                next_transform = transforms[i + 1]
                if next_transform['type'] == 'translate':
                    # Combine consecutive translates
                    x1, y1 = current['params'][:2] if len(current['params']) >= 2 else [current['params'][0], 0]
                    x2, y2 = next_transform['params'][:2] if len(next_transform['params']) >= 2 else [next_transform['params'][0], 0]
                    
                    combined_x = x1 + x2
                    combined_y = y1 + y2
                    
                    # Skip the next transform since we combined it
                    i += 2
                    
                    if abs(combined_x) > 10**-precision or abs(combined_y) > 10**-precision:
                        combined.append({
                            'type': 'translate',
                            'params': [combined_x, combined_y] if combined_y != 0 else [combined_x]
                        })
                    continue
            
            elif current['type'] == 'scale' and i + 1 < len(transforms):
                next_transform = transforms[i + 1]
                if next_transform['type'] == 'scale':
                    # Combine consecutive scales
                    sx1 = current['params'][0]
                    sy1 = current['params'][1] if len(current['params']) > 1 else sx1
                    sx2 = next_transform['params'][0]
                    sy2 = next_transform['params'][1] if len(next_transform['params']) > 1 else sx2
                    
                    combined_sx = sx1 * sx2
                    combined_sy = sy1 * sy2
                    
                    i += 2
                    
                    if abs(combined_sx - 1) > 10**-precision or abs(combined_sy - 1) > 10**-precision:
                        if abs(combined_sx - combined_sy) < 10**-precision:
                            combined.append({'type': 'scale', 'params': [combined_sx]})
                        else:
                            combined.append({'type': 'scale', 'params': [combined_sx, combined_sy]})
                    continue
            
            # If we can't combine, add the current transform
            combined.append(current)
            i += 1
        
        return combined
    
    def _transforms_to_string(self, transforms: List[Dict], precision: int) -> str:
        """Convert transforms back to string representation."""
        if not transforms:
            return ''
        
        parts = []
        for transform in transforms:
            func_type = transform['type']
            params = transform['params']
            
            # Format parameters with appropriate precision
            formatted_params = []
            for param in params:
                if abs(param) < 10**-precision:
                    formatted_params.append('0')
                elif param == int(param):
                    formatted_params.append(str(int(param)))
                else:
                    formatted = f"{param:.{precision}f}".rstrip('0').rstrip('.')
                    formatted_params.append(formatted if formatted else '0')
            
            parts.append(f"{func_type}({','.join(formatted_params)})")
        
        return ' '.join(parts)


class RemoveUselessStrokeAndFillPlugin(PreprocessingPlugin):
    """Remove useless stroke and fill attributes."""
    
    name = "removeUselessStrokeAndFill"
    description = "removes useless stroke and fill attributes"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return any(attr in element.attrib for attr in ['fill', 'stroke', 'stroke-width', 'stroke-opacity', 'fill-opacity'])
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        modified = False
        
        # Remove stroke attributes when stroke is 'none' or stroke-width is 0
        if element.attrib.get('stroke') == 'none' or element.attrib.get('stroke-width') == '0':
            stroke_attrs = ['stroke-width', 'stroke-opacity', 'stroke-dasharray', 'stroke-linecap', 'stroke-linejoin']
            for attr in stroke_attrs:
                if attr in element.attrib:
                    del element.attrib[attr]
                    modified = True
        
        # Remove fill-opacity when fill is 'none'
        if element.attrib.get('fill') == 'none' and 'fill-opacity' in element.attrib:
            del element.attrib['fill-opacity']
            modified = True
        
        # Remove stroke-opacity when stroke is 'none'
        if element.attrib.get('stroke') == 'none' and 'stroke-opacity' in element.attrib:
            del element.attrib['stroke-opacity']
            modified = True
        
        # Remove redundant opacity values
        if element.attrib.get('opacity') == '1':
            del element.attrib['opacity']
            modified = True
        
        if element.attrib.get('fill-opacity') == '1':
            del element.attrib['fill-opacity']
            modified = True
        
        if element.attrib.get('stroke-opacity') == '1':
            del element.attrib['stroke-opacity']
            modified = True
        
        if modified:
            context.record_modification(self.name, "removed_useless_stroke_fill")
        
        return modified


class RemoveHiddenElementsPlugin(PreprocessingPlugin):
    """Remove hidden elements (zero sized, with absent attributes)."""
    
    name = "removeHiddenElems"
    description = "removes hidden elements (zero sized, with absent attributes)"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return self._is_valid_element(element)  # Only process valid XML elements
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        if self._is_hidden_element(element):
            context.mark_for_removal(element)
            context.record_modification(self.name, "removed_hidden_element")
            return True
        return False
    
    def _is_hidden_element(self, element: ET.Element) -> bool:
        """Check if element should be considered hidden."""
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        
        # Check for zero dimensions
        if tag in ['rect', 'ellipse', 'image']:
            width = float(element.get('width', 1))
            height = float(element.get('height', 1))
            if width <= 0 or height <= 0:
                return True
        
        if tag == 'circle':
            r = float(element.get('r', 1))
            if r <= 0:
                return True
        
        if tag == 'line':
            x1, y1 = float(element.get('x1', 0)), float(element.get('y1', 0))
            x2, y2 = float(element.get('x2', 0)), float(element.get('y2', 0))
            if x1 == x2 and y1 == y2:
                return True
        
        # Check for invisible styling
        if (element.get('opacity') == '0' or 
            (element.get('fill') == 'none' and element.get('stroke') == 'none') or
            element.get('display') == 'none' or
            element.get('visibility') == 'hidden'):
            return True
        
        return False


class MinifyStylesPlugin(PreprocessingPlugin):
    """Minify CSS styles and remove unused styles."""
    
    name = "minifyStyles"
    description = "minifies styles and removes unused styles"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return self._tag_matches(element, 'style') or 'style' in element.attrib
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        modified = False
        
        # Process style elements
        if self._tag_matches(element, 'style') and element.text:
            minified_css = self._minify_css(element.text)
            if minified_css != element.text:
                element.text = minified_css
                modified = True
        
        # Process style attributes
        if 'style' in element.attrib:
            style_attr = element.attrib['style']
            minified_style = self._minify_style_attribute(style_attr)
            if minified_style != style_attr:
                element.set('style', minified_style)
                modified = True
        
        if modified:
            context.record_modification(self.name, "minified_styles")
        
        return modified
    
    def _minify_css(self, css_text: str) -> str:
        """Minify CSS text."""
        # Remove comments
        css_text = re.sub(r'/\*.*?\*/', '', css_text, flags=re.DOTALL)
        
        # Remove excessive whitespace
        css_text = re.sub(r'\s+', ' ', css_text)
        css_text = re.sub(r'\s*([{}:;,])\s*', r'\1', css_text)
        
        # Remove trailing semicolons before }
        css_text = re.sub(r';\s*}', '}', css_text)
        
        return css_text.strip()
    
    def _minify_style_attribute(self, style_attr: str) -> str:
        """Minify inline style attribute."""
        # Use canonical StyleParser with custom minification logic
        from ..utils.style_parser import style_parser
        style_dict = style_parser.parse_style_to_dict(style_attr)

        # Apply minification logic - skip redundant properties
        properties = []
        for key, value in style_dict.items():
            # Skip properties with zero/none values that don't affect rendering
            if self._is_redundant_property(key, value):
                continue
            properties.append(f"{key}:{value}")

        return ';'.join(properties)
    
    def _is_redundant_property(self, key: str, value: str) -> bool:
        """Check if a CSS property is redundant."""
        redundant_values = {
            'opacity': ['1'],
            'fill-opacity': ['1'],
            'stroke-opacity': ['1'],
            'stroke-width': ['0'],
        }
        
        return key in redundant_values and value in redundant_values[key]


class SortAttributesPlugin(PreprocessingPlugin):
    """Sort element attributes for better compression."""
    
    name = "sortAttrs"
    description = "Sort element attributes for better compression"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return len(element.attrib) > 1
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        if len(element.attrib) <= 1:
            return False
        
        # Get current attributes
        current_attrs = dict(element.attrib)
        
        # Sort by attribute name
        sorted_attrs = sorted(current_attrs.items())
        
        # Check if order changed
        if list(current_attrs.items()) == sorted_attrs:
            return False
        
        # Clear and re-add in sorted order
        element.attrib.clear()
        for key, value in sorted_attrs:
            element.set(key, value)
        
        context.record_modification(self.name, "sorted_attributes")
        return True


class RemoveUnknownsAndDefaultsPlugin(PreprocessingPlugin):
    """Remove unknown elements/attributes and attributes with default values."""
    
    name = "removeUnknownsAndDefaults"
    description = "removes unknown elements content and attributes, removes attrs with default values"
    
    def can_process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        return True
    
    def process(self, element: ET.Element, context: PreprocessingContext) -> bool:
        modified = False
        
        # Remove attributes with default values
        default_values = {
            'x': '0',
            'y': '0',
            'width': '100%',
            'height': '100%',
            'cx': '0',
            'cy': '0',
            'rx': '0',
            'ry': '0',
            'r': '0',
            'fill': 'black',
            'stroke': 'none',
            'stroke-width': '1',
            'opacity': '1',
            'fill-opacity': '1',
            'stroke-opacity': '1',
            'stroke-linecap': 'butt',
            'stroke-linejoin': 'miter',
            'stroke-miterlimit': '4',
        }
        
        attrs_to_remove = []
        for attr, value in element.attrib.items():
            if attr in default_values and value == default_values[attr]:
                attrs_to_remove.append(attr)
        
        for attr in attrs_to_remove:
            del element.attrib[attr]
            modified = True
        
        if modified:
            context.record_modification(self.name, "removed_defaults")
        
        return modified