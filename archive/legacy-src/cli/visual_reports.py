#!/usr/bin/env python3
"""
CLI Visual Report Coordinator for SVG2PPTX.

This module coordinates visual report generation from CLI interface,
integrating existing visual comparison infrastructure with CLI arguments
to provide unified visual reporting functionality.

Enhanced Features:
- Cross-platform automatic browser opening (Windows, macOS, Linux)
- CI/automated environment detection with graceful fallback
- User preference handling via environment variables
- Security considerations for browser launching
- Comprehensive error handling and platform-specific fallbacks
- Unified HTML template rendering with Handlebars-like syntax
- Enhanced progress indicators with time estimation and cancellation support
- File size-based duration estimation for LibreOffice operations
- Quiet mode support for automated/CI environments
- Real-time progress bars with ETA calculations
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, Tuple
import time
import shutil
import json
import re
import platform
import subprocess
import signal
import threading
import uuid

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from deliverables.visual_comparison_generator import VisualComparisonGenerator

# Import drop-in Google Slides integration
try:
    from .google_slides_integration import integrate_google_slides, check_google_auth_status
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

# Import visual diff generator
try:
    from .visual_diff import CLIVisualDiffGenerator
    VISUAL_DIFF_AVAILABLE = True
except ImportError:
    VISUAL_DIFF_AVAILABLE = False

# Import version management
try:
    from .version import VersionInfo
    VERSION_INFO_AVAILABLE = True
except ImportError:
    VERSION_INFO_AVAILABLE = False


class EnhancedProgressIndicator:
    """
    Enhanced progress indicator with time estimation, cancellation, and quiet mode.

    Provides comprehensive progress tracking for long-running operations with:
    - Real-time progress bars with percentage
    - Estimated time remaining calculations
    - Graceful cancellation support (Ctrl+C)
    - Quiet mode for automated/CI environments
    - File size-based operation estimation
    - Clear error messaging with progress context
    """

    def __init__(self, quiet_mode: bool = False, enable_cancellation: bool = True):
        """
        Initialize enhanced progress indicator.

        Args:
            quiet_mode: If True, minimal output for automated environments
            enable_cancellation: If True, set up Ctrl+C handling
        """
        self.quiet_mode = quiet_mode
        self.enable_cancellation = enable_cancellation
        self.start_time: Optional[float] = None
        self.last_update_time: Optional[float] = None
        self.operation_name: str = "Operation"
        self.cancelled = False
        self.estimated_duration: Optional[float] = None

        # Set up cancellation handling
        if enable_cancellation:
            self._setup_cancellation_handler()

    def _setup_cancellation_handler(self):
        """Set up Ctrl+C cancellation handling."""
        def signal_handler(signum, frame):
            self.cancelled = True
            if not self.quiet_mode:
                print(f"\n⚠️  Cancellation requested... stopping {self.operation_name}")

        signal.signal(signal.SIGINT, signal_handler)

    def start_operation(self, operation_name: str, estimated_duration: Optional[float] = None):
        """
        Start tracking a new operation.

        Args:
            operation_name: Human-readable name of the operation
            estimated_duration: Estimated duration in seconds (optional)
        """
        self.operation_name = operation_name
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.estimated_duration = estimated_duration
        self.cancelled = False

        if not self.quiet_mode:
            if estimated_duration:
                print(f"🚀 Starting {operation_name} (estimated: {estimated_duration:.1f}s)")
            else:
                print(f"🚀 Starting {operation_name}")

    def update_progress(self, percentage: float, message: str = "") -> bool:
        """
        Update progress display.

        Args:
            percentage: Progress percentage (0-100)
            message: Additional status message

        Returns:
            False if operation was cancelled, True otherwise
        """
        if self.cancelled:
            return False

        current_time = time.time()

        # Throttle updates to avoid spam (max once per 0.1 seconds)
        if self.last_update_time and (current_time - self.last_update_time) < 0.1:
            if percentage < 100:  # Always show 100% completion
                return True

        self.last_update_time = current_time

        if self.quiet_mode:
            # Minimal output for quiet mode
            if percentage in [25, 50, 75, 100]:
                print(f"📊 {self.operation_name}: {percentage}%")
            return True

        # Calculate timing information
        elapsed = current_time - self.start_time if self.start_time else 0

        # Estimate remaining time
        eta_str = ""
        if percentage > 5 and elapsed > 1:  # Only estimate after some progress
            if self.estimated_duration:
                # Use provided estimate
                remaining = max(0, self.estimated_duration - elapsed)
            else:
                # Calculate based on current progress
                estimated_total = elapsed / (percentage / 100)
                remaining = max(0, estimated_total - elapsed)

            if remaining > 60:
                eta_str = f" (ETA: {remaining/60:.1f}m)"
            elif remaining > 0:
                eta_str = f" (ETA: {remaining:.0f}s)"

        # Create progress bar
        bar_width = 20
        filled_width = int(percentage / 5)  # 5% per character
        progress_bar = "█" * filled_width + "░" * (bar_width - filled_width)

        # Format timing
        elapsed_str = f"{elapsed:.1f}s" if elapsed < 60 else f"{elapsed/60:.1f}m"

        # Display progress
        if message:
            status_text = f"{message}{eta_str}"
        else:
            status_text = f"{self.operation_name}{eta_str}"

        print(f"\r📊 [{progress_bar}] {percentage:3.0f}% {status_text} ({elapsed_str})",
              end="", flush=True)

        # New line when complete
        if percentage >= 100:
            print()

        return True

    def complete_operation(self, success: bool = True, final_message: str = ""):
        """
        Mark operation as complete.

        Args:
            success: Whether operation completed successfully
            final_message: Final status message
        """
        if self.start_time:
            elapsed = time.time() - self.start_time
            elapsed_str = f"{elapsed:.1f}s" if elapsed < 60 else f"{elapsed/60:.1f}m"

            if success and not self.cancelled:
                if not self.quiet_mode:
                    if final_message:
                        print(f"✅ {final_message} (completed in {elapsed_str})")
                    else:
                        print(f"✅ {self.operation_name} completed in {elapsed_str}")
                else:
                    print(f"✅ {self.operation_name}: completed")
            elif self.cancelled:
                print(f"🚫 {self.operation_name} cancelled after {elapsed_str}")
            else:
                if final_message:
                    print(f"❌ {final_message} (after {elapsed_str})")
                else:
                    print(f"❌ {self.operation_name} failed after {elapsed_str}")

    def error_with_context(self, error_message: str):
        """
        Display error with progress context.

        Args:
            error_message: Error description
        """
        if self.start_time:
            elapsed = time.time() - self.start_time
            elapsed_str = f"{elapsed:.1f}s" if elapsed < 60 else f"{elapsed/60:.1f}m"
            print(f"\n❌ {self.operation_name} failed after {elapsed_str}: {error_message}")
        else:
            print(f"❌ {error_message}")

    def is_cancelled(self) -> bool:
        """Check if operation was cancelled."""
        return self.cancelled

    @staticmethod
    def estimate_screenshot_duration(file_size_bytes: int) -> float:
        """
        Estimate LibreOffice screenshot duration based on file size.

        Args:
            file_size_bytes: PPTX file size in bytes

        Returns:
            Estimated duration in seconds
        """
        # Base time for LibreOffice startup
        base_time = 3.0

        # Additional time based on file size (rough estimation)
        size_mb = file_size_bytes / (1024 * 1024)
        if size_mb < 1:
            size_factor = 1.0
        elif size_mb < 5:
            size_factor = 2.0
        elif size_mb < 10:
            size_factor = 4.0
        else:
            size_factor = 8.0

        return base_time + size_factor

    @staticmethod
    def estimate_template_duration(template_complexity: int = 1) -> float:
        """
        Estimate template rendering duration.

        Args:
            template_complexity: Complexity factor (1-10)

        Returns:
            Estimated duration in seconds
        """
        base_time = 0.5  # Basic template rendering
        complexity_factor = template_complexity * 0.1
        return base_time + complexity_factor


@dataclass
class VisualReportConfig:
    """
    Configuration for visual report generation.

    This dataclass encapsulates all settings needed for generating
    visual comparison reports from the CLI interface.
    """
    svg_file: Path
    pptx_file: Path
    output_dir: Path
    include_debug: bool = True
    include_google_slides: bool = False
    auto_open_browser: bool = False
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Convert string paths to Path objects
        if isinstance(self.svg_file, str):
            self.svg_file = Path(self.svg_file)
        if isinstance(self.pptx_file, str):
            self.pptx_file = Path(self.pptx_file)
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)

        # Validate that required files exist
        if not self.svg_file.exists():
            raise FileNotFoundError(f"SVG file not found: {self.svg_file}")
        if not self.pptx_file.exists():
            raise FileNotFoundError(f"PPTX file not found: {self.pptx_file}")

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_report_filename(self) -> str:
        """
        Generate timestamped report filename.

        Returns:
            Filename for the HTML report with timestamp and SVG name
        """
        timestamp_str = self.timestamp.strftime('%Y%m%d_%H%M%S')
        svg_name = self.svg_file.stem
        return f"{svg_name}_visual_report_{timestamp_str}.html"

    def get_timestamped_output_dir(self) -> Path:
        """
        Get timestamped subdirectory for this report.

        Returns:
            Path to timestamped subdirectory within output_dir
        """
        date_str = self.timestamp.strftime('%Y-%m-%d')
        time_str = self.timestamp.strftime('%H%M%S')
        return self.output_dir / date_str / time_str


class CLITemplateRenderer:
    """
    Simple template rendering engine for CLI visual reports.

    Provides Handlebars-like template rendering without external dependencies.
    Supports basic variable substitution, conditional blocks, and iterations.
    """

    def __init__(self, template_path: Path):
        """
        Initialize template renderer with template file.

        Args:
            template_path: Path to HTML template file
        """
        self.template_path = template_path
        self.template_content = self._load_template()

    def _load_template(self) -> str:
        """Load template content from file."""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to load template {self.template_path}: {e}")

    def render(self, context: Dict[str, Any]) -> str:
        """
        Render template with provided context data.

        Args:
            context: Dictionary containing template variables

        Returns:
            Rendered HTML string
        """
        content = self.template_content

        # Handle conditional blocks first ({{#if condition}} ... {{/if}})
        content = self._handle_conditionals(content, context)

        # Handle iterations ({{#each items}} ... {{/each}})
        content = self._handle_iterations(content, context)

        # Handle variable substitutions ({{variable}})
        content = self._handle_variables(content, context)

        return content

    def _handle_conditionals(self, content: str, context: Dict[str, Any]) -> str:
        """Handle {{#if}} conditional blocks."""
        pattern = r'\{\{#if\s+([^}]+)\}\}(.*?)\{\{/if\}\}'

        def replace_conditional(match):
            condition = match.group(1).strip()
            block_content = match.group(2)

            # Evaluate condition
            value = self._get_nested_value(context, condition)
            if self._is_truthy(value):
                return block_content
            else:
                return ""

        return re.sub(pattern, replace_conditional, content, flags=re.DOTALL)

    def _handle_iterations(self, content: str, context: Dict[str, Any]) -> str:
        """Handle {{#each}} iteration blocks."""
        pattern = r'\{\{#each\s+([^}]+)\}\}(.*?)\{\{/each\}\}'

        def replace_iteration(match):
            array_name = match.group(1).strip()
            block_content = match.group(2)

            # Get array from context
            array_value = self._get_nested_value(context, array_name)
            if not isinstance(array_value, (list, tuple)):
                return ""

            # Render each item
            result = ""
            for item in array_value:
                # Create item context
                item_context = context.copy()
                if isinstance(item, dict):
                    item_context.update(item)
                else:
                    item_context['this'] = item

                # Render block for this item
                rendered_block = self._handle_variables(block_content, item_context)
                result += rendered_block

            return result

        return re.sub(pattern, replace_iteration, content, flags=re.DOTALL)

    def _handle_variables(self, content: str, context: Dict[str, Any]) -> str:
        """Handle {{variable}} substitutions."""
        pattern = r'\{\{([^#/][^}]*)\}\}'

        def replace_variable(match):
            variable_name = match.group(1).strip()
            value = self._get_nested_value(context, variable_name)

            # Convert to string and escape HTML
            if value is None:
                return ""
            elif isinstance(value, bool):
                return "true" if value else "false"
            elif isinstance(value, (int, float)):
                return str(value)
            else:
                return self._escape_html(str(value))

        return re.sub(pattern, replace_variable, content)

    def _get_nested_value(self, context: Dict[str, Any], key: str) -> Any:
        """Get value from context, supporting dot notation (e.g., 'user.name')."""
        try:
            # Handle simple key
            if '.' not in key:
                return context.get(key)

            # Handle nested key
            keys = key.split('.')
            value = context
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    return None
                if value is None:
                    return None

            return value
        except (KeyError, TypeError):
            return None

    def _is_truthy(self, value: Any) -> bool:
        """Check if value is truthy for conditional rendering."""
        if value is None or value is False:
            return False
        if isinstance(value, (str, list, dict)) and len(value) == 0:
            return False
        if isinstance(value, (int, float)) and value == 0:
            return False
        return True

    def _escape_html(self, text: str) -> str:
        """Basic HTML escaping."""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#x27;'))


class CLIVisualReportCoordinator:
    """
    Coordinates visual report generation from CLI interface.

    Integrates existing visual comparison infrastructure with CLI arguments
    to provide unified visual reporting functionality.
    """

    def __init__(self, output_dir: Optional[Path] = None, enable_google_slides: bool = False):
        """
        Initialize coordinator with output directory and Google Slides integration.

        Args:
            output_dir: Directory for visual report outputs (default: ./reports)
            enable_google_slides: Whether to include Google Slides integration
        """
        self.output_dir = Path(output_dir) if output_dir else Path('./reports')
        self.enable_google_slides = enable_google_slides
        self.visual_generator: Optional[VisualComparisonGenerator] = None

        # Ensure output directory exists with proper validation
        self._ensure_output_directory()

        # Initialize visual comparison generator
        self._initialize_visual_generator()

    def _ensure_output_directory(self):
        """
        Ensure output directory exists with proper validation and permissions.

        Raises:
            PermissionError: If directory cannot be created due to permissions
            OSError: If directory creation fails for other reasons
        """
        try:
            # Check if path exists and is not a directory
            if self.output_dir.exists() and not self.output_dir.is_dir():
                raise OSError(f"Output path exists but is not a directory: {self.output_dir}")

            # Create directory with parents if needed
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Test write permissions by creating and removing a test file
            test_file = self.output_dir / ".write_test"
            try:
                test_file.touch()
                test_file.unlink()
            except (PermissionError, OSError) as e:
                raise PermissionError(f"No write permission in directory: {self.output_dir}")

        except PermissionError:
            raise
        except Exception as e:
            raise OSError(f"Cannot create output directory {self.output_dir}: {e}")

    def _initialize_visual_generator(self):
        """Initialize the visual comparison generator for CLI use."""
        try:
            self.visual_generator = VisualComparisonGenerator(output_dir=self.output_dir)
        except Exception as e:
            print(f"Warning: Could not initialize visual comparison generator: {e}")
            self.visual_generator = None

    def create_timestamped_directory(self, base_name: str = None) -> Path:
        """
        Create a timestamped directory for organizing reports.

        Args:
            base_name: Optional base name for the directory (default: uses current timestamp)

        Returns:
            Path to created timestamped directory

        Raises:
            OSError: If directory creation fails
        """
        try:
            now = datetime.now()
            date_str = now.strftime('%Y-%m-%d')
            time_str = now.strftime('%H%M%S')

            if base_name:
                dir_name = f"{date_str}_{base_name}_{time_str}"
            else:
                dir_name = f"{date_str}/{time_str}"

            timestamp_dir = self.output_dir / dir_name
            timestamp_dir.mkdir(parents=True, exist_ok=True)

            return timestamp_dir

        except Exception as e:
            raise OSError(f"Cannot create timestamped directory: {e}")

    def get_directory_size(self, directory: Path = None) -> float:
        """
        Calculate total size of directory in MB.

        Args:
            directory: Directory to analyze (default: output_dir)

        Returns:
            Total size in megabytes
        """
        target_dir = directory or self.output_dir
        total_size = 0

        try:
            for file_path in target_dir.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size / (1024 * 1024)  # Convert to MB
        except Exception as e:
            print(f"Warning: Could not calculate directory size: {e}")
            return 0.0

    def validate_directory_structure(self) -> Dict[str, Any]:
        """
        Validate and analyze current directory structure.

        Returns:
            Dictionary with validation results and recommendations
        """
        validation = {
            'is_valid': True,
            'issues': [],
            'recommendations': [],
            'structure_info': {}
        }

        try:
            # Check if output directory exists and is writable
            if not self.output_dir.exists():
                validation['issues'].append(f"Output directory does not exist: {self.output_dir}")
                validation['is_valid'] = False
            elif not self.output_dir.is_dir():
                validation['issues'].append(f"Output path is not a directory: {self.output_dir}")
                validation['is_valid'] = False
            else:
                # Test write permissions
                try:
                    test_file = self.output_dir / ".permission_test"
                    test_file.touch()
                    test_file.unlink()
                except (PermissionError, OSError):
                    validation['issues'].append(f"No write permission in directory: {self.output_dir}")
                    validation['is_valid'] = False

            # Analyze structure
            if self.output_dir.exists():
                date_dirs = list(self.output_dir.glob("????-??-??"))
                total_size = self.get_directory_size()

                validation['structure_info'] = {
                    'date_directories': len(date_dirs),
                    'total_size_mb': round(total_size, 2),
                    'oldest_report': None,
                    'newest_report': None
                }

                # Find oldest and newest reports
                if date_dirs:
                    sorted_dirs = sorted(date_dirs, key=lambda d: d.name)
                    validation['structure_info']['oldest_report'] = sorted_dirs[0].name
                    validation['structure_info']['newest_report'] = sorted_dirs[-1].name

                # Add recommendations based on analysis
                if total_size > 100:  # MB
                    validation['recommendations'].append("Consider cleaning up old reports (>100MB total)")
                if len(date_dirs) > 30:
                    validation['recommendations'].append("Consider cleaning up old date directories (>30 days)")

        except Exception as e:
            validation['issues'].append(f"Validation error: {e}")
            validation['is_valid'] = False

        return validation

    def generate_visual_report(self, svg_file: Path, pptx_file: Path,
                             include_debug: bool = True,
                             auto_open: bool = False) -> Optional[Path]:
        """
        Generate comprehensive visual report from existing conversion output.

        Args:
            svg_file: Source SVG file path
            pptx_file: Generated PPTX file path
            include_debug: Include debug logging and performance metrics
            auto_open: Automatically open report in browser

        Returns:
            Path to generated HTML report file, or None if generation failed
        """
        try:
            # Create configuration
            config = VisualReportConfig(
                svg_file=svg_file,
                pptx_file=pptx_file,
                output_dir=self.output_dir,
                include_debug=include_debug,
                include_google_slides=self.enable_google_slides,
                auto_open_browser=auto_open
            )

            # Use timestamped output directory
            report_output_dir = config.get_timestamped_output_dir()

            print(f"📊 Generating visual report...")
            print(f"   SVG: {svg_file}")
            print(f"   PPTX: {pptx_file}")
            print(f"   Output: {report_output_dir}")

            # Use CLI adapter for enhanced visual comparison
            cli_adapter = CLIVisualComparisonAdapter(
                output_dir=report_output_dir,
                progress_callback=self._create_progress_callback(include_debug)
            )

            # Check dependencies if debug mode enabled
            if include_debug:
                dependencies = cli_adapter.check_dependencies()
                if dependencies['recommendations']:
                    print("⚠️  Dependency recommendations:")
                    for rec in dependencies['recommendations']:
                        print(f"   • {rec}")

            # Generate visual comparison
            report_path = cli_adapter.generate_visual_comparison(
                svg_file=svg_file,
                pptx_file=pptx_file,
                enable_path_testing=include_debug,
                timeout_seconds=120
            )

            if report_path:
                print(f"✅ Visual report generated: {report_path}")

                # Auto-open if requested
                if auto_open:
                    self._open_report_in_browser(report_path)

                # Cleanup temporary files
                cleanup_count = cli_adapter.cleanup_temp_files()
                if cleanup_count > 0:
                    print(f"🧹 Cleaned up {cleanup_count} temporary files")

                return report_path
            else:
                error_msg = cli_adapter.get_last_error() or "Unknown error"
                print(f"❌ Visual report generation failed: {error_msg}")
                return None

        except Exception as e:
            print(f"❌ Error generating visual report: {e}")
            return None

    def generate_visual_report_unified(self, config: VisualReportConfig) -> Optional[Path]:
        """
        Generate comprehensive visual report using unified template.

        Args:
            config: Visual report configuration containing all necessary parameters

        Returns:
            Path to generated HTML report file, or None if generation failed
        """
        try:
            print(f"🎨 Generating visual report for {config.svg_file.name}")

            # Create timestamped output directory for this report
            report_dir = config.get_timestamped_output_dir()
            report_dir.mkdir(parents=True, exist_ok=True)

            # Initialize CLI adapter with progress callback
            verbose = config.include_debug
            progress_callback = self._create_progress_callback(verbose)
            cli_adapter = CLIVisualComparisonAdapter(report_dir, progress_callback)

            # Verify required files exist
            svg_file = config.svg_file
            pptx_file = config.pptx_file

            if not svg_file.exists():
                print(f"❌ SVG file not found: {svg_file}")
                return None

            if not pptx_file.exists():
                print(f"❌ PPTX file not found: {pptx_file}")
                return None

            # Check dependencies if debug mode enabled
            if config.include_debug:
                dependencies = cli_adapter.check_dependencies()
                if dependencies['recommendations']:
                    print("⚠️  Dependency recommendations:")
                    for rec in dependencies['recommendations']:
                        print(f"   • {rec}")

            # Generate visual comparison data
            comparison_data = self._generate_comparison_data(cli_adapter, config)
            if not comparison_data:
                error_msg = cli_adapter.get_last_error() or "Unknown error"
                print(f"❌ Visual comparison generation failed: {error_msg}")
                return None

            # Generate HTML report using unified template
            report_path = self._generate_unified_html_report(comparison_data, report_dir, config)

            if report_path:
                print(f"✅ Visual report generated: {report_path}")

                # Auto-open if requested
                if config.auto_open_browser:
                    self._open_report_in_browser(report_path)

                # Cleanup temporary files
                cleanup_count = cli_adapter.cleanup_temp_files()
                if cleanup_count > 0:
                    print(f"🧹 Cleaned up {cleanup_count} temporary files")

                return report_path
            else:
                print(f"❌ HTML report generation failed")
                return None

        except Exception as e:
            print(f"❌ Error generating visual report: {e}")
            return None

    def _generate_comparison_data(self, cli_adapter: 'CLIVisualComparisonAdapter',
                                config: VisualReportConfig) -> Optional[Dict[str, Any]]:
        """
        Generate visual comparison data without creating HTML report.

        Args:
            cli_adapter: CLI adapter for visual comparison
            config: Visual report configuration

        Returns:
            Dictionary with comparison data, or None if failed
        """
        try:
            # Generate screenshots and conversion data
            svg_file = config.svg_file
            pptx_file = config.pptx_file

            # Initialize visual generator for data collection
            if not cli_adapter.visual_generator:
                print("❌ Visual generator not available")
                return None

            # Reset debug info for new comparison
            cli_adapter.visual_generator.debug_info = []
            cli_adapter.visual_generator.conversion_stats = {}

            # Run path system testing if enabled
            if config.include_debug:
                cli_adapter.progress_callback("Testing path system components...", 30)
                if not cli_adapter.visual_generator.test_path_system_components():
                    print("❌ Path system component testing failed")
                    return None

            # Generate LibreOffice screenshot
            cli_adapter.progress_callback("Capturing PPTX screenshot...", 60)
            screenshot_path = cli_adapter._capture_screenshot_with_timeout(pptx_file, 120)

            if not screenshot_path:
                print("❌ Screenshot generation failed")
                return None

            # Collect comparison data
            comparison_data = {
                'svg_file': svg_file,
                'pptx_file': pptx_file,
                'screenshot_path': screenshot_path,
                'conversion_stats': getattr(cli_adapter.visual_generator, 'conversion_stats', {}),
                'debug_entries': getattr(cli_adapter.visual_generator, 'debug_info', []),
                'timestamp': config.timestamp,
                'report_dir': cli_adapter.output_dir
            }

            cli_adapter.progress_callback("Comparison data collection complete", 80)
            return comparison_data

        except Exception as e:
            print(f"❌ Error generating comparison data: {e}")
            return None

    def _generate_unified_html_report(self, comparison_data: Dict[str, Any],
                                    report_dir: Path, config: VisualReportConfig) -> Optional[Path]:
        """
        Generate HTML report using unified template with enhanced progress tracking.

        Args:
            comparison_data: Data from visual comparison generation
            report_dir: Directory for report output
            config: Visual report configuration

        Returns:
            Path to generated HTML report, or None if failed
        """
        # Create enhanced progress indicator for template rendering
        quiet_mode = not config.include_debug or self._is_automated_environment()
        template_progress = self._create_enhanced_progress_callback(
            "Template Rendering",
            estimated_duration=EnhancedProgressIndicator.estimate_template_duration(2),
            quiet_mode=quiet_mode
        )

        try:
            # Step 1: Load template
            template_progress("Loading HTML template", 10)
            template_path = Path(__file__).parent / 'templates' / 'visual_report.html'
            if not template_path.exists():
                template_progress.indicator.error_with_context(f"Template not found: {template_path}")
                return None

            # Step 2: Initialize renderer
            template_progress("Initializing template renderer", 25)
            renderer = CLITemplateRenderer(template_path)

            # Step 3: Prepare context
            template_progress("Preparing template context", 40)
            context = self._prepare_template_context(comparison_data, config)

            # Step 4: Render HTML (most time-consuming step)
            template_progress("Rendering HTML content", 60)
            html_content = renderer.render(context)

            # Step 5: Write file
            template_progress("Writing report file", 80)
            report_filename = config.get_report_filename()
            report_path = report_dir / report_filename

            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # Step 6: Finalize
            template_progress("HTML report generation complete", 100)
            return report_path

        except KeyboardInterrupt:
            template_progress.indicator.complete_operation(
                success=False,
                final_message="Template rendering cancelled by user"
            )
            return None
        except Exception as e:
            template_progress.indicator.error_with_context(f"Template rendering failed: {e}")
            return None

    def _prepare_template_context(self, comparison_data: Dict[str, Any],
                                config: VisualReportConfig) -> Dict[str, Any]:
        """
        Prepare template context with all necessary data.

        Args:
            comparison_data: Data from visual comparison
            config: Visual report configuration

        Returns:
            Context dictionary for template rendering
        """
        import uuid

        svg_file = comparison_data['svg_file']
        pptx_file = comparison_data['pptx_file']
        screenshot_path = comparison_data['screenshot_path']
        stats = comparison_data.get('conversion_stats', {})
        debug_entries = comparison_data.get('debug_entries', [])

        # Read SVG content for inline embedding
        svg_content = ""
        try:
            with open(svg_file, 'r', encoding='utf-8') as f:
                svg_content = f.read()
        except Exception:
            svg_content = ""

        # Prepare statistics for display
        stat_items = []
        if stats:
            if 'path_elements' in stats:
                stat_items.append({'value': stats['path_elements'], 'label': 'Path Elements'})
            if 'processing_time' in stats:
                stat_items.append({'value': f"{stats['processing_time']:.3f}s", 'label': 'Processing Time'})
            if 'output_size' in stats:
                stat_items.append({'value': f"{stats['output_size']}B", 'label': 'Output Size'})
            if 'text_elements' in stats:
                stat_items.append({'value': stats['text_elements'], 'label': 'Text Elements'})

        # Format debug entries
        formatted_debug = []
        for entry in debug_entries:
            formatted_debug.append({
                'timestamp': entry.get('timestamp', ''),
                'level': entry.get('level', 'info').lower(),
                'message': entry.get('message', '')
            })

        # Prepare context
        context = {
            'title': f"SVG2PPTX Visual Report - {svg_file.stem}",
            'report_title': f"SVG2PPTX Visual Report",
            'subtitle': f"Conversion Analysis for {svg_file.name}",
            'timestamp': config.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'cli_command': f"svg2pptx {svg_file.name} --visual-report",
            'processing_time': stats.get('processing_time', 'N/A'),
            'status': 'Success',
            'status_class': 'status-completed',

            # File paths and content
            'svg_file_path': str(svg_file),
            'pptx_file_path': str(pptx_file),
            'svg_embedded': bool(svg_content),
            'svg_content': svg_content,
            'pptx_screenshot_path': str(screenshot_path),
            'screenshot_method': 'LibreOffice Headless',

            # Statistics
            'stats': stat_items,

            # Debug information
            'include_debug': config.include_debug,
            'debug_entries': formatted_debug,

            # Visual diff generation
            **self._generate_visual_diff_data(svg_file, screenshot_path, config),

            # Progress (placeholder)
            'show_progress': False,
            'progress_items': [],

            # Google Slides integration
            'google_slides_url': self.create_google_slides_link(pptx_file) if config.include_google_slides else None,

            # Metadata
            'output_dir': str(config.output_dir),
            'report_id': str(uuid.uuid4()),
            **self._get_version_metadata()
        }

        return context

    def _create_progress_callback(self, verbose: bool = True) -> Callable[[str, float], None]:
        """
        Create enhanced progress callback for visual comparison operations.

        Args:
            verbose: Whether to show detailed progress information

        Returns:
            Progress callback function with cancellation support
        """
        # Determine if we should use quiet mode
        quiet_mode = not verbose or self._is_automated_environment()

        # Create enhanced progress indicator
        progress_indicator = EnhancedProgressIndicator(
            quiet_mode=quiet_mode,
            enable_cancellation=True
        )

        def progress_callback(message: str, percentage: float, operation_name: str = "Visual Report Generation"):
            # Start operation tracking on first call
            if not hasattr(progress_callback, '_started'):
                progress_indicator.start_operation(operation_name)
                progress_callback._started = True

            # Update progress and check for cancellation
            if not progress_indicator.update_progress(percentage, message):
                # Operation was cancelled
                raise KeyboardInterrupt("Operation cancelled by user")

            # Complete operation when done
            if percentage >= 100:
                progress_indicator.complete_operation(success=True)

        # Store reference to progress indicator for external access
        progress_callback.indicator = progress_indicator
        return progress_callback

    def _create_enhanced_progress_callback(self, operation_name: str,
                                         estimated_duration: Optional[float] = None,
                                         quiet_mode: Optional[bool] = None) -> Callable[[str, float], None]:
        """
        Create enhanced progress callback with operation-specific settings.

        Args:
            operation_name: Name of the operation being tracked
            estimated_duration: Estimated duration in seconds
            quiet_mode: Override quiet mode detection

        Returns:
            Enhanced progress callback function
        """
        if quiet_mode is None:
            quiet_mode = not True or self._is_automated_environment()  # Default to verbose unless automated

        progress_indicator = EnhancedProgressIndicator(
            quiet_mode=quiet_mode,
            enable_cancellation=True
        )

        # Start the operation immediately
        progress_indicator.start_operation(operation_name, estimated_duration)

        def enhanced_progress_callback(message: str, percentage: float):
            try:
                # Update progress and check for cancellation
                if not progress_indicator.update_progress(percentage, message):
                    # Operation was cancelled
                    progress_indicator.complete_operation(success=False, final_message="Operation cancelled")
                    raise KeyboardInterrupt("Operation cancelled by user")

                # Complete operation when done
                if percentage >= 100:
                    progress_indicator.complete_operation(success=True)

            except Exception as e:
                if "cancelled" not in str(e).lower():
                    progress_indicator.error_with_context(str(e))
                raise

        # Store reference to progress indicator for external access
        enhanced_progress_callback.indicator = progress_indicator
        return enhanced_progress_callback

    def create_google_slides_link(self, pptx_file: Path) -> Optional[str]:
        """
        Generate Google Slides link for PPTX file using existing API infrastructure.

        Args:
            pptx_file: PPTX file to upload and link

        Returns:
            Google Slides URL or None if upload fails
        """
        # TODO: Implement Google Slides integration in next task
        # This is a stub for now - will be implemented in Task 3.1
        if not self.enable_google_slides:
            return None

        print("🔗 Google Slides integration not yet implemented")
        return None

    def _open_report_in_browser(self, report_path: Path) -> bool:
        """
        Open generated report in default browser with enhanced cross-platform support.

        This method provides comprehensive browser launching with:
        - Cross-platform compatibility (Windows, macOS, Linux)
        - CI/automated environment detection
        - Security considerations and user preferences
        - Graceful fallback and error handling
        - Clear success/failure messaging

        Args:
            report_path: Path to HTML report file

        Returns:
            True if browser launch succeeded, False otherwise
        """
        try:
            import webbrowser
            import os
            import subprocess
            import sys

            # Validate report file exists
            if not report_path.exists():
                print(f"❌ Report file not found: {report_path}")
                return False

            # Create absolute file URL
            file_url = f"file://{report_path.absolute()}"

            # Check if we're in an automated environment
            if self._is_automated_environment():
                print(f"🤖 Automated environment detected - not opening browser")
                print(f"🌐 Report available at: {file_url}")
                return False

            # Check user preferences for browser launching
            if not self._should_launch_browser():
                print(f"🌐 Report available at: {file_url}")
                return False

            # Try platform-specific browser launching with fallbacks
            print(f"🚀 Opening report in browser...")

            browser_launched = False
            launch_method = "unknown"

            try:
                # Method 1: Use webbrowser module (cross-platform)
                browser_launched = webbrowser.open(file_url)
                launch_method = "webbrowser"

                if browser_launched:
                    print(f"✅ Browser opened successfully using {launch_method}")
                    print(f"📄 Report: {report_path.name}")
                    return True

            except Exception as e:
                print(f"⚠️  webbrowser method failed: {e}")

            # Method 2: Platform-specific fallbacks
            if not browser_launched:
                browser_launched, launch_method = self._platform_specific_browser_launch(file_url)

                if browser_launched:
                    print(f"✅ Browser opened successfully using {launch_method}")
                    print(f"📄 Report: {report_path.name}")
                    return True

            # All methods failed - provide helpful fallback
            print(f"⚠️  Unable to automatically open browser")
            print(f"🌐 Please manually open: {file_url}")
            print(f"📁 Or navigate to: {report_path}")

            return False

        except Exception as e:
            print(f"❌ Browser launch failed: {e}")
            print(f"🌐 Report available at: file://{report_path.absolute()}")
            return False

    def _is_automated_environment(self) -> bool:
        """
        Detect if running in an automated/CI environment.

        Returns:
            True if in automated environment, False otherwise
        """
        # Check common CI environment variables
        ci_indicators = [
            'CI', 'CONTINUOUS_INTEGRATION', 'AUTOMATED',
            'JENKINS_URL', 'GITHUB_ACTIONS', 'GITLAB_CI',
            'TRAVIS', 'CIRCLECI', 'APPVEYOR', 'BUILDKITE',
            'TEAMCITY_VERSION', 'AZURE_PIPELINES'
        ]

        for indicator in ci_indicators:
            if os.environ.get(indicator):
                return True

        # Check if running in headless environment
        if os.environ.get('DISPLAY') == '' or not os.environ.get('DISPLAY'):
            # On Linux, no DISPLAY usually means headless
            if platform.system() == 'Linux':
                return True

        # Check if stdout is not a tty (piped/redirected)
        if not sys.stdout.isatty():
            return True

        return False

    def _should_launch_browser(self) -> bool:
        """
        Check user preferences and safety considerations for browser launching.

        Returns:
            True if browser should be launched, False otherwise
        """
        # Check for explicit user preference environment variable
        user_pref = os.environ.get('SVG2PPTX_AUTO_OPEN_BROWSER')
        if user_pref is not None:
            return user_pref.lower() in ('1', 'true', 'yes', 'on')

        # For now, default to True for interactive sessions
        # In future versions, could check user config file
        return True

    def _platform_specific_browser_launch(self, file_url: str) -> Tuple[bool, str]:
        """
        Attempt platform-specific browser launching methods.

        Args:
            file_url: File URL to open

        Returns:
            Tuple of (success: bool, method_used: str)
        """
        try:
            system = platform.system()

            if system == 'Darwin':  # macOS
                return self._launch_browser_macos(file_url)
            elif system == 'Windows':
                return self._launch_browser_windows(file_url)
            elif system == 'Linux':
                return self._launch_browser_linux(file_url)
            else:
                return False, f"unsupported_platform_{system}"

        except Exception as e:
            return False, f"platform_specific_error_{e}"

    def _launch_browser_macos(self, file_url: str) -> Tuple[bool, str]:
        """Launch browser on macOS using system open command."""
        try:
            subprocess.run(['open', file_url], check=True, capture_output=True)
            return True, "macos_open"
        except subprocess.CalledProcessError as e:
            # Try with specific browser
            try:
                subprocess.run(['open', '-a', 'Safari', file_url], check=True, capture_output=True)
                return True, "macos_safari"
            except subprocess.CalledProcessError:
                return False, "macos_failed"
        except FileNotFoundError:
            return False, "macos_no_open_command"

    def _launch_browser_windows(self, file_url: str) -> Tuple[bool, str]:
        """Launch browser on Windows using system start command."""
        try:
            subprocess.run(['cmd', '/c', 'start', file_url], check=True, capture_output=True)
            return True, "windows_start"
        except subprocess.CalledProcessError:
            # Try with powershell
            try:
                subprocess.run(['powershell', '-Command', f'Start-Process "{file_url}"'],
                             check=True, capture_output=True)
                return True, "windows_powershell"
            except subprocess.CalledProcessError:
                return False, "windows_failed"
        except FileNotFoundError:
            return False, "windows_no_start_command"

    def _launch_browser_linux(self, file_url: str) -> Tuple[bool, str]:
        """Launch browser on Linux using xdg-open or alternatives."""
        linux_commands = [
            (['xdg-open', file_url], "linux_xdg_open"),
            (['gnome-open', file_url], "linux_gnome_open"),
            (['kde-open', file_url], "linux_kde_open"),
            (['firefox', file_url], "linux_firefox"),
            (['chromium-browser', file_url], "linux_chromium"),
            (['google-chrome', file_url], "linux_chrome")
        ]

        for command, method_name in linux_commands:
            try:
                subprocess.run(command, check=True, capture_output=True)
                return True, method_name
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        return False, "linux_all_failed"

    def cleanup_old_reports(self, days_to_keep: int = 7) -> int:
        """
        Clean up old visual reports based on age.

        Args:
            days_to_keep: Number of days of reports to retain

        Returns:
            Number of directories cleaned up
        """
        try:
            from datetime import timedelta

            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            cleaned_count = 0

            # Look for date-based directories (YYYY-MM-DD format)
            for date_dir in self.output_dir.glob("????-??-??"):
                try:
                    dir_date = datetime.strptime(date_dir.name, '%Y-%m-%d')
                    if dir_date < cutoff_date:
                        import shutil
                        shutil.rmtree(date_dir)
                        cleaned_count += 1
                        print(f"🗑️  Cleaned up old reports: {date_dir}")
                except (ValueError, OSError) as e:
                    print(f"⚠️  Could not clean up {date_dir}: {e}")

            if cleaned_count > 0:
                print(f"✅ Cleaned up {cleaned_count} old report directories")

            return cleaned_count

        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            return 0

    def get_report_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about generated reports.

        Returns:
            Dictionary with report statistics
        """
        try:
            stats = {
                'total_reports': 0,
                'total_size_mb': 0.0,
                'oldest_report': None,
                'newest_report': None,
                'report_directories': []
            }

            # Scan for report directories
            for date_dir in self.output_dir.glob("????-??-??"):
                if date_dir.is_dir():
                    stats['report_directories'].append(str(date_dir))

                    # Count reports in this directory
                    for time_dir in date_dir.glob("??????"):
                        if time_dir.is_dir():
                            stats['total_reports'] += 1

                            # Calculate size
                            for file_path in time_dir.rglob('*'):
                                if file_path.is_file():
                                    stats['total_size_mb'] += file_path.stat().st_size / (1024 * 1024)

            return stats

        except Exception as e:
            print(f"❌ Error getting report statistics: {e}")
            return {'error': str(e)}

    def create_google_slides_link(self, pptx_file: Path) -> Optional[str]:
        """
        Create Google Slides link by uploading PPTX file.

        Args:
            pptx_file: Path to PPTX file to upload

        Returns:
            Google Slides present URL if successful, None otherwise
        """
        if not GOOGLE_API_AVAILABLE:
            return None

        if not self.enable_google_slides:
            return None

        try:
            print("🔄 Uploading PPTX to Google Slides...")

            # Use drop-in Google Slides integration
            urls = integrate_google_slides(
                pptx_path=str(pptx_file),
                make_public=True,
                custom_name=f"SVG2PPTX Report - {pptx_file.stem}"
            )

            # Return the present URL for best "published" experience
            slides_url = urls["present"]
            print(f"✅ Google Slides created: {slides_url}")

            return slides_url

        except FileNotFoundError as e:
            print(f"⚠️  Google OAuth setup required: {str(e)}")
            print("   Download client secret from Google Cloud Console and save as credentials/google_client_secret.json")
            return None

        except ImportError as e:
            print(f"⚠️  Google APIs not available: {str(e)}")
            return None

        except Exception as e:
            print(f"❌ Google Slides integration failed: {str(e)}")
            return None

    def get_google_authentication_status(self) -> Tuple[bool, str]:
        """
        Check Google API authentication status.

        Returns:
            Tuple of (is_authenticated, status_message)
        """
        if not GOOGLE_API_AVAILABLE:
            return False, "Google APIs not installed"

        try:
            return check_google_auth_status()
        except Exception as e:
            return False, f"Authentication check failed: {str(e)}"

    def _generate_visual_diff_data(self, svg_file: Path, pptx_screenshot_path: Optional[Path],
                                  config: VisualReportConfig) -> Dict[str, Any]:
        """
        Generate visual diff data for template context.

        Args:
            svg_file: Path to SVG file
            pptx_screenshot_path: Path to PPTX screenshot (if available)
            config: Visual report configuration

        Returns:
            Dictionary with visual diff data for template
        """
        # Default values when visual diff is not available
        default_diff_data = {
            'show_visual_diff': False,
            'similarity_score': 'N/A',
            'similarity_percentage': 'N/A',
            'different_pixels': 'N/A',
            'different_pixels_percentage': 'N/A',
            'max_difference': 'N/A',
            'rms_error': 'N/A',
            'diff_image_path': None,
            'visual_diff_available': False,
            'quality_assessment': 'Not available',
            'recommendation': 'Visual diff not generated'
        }

        # Check if we should generate visual diff
        if not config.include_debug or not pptx_screenshot_path:
            return default_diff_data

        # Check if visual diff is available
        if not VISUAL_DIFF_AVAILABLE:
            print("⚠️  Visual diff not available (install Pillow: pip install Pillow)")
            return default_diff_data

        try:
            print("🔍 Generating visual diff analysis...")

            # Initialize visual diff generator
            diff_generator = CLIVisualDiffGenerator(config.output_dir)

            if not diff_generator.is_available():
                return default_diff_data

            # We need an SVG screenshot for comparison
            # For now, assume PPTX screenshot is the only one we have
            # In a full implementation, we'd generate an SVG screenshot too
            # Let's check if there's an SVG screenshot in the same directory
            svg_screenshot_path = pptx_screenshot_path.parent / f"{svg_file.stem}_svg.png"

            if not svg_screenshot_path.exists():
                # Try to find any SVG screenshot
                svg_screenshots = list(pptx_screenshot_path.parent.glob("*svg*.png"))
                if svg_screenshots:
                    svg_screenshot_path = svg_screenshots[0]
                else:
                    print("⚠️  No SVG screenshot found for visual diff")
                    return default_diff_data

            # Generate visual diff
            diff_result = diff_generator.generate_visual_diff(
                svg_screenshot=svg_screenshot_path,
                pptx_screenshot=pptx_screenshot_path,
                method="structural_similarity"
            )

            if diff_result.get("available"):
                print(f"✅ Visual diff generated: {diff_result['similarity_percentage']} similar")

                # Build template data
                return {
                    'show_visual_diff': True,
                    'similarity_score': diff_result['similarity_score'],
                    'similarity_percentage': diff_result['similarity_percentage'],
                    'different_pixels': diff_result['pixel_difference_count'],
                    'different_pixels_percentage': diff_result['different_pixels_percentage'],
                    'max_difference': 'N/A',  # Would need additional calculation
                    'rms_error': 'N/A',  # Would need additional calculation
                    'diff_image_path': diff_result.get('diff_image_path'),
                    'visual_diff_available': True,
                    'quality_assessment': diff_result['metrics']['quality_assessment'],
                    'recommendation': diff_result['metrics']['recommendation'],
                    'areas_of_concern': diff_result['metrics'].get('areas_of_concern', []),
                    'diff_passed': diff_result['passed']
                }
            else:
                print(f"⚠️  Visual diff failed: {diff_result.get('error', 'Unknown error')}")
                return default_diff_data

        except Exception as e:
            print(f"⚠️  Visual diff error: {e}")
            return default_diff_data

    def _get_version_metadata(self) -> Dict[str, Any]:
        """
        Get version metadata for template context.

        Returns:
            Dictionary with version information
        """
        if VERSION_INFO_AVAILABLE:
            try:
                version_info = VersionInfo.gather()
                return version_info.to_dict()
            except Exception as e:
                print(f"⚠️  Version detection error: {e}")

        # Fallback version information
        return {
            'version': '2.0.0-dev',
            'cli_version': '2.0.0-dev',
            'python_version': platform.python_version(),
            'libreoffice_version': 'Not detected',
            'platform': platform.platform(),
            'working_directory': str(Path.cwd())
        }


class CLIVisualComparisonAdapter:
    """
    CLI-friendly adapter for VisualComparisonGenerator.

    Provides simplified interface with progress callbacks, enhanced error handling,
    and CLI-specific features while maintaining compatibility with existing
    visual comparison infrastructure.
    """

    def __init__(self, output_dir: Path, progress_callback: Optional[Callable[[str, float], None]] = None):
        """
        Initialize CLI adapter for visual comparison.

        Args:
            output_dir: Directory for visual comparison outputs
            progress_callback: Optional callback for progress updates (message, percentage)
        """
        self.output_dir = Path(output_dir)
        self.progress_callback = progress_callback or self._default_progress_callback
        self.visual_generator: Optional[VisualComparisonGenerator] = None
        self.last_error: Optional[str] = None

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize visual generator
        self._initialize_generator()

    def _default_progress_callback(self, message: str, percentage: float):
        """Default progress callback that prints to console."""
        progress_bar = "█" * int(percentage / 5) + "░" * (20 - int(percentage / 5))
        print(f"\r📊 [{progress_bar}] {percentage:3.0f}% {message}", end="", flush=True)
        if percentage >= 100:
            print()  # New line when complete

    def _initialize_generator(self) -> bool:
        """
        Initialize the visual comparison generator.

        Returns:
            True if initialization succeeded, False otherwise
        """
        try:
            self.progress_callback("Initializing visual comparison generator...", 10)
            self.visual_generator = VisualComparisonGenerator(output_dir=self.output_dir)
            self.progress_callback("Visual comparison generator ready", 20)
            return True
        except Exception as e:
            self.last_error = f"Failed to initialize visual generator: {e}"
            self.progress_callback(f"Initialization failed: {e}", 0)
            return False

    def check_dependencies(self) -> Dict[str, Any]:
        """
        Check availability of required dependencies for visual comparison.

        Returns:
            Dictionary with dependency status and recommendations
        """
        self.progress_callback("Checking dependencies...", 5)

        dependencies = {
            'libreoffice': {'available': False, 'path': None, 'version': None},
            'visual_generator': {'available': self.visual_generator is not None},
            'output_directory': {'writable': False, 'path': str(self.output_dir)},
            'recommendations': []
        }

        # Check LibreOffice availability
        libreoffice_paths = [
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            "/usr/bin/libreoffice",
            "/opt/libreoffice/bin/soffice",
            "soffice"
        ]

        for path in libreoffice_paths:
            if Path(path).exists() or shutil.which(path if not path.startswith('/') else None):
                dependencies['libreoffice']['available'] = True
                dependencies['libreoffice']['path'] = path
                break

        # Check output directory writability
        try:
            test_file = self.output_dir / ".dependency_test"
            test_file.touch()
            test_file.unlink()
            dependencies['output_directory']['writable'] = True
        except (PermissionError, OSError):
            dependencies['output_directory']['writable'] = False

        # Generate recommendations
        if not dependencies['libreoffice']['available']:
            dependencies['recommendations'].append(
                "Install LibreOffice for PPTX screenshot generation: https://www.libreoffice.org/download/"
            )

        if not dependencies['output_directory']['writable']:
            dependencies['recommendations'].append(
                f"Ensure write permissions for output directory: {self.output_dir}"
            )

        if not dependencies['visual_generator']['available']:
            dependencies['recommendations'].append(
                "Visual generator initialization failed - check system dependencies"
            )

        self.progress_callback("Dependency check complete", 15)
        return dependencies

    def generate_visual_comparison(self, svg_file: Path, pptx_file: Optional[Path] = None,
                                 enable_path_testing: bool = True,
                                 timeout_seconds: int = 120) -> Optional[Path]:
        """
        Generate comprehensive visual comparison with CLI-friendly progress tracking.

        Args:
            svg_file: Path to source SVG file
            pptx_file: Optional existing PPTX file (if None, will be generated)
            enable_path_testing: Whether to run path system component testing
            timeout_seconds: Maximum time to wait for operations

        Returns:
            Path to generated HTML report, or None if generation failed
        """
        if not self.visual_generator:
            self.last_error = "Visual generator not available"
            return None

        try:
            self.progress_callback("Starting visual comparison generation...", 25)

            # Reset debug info for new comparison
            self.visual_generator.debug_info = []
            self.visual_generator.conversion_stats = {}

            # Run path system testing if enabled
            if enable_path_testing:
                self.progress_callback("Testing path system components...", 30)
                if not self.visual_generator.test_path_system_components():
                    self.last_error = "Path system component testing failed"
                    return None

            # Handle PPTX generation if needed
            if pptx_file is None:
                self.progress_callback("Converting SVG to PPTX...", 40)
                pptx_file = self.output_dir / f"{svg_file.stem}_output.pptx"

                if not self.visual_generator.convert_svg_with_debugging(svg_file, pptx_file):
                    self.last_error = "SVG to PPTX conversion failed"
                    return None
            else:
                self.progress_callback("Using existing PPTX file...", 50)

            # Generate LibreOffice screenshot
            self.progress_callback("Capturing PPTX screenshot...", 60)
            screenshot_path = self._capture_screenshot_with_timeout(pptx_file, timeout_seconds)

            # Generate HTML report
            self.progress_callback("Generating HTML report...", 80)
            html_report = self._generate_html_report_cli(svg_file, screenshot_path)

            if html_report:
                self.progress_callback("Visual comparison complete!", 100)
                return html_report
            else:
                self.last_error = "HTML report generation failed"
                return None

        except Exception as e:
            self.last_error = f"Visual comparison generation failed: {e}"
            self.progress_callback(f"Error: {e}", 0)
            return None

    def _capture_screenshot_with_timeout(self, pptx_file: Path, timeout_seconds: int) -> Optional[Path]:
        """
        Capture LibreOffice screenshot with enhanced progress tracking and timeout handling.

        Args:
            pptx_file: Path to PPTX file
            timeout_seconds: Maximum time to wait

        Returns:
            Path to screenshot file, or None if failed
        """
        try:
            import threading
            import queue

            # Estimate duration based on file size
            file_size = pptx_file.stat().st_size if pptx_file.exists() else 1024
            estimated_duration = EnhancedProgressIndicator.estimate_screenshot_duration(file_size)

            # Create enhanced progress callback for this operation
            quiet_mode = False  # CLIVisualComparisonAdapter doesn't have _is_automated_environment method
            screenshot_progress = EnhancedProgressIndicator(
                quiet_mode=quiet_mode,
                enable_cancellation=True
            )

            screenshot_progress.start_operation(
                "LibreOffice Screenshot Capture",
                min(estimated_duration, timeout_seconds)
            )

            result_queue = queue.Queue()
            capture_cancelled = threading.Event()

            def capture_worker():
                try:
                    # Check for cancellation before starting
                    if capture_cancelled.is_set() or screenshot_progress.is_cancelled():
                        result_queue.put(('cancelled', 'Operation cancelled'))
                        return

                    screenshot_path = self.visual_generator.capture_libreoffice_screenshot(pptx_file)
                    result_queue.put(('success', screenshot_path))
                except Exception as e:
                    result_queue.put(('error', str(e)))

            # Start screenshot capture in separate thread
            thread = threading.Thread(target=capture_worker)
            thread.daemon = True
            thread.start()

            # Enhanced progress tracking with cancellation support
            start_time = time.time()
            last_progress_update = 0

            while thread.is_alive() and (time.time() - start_time) < timeout_seconds:
                try:
                    time.sleep(0.2)  # More frequent updates for better UX
                    elapsed = time.time() - start_time

                    # Calculate progress based on estimated duration or timeout
                    if estimated_duration > 0:
                        progress = min(95, (elapsed / estimated_duration) * 100)
                    else:
                        progress = min(95, (elapsed / timeout_seconds) * 100)

                    # Update progress with better messaging
                    if elapsed < 2:
                        message = "Initializing LibreOffice"
                    elif elapsed < 5:
                        message = "Loading PPTX file"
                    else:
                        message = "Generating screenshot"

                    # Check for cancellation
                    if not screenshot_progress.update_progress(progress, message):
                        # User cancelled - signal worker thread and break
                        capture_cancelled.set()
                        screenshot_progress.complete_operation(
                            success=False,
                            final_message="Screenshot capture cancelled"
                        )
                        return None

                except KeyboardInterrupt:
                    # Handle Ctrl+C gracefully
                    capture_cancelled.set()
                    screenshot_progress.complete_operation(
                        success=False,
                        final_message="Screenshot capture cancelled by user"
                    )
                    return None

            # Check if thread completed
            if thread.is_alive():
                capture_cancelled.set()
                screenshot_progress.error_with_context(
                    f"Screenshot capture timed out after {timeout_seconds}s"
                )
                self.last_error = f"Screenshot capture timed out after {timeout_seconds}s"
                return None

            # Get result
            try:
                result_type, result_value = result_queue.get_nowait()

                if result_type == 'success':
                    screenshot_progress.complete_operation(
                        success=True,
                        final_message="Screenshot captured successfully"
                    )
                    return result_value
                elif result_type == 'cancelled':
                    screenshot_progress.complete_operation(
                        success=False,
                        final_message="Screenshot capture cancelled"
                    )
                    self.last_error = "Screenshot capture was cancelled"
                    return None
                else:
                    screenshot_progress.error_with_context(f"LibreOffice error: {result_value}")
                    self.last_error = f"Screenshot capture failed: {result_value}"
                    return None

            except queue.Empty:
                screenshot_progress.error_with_context(
                    "Screenshot thread completed but no result available"
                )
                self.last_error = "Screenshot capture thread completed but no result available"
                return None

        except Exception as e:
            if hasattr(locals(), 'screenshot_progress'):
                screenshot_progress.error_with_context(f"Unexpected error: {e}")
            self.last_error = f"Screenshot capture error: {e}"
            return None

    def _generate_html_report_cli(self, svg_file: Path, screenshot_path: Optional[Path]) -> Optional[Path]:
        """
        Generate HTML report using existing infrastructure with CLI enhancements.

        Args:
            svg_file: Path to source SVG file
            screenshot_path: Path to PPTX screenshot (optional)

        Returns:
            Path to generated HTML report, or None if failed
        """
        try:
            # Create debug JSON file
            debug_file = self.output_dir / "debug_report.json"
            debug_data = {
                "timestamp": datetime.now().isoformat(),
                "svg_file": str(svg_file),
                "screenshot_file": str(screenshot_path) if screenshot_path else None,
                "conversion_stats": getattr(self.visual_generator, 'conversion_stats', {}),
                "debug_log": getattr(self.visual_generator, 'debug_info', [])
            }

            with open(debug_file, 'w') as f:
                import json
                json.dump(debug_data, f, indent=2)

            # Generate HTML report using existing infrastructure
            html_report = self.visual_generator.generate_visual_comparison_html(
                svg_file, screenshot_path, debug_file
            )

            return html_report

        except Exception as e:
            self.last_error = f"HTML report generation error: {e}"
            return None

    def get_last_error(self) -> Optional[str]:
        """Get the last error message, if any."""
        return self.last_error

    def cleanup_temp_files(self) -> int:
        """
        Clean up temporary files generated during comparison.

        Returns:
            Number of files cleaned up
        """
        try:
            cleanup_count = 0
            temp_patterns = ['.write_test', '.dependency_test', '.permission_test']

            for pattern in temp_patterns:
                for temp_file in self.output_dir.glob(f"**/{pattern}"):
                    try:
                        temp_file.unlink()
                        cleanup_count += 1
                    except OSError:
                        pass

            return cleanup_count

        except Exception as e:
            print(f"Warning: Cleanup failed: {e}")
            return 0