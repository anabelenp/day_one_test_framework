# Framework Tutorial: Day-1 SDET Automation Framework

This tutorial walks through every part of the framework from first principles — what it is, why it was built the way it was, how each component works, how to run each test type, and how the whole thing fits into a professional software development lifecycle.

---

## Table of Contents

1. [What This Framework Is and Why It Exists](#1-what-this-framework-is-and-why-it-exists)
2. [Big-Picture Architecture](#2-big-picture-architecture)
3. [The Five Environments](#3-the-five-environments)
4. [Core Components Deep Dive](#4-core-components-deep-dive)
5. [Running the Framework: Step by Step](#5-running-the-framework-step-by-step)
6. [Test Types: Purpose, Commands, and What They Verify](#6-test-types-purpose-commands-and-what-they-verify)
7. [End-to-End Walkthrough](#7-end-to-end-walkthrough)
8. [CI/CD Pipelines](#8-cicd-pipelines)
9. [Software Development Lifecycle Integration](#9-software-development-lifecycle-integration)
10. [Interview Reference: Key Concepts and Questions](#10-interview-reference-key-concepts-and-questions)

---

## 1. What This Framework Is and Why It Exists

### The Problem it Solves

Cloud security products sit in the critical path of enterprise network traffic. They implement Secure Web Gateway (SWG), Cloud Access Security Broker (CASB), Data Loss Prevention (DLP), Zero Trust Network Access (ZTNA), and Firewall-as-a-Service (FWaaS). Testing these systems presents a specific challenge: the real product handles sensitive corporate data, requires paid API credentials, and must not be accidentally modified by a test run.

A naive test suite breaks in three ways:
- It cannot run in CI without production credentials baked in
- It cannot run offline or during a network outage
- Developers cannot run it locally without setting up a replica of production infrastructure

This framework solves all three by building a **five-tier environment abstraction** that makes the same test code run identically whether services are in-memory mocks or live Kubernetes clusters.

### What "Day-1 Ready" Means

The name means: on day one of a new engineer joining the team, they can clone the repo, run `TESTING_MODE=mock pytest tests/unit/ -v`, and see 116 passing tests. No credentials. No Docker. No configuration. The framework defaults to an in-memory mock environment.

### The Products Under Test

| Product | Abbreviation | What it Tests |
|---|---|---|
| Secure Web Gateway | SWG | URL blocking, web traffic filtering, category enforcement |
| Cloud Access Security Broker | CASB | Cloud app access control |
| Data Loss Prevention | DLP | File scanning, PII/credit card detection, policy enforcement |
| Zero Trust Network Access | ZTNA | Access policies, MFA requirements, device posture |
| Firewall-as-a-Service | FWaaS | Port blocking, traffic rules, network security |

---

## 2. Big-Picture Architecture

```mermaid
graph TB
    subgraph "Test Code"
        TC1[tests/unit/]
        TC2[tests/integration/]
        TC3[tests/e2e/]
        TC4[tests/security/]
        TC5[tests/dlp/]
        TC6[tests/swg/]
        TC7[tests/ztna/]
        TC8[tests/firewall/]
    end

    subgraph "Service Manager"
        SM[ServiceManager]
        SMM[Mock Clients]
        SMR[Real Clients]
    end

    subgraph "Environment Manager"
        EM[EnvironmentManager]
        DET[detect_environment]
        LOAD[load_configuration]
    end

    subgraph "Infrastructure"
        K8S[Kubernetes]
        DC[Docker Compose]
        MOCK[In-Memory]
    end

    subgraph "Services"
        REDIS[(Redis)]
        KAFKA[(Kafka)]
        MONGO[(MongoDB)]
        API[Target API]
        AWS[AWS Services]
    end

    TC1 --> SM
    TC2 --> SM
    TC3 --> SM
    TC4 --> SM
    TC5 --> SM
    TC6 --> SM
    TC7 --> SM
    TC8 --> SM

    SM --> SMM
    SM --> SMR

    EM --> DET
    EM --> LOAD

    SMM --> MOCK
    SMR --> K8S
    SMR --> DC

    K8S --> REDIS
    K8S --> KAFKA
    K8S --> MONGO
    K8S --> API
    K8S --> AWS

    DC --> REDIS
    DC --> KAFKA
    DC --> MONGO
    DC --> API
    DC --> AWS

    MOCK --> REDIS
    MOCK --> KAFKA
    MOCK --> MONGO
    MOCK --> API

    style TC1 fill:#e1f5fe
    style EM fill:#fff3e0
    style SM fill:#e8f5e8
```

**Priority: TESTING_MODE env var → Kubernetes → Docker → local services → config files → default MOCK**

This is the environment detection priority chain — how the framework decides which environment to run in.

```python
# src/environment_manager.py:88-139

# 1. TESTING_MODE env var (highest priority)
export TESTING_MODE=mock   # forces mock, ignores everything else
export TESTING_MODE=local  # forces local Docker Compose
# Set this and it always wins, regardless of where you're running.

# 2. Kubernetes detected
if os.getenv("KUBERNETES_SERVICE_HOST"):
    # Running inside a K8s cluster
    # Check ENVIRONMENT var for which one:
    #   "staging"  → STAGING
    #   "production" → PRODUCTION
    #   anything else → INTEGRATION

# 3. Docker container detected
if os.path.exists("/.dockerenv"):
    # Running inside a Docker container
    # → LOCAL environment

# 4. Local dev services reachable
# Can TCP-connect to ≥3 of:
#   localhost:6379   (Redis)
#   localhost:9092   (Kafka)
#   localhost:27017  (MongoDB)
#   localhost:9090   (Prometheus)
#   localhost:3000   (Grafana)
# If your Docker Compose services are running → LOCAL.

# 5. Config files present
config/local.yaml       → LOCAL
config/integration.yaml → INTEGRATION
config/staging.yaml    → STAGING
config/production.yaml → PRODUCTION

# 6. Default fallback
→ MOCK  # safest — no external dependencies
```

**Why this order?** The explicit env var lets developers override everything. The K8s/Docker checks let the framework auto-detect when deployed. The port checks catch local dev scenarios. Config files are a last resort. MOCK is the safest default so tests fail fast if nothing is configured.

### The Key Design Principle: Service Abstraction

Every test imports the same four client types:

```python
from src.service_manager import (
    get_cache_client,       # → Redis (real) or dict (mock)
    get_message_client,     # → Kafka (real) or list (mock)
    get_database_client,    # → MongoDB (real) or dict (mock)
    get_api_client,         # → HTTP session (real) or fixed responses (mock)
)
```

The test does not know or care which implementation it gets. The `EnvironmentManager` decides at runtime based on the environment. This is the **Strategy pattern** applied at infrastructure level.

---

## 3. The Five Environments

Understanding the environments is the single most important concept in this framework.

### E1 — Mock (default)

**When used:** Local development, unit tests, CI pipelines without Docker  
**Services:** All in-memory Python objects — no external processes needed  
**Activate:** `export TESTING_MODE=mock` or leave unset

The `MockCacheClient` is a plain Python dict. `MockMessageClient` uses a dict of lists as its topic store. `MockDatabaseClient` holds collections as dict of lists and supports CRUD and basic aggregation (`$match`, `$group`). `MockAPIClient` returns hardcoded realistic JSON responses.

```bash
export TESTING_MODE=mock
pytest tests/unit/ -v
# Runs in seconds, no Docker required
```

### E2 — Local (Docker Compose)

**When used:** Integration testing on a developer's machine  
**Services:** Redis 7, Kafka (KRaft mode — no Zookeeper), MongoDB 6, LocalStack (AWS), Prometheus, Grafana, Jaeger, nginx mock API  
**Activate:** `export TESTING_MODE=local`

```bash
docker-compose -f docker-compose.local.yml up -d
export TESTING_MODE=local
pytest tests/integration/test_local_environment.py -v
```

Key note: `docker-compose.local.yml` is the current file. The legacy `docker-compose.yml` uses Zookeeper-based Kafka and should not be used.

### E3 — Integration (Kubernetes single-node)

**When used:** CI pipelines, pre-merge validation, E2E tests  
**Services:** Kubernetes-deployed Redis, Kafka (1 broker), MongoDB, Jaeger, monitoring stack  
**Prerequisite:** A Kubernetes cluster must be running first (see [Kubernetes Cluster Prerequisites](#kubernetes-cluster-prerequisites) below)  
**Activate:** `export TESTING_MODE=integration`

```bash
day1-sdet integration deploy    # deploys k8s/integration/ manifests
day1-sdet integration status
TESTING_MODE=integration pytest tests/e2e/ -v
```

**Manifest files in k8s/integration/:**
- `kafka-cluster.yaml` - Zookeeper + Kafka StatefulSets
- `mongodb-replica.yaml` - MongoDB StatefulSet
- `redis-cluster.yaml` - Redis cluster
- `mock-api-service.yaml` - Mock Netskope API
- `test-runner-job.yaml` - Integration test runner
- `monitoring-stack.yaml` - Prometheus + Grafana
- `jaeger-deployment.yaml` - Jaeger distributed tracing
- `ingress.yaml` - External access

### E4 — Staging (Kubernetes HA)

**When used:** Pre-production validation, load testing, security testing  
**Services:** Redis Sentinel (HA), 5-broker Kafka cluster, 5-node MongoDB replica set  
**Prerequisite:** A Kubernetes cluster must be running first  
**Activate:** `export TESTING_MODE=staging`

```bash
day1-sdet staging deploy
day1-sdet staging test --test-type load
```

### E5 — Production (Read-Only Monitoring)

**When used:** Health checks and smoke monitoring against real production  
**Access:** Read-only — no writes, no mutations, no destructive operations  
**Activate:** `export TESTING_MODE=production`

```bash
day1-sdet production health-check
day1-sdet production monitor --interval 300
day1-sdet production report --output health.json
```

### Setting Up Kubernetes

To use E3 (Integration) or E4 (Staging) environments, you need a Kubernetes cluster. See [Kubernetes Cluster Prerequisites](#kubernetes-cluster-prerequisites) for setup instructions.

### Environment Detection Logic

The `EnvironmentManager.detect_environment()` method walks a priority chain:

```python
1. TESTING_MODE env var (highest priority — always wins)
2. Kubernetes: KUBERNETES_SERVICE_HOST present → check ENVIRONMENT var
3. Docker: /.dockerenv exists
4. Local dev: can TCP-connect to Redis:6379 + Kafka:9092 + MongoDB:27017
5. Config files: integration.yaml / staging.yaml / production.yaml exist
6. Default: MOCK (safest fallback)
```

---

## 4. Core Components Deep Dive

### 4.1 Environment Manager (`src/environment_manager.py`)

Responsible for: detecting the current environment, loading the correct YAML configuration, validating service connectivity, and providing `ServiceConfig` objects to the service layer.

**Key classes:**

```python
Environment(Enum)           # MOCK, LOCAL, INTEGRATION, STAGING, PRODUCTION
ServiceConfig(dataclass)    # host, port, username, password, ssl_enabled, timeout
EnvironmentConfig(dataclass)# wraps four ServiceConfig + aws/monitoring/security dicts
EnvironmentManager          # singleton that does detection and config loading
```

**Thread safety:** Uses `threading.Lock` for the global singleton. `_config_cache` avoids re-parsing YAML on every call.

**Key methods to know:**

```python
env_manager.detect_environment()          # runs the priority chain
env_manager.get_current_environment()     # cached result of detect_environment()
env_manager.set_environment(Environment.LOCAL)  # manual override
env_manager.load_configuration()          # returns EnvironmentConfig, cached
env_manager.validate_environment()        # checks config completeness + TCP connectivity
env_manager.get_service_config("redis")   # returns ServiceConfig for a named service
```

### 4.2 Service Manager (`src/service_manager.py`)

This is the abstraction hub. It contains:

- **Abstract base classes:** `ServiceClient`, `CacheClient`, `MessageClient`, `DatabaseClient`, `APIClient` — these define the contract every implementation must fulfil
- **Mock implementations:** `MockCacheClient`, `MockMessageClient`, `MockDatabaseClient`, `MockAPIClient` — pure Python, no I/O
- **Real implementations:** `RealCacheClient` (Redis), and the real Kafka/MongoDB/API clients in `real_service_clients.py`
- **`ServiceManager`:** factory that asks `EnvironmentManager` which environment is active, then instantiates the correct client

**Pattern: Abstract base class + dual implementation**

```python
class CacheClient(ABC):
    def set(self, key, value, ttl=None) -> bool: ...
    def get(self, key) -> Any: ...
    def delete(self, key) -> bool: ...

class MockCacheClient(CacheClient):
    _store: dict   # just a Python dict

class RealCacheClient(CacheClient):
    _connection: redis.Redis  # real Redis
```

The test calls `get_cache_client().set("k", "v")` — identical syntax regardless of environment.

**Client lifecycle:** Clients are lazy-initialised and cached inside `ServiceManager._clients`. Calling `get_cache_client()` twice returns the same instance (idempotent). `disconnect_all()` tears them all down and clears the cache.

### 4.3 Circuit Breaker (`src/circuit_breaker.py`)

Implements the classic three-state fault tolerance pattern for real service calls.

```
CLOSED (failure_threshold reached) OPEN
                                         
                                    (timeout elapsed)
                                         
  (success_threshold in HALF_OPEN) HALF_OPEN
```

**States:**
- **CLOSED:** Normal operation. Every call goes through. Failure count accumulates.
- **OPEN:** All calls rejected immediately with `CircuitBreakerError`. No load on the failing service.
- **HALF_OPEN:** After `timeout` seconds, one probe call is allowed. Success → CLOSED. Failure → OPEN again.

**Configuration:**
```python
CircuitBreakerConfig(
    failure_threshold=5,   # consecutive failures to trip
    success_threshold=2,   # consecutive successes in HALF_OPEN to reset
    timeout=60,            # seconds to wait before trying HALF_OPEN
    name="my_service",
)
```

**Usage:**
```python
# As a decorator
@circuit_breaker("netskope_api")
def call_api():
    return requests.get(url)

# Programmatic
breaker = create_service_circuit_breaker("redis", failure_threshold=3)
result = breaker.call(redis_client.get, "my_key")

# Check state
breaker.state     # CircuitState.CLOSED / OPEN / HALF_OPEN
breaker.stats     # CircuitBreakerStats with counts
breaker.get_info()# dict for dashboards/monitoring
```

**Why it matters:** Without a circuit breaker, a failing Redis or Kafka node causes every test/request to hang for the full TCP timeout before failing. With the circuit breaker, after 5 failures it trips open and all subsequent calls fail fast for 60 seconds, then probe once.

### 4.4 Connection Pool (`src/connection_pool.py`)

Provides a generic thread-safe object pool with min/max size, idle eviction, and health validation. `HTTPConnectionPool` specialises it for `requests.Session` objects.

**Key concepts:**

```python
PoolConfig(
    min_size=5,            # pre-created connections
    max_size=20,           # hard cap
    max_idle_time=300,     # evict connections idle longer than 5 min
    max_lifetime=3600,     # evict connections older than 1 hour
    acquisition_timeout=30 # raise TimeoutError if no connection within 30s
)
```

**Lifecycle:** `acquire()` → use connection → `release()` (or context manager). A background daemon thread runs `_validation_loop()` every 60 seconds to evict stale connections and replenish to `min_size`.

**`HTTPConnectionPool`** creates `requests.Session` objects with a `Retry` strategy: 3 retries, 0.5s backoff factor, retrying on 429/500/502/503/504.

### 4.5 Real Service Clients (`src/real_service_clients.py`)

Three production-ready implementations:

**`RealMessageClient` (Kafka)**
- Producer: `acks="all"`, `retries=3`, JSON serialization
- Admin client: topic creation, listing, deletion
- Consumer: background thread, configurable group ID
- Auth: SASL/PLAIN or SASL/SCRAM-SHA-256, optional SSL

**`RealDatabaseClient` (MongoDB)**
- Full CRUD: `insert_one`, `insert_many`, `find_one`, `find_many`, `update_one`, `update_many`, `delete_one`, `delete_many`
- Index management: `create_index`, `drop_index`, `list_indexes`
- Aggregation pipeline support
- ObjectId-to-string conversion for JSON serialisation
- Bulk operations

**`RealAPIClient` (Netskope HTTP)**
- HTTP session with `HTTPAdapter` retry strategy
- Three auth methods: API key (Bearer token), username/password (JWT exchange), mTLS (client cert)
- Circuit breaker integration: records success/failure on every HTTP call
- Methods: `get`, `post`, `put`, `delete`

### 4.6 Custom Exceptions (`src/exceptions.py`)

A twelve-type hierarchy all inheriting `SDETFrameworkError`:

```
SDETFrameworkError
 ConfigurationError          # bad/missing config
 EnvironmentError            # detection/switch failure
 ValidationError             # data validation
 TestDataError               # test fixtures
 DeploymentError
    KubernetesError         # k8s-specific operations
 ServiceConnectionError      # base connection failure
    ServiceTimeoutError     # timed out
 AuthenticationError         # auth failure
 HealthCheckError            # health check failure
 ResourceNotFoundError       # 404-style
 CircuitBreakerError         # circuit is open
 RateLimitError              # rate limit exceeded
```

Each carries a structured `details` dict and a `__str__` that formats it for readable log output.

### 4.7 Test Result Logger (`src/test_result_logger.py`)

Hooks into pytest's plugin system to automatically log every test start, result, and session summary to MongoDB.

**Hooks implemented:**
```python
pytest_sessionstart(session)      # records session start time
pytest_runtest_setup(item)        # logs test_name, file, class, status=running
pytest_runtest_logreport(report)  # updates status, duration, error_message; counts skips
pytest_sessionfinish(session)     # writes session summary with pass/fail/skip counts
```

**Collections written:**
- `test_results` — one document per test
- `test_sessions` — one summary per pytest run

**Query your test data:**
```bash
mongosh "mongodb://admin:netskope_admin_2024@localhost:27017/netskope_local?authSource=admin"

# Last 10 test results
db.test_results.find().sort({start_time: -1}).limit(10)

# Failed tests only
db.test_results.find({status: "failed"}).sort({start_time: -1})

# Average duration per test
db.test_results.aggregate([
  {$group: {_id: "$test_name", avg_ms: {$avg: "$duration"}, runs: {$sum: 1}}}
])

# Session pass rate
db.test_sessions.find().sort({timestamp: -1}).limit(5)
```

---

## 5. Running the Framework: Step by Step

### First-Time Setup

```bash
# 1. Clone and enter the project
git clone <repo_url>
cd day_one_test_framework

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

# 3. Install in editable mode (registers the day1-sdet CLI command)
pip install -e .

# 4. Verify the install
python -c "from src.environment_manager import get_current_environment; print(get_current_environment().value)"
# Should print: mock  (or local if config/local.yaml is present — set TESTING_MODE=mock to override)
```

### CLI Reference

After `pip install -e .`, `day1-sdet` is available as a shell command. Before install, use `python src/cli.py` — arguments are identical.

```bash
# Environment commands
day1-sdet env detect                     # print detected environment
day1-sdet env info                       # full environment details
day1-sdet env info local                 # details for a specific env
day1-sdet env validate                   # check config + connectivity
day1-sdet env set mock                   # set environment for this session
day1-sdet env list                       # list all environments

# Service commands
day1-sdet services health                # health check all four services
day1-sdet services info                  # connection details
day1-sdet services test cache            # test Redis/mock cache
day1-sdet services test message          # test Kafka/mock messaging
day1-sdet services test database         # test MongoDB/mock database
day1-sdet services test api              # test API client

# Test runner
day1-sdet test unit                      # unit tests (mock env)
day1-sdet test integration -e local      # integration tests (local env)
day1-sdet test e2e -e integration        # E2E tests (integration env)
day1-sdet test security                  # security tests
day1-sdet test performance               # performance tests
day1-sdet test unit --html-report        # with HTML report at reports/
day1-sdet test unit --coverage           # with coverage report
day1-sdet test unit --markers "not slow" # filter by marker

# Reporting
day1-sdet test unit --html-report --coverage  # HTML + coverage report
# Generates: reports/test_report.html, reports/allure-results/, htmlcov/

# Local environment (Docker Compose)
day1-sdet local start                    # docker-compose up -d
day1-sdet local stop                     # docker-compose down
day1-sdet local status                   # health check all services
day1-sdet local restart                  # restart all services

# Integration environment (Kubernetes)
day1-sdet integration deploy
day1-sdet integration status
day1-sdet integration test
day1-sdet integration undeploy

# Staging environment (Kubernetes HA)
day1-sdet staging deploy
day1-sdet staging status
day1-sdet staging test --test-type load
day1-sdet staging undeploy

# Production (read-only)
day1-sdet production health-check
day1-sdet production monitor --interval 300
day1-sdet production report --output health.json

# Version
day1-sdet version
```

---

### CLI Reporting Options

The framework generates multiple report formats automatically via `pyproject.toml`:

| Format | Output | Use Case |
|-------|--------|----------|
| HTML Report | `reports/test_report.html` | Standalone, shareable results |
| Allure Results | `reports/allure-results/` | Rich interactive reports with trends |
| Coverage | `htmlcov/index.html` | Code coverage analysis |

**Quick commands:**

```bash
# All reports at once (recommended for CI)
TESTING_MODE=mock pytest tests/unit/ \
  --cov=src \
  --cov-report=html:reports/coverage \
  --cov-report=xml:reports/coverage.xml \
  --html=reports/test_report.html \
  --self-contained-html \
  --junitxml=reports/unit-results.xml \
  -v

# View Allure report (requires: brew install allure)
allure serve reports/allure-results

# View coverage
open htmlcov/index.html
```

**Dependencies** (already in requirements.txt):
```
pytest>=9.0.0
pytest-html>=4.2.0
allure-pytest>=2.14.0
pytest-cov>=4.0.0
```

---

## 6. Test Types: Purpose, Commands, and What They Verify

### 6.1 Unit Tests

**Location:** `tests/unit/`  
**Environment:** Mock (no external services)  
**Speed:** Seconds  
**Purpose:** Verify individual classes and functions in isolation using mocks

**What is tested:**

| File | Covers |
|---|---|
| `test_environment_manager.py` | Environment enum values, env var detection, Kubernetes/Docker detection, config caching, connectivity checks, singleton pattern |
| `test_service_manager.py` | MockCacheClient CRUD and TTL, MockMessageClient publish/subscribe/consume, MockDatabaseClient CRUD and aggregation, MockAPIClient endpoints, ServiceManager factory, client caching |
| `test_circuit_breaker.py` | State transitions (CLOSED→OPEN→HALF_OPEN→CLOSED), failure threshold, success threshold, timeout reset, `call()` wrapping, registry |
| `test_connection_pool.py` | Acquire/release, timeout, validation, idle eviction, stats |
| `test_cli.py` | Argument parsing, command dispatch, environment switching |

**Run commands:**

```bash
# All unit tests
TESTING_MODE=mock pytest tests/unit/ -v

# Single file
TESTING_MODE=mock pytest tests/unit/test_circuit_breaker.py -v

# Single test
TESTING_MODE=mock pytest tests/unit/test_service_manager.py::TestMockCacheClient::test_set_and_get -v

# With coverage
TESTING_MODE=mock pytest tests/unit/ --cov=src --cov-report=term-missing

# With HTML + Allure reports
TESTING_MODE=mock pytest tests/unit/ --html=reports/unit-report.html --self-contained-html -v

# Generate Allure report
allure serve reports/allure-results

# Skip slow tests
TESTING_MODE=mock pytest tests/unit/ -m "not slow" -v

# Via CLI
day1-sdet test unit
day1-sdet test unit --html-report --coverage
```

**Example — what a unit test looks like:**

```python
class TestCircuitBreaker:
    def test_trip_after_failure_threshold(self):
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker(config)

        for _ in range(3):
            breaker.record_failure()

        assert breaker.state == CircuitState.OPEN  # tripped exactly at threshold
```

### 6.2 Integration Tests

**Location:** `tests/integration/`  
**Speed:** Minutes  
**Purpose:** Verify that real services (Redis, Kafka, MongoDB) accept connections and that the framework's real clients work end-to-end

The integration tests have two variants:

#### Local Environment Tests (Docker Compose)

**File:** `tests/integration/test_local_environment.py`  
**Environment:** LOCAL (Docker Compose)  
**Requires:** `docker-compose -f docker-compose.local.yml up -d`

```bash
# Start services
docker-compose -f docker-compose.local.yml up -d

# Run local integration tests
TESTING_MODE=local pytest tests/integration/test_local_environment.py -v

# Run all local tests with full reporting
TESTING_MODE=local pytest tests/integration/test_local_environment.py \
  --html=reports/local-report.html \
  --cov=src \
  --cov-report=html:reports/integration-coverage \
  --cov-report=xml:reports/integration-coverage.xml \
  --junitxml=reports/integration-results.xml \
  -v

# Generate Allure report
allure serve reports/allure-results

# Teardown
docker-compose -f docker-compose.local.yml down
```

**What is tested:**

| Test | Description |
|------|-------------|
| `test_redis_connectivity` | Redis CRUD operations, TTL |
| `test_mongodb_connectivity` | MongoDB CRUD, aggregation, indexes |
| `test_cache_and_database_integration` | Cross-service data flow (Redis + MongoDB) |
| `test_service_health_checks` | All services report healthy |
| `test_monitoring_config` | Prometheus, Grafana accessibility |

#### Kubernetes Integration Tests

**File:** `tests/integration/test_integration_environment.py`  
**Environment:** INTEGRATION (Kubernetes)  
**Requires:** K8s cluster deployed via `day1-sdet integration deploy`

```bash
# Deploy integration environment
day1-sdet integration deploy

# Run Kubernetes integration tests
TESTING_MODE=integration pytest tests/integration/test_integration_environment.py -v

# Teardown
day1-sdet integration undeploy
```

### 6.3 Security Tests

**Location:** `tests/security/`  
**Environment:** Mock (for injection/XSS tests) or Local/Integration (for real endpoint tests)  
**Purpose:** Verify the API rejects malicious inputs and does not expose sensitive data

**What is tested:**

| Class | Scenarios |
|---|---|
| `TestSQLInjection` | `'; DROP TABLE users;--`, `' OR '1'='1`, MongoDB `$gt`/`$ne`/`$where` operators |
| `TestXSSVulnerabilities` | `<script>alert('XSS')`, `<img onerror=...>`, `javascript:` URLs |
| `TestAuthenticationSecurity` | Invalid credentials, missing credentials, weak passwords list |
| `TestAuthorizationSecurity` | Privilege escalation (`POST /api/v2/admin/users`), resource access control |
| `TestInputValidation` | Max length (10,000 char), invalid types (int/array/null), null bytes, encoded chars |
| `TestRateLimiting` | Rate-limit headers present, excessive requests blocked |
| `TestSSLSettings` | SSL required in production |
| `TestSecretExposure` | Passwords not appearing in logs, API keys not in responses |

**Run commands:**

```bash
# All security tests in mock mode
TESTING_MODE=mock pytest tests/security/ -v

# Only injection tests
TESTING_MODE=mock pytest tests/security/test_api_security.py::TestSQLInjection -v

# Data security tests
TESTING_MODE=mock pytest tests/security/test_data_security.py -v

# Via marker
TESTING_MODE=mock pytest -m security -v

# Via CLI
day1-sdet test security
```

### 6.4 Domain Tests (SWG, DLP, ZTNA, Firewall)

**Location:** `tests/swg/`, `tests/dlp/`, `tests/ztna/`, `tests/firewall/`  
**Environment:** Mock (default) — uses mock API responses  
**Purpose:** Verify business logic for each security product

**DLP example — what is tested:**

```python
# tests/dlp/test_file_dlp.py
# Sends files through the DLP scanner mock and verifies:
# - SSN patterns trigger "high" severity violations
# - Credit card numbers are detected
# - Clean files pass without violations
# - Quarantine action is applied for high-severity matches
```

**Run commands:**

```bash
# Individual product suites
TESTING_MODE=mock pytest tests/swg/ -v      # URL blocking, category rules
TESTING_MODE=mock pytest tests/dlp/ -v      # DLP file scanning, PII detection
TESTING_MODE=mock pytest tests/ztna/ -v     # access policies, MFA enforcement
TESTING_MODE=mock pytest tests/firewall/ -v # port rules, traffic analysis

# All domain tests together
TESTING_MODE=mock pytest tests/swg/ tests/dlp/ tests/ztna/ tests/firewall/ -v

# Parametric DLP scenarios
TESTING_MODE=mock pytest tests/dlp/test_dlp_scenarios.py -v
```

### 6.5 End-to-End Tests

**Location:** `tests/e2e/`  
**Environment:** Integration (Kubernetes) — tests skip automatically in any other environment  
**Purpose:** Validate complete workflows across all four services simultaneously

**Scenarios tested:**

| Test | What it does |
|---|---|
| `test_complete_security_event_workflow` | Simulates a detected threat: store in Redis, publish to Kafka, persist in MongoDB, retrieve via API — verifies data round-trips |
| `test_policy_management_workflow` | Create policy → cache → publish event → retrieve via API → update → verify cache and DB are consistent |
| `test_user_risk_assessment_workflow` | Create user → generate security events → calculate risk score → update all stores → verify consistency |
| `test_alert_generation_and_notification_workflow` | Critical DLP event → generate alert → cache → publish notification → acknowledge → verify state machine |
| `test_data_consistency_across_services` | Write same data to Redis + MongoDB + Kafka; read back from all three and assert identical values |
| `test_system_performance_under_load` | 5 concurrent threads × 20 operations each across all services; assert <10% error rate |

**Run commands:**

```bash
# Deploy integration environment first
day1-sdet integration deploy

# Run E2E tests (auto-skip if not in integration env)
TESTING_MODE=integration pytest tests/e2e/ -v

# E2E with full reporting
TESTING_MODE=integration pytest tests/e2e/ \
  --html=reports/e2e-report.html \
  --cov=src \
  --cov-report=html:reports/e2e-coverage \
  --cov-report=xml:reports/e2e-coverage.xml \
  --junitxml=reports/e2e-results.xml \
  -v

# Only the performance scenario
TESTING_MODE=integration pytest tests/e2e/ -m "e2e and slow" -v

# Skip slow tests (load scenario)
TESTING_MODE=integration pytest tests/e2e/ -m "e2e and not slow" -v

# Via CI workflow (runs after integration-tests.yml services are up)
TESTING_MODE=integration pytest tests/e2e/ -v --junitxml=reports/e2e-results.xml -x
```

**What makes E2E different from integration tests:**

Integration tests verify a single service at a time ("can we write to MongoDB?"). E2E tests verify a full workflow across all services ("when a security event is detected, does it get stored in Redis, published to Kafka, persisted in MongoDB, and queryable via the API — all with consistent data?").

### 6.6 Performance Tests

**Location:** `tests/performance/`  
**Three tools:** Python pytest-based, JMeter, Locust

**Python load tests (`tests/performance/test_load.py`):**
```bash
TESTING_MODE=local pytest tests/performance/ -v -m performance
# or
TESTING_MODE=mock pytest tests/performance/ -v    # mock mode for CI
```

**JMeter load tests:**
```bash
# Requires: jmeter installed and on PATH
jmeter -n \
  -t tests/performance/jmeter/netskope_api_load_test.jmx \
  -Jusers=50 \
  -Jramp_time=60 \
  -Jduration=300 \
  -l reports/jmeter_results.jtl \
  -e -o reports/jmeter_html_report

# Common JMeter parameters:
# -n            non-GUI mode
# -t            test plan file
# -Jusers       number of virtual users
# -Jramp_time   seconds to reach full load
# -Jduration    test duration in seconds
# -l            raw results file (.jtl)
# -e -o         generate HTML dashboard
```

**Locust load tests:**
```bash
# Requires: pip install locust

# Headless (CI-friendly)
locust -f tests/performance/locust/netskope_load_test.py \
  --host=http://localhost:8080 \
  --users=50 \
  --spawn-rate=5 \
  --run-time=300s \
  --headless \
  --csv=reports/locust_results

# Interactive web UI
locust -f tests/performance/locust/netskope_load_test.py \
  --host=http://localhost:8080
# Open http://localhost:8089 → set users/spawn rate → start

# Shell script wrapper
bash scripts/run_performance_tests.sh
```

### 6.6.1 Performance Security Tests

**Location:** `tests/performance/test_security_performance.py`  
**Purpose:** Validate security mechanisms under load — authentication, authorization, rate limiting, and DDoS resilience

**Test categories:**

| Category | Tests | Purpose |
|----------|-------|---------|
| Authentication Load | Token validation under 1000+ concurrent requests, burst handling, latency degradation | Ensure auth performs under load |
| RBAC Performance | Policy lookup under concurrent access, permission checks | Verify authorization scales |
| Rate Limiting | Threshold detection, TTL recovery, distributed rate limiting | Validate throttling works |
| DDoS Simulation | Connection pool stress, high volume requests, graceful degradation | Test resilience |

**Run commands:**
```bash
# All performance security tests
TESTING_MODE=mock pytest tests/performance/test_security_performance.py -v

# By marker
TESTING_MODE=mock pytest tests/performance/ -m "performance and security" -v

# Individual test class
TESTING_MODE=mock pytest tests/performance/test_security_performance.py::TestAuthenticationLoad -v
TESTING_MODE=mock pytest tests/performance/test_security_performance.py::TestRateLimiting -v
TESTING_MODE=mock pytest tests/performance/test_security_performance.py::TestDDOSSimulation -v
```

**Requirements validated:**
- Token validation P99 latency < 100ms
- Error rate < 1% under normal load
- Rate limiter activates correctly at threshold
- System degrades gracefully under attack

### 6.7 Production Monitoring Tests

**Location:** `tests/production/`  
**Environment:** Production (read-only)  
**Purpose:** Health checks and smoke tests against live production — no writes

```bash
TESTING_MODE=production pytest tests/production/ -v
# or
day1-sdet production health-check
```

### 6.8 Staging Tests

**Location:** `tests/staging/`  
**Environment:** Staging (Kubernetes HA)  
**Purpose:** Validate HA configuration, failover, and pre-production behaviour

```bash
day1-sdet staging deploy
TESTING_MODE=staging pytest tests/staging/ -v
day1-sdet staging test --test-type load
```

---

## 7. End-to-End Walkthrough

This section traces exactly what happens when the security event E2E test runs.

### The Scenario: `test_complete_security_event_workflow`

A simulated threat is detected. The test verifies the complete data pipeline:

```
Detection → Cache (Redis) → Message Queue (Kafka) → Database (MongoDB) → API Query
```

**Step-by-step:**

```python
# 1. Build the event payload
security_event = {
    "event_id": "evt_e2e_1712345678",
    "event_type": "swg",
    "severity": "high",
    "user": "test.user@company.com",
    "url": "malicious-site.com",
    ...
}

# 2. Cache for fast access (Redis)
cache_result = self.cache_client.set(
    f"security_event:{security_event['event_id']}",
    json.dumps(security_event)
)
assert cache_result  # write succeeded

# 3. Publish to Kafka for async processing
self.message_client.create_topic("security_events")
publish_result = self.message_client.publish("security_events", security_event)
assert publish_result

# 4. Persist to MongoDB for long-term storage
doc_id = self.db_client.insert_one("security_events", security_event)
assert doc_id is not None

# 5. Read back from cache
cached_event = json.loads(self.cache_client.get(cache_key))
assert cached_event["event_id"] == security_event["event_id"]

# 6. Consume from Kafka
messages = self.message_client.consume("security_events", timeout=5000)
assert any(m["event_id"] == security_event["event_id"] for m in messages)

# 7. Query from MongoDB
stored_event = self.db_client.find_one("security_events",
                                       {"event_id": security_event["event_id"]})
assert stored_event["severity"] == "high"

# 8. Query via API
api_events = self.api_client.get("/api/v2/events")
assert "data" in api_events

# 9. Clean up
self.cache_client.delete(cache_key)
self.db_client.delete_one("security_events", {"event_id": security_event["event_id"]})
```

### Running This Locally

```bash
# Option A: Run against mock (test logic only, no real services)
export TESTING_MODE=mock
# Note: E2E tests auto-skip when not in integration env
# Run integration-tagged unit tests instead:
TESTING_MODE=mock pytest tests/unit/ -v

# Option B: Run against local Docker services (E2 - Local)
docker-compose -f docker-compose.local.yml up -d
export TESTING_MODE=local
pytest tests/integration/test_local_environment.py -v        # integration tests

# Option C: Full E2E on Kubernetes (E3 - Integration)
# REQUIRES: A running Kubernetes cluster (see Prerequisites below)
day1-sdet integration deploy
export TESTING_MODE=integration
pytest tests/e2e/ -v -m "e2e and not slow"
```

### Kubernetes Cluster Prerequisites

**E3 (Integration Environment) requires an existing Kubernetes cluster.** The framework does NOT create a cluster—it only deploys manifests to an existing one.

**Setup a local Kubernetes cluster:**

```bash
# Option 1: Minikube (recommended for local development)
minikube start --driver=virtualbox  # or --driver=hyperkit on macOS
minikube addons enable ingress

# Option 2: Kind (Kubernetes in Docker)
kind create cluster --name day1-integration

# Option 3: K3s (lightweight)
curl -sfL https://get.k3s.io | sh -

# Option 4: Docker Desktop Kubernetes
# Enable Kubernetes in Docker Desktop Settings → Kubernetes
```

**Verify kubectl is configured:**
```bash
kubectl cluster-info          # Should show cluster info
kubectl get nodes             # Should list at least one node
```

**Deploy to the cluster:**
```bash
day1-sdet integration deploy                    # Deploy to default namespace
day1-sdet integration deploy --namespace my-ns  # Deploy to custom namespace

# Verify deployment
day1-sdet integration status
kubectl get pods -n netskope-integration
```

### Troubleshooting Integration Deployment

**Zookeeper fails with "serverid zookeeper-0 is not a number":**
```bash
# Check Zookeeper pod status
kubectl get pods -n netskope-integration -l app=zookeeper
# View logs
kubectl logs zookeeper-0 -n netskope-integration --previous
# Fix: Update kafka-cluster.yaml - change ZOOKEEPER_SERVER_ID to use pod index
# From: fieldPath: metadata.name
# To: fieldPath: metadata.labels['apps.kubernetes.io/pod-index']
```

**Zookeeper shows "My id 0 not in the peer list":**
```bash
# For single-node Zookeeper, configure in kafka-cluster.yaml:
- name: ZOOKEEPER_SERVER_ID
  value: "0"
# Set replicas to 1 (not 3)
# Then delete PVCs and recreate pod
kubectl delete pvc -n netskope-integration zookeeper-data-zookeeper-0 zookeeper-logs-zookeeper-0
kubectl delete pod -n netskope-integration zookeeper-0 --force --grace-period=0
```

**Zookeeper readiness probe fails:**
```bash
# Change exec probe to TCP socket in kafka-cluster.yaml:
livenessProbe:
  tcpSocket:
    port: 2181
readinessProbe:
  tcpSocket:
    port: 2181
```

**Kafka fails with "broker.id: Not a number":**
```bash
# Update KAFKA_BROKER_ID in kafka-cluster.yaml:
- name: KAFKA_BROKER_ID
  valueFrom:
    fieldRef:
      fieldPath: metadata.labels['apps.kubernetes.io/pod-index']
```

**Kafka fails with "Unable to parse PLAINTEXT://$(POD_NAME).kafka-headless:9092":**
```bash
# Use static FQDN instead of env var substitution:
- name: KAFKA_ADVERTISED_LISTENERS
  value: "PLAINTEXT://kafka-cluster-0.kafka-headless.netskope-integration.svc.cluster.local:9092"
```

**Kafka readiness probe times out:**
```bash
# Change to TCP socket probe in kafka-cluster.yaml:
readinessProbe:
  tcpSocket:
    port: 9092
  initialDelaySeconds: 30
  periodSeconds: 10

# Also reduce replication factors for single-node:
KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: "1"
KAFKA_DEFAULT_REPLICATION_FACTOR: "1"
KAFKA_NUM_PARTITIONS: "1"
```

**If you don't have a Kubernetes cluster:**
- Use **Option B (E2 - Local)** with Docker Compose for local development
- Integration tests will auto-skip without a cluster (this is expected behavior)

### Viewing Historical Test Results

Test results are automatically stored in MongoDB (requires LOCAL or INTEGRATION environment):

```bash
# Connect to MongoDB
mongosh "mongodb://admin:admin_2024@localhost:27017/day1_local?authSource=admin"

# Query recent test results
db.test_results.find().sort({start_time: -1}).limit(10)

# Failed tests
db.test_results.find({status: "failed"}).sort({start_time: -1})

# Average duration per test
db.test_results.aggregate([
  {$group: {_id: "$test_name", avg_ms: {$avg: "$duration"}, runs: {$sum: 1}}}
])

# Success rate analysis
db.test_results.aggregate([
  {$group: {_id: "$status", count: {$sum: 1}}}
])

# Session summaries
db.test_sessions.find().sort({timestamp: -1}).limit(5)
```

See `docs/REPORTING.md` for the complete reporting guide.

---

## 8. CI/CD Pipelines

### Overview of Workflows

```
.github/workflows/
 unit-tests.yml           # triggered: push/PR to main, develop
 integration-tests.yml    # triggered: push/PR + daily at 02:00 UTC
 security-scan.yml        # triggered: push/PR + daily at 03:00 UTC
 deployment.yml           # triggered: push to main, version tags, manual
 dlp-tests.yml            # DLP-specific test pipeline
 performance-jmeter.yml   # JMeter load tests
 test-quality.yml         # Daily: flaky tests, metrics, code quality
 sonar-analysis.yml       # Daily: SonarCloud/static analysis
 snyk-security.yml        # Push/PR: Snyk vulnerability scanning
```

### `unit-tests.yml` — Fast Feedback Loop

**Triggers:** Every push and pull request to `main` or `develop`  
**Matrix:** Python 3.9, 3.10, 3.11, 3.12 — four parallel jobs  
**Coverage Gate:** 80% minimum (fails CI if below)

**Steps:**
1. Checkout code
2. Set up Python
3. Cache pip dependencies (key: hash of `requirements.txt`)
4. `pip install -e .` + test dependencies (including allure-pytest)
5. Verify import: `from src.environment_manager import get_current_environment`
6. `pytest tests/unit/ -v --cov=src --cov-report=xml --html=reports/... --alluredir=...`
7. Check coverage threshold (`scripts/check_coverage.py --threshold 80`)
8. Upload HTML report + coverage + Allure results as artifacts
9. Upload coverage to Codecov (Python 3.12 only, avoids quadruple upload)
10. Comment on PR with test status (Python 3.12 only)

**Why four Python versions?** To catch version-specific issues — f-string syntax, dataclass behaviour, typing changes. The `matrix` strategy runs them in parallel, so the job takes no longer than a single version.

**Complete CI report command:**
```yaml
- name: Run unit tests
  run: |
    pytest tests/unit/ \
      --cov=src \
      --cov-report=xml \
      --cov-report=html \
      --html=reports/unit-test-report.html \
      --self-contained-html \
      --junitxml=reports/unit-test-results.xml \
      --alluredir=reports/allure-results \
      -v

- name: Generate Allure Report
  run: allure generate reports/allure-results -o reports/allure-report --clean

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml

- name: Upload test results
  uses: actions/upload-artifact@v3
  with:
    name: test-results
    path: reports/
```

```yaml
strategy:
  matrix:
    python-version: [3.9, 3.10, 3.11]
```

### `integration-tests.yml` — Service Validation

**Triggers:** Push/PR + scheduled daily at 02:00 UTC  
**Steps:**
1. Checkout
2. `docker-compose -f docker-compose.local.yml up -d`
3. Wait loops with `timeout 60 bash -c 'until redis-cli ping; do sleep 2; done'`
4. Run `pytest tests/integration/test_local_environment.py -v -x` (stop on first failure)
5. Run `pytest tests/e2e/ -v -x`
6. On failure: collect Docker logs from all services
7. Always: `docker-compose down -v` (clean volumes)
8. On scheduled-run failure: auto-create a GitHub issue

The `-x` flag (stop on first failure) is important for integration tests: if Redis is down, all tests will fail, so there is no value in running 50 more tests — stop, collect logs, investigate.

### `security-scan.yml` — Security Gate

**Triggers:** Push/PR + daily at 03:00 UTC  
**Jobs (parallel):**

```
sast-bandit      → bandit -r src/ tests/ -ll -i
sast-semgrep     → semgrep with p/security-audit, p/owasp-top-ten, p/secrets
dependency-scan  → safety check + pip-audit
secret-scan      → TruffleHog (git history scan) + Gitleaks
codeql-analysis  → GitHub CodeQL for Python
```

**What each tool does:**

| Tool | Type | Catches |
|---|---|---|
| Bandit | SAST | Python security antipatterns: hardcoded passwords, `subprocess` with shell=True, insecure hash functions |
| Semgrep | SAST | OWASP Top 10, custom rules, Python-specific vulnerabilities |
| Safety | SCA | CVEs in your `requirements.txt` dependencies |
| pip-audit | SCA | Same as Safety, different database, better for PyPI packages |
| TruffleHog | Secret scan | Scans git history for leaked credentials, API keys |
| Gitleaks | Secret scan | Similar to TruffleHog, pattern-based |
| CodeQL | SAST | Deep semantic analysis by GitHub, finds logic bugs |

Results are uploaded as SARIF to GitHub Security tab, making findings visible directly in the code.

### `test-quality.yml` — Test Quality & Flaky Detection

**Triggers:** Daily at 06:00 UTC + manual (`workflow_dispatch`)  
**Purpose:** Identify flaky tests, analyze test metrics, check documentation coverage

**Jobs:**
```
flaky-test-detection  → Query MongoDB for tests that pass/fail inconsistently
test-metrics          → Calculate success rate, avg duration from MongoDB history
documentation-coverage → Count files with docstrings, check key docs exist
code-quality-check    → Run flake8, black, mypy, radon complexity analysis
test-reliability-report → Generate GitHub step summary from all artifacts
```

**Run locally:**
```bash
# Detect flaky tests
python scripts/detect_flaky_tests.py --min-runs 5 --fail-on-flaky

# Analyze test metrics
python scripts/analyze_test_metrics.py

# Check documentation coverage
python scripts/check_documentation.py

# Run all quality checks
python scripts/run_quality_checks.py

# Check coverage threshold
python scripts/check_coverage.py --threshold 80
```

### `sonar-analysis.yml` — SonarQube/Cloud Analysis

**Triggers:** Daily at 04:00 UTC + manual (`workflow_dispatch`)  
**Purpose:** Static analysis, code smells, technical debt tracking

**Jobs:**
```
sonarcloud     → SonarCloud (free tier) analysis with coverage
sonar-scanner  → Self-hosted SonarQube (requires manual config)
```

**Requirements:**
- `SONAR_TOKEN` secret (SonarCloud) or manual inputs for self-hosted
- `coverage.xml` from pytest-cov

### `snyk-security.yml` — Snyk Vulnerability Scanning

**Triggers:** Push/PR + daily at 02:00 UTC  
**Purpose:** Dependency vulnerability scanning, license compliance, IaC security

**Jobs:**
```
snyk-security  → Dependency vulnerability scan
snyk-code      → Static code analysis (SAST)
snyk-iac       → Infrastructure as Code scanning (Terraform, Dockerfile)
```

**Requirements:**
- `SNYK_TOKEN` secret

**What it catches:**
- Known CVEs in dependencies (Safety, pip-audit, Snyk)
- Code vulnerabilities (Bandit, Semgrep, CodeQL, Snyk Code)
- Infrastructure misconfigurations (Snyk IaC)
- Secret leaks (TruffleHog, Gitleaks, Semgrep secrets)
- License compliance issues

### `deployment.yml` — Release Pipeline

**Triggers:**
- Push to `main` → auto-deploy to Integration
- Version tag (`v*`) → auto-deploy to Staging
- Manual `workflow_dispatch` → choose Integration or Staging

**Environment protection:** Uses GitHub's `environment:` key, which maps to deployment protection rules. You configure required reviewers and branch restrictions in GitHub settings. This means staging deployments require an approval before the job runs.

```yaml
jobs:
  deploy-integration:
    environment: integration    # requires no approval
  deploy-staging:
    environment: staging        # requires approver sign-off in GitHub
```

**Deployment flow:**
1. Pre-deployment checks: determine which environments to target
2. Deploy Integration: `kubectl apply -f k8s/integration/` → smoke tests
3. Deploy Staging (on version tag): `kubectl apply -f k8s/staging/` → health check → load test

### Artifact Retention

Every workflow uploads artifacts:
- `reports/*.html` — human-readable HTML reports
- `reports/*.xml` — JUnit XML (machine-readable, used by GitHub test summary)
- `htmlcov/` — line-by-line coverage HTML

Access them in GitHub Actions → workflow run → Artifacts section.

---

## 9. Software Development Lifecycle Integration

### Where the Framework Fits

```
Developer writes code
        
        
git commit + push
        
        
GitHub Actions — unit-tests.yml
   Python 3.9  pytest tests/unit/  pass/fail
   Python 3.10  pytest tests/unit/  pass/fail
   Python 3.11  pytest tests/unit/  pass/fail + coverage upload
        
         (PR opened or push to main)
GitHub Actions — security-scan.yml (parallel)
   Bandit SAST
   Semgrep SAST
   dependency-scan (Safety + pip-audit)
   secret-scan (TruffleHog + Gitleaks)
        
         (merge to main)
GitHub Actions — deployment.yml
   Deploy to Integration (k8s)
        
         (daily at 02:00 UTC)
GitHub Actions — integration-tests.yml
   Docker Compose up → pytest integration + e2e → Docker down
        
         (version tag pushed, e.g. v1.2.0)
GitHub Actions — deployment.yml
   Deploy to Staging (k8s HA, requires approval)
        
         (production)
day1-sdet production health-check   ← read-only, manual or scheduled
```

### Test Pyramid

The framework follows the classic test pyramid:

```
         /\
        /  \    E2E tests (few, slow, full system)
       /----\   tests/e2e/  ← requires Kubernetes
      /      \
     /--------\  Integration tests (more, minutes)
    /          \  tests/integration/  ← requires Docker
   /____________\
  /              \  Unit tests (many, seconds)
 /________________\  tests/unit/  ← no dependencies
```

**Proportion in this codebase:**
- Unit: ~155 tests — fast, exhaustive, mock everything
- Integration: ~10 tests — one per service, verifies real connectivity
- E2E: ~6 scenarios — full workflow coverage, runs in K8s only
- Security: ~25 tests — run in mock mode, validate API contract
- Performance Security: ~12 tests — auth load, RBAC, rate limiting, DDoS
- Domain (SWG/DLP/ZTNA/FW): ~30 tests — business logic verification

### Shift-Left Security

Security testing is "shifted left" — run on every PR, not just pre-release. The `security-scan.yml` workflow runs Bandit and Semgrep on every push. This means security bugs are caught within minutes of being introduced rather than weeks later in a security audit.

### Feature Development Workflow

A typical feature addition follows this path:

```
1. Write failing test first (TDD)
   → TESTING_MODE=mock pytest tests/unit/test_my_feature.py -v
   → Test fails (expected)

2. Implement the feature in src/

3. Run unit tests — they pass
   → TESTING_MODE=mock pytest tests/unit/ -v

4. Add integration test if feature touches a real service
   → docker-compose -f docker-compose.local.yml up -d
   → TESTING_MODE=local pytest tests/integration/test_local_environment.py -v

5. Push to PR branch
   → unit-tests.yml runs automatically (CI)
   → security-scan.yml runs automatically (CI)

6. PR merged to main
   → deployment.yml deploys to Integration
   → integration-tests.yml runs nightly

7. Release tag
   → deployment.yml deploys to Staging (with approval)
   → Staging smoke tests run
```

### Branch Strategy

```
main          ← protected, requires PR + passing CI + reviewer approval
develop       ← integration branch for feature work
feature/*     ← short-lived feature branches
hotfix/*      ← emergency fixes merged directly to main
```

### Environment Promotion

Code is promoted through environments, never deployed directly to higher environments:

```
feature branch → main → Integration (auto) → Staging (manual approval) → Production (manual)
```

Each promotion gate runs the relevant test suite. You cannot skip Integration to go straight to Staging.

### Monitoring and Observability

After tests run, results are accessible in multiple places:

| Channel | What it shows | Access |
|---|---|---|
| GitHub Actions | CI pass/fail per commit | PR page → Checks tab |
| HTML report | Full test output, stack traces | `reports/test_report.html` |
| Allure Report | Rich trends, categories, history | `allure serve reports/allure-results` |
| Coverage | Line-by-line coverage analysis | `htmlcov/index.html` |
| JUnit XML | Machine-readable for CI tools | `reports/*.xml` |
| MongoDB | Historical test data, trends | `db.test_results.find(...)` |
| Grafana | Service metrics (Redis ops, Kafka lag, API latency) | `http://localhost:3000` |

**Report generation (all at once):**
```bash
pytest tests/ \
  --cov=src \
  --cov-report=html:reports/coverage \
  --cov-report=xml:reports/coverage.xml \
  --html=reports/test_report.html \
  --self-contained-html \
  --junitxml=reports/results.xml \
  --alluredir=reports/allure-results \
  -v

# Generate Allure HTML
allure serve reports/allure-results
```

**Report cleanup:**
```bash
# Reports auto-clean before each test run (via tests/conftest.py)

# Manual cleanup
python scripts/clean_reports.py

# View reports
open reports/test_report.html
allure serve reports/allure-results
```

---

## 10. Interview Reference: Key Concepts and Questions

### Architecture Questions

**Q: Why use a service abstraction layer instead of direct imports?**  
A: The abstraction (abstract base classes + mock/real pairs) means test code is independent of infrastructure. Tests written against the mock work identically against real services. You can move from offline development to a full Kubernetes environment without changing a single test line. It also enforces interface contracts — if Redis adds a new method we want to use, we add it to `CacheClient`, and both mock and real clients must implement it.

**Q: What is the circuit breaker for, and how does it work?**  
A: It prevents cascading failures. If the Netskope API is down, repeated calls will each wait for the TCP timeout before failing — under load this can exhaust connection pools and make the entire test suite hang. The circuit breaker tracks consecutive failures. After 5 failures it "opens" — for the next 60 seconds, calls fail immediately (fast-fail) without hitting the service. After 60 seconds it enters HALF_OPEN, allows one probe call, and closes if that succeeds. This pattern is standard in resilient distributed systems (Netflix Hystrix, Resilience4j).

**Q: What is the difference between integration and E2E tests in this framework?**  
A: Integration tests verify that a single service works in isolation — "can the RealCacheClient connect to Redis and write/read a key?" E2E tests verify a complete business workflow across all services — "when a security event is detected, does it flow correctly through Redis → Kafka → MongoDB → API?" The E2E tests skip automatically unless `TESTING_MODE=integration`.

**Q: How does environment detection work?**  
A: The `EnvironmentManager.detect_environment()` method walks a priority chain: (1) `TESTING_MODE` env var always wins; (2) presence of `KUBERNETES_SERVICE_HOST` indicates K8s, then `ENVIRONMENT` var disambiguates staging/production/integration; (3) `/.dockerenv` indicates Docker; (4) TCP connectivity to localhost:6379/9092/27017 indicates local Docker Compose; (5) presence of config YAML files; (6) default to Mock.

### Testing Methodology Questions

**Q: How do you test security features without real credentials?**  
A: The mock API client (`MockAPIClient`) returns controlled, pre-defined JSON responses. For injection tests, the mock returns `{"status": "error"}` for malicious payloads — the test asserts the response contains an error, verifying the API contract rejects bad input. For authentication tests, `authenticate({})` returns `False`. This lets the security test suite validate the expected API behaviour and contract without hitting a real endpoint.

**Q: Why does `TESTING_MODE=mock pytest tests/unit/` matter?**  
A: Without it, environment detection may pick up `config/local.yaml` (which is committed to the repo) and return `LOCAL` — the `ServiceManager` would then try to connect to a real Redis. Setting `TESTING_MODE=mock` forces the environment before detection runs.

**Q: What is the test pyramid, and how does this framework implement it?**  
A: The test pyramid has many fast/cheap unit tests at the base, fewer integration tests in the middle, and a small number of slow/expensive E2E tests at the top. This framework maps directly: 116 unit tests (seconds, no dependencies), ~10 integration tests (minutes, Docker), ~6 E2E scenarios (slow, Kubernetes required). The pyramid shape ensures fast feedback for developers while still covering full system behaviour.

### CI/CD Questions

**Q: What happens when I push a commit?**  
A: Two GitHub Actions workflows trigger in parallel: `unit-tests.yml` (runs pytest across Python 3.9/3.10/3.11) and `security-scan.yml` (runs Bandit, Semgrep, dependency scan, secret scan). Both must pass for the PR to merge. On merge to `main`, `deployment.yml` deploys to the Integration Kubernetes cluster.

**Q: How does staging deployment get approved?**  
A: The `deployment.yml` workflow uses `environment: staging`. In GitHub repository settings, the `staging` environment has required reviewers configured. When the deployment job starts, GitHub pauses it and sends a notification to the required reviewers. Only after a reviewer approves does the job continue and apply the Kubernetes manifests.

**Q: What does `-x` in the integration test command do and why is it there?**  
A: `-x` tells pytest to stop after the first failure. Integration tests are expensive (they require running Docker services). If Redis is unreachable, every test that touches the cache will fail. Running all 50 tests to completion wastes time and produces a misleading report. Stop on first failure, collect the service logs (see the `collect service logs on failure` step), and fix the root cause.

### Software Engineering Questions

**Q: What design patterns does this framework use?**  
A: Strategy (mock vs real clients, same interface), Singleton (EnvironmentManager, ServiceManager), Factory (ServiceManager creates correct client for environment), Abstract Factory (the `get_*_client()` family), Decorator (`@circuit_breaker`), Observer (pytest hooks in test_result_logger), Template Method (abstract base classes define the contract).

**Q: How would you extend this to support a new service, say Elasticsearch?**  
A: (1) Add `ElasticsearchClient(ABC)` to `service_manager.py` with abstract `index`, `search`, `delete_document` methods. (2) Implement `MockElasticsearchClient` using a Python dict. (3) Implement `RealElasticsearchClient` in `real_service_clients.py`. (4) Add `elasticsearch` to `ServiceConfig` in `EnvironmentConfig`. (5) Add per-environment config to the YAML files. (6) Add `get_elasticsearch_client()` factory to `ServiceManager`. (7) Write unit tests in `tests/unit/test_service_manager.py`. The rest of the framework picks it up automatically.

**Q: What is "shift-left" testing?**  
A: Running tests and security scans as early as possible in the development cycle, ideally before code is merged. In this framework, unit tests and security scans run on every push to a branch, catching bugs and vulnerabilities when they are cheapest to fix — during development, not in a pre-release audit.

### Commands Cheat Sheet

```bash
# Zero-setup start
TESTING_MODE=mock pytest tests/unit/ -v

# With all reports
TESTING_MODE=mock pytest tests/unit/ \
  --cov=src --cov-report=html --html=reports/unit.html \
  --junitxml=reports/unit.xml --alluredir=reports/allure-results -v

# View Allure report
allure serve reports/allure-results

# Local with Docker
docker-compose -f docker-compose.local.yml up -d
TESTING_MODE=local pytest tests/integration/test_local_environment.py -v

# Security
TESTING_MODE=mock pytest tests/security/ -v

# Domain tests
TESTING_MODE=mock pytest tests/swg/ tests/dlp/ tests/ztna/ tests/firewall/ -v

# E2E (requires Kubernetes)
day1-sdet integration deploy
TESTING_MODE=integration pytest tests/e2e/ -v -m "e2e and not slow"

# Performance security tests
TESTING_MODE=mock pytest tests/performance/test_security_performance.py -v
TESTING_MODE=mock pytest tests/performance/ -m "performance and security" -v

# Performance load tests
jmeter -n -t tests/performance/jmeter/netskope_api_load_test.jmx \
  -Jusers=50 -Jramp_time=60 -Jduration=300 \
  -l reports/jmeter.jtl -e -o reports/jmeter_report

# Test quality checks
python scripts/detect_flaky_tests.py --min-runs 5 --fail-on-flaky
python scripts/analyze_test_metrics.py
python scripts/check_coverage.py --threshold 80
python scripts/check_documentation.py
python scripts/run_quality_checks.py

# Full environment health check
day1-sdet env validate
day1-sdet services health

# View test results in MongoDB
mongosh "mongodb://admin:admin_2024@localhost:27017/day1_local?authSource=admin"
# db.test_results.find({status:"failed"}).sort({start_time:-1})
```
## day_one_framework.egg-info
It's a Python packaging artifact generated by setuptools when you run pip install -e ..

day_one_framework.egg-info/
├── PKG-INFO          # Package metadata (name, version, author, etc.)
├── SOURCES.txt       # List of all source files included in the package
├── dependency_links.txt
├── top_level.txt     # Top-level package names
└── requires.txt      # Dependencies

What it's for:
- Tells pip and other tools which files belong to the package
- Used by pip list to show installed packages
- Required for uploading to PyPI

When it gets created:
pip install -e .   # creates/updates egg-info/
python setup.py egg_info  # also creates it

Should you commit it?
Typically no — it's generated. Add it to .gitignore:
*.egg-info/
The project's real documentation lives in docs/ (architecture, guides, etc.) and README.md.
