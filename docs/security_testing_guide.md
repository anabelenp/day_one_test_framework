# Day-1 Test Framework - Security Testing Guide

##  Overview

This guide provides comprehensive security testing methodologies specifically designed for cybersecurity API testing within the Day-1 Test Framework. It covers threat modeling, security test patterns, compliance validation, and incident response testing.

##  Security Testing Objectives

### **Primary Security Goals**
1. **Zero Trust Validation**: Verify all security controls and access policies
2. **Data Protection**: Ensure PII/PHI data is properly protected at all stages
3. **Compliance Assurance**: Validate SOC2, GDPR, PCI DSS, and industry standards
4. **Threat Detection**: Test security monitoring and incident response capabilities
5. **Vulnerability Prevention**: Proactive security testing to prevent breaches

### **Security Testing Principles**
- **Shift-Left Security**: Security testing integrated from development start
- **Defense in Depth**: Multiple layers of security validation
- **Continuous Security**: Ongoing security validation in all environments
- **Compliance by Design**: Built-in compliance validation
- **Threat-Informed Testing**: Based on real-world attack patterns

##  Threat Modeling for API Security

### **STRIDE Threat Model for Netskope APIs**

#### **Spoofing Identity**
```python
class TestIdentitySpoofing:
    """Test protection against identity spoofing attacks"""
    
    def test_jwt_token_tampering(self):
        """Verify JWT tokens cannot be tampered with"""
        # Create valid JWT token
        valid_token = self.auth_service.create_token(user_id="test_user")
        
        # Attempt to tamper with token payload
        tampered_token = self.tamper_jwt_payload(valid_token, {"role": "admin"})
        
        # Verify tampered token is rejected
        response = self.api_client.get("/api/v2/admin/users",
                                     headers={"Authorization": f"Bearer {tampered_token}"})
        assert response.status_code == 401
        assert "invalid_token" in response.json()["error"]
    
    def test_session_hijacking_protection(self):
        """Test protection against session hijacking"""
        # Create session for user A
        session_a = self.create_user_session("user_a", ip="192.168.1.100")
        
        # Attempt to use session from different IP
        response = self.api_client.get("/api/v2/profile",
                                     headers={"Authorization": f"Bearer {session_a}"},
                                     headers_override={"X-Forwarded-For": "10.0.0.1"})
        
        # Should require re-authentication due to IP change
        assert response.status_code in [401, 403]
```

#### **Tampering with Data**
```python
class TestDataTampering:
    """Test protection against data tampering"""
    
    def test_api_request_integrity(self):
        """Verify API requests cannot be tampered with"""
        # Create signed request
        payload = {"user_id": "test_user", "action": "view_file"}
        signature = self.create_request_signature(payload)
        
        # Tamper with payload
        tampered_payload = payload.copy()
        tampered_payload["action"] = "delete_file"
        
        # Send tampered request with original signature
        response = self.api_client.post("/api/v2/files/action",
                                      json=tampered_payload,
                                      headers={"X-Signature": signature})
        
        # Should reject due to signature mismatch
        assert response.status_code == 400
        assert "signature_mismatch" in response.json()["error"]
    
    def test_database_integrity_checks(self):
        """Test database integrity validation"""
        # Create user with specific permissions
        user = self.create_test_user(permissions=["read_files"])
        
        # Attempt to directly modify database (simulating SQL injection)
        malicious_query = "UPDATE users SET permissions='admin' WHERE id=?"
        
        # Verify database has integrity constraints
        with pytest.raises(IntegrityError):
            self.db.execute(malicious_query, (user.id,))
```

