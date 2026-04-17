# Day-1 SDET Automation Framework

Python testing framework for cloud security products (SWG, CASB, DLP, ZTNA, Firewall). The same test code runs against in-memory mocks, local Docker services, or Kubernetes clusters — controlled by a single environment variable.

## Prerequisites

- Python 3.9+
- Docker Desktop (for local/integration environments)
- `kubectl` (for Kubernetes environments only)

## Setup

```bash
git clone <repo_url>
cd day_one_test_framework

python -m venv .venv && source .venv/bin/activate

pip install -e .                 # registers the day1-sdet CLI command
pip install -r requirements.txt
```

Verify:
```bash
python -c "from src.environment_manager import get_current_environment; print(get_current_environment().value)"
```

> `day1-sdet <cmd>` and `python src/cli.py <cmd>` are equivalent. Use `python src/cli.py` if the package is not installed.

## Run Tests

`config/local.yaml` is committed, so always set `TESTING_MODE=mock` for unit tests to prevent the framework from attempting real service connections.

```bash
# Unit tests — no external dependencies
TESTING_MODE=mock pytest tests/unit/ -v

# Single test
TESTING_MODE=mock pytest tests/unit/test_circuit_breaker.py::TestCircuitBreaker::test_trip_after_failure_threshold -v

# Coverage
TESTING_MODE=mock pytest tests/unit/ --cov=src --cov-report=term-missing

# Security tests
TESTING_MODE=mock pytest tests/security/ -v

# Domain tests (SWG, DLP, ZTNA, Firewall)
TESTING_MODE=mock pytest tests/swg/ tests/dlp/ tests/ztna/ tests/firewall/ -v

# Filter by marker
TESTING_MODE=mock pytest -m "not slow" -v
TESTING_MODE=mock pytest -m "security or unit" -v
```

Markers (`pyproject.toml`): `unit`, `integration`, `e2e`, `performance`, `security`, `smoke`, `slow`, `load`, `staging`, `mock`.

## Environments

| Env | Value | Services | When to use |
|-----|-------|----------|-------------|
| Mock (E1) | `mock` | In-memory Python objects | Unit tests, CI without Docker |
| Local (E2) | `local` | Docker Compose | Integration tests on dev machine |
| Integration (E3) | `integration` | Kubernetes single-node | E2E tests, pre-merge CI |
| Staging (E4) | `staging` | Kubernetes HA | Load tests, pre-production |
| Production (E5) | `production` | Live — read-only | Health monitoring only |

Switch environment:
```bash
export TESTING_MODE=mock          # or local / integration / staging / production
day1-sdet env detect          # confirm what was detected
day1-sdet env validate        # check config completeness + TCP connectivity
```

## Local Environment (Docker Compose)

`docker-compose.yml` at the root is a legacy file using Zookeeper-based Kafka — do not use it. Always use `docker-compose.local.yml`.

```bash
# Start
docker-compose -f docker-compose.local.yml up -d

# Check services are healthy
docker-compose -f docker-compose.local.yml ps
TESTING_MODE=local day1-sdet services health

# Run local integration tests (requires Docker Compose)
TESTING_MODE=local pytest tests/integration/test_local_environment.py -v

# Run E2E tests (auto-skip if TESTING_MODE != integration)
TESTING_MODE=integration pytest tests/e2e/ -v

# Tear down
docker-compose -f docker-compose.local.yml down
docker-compose -f docker-compose.local.yml down --volumes  # clean slate
```

Services started:

| Service | Port | Credentials |
|---------|------|-------------|
| Redis 7 | 6379 | — |
| Kafka (KRaft) | 9092 | — |
| MongoDB 6 | 27017 | admin / admin_2024 |
| Mock Target API (nginx) | 8080 | — |
| LocalStack (AWS) | 4566 | — |
| Prometheus | 9090 | — |
| Grafana | 3000 | admin / grafana_2024 |
| Jaeger | 16686 | — |

## Kubernetes Environments

```bash
# Integration
day1-sdet integration deploy
day1-sdet integration status
TESTING_MODE=integration pytest tests/e2e/ -v
day1-sdet integration undeploy

# Staging (HA)
day1-sdet staging deploy
day1-sdet staging test --test-type load
day1-sdet staging undeploy

# Production (read-only)
day1-sdet production health-check
day1-sdet production monitor --interval 300
day1-sdet production report --output health.json
```

Port-forward services from K8s to localhost:
```bash
kubectl port-forward -n day1-integration svc/grafana-service 3000:3000
kubectl port-forward -n day1-integration svc/prometheus-service 9090:9090
```

## Performance Tests

