#!/usr/bin/env python3
"""
Clean test reports directory.

Usage:
    python scripts/clean_reports.py
    python scripts/clean_reports.py --all
"""

import argparse
import shutil
from pathlib import Path


def clean_reports(keep_allure_report=False):
    reports_dir = Path("reports")

    if not reports_dir.exists():
        print("Reports directory does not exist")
        return

    removed = []
    for item in reports_dir.iterdir():
        if item.name.startswith("."):
            continue

        if item.is_dir():
            if not keep_allure_report or item.name != "allure-report":
                shutil.rmtree(item)
                removed.append(f"{item.name}/")
        else:
            item.unlink()
            removed.append(item.name)

    if removed:
        print(f"Cleaned reports directory:")
        for item in removed:
            print(f"  - {item}")
    else:
        print("Reports directory already empty")


def main():
    parser = argparse.ArgumentParser(description="Clean test reports")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Remove all including allure-report",
    )
    args = parser.parse_args()

    clean_reports(keep_allure_report=not args.all)


if __name__ == "__main__":
    main()
