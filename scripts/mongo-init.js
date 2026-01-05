// MongoDB Initialization Script for Day-1 Framework

// Switch to the netskope_local database
db = db.getSiblingDB('netskope_local');

// Create application user with appropriate permissions
db.createUser({
  user: 'netskope_app',
  pwd: 'netskope_app_2024',
  roles: [
    {
      role: 'readWrite',
      db: 'netskope_local'
    }
  ]
});

// Create collections with validation schemas
db.createCollection('users', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['username', 'email', 'created_at'],
      properties: {
        username: {
          bsonType: 'string',
          description: 'Username must be a string and is required'
        },
        email: {
          bsonType: 'string',
          pattern: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
          description: 'Email must be a valid email address'
        },
        role: {
          bsonType: 'string',
          enum: ['admin', 'manager', 'user'],
          description: 'Role must be one of: admin, manager, user'
        },
        department: {
          bsonType: 'string',
          description: 'Department name'
        },
        risk_score: {
          bsonType: 'int',
          minimum: 0,
          maximum: 100,
          description: 'Risk score must be between 0 and 100'
        },
        created_at: {
          bsonType: 'date',
          description: 'Creation timestamp is required'
        },
        updated_at: {
          bsonType: 'date',
          description: 'Last update timestamp'
        }
      }
    }
  }
});

db.createCollection('security_events', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['event_type', 'user_id', 'timestamp', 'source_ip'],
      properties: {
        event_type: {
          bsonType: 'string',
          enum: ['login', 'logout', 'file_access', 'api_call', 'policy_violation', 'security_alert'],
          description: 'Event type must be one of the predefined types'
        },
        user_id: {
          bsonType: 'string',
          description: 'User ID is required'
        },
        source_ip: {
          bsonType: 'string',
          description: 'Source IP address'
        },
        user_agent: {
          bsonType: 'string',
          description: 'User agent string'
        },
        severity: {
          bsonType: 'string',
          enum: ['low', 'medium', 'high', 'critical'],
          description: 'Severity level'
        },
        risk_score: {
          bsonType: 'int',
          minimum: 0,
          maximum: 100,
          description: 'Risk score between 0 and 100'
        },
        timestamp: {
          bsonType: 'date',
          description: 'Event timestamp is required'
        },
        metadata: {
          bsonType: 'object',
          description: 'Additional event metadata'
        }
      }
    }
  }
});

db.createCollection('policies', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['name', 'type', 'enabled', 'created_at'],
      properties: {
        name: {
          bsonType: 'string',
          description: 'Policy name is required'
        },
        type: {
          bsonType: 'string',
          enum: ['dlp', 'swg', 'ztna', 'firewall'],
          description: 'Policy type must be one of: dlp, swg, ztna, firewall'
        },
        enabled: {
          bsonType: 'bool',
          description: 'Policy enabled status'
        },
        rules: {
          bsonType: 'array',
          description: 'Policy rules array'
        },
        priority: {
          bsonType: 'int',
          minimum: 1,
          maximum: 1000,
          description: 'Policy priority (1-1000)'
        },
        created_at: {
          bsonType: 'date',
          description: 'Creation timestamp is required'
        },
        updated_at: {
          bsonType: 'date',
          description: 'Last update timestamp'
        }
      }
    }
  }
});

db.createCollection('audit_logs', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['action', 'user_id', 'timestamp', 'resource'],
      properties: {
        action: {
          bsonType: 'string',
          description: 'Action performed'
        },
        user_id: {
          bsonType: 'string',
          description: 'User who performed the action'
        },
        resource: {
          bsonType: 'string',
          description: 'Resource that was accessed'
        },
        result: {
          bsonType: 'string',
          enum: ['success', 'failure', 'denied'],
          description: 'Action result'
        },
        timestamp: {
          bsonType: 'date',
          description: 'Action timestamp is required'
        },
        details: {
          bsonType: 'object',
          description: 'Additional action details'
        }
      }
    }
  }
});

// Create indexes for better performance
db.users.createIndex({ 'username': 1 }, { unique: true });
db.users.createIndex({ 'email': 1 }, { unique: true });
db.users.createIndex({ 'department': 1 });
db.users.createIndex({ 'role': 1 });
db.users.createIndex({ 'created_at': 1 });

db.security_events.createIndex({ 'user_id': 1 });
db.security_events.createIndex({ 'event_type': 1 });
db.security_events.createIndex({ 'timestamp': -1 });
db.security_events.createIndex({ 'severity': 1 });
db.security_events.createIndex({ 'source_ip': 1 });

db.policies.createIndex({ 'name': 1 }, { unique: true });
db.policies.createIndex({ 'type': 1 });
db.policies.createIndex({ 'enabled': 1 });
db.policies.createIndex({ 'priority': 1 });

db.audit_logs.createIndex({ 'user_id': 1 });
db.audit_logs.createIndex({ 'action': 1 });
db.audit_logs.createIndex({ 'timestamp': -1 });
db.audit_logs.createIndex({ 'resource': 1 });

// Insert sample data for testing
db.users.insertMany([
  {
    username: 'admin_user',
    email: 'admin@netskope.local',
    role: 'admin',
    department: 'IT',
    risk_score: 10,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    username: 'test_user',
    email: 'test@netskope.local',
    role: 'user',
    department: 'Engineering',
    risk_score: 25,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    username: 'manager_user',
    email: 'manager@netskope.local',
    role: 'manager',
    department: 'Sales',
    risk_score: 15,
    created_at: new Date(),
    updated_at: new Date()
  }
]);

db.policies.insertMany([
  {
    name: 'DLP - Sensitive Data Protection',
    type: 'dlp',
    enabled: true,
    rules: [
      { pattern: 'SSN', action: 'block' },
      { pattern: 'Credit Card', action: 'alert' }
    ],
    priority: 100,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    name: 'SWG - Social Media Block',
    type: 'swg',
    enabled: true,
    rules: [
      { category: 'social_media', action: 'block' },
      { category: 'entertainment', action: 'warn' }
    ],
    priority: 200,
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    name: 'ZTNA - Admin Access',
    type: 'ztna',
    enabled: true,
    rules: [
      { application: 'admin_portal', required_role: 'admin' },
      { application: 'user_portal', required_role: 'user' }
    ],
    priority: 50,
    created_at: new Date(),
    updated_at: new Date()
  }
]);

// Create TTL index for security events (auto-delete after 90 days)
db.security_events.createIndex(
  { 'timestamp': 1 },
  { expireAfterSeconds: 7776000 }  // 90 days
);

// Create TTL index for audit logs (auto-delete after 7 years for compliance)
db.audit_logs.createIndex(
  { 'timestamp': 1 },
  { expireAfterSeconds: 220752000 }  // 7 years
);

print('MongoDB initialization completed successfully!');
print('Created collections: users, security_events, policies, audit_logs');
print('Created indexes for performance optimization');
print('Inserted sample data for testing');
print('Configured TTL indexes for data retention compliance');