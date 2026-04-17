"""
Pytest configuration for Day-1 Test Framework

Provides fixtures and hooks for test execution.
"""

import shutil
from pathlib import Path

import pytest


@pytest.fixture(scope="session", autouse=True)
def clean_reports_dir():
    """Clean reports directory before test session."""
    reports_dir = Path("reports")

    # Clean old reports (except .gitkeep if exists)
    if reports_dir.exists():
        for item in reports_dir.iterdir():
            if item.name.startswith("."):
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

    # Create fresh directories
    reports_dir.mkdir(exist_ok=True)

    yield

    # No cleanup after - keep reports for inspection


@pytest.fixture(scope="function")
def test_data():
    """Provide test data fixtures."""
    return {
        "user": "test_user",
        "email": "test@example.com",
        "timestamp": "2024-01-01T00:00:00Z",
    }
