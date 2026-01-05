#!/usr/bin/env python3
"""
End-to-End Tests for Integration Environment

Complete end-to-end test scenarios that validate the entire system
working together in the Integration Environment (E3).
"""

import pytest
import time
import json
from typing import Dict, Any, List

from src.environment_manager import EnvironmentManager, Environment
from src.service_manager import ServiceManager


class TestIntegrationE2E:
    """End-to-end test scenarios for integration environment"""
    
    @pytest.fixture(autouse=True)
    def setup_integration_environment(self):
        """Setup for E2E tests in integration environment"""
        env_manager = EnvironmentManager()
        current_env = env_manager.get_current_environment()
        
        if current_env != Environment.INTEGRATION:
            pytest.skip(f"E2E tests require integration environment, got {current_env.value}")
        
        self.env_manager = env_manager
        self.service_manager = ServiceManager()
        
        # Get all service clients
        self.cache_client = self.service_manager.get_cache_client()
        self.message_client = self.service_manager.get_message_client()
        self.db_client = self.service_manager.get_database_client()
        self.api_client = self.service_manager.get_api_client()
        
        # Ensure all services are connected
        assert self.cache_client.connect(), "Cache client should connect"
        assert self.message_client.connect(), "Message client should connect"
        assert self.db_client.connect(), "Database client should connect"
        assert self.api_client.connect(), "API client should connect"
        
        # Authenticate API client
        auth_result = self.api_client.authenticate({"api_key": "integration-api-key-2024"})
        assert auth_result, "API authentication should succeed"
    
    @pytest.mark.e2e
    def test_complete_security_event_workflow(self):
        """Test complete workflow from security event detection to storage and retrieval"""
        
        # Step 1: Simulate security event detection
        security_event = {
            "event_id": f"evt_e2e_{int(time.time())}",
            "timestamp": time.time(),
            "event_type": "swg",
            "severity": "high",
            "user": "test.user@company.com",
            "action": "blocked",
            "url": "malicious-site.com",
            "category": "malware",
            "details": {
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 Test Browser",
                "threat_score": 95
            }
        }
        
        # Step 2: Store event in cache for fast access
        cache_key = f"security_event:{security_event['event_id']}"
        cache_result = self.cache_client.set(cache_key, json.dumps(security_event))
        assert cache_result, "Should store security event in cache"
        
        # Step 3: Publish event to message queue for processing
        topic = "security_events"
        self.message_client.create_topic(topic)
        publish_result = self.message_client.publish(topic, security_event)
        assert publish_result, "Should publish security event to message queue"
        
        # Step 4: Store event in database for persistence
        collection = "security_events"
        doc_id = self.db_client.insert_one(collection, security_event)
        assert doc_id is not None, "Should store security event in database"
        
        # Step 5: Verify event can be retrieved from cache
        cached_event = self.cache_client.get(cache_key)
        assert cached_event is not None, "Should retrieve event from cache"
        cached_event_data = json.loads(cached_event)
        assert cached_event_data["event_id"] == security_event["event_id"], "Cached event should match"
        
        # Step 6: Verify event can be consumed from message queue
        messages = self.message_client.consume(topic, timeout=5000)
        assert len(messages) > 0, "Should consume security event from message queue"
        
        consumed_event = None
        for message in messages:
            if message.get("event_id") == security_event["event_id"]:
                consumed_event = message
                break
        
        assert consumed_event is not None, "Should find our security event in consumed messages"
        assert consumed_event["event_type"] == security_event["event_type"], "Consumed event should match"
        
        # Step 7: Verify event can be retrieved from database
        stored_event = self.db_client.find_one(collection, {"event_id": security_event["event_id"]})
        assert stored_event is not None, "Should retrieve event from database"
        assert stored_event["severity"] == security_event["severity"], "Stored event should match"
        
        # Step 8: Query events via API
        api_events = self.api_client.get("/api/v2/events")
        assert api_events is not None, "Should get events from API"
        assert "data" in api_events, "API response should contain data"
        
        # Clean up
        self.cache_client.delete(cache_key)
        self.db_client.delete_one(collection, {"event_id": security_event["event_id"]})
    
    @pytest.mark.e2e
    def test_policy_management_workflow(self):
        """Test complete policy management workflow"""
        
        # Step 1: Create a new security policy
        policy = {
            "policy_id": f"pol_e2e_{int(time.time())}",
            "name": "E2E Test Policy",
            "type": "swg",
            "enabled": True,
            "rules": [
                {
                    "action": "block",
                    "categories": ["malware", "phishing"],
                    "users": ["all"]
                }
            ],
            "created_at": time.time(),
            "created_by": "e2e_test"
        }
        
        # Step 2: Store policy in database
        collection = "policies"
        doc_id = self.db_client.insert_one(collection, policy)
        assert doc_id is not None, "Should store policy in database"
        
        # Step 3: Cache policy for fast access
        cache_key = f"policy:{policy['policy_id']}"
        cache_result = self.cache_client.set(cache_key, json.dumps(policy))
        assert cache_result, "Should cache policy"
        
        # Step 4: Publish policy update event
        policy_event = {
            "event_type": "policy_created",
            "policy_id": policy["policy_id"],
            "timestamp": time.time(),
            "details": policy
        }
        
        topic = "policy_updates"
        self.message_client.create_topic(topic)
        publish_result = self.message_client.publish(topic, policy_event)
        assert publish_result, "Should publish policy update event"
        
        # Step 5: Retrieve policy via API
        api_policies = self.api_client.get("/api/v2/policies")
        assert api_policies is not None, "Should get policies from API"
        assert "data" in api_policies, "API response should contain data"
        
        # Step 6: Update policy
        updated_policy = policy.copy()
        updated_policy["enabled"] = False
        updated_policy["updated_at"] = time.time()
        
        update_result = self.db_client.update_one(
            collection,
            {"policy_id": policy["policy_id"]},
            {"$set": {"enabled": False, "updated_at": updated_policy["updated_at"]}}
        )
        assert update_result, "Should update policy in database"
        
        # Step 7: Update cache
        cache_result = self.cache_client.set(cache_key, json.dumps(updated_policy))
        assert cache_result, "Should update cached policy"
        
        # Step 8: Publish policy update event
        update_event = {
            "event_type": "policy_updated",
            "policy_id": policy["policy_id"],
            "timestamp": time.time(),
            "changes": {"enabled": False}
        }
        
        publish_result = self.message_client.publish(topic, update_event)
        assert publish_result, "Should publish policy update event"
        
        # Step 9: Verify updates
        cached_policy = self.cache_client.get(cache_key)
        assert cached_policy is not None, "Should retrieve updated policy from cache"
        cached_policy_data = json.loads(cached_policy)
        assert not cached_policy_data["enabled"], "Cached policy should be disabled"
        
        stored_policy = self.db_client.find_one(collection, {"policy_id": policy["policy_id"]})
        assert stored_policy is not None, "Should retrieve updated policy from database"
        assert not stored_policy["enabled"], "Stored policy should be disabled"
        
        # Clean up
        self.cache_client.delete(cache_key)
        self.db_client.delete_one(collection, {"policy_id": policy["policy_id"]})
    
    @pytest.mark.e2e
    def test_user_risk_assessment_workflow(self):
        """Test complete user risk assessment workflow"""
        
        # Step 1: Create user profile
        user = {
            "user_id": f"usr_e2e_{int(time.time())}",
            "email": "e2e.test@company.com",
            "name": "E2E Test User",
            "department": "Engineering",
            "risk_score": 50,
            "status": "active",
            "created_at": time.time(),
            "last_activity": time.time()
        }
        
        # Step 2: Store user in database
        collection = "users"
        doc_id = self.db_client.insert_one(collection, user)
        assert doc_id is not None, "Should store user in database"
        
        # Step 3: Simulate security events for risk calculation
        security_events = [
            {
                "event_id": f"evt_risk_{i}_{int(time.time())}",
                "user_id": user["user_id"],
                "event_type": "swg",
                "severity": "medium",
                "risk_impact": 10,
                "timestamp": time.time() - (i * 3600)  # Events over time
            }
            for i in range(3)
        ]
        
        # Store events
        events_collection = "security_events"
        for event in security_events:
            self.db_client.insert_one(events_collection, event)
        
        # Step 4: Calculate updated risk score
        total_risk_impact = sum(event["risk_impact"] for event in security_events)
        new_risk_score = min(100, user["risk_score"] + total_risk_impact)
        
        # Step 5: Update user risk score
        update_result = self.db_client.update_one(
            collection,
            {"user_id": user["user_id"]},
            {"$set": {"risk_score": new_risk_score, "updated_at": time.time()}}
        )
        assert update_result, "Should update user risk score"
        
        # Step 6: Cache updated user data
        cache_key = f"user:{user['user_id']}"
        user["risk_score"] = new_risk_score
        cache_result = self.cache_client.set(cache_key, json.dumps(user))
        assert cache_result, "Should cache updated user data"
        
        # Step 7: Publish risk update event
        risk_event = {
            "event_type": "risk_score_updated",
            "user_id": user["user_id"],
            "old_risk_score": 50,
            "new_risk_score": new_risk_score,
            "timestamp": time.time()
        }
        
        topic = "risk_updates"
        self.message_client.create_topic(topic)
        publish_result = self.message_client.publish(topic, risk_event)
        assert publish_result, "Should publish risk update event"
        
        # Step 8: Verify via API
        api_users = self.api_client.get("/api/v2/users")
        assert api_users is not None, "Should get users from API"
        assert "data" in api_users, "API response should contain data"
        
        # Step 9: Verify risk score update
        updated_user = self.db_client.find_one(collection, {"user_id": user["user_id"]})
        assert updated_user is not None, "Should retrieve updated user"
        assert updated_user["risk_score"] == new_risk_score, "Risk score should be updated"
        
        cached_user = self.cache_client.get(cache_key)
        assert cached_user is not None, "Should retrieve cached user"
        cached_user_data = json.loads(cached_user)
        assert cached_user_data["risk_score"] == new_risk_score, "Cached risk score should be updated"
        
        # Clean up
        self.cache_client.delete(cache_key)
        self.db_client.delete_one(collection, {"user_id": user["user_id"]})
        for event in security_events:
            self.db_client.delete_one(events_collection, {"event_id": event["event_id"]})
    
    @pytest.mark.e2e
    def test_alert_generation_and_notification_workflow(self):
        """Test complete alert generation and notification workflow"""
        
        # Step 1: Create high-severity security event that should trigger alert
        critical_event = {
            "event_id": f"evt_critical_{int(time.time())}",
            "timestamp": time.time(),
            "event_type": "dlp",
            "severity": "critical",
            "user": "admin@company.com",
            "action": "blocked",
            "file": "confidential_data.xlsx",
            "violation": "PII and financial data detected",
            "details": {
                "data_types": ["ssn", "credit_card", "bank_account"],
                "match_count": 150,
                "file_size": "2.5MB"
            }
        }
        
        # Step 2: Store event
        events_collection = "security_events"
        doc_id = self.db_client.insert_one(events_collection, critical_event)
        assert doc_id is not None, "Should store critical event"
        
        # Step 3: Generate alert based on event
        alert = {
            "alert_id": f"alt_critical_{int(time.time())}",
            "event_id": critical_event["event_id"],
            "timestamp": time.time(),
            "type": "data_breach_risk",
            "severity": "critical",
            "title": "Critical DLP Violation Detected",
            "description": f"User {critical_event['user']} attempted to access file with sensitive data",
            "status": "open",
            "assigned_to": None,
            "created_by": "system"
        }
        
        # Step 4: Store alert
        alerts_collection = "alerts"
        alert_doc_id = self.db_client.insert_one(alerts_collection, alert)
        assert alert_doc_id is not None, "Should store alert"
        
        # Step 5: Cache alert for fast access
        cache_key = f"alert:{alert['alert_id']}"
        cache_result = self.cache_client.set(cache_key, json.dumps(alert))
        assert cache_result, "Should cache alert"
        
        # Step 6: Publish alert notification
        notification = {
            "notification_type": "alert_created",
            "alert_id": alert["alert_id"],
            "severity": alert["severity"],
            "title": alert["title"],
            "timestamp": time.time(),
            "recipients": ["security-team@company.com"]
        }
        
        topic = "alert_notifications"
        self.message_client.create_topic(topic)
        publish_result = self.message_client.publish(topic, notification)
        assert publish_result, "Should publish alert notification"
        
        # Step 7: Simulate alert acknowledgment
        alert["status"] = "acknowledged"
        alert["assigned_to"] = "security.analyst@company.com"
        alert["acknowledged_at"] = time.time()
        
        update_result = self.db_client.update_one(
            alerts_collection,
            {"alert_id": alert["alert_id"]},
            {"$set": {
                "status": "acknowledged",
                "assigned_to": alert["assigned_to"],
                "acknowledged_at": alert["acknowledged_at"]
            }}
        )
        assert update_result, "Should update alert status"
        
        # Step 8: Update cache
        cache_result = self.cache_client.set(cache_key, json.dumps(alert))
        assert cache_result, "Should update cached alert"
        
        # Step 9: Publish status update
        status_update = {
            "notification_type": "alert_acknowledged",
            "alert_id": alert["alert_id"],
            "assigned_to": alert["assigned_to"],
            "timestamp": time.time()
        }
        
        publish_result = self.message_client.publish(topic, status_update)
        assert publish_result, "Should publish alert status update"
        
        # Step 10: Verify via API
        api_alerts = self.api_client.get("/api/v2/alerts")
        assert api_alerts is not None, "Should get alerts from API"
        assert "data" in api_alerts, "API response should contain data"
        
        # Step 11: Verify alert updates
        updated_alert = self.db_client.find_one(alerts_collection, {"alert_id": alert["alert_id"]})
        assert updated_alert is not None, "Should retrieve updated alert"
        assert updated_alert["status"] == "acknowledged", "Alert should be acknowledged"
        assert updated_alert["assigned_to"] == alert["assigned_to"], "Alert should be assigned"
        
        # Clean up
        self.cache_client.delete(cache_key)
        self.db_client.delete_one(alerts_collection, {"alert_id": alert["alert_id"]})
        self.db_client.delete_one(events_collection, {"event_id": critical_event["event_id"]})
    
    @pytest.mark.e2e
    @pytest.mark.slow
    def test_system_performance_under_load(self):
        """Test system performance under moderate load"""
        import concurrent.futures
        import threading
        
        # Test concurrent operations across all services
        def concurrent_operations(thread_id: int) -> Dict[str, Any]:
            results = {
                "thread_id": thread_id,
                "operations": 0,
                "errors": 0,
                "start_time": time.time()
            }
            
            try:
                for i in range(20):  # 20 operations per thread
                    # Cache operations
                    key = f"load_test_{thread_id}_{i}"
                    value = f"value_{thread_id}_{i}"
                    self.cache_client.set(key, value)
                    retrieved = self.cache_client.get(key)
                    assert retrieved == value
                    self.cache_client.delete(key)
                    
                    # Database operations
                    doc = {
                        "thread_id": thread_id,
                        "operation": i,
                        "timestamp": time.time()
                    }
                    doc_id = self.db_client.insert_one("load_test", doc)
                    assert doc_id is not None
                    
                    found_doc = self.db_client.find_one("load_test", {"thread_id": thread_id, "operation": i})
                    assert found_doc is not None
                    
                    self.db_client.delete_one("load_test", {"thread_id": thread_id, "operation": i})
                    
                    # API operations (every 5th iteration to avoid overwhelming)
                    if i % 5 == 0:
                        response = self.api_client.get("/api/v2/events")
                        assert response is not None
                    
                    results["operations"] += 1
                    
            except Exception as e:
                results["errors"] += 1
                print(f"Error in thread {thread_id}: {e}")
            
            results["end_time"] = time.time()
            results["duration"] = results["end_time"] - results["start_time"]
            
            return results
        
        # Run concurrent operations
        num_threads = 5
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(concurrent_operations, i) for i in range(num_threads)]
            
            results = []
            for future in concurrent.futures.as_completed(futures, timeout=60):
                result = future.result()
                results.append(result)
        
        # Analyze results
        total_operations = sum(r["operations"] for r in results)
        total_errors = sum(r["errors"] for r in results)
        avg_duration = sum(r["duration"] for r in results) / len(results)
        
        print(f"Load test results:")
        print(f"  Total operations: {total_operations}")
        print(f"  Total errors: {total_errors}")
        print(f"  Average duration per thread: {avg_duration:.2f}s")
        print(f"  Error rate: {(total_errors / total_operations * 100):.2f}%")
        
        # Assertions
        assert total_operations > 0, "Should complete some operations"
        assert total_errors / total_operations < 0.1, "Error rate should be less than 10%"
        assert avg_duration < 30, "Average duration should be reasonable"
    
    @pytest.mark.e2e
    def test_data_consistency_across_services(self):
        """Test data consistency across all services"""
        
        # Create test data
        test_id = f"consistency_test_{int(time.time())}"
        test_data = {
            "id": test_id,
            "name": "Data Consistency Test",
            "value": 12345,
            "timestamp": time.time(),
            "metadata": {
                "test_type": "consistency",
                "environment": "integration"
            }
        }
        
        # Store in all services
        # 1. Cache
        cache_key = f"consistency:{test_id}"
        cache_result = self.cache_client.set(cache_key, json.dumps(test_data))
        assert cache_result, "Should store in cache"
        
        # 2. Database
        collection = "consistency_test"
        doc_id = self.db_client.insert_one(collection, test_data)
        assert doc_id is not None, "Should store in database"
        
        # 3. Message queue
        topic = "consistency_test"
        self.message_client.create_topic(topic)
        publish_result = self.message_client.publish(topic, test_data)
        assert publish_result, "Should publish to message queue"
        
        # Verify data consistency
        # 1. Retrieve from cache
        cached_data = self.cache_client.get(cache_key)
        assert cached_data is not None, "Should retrieve from cache"
        cached_data_obj = json.loads(cached_data)
        assert cached_data_obj["id"] == test_id, "Cached data should match"
        assert cached_data_obj["value"] == test_data["value"], "Cached value should match"
        
        # 2. Retrieve from database
        stored_data = self.db_client.find_one(collection, {"id": test_id})
        assert stored_data is not None, "Should retrieve from database"
        assert stored_data["name"] == test_data["name"], "Stored name should match"
        assert stored_data["value"] == test_data["value"], "Stored value should match"
        
        # 3. Consume from message queue
        messages = self.message_client.consume(topic, timeout=5000)
        assert len(messages) > 0, "Should consume messages"
        
        consumed_data = None
        for message in messages:
            if message.get("id") == test_id:
                consumed_data = message
                break
        
        assert consumed_data is not None, "Should find our message"
        assert consumed_data["name"] == test_data["name"], "Consumed name should match"
        assert consumed_data["value"] == test_data["value"], "Consumed value should match"
        
        # Verify all data is identical
        assert cached_data_obj["name"] == stored_data["name"] == consumed_data["name"], \
            "Name should be consistent across all services"
        assert cached_data_obj["value"] == stored_data["value"] == consumed_data["value"], \
            "Value should be consistent across all services"
        
        # Clean up
        self.cache_client.delete(cache_key)
        self.db_client.delete_one(collection, {"id": test_id})


if __name__ == "__main__":
    # Run E2E tests
    pytest.main([__file__, "-v", "-m", "e2e"])