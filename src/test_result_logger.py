#!/usr/bin/env python3
"""
Test Result Logger for MongoDB Integration

Automatically stores test results, metrics, and execution data in MongoDB
for monitoring, analysis, and reporting.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pytest
import os
import traceback

from src.service_manager import get_database_client
from src.environment_manager import get_current_environment

class ResultLogger:
    """Logs test results to MongoDB for monitoring and analysis"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_client = None
        self.collection_name = "test_results"
        self.session_id = None
        self.environment = None
        
    def initialize(self):
        """Initialize database connection and session"""
        try:
            self.db_client = get_database_client()
            self.environment = get_current_environment().value
            self.session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.logger.info(f"Test result logger initialized for environment: {self.environment}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize test result logger: {e}")
            return False
    
    def log_test_start(self, test_name: str, test_file: str, test_class: str = None):
        """Log test start event"""
        if not self.db_client:
            return
            
        try:
            test_doc = {
                "session_id": self.session_id,
                "test_name": test_name,
                "test_file": test_file,
                "test_class": test_class,
                "environment": self.environment,
                "status": "running",
                "start_time": datetime.now(),
                "end_time": None,
                "duration": None,
                "error_message": None,
                "error_type": None,
                "traceback": None,
                "metadata": {
                    "python_version": os.sys.version,
                    "environment_vars": {
                        "TESTING_MODE": os.getenv("TESTING_MODE"),
                        "CI": os.getenv("CI", "false")
                    }
                }
            }
            
            doc_id = self.db_client.insert_one(self.collection_name, test_doc)
            self.logger.debug(f"Logged test start: {test_name} -> {doc_id}")
            return doc_id
            
        except Exception as e:
            self.logger.error(f"Failed to log test start: {e}")
            return None
    
    def log_test_result(self, test_name: str, status: str, duration: float, 
                       error_message: str = None, error_type: str = None, 
                       test_output: str = None, **kwargs):
        """Log test completion with results"""
        if not self.db_client:
            return
            
        try:
            # Find the test document
            test_filter = {
                "session_id": self.session_id,
                "test_name": test_name,
                "status": "running"
            }
            
            update_data = {
                "status": status,
                "end_time": datetime.now(),
                "duration": duration,
                "error_message": error_message,
                "error_type": error_type,
                "test_output": test_output,
                "additional_data": kwargs
            }
            
            # Update existing document or create new one
            success = self.db_client.update_one(self.collection_name, test_filter, update_data)
            
            if not success:
                # Create new document if update failed
                test_doc = {
                    "session_id": self.session_id,
                    "test_name": test_name,
                    "environment": self.environment,
                    "start_time": datetime.now() - timedelta(seconds=duration),
                    **update_data
                }
                doc_id = self.db_client.insert_one(self.collection_name, test_doc)
                self.logger.debug(f"Created new test result: {test_name} -> {doc_id}")
            else:
                self.logger.debug(f"Updated test result: {test_name} -> {status}")
                
        except Exception as e:
            self.logger.error(f"Failed to log test result: {e}")
    
    def log_session_summary(self, total_tests: int, passed: int, failed: int, 
                           skipped: int, total_duration: float):
        """Log test session summary"""
        if not self.db_client:
            return
            
        try:
            summary_doc = {
                "session_id": self.session_id,
                "document_type": "session_summary",
                "environment": self.environment,
                "timestamp": datetime.now(),
                "total_tests": total_tests,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "success_rate": (passed / total_tests * 100) if total_tests > 0 else 0,
                "total_duration": total_duration,
                "avg_test_duration": (total_duration / total_tests) if total_tests > 0 else 0
            }
            
            doc_id = self.db_client.insert_one("test_sessions", summary_doc)
            self.logger.info(f"Logged session summary: {self.session_id} -> {doc_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to log session summary: {e}")

# Global logger instance
_test_logger = None

def get_test_logger() -> ResultLogger:
    """Get global test result logger instance"""
    global _test_logger
    if _test_logger is None:
        _test_logger = ResultLogger()
        _test_logger.initialize()
    return _test_logger

# Pytest hooks for automatic test logging
def pytest_runtest_setup(item):
    """Called before each test runs"""
    logger = get_test_logger()
    test_name = item.name
    test_file = str(item.fspath)  # Convert to string directly
    test_class = item.cls.__name__ if item.cls else None
    
    logger.log_test_start(test_name, test_file, test_class)

def pytest_runtest_logreport(report):
    """Called after each test phase (setup, call, teardown)"""
    if report.when == "call":  # Only log the main test execution
        logger = get_test_logger()
        
        status = "passed" if report.passed else "failed" if report.failed else "skipped"
        duration = report.duration
        error_message = str(report.longrepr) if report.longrepr else None
        error_type = report.outcome if hasattr(report, 'outcome') else None
        
        logger.log_test_result(
            test_name=report.nodeid.split("::")[-1],
            status=status,
            duration=duration,
            error_message=error_message,
            error_type=error_type,
            test_file=str(report.fspath) if hasattr(report, 'fspath') else None
        )

def pytest_sessionfinish(session, exitstatus):
    """Called after entire test session"""
    logger = get_test_logger()
    
    # Calculate session statistics from the session object
    total_tests = getattr(session, 'testscollected', 0)
    failed = getattr(session, 'testsfailed', 0)
    
    # Calculate passed tests (total - failed - skipped)
    # Note: pytest doesn't directly track passed tests, we calculate it
    passed = total_tests - failed
    skipped = 0  # We'll track this separately if needed
    
    # Calculate total duration (approximate)
    total_duration = 0
    if hasattr(session, '_session_start_time'):
        total_duration = (datetime.now() - session._session_start_time).total_seconds()
    
    logger.log_session_summary(total_tests, passed, failed, skipped, total_duration)

# Add session start time tracking
def pytest_sessionstart(session):
    """Called at start of test session"""
    session._session_start_time = datetime.now()