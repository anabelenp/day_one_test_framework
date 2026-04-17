#!/usr/bin/env python3
"""
Generate Test Quality Summary Report

Creates a GitHub Actions step summary from flaky test and metrics data.
"""

import os
import json
import sys


def generate_summary():
    summary = [
        "## Test Quality Summary Report",
        "",
        "| Metric | Value |",
        "|--------|-------|",
    ]

    # Flaky test status
    flaky_file = "artifacts/flaky-test-report/flaky-test-report.json"
    if os.path.exists(flaky_file):
        try:
            with open(flaky_file) as f:
                data = json.load(f)
            flaky_count = data.get("summary", {}).get("flaky_count", 0)
            flaky_pct = data.get("summary", {}).get("flaky_percentage", 0)
            summary.append(f"| Flaky Tests | {flaky_count} |")
            summary.append(f"| Flaky Percentage | {flaky_pct}% |")
        except Exception as e:
            print(f"Error reading flaky test report: {e}", file=sys.stderr)
            summary.append("| Flaky Tests | Error |")
    else:
        summary.append("| Flaky Tests | N/A |")

    # Test metrics
    metrics_file = "artifacts/test-metrics/test-metrics.json"
    if os.path.exists(metrics_file):
        try:
            with open(metrics_file) as f:
                data = json.load(f)
            total_runs = data.get("total_runs", 0)
            success_rate = data.get("success_rate", 0)
            summary.append(f"| Total Test Runs | {total_runs} |")
            summary.append(f"| Success Rate | {success_rate}% |")
        except Exception as e:
            print(f"Error reading metrics: {e}", file=sys.stderr)
    else:
        summary.append("| Test Metrics | N/A |")

    summary.append("")

    # Generate timestamp
    try:
        timestamp = os.popen("date -u").read().strip()
        summary.append(f"Generated at: {timestamp}")
    except Exception:
        summary.append("Generated at: Unknown")

    output = "\n".join(summary)
    print(output)

    # Write to GITHUB_STEP_SUMMARY if available
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "w") as f:
            f.write(output)
        print(f"\nWritten to {summary_path}")


if __name__ == "__main__":
    generate_summary()