#### **Repudiation**
```python
class TestNonRepudiation:
    """Test audit logging and non-repudiation controls"""
    
    def test_audit_log_integrity(self):
        """Verify audit logs cannot be modified"""
        # Perform auditable action
        response = self.api_client.delete("/api/v2/files/sensitive_document.pdf")
        assert response.status_code == 200
        
        # Verify audit log entry exists
        audit_logs = self.get_audit_logs(action="file_delete")
        assert len(audit_logs) == 1
        
        # Attempt to modify audit log
        original_log = audit_logs[0]
        with pytest.raises(PermissionError):
            self.audit_service.modify_log(original_log.id, {"action": "file_view"})
    
    def test_digital_signatures(self):
        """Test digital signature validation"""
        # Create signed document
        document = {"content": "Sensitive policy document", "version": "1.0"}
        signature = self.crypto_service.sign_document(document)
        
        # Verify signature validation
        is_valid = self.crypto_service.verify_signature(document, signature)
        assert is_valid == True
        
        # Tamper with document
        tampered_document = document.copy()
        tampered_document["content"] = "Modified content"
        
        # Verify signature fails for tampered document
        is_valid = self.crypto_service.verify_signature(tampered_document, signature)
        assert is_valid == False
```

#### **Information Disclosure**
```python
class TestInformationDisclosure:
    """Test protection against information disclosure"""
    
    def test_sensitive_data_exposure(self):
        """Verify sensitive data is not exposed in responses"""
        # Create user with sensitive data
        user = self.create_test_user(
            ssn="123-45-6789",
            credit_card="4111-1111-1111-1111"
        )
        
        # Retrieve user profile
        response = self.api_client.get(f"/api/v2/users/{user.id}")
        user_data = response.json()
        
        # Verify sensitive data is masked
        assert user_data["ssn"] == "***-**-6789"
        assert user_data["credit_card"] == "****-****-****-1111"
    
    def test_error_message_information_leakage(self):
        """Verify error messages don't leak sensitive information"""
        # Attempt to access non-existent user
        response = self.api_client.get("/api/v2/users/999999")
        
        # Error message should be generic
        assert response.status_code == 404
        error_message = response.json()["error"]
        assert "user not found" in error_message.lower()
        assert "database" not in error_message.lower()
        assert "table" not in error_message.lower()
        assert "sql" not in error_message.lower()
```

#### **Denial of Service**
```python
class TestDenialOfService:
    """Test protection against DoS attacks"""
    
    def test_rate_limiting(self):
        """Verify API rate limiting is enforced"""
        # Make requests up to rate limit
        for i in range(100):  # Assuming 100 req/min limit
            response = self.api_client.get("/api/v2/events")
            if i < 99:
                assert response.status_code == 200
        
        # Next request should be rate limited
        response = self.api_client.get("/api/v2/events")
        assert response.status_code == 429
        assert "rate_limit_exceeded" in response.json()["error"]
    
    def test_resource_exhaustion_protection(self):
        """Test protection against resource exhaustion"""
        # Attempt to request large dataset
        response = self.api_client.get("/api/v2/events?limit=1000000")
        
        # Should limit response size
        assert response.status_code in [400, 413]  # Bad request or payload too large
        
        # Or should paginate results
        if response.status_code == 200:
            data = response.json()
            assert len(data["events"]) <= 1000  # Max page size
            assert "next_page" in data  # Pagination required
```

#### **Elevation of Privilege**
```python
class TestPrivilegeEscalation:
    """Test protection against privilege escalation"""
    
    def test_horizontal_privilege_escalation(self):
        """Verify users cannot access other users' data"""
        # Create two users
        user_a = self.create_test_user("user_a")
        user_b = self.create_test_user("user_b")
        
        # User A attempts to access User B's data
        token_a = self.authenticate_user(user_a)
        response = self.api_client.get(f"/api/v2/users/{user_b.id}/profile",
                                     headers={"Authorization": f"Bearer {token_a}"})
        
        # Should be forbidden
        assert response.status_code == 403
    
    def test_vertical_privilege_escalation(self):
        """Verify users cannot escalate to admin privileges"""
        # Create regular user
        user = self.create_test_user(role="user")
        token = self.authenticate_user(user)
        
        # Attempt to access admin endpoint
        response = self.api_client.get("/api/v2/admin/system-config",
                                     headers={"Authorization": f"Bearer {token}"})
        
        # Should be forbidden
        assert response.status_code == 403
        
        # Attempt to modify own role
        response = self.api_client.patch(f"/api/v2/users/{user.id}",
                                       json={"role": "admin"},
                                       headers={"Authorization": f"Bearer {token}"})
        
        # Should be forbidden
        assert response.status_code == 403
```

