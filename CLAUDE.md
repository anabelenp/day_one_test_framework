# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development guidelines

- Keep it simple. No over-engineering or unnecessary defensive programming
- Identify root cause before fixing issues. Prove with evidence, then fix.
- Work incrementally with small steps. Validate each increment.
- Use latest library APIs.
- Use 'uv' as Python package manager in Docker
- Planning docs are in '/docs'


## Essential Commands

```bash
# Install (required before using the day1-sdet CLI)
pip install -e .

# Unit tests — always prefix with TESTING_MODE=mock (see Gotchas)
TESTING_MODE=mock pytest tests/unit/ -v
TESTING_MODE=mock pytest tests/unit/test_circuit_breaker.py -v
TESTING_MODE=mock pytest tests/unit/test_circuit_breaker.py::TestCircuitBreaker::test_trip_after_failure_threshold -v

# Coverage with threshold check
TESTING_MODE=mock pytest tests/unit/ --cov=src --cov-report=term-missing
python scripts/check_coverage.py --threshold 80

# Local environment (Docker Compose)
docker-compose -f docker-compose.local.yml up -d   # NOT docker-compose.yml (that file is legacy)
TESTING_MODE=local pytest tests/integration/test_local_environment.py -v

# Security, domain, and all other pytest-based tests
TESTING_MODE=mock pytest tests/security/ -v
TESTING_MODE=mock pytest tests/swg/ tests/dlp/ tests/ztna/ tests/firewall/ -v

# Performance security tests
TESTING_MODE=mock pytest tests/performance/test_security_performance.py -v
TESTING_MODE=mock pytest tests/performance/ -m security -v

# E2E (requires Kubernetes integration environment - see Prerequisites)
TESTING_MODE=integration pytest tests/e2e/ -v

# Filter by marker (-m accepts pytest boolean expressions)
TESTING_MODE=mock pytest -m "not slow" -v
TESTING_MODE=mock pytest -m "security or unit" -v
TESTING_MODE=mock pytest -m "performance and security" -v

# CLI (day1-sdet == python src/cli.py, both take identical arguments)
day1-sdet env detect
day1-sdet services health
day1-sdet test unit --html-report --coverage

# Test quality tools
python scripts/detect_flaky_tests.py --min-runs 5 --fail-on-flaky
python scripts/analyze_test_metrics.py
python scripts/check_documentation.py
python scripts/run_quality_checks.py
```

Markers defined in `pyproject.toml`: `unit`, `integration`, `e2e`, `performance`, `security`, `smoke`, `slow`, `load`, `staging`, `mock`.

## Environment Prerequisites

**E2 (Local) - Docker Compose:**
```bash
docker-compose -f docker-compose.local.yml up -d
```
No additional setup required.

**E3 (Integration) - Kubernetes:**
Requires an existing Kubernetes cluster. Setup options:
```bash
# Minikube
minikube start

# Kind
kind create cluster --name day1-integration

# K3s
curl -sfL https://get.k3s.io | sh -

# Docker Desktop Kubernetes
# Enable in Settings → Kubernetes
```

**Tests without Kubernetes:**
- `TESTING_MODE=mock` → Unit tests (no external deps)
- `TESTING_MODE=local` → Integration tests (Docker Compose)
- `TESTING_MODE=integration` → E2E tests (requires K8s cluster)

Integration tests in `tests/integration/test_integration_environment.py` will **skip** if no Kubernetes cluster is available (expected behavior).


## CI/CD Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `unit-tests.yml` | Push/PR | Unit tests on Python 3.9-3.12, coverage gate (80%) |
| `integration-tests.yml` | Push/PR, daily | Docker Compose integration tests |
| `security-scan.yml` | Push/PR, daily | SAST (Bandit, Semgrep, CodeQL), dependency scan |
| `test-quality.yml` | Daily, manual | Flaky test detection, metrics, code quality |
| `sonar-analysis.yml` | Daily, manual | SonarCloud/sonar-scanner analysis |
| `snyk-security.yml` | Push/PR, daily | Snyk vulnerability and IaC scanning |


## Architecture

### Environment → Service abstraction

`EnvironmentManager` (`src/environment_manager.py`) detects the runtime environment and is the source of truth for all service configuration. `ServiceManager` (`src/service_manager.py`) consults it and returns the correct client implementation — mock or real — through a uniform interface.

```
Test code
  └─ get_cache_client() / get_message_client() / get_database_client() / get_api_client()
       └─ ServiceManager  ──reads──  EnvironmentManager.get_current_environment()
            ├─ MOCK  →  MockCacheClient / MockMessageClient / MockDatabaseClient / MockAPIClient
            └─ other →  RealCacheClient (redis) / RealMessageClient (kafka) /
                        RealDatabaseClient (mongodb) / RealAPIClient (http)
                        all implemented in src/real_service_clients.py
```

