# Mock Responses Directory

This directory contains mock API responses for testing without real Netskope credentials.

## Purpose

- **Local Development**: Test the framework without needing production API access
- **CI/CD Testing**: Run automated tests in pipelines without credentials
- **Learning**: Understand the framework behavior with sample data
- **Offline Testing**: Work without internet connectivity

## Mock Mode

When `MOCK_MODE: true` is set in `config/env.yaml`, the framework will:
- Use local mock servers instead of real APIs
- Return predefined responses from this directory
- Simulate realistic API behavior and latency
- Generate random test data for comprehensive testing

## Structure

```
mock_responses/
├── swg/          # Secure Web Gateway mock responses
├── dlp/          # Data Loss Prevention mock responses
├── ztna/         # Zero Trust Network Access mock responses
├── firewall/     # Firewall mock responses
└── common/       # Common API responses (auth, users, etc.)
```

## Usage

The API client automatically detects mock mode and uses these responses.
No code changes needed - just set `MOCK_MODE: true` in config.