##  Authentication & Authorization Testing

### **Multi-Factor Authentication (MFA) Testing**
```python
class TestMFAImplementation:
    """Test Multi-Factor Authentication implementation"""
    
    def test_mfa_enrollment_flow(self):
        """Test MFA enrollment process"""
        user = self.create_test_user()
        
        # Step 1: Initiate MFA enrollment
        response = self.api_client.post("/api/v2/auth/mfa/enroll",
                                      json={"method": "totp"})
        assert response.status_code == 200
        
        enrollment_data = response.json()
        assert "qr_code" in enrollment_data
        assert "backup_codes" in enrollment_data
        
        # Step 2: Verify MFA setup
        totp_code = self.generate_totp_code(enrollment_data["secret"])
        response = self.api_client.post("/api/v2/auth/mfa/verify",
                                      json={"code": totp_code})
        assert response.status_code == 200
    
    def test_mfa_login_flow(self):
        """Test MFA-enabled login process"""
        user = self.create_mfa_enabled_user()
        
        # Step 1: Primary authentication
        response = self.api_client.post("/api/v2/auth/login",
                                      json={"username": user.username, "password": "password"})
        assert response.status_code == 200
        
        login_data = response.json()
        assert login_data["mfa_required"] == True
        assert "mfa_token" in login_data
        
        # Step 2: MFA verification
        totp_code = self.generate_totp_code(user.mfa_secret)
        response = self.api_client.post("/api/v2/auth/mfa/authenticate",
                                      json={"mfa_token": login_data["mfa_token"], "code": totp_code})
        assert response.status_code == 200
        
        auth_data = response.json()
        assert "access_token" in auth_data
    
    def test_mfa_bypass_attempts(self):
        """Test that MFA cannot be bypassed"""
        user = self.create_mfa_enabled_user()
        
        # Attempt to access protected resource without MFA
        partial_token = self.get_partial_auth_token(user)
        response = self.api_client.get("/api/v2/profile",
                                     headers={"Authorization": f"Bearer {partial_token}"})
        
        # Should require MFA completion
        assert response.status_code == 401
        assert "mfa_required" in response.json()["error"]
```

### **Role-Based Access Control (RBAC) Testing**
```python
class TestRBACImplementation:
    """Test Role-Based Access Control"""
    
    def test_role_hierarchy(self):
        """Test role hierarchy enforcement"""
        # Create users with different roles
        admin = self.create_test_user(role="admin")
        manager = self.create_test_user(role="manager")
        user = self.create_test_user(role="user")
        
        # Test admin access
        admin_token = self.authenticate_user(admin)
        response = self.api_client.get("/api/v2/admin/users",
                                     headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        
        # Test manager access (should have limited admin access)
        manager_token = self.authenticate_user(manager)
        response = self.api_client.get("/api/v2/admin/users",
                                     headers={"Authorization": f"Bearer {manager_token}"})
        assert response.status_code == 403  # Or 200 with filtered results
        
        # Test user access (should be denied)
        user_token = self.authenticate_user(user)
        response = self.api_client.get("/api/v2/admin/users",
                                     headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 403
    
    def test_resource_based_permissions(self):
        """Test resource-based permission enforcement"""
        # Create users in different departments
        hr_user = self.create_test_user(department="HR", role="user")
        eng_user = self.create_test_user(department="Engineering", role="user")
        
        # Create department-specific resources
        hr_document = self.create_document(department="HR", classification="confidential")
        eng_document = self.create_document(department="Engineering", classification="internal")
        
        # Test HR user access
        hr_token = self.authenticate_user(hr_user)
        response = self.api_client.get(f"/api/v2/documents/{hr_document.id}",
                                     headers={"Authorization": f"Bearer {hr_token}"})
        assert response.status_code == 200
        
        # HR user should not access Engineering documents
        response = self.api_client.get(f"/api/v2/documents/{eng_document.id}",
                                     headers={"Authorization": f"Bearer {hr_token}"})
        assert response.status_code == 403
```

