import pytest
from tests.utils.api_client import NetskopeAPIClient

client = NetskopeAPIClient()

def test_firewall_ports():
    assert client.check_port(22) == "block"
    assert client.check_port(80) == "allow"
