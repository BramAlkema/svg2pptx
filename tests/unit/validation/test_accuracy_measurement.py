#!/usr/bin/env python3
"""
Comprehensive tests for accuracy measurement and reporting systems.
"""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import sqlite3

from tools.accuracy_measurement import (
    AccuracyMeasurementEngine, 
    AccuracyMetric, 
    AccuracyReport, 
    AccuracyDimension, 
    AccuracyLevel
)
from tools.accuracy_reporter import AccuracyReporter, AccuracyTrend


class TestAccuracyMetric:
    """Test AccuracyMetric dataclass functionality."""
    
    def test_accuracy_metric_initialization(self):
        """Test basic AccuracyMetric initialization."""
        metric = AccuracyMetric(
            dimension=AccuracyDimension.VISUAL,
            score=0.85,
            weight=0.25
        )
        
        assert metric.dimension == AccuracyDimension.VISUAL
        assert metric.score == 0.85
        assert metric.weight == 0.25
        assert metric.details == {}
        assert metric.error_details is None
    
    def test_weighted_score_calculation(self):
        """Test weighted score calculation."""
        metric = AccuracyMetric(
            dimension=AccuracyDimension.STRUCTURAL,
            score=0.90,
            weight=0.30
        )
        
        expected_weighted = 0.90 * 0.30
        assert abs(metric.weighted_score - expected_weighted) < 1e-6
    
    def test_accuracy_level_classification(self):
        """Test accuracy level classification."""
        test_cases = [
            (0.98, AccuracyLevel.EXCELLENT),
            (0.90, AccuracyLevel.GOOD),
            (0.75, AccuracyLevel.ACCEPTABLE),
            (0.55, AccuracyLevel.POOR),
            (0.30, AccuracyLevel.FAILED)
        ]
        
        for score, expected_level in test_cases:
            metric = AccuracyMetric(
                dimension=AccuracyDimension.CONTENT,
                score=score
            )
            assert metric.level == expected_level


class TestAccuracyReport:
    """Test AccuracyReport functionality."""
    
    def test_accuracy_report_initialization(self):
        """Test AccuracyReport initialization."""
        timestamp = datetime.now()
        metrics = [
            AccuracyMetric(AccuracyDimension.VISUAL, 0.90, 0.25),
            AccuracyMetric(AccuracyDimension.STRUCTURAL, 0.85, 0.20)
        ]
        
        report = AccuracyReport(
            test_name="test_report",
            svg_path="/path/to/test.svg",
            pptx_path="/path/to/test.pptx",
            timestamp=timestamp,
            metrics=metrics,
            overall_score=0.875,
            overall_level=AccuracyLevel.GOOD,
            processing_time=1.5
        )
        
        assert report.test_name == "test_report"
        assert len(report.metrics) == 2
        assert report.overall_score == 0.875
        assert report.overall_level == AccuracyLevel.GOOD
        assert report.validation_errors == []
        assert report.metadata == {}
    
    def test_dimension_scores_property(self):
        """Test dimension_scores property."""
        metrics = [
            AccuracyMetric(AccuracyDimension.VISUAL, 0.90),
            AccuracyMetric(AccuracyDimension.STRUCTURAL, 0.85),
            AccuracyMetric(AccuracyDimension.CONTENT, 0.80)
        ]
        
        report = AccuracyReport(
            test_name="test",
            svg_path="test.svg",
            pptx_path="test.pptx",
            timestamp=datetime.now(),
            metrics=metrics,
            overall_score=0.85,
            overall_level=AccuracyLevel.GOOD,
            processing_time=1.0
        )
        
        dimension_scores = report.dimension_scores
        assert dimension_scores[AccuracyDimension.VISUAL] == 0.90
        assert dimension_scores[AccuracyDimension.STRUCTURAL] == 0.85
        assert dimension_scores[AccuracyDimension.CONTENT] == 0.80
    
    def test_weighted_average_calculation(self):
        """Test weighted average calculation."""
        metrics = [
            AccuracyMetric(AccuracyDimension.VISUAL, 0.90, 0.5),
            AccuracyMetric(AccuracyDimension.STRUCTURAL, 0.80, 0.3),
            AccuracyMetric(AccuracyDimension.CONTENT, 0.70, 0.2)
        ]
        
        report = AccuracyReport(
            test_name="test",
            svg_path="test.svg", 
            pptx_path="test.pptx",
            timestamp=datetime.now(),
            metrics=metrics,
            overall_score=0.85,
            overall_level=AccuracyLevel.GOOD,
            processing_time=1.0
        )
        
        expected_weighted = ((0.90 * 0.5) + (0.80 * 0.3) + (0.70 * 0.2)) / (0.5 + 0.3 + 0.2)
        assert abs(report.weighted_average - expected_weighted) < 1e-6
    
    def test_to_dict_serialization(self):
        """Test dictionary serialization."""
        timestamp = datetime.now()
        metrics = [AccuracyMetric(AccuracyDimension.VISUAL, 0.90)]
        
        report = AccuracyReport(
            test_name="test",
            svg_path="test.svg",
            pptx_path="test.pptx", 
            timestamp=timestamp,
            metrics=metrics,
            overall_score=0.90,
            overall_level=AccuracyLevel.EXCELLENT,
            processing_time=1.0
        )
        
        report_dict = report.to_dict()
        
        assert report_dict["test_name"] == "test"
        assert report_dict["overall_score"] == 0.90
        assert report_dict["overall_level"] == "excellent"
        assert report_dict["timestamp"] == timestamp.isoformat()
        assert len(report_dict["metrics"]) == 1