##  Data Protection Testing

### **Encryption Testing**
```python
class TestEncryptionImplementation:
    """Test data encryption at rest and in transit"""
    
    def test_encryption_at_rest(self):
        """Verify sensitive data is encrypted in database"""
        # Store sensitive data
        user_data = {
            "username": "test_user",
            "ssn": "123-45-6789",
            "credit_card": "4111-1111-1111-1111"
        }
        
        user = self.create_user(user_data)
        
        # Check database directly (raw data should be encrypted)
        raw_user_data = self.db.execute("SELECT * FROM users WHERE id = ?", (user.id,)).fetchone()
        
        # SSN and credit card should be encrypted
        assert raw_user_data["ssn"] != "123-45-6789"
        assert raw_user_data["credit_card"] != "4111-1111-1111-1111"
        assert len(raw_user_data["ssn"]) > 20  # Encrypted data is longer
    
    def test_encryption_in_transit(self):
        """Verify data is encrypted in transit"""
        # Test TLS configuration
        response = requests.get("https://api.netskope.com/api/v2/health")
        
        # Verify TLS version and cipher
        assert response.raw.version >= 11  # TLS 1.1 minimum
        
        # Test that HTTP is redirected to HTTPS
        http_response = requests.get("http://api.netskope.com/api/v2/health", allow_redirects=False)
        assert http_response.status_code in [301, 302, 308]
        assert "https://" in http_response.headers.get("Location", "")
    
    def test_key_rotation(self):
        """Test encryption key rotation"""
        # Create data with current key
        original_data = "sensitive information"
        encrypted_data = self.encryption_service.encrypt(original_data)
        
        # Rotate encryption key
        self.encryption_service.rotate_key()
        
        # Verify old data can still be decrypted
        decrypted_data = self.encryption_service.decrypt(encrypted_data)
        assert decrypted_data == original_data
        
        # Verify new data uses new key
        new_encrypted_data = self.encryption_service.encrypt(original_data)
        assert new_encrypted_data != encrypted_data  # Different ciphertext
```

### **Data Masking and Anonymization Testing**
```python
class TestDataMasking:
    """Test data masking and anonymization"""
    
    def test_pii_masking_in_logs(self):
        """Verify PII is masked in application logs"""
        # Perform action that logs user data
        user = self.create_test_user(ssn="123-45-6789", email="test@example.com")
        
        # Trigger logging
        self.api_client.get(f"/api/v2/users/{user.id}")
        
        # Check log files
        log_content = self.get_application_logs()
        
        # PII should be masked in logs
        assert "123-45-6789" not in log_content
        assert "test@example.com" not in log_content
        assert "***-**-6789" in log_content or "[MASKED]" in log_content
    
    def test_data_export_anonymization(self):
        """Test data export anonymization"""
        # Create user with sensitive data
        user = self.create_test_user(
            name="John Doe",
            ssn="123-45-6789",
            email="john.doe@company.com"
        )
        
        # Export user data for analytics
        export_data = self.data_service.export_user_data(user.id, anonymize=True)
        
        # Verify data is anonymized
        assert export_data["name"] != "John Doe"
        assert export_data["ssn"] == "***-**-6789"
        assert export_data["email"] != "john.doe@company.com"
        assert "@" in export_data["email"]  # Email format preserved
```

