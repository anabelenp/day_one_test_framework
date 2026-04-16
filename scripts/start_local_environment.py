#!/usr/bin/env python3
"""
Local Environment Startup Script for Day-1 Framework

This script orchestrates the startup of the complete local development environment
including all services, monitoring, and validation.

Usage:
    python scripts/start_local_environment.py --start
    python scripts/start_local_environment.py --stop
    python scripts/start_local_environment.py --status
"""

import os
import sys
import time
import subprocess
import requests
import logging
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.environment_manager import EnvironmentManager, Environment
from src.service_manager import ServiceManager


class LocalEnvironmentManager:
    """Manages the local development environment startup and validation"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_logging()

        # Initialize managers
        self.env_manager = EnvironmentManager()
        self.service_manager = ServiceManager()

        # Service health check endpoints
        self.health_checks = {
            "redis": ("localhost", 6379),
            "kafka": ("localhost", 9092),
            "mongodb": ("localhost", 27017),
            "localstack": ("localhost", 4566, "/health"),
            "prometheus": ("localhost", 9090, "/-/healthy"),
            "grafana": ("localhost", 3000, "/api/health"),
            "jaeger": ("localhost", 16686, "/"),
        }

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("logs/local_environment.log"),
            ],
        )

    def start_environment(self) -> bool:
        """
        Start the complete local environment

        Returns:
            bool: True if environment started successfully
        """
        try:
            self.logger.info(" Starting Day-1 Local Environment...")

            # Step 1: Set environment mode
            self.env_manager.set_environment(Environment.LOCAL)

            # Step 2: Start Docker services
            if not self._start_docker_services():
                return False

            # Step 3: Wait for services to be ready
            if not self._wait_for_services():
                return False

            # Step 4: Initialize services
            if not self._initialize_services():
                return False

            # Step 5: Validate environment
            if not self._validate_environment():
                return False

            # Step 6: Display environment information
            self._display_environment_info()

            self.logger.info(" Local environment started successfully!")
            return True

        except Exception as e:
            self.logger.error(f" Failed to start local environment: {e}")
            return False

    def stop_environment(self) -> bool:
        """
        Stop the local environment

        Returns:
            bool: True if environment stopped successfully
        """
        try:
            self.logger.info(" Stopping Day-1 Local Environment...")

            # Disconnect service clients
            self.service_manager.disconnect_all()

            # Stop Docker services
            result = subprocess.run(
                ["docker-compose", "-f", "docker-compose.local.yml", "down"],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                self.logger.error(f"Failed to stop Docker services: {result.stderr}")
                return False

            self.logger.info(" Local environment stopped successfully!")
            return True

        except Exception as e:
            self.logger.error(f" Failed to stop local environment: {e}")
            return False

    def restart_environment(self) -> bool:
        """
        Restart the local environment

        Returns:
            bool: True if environment restarted successfully
        """
        self.logger.info(" Restarting local environment...")

        if not self.stop_environment():
            return False

        # Wait a bit before restarting
        time.sleep(5)

        return self.start_environment()

    def _start_docker_services(self) -> bool:
        """Start Docker Compose services"""
        self.logger.info(" Starting Docker services...")

        try:
            # Check if Docker is running
            result = subprocess.run(["docker", "info"], capture_output=True, text=True)
            if result.returncode != 0:
                self.logger.error("Docker is not running. Please start Docker Desktop.")
                return False

            # Start services
            result = subprocess.run(
                ["docker-compose", "-f", "docker-compose.local.yml", "up", "-d"],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                self.logger.error(f"Failed to start Docker services: {result.stderr}")
                return False

            self.logger.info(" Docker services started")
            return True

        except FileNotFoundError:
            self.logger.error(
                "Docker or docker-compose not found. Please install Docker Desktop."
            )
            return False
        except Exception as e:
            self.logger.error(f"Error starting Docker services: {e}")
            return False

    def _wait_for_services(self, timeout: int = 300) -> bool:
        """Wait for all services to be ready"""
        self.logger.info("⏳ Waiting for services to be ready...")

        start_time = time.time()

        for service_name, check_info in self.health_checks.items():
            self.logger.info(f"Checking {service_name}...")

            host, port = check_info[0], check_info[1]
            endpoint = check_info[2] if len(check_info) > 2 else None

            if not self._wait_for_service(service_name, host, port, endpoint, timeout):
                return False

            # Check timeout
            if time.time() - start_time > timeout:
                self.logger.error(f"Timeout waiting for services (>{timeout}s)")
                return False

        self.logger.info(" All services are ready")
        return True

    def _wait_for_service(
        self, name: str, host: str, port: int, endpoint: str = None, timeout: int = 60
    ) -> bool:
        """Wait for a specific service to be ready"""

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                if endpoint:
                    # HTTP health check
                    url = f"http://{host}:{port}{endpoint}"
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        self.logger.info(f" {name} is ready")
                        return True
                else:
                    # TCP port check
                    import socket

                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex((host, port))
                    sock.close()

                    if result == 0:
                        self.logger.info(f" {name} is ready")
                        return True

            except Exception:
                pass

            time.sleep(2)

        self.logger.error(f" {name} failed to start within {timeout}s")
        return False

    def _initialize_services(self) -> bool:
        """Initialize services with test data and configuration"""
        self.logger.info(" Initializing services...")

        try:
            # Test service connections
            cache_client = self.service_manager.get_cache_client()
            message_client = self.service_manager.get_message_client()
            db_client = self.service_manager.get_database_client()
            api_client = self.service_manager.get_api_client()

            # Initialize test data
            self._initialize_test_data(cache_client, message_client, db_client)

            self.logger.info(" Services initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f" Failed to initialize services: {e}")
            return False

    def _initialize_test_data(self, cache_client, message_client, db_client):
        """Initialize test data in services"""

        # Initialize cache with test data
        cache_client.set("test_key", "test_value")
        cache_client.set("environment", "local")

        # Create test topics in Kafka
        message_client.create_topic("security_events")
        message_client.create_topic("audit_logs")
        message_client.create_topic("policy_violations")

        # Publish test message
        message_client.publish(
            "security_events",
            {
                "event_type": "test_event",
                "message": "Local environment initialization",
                "timestamp": time.time(),
            },
        )

        # Test database operations
        test_doc_id = db_client.insert_one(
            "test_collection",
            {
                "name": "local_environment_test",
                "status": "initialized",
                "timestamp": time.time(),
            },
        )

        self.logger.info(
            f"Initialized test data - Cache: , Kafka: , MongoDB:  (doc: {test_doc_id})"
        )

    def _validate_environment(self) -> bool:
        """Validate that the environment is working correctly"""
        self.logger.info(" Validating environment...")

        try:
            # Validate environment configuration
            if not self.env_manager.validate_environment():
                self.logger.error("Environment validation failed")
                return False

            # Validate service health
            health_results = self.service_manager.health_check_all()

            failed_services = [
                service for service, healthy in health_results.items() if not healthy
            ]

            if failed_services:
                self.logger.error(f"Unhealthy services: {failed_services}")
                return False

            self.logger.info(" Environment validation passed")
            return True

        except Exception as e:
            self.logger.error(f" Environment validation failed: {e}")
            return False

    def _display_environment_info(self):
        """Display environment information and access URLs"""

        info = self.env_manager.get_environment_info()

        print("\n" + "=" * 60)
        print(" DAY-1 LOCAL ENVIRONMENT READY")
        print("=" * 60)

        print(f"\n Environment: {info['name']}")
        print(f" Mode: {info['environment']}")
        print(f" Status: {'Healthy' if info['valid'] else 'Unhealthy'}")

        print("\n Service Access URLs:")
        print(
            "    Grafana Dashboard:    http://localhost:3000 (admin/netskope_grafana_2024)"
        )
        print("    Prometheus Metrics:   http://localhost:9090")
        print("    Jaeger Tracing:       http://localhost:16686")
        print("     LocalStack Console:   http://localhost:4566")

        print("\n Database Access:")
        print("    Redis:     localhost:6379")
        print("    Kafka:     localhost:9092")
        print("    MongoDB:   localhost:27017 (netskope_app/netskope_app_2024)")

        print("\n Test Commands:")
        print("   pytest tests/integration/ -v")
        print("   pytest tests/e2e/ -v")
        print("   python src/service_manager.py health")
        print("   python src/environment_manager.py info")

        print("\n Stop Environment:")
        print("   python scripts/start_local_environment.py --stop")
        print("   docker-compose -f docker-compose.local.yml down")

        print("\n" + "=" * 60)


def main():
    """Main function for CLI usage"""
    import argparse

    parser = argparse.ArgumentParser(description="Day-1 Local Environment Manager")
    parser.add_argument(
        "--start", action="store_true", help="Start the local environment"
    )
    parser.add_argument(
        "--stop", action="store_true", help="Stop the local environment"
    )
    parser.add_argument(
        "--restart", action="store_true", help="Restart the local environment"
    )
    parser.add_argument(
        "--status", action="store_true", help="Check environment status"
    )

    args = parser.parse_args()

    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    env_manager = LocalEnvironmentManager()

    if args.stop:
        success = env_manager.stop_environment()
        sys.exit(0 if success else 1)

    elif args.restart:
        success = env_manager.restart_environment()
        sys.exit(0 if success else 1)

    elif args.status:
        # Check status without starting
        try:
            service_manager = ServiceManager()
            health_results = service_manager.health_check_all()

            print(" Service Health Status:")
            for service, healthy in health_results.items():
                status = " Healthy" if healthy else " Unhealthy"
                print(f"   {service}: {status}")

            all_healthy = all(health_results.values())
            print(
                f"\n Overall Status: {' All services healthy' if all_healthy else ' Some services unhealthy'}"
            )

        except Exception as e:
            print(f" Failed to check status: {e}")
            sys.exit(1)

    else:
        # Default action is to start
        success = env_manager.start_environment()

        if success:
            print("\n Environment is ready for testing!")
            print("   Use Ctrl+C to keep environment running, or --stop to shut down")

            try:
                # Keep running until interrupted
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                print("\n\n Keeping environment running...")
                print(
                    "   Use 'python scripts/start_local_environment.py --stop' to shut down"
                )

        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
