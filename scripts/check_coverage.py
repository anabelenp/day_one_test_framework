#!/usr/bin/env python3
"""
Check code coverage against a threshold and fail if below.

Usage: python scripts/check_coverage.py --threshold 80
"""

import argparse
import os
import sys
import xml.etree.ElementTree as ET


def parse_coverage_xml(xml_file):
    """Parse coverage.xml and return total coverage percentage."""
    if not os.path.exists(xml_file):
        print(f"Coverage file not found: {xml_file}")
        return None

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        line_rate = root.get("line-rate")
        if line_rate is not None:
            return float(line_rate) * 100

        for coverage in root.iter("coverage"):
            line_rate = coverage.get("line-rate")
            if line_rate:
                return float(line_rate) * 100

        return None
    except Exception as e:
        print(f"Error parsing coverage XML: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Check code coverage threshold")
    parser.add_argument(
        "--threshold",
        type=float,
        default=80.0,
        help="Minimum coverage percentage (default: 80)",
    )
    parser.add_argument(
        "--xml-file",
        default="coverage.xml",
        help="Path to coverage.xml file",
    )
    parser.add_argument(
        "--fail",
        action="store_true",
        help="Exit with failure if below threshold",
    )
    args = parser.parse_args()

    coverage = parse_coverage_xml(args.xml_file)

    if coverage is None:
        print("Could not determine coverage percentage")
        if args.fail:
            sys.exit(1)
        return

    print(f"Code Coverage: {coverage:.2f}%")
    print(f"Threshold: {args.threshold}%")

    if coverage < args.threshold:
        print(
            f"ERROR: Coverage ({coverage:.2f}%) is below threshold ({args.threshold}%)"
        )
        if args.fail:
            sys.exit(1)
    else:
        print(f"Coverage meets threshold")


if __name__ == "__main__":
    main()
