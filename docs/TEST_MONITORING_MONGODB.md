# Test Monitoring with MongoDB - Complete Guide

## 📊 Overview

The Day-1 Framework includes automatic test result logging to MongoDB for comprehensive test monitoring, analytics, and reporting. This guide covers how to use, configure, and analyze test data stored in MongoDB.

## 🚀 Quick Start

### **Automatic Test Logging**
Test results are automatically logged to MongoDB when you run pytest - no additional configuration needed!

```bash
# Start MongoDB service
docker-compose -f docker-compose.local.yml up -d mongodb

# Run tests (automatically logs to MongoDB)
pytest tests/ -v

# View logged results
mongosh "mongodb://admin:netskope_admin_2024@localhost:27017/netskope_local?authSource=admin"
```

### **What Gets Logged Automatically**
- ✅ **Test execution results** (pass/fail/skip)
- ⏱️ **Test duration and timing**
- 🔍 **Error messages and stack traces**
- 📊 **Session summaries and statistics**
- 🌍 **Environment and metadata**
- 📈 **Performance metrics**

---

## 🔧 How It Works

### **Automatic Integration**
The framework uses pytest hooks to automatically capture and log test data:

```python
# Configured in pytest.ini
plugins = 
    src.test_result_logger

# Automatic hooks capture:
# - Test start/end times
# - Results and errors
# - Session statistics
# - Environment context
```

### **Database Collections**

#### **1. test_results Collection**
Stores individual test execution data:
```javascript
{
  "_id": ObjectId("..."),
  "session_id": "test_session_20241220_143022",
  "test_name": "test_api_authentication",
  "test_file": "tests/test_api.py",
  "test_class": "TestAuthentication",
  "environment": "local",
  "status": "passed",
  "start_time": ISODate("2024-12-20T14:30:22.123Z"),
  "end_time": ISODate("2024-12-20T14:30:23.456Z"),
  "duration": 1.333,
  "error_message": null,
  "error_type": null,
  "traceback": null,
  "test_output": "Test passed successfully",
  "metadata": {
    "python_version": "3.11.5",
    "environment_vars": {
      "TESTING_MODE": "local",
      "CI": "false"
    }
  },
  "additional_data": {}
}
```

#### **2. test_sessions Collection**
Stores test session summaries:
```javascript
{
  "_id": ObjectId("..."),
  "session_id": "test_session_20241220_143022",
  "document_type": "session_summary",
  "environment": "local",
  "timestamp": ISODate("2024-12-20T14:35:45.789Z"),
  "total_tests": 25,
  "passed": 23,
  "failed": 2,
  "skipped": 0,
  "success_rate": 92.0,
  "total_duration": 45.67,
  "avg_test_duration": 1.83
}
```

---

## 📊 MongoDB Access Methods

### **1. Command Line Access (Recommended)**
```bash
# Connect via Docker (recommended)
docker-compose -f docker-compose.local.yml exec mongodb mongosh -u admin -p netskope_admin_2024 --authenticationDatabase admin netskope_local

# Or connect directly
mongosh "mongodb://admin:netskope_admin_2024@localhost:27017/netskope_local?authSource=admin"
```

### **2. GUI Tools**
```bash
# MongoDB Compass (Official GUI)
# Connection string: 
mongodb://admin:netskope_admin_2024@localhost:27017/netskope_local?authSource=admin

# Other popular tools:
# - Studio 3T: https://studio3t.com/
# - Robo 3T: https://robomongo.org/
# - NoSQLBooster: https://nosqlbooster.com/
```

### **3. Python Integration**
```python
from src.service_manager import get_database_client

# Get database client
db_client = get_database_client()

# Query test results
results = db_client.find("test_results", {"status": "failed"})
for result in results:
    print(f"Failed test: {result['test_name']} - {result['error_message']}")
```

---

## 🔍 Test Data Analysis

### **Basic Queries**

#### **View Recent Test Results**
```javascript
// Connect to database
use netskope_local

// Show all collections
show collections

// Recent test results (last 10)
db.test_results.find().sort({start_time: -1}).limit(10)

// Recent failed tests
db.test_results.find({status: "failed"}).sort({start_time: -1}).limit(5)

// Tests from specific session
db.test_results.find({session_id: "test_session_20241220_143022"})
```

