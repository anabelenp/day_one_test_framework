# Test Reporting Guide

This document describes all methods for generating and viewing test reports in the Day-1 SDET Framework.

## Report Types

| Type | Format | Use Case |
|------|--------|----------|
| HTML Report | Standalone `.html` | Human-readable, shareable results |
| Allure Report | Rich `.html` with trends | Visual trends, categories, history |
| Coverage Report | HTML + XML | Code coverage analysis |
| JUnit XML | `.xml` | CI/CD integration, GitHub Actions |
| MongoDB | Collections | Historical trends, analytics |

---

## 1. HTML Reports

Generates a standalone HTML file viewable in any browser.

```bash
# Single command
pytest tests/ --html=reports/test_report.html --self-contained-html

# Via CLI
day1-sdet test unit --html-report
```

### Viewing Reports

```bash
# macOS
open reports/test_report.html

# Linux
xdg-open reports/test_report.html

# Or serve with a simple HTTP server
python -m http.server 8000 --directory reports
```

---

## 2. Allure Reports

Allure provides rich, interactive test reports with trends, categories, and history.

### Installation

```bash
# Install Allure (requires Java)
brew install allure  # macOS
# or: scoop install allure  # Windows
# or: apt install allure  # Ubuntu/Debian

# Install Python adapter
pip install allure-pytest
```

### Generate Reports

```bash
# Run tests (results saved to reports/allure-results/)
pytest tests/unit/ -v

# Generate HTML report from results
allure serve reports/allure-results

# Or generate static report
allure generate reports/allure-results -o reports/allure-report --clean
```

### View Reports

```bash
# Serve report locally (opens in browser)
allure serve reports/allure-results

# Serve specific report
allure serve reports/allure-results --port 9000

# Open static report
open reports/allure-report/index.html
```

### Features

- **Trends**: Track pass/fail rates over time
- **Categories**: Group failures by type (Product Defects, Test Defects, etc.)
- **History**: Compare with previous runs
- **Attachments**: Screenshots, logs, stdout
- **Timeline**: See test execution timeline
- **Behaviors**: Group tests by feature/epic

### GitHub Actions Integration

```yaml
- name: Generate Allure Report
  if: always()
  run: |
    allure generate reports/allure-results -o reports/allure-report --clean

- name: Upload Allure Report
  uses: actions/upload-artifact@v3
  if: always()
  with:
    name: allure-report
    path: reports/allure-report
```

---

## 3. Code Coverage Reports

Uses `pytest-cov` to measure code coverage.

```bash
# Terminal output with missing lines
pytest tests/unit/ --cov=src --cov-report=term-missing

# HTML report (interactive)
pytest tests/ --cov=src --cov-report=html

# XML for CI tools (Cobertura format)
pytest tests/ --cov=src --cov-report=xml

# Multiple formats at once
pytest tests/ --cov=src --cov-report=html --cov-report=xml --cov-report=term-missing
```

### Viewing HTML Coverage

```bash
open htmlcov/index.html
```

---

## 4. JUnit XML Reports

Machine-readable format for CI/CD tools like GitHub Actions, Jenkins, CircleCI.

```bash
# Single file
pytest tests/ --junitxml=reports/junit.xml

# Per-suite (useful for Jenkins)
pytest tests/unit/ --junitxml=reports/unit-results.xml
pytest tests/integration/ --junitxml=reports/integration-results.xml
pytest tests/e2e/ --junitxml=reports/e2e-results.xml
```

### GitHub Actions Example

```yaml
- name: Run tests
  run: pytest tests/ --junitxml=reports/results.xml

- name: Publish test results
  uses: dorny/test-reporter@v1
  with:
    name: Test Results
    path: reports/results.xml
    reporter: jest-junit
```

### Jenkins Example

```groovy
post {
    always {
        junit 'reports/*.xml'
    }
}
```

---

## 5. MongoDB Test Analytics

Every pytest run automatically logs results to MongoDB via `src/test_result_logger.py`.

### Collections

| Collection | Contents |
|------------|----------|
| `test_results` | One document per test (name, status, duration, error) |
| `test_sessions` | Session summary (timestamp, pass/fail/skip counts) |

### Querying Results

```bash
mongosh "mongodb://admin:admin_2024@localhost:27017/day1_local?authSource=admin"
```