##  Security Monitoring and Incident Response Testing

### **Threat Detection Testing**
```python
class TestThreatDetection:
    """Test security monitoring and threat detection"""
    
    def test_brute_force_detection(self):
        """Test brute force attack detection"""
        user = self.create_test_user()
        
        # Simulate brute force attack
        for i in range(10):
            response = self.api_client.post("/api/v2/auth/login",
                                          json={"username": user.username, "password": "wrong_password"})
            assert response.status_code == 401
        
        # Account should be locked after multiple failures
        response = self.api_client.post("/api/v2/auth/login",
                                      json={"username": user.username, "password": user.password})
        assert response.status_code == 423  # Account locked
        
        # Security alert should be generated
        alerts = self.get_security_alerts(user_id=user.id)
        assert len(alerts) > 0
        assert alerts[0]["type"] == "brute_force_attempt"
    
    def test_anomaly_detection(self):
        """Test behavioral anomaly detection"""
        user = self.create_test_user()
        
        # Establish normal behavior pattern
        for _ in range(30):
            self.simulate_normal_user_activity(user)
        
        # Simulate anomalous behavior
        self.simulate_anomalous_activity(user, activity_type="mass_data_download")
        
        # Anomaly should be detected
        anomalies = self.get_anomaly_alerts(user_id=user.id)
        assert len(anomalies) > 0
        assert anomalies[0]["type"] == "unusual_data_access"
    
    def test_insider_threat_detection(self):
        """Test insider threat detection"""
        # Create privileged user
        admin_user = self.create_test_user(role="admin")
        
        # Simulate suspicious admin behavior
        self.simulate_suspicious_admin_activity(admin_user, [
            "access_user_passwords",
            "bulk_user_export",
            "disable_audit_logging"
        ])
        
        # Insider threat alert should be generated
        threats = self.get_insider_threat_alerts(user_id=admin_user.id)
        assert len(threats) > 0
        assert threats[0]["severity"] == "high"
```

### **Incident Response Testing**
```python
class TestIncidentResponse:
    """Test incident response procedures"""
    
    def test_security_incident_workflow(self):
        """Test complete security incident workflow"""
        # Step 1: Trigger security incident
        user = self.create_test_user()
        self.simulate_security_breach(user, breach_type="data_exfiltration")
        
        # Step 2: Verify incident detection
        incidents = self.get_security_incidents(user_id=user.id)
        assert len(incidents) > 0
        
        incident = incidents[0]
        assert incident["status"] == "detected"
        assert incident["severity"] in ["high", "critical"]
        
        # Step 3: Test incident escalation
        self.incident_service.escalate_incident(incident.id)
        
        updated_incident = self.get_security_incident(incident.id)
        assert updated_incident["status"] == "escalated"
        assert updated_incident["assigned_to"] is not None
        
        # Step 4: Test containment actions
        containment_actions = self.incident_service.get_containment_actions(incident.id)
        assert "disable_user_account" in containment_actions
        assert "isolate_affected_systems" in containment_actions
        
        # Step 5: Test incident resolution
        self.incident_service.resolve_incident(incident.id, resolution="contained")
        
        resolved_incident = self.get_security_incident(incident.id)
        assert resolved_incident["status"] == "resolved"
        assert resolved_incident["resolution_time"] is not None
    
    def test_automated_response_actions(self):
        """Test automated incident response actions"""
        user = self.create_test_user()
        
        # Trigger high-severity incident
        self.simulate_security_breach(user, breach_type="privilege_escalation", severity="critical")
        
        # Wait for automated response
        time.sleep(5)
        
        # Verify automated actions were taken
        user_status = self.get_user_status(user.id)
        assert user_status["account_locked"] == True
        
        # Verify notifications were sent
        notifications = self.get_incident_notifications()
        assert len(notifications) > 0
        assert any("critical security incident" in n["message"] for n in notifications)
```

