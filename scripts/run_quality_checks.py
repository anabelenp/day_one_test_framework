#!/usr/bin/env python3
"""
Run code quality checks and generate a report.
"""

import subprocess
import sys


def run_command(cmd, description, allow_failure=True):
    """Run a command and print output."""
    print(f"\n## {description}")
    print("-" * 40)
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.stdout:
            print(result.stdout[:3000])
        if result.stderr and result.returncode != 0:
            print(result.stderr[:1000])
        if result.returncode != 0 and not allow_failure:
            print(f"FAILED with exit code {result.returncode}")
        return result.returncode == 0 or allow_failure
    except subprocess.TimeoutExpired:
        print("TIMEOUT - Command took too long")
        return allow_failure
    except Exception as e:
        print(f"ERROR: {e}")
        return allow_failure


def main():
    print("## Code Quality Checks\n")

    checks = [
        (
            "flake8 src tests --count --show-source --statistics --max-line-length=120",
            "Flake8 Results",
            True,
        ),
        ("black --check src tests --diff 2>&1 | head -100", "Black Format Check", True),
        ("mypy src --ignore-missing-imports 2>&1 | head -50", "MyPy Type Check", True),
    ]

    all_passed = True
    for cmd, desc, allow_fail in checks:
        passed = run_command(cmd, desc, allow_fail)
        if not passed and not allow_fail:
            all_passed = False

    # Complexity check
    print("\n## Code Complexity Report")
    print("-" * 40)
    try:
        import radon

        result = subprocess.run(
            ["radon", "cc", "src", "-a", "-j"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and result.stdout:
            import json

            data = json.loads(result.stdout)
            files = {}
            for filepath, complexity in data.items():
                if complexity:
                    avg = sum(c["complexity"] for c in complexity) / len(complexity)
                    files[filepath] = {
                        "modules": len(complexity),
                        "avg_complexity": round(avg, 1),
                        "max_complexity": max(c["complexity"] for c in complexity),
                    }

            print(f"Files analyzed: {len(files)}")

            if files:
                sorted_files = sorted(
                    files.items(), key=lambda x: x[1]["avg_complexity"], reverse=True
                )
                print("\nTop 5 Most Complex Files:")
                for filepath, info in sorted_files[:5]:
                    print(
                        f"  {filepath}: avg={info['avg_complexity']}, max={info['max_complexity']}"
                    )

                high_complexity = [
                    (f, i) for f, i in sorted_files if i["avg_complexity"] > 10
                ]
                if high_complexity:
                    print(
                        f"\nWarning: {len(high_complexity)} files have high complexity (>10)"
                    )
        else:
            print("Could not analyze complexity")

    except ImportError:
        print("radon not installed - skipping complexity check")
    except Exception as e:
        print(f"Error: {e}")

    print("\n" + "=" * 40)
    if all_passed:
        print("All code quality checks completed")
    else:
        print("Some checks failed - review output above")


if __name__ == "__main__":
    main()
