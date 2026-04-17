#!/usr/bin/env python3
"""
Complexity Check Script

Analyzes code complexity using radon and outputs a report.
"""

import json
import subprocess
import sys
from pathlib import Path


def main():
    try:
        result = subprocess.run(
            ["radon", "cc", "src", "-o", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0 and not result.stdout:
            print("Could not analyze complexity")
            return

        data = json.loads(result.stdout) if result.stdout else {}

        files = {}
        for filepath, complexity in data.items():
            if complexity:
                avg = sum(c["complexity"] for c in complexity) / len(complexity)
                files[filepath] = {
                    "modules": len(complexity),
                    "avg_complexity": round(avg, 1),
                    "max_complexity": max(c["complexity"] for c in complexity),
                }

        print("## Code Complexity Analysis")
        print(f"Files analyzed: {len(files)}")
        print()

        if files:
            sorted_files = sorted(
                files.items(), key=lambda x: x[1]["avg_complexity"], reverse=True
            )

            print("Top 10 Most Complex Files:")
            for filepath, info in sorted_files[:10]:
                print(f"  {filepath}")
                print(
                    f"    Avg: {info['avg_complexity']}, Max: {info['max_complexity']}"
                )

            high_complexity = [
                (f, i) for f, i in sorted_files if i["avg_complexity"] > 10
            ]
            if high_complexity:
                print()
                print(
                    f"Warning: {len(high_complexity)} files have high complexity (>10)"
                )
                for filepath, info in high_complexity:
                    print(f"  - {filepath}: {info['avg_complexity']}")

    except FileNotFoundError:
        print("radon not installed. Run: pip install radon")
    except json.JSONDecodeError:
        print("Could not parse complexity data")
    except Exception as e:
        print(f"Error analyzing complexity: {e}")


if __name__ == "__main__":
    main()
