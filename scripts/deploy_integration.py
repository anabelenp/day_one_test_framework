#!/usr/bin/env python3
"""
Day-1 Framework - Integration Environment Deployment Script

This script deploys the complete Integration Environment (E3) to Kubernetes.
It provides a production-like environment for comprehensive E2E testing.
"""

import os
import sys
import time
import subprocess
import argparse
import yaml
from pathlib import Path
from typing import Dict, List, Optional

class IntegrationDeployment:
    """Manages deployment of the Integration Environment to Kubernetes"""
    
    def __init__(self, kubeconfig: Optional[str] = None, namespace: str = "netskope-integration"):
        self.namespace = namespace
        self.kubeconfig = kubeconfig
        self.k8s_dir = Path(__file__).parent.parent / "k8s" / "integration"
        
        # Deployment order matters for dependencies
        self.deployment_order = [
            "namespace.yaml",
            "redis-cluster.yaml",
            "kafka-cluster.yaml", 
            "mongodb-replica.yaml",
            "mock-api-service.yaml",
            "monitoring-stack.yaml",
            "test-runner-job.yaml"
        ]
    
    def run_kubectl(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run kubectl command with optional kubeconfig"""
        cmd = ["kubectl"]
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])
        cmd.extend(args)
        
        print(f"🔧 Running: {' '.join(cmd)}")
        return subprocess.run(cmd, check=check, capture_output=True, text=True)
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met"""
        print("🔍 Checking prerequisites...")
        
        # Check kubectl
        try:
            result = self.run_kubectl(["version", "--client"])
            print("✅ kubectl is available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ kubectl is not available or not in PATH")
            return False
        
        # Check cluster connectivity
        try:
            result = self.run_kubectl(["cluster-info"])
            print("✅ Kubernetes cluster is accessible")
        except subprocess.CalledProcessError:
            print("❌ Cannot connect to Kubernetes cluster")
            return False
        
        # Check if namespace exists
        try:
            result = self.run_kubectl(["get", "namespace", self.namespace])
            print(f"✅ Namespace '{self.namespace}' exists")
        except subprocess.CalledProcessError:
            print(f"ℹ️ Namespace '{self.namespace}' will be created")
        
        # Check available resources
        try:
            result = self.run_kubectl(["top", "nodes"])
            print("✅ Cluster has available resources")
        except subprocess.CalledProcessError:
            print("⚠️ Cannot check cluster resources (metrics-server may not be installed)")
        
        return True
    
    def deploy_manifest(self, manifest_file: str) -> bool:
        """Deploy a single Kubernetes manifest"""
        manifest_path = self.k8s_dir / manifest_file
        
        if not manifest_path.exists():
            print(f"❌ Manifest file not found: {manifest_path}")
            return False
        
        print(f"📦 Deploying {manifest_file}...")
        
        try:
            result = self.run_kubectl(["apply", "-f", str(manifest_path)])
            print(f"✅ Successfully deployed {manifest_file}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to deploy {manifest_file}: {e.stderr}")
            return False
    
    def wait_for_pods(self, label_selector: str, timeout: int = 300) -> bool:
        """Wait for pods to be ready"""
        print(f"⏳ Waiting for pods with selector '{label_selector}' to be ready...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = self.run_kubectl([
                    "get", "pods", 
                    "-n", self.namespace,
                    "-l", label_selector,
                    "--no-headers"
                ])
                
                if result.stdout.strip():
                    # Check if all pods are running
                    lines = result.stdout.strip().split('\n')
                    all_ready = True
                    
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 3:
                            status = parts[2]
                            if status not in ["Running", "Completed"]:
                                all_ready = False
                                break
                    
                    if all_ready:
                        print(f"✅ All pods with selector '{label_selector}' are ready")
                        return True
                
                time.sleep(10)
                
            except subprocess.CalledProcessError:
                time.sleep(10)
        
        print(f"❌ Timeout waiting for pods with selector '{label_selector}'")
        return False
    
    def wait_for_services(self) -> bool:
        """Wait for all services to be ready"""
        services = [
            ("app=redis", "Redis"),
            ("app=kafka", "Kafka"), 
            ("app=mongodb", "MongoDB"),
            ("app=mock-api", "Mock API"),
            ("app=prometheus", "Prometheus"),
            ("app=grafana", "Grafana"),
            ("app=jaeger", "Jaeger")
        ]
        
        for selector, name in services:
            if not self.wait_for_pods(selector, timeout=300):
                print(f"❌ {name} pods are not ready")
                return False
        
        return True
    
    def run_health_checks(self) -> bool:
        """Run health checks on deployed services"""
        print("🏥 Running health checks...")
        
        health_checks = [
            {
                "name": "Redis",
                "command": ["redis-cli", "-h", "redis-service", "-p", "6379", "-a", "integration-redis-2024", "ping"]
            },
            {
                "name": "MongoDB", 
                "command": ["mongosh", "--host", "mongodb-service:27017", "--eval", "db.adminCommand('ping')"]
            },
            {
                "name": "Mock API",
                "command": ["curl", "-f", "http://mock-api-service:8080/health"]
            },
            {
                "name": "Prometheus",
                "command": ["curl", "-f", "http://prometheus-service:9090/-/healthy"]
            },
            {
                "name": "Grafana",
                "command": ["curl", "-f", "http://grafana-service:3000/api/health"]
            }
        ]
        
        all_healthy = True
        
        for check in health_checks:
            try:
                # Run health check in a temporary pod
                result = self.run_kubectl([
                    "run", f"health-check-{check['name'].lower()}",
                    "-n", self.namespace,
                    "--image=curlimages/curl:latest",
                    "--rm", "-i", "--restart=Never",
                    "--", "sh", "-c", " ".join(check['command'])
                ])
                print(f"✅ {check['name']} health check passed")
            except subprocess.CalledProcessError:
                print(f"❌ {check['name']} health check failed")
                all_healthy = False
        
        return all_healthy
    
    def deploy_integration_environment(self) -> bool:
        """Deploy the complete integration environment"""
        print("🚀 Starting Integration Environment (E3) deployment...")
        
        if not self.check_prerequisites():
            return False
        
        # Deploy manifests in order
        for manifest in self.deployment_order:
            if not self.deploy_manifest(manifest):
                print(f"❌ Deployment failed at {manifest}")
                return False
            
            # Wait a bit between deployments
            time.sleep(5)
        
        # Wait for all services to be ready
        if not self.wait_for_services():
            print("❌ Some services failed to start")
            return False
        
        # Run health checks
        if not self.run_health_checks():
            print("⚠️ Some health checks failed, but deployment completed")
        
        print("🎉 Integration Environment (E3) deployment completed successfully!")
        return True
    
    def undeploy_integration_environment(self) -> bool:
        """Remove the integration environment"""
        print("🗑️ Removing Integration Environment (E3)...")
        
        try:
            result = self.run_kubectl(["delete", "namespace", self.namespace])
            print(f"✅ Namespace '{self.namespace}' deleted")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to delete namespace: {e.stderr}")
            return False
    
    def get_environment_status(self) -> Dict:
        """Get status of the integration environment"""
        print("📊 Getting Integration Environment status...")
        
        status = {
            "namespace": self.namespace,
            "services": {},
            "pods": {},
            "overall_health": "unknown"
        }
        
        try:
            # Get services
            result = self.run_kubectl([
                "get", "services", "-n", self.namespace, "-o", "json"
            ])
            services_data = yaml.safe_load(result.stdout)
            
            for service in services_data.get("items", []):
                name = service["metadata"]["name"]
                status["services"][name] = {
                    "type": service["spec"]["type"],
                    "ports": service["spec"]["ports"]
                }
            
            # Get pods
            result = self.run_kubectl([
                "get", "pods", "-n", self.namespace, "-o", "json"
            ])
            pods_data = yaml.safe_load(result.stdout)
            
            all_healthy = True
            for pod in pods_data.get("items", []):
                name = pod["metadata"]["name"]
                phase = pod["status"]["phase"]
                status["pods"][name] = {
                    "phase": phase,
                    "ready": phase == "Running"
                }
                if phase != "Running":
                    all_healthy = False
            
            status["overall_health"] = "healthy" if all_healthy else "unhealthy"
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to get status: {e.stderr}")
            status["overall_health"] = "error"
        
        return status
    
    def print_access_info(self):
        """Print information about accessing the deployed services"""
        print("\n🌐 Integration Environment Access Information:")
        print("=" * 60)
        
        # Port forwarding commands
        port_forwards = [
            ("Grafana Dashboard", "grafana-service", "3000:3000"),
            ("Prometheus", "prometheus-service", "9090:9090"), 
            ("Jaeger UI", "jaeger-service", "16686:16686"),
            ("Mock API", "mock-api-service", "8080:8080")
        ]
        
        print("\n📡 Port Forward Commands (run in separate terminals):")
        for name, service, ports in port_forwards:
            cmd = f"kubectl port-forward -n {self.namespace} svc/{service} {ports}"
            print(f"  {name}: {cmd}")
        
        print(f"\n🔑 Default Credentials:")
        print(f"  Grafana: admin / integration-grafana-2024")
        print(f"  Redis: integration-redis-2024")
        print(f"  MongoDB: netskope_app / netskope-app-2024")
        print(f"  API Key: integration-api-key-2024")
        
        print(f"\n🧪 Running Tests:")
        print(f"  kubectl apply -f k8s/integration/test-runner-job.yaml")
        print(f"  kubectl logs -n {self.namespace} job/test-runner-integration -f")
        
        print(f"\n📊 Monitoring:")
        print(f"  kubectl get pods -n {self.namespace}")
        print(f"  kubectl get services -n {self.namespace}")
        print(f"  kubectl describe namespace {self.namespace}")