#### **Session Statistics**
```javascript
// All test sessions
db.test_sessions.find().sort({timestamp: -1})

// Sessions with low success rate
db.test_sessions.find({success_rate: {$lt: 90}}).sort({timestamp: -1})

// Average success rate over time
db.test_sessions.aggregate([
  {$group: {
    _id: null,
    avg_success_rate: {$avg: "$success_rate"},
    total_sessions: {$sum: 1}
  }}
])
```

### **Advanced Analytics**

#### **Test Performance Analysis**
```javascript
// Average test duration by test name
db.test_results.aggregate([
  {$group: {
    _id: "$test_name",
    avg_duration: {$avg: "$duration"},
    count: {$sum: 1},
    success_rate: {
      $avg: {$cond: [{$eq: ["$status", "passed"]}, 1, 0]}
    }
  }},
  {$sort: {avg_duration: -1}}
])

// Slowest tests
db.test_results.find({}, {test_name: 1, duration: 1, test_file: 1})
  .sort({duration: -1}).limit(10)

// Performance trends over time
db.test_results.aggregate([
  {$match: {
    start_time: {$gte: new Date(Date.now() - 7*24*60*60*1000)} // Last 7 days
  }},
  {$group: {
    _id: {
      date: {$dateToString: {format: "%Y-%m-%d", date: "$start_time"}},
      test_name: "$test_name"
    },
    avg_duration: {$avg: "$duration"},
    count: {$sum: 1}
  }},
  {$sort: {"_id.date": 1, "_id.test_name": 1}}
])
```

#### **Error Analysis**
```javascript
// Most common errors
db.test_results.aggregate([
  {$match: {status: "failed"}},
  {$group: {
    _id: "$error_type",
    count: {$sum: 1},
    tests: {$addToSet: "$test_name"}
  }},
  {$sort: {count: -1}}
])

// Error trends by day
db.test_results.aggregate([
  {$match: {
    status: "failed",
    start_time: {$gte: new Date(Date.now() - 30*24*60*60*1000)} // Last 30 days
  }},
  {$group: {
    _id: {$dateToString: {format: "%Y-%m-%d", date: "$start_time"}},
    error_count: {$sum: 1},
    unique_errors: {$addToSet: "$error_type"}
  }},
  {$sort: {_id: 1}}
])

// Tests that fail most frequently
db.test_results.aggregate([
  {$group: {
    _id: "$test_name",
    total_runs: {$sum: 1},
    failures: {$sum: {$cond: [{$eq: ["$status", "failed"]}, 1, 0]}},
    failure_rate: {
      $avg: {$cond: [{$eq: ["$status", "failed"]}, 1, 0]}
    }
  }},
  {$match: {failure_rate: {$gt: 0}}},
  {$sort: {failure_rate: -1}}
])
```

#### **Environment Comparison**
```javascript
// Success rates by environment
db.test_results.aggregate([
  {$group: {
    _id: "$environment",
    total_tests: {$sum: 1},
    passed: {$sum: {$cond: [{$eq: ["$status", "passed"]}, 1, 0]}},
    failed: {$sum: {$cond: [{$eq: ["$status", "failed"]}, 1, 0]}},
    success_rate: {
      $avg: {$cond: [{$eq: ["$status", "passed"]}, 1, 0]}
    }
  }},
  {$sort: {success_rate: -1}}
])

// Performance by environment
db.test_results.aggregate([
  {$group: {
    _id: "$environment",
    avg_duration: {$avg: "$duration"},
    min_duration: {$min: "$duration"},
    max_duration: {$max: "$duration"}
  }}
])
```

---

## 📈 Real-Time Monitoring

### **Live Test Monitoring**
```javascript
// Watch for new test results (MongoDB 4.0+)
db.test_results.watch([
  {$match: {"fullDocument.status": "failed"}}
])

// Monitor current test session
var currentSession = db.test_sessions.findOne({}, {session_id: 1}, {sort: {timestamp: -1}})
db.test_results.find({session_id: currentSession.session_id}).sort({start_time: -1})

// Real-time failure rate
setInterval(function() {
  var stats = db.test_results.aggregate([
    {$match: {
      start_time: {$gte: new Date(Date.now() - 60*60*1000)} // Last hour
    }},
    {$group: {
      _id: null,
      total: {$sum: 1},
      failed: {$sum: {$cond: [{$eq: ["$status", "failed"]}, 1, 0]}}
    }}
  ]).toArray()[0];
  
  if (stats) {
    print("Failure rate (last hour): " + (stats.failed / stats.total * 100).toFixed(2) + "%");
  }
}, 30000); // Update every 30 seconds
```

