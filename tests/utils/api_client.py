import yaml
import json
import os
import time
import random
from datetime import datetime

# Load environment
with open('config/env.yaml') as f:
    env = yaml.safe_load(f)

with open('config/policies.json') as f:
    POLICIES = json.load(f)

# Mock mode configuration
MOCK_MODE = env.get('MOCK_MODE', True)
MOCK_RESPONSES_PATH = env.get('MOCK_RESPONSES_PATH', './tests/mock_responses')

class NetskopeAPIClient:
    def __init__(self):
        self.policies = POLICIES
        self.users = {}
        self.mock_mode = MOCK_MODE
        self.base_url = env.get('NETSKOPE_BASE_URL')
        self.api_key = env.get('API_KEY')
        
        # Initialize mock data
        if self.mock_mode:
            self._init_mock_data()
    
    def _init_mock_data(self):
        """Initialize mock data for testing"""
        self.mock_events = []
        self.mock_alerts = []
        self.mock_users = {
            "john.doe": {"role": "user", "department": "Engineering", "risk_score": 25},
            "jane.smith": {"role": "admin", "department": "IT", "risk_score": 10},
            "bob.wilson": {"role": "user", "department": "Sales", "risk_score": 45}
        }
        
    def _generate_mock_response(self, endpoint, data=None):
        """Generate realistic mock responses"""
        timestamp = datetime.now().isoformat()
        
        mock_responses = {
            "events": {
                "status": "success",
                "data": [
                    {
                        "timestamp": timestamp,
                        "user": random.choice(list(self.mock_users.keys())),
                        "action": random.choice(["allow", "block", "warn"]),
                        "category": random.choice(["SWG", "DLP", "ZTNA", "Firewall"]),
                        "risk_score": random.randint(1, 100)
                    }
                ],
                "total": 1
            },
            "policies": {
                "status": "success", 
                "data": self.policies
            },
            "users": {
                "status": "success",
                "data": list(self.mock_users.values())
            }
        }
        
        return mock_responses.get(endpoint, {"status": "success", "data": data or {}})

    # SWG
    def check_url(self, url):
        return "block" if url in self.policies['swg']['blocked_urls'] else "allow"

    # DLP
    def check_file_content(self, content):
        for pattern in self.policies['dlp']['blocked_patterns']:
            if pattern in content:
                return "block"
        return "allow"

    # ZTNA
    def check_app_access(self, username, app):
        if app in self.policies['ztna']['restricted_apps']:
            return "deny"
        return "allow"

    # Firewall
    def check_port(self, port):
        return "block" if port in self.policies['firewall']['blocked_ports'] else "allow"

    # User management
    def create_user(self, username, role="user"):
        self.users[username] = role
        return {"username": username, "role": role}

    def delete_user(self, username):
        if username in self.users:
            del self.users[username]
            return True
        return False