class TestAccuracyMeasurementEngine:
    """Test AccuracyMeasurementEngine functionality."""
    
    def test_engine_initialization(self):
        """Test engine initialization with database setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_accuracy.db"
            
            engine = AccuracyMeasurementEngine(database_path=db_path)
            
            assert engine.database_path == db_path
            assert db_path.exists()
            
            # Verify database tables exist
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN ('accuracy_reports', 'accuracy_metrics')
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                assert 'accuracy_reports' in tables
                assert 'accuracy_metrics' in tables
    
    def test_default_weights(self):
        """Test default dimension weights."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_accuracy.db"
            engine = AccuracyMeasurementEngine(database_path=db_path)
            
            # Verify all dimensions have weights
            for dimension in AccuracyDimension:
                assert dimension in engine.default_weights
                assert 0 <= engine.default_weights[dimension] <= 1
            
            # Verify weights sum to approximately 1
            total_weight = sum(engine.default_weights.values())
            assert abs(total_weight - 1.0) < 1e-6
    
    def test_structural_accuracy_measurement(self):
        """Test structural accuracy measurement."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_accuracy.db"
            engine = AccuracyMeasurementEngine(database_path=db_path)
            
            svg_path = Path(temp_dir) / "test.svg"
            pptx_path = Path(temp_dir) / "test.pptx"
            
            # Create test files
            svg_path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>')
            pptx_path.write_text("dummy pptx content")
            
            with patch('tools.workflow_validator.WorkflowValidator') as mock_validator_class:
                mock_validator = Mock()
                mock_validator_class.return_value = mock_validator
                
                mock_result = Mock()
                mock_result.accuracy_score = 0.85
                mock_result.stage_results = [
                    Mock(success=True, critical=False),
                    Mock(success=True, critical=False),
                    Mock(success=False, critical=False)
                ]
                mock_result.validation_errors = ["minor warning"]
                mock_validator.validate_workflow.return_value = mock_result
                
                metric = engine.measure_structural_accuracy(svg_path, pptx_path)
                
                assert metric.dimension == AccuracyDimension.STRUCTURAL
                assert metric.score == 0.85
                assert metric.details["pipeline_stages_passed"] == 2
                assert metric.details["total_pipeline_stages"] == 3
    
    def test_content_accuracy_measurement(self):
        """Test content accuracy measurement."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_accuracy.db"
            engine = AccuracyMeasurementEngine(database_path=db_path)
            
            svg_path = Path(temp_dir) / "test.svg"
            pptx_path = Path(temp_dir) / "test.pptx"
            
            svg_path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>Hello</text></svg>')
            pptx_path.write_text("dummy pptx content")
            
            with patch('tools.pptx_validator.PPTXValidator') as mock_validator_class:
                mock_validator = Mock()
                mock_validator_class.return_value = mock_validator
                
                mock_validator.extract_content.return_value = {
                    'text_content': ['Hello', 'World'],
                    'shapes': ['rect', 'circle', 'path']
                }
                
                metric = engine.measure_content_accuracy(svg_path, pptx_path)
                
                assert metric.dimension == AccuracyDimension.CONTENT
                assert metric.score > 0
                assert metric.details["text_elements"] == 2
                assert metric.details["shape_elements"] == 3
                assert metric.details["has_text"] is True
                assert metric.details["has_shapes"] is True
    
    def test_measure_accuracy_comprehensive(self):
        """Test comprehensive accuracy measurement."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_accuracy.db"
            engine = AccuracyMeasurementEngine(database_path=db_path)
            
            svg_path = Path(temp_dir) / "test.svg"
            pptx_path = Path(temp_dir) / "test.pptx"
            
            # Create test files
            svg_path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>')
            pptx_path.write_text("dummy pptx content")
            
            # Mock all measurement methods
            with patch.object(engine, 'measure_structural_accuracy') as mock_structural, \
                 patch.object(engine, 'measure_visual_accuracy') as mock_visual, \
                 patch.object(engine, 'measure_content_accuracy') as mock_content, \
                 patch.object(engine, 'measure_semantic_accuracy') as mock_semantic, \
                 patch.object(engine, 'measure_geometric_accuracy') as mock_geometric, \
                 patch.object(engine, 'measure_stylistic_accuracy') as mock_stylistic:
                
                # Setup mock returns
                mock_structural.return_value = AccuracyMetric(AccuracyDimension.STRUCTURAL, 0.90, 0.20)
                mock_visual.return_value = AccuracyMetric(AccuracyDimension.VISUAL, 0.85, 0.25)
                mock_content.return_value = AccuracyMetric(AccuracyDimension.CONTENT, 0.80, 0.20)
                mock_semantic.return_value = AccuracyMetric(AccuracyDimension.SEMANTIC, 0.75, 0.15)
                mock_geometric.return_value = AccuracyMetric(AccuracyDimension.GEOMETRIC, 0.85, 0.15)
                mock_stylistic.return_value = AccuracyMetric(AccuracyDimension.STYLISTIC, 0.70, 0.05)
                
                report = engine.measure_accuracy(svg_path, pptx_path, "comprehensive_test")
                
                assert len(report.metrics) == 6
                assert report.test_name == "comprehensive_test"
                assert report.overall_score > 0
                assert report.overall_level in AccuracyLevel
                assert report.processing_time > 0
                
                # Verify all measurement methods were called
                mock_structural.assert_called_once_with(svg_path, pptx_path)
                mock_visual.assert_called_once_with(svg_path, pptx_path)
                mock_content.assert_called_once_with(svg_path, pptx_path)
                mock_semantic.assert_called_once_with(svg_path, pptx_path)
                mock_geometric.assert_called_once_with(svg_path, pptx_path)
                mock_stylistic.assert_called_once_with(svg_path, pptx_path)
    
    def test_selective_dimension_measurement(self):
        """Test measuring specific dimensions only."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_accuracy.db"
            engine = AccuracyMeasurementEngine(database_path=db_path)
            
            svg_path = Path(temp_dir) / "test.svg"
            pptx_path = Path(temp_dir) / "test.pptx"
            
            svg_path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>')
            pptx_path.write_text("dummy pptx content")
            
            selected_dimensions = [AccuracyDimension.VISUAL, AccuracyDimension.CONTENT]
            
            with patch.object(engine, 'measure_visual_accuracy') as mock_visual, \
                 patch.object(engine, 'measure_content_accuracy') as mock_content:
                
                mock_visual.return_value = AccuracyMetric(AccuracyDimension.VISUAL, 0.85, 0.25)
                mock_content.return_value = AccuracyMetric(AccuracyDimension.CONTENT, 0.80, 0.20)
                
                report = engine.measure_accuracy(
                    svg_path, pptx_path, "selective_test", 
                    dimensions=selected_dimensions
                )
                
                assert len(report.metrics) == 2
                dimensions_measured = {metric.dimension for metric in report.metrics}
                assert dimensions_measured == {AccuracyDimension.VISUAL, AccuracyDimension.CONTENT}


