"""
Locust Performance Testing for Netskope SDET Framework

This module provides comprehensive load testing using Locust for all Netskope security services:
- SWG (Secure Web Gateway) - URL checking and web filtering
- DLP (Data Loss Prevention) - File scanning and content analysis  
- ZTNA (Zero Trust Network Access) - Application access control
- Firewall - Network security rule validation

Usage:
    # Basic load test
    locust -f tests/performance/locust/netskope_load_test.py --host=http://localhost:8080

    # Custom configuration
    locust -f tests/performance/locust/netskope_load_test.py --host=http://localhost:8080 --users=100 --spawn-rate=10 --run-time=300s

    # Web UI mode
    locust -f tests/performance/locust/netskope_load_test.py --host=http://localhost:8080 --web-host=0.0.0.0 --web-port=8089

    # Headless mode with CSV output
    locust -f tests/performance/locust/netskope_load_test.py --host=http://localhost:8080 --users=50 --spawn-rate=5 --run-time=180s --headless --csv=reports/locust_results
"""

import json
import random
import time
from locust import HttpUser, task, between, events
from locust.env import Environment
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging
import logging

# Configure logging
setup_logging("INFO", None)
logger = logging.getLogger(__name__)

class NetskopeSecurityUser(HttpUser):
    """
    Simulates a user interacting with Netskope security services.
    
    This user class represents realistic usage patterns across all security services:
    - Web browsing (SWG)
    - File operations (DLP) 
    - Application access (ZTNA)
    - Network traffic (Firewall)
    """
    
    # Wait time between tasks (1-3 seconds to simulate realistic user behavior)
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize user session with authentication"""
        self.user_id = f"user_{random.randint(1, 10000)}"
        self.device_id = f"device_{random.randint(1, 1000)}"
        self.session_token = f"session_{random.randint(100000, 999999)}"
        
        # Set common headers for all requests
        self.client.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer mock-api-key-12345",
            "X-API-Key": "mock-api-key-12345",
            "X-User-ID": self.user_id,
            "X-Device-ID": self.device_id,
            "X-Session-Token": self.session_token
        })
        
        logger.info(f"User {self.user_id} started session with device {self.device_id}")
    
    @task(4)  # 40% of requests - Most common operation
    def check_url_swg(self):
        """
        SWG (Secure Web Gateway) - URL checking and web filtering
        
        Simulates users browsing to various websites that need to be checked
        against security policies for malware, phishing, and content filtering.
        """
        # Generate realistic URLs with different risk levels
        url_categories = [
            # Safe business URLs (70%)
            "salesforce.com", "office365.com", "slack.com", "zoom.us", "github.com",
            "linkedin.com", "microsoft.com", "google.com", "aws.amazon.com",
            
            # Potentially risky URLs (20%)
            "example-social.com", "random-blog.net", "file-sharing.org",
            
            # High-risk URLs (10%)
            "suspicious-site.com", "malware-test.org", "phishing-example.net"
        ]
        
        test_url = random.choice(url_categories)
        
        payload = {
            "url": test_url,
            "user_id": self.user_id,
            "device_id": self.device_id,
            "timestamp": int(time.time()),
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "source_ip": f"192.168.1.{random.randint(1, 254)}"
        }
        
        with self.client.post("/api/v2/swg/check-url", 
                             json=payload, 
                             name="SWG - URL Check",
                             catch_response=True) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "action" in result:
                        response.success()
                        logger.debug(f"SWG check for {test_url}: {result.get('action', 'unknown')}")
                    else:
                        response.failure("Missing action in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(3)  # 30% of requests - File operations
    def scan_file_dlp(self):
        """
        DLP (Data Loss Prevention) - File scanning and content analysis
        
        Simulates file uploads and content scanning for sensitive data like
        PII, credit cards, SSNs, and confidential business information.
        """
        # Generate realistic file content with varying sensitivity levels
        content_types = [
            # Safe content (60%)
            "This is a regular business document about quarterly results.",
            "Meeting notes from the team standup on project progress.",
            "Technical documentation for the new API endpoints.",
            
            # Sensitive content (30%)
            f"Employee record: John Doe, SSN: {random.randint(100000000, 999999999)}",
            f"Credit card processing: Card number {random.randint(1000000000000000, 9999999999999999)}",
            "CONFIDENTIAL: Merger and acquisition details for Q4 2024",
            
            # Highly sensitive content (10%)
            f"Database backup contains user passwords and SSN: {random.randint(100000000, 999999999)}",
            "TOP SECRET: Customer financial data export with full PII details"
        ]
        
        file_types = ["document.pdf", "spreadsheet.xlsx", "presentation.pptx", 
                     "data.csv", "backup.sql", "config.json", "report.docx"]
        
        content = random.choice(content_types)
        filename = random.choice(file_types)
        
        payload = {
            "content": content,
            "filename": filename,
            "user_id": self.user_id,
            "file_size": len(content),
            "mime_type": "application/octet-stream",
            "upload_timestamp": int(time.time()),
            "scan_policies": ["pii_detection", "credit_card", "confidential_data"]
        }
        
        with self.client.post("/api/v2/dlp/scan-file", 
                             json=payload, 
                             name="DLP - File Scan",
                             catch_response=True) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "scan_result" in result:
                        response.success()
                        logger.debug(f"DLP scan for {filename}: {result.get('scan_result', 'unknown')}")
                    else:
                        response.failure("Missing scan_result in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(2)  # 20% of requests - Application access
    def check_access_ztna(self):
        """
        ZTNA (Zero Trust Network Access) - Application access control
        
        Simulates users attempting to access various applications with
        different security requirements and access policies.
        """
        # Realistic application access patterns
        applications = [
            # Business applications (70%)
            {"name": "email_app", "sensitivity": "low", "mfa_required": False},
            {"name": "crm_system", "sensitivity": "medium", "mfa_required": True},
            {"name": "file_server", "sensitivity": "medium", "mfa_required": True},
            {"name": "collaboration_tool", "sensitivity": "low", "mfa_required": False},
            
            # Administrative applications (20%)
            {"name": "admin_portal", "sensitivity": "high", "mfa_required": True},
            {"name": "database_admin", "sensitivity": "high", "mfa_required": True},
            {"name": "security_console", "sensitivity": "critical", "mfa_required": True},
            
            # Development applications (10%)
            {"name": "jenkins", "sensitivity": "high", "mfa_required": True},
            {"name": "gitlab", "sensitivity": "high", "mfa_required": True},
            {"name": "monitoring_dashboard", "sensitivity": "medium", "mfa_required": True}
        ]
        
        app = random.choice(applications)
        
        payload = {
            "user": self.user_id,
            "application": app["name"],
            "device_id": self.device_id,
            "source_ip": f"10.0.{random.randint(1, 255)}.{random.randint(1, 255)}",
            "timestamp": int(time.time()),
            "device_posture": random.choice(["compliant", "non_compliant", "unknown"]),
            "mfa_status": random.choice([True, False]) if app["mfa_required"] else False,
            "risk_score": random.randint(1, 100)
        }
        
        with self.client.post("/api/v2/ztna/check-access", 
                             json=payload, 
                             name="ZTNA - Access Check",
                             catch_response=True) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "access_decision" in result:
                        response.success()
                        logger.debug(f"ZTNA access for {app['name']}: {result.get('access_decision', 'unknown')}")
                    else:
                        response.failure("Missing access_decision in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)  # 10% of requests - Network security
    def check_firewall_rules(self):
        """
        Firewall - Network security rule validation
        
        Simulates network traffic that needs to be evaluated against
        firewall rules for port access, protocol validation, and traffic filtering.
        """
        # Common network traffic patterns
        traffic_patterns = [
            # Standard business traffic (80%)
            {"protocol": "HTTPS", "port": 443, "risk": "low"},
            {"protocol": "HTTP", "port": 80, "risk": "medium"},
            {"protocol": "SMTP", "port": 587, "risk": "low"},
            {"protocol": "DNS", "port": 53, "risk": "low"},
            {"protocol": "SSH", "port": 22, "risk": "medium"},
            
            # Administrative traffic (15%)
            {"protocol": "RDP", "port": 3389, "risk": "high"},
            {"protocol": "VNC", "port": 5900, "risk": "high"},
            {"protocol": "SNMP", "port": 161, "risk": "medium"},
            
            # Suspicious traffic (5%)
            {"protocol": "TELNET", "port": 23, "risk": "critical"},
            {"protocol": "FTP", "port": 21, "risk": "high"},
            {"protocol": "CUSTOM", "port": random.randint(8000, 9999), "risk": "critical"}
        ]
        
        traffic = random.choice(traffic_patterns)
        
        payload = {
            "source_ip": f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
            "destination_ip": f"10.0.{random.randint(1, 255)}.{random.randint(1, 255)}",
            "protocol": traffic["protocol"],
            "destination_port": traffic["port"],
            "user_id": self.user_id,
            "timestamp": int(time.time()),
            "packet_size": random.randint(64, 1500),
            "connection_state": random.choice(["new", "established", "related"])
        }
        
        with self.client.post("/api/v2/firewall/check-rules", 
                             json=payload, 
                             name="Firewall - Rule Check",
                             catch_response=True) as response:
            if response.status_code == 200:
                try:
                    result = response.json()
                    if "action" in result:
                        response.success()
                        logger.debug(f"Firewall check for {traffic['protocol']}:{traffic['port']}: {result.get('action', 'unknown')}")
                    else:
                        response.failure("Missing action in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    def on_stop(self):
        """Cleanup when user session ends"""
        logger.info(f"User {self.user_id} session ended")


class AdminUser(HttpUser):
    """
    Administrative user for monitoring and reporting endpoints.
    
    Simulates administrative operations like viewing dashboards,
    generating reports, and monitoring system health.
    """
    
    wait_time = between(5, 15)  # Longer wait times for admin operations
    weight = 1  # Lower weight - fewer admin users
    
    def on_start(self):
        """Initialize admin session"""
        self.admin_id = f"admin_{random.randint(1, 100)}"
        self.client.headers.update({
            "Content-Type": "application/json",
            "Authorization": "Bearer admin-api-key-67890",
            "X-Admin-ID": self.admin_id
        })
        logger.info(f"Admin {self.admin_id} started session")
    
    @task(3)
    def get_security_events(self):
        """Retrieve security events for monitoring"""
        params = {
            "limit": random.randint(10, 100),
            "severity": random.choice(["low", "medium", "high", "critical"]),
            "time_range": random.choice(["1h", "24h", "7d"])
        }
        
        with self.client.get("/api/v2/events", 
                            params=params,
                            name="Admin - Security Events") as response:
            if response.status_code == 200:
                logger.debug(f"Retrieved {len(response.json().get('events', []))} security events")
    
    @task(2)
    def get_security_reports(self):
        """Generate security reports"""
        report_types = ["compliance", "incidents", "performance", "user_activity"]
        report_type = random.choice(report_types)
        
        params = {
            "report_type": report_type,
            "format": random.choice(["json", "csv", "pdf"]),
            "date_range": random.choice(["today", "week", "month"])
        }
        
        with self.client.get("/api/v2/reports", 
                            params=params,
                            name="Admin - Security Reports") as response:
            if response.status_code == 200:
                logger.debug(f"Generated {report_type} report")
    
    @task(1)
    def get_system_health(self):
        """Check system health status"""
        with self.client.get("/api/v2/health", 
                            name="Admin - System Health") as response:
            if response.status_code == 200:
                health_data = response.json()
                logger.debug(f"System health: {health_data.get('status', 'unknown')}")


# Custom event handlers for enhanced reporting
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Log detailed request information"""
    if exception:
        logger.error(f"Request failed: {name} - {exception}")
    else:
        logger.debug(f"Request completed: {name} - {response_time}ms")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log test start information"""
    logger.info(f"Load test started with {environment.parsed_options.num_users} users")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log test completion and summary"""
    stats = environment.stats
    logger.info(f"Load test completed:")
    logger.info(f"  Total requests: {stats.total.num_requests}")
    logger.info(f"  Failed requests: {stats.total.num_failures}")
    logger.info(f"  Average response time: {stats.total.avg_response_time:.2f}ms")
    logger.info(f"  Max response time: {stats.total.max_response_time}ms")
    logger.info(f"  Requests per second: {stats.total.current_rps:.2f}")