```bash
# Python-based
TESTING_MODE=local pytest tests/performance/ -v

# JMeter
jmeter -n \
  -t tests/performance/jmeter/netskope_api_load_test.jmx \
  -Jusers=50 -Jramp_time=60 -Jduration=300 \
  -l reports/jmeter_results.jtl -e -o reports/jmeter_report

# Locust (headless)
locust -f tests/performance/locust/netskope_load_test.py \
  --host=http://localhost:8080 \
  --users=50 --spawn-rate=5 --run-time=300s \
  --headless --csv=reports/locust_results

# Locust (interactive UI at http://localhost:8089)
locust -f tests/performance/locust/netskope_load_test.py --host=http://localhost:8080
```

## Reports

```bash
pytest tests/ --html=reports/test_report.html --self-contained-html
pytest tests/ --junitxml=reports/junit.xml
pytest tests/ --cov=src --cov-report=html
```

All `pytest` runs automatically log results to MongoDB (`test_results` and `test_sessions` collections) when MongoDB is reachable; silently skipped otherwise.

```bash
mongosh "mongodb://admin:admin_2024@localhost:27017/day1_local?authSource=admin"

# Recent failures
db.test_results.find({status: "failed"}).sort({start_time: -1}).limit(10)

# Per-test average duration
db.test_results.aggregate([{$group: {_id: "$test_name", avg_ms: {$avg: "$duration"}}}])

# Session summaries
db.test_sessions.find().sort({timestamp: -1}).limit(5)
```

## CLI Reference

```bash
day1-sdet env detect|info|validate|list|set
day1-sdet services health|info|test <cache|message|database|api>
day1-sdet local start|stop|restart|status
day1-sdet integration deploy|status|test|undeploy
day1-sdet staging deploy|status|test|undeploy
day1-sdet production health-check|monitor|report
day1-sdet test <unit|integration|e2e|security|performance> [-e <env>] [--html-report] [--coverage] [--markers "<expr>"]
day1-sdet version
```

## CI/CD

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `unit-tests.yml` | push / PR to `main`, `develop` | pytest matrix across Python 3.9–3.11, uploads coverage |
| `integration-tests.yml` | push / PR + daily 02:00 UTC | Docker Compose up → integration + E2E tests → down; opens GitHub issue on scheduled failure |
| `security-scan.yml` | push / PR + daily 03:00 UTC | Bandit, Semgrep (OWASP), Safety, pip-audit, TruffleHog, Gitleaks, CodeQL |
| `deployment.yml` | push to `main` → integration; version tag → staging (requires approval) | `kubectl apply` + smoke tests |
| `performance-jmeter.yml` | manual | JMeter load tests |

Deployment to staging uses GitHub environment protection rules (`environment: staging`). Configure required reviewers in repository Settings → Environments.

## Troubleshooting

**Unit tests try to connect to Redis/MongoDB:**  
`config/local.yaml` is committed and triggers LOCAL detection. Set `TESTING_MODE=mock` explicitly.

**"production" detected instead of "local":**  
`export TESTING_MODE=local` — the env var takes highest priority.

**Services unhealthy after `docker-compose up`:**  
```bash
docker-compose -f docker-compose.local.yml ps   # check state
docker-compose -f docker-compose.local.yml logs kafka  # inspect logs
docker-compose -f docker-compose.local.yml restart
```

**E2E tests all skip:**  
They require `TESTING_MODE=integration`. They intentionally skip in mock and local modes.

**Kafka import errors in local mode:**  
Expected — the framework falls back to the mock Kafka client if `kafka-python` is not installed or the broker is unreachable.

See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for additional scenarios.

## Documentation

| Document | Contents |
|----------|----------|
| [architecture.md](docs/architecture.md) | System design and component diagrams |
| [testing_strategy.md](docs/testing_strategy.md) | Test pyramid and testing approach |
| [environment_setup.md](docs/environment_setup.md) | Per-environment configuration detail |
| [integration_environment_guide.md](docs/integration_environment_guide.md) | Kubernetes integration deployment |
| [staging_environment_guide.md](docs/staging_environment_guide.md) | HA staging deployment |
| [production_environment_guide.md](docs/production_environment_guide.md) | Production monitoring setup |
| [security_testing_guide.md](docs/security_testing_guide.md) | Security test patterns |
| [PERFORMANCE_TESTING_GUIDE.md](docs/PERFORMANCE_TESTING_GUIDE.md) | JMeter and Locust usage |
| [CI_CD_INTEGRATION_GUIDE.md](docs/CI_CD_INTEGRATION_GUIDE.md) | GitHub Actions and Jenkins setup |
| [MONITORING_AND_REPORTS_GUIDE.md](docs/MONITORING_AND_REPORTS_GUIDE.md) | Prometheus, Grafana, Jaeger |
| [TEST_MONITORING_MONGODB.md](docs/TEST_MONITORING_MONGODB.md) | Test result analytics queries |
| [REPORTING.md](docs/REPORTING.md) | HTML, coverage, JUnit, MongoDB test reports |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues and fixes |
