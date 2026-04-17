#!/usr/bin/env python3
"""
Check if flaky test percentage exceeds threshold and fail if so.
"""

import argparse
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="Check flaky test threshold")
    parser.add_argument(
        "--threshold", type=float, default=5.0, help="Threshold percentage"
    )
    parser.add_argument(
        "--report-file",
        default="reports/flaky-test-report.json",
        help="Path to flaky test report",
    )
    args = parser.parse_args()

    report_path = args.report_file
    if not os.path.exists(report_path):
        print("No flaky test report found - skipping threshold check")
        sys.exit(0)

    with open(report_path) as f:
        data = json.load(f)

    flaky_count = data.get("summary", {}).get("flaky_count", 0)
    flaky_pct = data.get("summary", {}).get("flaky_percentage", 0)

    print(f"Flaky tests: {flaky_count} ({flaky_pct}%)")
    print(f"Threshold: {args.threshold}%")

    if flaky_pct > args.threshold:
        print(
            f"ERROR: Flaky test percentage ({flaky_pct}%) exceeds threshold ({args.threshold}%)"
        )
        sys.exit(1)

    print("Flaky test percentage within threshold")


if __name__ == "__main__":
    main()
