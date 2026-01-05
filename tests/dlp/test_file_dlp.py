import pytest
from tests.utils.api_client import NetskopeAPIClient
from tests.utils.nosql_helper import insert_log

client = NetskopeAPIClient()

def test_dlp_blocking():
    files = {"file1.txt": "This contains SSN 123-45-6789", "file2.txt": "Safe content"}
    results = {}
    for fname, content in files.items():
        result = client.check_file_content(content)
        results[fname] = result
        insert_log({"file": fname, "action": result})

    assert results["file1.txt"] == "block"
    assert results["file2.txt"] == "allow"
