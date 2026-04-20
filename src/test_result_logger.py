#!/usr/bin/env python3
"""
Test Result Logger for MongoDB Integration

Automatically stores test results, metrics, and execution data in MongoDB
for monitoring, analysis, and reporting.
"""

import json
import logging
import sys
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pytest
import os
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler

from .service_manager import get_database_client
from .environment_manager import get_current_environment

try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class ResultLogger:
    """Logs test results to MongoDB for monitoring and analysis"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_client = None
        self.collection_name = "test_results"
        self.session_id = None
        self.environment = None
        self._skipped_count = 0
        self._metrics_server = None
        self._init_prometheus_metrics()

    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics if prometheus_client is available"""
        if not PROMETHEUS_AVAILABLE:
            self.logger.warning("prometheus_client not available, metrics disabled")
            return

        try:
            self.pytest_tests_total = Counter(
                'pytest_tests_total',
                'Total number of pytest tests',
                ['environment', 'status', 'test_file', 'test_name']
            )
            self.pytest_test_duration_seconds = Histogram(
                'pytest_test_duration_seconds',
                'Test duration in seconds',
                ['environment', 'test_file', 'test_name']
            )
            self.pytest_session_tests = Gauge(
                'pytest_session_tests',
                'Number of tests in current session',
                ['environment', 'status']
            )
            self.pytest_success_rate = Gauge(
                'pytest_success_rate',
                'Current test suite success rate',
                ['environment']
            )
            self.logger.info("Prometheus metrics initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Prometheus metrics: {e}")

    def initialize(self):
        """Initialize database connection and session"""
        try:
            self.db_client = get_database_client()
            self.environment = get_current_environment().value
            self.session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.logger.info(
                f"Test result logger initialized for environment: {self.environment}"
            )
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
                    "python_version": sys.version,
                    "environment_vars": {
                        "TESTING_MODE": os.getenv("TESTING_MODE"),
                        "CI": os.getenv("CI", "false"),
                    },
                },
            }

            doc_id = self.db_client.insert_one(self.collection_name, test_doc)
            self.logger.debug(f"Logged test start: {test_name} -> {doc_id}")
            return doc_id

        except Exception as e:
            self.logger.error(f"Failed to log test start: {e}")
            return None

    def log_test_result(
        self,
        test_name: str,
        status: str,
        duration: float,
        error_message: str = None,
        error_type: str = None,
        test_output: str = None,
        **kwargs,
    ):
        """Log test completion with results"""
        if not self.db_client:
            return

        try:
            # Find the test document
            test_filter = {
                "session_id": self.session_id,
                "test_name": test_name,
                "status": "running",
            }

            update_data = {
                "status": status,
                "end_time": datetime.now(),
                "duration": duration,
                "error_message": error_message,
                "error_type": error_type,
                "test_output": test_output,
                "additional_data": kwargs,
            }

            # Update existing document or create new one
            success = self.db_client.update_one(
                self.collection_name, test_filter, update_data
            )

            if not success:
                # Create new document if update failed
                test_doc = {
                    "session_id": self.session_id,
                    "test_name": test_name,
                    "environment": self.environment,
                    "start_time": datetime.now() - timedelta(seconds=duration),
                    **update_data,
                }
                doc_id = self.db_client.insert_one(self.collection_name, test_doc)
                self.logger.debug(f"Created new test result: {test_name} -> {doc_id}")
            else:
                self.logger.debug(f"Updated test result: {test_name} -> {status}")

            self._update_prometheus_metrics(test_name, status, duration, kwargs.get('test_file', 'unknown'))

        except Exception as e:
            self.logger.error(f"Failed to log test result: {e}")

    def _update_prometheus_metrics(self, test_name: str, status: str, duration: float, test_file: str):
        """Update Prometheus metrics"""
        if not PROMETHEUS_AVAILABLE:
            return

        try:
            self.pytest_tests_total.labels(
                environment=self.environment,
                status=status,
                test_file=test_file,
                test_name=test_name
            ).inc()

            self.pytest_test_duration_seconds.labels(
                environment=self.environment,
                test_file=test_file,
                test_name=test_name
            ).observe(duration)
        except Exception as e:
            self.logger.debug(f"Failed to update Prometheus metrics: {e}")

    def log_session_summary(
        self,
        total_tests: int,
        passed: int,
        failed: int,
        skipped: int,
        total_duration: float,
    ):
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
                "avg_test_duration": (total_duration / total_tests)
                if total_tests > 0
                else 0,
            }

            doc_id = self.db_client.insert_one("test_sessions", summary_doc)
            self.logger.info(f"Logged session summary: {self.session_id} -> {doc_id}")

            if PROMETHEUS_AVAILABLE:
                try:
                    self.pytest_session_tests.labels(
                        environment=self.environment,
                        status='total'
                    ).set(total_tests)
                    self.pytest_session_tests.labels(
                        environment=self.environment,
                        status='passed'
                    ).set(passed)
                    self.pytest_session_tests.labels(
                        environment=self.environment,
                        status='failed'
                    ).set(failed)
                    self.pytest_success_rate.labels(
                        environment=self.environment
                    ).set(summary_doc['success_rate'])
                except Exception as e:
                    self.logger.debug(f"Failed to update session Prometheus metrics: {e}")

        except Exception as e:
            self.logger.error(f"Failed to log session summary: {e}")


