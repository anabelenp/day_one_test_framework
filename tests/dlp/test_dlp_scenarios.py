import pytest
from tests.utils.api_client import NetskopeAPIClient
from tests.utils.nosql_helper import insert_log, find_document


@pytest.fixture
def client():
    return NetskopeAPIClient()


@pytest.mark.parametrize("content,expected", [
    ("This contains SSN 123-45-6789", "block"),
    ("Safe content with no PII", "allow"),
    ("User provided CreditCard 4111-1111-1111-1111", "block"),
    ("ssn in lowercase 123-45-6789", "allow"),  # current implementation is case-sensitive
    ("", "allow"),
])
def test_dlp_parametric(client, content, expected):
    """Parametric checks for DLP patterns and basic logging into the DB."""
    result = client.check_file_content(content)
    # Log a short sample of the content for analytics
    insert_log({"sample": content[:120], "action": result})
    assert result == expected


def test_dlp_policy_update_affects_decision(client):
    """Ensure policy updates on the client affect DLP decisions at runtime."""
    sample = "Contains SSN 000-00-0000"
    assert client.check_file_content(sample) == "block"

    # Remove SSN from blocked patterns and ensure the decision changes
    original = list(client.policies['dlp']['blocked_patterns'])
    try:
        client.policies['dlp']['blocked_patterns'] = [p for p in original if p != 'SSN']
        assert client.check_file_content(sample) == "allow"
    finally:
        client.policies['dlp']['blocked_patterns'] = original


def test_dlp_large_file_detection(client):
    """Large file that contains a blocked pattern should still be detected."""
    large_body = ("SafeLine\n" * 10000) + "Some text SSN 123-45-6789 trailing"
    result = client.check_file_content(large_body)
    assert result == "block"


def test_dlp_integration_with_nosql_logging(client):
    """Verify that DLP decisions are persisted using the test DB client."""
    filename = "sensitive_doc.txt"
    content = "This file contains CreditCard 4111-1111-1111-1111"
    action = client.check_file_content(content)

    doc_id = insert_log({"file": filename, "action": action})
    assert doc_id is not None

    # Ensure a document can be retrieved from the mock DB
    found = find_document("logs", {"file": filename})
    assert found is not None
    assert found.get("action") == action