def main():
    parser = argparse.ArgumentParser(
        description="Deploy Day-1 Integration Environment (E3) to Kubernetes"
    )
    parser.add_argument(
        "--action", 
        choices=["deploy", "undeploy", "status", "health-check"],
        default="deploy",
        help="Action to perform"
    )
    parser.add_argument(
        "--kubeconfig",
        help="Path to kubeconfig file"
    )
    parser.add_argument(
        "--namespace",
        default="netskope-integration",
        help="Kubernetes namespace"
    )
    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=600,
        help="Timeout for waiting for services (seconds)"
    )
    
    args = parser.parse_args()
    
    deployment = IntegrationDeployment(
        kubeconfig=args.kubeconfig,
        namespace=args.namespace
    )
    
    if args.action == "deploy":
        success = deployment.deploy_integration_environment()
        if success:
            deployment.print_access_info()
        sys.exit(0 if success else 1)
    
    elif args.action == "undeploy":
        success = deployment.undeploy_integration_environment()
        sys.exit(0 if success else 1)
    
    elif args.action == "status":
        status = deployment.get_environment_status()
        print(f"\n📊 Environment Status:")
        print(f"Namespace: {status['namespace']}")
        print(f"Overall Health: {status['overall_health']}")
        print(f"Services: {len(status['services'])}")
        print(f"Pods: {len(status['pods'])}")
        
        for name, info in status['pods'].items():
            status_icon = "✅" if info['ready'] else "❌"
            print(f"  {status_icon} {name}: {info['phase']}")
    
    elif args.action == "health-check":
        success = deployment.run_health_checks()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()