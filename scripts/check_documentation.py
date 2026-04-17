#!/usr/bin/env python3
"""
Check documentation coverage and generate a report.
"""

import os
from pathlib import Path


def check_documentation():
    print("## Documentation Coverage Report\n")

    py_files = list(Path("src").rglob("*.py")) + list(Path("tests").rglob("*.py"))
    py_count = len(py_files)
    print(f"- Python files: {py_count}")

    doc_files = list(Path("docs").rglob("*.md"))
    doc_count = len(doc_files)
    print(f"- Documentation files: {doc_count}")

    files_with_docs = 0
    for py_file in py_files:
        if py_file.stem.startswith("__"):
            continue
        try:
            content = py_file.read_text()
            if '"""' in content or "'''" in content:
                files_with_docs += 1
        except Exception:
            pass
    print(f"- Files with docstrings: {files_with_docs}")

    if py_count > 0:
        doc_coverage = (files_with_docs / py_count) * 100
        print(f"- Docstring coverage: {doc_coverage:.1f}%")

    if Path("README.md").exists():
        lines = len(Path("README.md").read_text().splitlines())
        print(f"- README lines: {lines}")
    else:
        print("- README: Missing")

    print("\nKey Documentation Files:")
    key_docs = [
        "docs/ARCHITECTURE.md",
        "docs/TUTORIAL.md",
        "docs/REPORTING.md",
        "docs/TROUBLESHOOTING.md",
    ]
    for doc in key_docs:
        status = "✓" if Path(doc).exists() else "✗"
        note = "" if Path(doc).exists() else " (missing)"
        print(f"  {status} {doc}{note}")


if __name__ == "__main__":
    check_documentation()
