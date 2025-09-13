"""
Common test fixtures used across multiple test modules.
"""
import os
import tempfile
import shutil
from pathlib import Path
from typing import Generator, Dict

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files.
    
    Yields:
        Path: Path to temporary directory that is cleaned up after test.
    """
    temp_path = Path(tempfile.mkdtemp())
    try:
        yield temp_path
    finally:
        shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def benchmark_data_dir(temp_dir: Path) -> Path:
    """Create directory for benchmark test data.
    
    Args:
        temp_dir: Temporary directory fixture
        
    Returns:
        Path: Path to benchmark data directory
    """
    bench_dir = temp_dir / "benchmarks"
    bench_dir.mkdir()
    return bench_dir


@pytest.fixture
def performance_config() -> Dict[str, any]:
    """Configuration for performance testing.
    
    Returns:
        Dict containing performance test configuration parameters.
    """
    return {
        "timeout": 30.0,
        "max_memory_mb": 500,
        "benchmark_rounds": 5,
        "warmup_rounds": 2
    }


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables and configuration.
    
    This fixture runs once per test session and sets up necessary
    environment variables and test data directories.
    """
    # Set test environment variables
    os.environ["TESTING"] = "1"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    # Create test data directories
    test_root = Path(__file__).parent.parent
    test_data_dir = test_root / "data"
    test_data_dir.mkdir(exist_ok=True)
    
    # Create subdirectories for test assets
    (test_data_dir / "svg").mkdir(exist_ok=True)
    (test_data_dir / "expected").mkdir(exist_ok=True)
    (test_data_dir / "baselines").mkdir(exist_ok=True)
    
    yield
    
    # Cleanup after all tests
    if "TESTING" in os.environ:
        del os.environ["TESTING"]


@pytest.fixture(autouse=True)
def cleanup_globals():
    """Clean up global state after each test.
    
    This fixture automatically runs after each test to reset
    any global caches or singletons.
    """
    yield
    
    # Reset any global caches or singletons
    try:
        from src.performance.cache import _global_cache
        if _global_cache:
            _global_cache.clear_all()
    except ImportError:
        pass