### **Automated Alerts**
```python
# Python script for monitoring alerts
import time
from datetime import datetime, timedelta
from src.service_manager import get_database_client

def monitor_test_failures():
    db_client = get_database_client()
    
    while True:
        # Check for high failure rate in last 10 minutes
        ten_minutes_ago = datetime.now() - timedelta(minutes=10)
        
        recent_tests = list(db_client.find("test_results", {
            "start_time": {"$gte": ten_minutes_ago}
        }))
        
        if len(recent_tests) > 5:  # Only alert if we have enough data
            failed_tests = [t for t in recent_tests if t["status"] == "failed"]
            failure_rate = len(failed_tests) / len(recent_tests) * 100
            
            if failure_rate > 20:  # Alert if >20% failure rate
                print(f"🚨 HIGH FAILURE RATE ALERT: {failure_rate:.1f}% ({len(failed_tests)}/{len(recent_tests)} tests failed)")
                
                # Send notification (email, Slack, etc.)
                # send_alert_notification(failure_rate, failed_tests)
        
        time.sleep(60)  # Check every minute

# Run monitoring
if __name__ == "__main__":
    monitor_test_failures()
```

---

## 📊 Custom Dashboards and Reports

### **MongoDB Charts Integration**
```javascript
// Prepare data for MongoDB Charts
// 1. Test success rate over time
db.test_results.aggregate([
  {$group: {
    _id: {
      date: {$dateToString: {format: "%Y-%m-%d %H:00", date: "$start_time"}}
    },
    total_tests: {$sum: 1},
    passed_tests: {$sum: {$cond: [{$eq: ["$status", "passed"]}, 1, 0]}},
    success_rate: {$avg: {$cond: [{$eq: ["$status", "passed"]}, 1, 0]}}
  }},
  {$sort: {"_id.date": 1}}
])

// 2. Test duration distribution
db.test_results.aggregate([
  {$bucket: {
    groupBy: "$duration",
    boundaries: [0, 1, 2, 5, 10, 30, 60],
    default: "60+",
    output: {
      count: {$sum: 1},
      avg_duration: {$avg: "$duration"}
    }
  }}
])
```

### **Export Data for External Tools**
```python
# Export test data to CSV for analysis
import csv
from datetime import datetime, timedelta
from src.service_manager import get_database_client

def export_test_data_to_csv(days=7):
    db_client = get_database_client()
    
    # Get test data from last N days
    since_date = datetime.now() - timedelta(days=days)
    test_data = list(db_client.find("test_results", {
        "start_time": {"$gte": since_date}
    }))
    
    # Export to CSV
    with open(f'test_data_export_{datetime.now().strftime("%Y%m%d")}.csv', 'w', newline='') as csvfile:
        fieldnames = ['session_id', 'test_name', 'test_file', 'status', 'duration', 'start_time', 'error_type']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for test in test_data:
            writer.writerow({
                'session_id': test.get('session_id'),
                'test_name': test.get('test_name'),
                'test_file': test.get('test_file'),
                'status': test.get('status'),
                'duration': test.get('duration'),
                'start_time': test.get('start_time'),
                'error_type': test.get('error_type')
            })
    
    print(f"Exported {len(test_data)} test records to CSV")

# Usage
export_test_data_to_csv(30)  # Export last 30 days
```

### **Grafana Integration**
```python
# Create Grafana dashboard for MongoDB test data
# Install MongoDB datasource plugin in Grafana
# Configure datasource with connection: mongodb://admin:netskope_admin_2024@localhost:27017/netskope_local

# Example Grafana queries:
# 1. Test success rate over time
# 2. Average test duration
# 3. Most failing tests
# 4. Error distribution
```

---

## 🔧 Configuration and Customization

### **Custom Test Metadata**
```python
# Add custom metadata to test logging
import pytest
from src.test_result_logger import get_test_logger

def test_with_custom_metadata():
    logger = get_test_logger()
    
    # Add custom data to test result
    logger.log_test_result(
        test_name="test_custom_metadata",
        status="passed",
        duration=1.5,
        custom_field="custom_value",
        performance_metrics={
            "memory_usage": "45MB",
            "cpu_usage": "12%"
        },
        business_context={
            "feature": "authentication",
            "priority": "high"
        }
    )
```

