#!/usr/bin/env python3
"""
Mock Server for Netskope API Testing

This mock server simulates Netskope API endpoints for testing without real credentials.
Run this server locally to test the framework in mock mode.
"""

import json
import os
import time
import random
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class MockNetskopeHandler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        """Handle GET requests"""
        self._handle_request('GET')
    
    def do_POST(self):
        """Handle POST requests"""
        self._handle_request('POST')
    
    def do_PUT(self):
        """Handle PUT requests"""
        self._handle_request('PUT')
    
    def do_DELETE(self):
        """Handle DELETE requests"""
        self._handle_request('DELETE')
    
    def _handle_request(self, method):
        """Process API requests and return mock responses"""
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)
        
        # Add realistic API delay
        time.sleep(random.uniform(0.1, 0.5))
        
        # Route to appropriate handler
        if '/api/v2/events' in path:
            response = self._get_events()
        elif '/api/v2/policies' in path:
            response = self._get_policies()
        elif '/api/v2/users' in path:
            response = self._handle_users(method)
        elif '/api/v2/reports' in path:
            response = self._get_reports()
        elif '/api/v2/alerts' in path:
            response = self._get_alerts()
        else:
            response = self._default_response()
        
        # Send response
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
    
    def _get_events(self):
        """Mock events endpoint"""
        return {
            "status": "success",
            "data": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "event_id": f"evt_{random.randint(10000, 99999)}",
                    "user": random.choice(["john.doe", "jane.smith", "bob.wilson"]),
                    "action": random.choice(["allow", "block", "warn"]),
                    "category": random.choice(["SWG", "DLP", "ZTNA", "Firewall"]),
                    "risk_score": random.randint(1, 100),
                    "source_ip": f"192.168.1.{random.randint(1, 254)}",
                    "destination": "example.com",
                    "bytes_sent": random.randint(1000, 50000),
                    "bytes_received": random.randint(1000, 50000)
                }
                for _ in range(random.randint(1, 10))
            ],
            "total": random.randint(100, 1000)
        }
    
    def _get_policies(self):
        """Mock policies endpoint"""
        return {
            "status": "success",
            "data": {
                "swg_policies": [
                    {"id": 1, "name": "Block Social Media", "action": "block"},
                    {"id": 2, "name": "Allow Business Apps", "action": "allow"}
                ],
                "dlp_policies": [
                    {"id": 1, "name": "PCI Compliance", "severity": "high"},
                    {"id": 2, "name": "PII Protection", "severity": "medium"}
                ],
                "ztna_policies": [
                    {"id": 1, "name": "Engineering Access", "users": 25},
                    {"id": 2, "name": "Admin Access", "users": 3}
                ]
            }
        }
    
    def _handle_users(self, method):
        """Mock users endpoint"""
        if method == 'GET':
            return {
                "status": "success",
                "data": [
                    {
                        "username": "john.doe",
                        "email": "john.doe@company.com",
                        "department": "Engineering",
                        "risk_score": 25,
                        "last_activity": datetime.now().isoformat()
                    },
                    {
                        "username": "jane.smith", 
                        "email": "jane.smith@company.com",
                        "department": "IT",
                        "risk_score": 10,
                        "last_activity": datetime.now().isoformat()
                    }
                ]
            }
        else:
            return {"status": "success", "message": f"User {method} operation completed"}
    
    def _get_reports(self):
        """Mock reports endpoint"""
        return {
            "status": "success",
            "data": {
                "report_id": f"rpt_{random.randint(10000, 99999)}",
                "generated_at": datetime.now().isoformat(),
                "summary": {
                    "total_events": random.randint(1000, 10000),
                    "blocked_events": random.randint(100, 1000),
                    "high_risk_users": random.randint(5, 25),
                    "policy_violations": random.randint(10, 100)
                }
            }
        }
    
    def _get_alerts(self):
        """Mock alerts endpoint"""
        return {
            "status": "success",
            "data": [
                {
                    "alert_id": f"alt_{random.randint(10000, 99999)}",
                    "severity": random.choice(["low", "medium", "high", "critical"]),
                    "title": random.choice([
                        "Suspicious File Upload Detected",
                        "Multiple Failed Login Attempts", 
                        "Malware Download Blocked",
                        "Data Exfiltration Attempt"
                    ]),
                    "user": random.choice(["john.doe", "jane.smith", "bob.wilson"]),
                    "timestamp": datetime.now().isoformat(),
                    "status": random.choice(["open", "investigating", "resolved"])
                }
                for _ in range(random.randint(1, 5))
            ]
        }
    
    def _default_response(self):
        """Default mock response"""
        return {
            "status": "success",
            "message": "Mock API response",
            "timestamp": datetime.now().isoformat()
        }
    
    def log_message(self, format, *args):
        """Custom log format"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

def start_mock_server(port=8080):
    """Start the mock server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, MockNetskopeHandler)
    print(f"🚀 Mock Netskope API Server running on http://localhost:{port}")
    print("📝 Available endpoints:")
    print("   - GET  /api/v2/events")
    print("   - GET  /api/v2/policies") 
    print("   - GET  /api/v2/users")
    print("   - GET  /api/v2/reports")
    print("   - GET  /api/v2/alerts")
    print("   - POST /api/v2/users")
    print("\n🔧 Mock mode is active - no real API calls will be made")
    print("⏹️  Press Ctrl+C to stop the server\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Mock server stopped")
        httpd.server_close()

if __name__ == '__main__':
    start_mock_server()