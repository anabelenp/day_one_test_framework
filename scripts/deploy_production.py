#!/usr/bin/env python3
"""
Day-1 Framework - Production Environment Monitoring Script

This script provides read-only monitoring and health checks for the Production Environment (E5).
It does NOT deploy anything to production - only monitors existing production services.
"""

import os
import sys
import time
import subprocess
import argparse
import yaml
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

class ProductionMonitoring:
    """Manages read-only monitoring of the Production Environment"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "config/production.yaml"
        self.config = self._load_config()
        self.session = requests.Session()
        self.session.timeout = 30
        
        # Setup authentication if available
        self._setup_authentication()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load production configuration with environment variable substitution"""
        config_path = Path(self.config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Production config not found: {config_path}")
        
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Replace environment variables
        import re
        def replace_env_var(match):
            var_name = match.group(1)
            return os.environ.get(var_name, f"${{{var_name}}}")
        
        content = re.sub(r'\$\{([^}]+)\}', replace_env_var, content)
        
        try:
            config = yaml.safe_load(content)
            print("✅ Production configuration loaded")
            return config
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid production config: {e}")
    
    def _setup_authentication(self):
        """Setup authentication for production services"""
        # Setup API authentication
        if self.config.get('API_KEY'):
            self.session.headers.update({
                'Authorization': f"Bearer {self.config['API_KEY']}",
                'X-API-Key': self.config['API_KEY']
            })
        
        # Setup TLS if enabled
        if self.config.get('SECURITY_TLS_ENABLED'):
            cert_path = self.config.get('SECURITY_CERT_PATH')
            key_path = self.config.get('SECURITY_KEY_PATH')
            ca_path = self.config.get('SECURITY_CA_PATH')
            
            if cert_path and key_path:
                self.session.cert = (cert_path, key_path)
            if ca_path:
                self.session.verify = ca_path
    
    def check_prerequisites(self) -> bool:
        """Check if monitoring prerequisites are met"""
        print("🔍 Checking production monitoring prerequisites...")
        
        # Check read-only mode
        if not self.config.get('READ_ONLY_MODE', False):
            print("❌ Production config must have READ_ONLY_MODE: true")
            return False
        
        # Check required environment variables
        required_vars = [
            'REDIS_PROD_PASSWORD',
            'KAFKA_PROD_USERNAME', 
            'KAFKA_PROD_PASSWORD',
            'MONGODB_PROD_USERNAME',
            'MONGODB_PROD_PASSWORD',
            'NETSKOPE_PROD_API_KEY'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            print("💡 Set these variables or use external secret management")
            return False
        
        # Check network connectivity
        try:
            response = requests.get('https://www.google.com', timeout=5)
            print("✅ Network connectivity available")
        except requests.RequestException:
            print("❌ No network connectivity")
            return False
        
        print("✅ Production monitoring prerequisites met")
        return True
    
    def health_check_redis(self) -> Dict[str, Any]:
        """Health check for production Redis"""
        print("🔍 Checking Redis production health...")
        
        try:
            import redis
            
            # Connect to Redis with read-only user
            r = redis.Redis(
                host=self.config['REDIS_HOST'],
                port=self.config['REDIS_PORT'],
                password=os.environ.get('REDIS_PROD_PASSWORD'),
                ssl=self.config.get('REDIS_SSL', False),
                socket_timeout=10,
                socket_connect_timeout=10,
                health_check_interval=30
            )
            
            # Basic connectivity test
            ping_result = r.ping()
            
            # Get basic info (read-only)
            info = r.info()
            
            # Check replication status
            replication_info = r.info('replication')
            
            return {
                'status': 'healthy' if ping_result else 'unhealthy',
                'ping': ping_result,
                'version': info.get('redis_version'),
                'uptime': info.get('uptime_in_seconds'),
                'connected_clients': info.get('connected_clients'),
                'used_memory': info.get('used_memory_human'),
                'role': replication_info.get('role'),
                'connected_slaves': replication_info.get('connected_slaves', 0),
                'master_link_status': replication_info.get('master_link_status'),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def health_check_kafka(self) -> Dict[str, Any]:
        """Health check for production Kafka"""
        print("🔍 Checking Kafka production health...")
        
        try:
            # Import kafka modules (may not be available in test environment)
            try:
                from kafka import KafkaConsumer, KafkaProducer
                from kafka.admin import KafkaAdminClient
            except ImportError:
                return {
                    'status': 'error',
                    'error': 'Kafka client not available (kafka-python not installed)',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Setup SASL authentication
            sasl_config = {
                'bootstrap_servers': [self.config['KAFKA_BOOTSTRAP_SERVERS']],
                'security_protocol': self.config['KAFKA_SECURITY_PROTOCOL'],
                'sasl_mechanism': self.config['KAFKA_SASL_MECHANISM'],
                'sasl_plain_username': os.environ.get('KAFKA_PROD_USERNAME'),
                'sasl_plain_password': os.environ.get('KAFKA_PROD_PASSWORD'),
                'api_version': (2, 0, 0)
            }
            
            # Create admin client for cluster info
            admin_client = KafkaAdminClient(**sasl_config)
            
            # Get cluster metadata
            metadata = admin_client.describe_cluster()
            
            # Create consumer to check connectivity
            consumer = KafkaConsumer(
                **sasl_config,
                consumer_timeout_ms=5000,
                enable_auto_commit=False
            )
            
            # Get available topics (read-only)
            topics = consumer.topics()
            
            consumer.close()
            admin_client.close()
            
            return {
                'status': 'healthy',
                'cluster_id': metadata.cluster_id if hasattr(metadata, 'cluster_id') else 'unknown',
                'brokers': len(metadata.brokers) if hasattr(metadata, 'brokers') else 0,
                'topics_count': len(topics),
                'controller': metadata.controller.id if hasattr(metadata, 'controller') else 'unknown',
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def health_check_mongodb(self) -> Dict[str, Any]:
        """Health check for production MongoDB"""
        print("🔍 Checking MongoDB production health...")
        
        try:
            # Import pymongo (may not be available in test environment)
            try:
                from pymongo import MongoClient
            except ImportError:
                return {
                    'status': 'error',
                    'error': 'MongoDB client not available (pymongo not installed)',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Connect with read-only user
            client = MongoClient(
                host=self.config['MONGODB_HOST'],
                port=self.config['MONGODB_PORT'],
                username=os.environ.get('MONGODB_PROD_USERNAME'),
                password=os.environ.get('MONGODB_PROD_PASSWORD'),
                authSource=self.config['MONGODB_AUTH_SOURCE'],
                ssl=self.config.get('MONGODB_SSL', False),
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                maxPoolSize=5  # Limited for production
            )
            
            # Test connection
            client.admin.command('ping')
            
            # Get server info
            server_info = client.server_info()
            
            # Get replica set status (if applicable)
            try:
                rs_status = client.admin.command('replSetGetStatus')
                replica_set_info = {
                    'set_name': rs_status.get('set'),
                    'members': len(rs_status.get('members', [])),
                    'primary': next((m['name'] for m in rs_status.get('members', []) if m.get('stateStr') == 'PRIMARY'), None)
                }
            except:
                replica_set_info = {'set_name': None, 'members': 1, 'primary': 'standalone'}
            
            # Get database stats
            db = client[self.config['MONGODB_DATABASE']]
            db_stats = db.command('dbStats')
            
            client.close()
            
            return {
                'status': 'healthy',
                'version': server_info.get('version'),
                'uptime': server_info.get('uptime'),
                'replica_set': replica_set_info,
                'database_size': db_stats.get('dataSize'),
                'collections': db_stats.get('collections'),
                'indexes': db_stats.get('indexes'),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def health_check_api(self) -> Dict[str, Any]:
        """Health check for production Netskope API"""
        print("🔍 Checking Netskope API production health...")
        
        try:
            base_url = self.config['NETSKOPE_BASE_URL']
            
            # Check API health endpoint
            health_url = f"{base_url}/health"
            response = self.session.get(health_url, timeout=30)
            
            if response.status_code == 200:
                health_data = response.json() if response.content else {}
                
                # Try to get API version info
                try:
                    version_url = f"{base_url}/api/v2/version"
                    version_response = self.session.get(version_url, timeout=10)
                    version_data = version_response.json() if version_response.status_code == 200 else {}
                except:
                    version_data = {}
                
                return {
                    'status': 'healthy',
                    'response_time': response.elapsed.total_seconds(),
                    'api_version': version_data.get('version', 'unknown'),
                    'health_data': health_data,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'unhealthy',
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def health_check_monitoring(self) -> Dict[str, Any]:
        """Health check for production monitoring services"""
        print("🔍 Checking production monitoring services...")
        
        monitoring_services = {
            'prometheus': self.config.get('PROMETHEUS_URL'),
            'grafana': self.config.get('GRAFANA_URL'),
            'jaeger': self.config.get('JAEGER_URL'),
            'alertmanager': self.config.get('ALERTMANAGER_URL')
        }
        
        results = {}
        
        for service, url in monitoring_services.items():
            if not url:
                results[service] = {'status': 'not_configured'}
                continue
            
            try:
                # Check health endpoint
                health_endpoints = {
                    'prometheus': f"{url}/-/healthy",
                    'grafana': f"{url}/api/health",
                    'jaeger': f"{url}/api/health",
                    'alertmanager': f"{url}/-/healthy"
                }
                
                health_url = health_endpoints.get(service, f"{url}/health")
                response = self.session.get(health_url, timeout=10)
                
                results[service] = {
                    'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                    'status_code': response.status_code,
                    'response_time': response.elapsed.total_seconds(),
                    'timestamp': datetime.now().isoformat()
                }
                
            except Exception as e:
                results[service] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
        
        return results
    
    def run_comprehensive_health_check(self) -> Dict[str, Any]:
        """Run comprehensive health check on all production services"""
        print("🏥 Running comprehensive production health check...")
        print("⚠️  This is read-only monitoring - no changes will be made")
        
        health_results = {
            'environment': 'production',
            'timestamp': datetime.now().isoformat(),
            'read_only_mode': True,
            'services': {}
        }
        
        # Check each service
        services = [
            ('redis', self.health_check_redis),
            ('kafka', self.health_check_kafka),
            ('mongodb', self.health_check_mongodb),
            ('api', self.health_check_api)
        ]
        
        for service_name, check_func in services:
            try:
                print(f"  Checking {service_name}...")
                result = check_func()
                health_results['services'][service_name] = result
                
                status_icon = "✅" if result['status'] == 'healthy' else "❌"
                print(f"  {status_icon} {service_name}: {result['status']}")
                
            except Exception as e:
                health_results['services'][service_name] = {
                    'status': 'error',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                print(f"  ❌ {service_name}: error - {e}")
        
        # Check monitoring services
        monitoring_results = self.health_check_monitoring()
        health_results['monitoring'] = monitoring_results
        
        for service, result in monitoring_results.items():
            status_icon = "✅" if result.get('status') == 'healthy' else "❌"
            print(f"  {status_icon} {service}: {result.get('status', 'unknown')}")
        
        # Calculate overall health
        all_services = list(health_results['services'].values()) + list(monitoring_results.values())
        healthy_count = sum(1 for s in all_services if s.get('status') == 'healthy')
        total_count = len(all_services)
        
        health_results['overall_health'] = {
            'status': 'healthy' if healthy_count == total_count else 'degraded',
            'healthy_services': healthy_count,
            'total_services': total_count,
            'health_percentage': (healthy_count / total_count * 100) if total_count > 0 else 0
        }
        
        print(f"\n📊 Overall Health: {health_results['overall_health']['status']}")
        print(f"📈 Health Score: {health_results['overall_health']['health_percentage']:.1f}%")
        print(f"🔢 Services: {healthy_count}/{total_count} healthy")
        
        return health_results
    
    def get_production_metrics(self) -> Dict[str, Any]:
        """Get production metrics from monitoring systems"""
        print("📊 Collecting production metrics...")
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'environment': 'production',
            'prometheus': {},
            'custom': {}
        }
        
        # Get Prometheus metrics if available
        prometheus_url = self.config.get('PROMETHEUS_URL')
        if prometheus_url:
            try:
                # Query key production metrics
                queries = {
                    'cpu_usage': 'avg(100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100))',
                    'memory_usage': 'avg((1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100)',
                    'disk_usage': 'avg(100 - ((node_filesystem_avail_bytes * 100) / node_filesystem_size_bytes))',
                    'api_response_time': 'avg(api_request_duration_seconds)',
                    'api_error_rate': 'rate(api_errors_total[5m])',
                    'service_uptime': 'avg(up)'
                }
                
                for metric_name, query in queries.items():
                    try:
                        response = self.session.get(
                            f"{prometheus_url}/api/v1/query",
                            params={'query': query},
                            timeout=10
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            if data.get('status') == 'success' and data.get('data', {}).get('result'):
                                value = data['data']['result'][0]['value'][1]
                                metrics['prometheus'][metric_name] = float(value)
                            else:
                                metrics['prometheus'][metric_name] = None
                        else:
                            metrics['prometheus'][metric_name] = None
                            
                    except Exception as e:
                        metrics['prometheus'][metric_name] = f"error: {e}"
                
                print("✅ Prometheus metrics collected")
                
            except Exception as e:
                print(f"❌ Failed to collect Prometheus metrics: {e}")
                metrics['prometheus'] = {'error': str(e)}
        
        # Add custom metrics
        metrics['custom'] = {
            'health_check_timestamp': datetime.now().isoformat(),
            'monitoring_mode': 'read_only',
            'framework_version': '1.0.0'
        }
        
        return metrics
    
    def generate_health_report(self, output_file: Optional[str] = None) -> str:
        """Generate comprehensive health report"""
        print("📋 Generating production health report...")
        
        # Run health checks
        health_data = self.run_comprehensive_health_check()
        
        # Get metrics
        metrics_data = self.get_production_metrics()
        
        # Combine data
        report_data = {
            'report_metadata': {
                'generated_at': datetime.now().isoformat(),
                'environment': 'production',
                'framework': 'Day-1 Framework',
                'version': '1.0.0',
                'mode': 'read_only_monitoring'
            },
            'health_check': health_data,
            'metrics': metrics_data,
            'recommendations': self._generate_recommendations(health_data, metrics_data)
        }
        
        # Generate report
        report_json = json.dumps(report_data, indent=2)
        
        # Save to file if specified
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                f.write(report_json)
            
            print(f"✅ Health report saved to: {output_path}")
        
        return report_json
    
    def _generate_recommendations(self, health_data: Dict, metrics_data: Dict) -> List[str]:
        """Generate recommendations based on health and metrics data"""
        recommendations = []
        
        # Check service health
        for service, data in health_data.get('services', {}).items():
            if data.get('status') != 'healthy':
                recommendations.append(f"🔴 {service.upper()}: Service is {data.get('status')} - investigate immediately")
        
        # Check monitoring services
        for service, data in health_data.get('monitoring', {}).items():
            if data.get('status') != 'healthy':
                recommendations.append(f"🟡 {service.upper()}: Monitoring service is {data.get('status')} - check configuration")
        
        # Check Prometheus metrics
        prometheus_metrics = metrics_data.get('prometheus', {})
        
        if isinstance(prometheus_metrics.get('cpu_usage'), (int, float)):
            if prometheus_metrics['cpu_usage'] > 80:
                recommendations.append("🔴 HIGH CPU USAGE: CPU usage is above 80% - scale resources")
            elif prometheus_metrics['cpu_usage'] > 70:
                recommendations.append("🟡 ELEVATED CPU USAGE: CPU usage is above 70% - monitor closely")
        
        if isinstance(prometheus_metrics.get('memory_usage'), (int, float)):
            if prometheus_metrics['memory_usage'] > 85:
                recommendations.append("🔴 HIGH MEMORY USAGE: Memory usage is above 85% - scale resources")
            elif prometheus_metrics['memory_usage'] > 75:
                recommendations.append("🟡 ELEVATED MEMORY USAGE: Memory usage is above 75% - monitor closely")
        
        if isinstance(prometheus_metrics.get('api_error_rate'), (int, float)):
            if prometheus_metrics['api_error_rate'] > 0.01:  # 1%
                recommendations.append("🔴 HIGH ERROR RATE: API error rate is above 1% - investigate errors")
            elif prometheus_metrics['api_error_rate'] > 0.005:  # 0.5%
                recommendations.append("🟡 ELEVATED ERROR RATE: API error rate is above 0.5% - monitor closely")
        
        # Overall health recommendations
        overall_health = health_data.get('overall_health', {})
        health_percentage = overall_health.get('health_percentage', 0)
        
        if health_percentage < 80:
            recommendations.append("🔴 CRITICAL: Overall system health is below 80% - immediate action required")
        elif health_percentage < 95:
            recommendations.append("🟡 WARNING: Overall system health is below 95% - investigate degraded services")
        else:
            recommendations.append("✅ HEALTHY: All systems operating normally")
        
        return recommendations
    
    def monitor_continuous(self, interval: int = 300, duration: int = 3600) -> None:
        """Run continuous monitoring for specified duration"""
        print(f"🔄 Starting continuous production monitoring...")
        print(f"📊 Interval: {interval} seconds")
        print(f"⏱️ Duration: {duration} seconds")
        print("⚠️  Press Ctrl+C to stop monitoring")
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                print(f"\n{'='*60}")
                print(f"🕐 Monitoring cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Run health check
                health_data = self.run_comprehensive_health_check()
                
                # Check for critical issues
                critical_issues = []
                for service, data in health_data.get('services', {}).items():
                    if data.get('status') == 'error':
                        critical_issues.append(f"{service}: {data.get('error', 'unknown error')}")
                
                if critical_issues:
                    print(f"\n🚨 CRITICAL ISSUES DETECTED:")
                    for issue in critical_issues:
                        print(f"  ❌ {issue}")
                else:
                    print(f"\n✅ No critical issues detected")
                
                # Wait for next cycle
                print(f"\n⏳ Waiting {interval} seconds for next check...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print(f"\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"\n❌ Monitoring error: {e}")
        
        print(f"\n📊 Monitoring completed after {time.time() - start_time:.1f} seconds")

def main():
    parser = argparse.ArgumentParser(
        description="Day-1 Production Environment Monitoring (Read-Only)"
    )
    parser.add_argument(
        "--action",
        choices=["health-check", "metrics", "report", "monitor"],
        default="health-check",
        help="Monitoring action to perform"
    )
    parser.add_argument(
        "--config",
        default="config/production.yaml",
        help="Production configuration file"
    )
    parser.add_argument(
        "--output",
        help="Output file for reports"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Monitoring interval in seconds (for continuous monitoring)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=3600,
        help="Monitoring duration in seconds (for continuous monitoring)"
    )
    
    args = parser.parse_args()
    
    try:
        monitor = ProductionMonitoring(config_file=args.config)
        
        if not monitor.check_prerequisites():
            print("❌ Prerequisites not met")
            sys.exit(1)
        
        if args.action == "health-check":
            health_data = monitor.run_comprehensive_health_check()
            overall_status = health_data.get('overall_health', {}).get('status', 'unknown')
            sys.exit(0 if overall_status == 'healthy' else 1)
        
        elif args.action == "metrics":
            metrics = monitor.get_production_metrics()
            print(json.dumps(metrics, indent=2))
        
        elif args.action == "report":
            output_file = args.output or f"reports/production_health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report = monitor.generate_health_report(output_file)
            if not args.output:
                print(report)
        
        elif args.action == "monitor":
            monitor.monitor_continuous(interval=args.interval, duration=args.duration)
        
    except Exception as e:
        print(f"❌ Production monitoring error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()