##  Compliance Testing

### **SOC 2 Type II Controls Testing**
```python
class TestSOC2Compliance:
    """Test SOC 2 Type II controls"""
    
    def test_cc6_1_logical_access_controls(self):
        """CC6.1: Logical and physical access controls"""
        # Test user provisioning process
        new_user_request = {
            "username": "new_employee",
            "department": "Engineering",
            "role": "developer",
            "manager_approval": True
        }
        
        # User creation should require approval
        response = self.api_client.post("/api/v2/admin/users", json=new_user_request)
        assert response.status_code == 202  # Accepted for approval
        
        # Verify approval workflow
        pending_requests = self.get_pending_user_requests()
        assert len(pending_requests) > 0
        
        # Approve request
        self.approve_user_request(pending_requests[0]["id"])
        
        # Verify user is created with correct permissions
        created_user = self.get_user_by_username("new_employee")
        assert created_user["role"] == "developer"
        assert created_user["status"] == "active"
    
    def test_cc6_2_access_termination(self):
        """CC6.2: Access termination procedures"""
        # Create active user
        user = self.create_test_user(status="active")
        
        # Simulate employee termination
        termination_request = {
            "user_id": user.id,
            "termination_date": datetime.now().isoformat(),
            "reason": "employment_ended"
        }
        
        response = self.api_client.post("/api/v2/admin/users/terminate", json=termination_request)
        assert response.status_code == 200
        
        # Verify immediate access revocation
        user_token = self.get_user_token(user.id)
        response = self.api_client.get("/api/v2/profile",
                                     headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 401
        
        # Verify audit trail
        audit_logs = self.get_audit_logs(user_id=user.id, action="account_terminated")
        assert len(audit_logs) > 0
    
    def test_cc7_1_system_monitoring(self):
        """CC7.1: System monitoring controls"""
        # Perform monitored actions
        user = self.create_test_user()
        
        actions = [
            ("login", "/api/v2/auth/login"),
            ("data_access", "/api/v2/sensitive-data"),
            ("configuration_change", "/api/v2/admin/config")
        ]
        
        for action_type, endpoint in actions:
            response = self.api_client.get(endpoint)
            
            # Verify monitoring logs
            monitoring_logs = self.get_monitoring_logs(action=action_type)
            assert len(monitoring_logs) > 0
            
            log_entry = monitoring_logs[-1]  # Most recent
            assert log_entry["user_id"] == user.id
            assert log_entry["endpoint"] == endpoint
            assert log_entry["timestamp"] is not None
```

### **GDPR Compliance Testing**
```python
class TestGDPRCompliance:
    """Test GDPR compliance requirements"""
    
    def test_article_17_right_to_erasure(self):
        """Article 17: Right to erasure (right to be forgotten)"""
        # Create user with personal data
        user = self.create_test_user_with_personal_data()
        
        # User requests data deletion
        deletion_request = {
            "user_id": user.id,
            "request_type": "erasure",
            "reason": "withdrawal_of_consent"
        }
        
        response = self.api_client.post("/api/v2/gdpr/erasure-request", json=deletion_request)
        assert response.status_code == 202  # Accepted for processing
        
        # Process deletion request
        self.process_gdpr_requests()
        
        # Verify complete data removal
        assert self.get_user(user.id) is None
        assert self.get_user_events(user.id) == []
        assert self.get_user_logs(user.id) == []
        
        # Verify deletion audit trail
        deletion_logs = self.get_gdpr_audit_logs(request_type="erasure", user_id=user.id)
        assert len(deletion_logs) > 0
    
    def test_article_20_data_portability(self):
        """Article 20: Right to data portability"""
        user = self.create_test_user_with_personal_data()
        
        # User requests data export
        export_request = {
            "user_id": user.id,
            "request_type": "portability",
            "format": "json"
        }
        
        response = self.api_client.post("/api/v2/gdpr/export-request", json=export_request)
        assert response.status_code == 202
        
        # Process export request
        self.process_gdpr_requests()
        
        # Verify export completeness
        export_data = self.get_gdpr_export(user.id)
        
        required_data_categories = [
            "personal_information",
            "account_data",
            "activity_logs",
            "preferences",
            "consent_records"
        ]
        
        for category in required_data_categories:
            assert category in export_data
            assert export_data[category] is not None
    
    def test_article_25_data_protection_by_design(self):
        """Article 25: Data protection by design and by default"""
        # Test default privacy settings for new users
        user = self.create_test_user()
        
        privacy_settings = self.get_user_privacy_settings(user.id)
        
        # Verify privacy-friendly defaults
        assert privacy_settings["data_sharing_enabled"] == False
        assert privacy_settings["marketing_emails_enabled"] == False
        assert privacy_settings["analytics_tracking_enabled"] == False
        assert privacy_settings["data_retention_period"] == "minimum_required"
```