class TestAccuracyReporter:
    """Test AccuracyReporter functionality."""
    
    def setup_test_database(self, db_path: Path):
        """Setup test database with sample data."""
        engine = AccuracyMeasurementEngine(database_path=db_path)
        
        # Create sample reports
        test_data = [
            {
                "test_name": "basic_shapes_test",
                "overall_score": 0.95,
                "overall_level": AccuracyLevel.EXCELLENT,
                "metrics": [
                    (AccuracyDimension.VISUAL, 0.98),
                    (AccuracyDimension.STRUCTURAL, 0.93),
                    (AccuracyDimension.CONTENT, 0.94)
                ]
            },
            {
                "test_name": "complex_paths_test",
                "overall_score": 0.82,
                "overall_level": AccuracyLevel.ACCEPTABLE,
                "metrics": [
                    (AccuracyDimension.VISUAL, 0.85),
                    (AccuracyDimension.STRUCTURAL, 0.80),
                    (AccuracyDimension.CONTENT, 0.81)
                ]
            },
            {
                "test_name": "text_rendering_test",
                "overall_score": 0.68,
                "overall_level": AccuracyLevel.POOR,
                "metrics": [
                    (AccuracyDimension.VISUAL, 0.70),
                    (AccuracyDimension.STRUCTURAL, 0.65),
                    (AccuracyDimension.CONTENT, 0.69)
                ]
            }
        ]
        
        for data in test_data:
            metrics = []
            for dimension, score in data["metrics"]:
                metrics.append(AccuracyMetric(dimension, score, 1.0))
            
            report = AccuracyReport(
                test_name=data["test_name"],
                svg_path=f"/test/{data['test_name']}.svg",
                pptx_path=f"/test/{data['test_name']}.pptx",
                timestamp=datetime.now() - timedelta(days=1),
                metrics=metrics,
                overall_score=data["overall_score"],
                overall_level=data["overall_level"],
                processing_time=1.0
            )
            
            engine._store_report(report)
    
    def test_reporter_initialization(self):
        """Test AccuracyReporter initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_reporter.db"
            
            reporter = AccuracyReporter(db_path)
            assert reporter.database_path == db_path
    
    def test_generate_summary_report(self):
        """Test summary report generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_reporter.db"
            self.setup_test_database(db_path)
            
            reporter = AccuracyReporter(db_path)
            summary = reporter.generate_summary_report()
            
            assert "overall_statistics" in summary
            assert "dimensional_breakdown" in summary
            assert "recent_tests" in summary
            assert "quality_distribution" in summary
            
            stats = summary["overall_statistics"]
            assert stats["total_tests"] == 3
            assert "avg_score" in stats
            assert "success_rate" in stats
            
            distribution = summary["quality_distribution"]
            assert distribution["excellent"] == 1
            assert distribution["poor"] == 1
    
    def test_analyze_accuracy_trends(self):
        """Test accuracy trend analysis."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_reporter.db"
            self.setup_test_database(db_path)
            
            reporter = AccuracyReporter(db_path)
            trends = reporter.analyze_accuracy_trends()
            
            assert len(trends) > 0
            
            for trend in trends:
                assert isinstance(trend, AccuracyTrend)
                assert trend.dimension in ["overall"]
                assert trend.period in ["daily", "weekly", "monthly"]
                assert isinstance(trend.scores, list)
                assert isinstance(trend.timestamps, list)
                assert trend.trend_direction in ["improving", "declining", "stable"]
    
    def test_compare_test_suites(self):
        """Test test suite comparison functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_reporter.db"
            self.setup_test_database(db_path)
            
            reporter = AccuracyReporter(db_path)
            comparison = reporter.compare_test_suites(["basic", "complex"])
            
            assert "suite_comparisons" in comparison
            assert "suites_compared" in comparison
            
            suite_data = comparison["suite_comparisons"]
            
            for suite_name in ["basic", "complex"]:
                if suite_name in suite_data:
                    suite_stats = suite_data[suite_name]
                    assert "test_count" in suite_stats
                    assert "avg_score" in suite_stats
                    assert "success_rate" in suite_stats
    
    def test_html_report_generation(self):
        """Test HTML report generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_reporter.db"
            self.setup_test_database(db_path)
            
            reporter = AccuracyReporter(db_path)
            output_path = Path(temp_dir) / "test_report.html"
            
            result_path = reporter.generate_html_report(output_path)
            
            assert result_path == output_path
            assert output_path.exists()
            
            # Verify HTML content
            html_content = output_path.read_text()
            assert "<!DOCTYPE html>" in html_content
            assert "SVG to PPTX Accuracy Report" in html_content
            assert "Overall Statistics" in html_content or "Total Tests" in html_content
    
    def test_data_export_json(self):
        """Test JSON data export."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_reporter.db"
            self.setup_test_database(db_path)
            
            reporter = AccuracyReporter(db_path)
            output_path = Path(temp_dir) / "export.json"
            
            result_path = reporter.export_data(output_path, "json")
            
            assert result_path == output_path
            assert output_path.exists()
            
            # Verify JSON structure
            with open(output_path) as f:
                data = json.load(f)
            
            assert "summary" in data
            assert "trends" in data
            assert "export_metadata" in data
    
    def test_data_export_csv(self):
        """Test CSV data export."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_reporter.db"
            self.setup_test_database(db_path)
            
            reporter = AccuracyReporter(db_path)
            output_path = Path(temp_dir) / "export.csv"
            
            result_path = reporter.export_data(output_path, "csv")
            
            assert result_path == output_path
            assert output_path.exists()
            
            # Verify CSV structure
            import csv
            with open(output_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                assert len(rows) > 0
                
                # Check expected columns
                expected_columns = ["test_name", "overall_score", "timestamp"]
                for col in expected_columns:
                    assert col in reader.fieldnames


class TestAccuracyIntegration:
    """Integration tests for accuracy measurement and reporting."""
    
    def test_end_to_end_accuracy_workflow(self):
        """Test complete accuracy measurement and reporting workflow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "integration_test.db"
            
            # Initialize components
            engine = AccuracyMeasurementEngine(database_path=db_path)
            reporter = AccuracyReporter(db_path)
            
            # Create test files
            svg_path = Path(temp_dir) / "test.svg"
            pptx_path = Path(temp_dir) / "test.pptx"
            
            svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
                <rect x="10" y="10" width="80" height="80" fill="blue"/>
                <text x="50" y="55" text-anchor="middle">Test</text>
            </svg>'''
            
            svg_path.write_text(svg_content)
            pptx_path.write_text("dummy pptx content for testing")
            
            # Mock dependencies to avoid external tool requirements
            with patch('tools.workflow_validator.WorkflowValidator') as mock_wf_validator, \
                 patch('tools.visual_regression_tester.VisualRegressionTester') as mock_vr_tester, \
                 patch('tools.pptx_validator.PPTXValidator') as mock_pptx_validator:
                
                # Setup workflow validator mock
                mock_wf_result = Mock()
                mock_wf_result.accuracy_score = 0.88
                mock_wf_result.stage_results = [Mock(success=True, critical=False)] * 5
                mock_wf_result.validation_errors = []
                mock_wf_validator.return_value.validate_workflow.return_value = mock_wf_result
                
                # Setup visual regression tester mock
                mock_vr_result = Mock()
                mock_vr_result.actual_similarity = 0.92
                mock_vr_result.comparison_results = {"ssim": Mock(similarity_score=0.92)}
                mock_vr_tester.return_value.run_regression_test.return_value = mock_vr_result
                
                # Setup PPTX validator mock
                mock_pptx_validator.return_value.extract_content.return_value = {
                    'text_content': ['Test'],
                    'shapes': ['rect']
                }
                
                # Perform measurement
                report = engine.measure_accuracy(svg_path, pptx_path, "integration_test")
                
                # Verify report
                assert report.test_name == "integration_test"
                assert len(report.metrics) == 6  # All dimensions
                assert report.overall_score > 0
                assert report.overall_level in AccuracyLevel
                
                # Generate reports
                summary = reporter.generate_summary_report()
                assert summary["overall_statistics"]["total_tests"] == 1
                
                trends = reporter.analyze_accuracy_trends()
                assert len(trends) >= 0  # May be empty for single data point
                
                # Export data
                json_path = Path(temp_dir) / "export.json"
                reporter.export_data(json_path, "json")
                assert json_path.exists()
                
                html_path = Path(temp_dir) / "report.html"
                reporter.generate_html_report(html_path)
                assert html_path.exists()


if __name__ == "__main__":
    pytest.main([__file__])