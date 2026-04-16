#!/usr/bin/env python3
"""
Day-1 Framework - Command Line Interface

Main CLI entry point for the Day-1 Framework.
Provides unified access to all framework functionality.
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import time
import json
from argparse import Namespace
from pathlib import Path
from typing import Optional

from .environment_manager import (
    EnvironmentManager,
    Environment,
    get_environment_manager,
)
from .service_manager import ServiceManager


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def cmd_environment(args: Namespace) -> int:
    """Handle environment commands"""
    env_manager = get_environment_manager()

    if args.env_action == "detect":
        env = env_manager.detect_environment()
        print(f"Detected environment: {env.value}")

    elif args.env_action == "info":
        target_env = None
        if args.environment:
            try:
                target_env = Environment(args.environment)
            except ValueError:
                print(f"Invalid environment: {args.environment}")
                return 1

        info = env_manager.get_environment_info(target_env)

        print(f"Environment: {info['environment']}")
        print(f"Name: {info['name']}")
        print(f"Valid: {'' if info['valid'] else ''}")
        print("\nServices:")
        for service, config in info["services"].items():
            print(f"  {service}: {config['host']}:{config['port']}")

    elif args.env_action == "validate":
        target_env = None
        if args.environment:
            try:
                target_env = Environment(args.environment)
            except ValueError:
                print(f"Invalid environment: {args.environment}")
                return 1

        is_valid = env_manager.validate_environment(target_env)
        env_name = (
            target_env.value
            if target_env
            else env_manager.get_current_environment().value
        )

        if is_valid:
            print(f" {env_name} environment is valid")
            return 0
        else:
            print(f" {env_name} environment validation failed")
            return 1

    elif args.env_action == "set":
        if not args.environment:
            print("Error: Environment name required for 'set' action")
            return 1

        try:
            target_env = Environment(args.environment)
            env_manager.set_environment(target_env)
            print(f" Environment set to: {target_env.value}")
        except ValueError:
            print(f"Invalid environment: {args.environment}")
            return 1

    elif args.env_action == "list":
        current_env = env_manager.get_current_environment()
        print("Available environments:")
        for env in Environment:
            marker = " (*)" if env == current_env else "    "
            print(f"{marker} {env.value}")

    return 0


def cmd_services(args: Namespace) -> int:
    """Handle service commands"""
    service_manager = ServiceManager()

    if args.service_action == "health":
        print("Checking service health...")
        health_results = service_manager.health_check_all()

        all_healthy = True
        for service, is_healthy in health_results.items():
            status = " Healthy" if is_healthy else " Unhealthy"
            print(f"  {service}: {status}")
            if not is_healthy:
                all_healthy = False

        return 0 if all_healthy else 1

    elif args.service_action == "info":
        print("Service connection information:")

        clients = {
            "cache": service_manager.get_cache_client(),
            "message": service_manager.get_message_client(),
            "database": service_manager.get_database_client(),
            "api": service_manager.get_api_client(),
        }

        for service_name, client in clients.items():
            info = client.get_connection_info()
            print(f"  {service_name}:")
            for key, value in info.items():
                print(f"    {key}: {value}")

    elif args.service_action == "test":
        service_type = args.service_type or "all"

        if service_type in ["cache", "all"]:
            print("Testing cache operations...")
            cache = service_manager.get_cache_client()

            cache.set("test_key", "test_value")
            value = cache.get("test_key")
            exists = cache.exists("test_key")
            deleted = cache.delete("test_key")

            print(f"  SET/GET: {value}")
            print(f"  EXISTS: {exists}")
            print(f"  DELETE: {deleted}")

        if service_type in ["message", "all"]:
            print("Testing message operations...")
            message_client = service_manager.get_message_client()

            message_client.create_topic("test_topic")
            message_client.publish("test_topic", {"message": "Hello, World!"})

            messages = message_client.consume("test_topic")
            print(f"  Published and consumed {len(messages)} messages")

        if service_type in ["database", "all"]:
            print("Testing database operations...")
            db = service_manager.get_database_client()

            doc_id = db.insert_one("test_collection", {"name": "test", "value": 123})
            doc = db.find_one("test_collection", {"name": "test"})
            count = db.count_documents("test_collection")

            print(f"  INSERT: {doc_id}")
            print(f"  FIND: {doc is not None}")
            print(f"  COUNT: {count}")

        if service_type in ["api", "all"]:
            print("Testing API operations...")
            api = service_manager.get_api_client()

            api.authenticate({"api_key": "test-key"})

            try:
                events = api.get("/api/v2/events")
                print(f"  GET events: Success")
            except Exception as e:
                print(f"  GET events: Failed (expected in mock mode): {e}")

    return 0


def cmd_local(args: Namespace) -> int:
    """Handle local environment commands"""
    try:
        from scripts.start_local_environment import LocalEnvironmentManager

        env_manager = LocalEnvironmentManager()

        if args.local_action == "start":
            success = env_manager.start_environment()
            return 0 if success else 1

        elif args.local_action == "stop":
            success = env_manager.stop_environment()
            return 0 if success else 1

        elif args.local_action == "restart":
            success = env_manager.restart_environment()
            return 0 if success else 1

        elif args.local_action == "status":
            service_manager = ServiceManager()
            health_results = service_manager.health_check_all()

            print(" Local Environment Status:")
            for service, healthy in health_results.items():
                status = " Healthy" if healthy else " Unhealthy"
                print(f"   {service}: {status}")

            all_healthy = all(health_results.values())
            print(
                f"\n Overall: {' All services healthy' if all_healthy else ' Some services unhealthy'}"
            )

            return 0 if all_healthy else 1

    except ImportError as e:
        print(f"Error: Local environment manager not available: {e}")
        return 1


def cmd_staging(args: Namespace) -> int:
    """Handle staging environment commands"""
    try:
        from scripts.deploy_staging import StagingDeployment

        deployment = StagingDeployment(
            kubeconfig=args.kubeconfig, namespace=args.namespace or "netskope-staging"
        )

        if args.staging_action == "deploy":
            print(" Deploying Staging Environment (E4)...")
            print("  This is a production-like environment with enhanced security")
            success = deployment.deploy_staging_environment()
            if success:
                deployment.print_access_info()
            return 0 if success else 1

        elif args.staging_action == "undeploy":
            print(" Removing Staging Environment (E4)...")
            success = deployment.undeploy_staging_environment()
            return 0 if success else 1

        elif args.staging_action == "status":
            status = deployment.get_environment_status()
            print(f"\n Staging Environment Status:")
            print(f"Namespace: {status['namespace']}")
            print(f"Environment: {status['environment']}")
            print(f"Overall Health: {status['overall_health']}")
            print(f"Services: {len(status['services'])}")
            print(f"Pods: {len(status['pods'])}")
            print(f"Storage Volumes: {len(status['storage'])}")

            for name, info in status["pods"].items():
                status_icon = "" if info["ready"] else ""
                print(f"  {status_icon} {name}: {info['phase']}")

            return 0 if status["overall_health"] == "healthy" else 1

        elif args.staging_action == "health-check":
            success = deployment.run_health_checks()
            return 0 if success else 1

        elif args.staging_action == "logs":
            # Show logs for staging environment
            import subprocess

            if args.service:
                # Show logs for specific service
                cmd = [
                    "kubectl",
                    "logs",
                    "-n",
                    args.namespace or "netskope-staging",
                    "-l",
                    f"app={args.service}",
                    "--tail=100",
                ]
                if args.follow:
                    cmd.append("-f")
            else:
                # Show logs for all staging services
                cmd = [
                    "kubectl",
                    "logs",
                    "-n",
                    args.namespace or "netskope-staging",
                    "-l",
                    "environment=staging",
                    "--tail=100",
                ]
                if args.follow:
                    cmd.append("-f")

            try:
                subprocess.run(cmd)
                return 0
            except subprocess.CalledProcessError:
                print(" Failed to retrieve logs")
                return 1

        elif args.staging_action == "test":
            # Run staging tests
            test_type = args.test_type or "integration"

            print(f" Running {test_type} tests in staging environment...")
            print(
                "  Staging tests may take longer due to enhanced security and HA setup"
            )

            # Build kubectl command to run test job
            job_name = f"staging-test-{test_type}-{int(time.time())}"

            cmd = [
                "kubectl",
                "run",
                job_name,
                "-n",
                args.namespace or "netskope-staging",
                "--image=netskope-sdet:staging",
                "--rm",
                "-i",
                "--restart=Never",
                "--",
                "/app/run_staging_tests.sh",
                test_type,
            ]

            try:
                subprocess.run(cmd, check=True)
                print(f" Staging tests completed")
                return 0
            except subprocess.CalledProcessError:
                print(" Failed to run staging tests")
                return 1

    except ImportError as e:
        print(f"Error: Staging deployment manager not available: {e}")
        return 1


def cmd_production(args: Namespace) -> int:
    """Handle production environment commands (READ-ONLY)"""
    try:
        from scripts.deploy_production import ProductionMonitoring

        monitor = ProductionMonitoring(config_file=args.config)

        if args.production_action == "health-check":
            print(" Running production health check...")
            print("  This is READ-ONLY monitoring - no changes will be made")

            if not monitor.check_prerequisites():
                print(" Prerequisites not met")
                return 1

            health_data = monitor.run_comprehensive_health_check()
            overall_status = health_data.get("overall_health", {}).get(
                "status", "unknown"
            )
            return 0 if overall_status == "healthy" else 1

        elif args.production_action == "metrics":
            print(" Collecting production metrics...")

            if not monitor.check_prerequisites():
                print(" Prerequisites not met")
                return 1

            metrics = monitor.get_production_metrics()
            print(json.dumps(metrics, indent=2))
            return 0

        elif args.production_action == "report":
            print(" Generating production health report...")

            if not monitor.check_prerequisites():
                print(" Prerequisites not met")
                return 1

            output_file = (
                args.output
                or f"reports/production_health_report_{int(time.time())}.json"
            )
            report = monitor.generate_health_report(output_file)

            if not args.output:
                print(report)

            return 0

        elif args.production_action == "monitor":
            print(" Starting continuous production monitoring...")
            print("  This is READ-ONLY monitoring - no changes will be made")

            if not monitor.check_prerequisites():
                print(" Prerequisites not met")
                return 1

            try:
                monitor.monitor_continuous(
                    interval=args.interval or 300, duration=args.duration or 3600
                )
                return 0
            except KeyboardInterrupt:
                print("\n Monitoring stopped by user")
                return 0
            except Exception as e:
                print(f" Monitoring error: {e}")
                return 1

        elif args.production_action == "status":
            print(" Getting production environment status...")

            if not monitor.check_prerequisites():
                print(" Prerequisites not met")
                return 1

            health_data = monitor.run_comprehensive_health_check()

            print(f"\n Production Environment Status:")
            print(f"Environment: {health_data['environment']}")
            print(
                f"Mode: {'READ-ONLY' if health_data['read_only_mode'] else 'UNKNOWN'}"
            )
            print(f"Overall Health: {health_data['overall_health']['status']}")
            print(
                f"Health Score: {health_data['overall_health']['health_percentage']:.1f}%"
            )
            print(
                f"Services: {health_data['overall_health']['healthy_services']}/{health_data['overall_health']['total_services']} healthy"
            )

            print(f"\n Service Status:")
            for service, data in health_data["services"].items():
                status_icon = "" if data["status"] == "healthy" else ""
                print(f"  {status_icon} {service}: {data['status']}")

            print(f"\n Monitoring Services:")
            for service, data in health_data.get("monitoring", {}).items():
                status_icon = "" if data.get("status") == "healthy" else ""
                print(f"  {status_icon} {service}: {data.get('status', 'unknown')}")

            return 0 if health_data["overall_health"]["status"] == "healthy" else 1

    except ImportError as e:
        print(f"Error: Production monitoring not available: {e}")
        return 1


def cmd_integration(args: Namespace) -> int:
    """Handle integration environment commands"""
    try:
        from scripts.deploy_integration import IntegrationDeployment

        deployment = IntegrationDeployment(
            kubeconfig=args.kubeconfig,
            namespace=args.namespace or "netskope-integration",
        )

        if args.integration_action == "deploy":
            print(" Deploying Integration Environment (E3)...")
            success = deployment.deploy_integration_environment()
            if success:
                deployment.print_access_info()
            return 0 if success else 1

        elif args.integration_action == "undeploy":
            print(" Removing Integration Environment (E3)...")
            success = deployment.undeploy_integration_environment()
            return 0 if success else 1

        elif args.integration_action == "status":
            status = deployment.get_environment_status()
            print(f"\n Integration Environment Status:")
            print(f"Namespace: {status['namespace']}")
            print(f"Overall Health: {status['overall_health']}")
            print(f"Services: {len(status['services'])}")
            print(f"Pods: {len(status['pods'])}")

            for name, info in status["pods"].items():
                status_icon = "" if info["ready"] else ""
                print(f"  {status_icon} {name}: {info['phase']}")

            return 0 if status["overall_health"] == "healthy" else 1

        elif args.integration_action == "health-check":
            success = deployment.run_health_checks()
            return 0 if success else 1

        elif args.integration_action == "logs":
            # Show logs for integration environment
            import subprocess

            if args.service:
                # Show logs for specific service
                cmd = [
                    "kubectl",
                    "logs",
                    "-n",
                    args.namespace or "netskope-integration",
                    "-l",
                    f"app={args.service}",
                    "--tail=100",
                ]
                if args.follow:
                    cmd.append("-f")
            else:
                # Show logs for test runner
                cmd = [
                    "kubectl",
                    "logs",
                    "-n",
                    args.namespace or "netskope-integration",
                    "job/test-runner-integration",
                    "--tail=100",
                ]
                if args.follow:
                    cmd.append("-f")

            try:
                subprocess.run(cmd)
                return 0
            except subprocess.CalledProcessError:
                print(" Failed to retrieve logs")
                return 1

        elif args.integration_action == "test":
            # Run integration tests
            test_type = args.test_type or "integration"

            # Build kubectl command to run test job
            job_name = f"test-runner-{test_type}-{int(time.time())}"

            cmd = [
                "kubectl",
                "create",
                "job",
                "-n",
                args.namespace or "netskope-integration",
                job_name,
                "--from=cronjob/scheduled-integration-tests",
            ]

            try:
                subprocess.run(cmd, check=True)
                print(f" Started test job: {job_name}")
                print(
                    f" Monitor with: kubectl logs -n {args.namespace or 'netskope-integration'} job/{job_name} -f"
                )
                return 0
            except subprocess.CalledProcessError:
                print(" Failed to start test job")
                return 1

    except ImportError as e:
        print(f"Error: Integration deployment manager not available: {e}")
        return 1


def cmd_test(args: Namespace) -> int:
    """Handle test commands"""
    import subprocess

    # Build pytest command
    cmd = ["python", "-m", "pytest"]

    if args.test_type:
        if args.test_type == "unit":
            cmd.append("tests/unit/")
        elif args.test_type == "integration":
            cmd.append("tests/integration/")
        elif args.test_type == "e2e":
            cmd.append("tests/e2e/")
        elif args.test_type == "security":
            cmd.append("tests/security/")
        elif args.test_type == "performance":
            cmd.append("tests/performance/")
        else:
            cmd.append("tests/")
    else:
        cmd.append("tests/")

    # Add common options
    cmd.extend(["-v"])

    if args.html_report:
        cmd.extend(["--html=reports/test_report.html", "--self-contained-html"])

    if args.coverage:
        cmd.extend(["--cov=src", "--cov-report=html"])

    if args.markers:
        cmd.extend(["-m", args.markers])

    # Set environment if specified
    env = {}
    if args.environment:
        env["TESTING_MODE"] = args.environment

    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, env={**os.environ, **env})
        return result.returncode
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def cmd_version(args: Namespace) -> int:
    """Show version information"""
    print("Day-1 Framework v1.0.0")
    print("Multi-environment cybersecurity API testing framework")
    print()
    print("Environments:")
    print("   Mock Environment (E1) - Complete")
    print("   Local Environment (E2) - Complete")
    print("   Integration Environment (E3) - Complete")
    print("   Staging Environment (E4) - Complete")
    print("   Production Environment (E5) - Complete")
    print()
    print("Components:")
    print("   Environment Manager")
    print("   Service Abstraction Layer")
    print("   Docker Compose Local Environment")
    print("   Mock Service Implementations")
    print("   Real Service Implementations (Redis, Kafka, MongoDB, API)")
    print("   Kubernetes Integration Environment")
    print("   Kubernetes Staging Environment (HA)")
    print("   Production Monitoring (Read-Only)")
    print("   CI/CD Pipeline (GitHub Actions + Jenkins)")
    print("   Security Testing Framework (SAST, DAST, SCA, Secrets)")
    print()
    print("CI/CD Integration:")
    print("   GitHub Actions Workflows")
    print("   Jenkins Pipeline")
    print("   Security Scanning (Bandit, Semgrep, CodeQL)")
    print("   Dependency Scanning (Safety, pip-audit)")
    print("   Secret Scanning (TruffleHog, Gitleaks)")
    print("   Automated Deployment")
    print()
    print("Overall Framework Completion: 100% ")
    return 0


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Day-1 Framework - Multi-environment cybersecurity API testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  netskope-sdet env detect                    # Detect current environment
  netskope-sdet env info local               # Show local environment info
  netskope-sdet services health              # Check service health
  netskope-sdet local start                  # Start local environment
  netskope-sdet integration deploy           # Deploy integration environment (K8s)
  netskope-sdet integration status           # Check integration environment status
  netskope-sdet integration test             # Run tests in integration environment
  netskope-sdet staging deploy               # Deploy staging environment (K8s HA)
  netskope-sdet staging status               # Check staging environment status
  netskope-sdet staging test --test-type load # Run load tests in staging environment
  netskope-sdet production health-check      # Check production health (read-only)
  netskope-sdet production report --output report.json # Generate production health report
  netskope-sdet production monitor --interval 300 # Continuous production monitoring
  netskope-sdet test unit --html-report      # Run unit tests with HTML report
  netskope-sdet test integration -e local    # Run integration tests in local env
        """,
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Environment commands
    env_parser = subparsers.add_parser("env", help="Environment management")
    env_parser.add_argument(
        "env_action",
        choices=["detect", "info", "validate", "set", "list"],
        help="Environment action to perform",
    )
    env_parser.add_argument(
        "environment",
        nargs="?",
        choices=["mock", "local", "integration", "staging", "production"],
        help="Target environment",
    )

    # Service commands
    service_parser = subparsers.add_parser("services", help="Service management")
    service_parser.add_argument(
        "service_action",
        choices=["health", "info", "test"],
        help="Service action to perform",
    )
    service_parser.add_argument(
        "service_type",
        nargs="?",
        choices=["cache", "message", "database", "api", "all"],
        help="Service type to test (for test action)",
    )

    # Local environment commands
    local_parser = subparsers.add_parser("local", help="Local environment management")
    local_parser.add_argument(
        "local_action",
        choices=["start", "stop", "restart", "status"],
        help="Local environment action",
    )

    # Integration environment commands
    integration_parser = subparsers.add_parser(
        "integration", help="Integration environment management (Kubernetes)"
    )
    integration_parser.add_argument(
        "integration_action",
        choices=["deploy", "undeploy", "status", "health-check", "logs", "test"],
        help="Integration environment action",
    )
    integration_parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    integration_parser.add_argument(
        "--namespace", default="netskope-integration", help="Kubernetes namespace"
    )
    integration_parser.add_argument(
        "--service", help="Service name for logs (redis, kafka, mongodb, etc.)"
    )
    integration_parser.add_argument(
        "--follow", "-f", action="store_true", help="Follow logs"
    )
    integration_parser.add_argument(
        "--test-type",
        choices=["integration", "e2e", "security", "performance", "smoke"],
        help="Type of tests to run",
    )

    # Staging environment commands
    staging_parser = subparsers.add_parser(
        "staging", help="Staging environment management (Kubernetes HA)"
    )
    staging_parser.add_argument(
        "staging_action",
        choices=["deploy", "undeploy", "status", "health-check", "logs", "test"],
        help="Staging environment action",
    )
    staging_parser.add_argument("--kubeconfig", help="Path to kubeconfig file")
    staging_parser.add_argument(
        "--namespace", default="netskope-staging", help="Kubernetes namespace"
    )
    staging_parser.add_argument("--service", help="Service name for logs")
    staging_parser.add_argument(
        "--follow", "-f", action="store_true", help="Follow logs"
    )
    staging_parser.add_argument(
        "--test-type",
        choices=["integration", "e2e", "security", "performance", "load"],
        help="Type of tests to run",
    )
    staging_parser.add_argument(
        "--confirm", action="store_true", help="Skip confirmation prompts"
    )

    # Production environment commands (READ-ONLY)
    production_parser = subparsers.add_parser(
        "production", help="Production environment monitoring (READ-ONLY)"
    )
    production_parser.add_argument(
        "production_action",
        choices=["health-check", "metrics", "report", "monitor", "status"],
        help="Production monitoring action",
    )
    production_parser.add_argument(
        "--config",
        default="config/production.yaml",
        help="Production configuration file",
    )
    production_parser.add_argument("--output", help="Output file for reports")
    production_parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Monitoring interval in seconds (for continuous monitoring)",
    )
    production_parser.add_argument(
        "--duration",
        type=int,
        default=3600,
        help="Monitoring duration in seconds (for continuous monitoring)",
    )

    # Test commands
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument(
        "test_type",
        nargs="?",
        choices=["unit", "integration", "e2e", "security", "performance"],
        help="Type of tests to run",
    )
    test_parser.add_argument(
        "-e",
        "--environment",
        choices=["mock", "local", "integration", "staging", "production"],
        help="Environment to run tests in",
    )
    test_parser.add_argument(
        "--html-report", action="store_true", help="Generate HTML test report"
    )
    test_parser.add_argument(
        "--coverage", action="store_true", help="Generate coverage report"
    )
    test_parser.add_argument("-m", "--markers", help="Pytest markers to filter tests")

    # Version command
    version_parser = subparsers.add_parser("version", help="Show version information")

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Handle commands
    if args.command == "env":
        return cmd_environment(args)
    elif args.command == "services":
        return cmd_services(args)
    elif args.command == "local":
        return cmd_local(args)
    elif args.command == "integration":
        return cmd_integration(args)
    elif args.command == "staging":
        return cmd_staging(args)
    elif args.command == "production":
        return cmd_production(args)
    elif args.command == "test":
        return cmd_test(args)
    elif args.command == "version":
        return cmd_version(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    import os

    sys.exit(main())