##  Security Testing Tools Integration

### **Static Application Security Testing (SAST)**
```python
# scripts/security_scans.py
import subprocess
import json

class SecurityScanner:
    def run_bandit_scan(self):
        """Run Bandit SAST scan"""
        result = subprocess.run([
            "bandit", "-r", ".", "-f", "json", "-o", "reports/bandit-report.json"
        ], capture_output=True, text=True)
        
        with open("reports/bandit-report.json", "r") as f:
            report = json.load(f)
        
        # Fail if high or medium severity issues found
        high_issues = [issue for issue in report["results"] if issue["issue_severity"] == "HIGH"]
        medium_issues = [issue for issue in report["results"] if issue["issue_severity"] == "MEDIUM"]
        
        assert len(high_issues) == 0, f"High severity security issues found: {len(high_issues)}"
        assert len(medium_issues) == 0, f"Medium severity security issues found: {len(medium_issues)}"
    
    def run_safety_scan(self):
        """Run Safety dependency vulnerability scan"""
        result = subprocess.run([
            "safety", "check", "--json", "--output", "reports/safety-report.json"
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            with open("reports/safety-report.json", "r") as f:
                vulnerabilities = json.load(f)
            
            critical_vulns = [v for v in vulnerabilities if v.get("severity") == "critical"]
            assert len(critical_vulns) == 0, f"Critical vulnerabilities found: {len(critical_vulns)}"
```

### **Dynamic Application Security Testing (DAST)**
```python
class DynamicSecurityTesting:
    def test_sql_injection_protection(self):
        """Test SQL injection protection"""
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "'; INSERT INTO users (username) VALUES ('hacker'); --",
            "' UNION SELECT password FROM users WHERE '1'='1"
        ]
        
        for payload in sql_payloads:
            response = self.api_client.get(f"/api/v2/search?query={payload}")
            
            # Should not return 500 error (indicates SQL error)
            assert response.status_code != 500
            
            # Should return error or empty results
            assert response.status_code in [400, 422] or response.json().get("results", []) == []
    
    def test_xss_protection(self):
        """Test Cross-Site Scripting (XSS) protection"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//"
        ]
        
        for payload in xss_payloads:
            # Test in various input fields
            response = self.api_client.post("/api/v2/users", json={
                "username": payload,
                "email": f"test{payload}@example.com"
            })
            
            # Payload should be sanitized or rejected
            if response.status_code == 200:
                user_data = response.json()
                assert "<script>" not in user_data.get("username", "")
                assert "javascript:" not in user_data.get("username", "")
```

##  Security Metrics and Reporting

