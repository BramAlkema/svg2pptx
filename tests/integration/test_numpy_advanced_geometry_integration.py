#!/usr/bin/env python3
"""
Integration tests for NumPy advanced geometric operations (Task 2.1.3).

Tests end-to-end integration of vectorized shape intersection algorithms,
coordinate transformations, and advanced spatial operations within the
complete SVG2PPTX conversion pipeline.
"""

import numpy as np
import pytest
from typing import List, Dict, Any
import xml.etree.ElementTree as ET
import time

from src.converters.shapes.numpy_geometry import (
    NumPyGeometryEngine,
    ShapeGeometry,
    ShapeType,
    create_geometry_engine
)
from src.converters.shapes.numpy_converter import NumPyShapeConverter


class TestAdvancedGeometryIntegration:
    """Integration tests for Task 2.1.3 advanced geometric operations."""

    @pytest.fixture
    def conversion_context(self):
        """Mock conversion context for testing."""
        class MockCoordinateSystem:
            def svg_length_to_emu(self, length, axis):
                return int(float(length) * 12700)  # Basic conversion

            def svg_to_emu(self, x, y):
                return (int(float(x) * 12700), int(float(y) * 12700))

        class MockContext:
            def __init__(self):
                self.coordinate_system = MockCoordinateSystem()
                self.viewport_mapping = None

        return MockContext()

    @pytest.fixture
    def numpy_converter(self, conversion_context):
        """Create NumPy shape converter for integration testing."""
        return NumPyShapeConverter()

    @pytest.fixture
    def complex_svg_elements(self):
        """Create complex SVG elements for integration testing."""
        elements = []

        # Rectangle elements with various positions and sizes
        rect_data = [
            {"x": "10", "y": "10", "width": "50", "height": "30"},
            {"x": "40", "y": "25", "width": "60", "height": "40"},
            {"x": "80", "y": "10", "width": "30", "height": "50"},
            {"x": "120", "y": "35", "width": "40", "height": "25"},
        ]

        for i, data in enumerate(rect_data):
            elem = ET.Element('rect')
            elem.set('id', f'rect{i}')
            for key, value in data.items():
                elem.set(key, value)
            elem.set('fill', f'rgb({i*60}, {i*40}, {255-i*50})')
            elem.set('stroke', 'black')
            elem.set('stroke-width', '2')
            elements.append(elem)

        # Circle elements
        circle_data = [
            {"cx": "200", "cy": "30", "r": "20"},
            {"cx": "240", "cy": "60", "r": "15"},
            {"cx": "280", "cy": "40", "r": "25"},
            {"cx": "320", "cy": "20", "r": "18"},
        ]

        for i, data in enumerate(circle_data):
            elem = ET.Element('circle')
            elem.set('id', f'circle{i}')
            for key, value in data.items():
                elem.set(key, value)
            elem.set('fill', f'rgba({255-i*50}, {i*60}, {i*40}, 0.8)')
            elements.append(elem)

        # Polygon elements
        polygon_data = [
            {"points": "350,10 380,30 370,60 340,50"},
            {"points": "400,20 430,15 440,45 415,55 390,40"},
            {"points": "460,25 490,30 485,50 465,55 450,40"},
        ]

        for i, data in enumerate(polygon_data):
            elem = ET.Element('polygon')
            elem.set('id', f'polygon{i}')
            elem.set('points', data['points'])
            elem.set('fill', f'hsl({i*120}, 70%, 50%)')
            elements.append(elem)

        return elements

    # ==================== End-to-End Integration Tests ====================

    def test_complete_shape_intersection_workflow(self, numpy_converter, conversion_context, complex_svg_elements):
        """Test complete workflow: SVG parsing -> geometry creation -> intersection detection."""
        # Convert SVG elements to shapes using the NumPy converter
        shape_geometries = []

        for element in complex_svg_elements:
            if element.tag in ['rect', 'circle', 'polygon']:
                # Use the converter to process each element
                drawingml_xml = numpy_converter.convert(element, conversion_context)

                # Extract geometry information for intersection testing
                if element.tag == 'rect':
                    x = float(element.get('x', '0'))
                    y = float(element.get('y', '0'))
                    width = float(element.get('width', '0'))
                    height = float(element.get('height', '0'))
                    bbox = np.array([x, y, width, height])
                    shape_type = ShapeType.RECTANGLE

                elif element.tag == 'circle':
                    cx = float(element.get('cx', '0'))
                    cy = float(element.get('cy', '0'))
                    r = float(element.get('r', '0'))
                    bbox = np.array([cx-r, cy-r, 2*r, 2*r])
                    shape_type = ShapeType.CIRCLE

                elif element.tag == 'polygon':
                    # Parse polygon points for bounding box calculation
                    points_str = element.get('points', '')
                    coords = []
                    for coord in points_str.replace(',', ' ').split():
                        if coord.strip():
                            coords.append(float(coord))

                    if len(coords) >= 4:
                        points = np.array(coords).reshape(-1, 2)
                        min_coords = np.min(points, axis=0)
                        max_coords = np.max(points, axis=0)
                        bbox = np.concatenate([min_coords, max_coords - min_coords])
                        shape_type = ShapeType.POLYGON
                    else:
                        continue

                geometry = ShapeGeometry(
                    shape_type=shape_type,
                    bounding_box=bbox,
                    drawingml_xml=drawingml_xml
                )
                shape_geometries.append(geometry)

        # Now test advanced intersection detection on the converted shapes
        engine = create_geometry_engine(optimization_level=2)

        # Test pairwise intersections
        if len(shape_geometries) >= 2:
            # Create pairs for intersection testing
            shapes_a = shape_geometries[:len(shape_geometries)//2]
            shapes_b = shape_geometries[len(shape_geometries)//2:]

            # Pad to equal length if needed
            min_len = min(len(shapes_a), len(shapes_b))
            shapes_a = shapes_a[:min_len]
            shapes_b = shapes_b[:min_len]

            intersections = engine.calculate_shape_intersections_batch(shapes_a, shapes_b)

            # Validate results
            assert isinstance(intersections, list)
            assert len(intersections) == min_len
            assert all(isinstance(result, bool) for result in intersections)

            print(f"Processed {len(shape_geometries)} shapes from SVG elements")
            print(f"Intersection results: {intersections}")

    def test_coordinate_transformation_integration(self, numpy_converter, conversion_context):
        """Test coordinate transformation integration with real SVG conversion."""
        # Create SVG elements with known coordinates
        svg_elements = []

        # Rectangle at different positions
        positions = [(0, 0), (50, 50), (100, 100), (150, 150)]
        for i, (x, y) in enumerate(positions):
            elem = ET.Element('rect')
            elem.set('x', str(x))
            elem.set('y', str(y))
            elem.set('width', '40')
            elem.set('height', '30')
            elem.set('id', f'transform_rect{i}')
            svg_elements.append(elem)

        # Process elements through converter
        converted_shapes = []
        for element in svg_elements:
            drawingml_xml = numpy_converter.convert(element, conversion_context)

            x = float(element.get('x'))
            y = float(element.get('y'))
            width = float(element.get('width'))
            height = float(element.get('height'))

            geometry = ShapeGeometry(
                shape_type=ShapeType.RECTANGLE,
                bounding_box=np.array([x, y, width, height]),
                drawingml_xml=drawingml_xml
            )
            converted_shapes.append(geometry)

        # Apply coordinate transformations
        engine = create_geometry_engine()

        # Extract coordinates for transformation testing
        coordinates = np.array([[[shape.bounding_box[0], shape.bounding_box[1]],
                                [shape.bounding_box[0] + shape.bounding_box[2],
                                 shape.bounding_box[1] + shape.bounding_box[3]]]
                               for shape in converted_shapes])

        # Create transformation matrices (scale by 2x, translate by [10, 20])
        transform_matrices = []
        for i in range(len(converted_shapes)):
            # Each shape gets a different transformation
            scale = 1 + i * 0.5
            translate_x = i * 10
            translate_y = i * 20

            matrix = np.array([
                [scale, 0, translate_x],
                [0, scale, translate_y],
                [0, 0, 1]
            ])
            transform_matrices.append(matrix)

        transform_matrices = np.array(transform_matrices)

        # Apply batch transformations
        transformed_coords = engine.transform_coordinates_batch(coordinates, transform_matrices)

        # Validate transformation results
        assert transformed_coords.shape == coordinates.shape
        assert not np.array_equal(transformed_coords, coordinates)  # Should be different

        # Verify specific transformations
        for i, (original, transformed) in enumerate(zip(coordinates, transformed_coords)):
            scale = 1 + i * 0.5
            translate_x = i * 10
            translate_y = i * 20

            # Check transformation accuracy
            expected = original * scale + np.array([translate_x, translate_y])
            np.testing.assert_array_almost_equal(transformed, expected, decimal=5)

        print(f"Successfully transformed {len(converted_shapes)} shapes with vectorized operations")

    def test_shape_complexity_optimization_integration(self, conversion_context):
        """Test shape complexity optimization integrated with real polygon conversion."""
        # Create complex polygons with many points
        complex_polygons = []

        # Generate polygons with increasing complexity
        for complexity in [20, 50, 100, 200]:
            # Create a polygon with many points (star-like pattern)
            angles = np.linspace(0, 2*np.pi, complexity, endpoint=False)
            radii = 20 + 10 * np.sin(angles * 5)  # Variable radius for complexity
            center_x, center_y = 100 + complexity, 100

            points = []
            for angle, radius in zip(angles, radii):
                x = center_x + radius * np.cos(angle)
                y = center_y + radius * np.sin(angle)
                points.extend([x, y])

            points_str = ' '.join(map(str, points))

            elem = ET.Element('polygon')
            elem.set('points', points_str)
            elem.set('id', f'complex_polygon_{complexity}')
            elem.set('fill', 'blue')

            # Convert to geometry
            coords = np.array(points).reshape(-1, 2)
            min_coords = np.min(coords, axis=0)
            max_coords = np.max(coords, axis=0)
            bbox = np.concatenate([min_coords, max_coords - min_coords])

            geometry = ShapeGeometry(
                shape_type=ShapeType.POLYGON,
                bounding_box=bbox,
                points=coords,
                drawingml_xml=f"<polygon_{complexity}/>"
            )
            complex_polygons.append(geometry)

        # Apply complexity optimization
        engine = create_geometry_engine()

        # Test different optimization levels
        for max_points in [10, 25, 50]:
            optimized_shapes = engine.optimize_shape_complexity_batch(
                complex_polygons, max_points_per_shape=max_points
            )

            assert len(optimized_shapes) == len(complex_polygons)

            for i, (original, optimized) in enumerate(zip(complex_polygons, optimized_shapes)):
                if hasattr(original, 'points') and len(original.points) > max_points:
                    # Should be simplified
                    assert hasattr(optimized, 'points')
                    assert len(optimized.points) <= max_points
                    assert len(optimized.points) > 0

                    print(f"Polygon {i}: {len(original.points)} -> {len(optimized.points)} points "
                          f"(max {max_points})")

    def test_spatial_analysis_integration(self, complex_svg_elements, conversion_context):
        """Test integration of spatial analysis features with converted shapes."""
        # Convert SVG elements to geometries
        shape_geometries = []

        for element in complex_svg_elements[:6]:  # Use subset for performance
            if element.tag == 'rect':
                x = float(element.get('x', '0'))
                y = float(element.get('y', '0'))
                width = float(element.get('width', '0'))
                height = float(element.get('height', '0'))
                bbox = np.array([x, y, width, height])
                shape_type = ShapeType.RECTANGLE

                geometry = ShapeGeometry(
                    shape_type=shape_type,
                    bounding_box=bbox,
                    drawingml_xml=f"<{element.tag}/>"
                )
                shape_geometries.append(geometry)

        if not shape_geometries:
            pytest.skip("No suitable shapes for spatial analysis testing")

        engine = create_geometry_engine()

        # Test union bounds calculation
        union_bounds = engine.calculate_union_bounds_batch(shape_geometries)
        assert union_bounds.shape == (4,)
        assert np.all(union_bounds >= 0)

        # Test area calculations
        areas = engine.calculate_shape_areas_batch(shape_geometries)
        assert len(areas) == len(shape_geometries)
        assert np.all(areas >= 0)

        # Test mask generation
        canvas_size = (200, 100)
        masks = engine.generate_shape_masks_batch(shape_geometries, canvas_size, resolution=64)
        assert masks.shape == (len(shape_geometries), 64, 64)
        assert masks.dtype == bool

        print(f"Spatial analysis completed for {len(shape_geometries)} shapes")
        print(f"Union bounds: {union_bounds}")
        print(f"Areas: {areas}")
        print(f"Total mask coverage: {np.sum(masks)} pixels")

    # ==================== Performance Integration Tests ====================

    def test_large_scale_processing_performance(self, conversion_context):
        """Test performance with large numbers of shapes in integrated workflow."""
        # Generate large number of shapes
        n_shapes = 500

        # Create diverse shape elements
        elements = []
        np.random.seed(42)  # For reproducible results

        for i in range(n_shapes):
            if i % 3 == 0:  # Rectangle
                elem = ET.Element('rect')
                elem.set('x', str(np.random.rand() * 500))
                elem.set('y', str(np.random.rand() * 300))
                elem.set('width', str(np.random.rand() * 50 + 10))
                elem.set('height', str(np.random.rand() * 50 + 10))
                elem.set('id', f'perf_rect{i}')

            elif i % 3 == 1:  # Circle
                elem = ET.Element('circle')
                elem.set('cx', str(np.random.rand() * 500))
                elem.set('cy', str(np.random.rand() * 300))
                elem.set('r', str(np.random.rand() * 25 + 5))
                elem.set('id', f'perf_circle{i}')

            else:  # Simple polygon (square)
                x, y = np.random.rand(2) * 400
                size = np.random.rand() * 30 + 10
                points = f"{x},{y} {x+size},{y} {x+size},{y+size} {x},{y+size}"
                elem = ET.Element('polygon')
                elem.set('points', points)
                elem.set('id', f'perf_polygon{i}')

            elements.append(elem)

        # Measure conversion performance
        converter = NumPyShapeConverter()
        start_time = time.perf_counter()

        converted_geometries = []
        for element in elements:
            # Convert element
            drawingml_xml = converter.convert(element, conversion_context)

            # Create geometry for advanced operations
            if element.tag == 'rect':
                x = float(element.get('x'))
                y = float(element.get('y'))
                width = float(element.get('width'))
                height = float(element.get('height'))
                bbox = np.array([x, y, width, height])
                shape_type = ShapeType.RECTANGLE

            elif element.tag == 'circle':
                cx = float(element.get('cx'))
                cy = float(element.get('cy'))
                r = float(element.get('r'))
                bbox = np.array([cx-r, cy-r, 2*r, 2*r])
                shape_type = ShapeType.CIRCLE

            elif element.tag == 'polygon':
                points_str = element.get('points', '')
                coords = []
                for coord in points_str.replace(',', ' ').split():
                    if coord.strip():
                        coords.append(float(coord))

                points = np.array(coords).reshape(-1, 2)
                min_coords = np.min(points, axis=0)
                max_coords = np.max(points, axis=0)
                bbox = np.concatenate([min_coords, max_coords - min_coords])
                shape_type = ShapeType.POLYGON

            geometry = ShapeGeometry(
                shape_type=shape_type,
                bounding_box=bbox,
                drawingml_xml=drawingml_xml
            )
            converted_geometries.append(geometry)

        conversion_time = time.perf_counter() - start_time

        # Measure advanced operations performance
        engine = create_geometry_engine(optimization_level=2)

        # Test batch operations
        operations_start = time.perf_counter()

        # Union bounds
        union_bounds = engine.calculate_union_bounds_batch(converted_geometries)

        # Area calculations
        areas = engine.calculate_shape_areas_batch(converted_geometries)

        # Intersection tests (subset to avoid O(n²) complexity)
        subset_size = min(100, len(converted_geometries) // 2)
        shapes_a = converted_geometries[:subset_size]
        shapes_b = converted_geometries[subset_size:subset_size*2]
        if shapes_a and shapes_b and len(shapes_a) == len(shapes_b):
            intersections = engine.calculate_shape_intersections_batch(shapes_a, shapes_b)
        else:
            intersections = []

        operations_time = time.perf_counter() - operations_start
        total_time = conversion_time + operations_time

        # Performance assertions
        assert total_time < 5.0  # Should complete within 5 seconds
        assert len(converted_geometries) == n_shapes
        assert len(areas) == n_shapes
        assert union_bounds.shape == (4,)

        # Report performance metrics
        shapes_per_second = n_shapes / total_time
        print(f"\n=== Large Scale Performance Results ===")
        print(f"Processed {n_shapes} shapes in {total_time:.3f}s")
        print(f"Conversion time: {conversion_time:.3f}s")
        print(f"Advanced operations time: {operations_time:.3f}s")
        print(f"Throughput: {shapes_per_second:.1f} shapes/second")
        print(f"Intersection tests: {len(intersections)} pairs")

        # Performance target: should handle at least 100 shapes/second
        assert shapes_per_second >= 50, f"Performance too low: {shapes_per_second:.1f} shapes/second"

    def test_memory_usage_integration(self, conversion_context):
        """Test memory usage during large-scale integrated operations."""
        import gc

        # Create moderate number of complex shapes
        n_shapes = 200
        elements = []

        for i in range(n_shapes):
            # Create complex polygon with many points
            n_points = 20 + (i % 30)  # Variable complexity
            angles = np.linspace(0, 2*np.pi, n_points, endpoint=False)
            radii = 50 + 20 * np.sin(angles * 3)
            center_x, center_y = i % 20 * 30, (i // 20) * 40

            points = []
            for angle, radius in zip(angles, radii):
                x = center_x + radius * np.cos(angle)
                y = center_y + radius * np.sin(angle)
                points.extend([x, y])

            points_str = ' '.join(f"{p:.2f}" for p in points)

            elem = ET.Element('polygon')
            elem.set('points', points_str)
            elem.set('id', f'memory_polygon_{i}')
            elements.append(elem)

        # Measure memory before processing
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Process all elements
        converter = NumPyShapeConverter()
        engine = create_geometry_engine()
        geometries = []

        for element in elements:
            drawingml_xml = converter.convert(element, conversion_context)

            # Parse points for geometry
            points_str = element.get('points', '')
            coords = []
            for coord in points_str.replace(',', ' ').split():
                if coord.strip():
                    coords.append(float(coord))

            points = np.array(coords).reshape(-1, 2)
            min_coords = np.min(points, axis=0)
            max_coords = np.max(points, axis=0)
            bbox = np.concatenate([min_coords, max_coords - min_coords])

            geometry = ShapeGeometry(
                shape_type=ShapeType.POLYGON,
                bounding_box=bbox,
                points=points,
                drawingml_xml=drawingml_xml
            )
            geometries.append(geometry)

        # Perform advanced operations
        union_bounds = engine.calculate_union_bounds_batch(geometries)
        areas = engine.calculate_shape_areas_batch(geometries)
        optimized = engine.optimize_shape_complexity_batch(geometries, max_points_per_shape=15)

        # Measure memory after processing
        gc.collect()
        final_objects = len(gc.get_objects())
        memory_usage = engine.get_memory_usage()

        # Clean up
        del geometries, optimized, union_bounds, areas
        gc.collect()
        cleanup_objects = len(gc.get_objects())

        # Memory usage assertions
        object_increase = final_objects - initial_objects
        object_cleanup = final_objects - cleanup_objects

        print(f"\n=== Memory Usage Integration Results ===")
        print(f"Initial objects: {initial_objects}")
        print(f"Final objects: {final_objects} (+{object_increase})")
        print(f"After cleanup: {cleanup_objects} (freed {object_cleanup})")
        print(f"Engine memory: {memory_usage['total_mb']:.2f} MB")
        print(f"Cache entries: {memory_usage['cache_entries']}")

        # Should not leak excessive objects
        remaining_increase = cleanup_objects - initial_objects
        assert remaining_increase < 1000, f"Potential memory leak: {remaining_increase} objects remain"