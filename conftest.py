"""
Pytest configuration file for Netskope SDET Framework

This file configures the Python path and test environment for all tests.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Add tests directory to Python path
tests_dir = project_root / "tests"
sys.path.insert(0, str(tests_dir))

# Import test result logger hooks
from src.test_result_logger import (
    pytest_runtest_setup,
    pytest_runtest_logreport, 
    pytest_sessionfinish,
    pytest_sessionstart
)

# Configure pytest
def pytest_configure(config):
    """Configure pytest with custom settings"""
    # Add custom markers
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "mock: marks tests that use mock mode"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Mark performance tests as slow
        if "performance" in str(item.fspath):
            item.add_marker("slow")
        
        # Mark all tests as mock by default (since we're using mock mode)
        item.add_marker("mock")