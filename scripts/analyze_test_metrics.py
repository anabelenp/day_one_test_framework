#!/usr/bin/env python3
"""
Analyze test metrics from MongoDB and generate a report.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    from pymongo import MongoClient
except ImportError:
    print("pymongo not installed - skipping metrics analysis")
    sys.exit(0)


def analyze_test_metrics():
    os.makedirs("reports", exist_ok=True)

    try:
        client = MongoClient(
            "mongodb://admin:admin_2024@localhost:27017/",
            serverSelectionTimeoutMS=5000,
        )
        client.admin.command("ping")
        db = client.day1_local
    except Exception as e:
        print(f"Could not connect to MongoDB: {e}")
        print("Writing empty metrics file")
        metrics = {
            "period": "7 days",
            "total_runs": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "success_rate": 0,
            "avg_duration_seconds": 0,
            "max_duration_seconds": 0,
            "sessions": 0,
            "status": "MongoDB not available",
        }
        with open("reports/test-metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)
        return

    cutoff = datetime.utcnow() - timedelta(days=7)
    results = list(db.test_results.find({"start_time": {"$gte": cutoff}}))

    print("## Test Metrics Summary (Last 7 Days)")

    if not results:
        print("- No test results found in the last 7 days")
        metrics = {
            "period": "7 days",
            "total_runs": 0,
            "status": "No data",
        }
        with open("reports/test-metrics.json", "w") as f:
            json.dump(metrics, f, indent=2)
        return

    total = len(results)
    passed = sum(1 for r in results if r.get("status") in ("passed", "success"))
    failed = sum(1 for r in results if r.get("status") == "failed")
    skipped = sum(1 for r in results if r.get("status") == "skipped")

    durations = [r.get("duration", 0) for r in results if r.get("duration")]
    avg_duration = sum(durations) / len(durations) if durations else 0
    max_duration = max(durations) if durations else 0

    success_rate = (passed / total * 100) if total > 0 else 0

    sessions = list(db.test_sessions.find({"timestamp": {"$gte": cutoff}}))

    print(f"- Total Test Runs: {total}")
    print(f"- Passed: {passed}")
    print(f"- Failed: {failed}")
    print(f"- Skipped: {skipped}")
    print(f"- Success Rate: {success_rate:.1f}%")
    print(f"- Avg Duration: {avg_duration:.2f}s")
    print(f"- Max Duration: {max_duration:.2f}s")
    print(f"- Test Sessions: {len(sessions)}")

    metrics = {
        "period": "7 days",
        "total_runs": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "success_rate": round(success_rate, 1),
        "avg_duration_seconds": round(avg_duration, 2),
        "max_duration_seconds": round(max_duration, 2),
        "sessions": len(sessions),
    }

    with open("reports/test-metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\nMetrics written to reports/test-metrics.json")


if __name__ == "__main__":
    analyze_test_metrics()
