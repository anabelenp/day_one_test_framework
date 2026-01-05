import pytest
from concurrent.futures import ThreadPoolExecutor
from tests.utils.api_client import NetskopeAPIClient
from tests.utils.kafka_helper import publish_event
from tests.utils.redis_helper import set_key
from tests.utils.nosql_helper import insert_log

client = NetskopeAPIClient()
NUM_USERS = 1000

def simulate_user(user_id):
    url_result = client.check_url("example.com" if user_id % 2 == 0 else "safe.com")
    content = "This contains SSN" if user_id % 3 == 0 else "Safe content"
    dlp_result = client.check_file_content(content)
    app_result = client.check_app_access(f"user{user_id}", "admin_portal" if user_id % 5 == 0 else "email_app")
    publish_event("netskope_events", f"user{user_id}:{url_result},{dlp_result},{app_result}")
    set_key(f"user{user_id}_status", f"{url_result},{dlp_result},{app_result}")
    insert_log({
        "user_id": user_id,
        "url_result": url_result,
        "dlp_result": dlp_result,
        "app_result": app_result
    })
    return (url_result, dlp_result, app_result)

def test_load_simulation():
    results = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(simulate_user, i) for i in range(NUM_USERS)]
        for f in futures:
            results.append(f.result())
    swg_blocks = [res[0] for res in results if res[0] == "block"]
    assert len(swg_blocks) > 0
