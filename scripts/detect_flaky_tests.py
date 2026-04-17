#!/usr/bin/env python3
"""
Flaky Test Detection Script

Analyzes test results from MongoDB to identify flaky tests.
Tests that pass and fail across multiple runs are considered flaky.

Usage:
    python scripts/detect_flaky_tests.py --min-runs 5 --stability-threshold 0.8

Exit codes:
    0 - No flaky tests found
    1 - Flaky tests detected (exits with list of flaky tests)
    2 - Error (MongoDB unavailable, etc.)
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json


try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, OperationFailure
except ImportError:
    print("Error: pymongo not installed. Run: pip install pymongo")
    sys.exit(2)


class FlakyTestDetector:
    """Detects flaky tests based on historical test results."""

    def __init__(
        self,
        mongo_uri: str = "mongodb://admin:admin_2024@localhost:27017/",
        database: str = "day1_local",
    ):
        self.mongo_uri = mongo_uri
        self.database_name = database
        self.client: Optional[MongoClient] = None
        self.db = None

    def connect(self) -> bool:
        """Connect to MongoDB."""
        try:
            self.client = MongoClient(
                self.mongo_uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
            )
            self.client.admin.command("ping")
            self.db = self.client[self.database_name]
            return True
        except ConnectionFailure as e:
            print(f"Error: Could not connect to MongoDB: {e}")
            return False

    def get_test_history(
        self, test_name: str = None, hours: int = 168
    ) -> List[Dict[str, Any]]:
        """Get test history from the last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = {"start_time": {"$gte": cutoff}}
        if test_name:
            query["test_name"] = test_name
        return list(self.db.test_results.find(query))

    def analyze_flaky_tests(
        self, min_runs: int = 5, stability_threshold: float = 0.8
    ) -> Dict[str, Any]:
        """
        Analyze test results to find flaky tests.

        A flaky test is one that:
        1. Has been run at least min_runs times
        2. Has both passed and failed results
        3. Has a pass rate between stability_threshold and (1 - stability_threshold)
        """
        history = self.get_test_history()
        if not history:
            return {
                "status": "no_data",
                "message": "No test results found in the specified time period",
                "flaky_tests": [],
                "summary": {},
            }

        test_results: Dict[str, List[str]] = {}
        for result in history:
            test_name = result.get("test_name", "unknown")
            status = result.get("status", "unknown")
            if test_name not in test_results:
                test_results[test_name] = []
            test_results[test_name].append(status)

        flaky_tests = []
        stable_tests = []
        unreliable_tests = []

        for test_name, statuses in test_results.items():
            if len(statuses) < min_runs:
                continue

            total_runs = len(statuses)
            passed = sum(1 for s in statuses if s in ("passed", "success"))
            failed = sum(1 for s in statuses if s in ("failed", "failure"))
            skipped = sum(1 for s in statuses if s == "skipped")

            pass_rate = passed / total_runs if total_runs > 0 else 0
            failure_rate = failed / total_runs if total_runs > 0 else 0

            unique_statuses = set(statuses)
            has_multiple_outcomes = len(unique_statuses) > 1

            test_info = {
                "test_name": test_name,
                "total_runs": total_runs,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "pass_rate": round(pass_rate * 100, 1),
                "failure_rate": round(failure_rate * 100, 1),
                "statuses": dict((s, statuses.count(s)) for s in unique_statuses),
            }

            if has_multiple_outcomes:
                if pass_rate >= stability_threshold:
                    unreliable_tests.append(test_info)
                elif failure_rate >= stability_threshold:
                    flaky_tests.append(test_info)
                else:
                    flaky_tests.append(test_info)
            else:
                if pass_rate == 1.0:
                    stable_tests.append(test_info)
                else:
                    unreliable_tests.append(test_info)

        flaky_tests.sort(key=lambda x: x["failure_rate"], reverse=True)
        unreliable_tests.sort(key=lambda x: x["failure_rate"], reverse=True)

        return {
            "status": "complete",
            "total_tests_analyzed": len(test_results),
            "flaky_tests": flaky_tests,
            "unreliable_tests": unreliable_tests,
            "stable_tests": stable_tests,
            "summary": {
                "flaky_count": len(flaky_tests),
                "unreliable_count": len(unreliable_tests),
                "stable_count": len(stable_tests),
                "flaky_percentage": (
                    round(len(flaky_tests) / len(test_results) * 100, 1)
                    if test_results
                    else 0
                ),
            },
        }

    def generate_report(self, analysis: Dict[str, Any], format: str = "text") -> str:
        """Generate a report from the analysis."""
        if format == "json":
            return json.dumps(analysis, indent=2)

        lines = []
        lines.append("=" * 70)
        lines.append("FLAKY TEST DETECTION REPORT")
        lines.append("=" * 70)
        lines.append("")

        summary = analysis.get("summary", {})
        lines.append("SUMMARY")
        lines.append("-" * 40)
        lines.append(
            f"  Total Tests Analyzed: {summary.get('total_tests_analyzed', 0)}"
        )
        lines.append(f"  Flaky Tests: {summary.get('flaky_count', 0)}")
        lines.append(f"  Unreliable Tests: {summary.get('unreliable_count', 0)}")
        lines.append(f"  Stable Tests: {summary.get('stable_count', 0)}")
        lines.append(f"  Flaky Percentage: {summary.get('flaky_percentage', 0)}%")
        lines.append("")

        flaky = analysis.get("flaky_tests", [])
        if flaky:
            lines.append("FLAKY TESTS (Pass/fail inconsistently)")
            lines.append("-" * 40)
            for test in flaky[:10]:
                lines.append(f"  {test['test_name']}")
                lines.append(
                    f"    Runs: {test['total_runs']}, "
                    f"Passed: {test['passed']}, "
                    f"Failed: {test['failed']}, "
                    f"Rate: {test['pass_rate']}%"
                )
            if len(flaky) > 10:
                lines.append(f"  ... and {len(flaky) - 10} more")
            lines.append("")

        unreliable = analysis.get("unreliable_tests", [])
        if unreliable:
            lines.append("UNRELIABLE TESTS (High failure rate)")
            lines.append("-" * 40)
            for test in unreliable[:5]:
                lines.append(f"  {test['test_name']}")
                lines.append(
                    f"    Failed: {test['failed']}/{test['total_runs']} ({test['failure_rate']}%)"
                )
            if len(unreliable) > 5:
                lines.append(f"  ... and {len(unreliable) - 5} more")
            lines.append("")

        if not flaky and not unreliable:
            lines.append("All tests are stable!")
            lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)

    def export_to_json(self, analysis: Dict[str, Any], output_file: str):
        """Export analysis to JSON file."""
        with open(output_file, "w") as f:
            json.dump(analysis, f, indent=2)
        print(f"Exported analysis to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Detect flaky tests from MongoDB test results"
    )
    parser.add_argument(
        "--mongo-uri",
        default="mongodb://admin:admin_2024@localhost:27017/",
        help="MongoDB connection URI",
    )
    parser.add_argument(
        "--database",
        default="day1_local",
        help="Database name",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=168,
        help="Look back period in hours (default: 168 = 1 week)",
    )
    parser.add_argument(
        "--min-runs",
        type=int,
        default=5,
        help="Minimum number of runs to consider (default: 5)",
    )
    parser.add_argument(
        "--stability-threshold",
        type=float,
        default=0.8,
        help="Stability threshold 0-1 (default: 0.8)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    parser.add_argument(
        "--output",
        help="Output file path (JSON format)",
    )
    parser.add_argument(
        "--fail-on-flaky",
        action="store_true",
        help="Exit with code 1 if flaky tests found",
    )

    args = parser.parse_args()

    detector = FlakyTestDetector(mongo_uri=args.mongo_uri, database=args.database)

    if not detector.connect():
        sys.exit(2)

    print(f"Analyzing test results from the last {args.hours} hours...")
    print(f"Minimum runs required: {args.min_runs}")
    print(f"Stability threshold: {args.stability_threshold}")
    print("")

    analysis = detector.analyze_flaky_tests(
        min_runs=args.min_runs, stability_threshold=args.stability_threshold
    )

    if args.output:
        detector.export_to_json(analysis, args.output)

    report = detector.generate_report(analysis, format=args.format)
    print(report)

    flaky_count = analysis["summary"].get("flaky_count", 0)
    unreliable_count = analysis["summary"].get("unreliable_count", 0)

    if args.fail_on_flaky and (flaky_count > 0 or unreliable_count > 0):
        print("\nFLAKY TESTS DETECTED - Build should fail")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
