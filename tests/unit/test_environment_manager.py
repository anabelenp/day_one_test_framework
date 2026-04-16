#!/usr/bin/env python3
"""
Unit tests for EnvironmentManager module.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.environment_manager import (
    EnvironmentManager,
    Environment,
    ServiceConfig,
    EnvironmentConfig,
)


class TestEnvironmentEnum:
    """Tests for Environment enum"""

    def test_environment_values(self):
        """Test that all expected environments exist"""
        assert Environment.MOCK.value == "mock"
        assert Environment.LOCAL.value == "local"
        assert Environment.INTEGRATION.value == "integration"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"

    def test_environment_count(self):
        """Test that we have exactly 5 environments"""
        assert len(Environment) == 5


class TestServiceConfig:
    """Tests for ServiceConfig dataclass"""

    def test_service_config_creation(self):
        """Test basic ServiceConfig creation"""
        config = ServiceConfig(host="localhost", port=6379)
        assert config.host == "localhost"
        assert config.port == 6379
        assert config.ssl_enabled is False
        assert config.connection_pool_size == 10
        assert config.timeout == 30

    def test_service_config_with_auth(self):
        """Test ServiceConfig with authentication"""
        config = ServiceConfig(
            host="localhost",
            port=27017,
            username="admin",
            password="secret",
        )
        assert config.username == "admin"
        assert config.password == "secret"

    def test_connection_string_without_auth(self):
        """Test connection string generation without auth"""
        config = ServiceConfig(host="localhost", port=6379)
        assert config.connection_string == "tcp://localhost:6379"

    def test_connection_string_with_auth(self):
        """Test connection string generation with auth"""
        config = ServiceConfig(
            host="localhost",
            port=27017,
            username="admin",
            password="secret",
        )
        assert config.connection_string == "tcp://admin:secret@localhost:27017"

    def test_connection_string_with_ssl(self):
        """Test connection string generation with SSL"""
        config = ServiceConfig(host="localhost", port=6379, ssl_enabled=True)
        assert config.connection_string == "ssl://localhost:6379"


class TestEnvironmentManager:
    """Tests for EnvironmentManager class"""

    def setup_method(self):
        """Setup for each test"""
        self.manager = EnvironmentManager(config_dir="config")

    def teardown_method(self):
        """Cleanup after each test"""
        pass

    @patch.dict(os.environ, {"TESTING_MODE": "mock"}, clear=False)
    def test_detect_environment_from_env_var_mock(self):
        """Test environment detection from TESTING_MODE env var"""
        manager = EnvironmentManager()
        env = manager.detect_environment()
        assert env == Environment.MOCK

    @patch.dict(os.environ, {"TESTING_MODE": "local"}, clear=False)
    def test_detect_environment_from_env_var_local(self):
        """Test environment detection from TESTING_MODE env var"""
        manager = EnvironmentManager()
        env = manager.detect_environment()
        assert env == Environment.LOCAL

    @patch.dict(os.environ, {"TESTING_MODE": "production"}, clear=False)
    def test_detect_environment_from_env_var_production(self):
        """Test environment detection from TESTING_MODE env var"""
        manager = EnvironmentManager()
        env = manager.detect_environment()
        assert env == Environment.PRODUCTION

    @patch.dict(os.environ, {}, clear=True)
    @patch("src.environment_manager.EnvironmentManager._is_kubernetes_environment")
    def test_detect_kubernetes_staging(self, mock_k8s):
        """Test Kubernetes environment detection for staging"""
        mock_k8s.return_value = True
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            manager = EnvironmentManager()
            env = manager.detect_environment()
            assert env == Environment.STAGING

    @patch.dict(os.environ, {}, clear=True)
    @patch("src.environment_manager.EnvironmentManager._is_kubernetes_environment")
    def test_detect_kubernetes_production(self, mock_k8s):
        """Test Kubernetes environment detection for production"""
        mock_k8s.return_value = True
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            manager = EnvironmentManager()
            env = manager.detect_environment()
            assert env == Environment.PRODUCTION

    @patch.dict(os.environ, {}, clear=True)
    @patch("src.environment_manager.EnvironmentManager._is_kubernetes_environment")
    @patch("src.environment_manager.EnvironmentManager._is_docker_environment")
    @patch(
        "src.environment_manager.EnvironmentManager._is_local_development_environment"
    )
    @patch("pathlib.Path.exists")
    def test_detect_kubernetes_integration(
        self, mock_exists, mock_local, mock_docker, mock_k8s
    ):
        """Test Kubernetes environment detection defaults to integration"""
        mock_k8s.return_value = True
        mock_exists.return_value = False
        mock_local.return_value = False
        with patch.dict(os.environ, {}, clear=True):
            manager = EnvironmentManager()
            env = manager.detect_environment()
            assert env == Environment.INTEGRATION

    def test_get_current_environment_cached(self):
        """Test that get_current_environment caches result"""
        manager = EnvironmentManager()
        manager._current_environment = Environment.MOCK
        assert manager.get_current_environment() == Environment.MOCK
        assert manager._current_environment == Environment.MOCK

    def test_set_environment(self):
        """Test setting environment manually"""
        manager = EnvironmentManager()
        manager.set_environment(Environment.STAGING)
        assert manager.get_current_environment() == Environment.STAGING

    def test_set_environment_clears_cache(self):
        """Test that setting environment clears config cache"""
        manager = EnvironmentManager()
        manager._config_cache[Environment.LOCAL] = MagicMock()
        manager.set_environment(Environment.LOCAL)
        assert Environment.LOCAL not in manager._config_cache

    def test_get_environment_info(self):
        """Test getting comprehensive environment info"""
        with patch.object(self.manager, "load_configuration") as mock_load:
            mock_config = MagicMock()
            mock_config.name = "Test Environment"
            mock_config.redis.host = "localhost"
            mock_config.redis.port = 6379
            mock_config.redis.ssl_enabled = False
            mock_config.kafka.host = "localhost"
            mock_config.kafka.port = 9092
            mock_config.kafka.ssl_enabled = False
            mock_config.mongodb.host = "localhost"
            mock_config.mongodb.port = 27017
            mock_config.mongodb.database = "test"
            mock_config.target_api.host = "localhost"
            mock_config.target_api.port = 8080
            mock_config.target_api.ssl_enabled = False
            mock_config.aws_config = {}
            mock_config.monitoring = {}
            mock_config.security = {}
            mock_config.performance = {}
            mock_load.return_value = mock_config

            with patch.object(self.manager, "validate_environment", return_value=True):
                info = self.manager.get_environment_info(Environment.LOCAL)

            assert info["environment"] == "local"
            assert info["name"] == "Test Environment"
            assert info["valid"] is True
            assert "services" in info

    def test_get_service_config_redis(self):
        """Test getting Redis service config"""
        with patch.object(self.manager, "load_configuration") as mock_load:
            mock_config = MagicMock()
            mock_config.redis = ServiceConfig(host="redis.local", port=6379)
            mock_config.kafka = MagicMock()
            mock_config.mongodb = MagicMock()
            mock_config.target_api = MagicMock()
            mock_load.return_value = mock_config

            config = self.manager.get_service_config("redis")
            assert config.host == "redis.local"
            assert config.port == 6379

    def test_get_service_config_unknown_service(self):
        """Test that unknown service raises ValueError"""
        with pytest.raises(ValueError, match="Unknown service"):
            self.manager.get_service_config("unknown")

    def test_load_configuration_caching(self):
        """Test that configuration is cached"""
        with patch.object(self.manager, "_load_environment_config") as mock_load:
            mock_load.return_value = MagicMock()
            self.manager._config_cache.clear()

            config1 = self.manager.load_configuration(Environment.MOCK)
            config2 = self.manager.load_configuration(Environment.MOCK)

            assert config1 is config2
            assert mock_load.call_count == 1

    def test_validate_environment_success(self):
        """Test successful environment validation"""
        with patch.object(
            self.manager, "_validate_config_completeness", return_value=True
        ):
            with patch.object(
                self.manager, "_validate_service_connectivity", return_value=True
            ):
                with patch.object(self.manager, "load_configuration") as mock_load:
                    mock_config = MagicMock()
                    mock_config.environment = Environment.MOCK
                    mock_load.return_value = mock_config

                    result = self.manager.validate_environment(Environment.MOCK)
                    assert result is True

    def test_validate_environment_failure(self):
        """Test failed environment validation"""
        with patch.object(
            self.manager, "_validate_config_completeness", return_value=True
        ):
            with patch.object(
                self.manager, "_validate_service_connectivity", return_value=False
            ):
                with patch.object(self.manager, "load_configuration") as mock_load:
                    mock_config = MagicMock()
                    mock_config.environment = Environment.LOCAL
                    mock_load.return_value = mock_config

                    result = self.manager.validate_environment(Environment.LOCAL)
                    assert result is False

    def test_check_port_connectivity_success(self):
        """Test successful port connectivity check"""
        import socket

        with patch("socket.socket") as mock_socket:
            mock_sock_instance = MagicMock()
            mock_sock_instance.connect_ex.return_value = 0
            mock_socket.return_value = mock_sock_instance

            result = self.manager._check_port_connectivity("localhost", 6379, timeout=5)
            assert result is True

    def test_check_port_connectivity_failure(self):
        """Test failed port connectivity check"""
        with patch("socket.socket") as mock_socket:
            mock_sock_instance = MagicMock()
            mock_sock_instance.connect_ex.return_value = 1
            mock_socket.return_value = mock_sock_instance

            result = self.manager._check_port_connectivity("localhost", 6379, timeout=5)
            assert result is False

    def test_validate_config_completeness(self):
        """Test configuration completeness validation"""
        from dataclasses import dataclass

        valid_config = MagicMock()
        valid_config.redis = True
        valid_config.kafka = True
        valid_config.mongodb = True
        valid_config.target_api = True

        result = self.manager._validate_config_completeness(valid_config)
        assert result is True

    def test_validate_config_completeness_missing_field(self):
        """Test configuration completeness with missing fields"""
        invalid_config = MagicMock()
        del invalid_config.redis

        result = self.manager._validate_config_completeness(invalid_config)
        assert result is False


class TestGlobalFunctions:
    """Tests for global convenience functions"""

    def test_get_environment_manager_singleton(self):
        """Test that get_environment_manager returns singleton"""
        from src.environment_manager import (
            get_environment_manager,
            _environment_manager,
        )

        _environment_manager = None

        manager1 = get_environment_manager()
        manager2 = get_environment_manager()

        assert manager1 is manager2

    def test_get_current_environment_helper(self):
        """Test get_current_environment convenience function"""
        from src.environment_manager import get_current_environment

        with patch("src.environment_manager.get_environment_manager") as mock_mgr:
            mock_instance = MagicMock()
            mock_instance.get_current_environment.return_value = Environment.MOCK
            mock_mgr.return_value = mock_instance

            result = get_current_environment()
            assert result == Environment.MOCK


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