Abstract base classes (`CacheClient`, `MessageClient`, `DatabaseClient`, `APIClient`) live in `service_manager.py` and define the full contract both implementations must satisfy. Tests should only import through the factory functions (`get_cache_client()` etc.), never mock classes directly.

### Environment detection priority chain

`EnvironmentManager.detect_environment()` walks in order:
1. `TESTING_MODE` env var — always wins
2. `KUBERNETES_SERVICE_HOST` present → check `ENVIRONMENT` var for staging/production/integration
3. `/.dockerenv` present → LOCAL
4. TCP connectivity to ≥3 of: Redis:6379, Kafka:9092, MongoDB:27017, Prometheus:9090, Grafana:3000 → LOCAL
5. Config YAML files present → infer from which file exists
6. Default → MOCK

### Singleton patterns

`EnvironmentManager`, `ServiceManager`, `CircuitBreakerRegistry`, `PoolManager`, and `ResultLogger` are all global singletons using double-checked locking. Clients inside `ServiceManager._clients` are lazy-initialised and cached — `get_cache_client()` called twice returns the same instance. `disconnect_all()` clears the cache.

### Circuit breaker

`src/circuit_breaker.py` implements CLOSED → OPEN → HALF_OPEN states. It is currently wired only to `RealAPIClient` (in `real_service_clients.py`) via `_record_success()` / `_record_failure()` helpers called after every HTTP request. Other real clients do not yet use it.

### Test result logging

`src/test_result_logger.py` hooks into pytest via `conftest.py`. It registers `pytest_sessionstart`, `pytest_runtest_setup`, `pytest_runtest_logreport`, and `pytest_sessionfinish` to write every test result and session summary to MongoDB collections `test_results` and `test_sessions`. This runs automatically on every `pytest` invocation; if MongoDB is unavailable the logger silently no-ops.


## Critical Gotchas

**Always set `TESTING_MODE=mock` for unit tests.** `config/local.yaml` is committed to the repo. Without the env var, `detect_environment()` reaches step 5 and returns `LOCAL`, causing `ServiceManager` to attempt real Redis/Kafka/MongoDB connections.

**Use `docker-compose.local.yml`, not `docker-compose.yml`.** The root `docker-compose.yml` is a legacy file using Zookeeper-based Kafka. `docker-compose.local.yml` is the current full stack (KRaft Kafka, Redis 7, MongoDB 6, LocalStack, Prometheus, Grafana, Jaeger, nginx mock API).

**E2E tests auto-skip outside the integration environment.** The `setup_integration_environment` autouse fixture in `tests/e2e/test_integration_e2e.py` calls `pytest.skip()` unless `TESTING_MODE=integration`.

**Integration tests have two variants:**
- `tests/integration/test_local_environment.py` — requires `TESTING_MODE=local` (Docker Compose)
- `tests/integration/test_integration_environment.py` — requires `TESTING_MODE=integration` (Kubernetes)

**Mock `aggregate()` is incomplete.** `MockDatabaseClient.aggregate()` supports only `$match` and `$group` stages. Tests relying on `$project`, `$sort`, `$limit`, or `$avg` will silently return wrong results in mock mode.

**Allure pytest version compatibility.** Use `allure-pytest>=2.14.0` with pytest 9.x. Older versions (e.g., 2.13.2) have compatibility issues with `iter_parents`.


## Adding a New Service

1. Add an abstract class (e.g. `ElasticsearchClient(ServiceClient)`) to `src/service_manager.py`
2. Implement `MockElasticsearchClient` in the same file (pure Python, no I/O)
3. Implement `RealElasticsearchClient` in `src/real_service_clients.py`
4. Add `elasticsearch: ServiceConfig` to `EnvironmentConfig` in `src/environment_manager.py`
5. Add the service config block to each relevant YAML in `config/`
6. Add `get_elasticsearch_client()` factory to `ServiceManager`
7. Add unit tests in `tests/unit/test_service_manager.py`


## Helper Scripts

| Script | Purpose |
|--------|---------|
| `scripts/detect_flaky_tests.py` | Analyze MongoDB for flaky tests |
| `scripts/check_coverage.py` | Enforce coverage threshold (80%) |
| `scripts/analyze_test_metrics.py` | Generate test metrics report |
| `scripts/check_documentation.py` | Check doc coverage |
| `scripts/run_quality_checks.py` | Run flake8/black/mypy |
| `scripts/generate_quality_summary.py` | Generate GitHub summary |
| `scripts/check_complexity.py` | Analyze code complexity |
| `scripts/check_flaky_threshold.py` | Check flaky test threshold |
| `scripts/clean_reports.py` | Clean old reports directory |