### **Environment-Specific Configuration**
```python
# Customize logging based on environment
class TestResultLogger:
    def __init__(self):
        self.environment = get_current_environment().value
        
        # Environment-specific settings
        if self.environment == "production":
            self.collection_name = "prod_test_results"
            self.retention_days = 90
        elif self.environment == "staging":
            self.collection_name = "staging_test_results"
            self.retention_days = 30
        else:  # local/development
            self.collection_name = "test_results"
            self.retention_days = 7
```

### **Data Retention Management**
```javascript
// Set up automatic data cleanup
// Create TTL index for automatic deletion
db.test_results.createIndex(
  {"start_time": 1}, 
  {expireAfterSeconds: 2592000}  // 30 days
)

// Manual cleanup of old data
db.test_results.deleteMany({
  start_time: {$lt: new Date(Date.now() - 30*24*60*60*1000)}
})

// Archive old data before deletion
db.test_results.aggregate([
  {$match: {
    start_time: {$lt: new Date(Date.now() - 90*24*60*60*1000)}
  }},
  {$out: "test_results_archive"}
])
```

---

## 🚀 Advanced Use Cases

### **A/B Testing Analysis**
```javascript
// Compare test results between different versions
db.test_results.aggregate([
  {$match: {
    "metadata.version": {$in: ["v1.0", "v2.0"]}
  }},
  {$group: {
    _id: "$metadata.version",
    avg_duration: {$avg: "$duration"},
    success_rate: {$avg: {$cond: [{$eq: ["$status", "passed"]}, 1, 0]}},
    total_tests: {$sum: 1}
  }}
])
```

### **Performance Regression Detection**
```javascript
// Detect performance regressions
db.test_results.aggregate([
  {$match: {
    test_name: "test_api_response_time",
    start_time: {$gte: new Date(Date.now() - 14*24*60*60*1000)} // Last 2 weeks
  }},
  {$group: {
    _id: {$dateToString: {format: "%Y-%m-%d", date: "$start_time"}},
    avg_duration: {$avg: "$duration"},
    max_duration: {$max: "$duration"}
  }},
  {$sort: {"_id": 1}}
])
```

### **Flaky Test Detection**
```javascript
// Identify flaky tests (inconsistent results)
db.test_results.aggregate([
  {$group: {
    _id: "$test_name",
    total_runs: {$sum: 1},
    unique_results: {$addToSet: "$status"},
    failure_rate: {$avg: {$cond: [{$eq: ["$status", "failed"]}, 1, 0]}}
  }},
  {$match: {
    total_runs: {$gte: 5},  // At least 5 runs
    $expr: {$gt: [{$size: "$unique_results"}, 1]}  // Mixed results
  }},
  {$sort: {failure_rate: -1}}
])
```

---

## 🛠️ Troubleshooting

### **Common Issues**

#### **No Test Data in MongoDB**
```bash
# Check if test logger is enabled
grep -r "test_result_logger" pytest.ini

# Verify MongoDB connection
python -c "from src.service_manager import get_database_client; print(get_database_client().ping())"

# Check test execution with verbose logging
pytest tests/ -v -s --log-cli-level=DEBUG
```

#### **Connection Issues**
```bash
# Test MongoDB connectivity
docker-compose -f docker-compose.local.yml exec mongodb mongosh --eval "db.adminCommand('ping')"

# Check authentication
mongosh "mongodb://admin:netskope_admin_2024@localhost:27017/admin" --eval "db.runCommand({connectionStatus: 1})"

# Verify database and collections exist
mongosh "mongodb://admin:netskope_admin_2024@localhost:27017/netskope_local?authSource=admin" --eval "show collections"
```

#### **Performance Issues**
```javascript
// Check for missing indexes
db.test_results.getIndexes()

// Create performance indexes
db.test_results.createIndex({session_id: 1})
db.test_results.createIndex({test_name: 1})
db.test_results.createIndex({start_time: -1})
db.test_results.createIndex({status: 1, start_time: -1})

// Monitor slow queries
db.setProfilingLevel(2, {slowms: 100})
db.system.profile.find().limit(5).sort({ts: -1})
```

