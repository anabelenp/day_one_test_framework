#!/usr/bin/env python3
"""
Unit tests for CLI module.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


class TestSetupLogging:
    """Tests for setup_logging function"""

    def test_setup_logging_verbose(self):
        """Test logging setup with verbose=True"""
        from src.cli import setup_logging
        import logging

        with patch("logging.basicConfig") as mock_config:
            setup_logging(verbose=True)
            mock_config.assert_called_once()
            call_kwargs = mock_config.call_args[1]
            assert call_kwargs["level"] == logging.DEBUG

    def test_setup_logging_non_verbose(self):
        """Test logging setup with verbose=False"""
        from src.cli import setup_logging
        import logging

        with patch("logging.basicConfig") as mock_config:
            setup_logging(verbose=False)
            mock_config.assert_called_once()
            call_kwargs = mock_config.call_args[1]
            assert call_kwargs["level"] == logging.INFO


class TestCmdEnvironment:
    """Tests for cmd_environment function"""

    def test_detect_environment(self):
        """Test environment detection command"""
        from src.cli import cmd_environment
        from argparse import Namespace

        with patch("src.cli.EnvironmentManager") as mock_manager:
            mock_instance = MagicMock()
            mock_instance.detect_environment.return_value = MagicMock(value="mock")
            mock_manager.return_value = mock_instance

            args = Namespace(env_action="detect", environment=None)

            result = cmd_environment(args)
            assert result == 0

    def test_environment_set_success(self):
        """Test setting environment successfully"""
        from src.cli import cmd_environment
        from argparse import Namespace

        with patch("src.cli.EnvironmentManager") as mock_manager:
            mock_instance = MagicMock()
            mock_manager.return_value = mock_instance

            args = Namespace(env_action="set", environment="local")

            result = cmd_environment(args)
            assert result == 0

    def test_environment_set_invalid(self):
        """Test setting invalid environment"""
        from src.cli import cmd_environment
        from argparse import Namespace

        with patch("src.cli.EnvironmentManager") as mock_manager:
            args = Namespace(env_action="set", environment="invalid_env")

            result = cmd_environment(args)
            assert result == 1

    def test_environment_validate_success(self):
        """Test environment validation success"""
        from src.cli import cmd_environment
        from argparse import Namespace

        with patch("src.cli.EnvironmentManager") as mock_manager:
            mock_instance = MagicMock()
            mock_instance.validate_environment.return_value = True
            mock_instance.get_current_environment.return_value = MagicMock(value="mock")
            mock_manager.return_value = mock_instance

            args = Namespace(env_action="validate", environment="mock")

            result = cmd_environment(args)
            assert result == 0

    def test_environment_validate_failure(self):
        """Test environment validation failure"""
        from src.cli import cmd_environment
        from src.environment_manager import reset_environment_manager
        from argparse import Namespace

        reset_environment_manager()
        with patch("src.cli.get_environment_manager") as mock_get_manager:
            mock_instance = MagicMock()
            mock_instance.validate_environment.return_value = False
            mock_instance.get_current_environment.return_value = MagicMock(value="mock")
            mock_get_manager.return_value = mock_instance

            args = Namespace(env_action="validate", environment=None)

            result = cmd_environment(args)
            assert result == 1

    def test_environment_list(self):
        """Test listing environments"""
        from src.cli import cmd_environment
        from argparse import Namespace
        from src.environment_manager import Environment

        with patch("src.cli.EnvironmentManager") as mock_manager:
            mock_instance = MagicMock()
            mock_instance.get_current_environment.return_value = Environment.MOCK
            mock_manager.return_value = mock_instance

            args = Namespace(env_action="list", environment=None)

            result = cmd_environment(args)
            assert result == 0


class TestCmdServices:
    """Tests for cmd_services function"""

    def test_health_all_healthy(self):
        """Test service health check - all healthy"""
        from src.cli import cmd_services
        from argparse import Namespace

        with patch("src.cli.ServiceManager") as mock_manager:
            mock_instance = MagicMock()
            mock_instance.health_check_all.return_value = {
                "cache": True,
                "message": True,
                "database": True,
                "api": True,
            }
            mock_manager.return_value = mock_instance

            args = Namespace(service_action="health", service_type=None)

            result = cmd_services(args)
            assert result == 0

    def test_health_some_unhealthy(self):
        """Test service health check - some unhealthy"""
        from src.cli import cmd_services
        from argparse import Namespace

        with patch("src.cli.ServiceManager") as mock_manager:
            mock_instance = MagicMock()
            mock_instance.health_check_all.return_value = {
                "cache": True,
                "message": False,
                "database": True,
                "api": True,
            }
            mock_manager.return_value = mock_instance

            args = Namespace(service_action="health", service_type=None)

            result = cmd_services(args)
            assert result == 1

    def test_info_command(self):
        """Test service info command"""
        from src.cli import cmd_services
        from argparse import Namespace

        with patch("src.cli.ServiceManager") as mock_manager:
            mock_instance = MagicMock()
            mock_client = MagicMock()
            mock_client.get_connection_info.return_value = {
                "type": "mock",
                "host": "localhost",
            }
            mock_instance.get_cache_client.return_value = mock_client
            mock_instance.get_message_client.return_value = mock_client
            mock_instance.get_database_client.return_value = mock_client
            mock_instance.get_api_client.return_value = mock_client
            mock_manager.return_value = mock_instance

            args = Namespace(service_action="info", service_type=None)

            result = cmd_services(args)
            assert result == 0

    def test_test_cache(self):
        """Test cache operations test"""
        from src.cli import cmd_services
        from argparse import Namespace

        with patch("src.cli.ServiceManager") as mock_manager:
            mock_instance = MagicMock()
            mock_cache = MagicMock()
            mock_cache.set.return_value = True
            mock_cache.get.return_value = "test_value"
            mock_cache.exists.return_value = True
            mock_cache.delete.return_value = True
            mock_instance.get_cache_client.return_value = mock_cache
            mock_manager.return_value = mock_instance

            args = Namespace(service_action="test", service_type="cache")

            result = cmd_services(args)
            assert result == 0


class TestCmdLocal:
    """Tests for cmd_local function"""

    def test_local_status(self):
        """Test local environment status"""
        from src.cli import cmd_local
        from argparse import Namespace

        with patch("src.cli.ServiceManager") as mock_manager:
            mock_instance = MagicMock()
            mock_instance.health_check_all.return_value = {
                "cache": True,
                "message": True,
                "database": True,
                "api": True,
            }
            mock_manager.return_value = mock_instance

            with patch.dict(
                "sys.modules", {"scripts.start_local_environment": MagicMock()}
            ):
                import sys

                sys.modules[
                    "scripts.start_local_environment"
                ].LocalEnvironmentManager = MagicMock

                args = Namespace(local_action="status")
                result = cmd_local(args)
                assert result == 0


class TestCmdVersion:
    """Tests for cmd_version function"""

    def test_version_output(self):
        """Test version command output"""
        from src.cli import cmd_version
        from argparse import Namespace

        args = Namespace()
        result = cmd_version(args)
        assert result == 0


class TestMainFunction:
    """Tests for main function argument parsing"""

    def test_help_flag(self):
        """Test --help flag"""
        from src.cli import main
        import sys

        with patch.object(sys, "argv", ["netskope-sdet", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

    def test_version_command(self):
        """Test version subcommand"""
        from src.cli import main
        import sys

        with patch.object(sys, "argv", ["netskope-sdet", "version"]):
            result = main()
            assert result == 0

    def test_env_command(self):
        """Test env subcommand"""
        from src.cli import main
        import sys

        with patch.object(sys, "argv", ["netskope-sdet", "env", "list"]):
            with patch("src.cli.EnvironmentManager") as mock_manager:
                mock_instance = MagicMock()
                mock_instance.get_current_environment.return_value = MagicMock(
                    value="mock"
                )
                mock_manager.return_value = mock_instance
                result = main()
                assert result == 0

    def test_services_health_command(self):
        """Test services health subcommand"""
        from src.cli import main
        import sys

        with patch.object(sys, "argv", ["netskope-sdet", "services", "health"]):
            with patch("src.cli.ServiceManager") as mock_manager:
                mock_instance = MagicMock()
                mock_instance.health_check_all.return_value = {"cache": True}
                mock_manager.return_value = mock_instance
                result = main()
                assert result == 0

    def test_invalid_command(self):
        """Test invalid command"""
        from src.cli import main
        import sys

        with patch.object(sys, "argv", ["netskope-sdet", "invalid_command"]):
            with patch("src.cli.argparse.ArgumentParser") as mock_parser:
                mock_instance = MagicMock()
                mock_instance.parse_args.return_value = MagicMock(command="invalid")
                mock_parser.return_value = mock_instance
                result = main()
                assert result == 1


class TestArgumentParsing:
    """Tests for argument parsing"""

    def test_environment_parser(self):
        """Test environment parser configuration"""
        from src.cli import main
        import sys
        from io import StringIO

        with patch.object(sys, "argv", ["netskope-sdet", "env", "--help"]):
            with pytest.raises(SystemExit):
                main()

    def test_service_parser(self):
        """Test service parser configuration"""
        from src.cli import main
        import sys

        with patch.object(sys, "argv", ["netskope-sdet", "services", "--help"]):
            with pytest.raises(SystemExit):
                main()

    def test_test_parser(self):
        """Test test parser configuration"""
        from src.cli import main
        import sys

        with patch.object(sys, "argv", ["netskope-sdet", "test", "--help"]):
            with pytest.raises(SystemExit):
                main()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