```javascript
// Last 10 test results
db.test_results.find().sort({start_time: -1}).limit(10)

// Failed tests only
db.test_results.find({status: "failed"}).sort({start_time: -1})

// Average duration per test
db.test_results.aggregate([
  {$group: {
    _id: "$test_name",
    avg_ms: {$avg: "$duration"},
    runs: {$sum: 1}
  }}
])

// Success rate analysis
db.test_results.aggregate([
  {$group: {
    _id: "$status",
    count: {$sum: 1}
  }}
])

// Session summaries
db.test_sessions.find().sort({timestamp: -1}).limit(5)

// Flaky tests (tests that pass and fail across sessions)
db.test_results.aggregate([
  {$group: {
    _id: {test_name: "$test_name", status: "$status"},
    count: {$sum: 1}
  }},
  {$group: {
    _id: "$_id.test_name",
    statuses: {$push: {status: "$_id.status", count: "$count"}}
  }},
  {$match: {$expr: {$gt: [{$size: "$statuses"}, 1]}}}
])
```

---

## 6. Complete Report Command

Generate all reports at once:

```bash
pytest tests/unit/ \
  --cov=src \
  --cov-report=html:reports/coverage \
  --cov-report=xml:reports/coverage.xml \
  --html=reports/unit-report.html \
  --self-contained-html \
  --junitxml=reports/unit-results.xml \
  -v
```

---

## 7. CI/CD Integration

### GitHub Actions Workflow

See `.github/workflows/unit-tests.yml`:

```yaml
- name: Run unit tests
  run: |
    pytest tests/unit/ \
      --cov=src \
      --cov-report=xml \
      --cov-report=html \
      --html=reports/unit-test-report.html \
      --junitxml=reports/unit-test-results.xml \
      -v

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

### Jenkins Pipeline

See `Jenkinsfile`:

```groovy
stage('Unit Tests') {
    steps {
        sh '''
            pytest tests/unit/ \
                --cov=src \
                --cov-report=xml \
                --cov-report=html \
                --html=reports/unit-test-report.html \
                --junitxml=reports/unit-test-results.xml \
                -v
        '''
    }
    post {
        always {
            junit 'reports/*.xml'
            publishHTML([
                allowMissing: false,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'htmlcov',
                reportFiles: 'index.html',
                reportName: 'Coverage Report'
            ])
        }
    }
}
```

---

## 8. JMeter Load Test Reports

For performance testing with JMeter:

```bash
jmeter -n \
  -t tests/performance/jmeter/netskope_api_load_test.jmx \
  -Jusers=50 \
  -Jramp_time=60 \
  -Jduration=300 \
  -l reports/jmeter_results.jtl \
  -e -o reports/jmeter_report
```

Outputs:
- `reports/jmeter_results.jtl` — raw results (CSV)
- `reports/jmeter_report/` — HTML dashboard

---

## 9. Locust Reports

For Locust load tests:

```bash
# Headless (CI)
locust -f tests/performance/locust/netskope_load_test.py \
  --host=http://localhost:8080 \
  --users=50 \
  --spawn-rate=5 \
  --run-time=300s \
  --headless \
  --csv=reports/locust_results

# Interactive (generates HTML on shutdown)
locust -f tests/performance/locust/netskope_load_test.py \
  --host=http://localhost:8080
# Open http://localhost:8089, run test, download report
```

---

## 10. Test Result Logger Configuration

The `src/test_result_logger.py` hooks into pytest automatically via `conftest.py`. It silently skips if MongoDB is unavailable.

```python
# src/test_result_logger.py hooks:
pytest_sessionstart       # Log session start
pytest_runtest_setup      # Log test start
pytest_runtest_logreport  # Update status/duration on completion
pytest_sessionfinish      # Log session summary
```

No configuration required — runs on every `pytest` invocation.

---

## 11. Test Quality Reports

### Flaky Test Detection

Detect tests that pass and fail inconsistently using the flaky test detector:

```bash
# Basic detection
python scripts/detect_flaky_tests.py

# With custom parameters
python scripts/detect_flaky_tests.py \
  --min-runs 5 \
  --stability-threshold 0.8 \
  --hours 168

