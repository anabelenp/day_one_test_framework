#!/usr/bin/env python3
"""
Environment Manager for Day-1 Framework

Manages multi-environment configuration and service discovery across:
- Mock Environment (E1)
- Local Environment (E2)
- Integration Environment (E3)
- Staging Environment (E4)
- Production Environment (E5)
"""

import os
import re
import yaml
import logging
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
from pathlib import Path


def expand_env_vars(value: Any) -> Any:
    """Recursively expand environment variables in config values.

    Supports ${VAR} and ${VAR:-default} syntax.
    """
    if isinstance(value, str):
        pattern = r"\$\{([^}:]+)(?::-([^}]*))?\}"

        def replacer(match):
            var_name = match.group(1)
            default = match.group(2) if match.group(2) is not None else ""
            return os.environ.get(var_name, default)

        return re.sub(pattern, replacer, value)
    elif isinstance(value, dict):
        return {k: expand_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [expand_env_vars(item) for item in value]
    return value


class Environment(Enum):
    """Supported testing environments"""

    MOCK = "mock"
    LOCAL = "local"
    INTEGRATION = "integration"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class ServiceConfig:
    """Service configuration for a specific environment"""

    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    auth_source: Optional[str] = "admin"
    ssl_enabled: bool = False
    connection_pool_size: int = 10
    timeout: int = 30

    @property
    def connection_string(self) -> str:
        """Generate connection string for the service"""
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        else:
            auth = ""

        protocol = "ssl" if self.ssl_enabled else "tcp"
        return f"{protocol}://{auth}{self.host}:{self.port}"


@dataclass
class EnvironmentConfig:
    """Complete environment configuration"""

    name: str
    environment: Environment
    redis: ServiceConfig
    kafka: ServiceConfig
    mongodb: ServiceConfig
    target_api: ServiceConfig
    aws_config: Dict[str, Any]
    monitoring: Dict[str, Any]
    security: Dict[str, Any]
    performance: Dict[str, Any]


class EnvironmentManager:
    """Manages environment detection, configuration, and service discovery"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.logger = logging.getLogger(__name__)
        self._current_environment: Optional[Environment] = None
        self._config_cache: Dict[Environment, EnvironmentConfig] = {}

        # Initialize logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    def detect_environment(self) -> Environment:
        """
        Detect current environment based on various indicators

        Priority order:
        1. TESTING_MODE environment variable
        2. Kubernetes environment detection
        3. Docker environment detection
        4. Local development detection (Docker Compose services)
        5. Configuration file detection
        6. Default to mock
        """
        # Check environment variable
        env_mode = os.getenv("TESTING_MODE", "").lower()
        if env_mode in [e.value for e in Environment]:
            self.logger.info(f"Environment detected from TESTING_MODE: {env_mode}")
            return Environment(env_mode)

        # Check for Kubernetes environment
        if self._is_kubernetes_environment():
            if os.getenv("ENVIRONMENT") == "production":
                return Environment.PRODUCTION
            elif os.getenv("ENVIRONMENT") == "staging":
                return Environment.STAGING
            else:
                return Environment.INTEGRATION

        # Check for Docker environment (local development)
        if self._is_docker_environment():
            return Environment.LOCAL

        # Check for local development environment (Docker Compose services running)
        if self._is_local_development_environment():
            self.logger.info(
                "Local development environment detected (Docker Compose services)"
            )
            return Environment.LOCAL

        # Check configuration files (only if no local development detected)
        if (self.config_dir / "local.yaml").exists():
            # If local.yaml exists and we're not in K8s/Docker, assume local development
            return Environment.LOCAL
        elif (self.config_dir / "integration.yaml").exists():
            return Environment.INTEGRATION
        elif (self.config_dir / "staging.yaml").exists():
            return Environment.STAGING
        elif (self.config_dir / "production.yaml").exists():
            return Environment.PRODUCTION

        # Default to mock
        self.logger.info("No specific environment detected, defaulting to mock")
        return Environment.MOCK

    def get_current_environment(self) -> Environment:
        """Get the current active environment"""
        if self._current_environment is None:
            self._current_environment = self.detect_environment()
        return self._current_environment

    def set_environment(self, environment: Environment) -> None:
        """Manually set the current environment"""
        self.logger.info(f"Switching to {environment.value} environment")
        self._current_environment = environment

        # Clear cache to force reload
        if environment in self._config_cache:
            del self._config_cache[environment]

    def load_configuration(
        self, environment: Optional[Environment] = None
    ) -> EnvironmentConfig:
        """
        Load configuration for specified environment

        Args:
            environment: Target environment (defaults to current)

        Returns:
            EnvironmentConfig: Complete environment configuration
        """
        if environment is None:
            environment = self.get_current_environment()

        # Check cache first
        if environment in self._config_cache:
            return self._config_cache[environment]

        # Load configuration
        config = self._load_environment_config(environment)

        # Cache configuration
        self._config_cache[environment] = config

        self.logger.info(f"Loaded configuration for {environment.value} environment")
        return config

    def validate_environment(self, environment: Optional[Environment] = None) -> bool:
        """
        Validate that the environment is properly configured and accessible

        Args:
            environment: Target environment (defaults to current)

        Returns:
            bool: True if environment is valid and accessible
        """
        if environment is None:
            environment = self.get_current_environment()

        try:
            config = self.load_configuration(environment)

            # Validate configuration completeness
            if not self._validate_config_completeness(config):
                return False

            # For non-mock environments, validate service connectivity
            if environment != Environment.MOCK:
                return self._validate_service_connectivity(config)

            return True

        except Exception as e:
            self.logger.error(f"Environment validation failed: {str(e)}")
            return False

    def get_service_config(
        self, service_name: str, environment: Optional[Environment] = None
    ) -> ServiceConfig:
        """
        Get configuration for a specific service

        Args:
            service_name: Name of the service (redis, kafka, mongodb, target_api)
            environment: Target environment (defaults to current)

        Returns:
            ServiceConfig: Service configuration
        """
        config = self.load_configuration(environment)

        service_configs = {
            "redis": config.redis,
            "kafka": config.kafka,
            "mongodb": config.mongodb,
            "target_api": config.target_api,
        }

        if service_name not in service_configs:
            raise ValueError(f"Unknown service: {service_name}")

        return service_configs[service_name]

    def get_environment_info(
        self, environment: Optional[Environment] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive environment information

        Args:
            environment: Target environment (defaults to current)

        Returns:
            Dict: Environment information including config, status, and metadata
        """
        if environment is None:
            environment = self.get_current_environment()

        config = self.load_configuration(environment)
        is_valid = self.validate_environment(environment)

        return {
            "environment": environment.value,
            "name": config.name,
            "valid": is_valid,
            "services": {
                "redis": {
                    "host": config.redis.host,
                    "port": config.redis.port,
                    "ssl_enabled": config.redis.ssl_enabled,
                },
                "kafka": {
                    "host": config.kafka.host,
                    "port": config.kafka.port,
                    "ssl_enabled": config.kafka.ssl_enabled,
                },
                "mongodb": {
                    "host": config.mongodb.host,
                    "port": config.mongodb.port,
                    "database": config.mongodb.database,
                },
                "target_api": {
                    "host": config.target_api.host,
                    "port": config.target_api.port,
                    "ssl_enabled": config.target_api.ssl_enabled,
                },
            },
            "aws_config": config.aws_config,
            "monitoring": config.monitoring,
            "security": config.security,
            "performance": config.performance,
        }

    def _load_environment_config(self, environment: Environment) -> EnvironmentConfig:
        """Load configuration from files for specific environment"""

        # Define configuration file paths
        config_files = [
            self.config_dir / f"{environment.value}.yaml",
            self.config_dir / "env.yaml",  # Fallback to current env.yaml
            self.config_dir / "default.yaml",  # Default configuration
        ]

        # Load base configuration
        base_config = self._load_base_config()

        # Load environment-specific configuration
        env_config = {}
        for config_file in config_files:
            if config_file.exists():
                with open(config_file, "r") as f:
                    file_config = yaml.safe_load(f) or {}
                    # Expand environment variables in config
                    file_config = expand_env_vars(file_config)
                    env_config.update(file_config)
                break

        # Merge configurations (environment-specific overrides base)
        merged_config = {**base_config, **env_config}

        # Create EnvironmentConfig object
        return self._create_environment_config(environment, merged_config)

    def _load_base_config(self) -> Dict[str, Any]:
        """Load base configuration with defaults for all environments"""
        return {
            # Default service configurations
            "redis": {
                "host": "localhost",
                "port": 6379,
                "ssl_enabled": False,
                "connection_pool_size": 10,
                "timeout": 30,
            },
            "kafka": {
                "host": "localhost",
                "port": 9092,
                "ssl_enabled": False,
                "connection_pool_size": 10,
                "timeout": 30,
            },
            "mongodb": {
                "host": "localhost",
                "port": 27017,
                "database": "day1_test",
                "ssl_enabled": False,
                "connection_pool_size": 10,
                "timeout": 30,
            },
            "target_api": {
                "host": "localhost",
                "port": 8080,
                "ssl_enabled": False,
                "timeout": 30,
            },
            "aws_config": {
                "region": "us-east-1",
                "endpoint_url": None,
                "access_key_id": None,
                "secret_access_key": None,
            },
            "monitoring": {
                "enabled": True,
                "prometheus_url": "http://localhost:9090",
                "grafana_url": "http://localhost:3000",
            },
            "security": {
                "tls_enabled": False,
                "mutual_tls": False,
                "encryption_at_rest": False,
                "audit_logging": True,
            },
            "performance": {
                "max_concurrent_connections": 100,
                "connection_pool_size": 10,
                "cache_ttl": 300,
                "batch_size": 100,
            },
        }

    def _create_environment_config(
        self, environment: Environment, config: Dict[str, Any]
    ) -> EnvironmentConfig:
        """Create EnvironmentConfig object from configuration dictionary"""

        # Create service configurations
        redis_config = ServiceConfig(**config.get("redis", {}))
        kafka_config = ServiceConfig(**config.get("kafka", {}))
        mongodb_config = ServiceConfig(**config.get("mongodb", {}))
        target_config = ServiceConfig(**config.get("target_api", {}))

        return EnvironmentConfig(
            name=config.get("name", f"{environment.value.title()} Environment"),
            environment=environment,
            redis=redis_config,
            kafka=kafka_config,
            mongodb=mongodb_config,
            target_api=target_config,
            aws_config=config.get("aws_config", {}),
            monitoring=config.get("monitoring", {}),
            security=config.get("security", {}),
            performance=config.get("performance", {}),
        )

    def _is_kubernetes_environment(self) -> bool:
        """Check if running in Kubernetes environment"""
        return (
            os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount")
            or os.getenv("KUBERNETES_SERVICE_HOST") is not None
        )

    def _is_docker_environment(self) -> bool:
        """Check if running in Docker environment"""
        return (
            os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER") is not None
        )

    def _is_local_development_environment(self) -> bool:
        """Check if local development environment is active (Docker Compose services)"""
        import socket

        # Check if typical local development services are running
        local_services = [
            ("localhost", 6379),  # Redis
            ("localhost", 9092),  # Kafka
            ("localhost", 27017),  # MongoDB
            ("localhost", 9090),  # Prometheus
            ("localhost", 3000),  # Grafana
        ]

        # If at least 3 out of 5 services are running, assume local development
        running_services = 0
        for host, port in local_services:
            if self._check_port_connectivity(host, port, timeout=1):
                running_services += 1

        return running_services >= 3

    def _validate_config_completeness(self, config: EnvironmentConfig) -> bool:
        """Validate that configuration has all required fields"""
        required_fields = ["redis", "kafka", "mongodb", "target_api"]

        for field in required_fields:
            if not hasattr(config, field):
                self.logger.error(f"Missing required configuration field: {field}")
                return False

        return True

    def _validate_service_connectivity(self, config: EnvironmentConfig) -> bool:
        """Validate connectivity to all configured services"""
        import socket
        import time

        services_to_check = [
            ("Redis", config.redis.host, config.redis.port),
            ("Kafka", config.kafka.host, config.kafka.port),
            ("MongoDB", config.mongodb.host, config.mongodb.port),
        ]

        # Only check Target API for non-local environments
        if config.environment != Environment.LOCAL:
            services_to_check.append(
                ("Target API", config.target_api.host, config.target_api.port)
            )

        self.logger.info(
            f"Validating connectivity for {len(services_to_check)} services..."
        )

        for service_name, host, port in services_to_check:
            self.logger.info(f"Checking {service_name} at {host}:{port}...")
            if not self._check_port_connectivity(host, port, timeout=10):
                self.logger.warning(f"{service_name} not accessible at {host}:{port}")
                return False
            else:
                self.logger.info(f"{service_name} is accessible at {host}:{port}")

        self.logger.info("All services are accessible")
        return True

    def _check_port_connectivity(self, host: str, port: int, timeout: int = 10) -> bool:
        """Check if a specific host:port is accessible"""
        import socket

        try:
            self.logger.debug(
                f"Creating socket connection to {host}:{port} with timeout {timeout}s"
            )
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            self.logger.debug(f"Connection result for {host}:{port}: {result}")
            return result == 0
        except Exception as e:
            self.logger.error(
                f"Exception during connectivity check for {host}:{port}: {e}"
            )
            return False


# Global environment manager instance with thread safety
import threading

_environment_manager = None
_environment_manager_lock = threading.Lock()


def get_environment_manager() -> EnvironmentManager:
    """Get global environment manager instance (thread-safe)"""
    global _environment_manager
    if _environment_manager is None:
        with _environment_manager_lock:
            if _environment_manager is None:
                _environment_manager = EnvironmentManager()
    return _environment_manager


def reset_environment_manager() -> None:
    """Reset the global environment manager (useful for testing)"""
    global _environment_manager
    with _environment_manager_lock:
        _environment_manager = None


def get_current_environment() -> Environment:
    """Get current environment (convenience function)"""
    return get_environment_manager().get_current_environment()


def get_service_config(service_name: str) -> ServiceConfig:
    """Get service configuration for current environment (convenience function)"""
    return get_environment_manager().get_service_config(service_name)


# CLI interface for environment management
if __name__ == "__main__":
    import sys
    import json

    def print_usage():
        print("Usage: python environment_manager.py <command> [args]")
        print("Commands:")
        print("  detect                    - Detect current environment")
        print("  info [environment]        - Show environment information")
        print("  validate [environment]    - Validate environment configuration")
        print("  set <environment>         - Set current environment")
        print("  list                      - List all available environments")

    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()
    env_manager = EnvironmentManager()

    if command == "detect":
        current_env = env_manager.detect_environment()
        print(f"Detected environment: {current_env.value}")

    elif command == "info":
        target_env = None
        if len(sys.argv) > 2:
            try:
                target_env = Environment(sys.argv[2])
            except ValueError:
                print(f"Invalid environment: {sys.argv[2]}")
                sys.exit(1)

        info = env_manager.get_environment_info(target_env)
        print(json.dumps(info, indent=2))

    elif command == "validate":
        target_env = None
        if len(sys.argv) > 2:
            try:
                target_env = Environment(sys.argv[2])
            except ValueError:
                print(f"Invalid environment: {sys.argv[2]}")
                sys.exit(1)

        is_valid = env_manager.validate_environment(target_env)
        env_name = (
            target_env.value
            if target_env
            else env_manager.get_current_environment().value
        )

        if is_valid:
            print(f" {env_name} environment is valid and accessible")
        else:
            print(f" {env_name} environment validation failed")
            sys.exit(1)

    elif command == "set":
        if len(sys.argv) < 3:
            print("Error: Environment name required")
            print_usage()
            sys.exit(1)

        try:
            target_env = Environment(sys.argv[2])
            env_manager.set_environment(target_env)
            print(f" Environment set to: {target_env.value}")
        except ValueError:
            print(f"Invalid environment: {sys.argv[2]}")
            sys.exit(1)

    elif command == "list":
        print("Available environments:")
        for env in Environment:
            current = "(*)" if env == env_manager.get_current_environment() else "   "
            print(f"  {current} {env.value}")

    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)
