import pytest
from tests.utils.api_client import NetskopeAPIClient
from tests.utils.nosql_helper import insert_log

client = NetskopeAPIClient()

def test_url_blocking():
    urls = ["example.com", "safe.com"]
    results = {}
    for url in urls:
        result = client.check_url(url)
        results[url] = result
        insert_log({"url": url, "action": result})
    
    assert results["example.com"] == "block"
    assert results["safe.com"] == "allow"
