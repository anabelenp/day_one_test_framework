```markdown
# DLP Testing — Day-1 Framework

This document describes the DLP (Data Loss Prevention) test scenarios implemented under `tests/dlp/` and how to run and extend them.

## Purpose

- Validate DLP detection logic and policy enforcement patterns.
- Verify integration with the framework's logging/storage layer (MongoDB via `ServiceManager`).
- Exercise edge-cases: large files, policy updates, and case-sensitivity.

## Implemented Scenarios

- `test_dlp_parametric` — parameterized checks for blocked patterns (SSN, CreditCard), empty files, and case-sensitivity observations.
- `test_dlp_policy_update_affects_decision` — mutate in-memory policy and assert runtime decision changes.
- `test_dlp_large_file_detection` — verify detection works for very large payloads.
- `test_dlp_integration_with_nosql_logging` — verify decisions are persisted through the `tests/utils/nosql_helper.py` client (using mock DB in test mode).

Files added:

- `tests/dlp/test_dlp_scenarios.py` — new comprehensive scenarios
- `tests/dlp/conftest.py` — forces `TESTING_MODE=mock` during the DLP test run (so tests use mock clients by default)

## How to run

Run only DLP tests (recommended during development):

```bash
python -m pytest tests/dlp -q
```

Run within CI or with real services:

- If you want the tests to exercise real service clients, unset or change `TESTING_MODE` so `ServiceManager` creates `Real*` clients and ensure local services are available (MongoDB on 27017, Kafka, Redis, etc.).

Example (local stack up):

```bash
docker-compose -f docker-compose.local.yml up -d
export TESTING_MODE=local
python -m pytest tests/dlp -q
```

## Notes & Observations

- The current in-repo DLP matcher (`tests/utils/api_client.py`) does simple substring matches against patterns in `config/policies.json` (case-sensitive). Consider normalizing patterns or performing regex-based matching for production parity.
- Tests use the framework's `nosql_helper` which fetches a DB client from `ServiceManager`. By forcing `TESTING_MODE=mock` in `tests/dlp/conftest.py`, tests run without external DB dependencies.
- For CI, run DLP tests in mock mode for fast, reliable results; add a separate integration job to run them against the real stack.

## Extending DLP Tests

- Add binary/file-type tests: create fixture that supplies binary payloads (e.g., PDFs) and assert detection or bypass rules.
- Add contextual rules: simulate metadata (user, department, location) and assert policy decisions vary accordingly.
- Add false-positive regression tests: collect known FP inputs and assert `allow` to keep the false-positive rate low.

---

If you'd like, I can also:

- add CI matrix entries to run DLP tests in mock and integration modes, or
- convert `api_client.check_file_content` to regex/CIC-based matching and add tests to assert regex boundaries.

```