### **Debug Commands**
```python
# Test the logger directly
from src.test_result_logger import TestResultLogger

logger = TestResultLogger()
success = logger.initialize()
print(f"Logger initialized: {success}")

if success:
    # Test logging
    logger.log_test_start("debug_test", "debug.py")
    logger.log_test_result("debug_test", "passed", 1.0)
    print("Test logging successful")
```

---

## 📚 Integration Examples

### **CI/CD Pipeline Integration**
```yaml
# GitHub Actions example
name: Test with MongoDB Monitoring
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      mongodb:
        image: mongo:7.0
        env:
          MONGO_INITDB_ROOT_USERNAME: admin
          MONGO_INITDB_ROOT_PASSWORD: netskope_admin_2024
        ports:
          - 27017:27017

    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run tests with MongoDB logging
        run: |
          export TESTING_MODE=ci
          pytest tests/ -v
      
      - name: Generate test report from MongoDB
        run: |
          python scripts/generate_test_report.py --source mongodb --output test-report.json
      
      - name: Upload test results
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: test-report.json
```

### **Slack Notifications**
```python
# Send test results to Slack
import requests
from src.service_manager import get_database_client

def send_test_summary_to_slack(webhook_url):
    db_client = get_database_client()
    
    # Get latest session summary
    latest_session = db_client.find_one("test_sessions", {}, sort=[("timestamp", -1)])
    
    if latest_session:
        message = {
            "text": f"🧪 Test Results Summary",
            "attachments": [{
                "color": "good" if latest_session["success_rate"] > 90 else "warning",
                "fields": [
                    {"title": "Success Rate", "value": f"{latest_session['success_rate']:.1f}%", "short": True},
                    {"title": "Total Tests", "value": str(latest_session["total_tests"]), "short": True},
                    {"title": "Passed", "value": str(latest_session["passed"]), "short": True},
                    {"title": "Failed", "value": str(latest_session["failed"]), "short": True},
                    {"title": "Duration", "value": f"{latest_session['total_duration']:.1f}s", "short": True},
                    {"title": "Environment", "value": latest_session["environment"], "short": True}
                ]
            }]
        }
        
        response = requests.post(webhook_url, json=message)
        return response.status_code == 200
    
    return False

# Usage in pytest hook
def pytest_sessionfinish(session, exitstatus):
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if webhook_url:
        send_test_summary_to_slack(webhook_url)
```

---

## 🎯 Best Practices

### **1. Query Optimization**
- Always use indexes for frequently queried fields
- Limit result sets with `.limit()` for large datasets
- Use aggregation pipelines for complex analytics
- Consider using MongoDB views for common queries

### **2. Data Management**
- Set up TTL indexes for automatic data cleanup
- Archive old data before deletion
- Monitor database size and performance
- Use appropriate data types (ISODate for timestamps)

### **3. Security**
- Use authentication for production environments
- Limit database user permissions
- Encrypt sensitive test data
- Audit database access logs

### **4. Performance**
- Create compound indexes for multi-field queries
- Use projection to limit returned fields
- Batch operations when possible
- Monitor slow query logs

---

## 📞 Support and Resources

### **Documentation Links**
- 📖 **[Main Framework Guide](../README.md)** - Complete setup instructions
- 🔧 **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and solutions
- 📊 **[Monitoring Guide](MONITORING_AND_REPORTS_GUIDE.md)** - All monitoring platforms
- 🏗️ **[Architecture Guide](architecture.md)** - System design overview

### **MongoDB Resources**
- 📚 **[MongoDB Manual](https://docs.mongodb.com/manual/)** - Official documentation
- 🔍 **[Query Reference](https://docs.mongodb.com/manual/reference/operator/query/)** - Query operators
- 📊 **[Aggregation Pipeline](https://docs.mongodb.com/manual/aggregation/)** - Advanced analytics
- 🛠️ **[MongoDB Compass](https://www.mongodb.com/products/compass)** - GUI tool

### **Getting Help**
```bash
# Framework CLI help
python src/cli.py --help
python src/cli.py services --help

# Check service status
python src/cli.py services health

# Environment information
python src/cli.py env info
```

---

**🎯 This guide provides complete coverage of test monitoring with MongoDB in the Day-1 Framework. Use it to gain deep insights into your test execution patterns, performance trends, and quality metrics!**