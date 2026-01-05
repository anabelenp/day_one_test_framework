import pytest
from tests.utils.api_client import NetskopeAPIClient

client = NetskopeAPIClient()

def test_ztna_access():
    client.create_user("user1")
    assert client.check_app_access("user1", "admin_portal") == "deny"
    assert client.check_app_access("user1", "email_app") == "allow"