# JSON output for CI
python scripts/detect_flaky_tests.py \
  --format json \
  --output reports/flaky-test-report.json

# Fail CI if flaky tests found
python scripts/detect_flaky_tests.py \
  --fail-on-flaky \
  --threshold 5
```

**Flaky test criteria:**
- Has been run at least `--min-runs` times
- Has both passed and failed results
- Pass rate between stability thresholds

### Test Metrics Analysis

Generate test metrics from MongoDB:

```bash
# Analyze test metrics
python scripts/analyze_test_metrics.py

# Output: reports/test-metrics.json
{
  "total_runs": 150,
  "passed": 145,
  "failed": 3,
  "skipped": 2,
  "success_rate": 96.7,
  "avg_duration_seconds": 0.45,
  "sessions": 12
}
```

### Code Quality Reports

```bash
# Run all quality checks
python scripts/run_quality_checks.py

# Check documentation coverage
python scripts/check_documentation.py

# Check code complexity
python scripts/check_complexity.py

# Coverage threshold check
python scripts/check_coverage.py --threshold 80
```

### CI/CD Quality Pipeline

The `test-quality.yml` workflow runs daily and generates:

| Artifact | Contents |
|---------|---------|
| `flaky-test-report.json` | Tests with inconsistent pass/fail history |
| `test-metrics.json` | Success rate, duration analysis |
| Code quality checks | flake8, black, mypy results |

Access in GitHub Actions → Artifacts after workflow run.

---

## 12. Quick Reference

| Report Type | Command |
|-------------|---------|
| HTML | `pytest --html=reports/report.html --self-contained-html` |
| Allure | `pytest` + `allure serve reports/allure-results` |
| Coverage | `pytest --cov=src --cov-report=html --cov-report=xml` |
| JUnit XML | `pytest --junitxml=reports/results.xml` |
| MongoDB | Automatic (requires MongoDB connection) |
| JMeter | `jmeter -n -t test.jmx -l results.jtl -e -o report/` |
| Locust | `locust -f test.py --csv=results --headless` |
| Flaky Tests | `python scripts/detect_flaky_tests.py` |
| Test Metrics | `python scripts/analyze_test_metrics.py` |
| Coverage Gate | `python scripts/check_coverage.py --threshold 80` |
| Code Quality | `python scripts/run_quality_checks.py` |


---

## 13. Report Management

### Automatic Cleanup

Reports are automatically cleaned before each test run via `tests/conftest.py`:

```python
@pytest.fixture(scope="session", autouse=True)
def clean_reports_dir():
    """Clean reports directory before test session."""
    # Removes old reports, creates fresh directories
```

**Generated reports after each run:**
```
reports/
├── test_report.html      # HTML report (generated fresh)
└── allure-results/       # Allure raw data (generated fresh)
```

### Manual Cleanup

To manually clean reports:

```bash
# Clean all reports
python scripts/clean_reports.py

# Clean including allure-report
python scripts/clean_reports.py --all

# Manual cleanup
rm -rf reports/*
```

### Running Tests with Reports

**pytest.ini** already configures default report locations:
```ini
addopts =
    --html=reports/test_report.html
    --self-contained-html
    --alluredir=reports/allure-results
```

**Run with all reports:**
```bash
# Integration tests with full reporting
TESTING_MODE=local pytest tests/integration/ \
  --html=reports/test_report.html \
  --self-contained-html \
  --alluredir=reports/allure-results \
  --cov=src \
  --cov-report=html \
  --cov-report=xml \
  --junitxml=reports/results.xml \
  -v
```

**View reports:**
```bash
# Open HTML report
open reports/test_report.html

# Serve Allure report
allure serve reports/allure-results

# Generate static Allure HTML
allure generate reports/allure-results -o reports/allure-report --clean
open reports/allure-report/index.html
```

---

## Dependencies

```bash
pip install pytest pytest-html pytest-cov pytest-xdist allure-pytest
```

Listed in `requirements.txt`:
```
pytest>=9.0.0
pytest-html>=4.2.0
allure-pytest>=2.14.0
pytest-cov>=4.0.0
pytest-xdist>=3.0.0
```

Listed in `setup.py` extras:
```python
extras_require={
    'dev': ['pytest-cov>=4.0.0', 'pytest-xdist>=3.0.0'],
}
```