# Global logger instance with thread safety
import threading

_test_logger = None
_test_logger_lock = threading.Lock()


def get_test_logger() -> ResultLogger:
    """Get global test result logger instance (thread-safe)"""
    global _test_logger
    if _test_logger is None:
        with _test_logger_lock:
            if _test_logger is None:
                _test_logger = ResultLogger()
                _test_logger.initialize()
    return _test_logger


def reset_test_logger() -> None:
    """Reset the global test logger (useful for testing)"""
    global _test_logger
    with _test_logger_lock:
        _test_logger = None


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
        if report.skipped:
            logger._skipped_count += 1
        duration = report.duration
        error_message = str(report.longrepr) if report.longrepr else None
        error_type = report.outcome if hasattr(report, "outcome") else None

        logger.log_test_result(
            test_name=report.nodeid.split("::")[-1],
            status=status,
            duration=duration,
            error_message=error_message,
            error_type=error_type,
            test_file=str(report.fspath) if hasattr(report, "fspath") else None,
        )


def pytest_sessionfinish(session, exitstatus):
    """Called after entire test session"""
    logger = get_test_logger()

    # Calculate session statistics from the session object
    total_tests = getattr(session, "testscollected", 0)
    failed = getattr(session, "testsfailed", 0)
    skipped = logger._skipped_count
    passed = total_tests - failed - skipped

    # Calculate total duration (approximate)
    total_duration = 0
    if hasattr(session, "_session_start_time"):
        total_duration = (datetime.now() - session._session_start_time).total_seconds()

    logger.log_session_summary(total_tests, passed, failed, skipped, total_duration)


# Add session start time tracking
def pytest_sessionstart(session):
    """Called at start of test session"""
    session._session_start_time = datetime.now()


# Prometheus metrics HTTP server
class PrometheusMetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for Prometheus metrics endpoint"""

    def do_GET(self):
        if self.path == '/metrics' or self.path == '/metrics/':
            if PROMETHEUS_AVAILABLE:
                try:
                    metrics_output = generate_latest(REGISTRY)
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain; version=0.0.4')
                    self.end_headers()
                    self.wfile.write(metrics_output)
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(f"Error generating metrics: {e}".encode())
            else:
                self.send_response(503)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b"Prometheus metrics not available (prometheus_client not installed)")
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Not Found")

    def log_message(self, format, *args):
        pass  # Suppress HTTP logging


def start_metrics_server(port: int = 9091):
    """Start the Prometheus metrics HTTP server"""
    if not PROMETHEUS_AVAILABLE:
        logging.warning("Cannot start metrics server: prometheus_client not installed")
        return None

    try:
        server = HTTPServer(('0.0.0.0', port), PrometheusMetricsHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        logging.info(f"Prometheus metrics server started on port {port}")
        return server
    except Exception as e:
        logging.error(f"Failed to start metrics server: {e}")
        return None