### **Security Test Metrics**
```python
class SecurityMetricsCollector:
    def collect_security_test_metrics(self):
        """Collect comprehensive security test metrics"""
        metrics = {
            "vulnerability_tests": {
                "total_tests": self.count_vulnerability_tests(),
                "passed_tests": self.count_passed_vulnerability_tests(),
                "failed_tests": self.count_failed_vulnerability_tests(),
                "coverage_percentage": self.calculate_vulnerability_coverage()
            },
            "compliance_tests": {
                "soc2_controls_tested": self.count_soc2_tests(),
                "gdpr_requirements_tested": self.count_gdpr_tests(),
                "pci_controls_tested": self.count_pci_tests(),
                "compliance_score": self.calculate_compliance_score()
            },
            "security_incidents": {
                "incidents_detected": self.count_detected_incidents(),
                "false_positives": self.count_false_positives(),
                "mean_detection_time": self.calculate_mean_detection_time(),
                "mean_response_time": self.calculate_mean_response_time()
            }
        }
        
        return metrics
    
    def generate_security_report(self):
        """Generate comprehensive security test report"""
        metrics = self.collect_security_test_metrics()
        
        report = {
            "report_date": datetime.now().isoformat(),
            "security_posture": self.assess_security_posture(metrics),
            "risk_assessment": self.perform_risk_assessment(metrics),
            "recommendations": self.generate_recommendations(metrics),
            "metrics": metrics
        }
        
        # Save report
        with open(f"reports/security-report-{datetime.now().strftime('%Y%m%d')}.json", "w") as f:
            json.dump(report, f, indent=2)
        
        return report
```

##  Security Testing Best Practices

### **Test Data Security**
- Use synthetic data for security testing
- Never use production credentials in tests
- Implement secure test data cleanup
- Encrypt sensitive test data at rest

### **Test Environment Security**
- Isolate security test environments
- Use dedicated security testing infrastructure
- Implement network segmentation
- Monitor test environment access

### **Continuous Security Testing**
- Integrate security tests in CI/CD pipeline
- Automate security regression testing
- Implement security test result monitoring
- Maintain security test coverage metrics

### **Incident Response Testing**
- Regularly test incident response procedures
- Simulate realistic attack scenarios
- Validate automated response systems
- Test communication and escalation procedures

##  Mock Client Security Validation

The Day-1 Test Framework's mock clients include built-in security validation that mimics production behavior:

### Running Security Tests with Mocks

```bash
# Run all security tests with mock environment (no external dependencies required)
TESTING_MODE=mock pytest tests/security/ -v

# Run specific security test categories
TESTING_MODE=mock pytest tests/security/test_api_security.py -v
TESTING_MODE=mock pytest tests/security/test_data_security.py -v
```

### Mock Security Behavior

The mock implementations validate security in `TESTING_MODE=mock`:

| Security Test | Mock Behavior | Expected Response |
|--------------|--------------|-----------------|
| SQL Injection | Detects SQL patterns in params/body | `{"status": "error", "error": "Potential SQL injection..."}` |
| Invalid Credentials | Validates against mock users | Returns `False` |
| Weak Passwords | Rejects common weak passwords | Returns `False` |
| Privilege Escalation | Admin endpoints require admin role | `{"status": "error", "error": "Unauthorized"}` |
| Rate Limiting | Returns rate limit headers | `X-RateLimit-Limit`, `X-RateLimit-Remaining` |
| Password Hashing | SHA-256 hashes on insert | Stored value differs from plaintext |

### Password Hash Implementation

When `MockDatabaseClient.insert_one()` is called with sensitive fields, they are automatically hashed:

```python
from src.service_manager import ServiceManager

manager = ServiceManager()
db = manager.get_database_client()

# Password is automatically hashed before storage
doc_id = db.insert_one("users", {"username": "test", "password": "plaintext"})
doc = db.find_one("users", {"username": "test"})

# Stored password is hashed, not plaintext
assert doc["password"] != "plaintext"  # True: it's a SHA-256 hash
```

This comprehensive security testing guide ensures robust security validation across all aspects of the Netskope SDET Framework, from basic authentication to advanced threat detection and compliance requirements.