# Configuration for different load test scenarios
class LoadTestScenarios:
    """Predefined load test scenarios for different testing needs"""
    
    SMOKE_TEST = {
        "users": 5,
        "spawn_rate": 1,
        "run_time": "60s",
        "description": "Quick smoke test to verify basic functionality"
    }
    
    NORMAL_LOAD = {
        "users": 50,
        "spawn_rate": 5,
        "run_time": "300s",
        "description": "Normal business hours load simulation"
    }
    
    PEAK_LOAD = {
        "users": 200,
        "spawn_rate": 10,
        "run_time": "600s",
        "description": "Peak usage load testing"
    }
    
    STRESS_TEST = {
        "users": 500,
        "spawn_rate": 20,
        "run_time": "900s",
        "description": "Stress testing to find breaking points"
    }
    
    ENDURANCE_TEST = {
        "users": 100,
        "spawn_rate": 5,
        "run_time": "3600s",
        "description": "Long-running endurance test"
    }


if __name__ == "__main__":
    """
    Run Locust load tests with predefined scenarios
    
    Usage:
        python tests/performance/locust/netskope_load_test.py [scenario]
        
    Scenarios: smoke, normal, peak, stress, endurance
    """
    import sys
    import subprocess
    
    scenario_name = sys.argv[1] if len(sys.argv) > 1 else "normal"
    scenarios = LoadTestScenarios()
    
    if hasattr(scenarios, f"{scenario_name.upper()}_LOAD") or hasattr(scenarios, f"{scenario_name.upper()}_TEST"):
        scenario = getattr(scenarios, f"{scenario_name.upper()}_LOAD", 
                          getattr(scenarios, f"{scenario_name.upper()}_TEST"))
        
        print(f"Running {scenario_name} load test: {scenario['description']}")
        
        cmd = [
            "locust",
            "-f", __file__,
            "--host", "http://localhost:8080",
            "--users", str(scenario["users"]),
            "--spawn-rate", str(scenario["spawn_rate"]),
            "--run-time", scenario["run_time"],
            "--headless",
            "--csv", f"reports/locust_{scenario_name}_results"
        ]
        
        subprocess.run(cmd)
    else:
        print(f"Unknown scenario: {scenario_name}")
        print("Available scenarios: smoke, normal, peak, stress, endurance")