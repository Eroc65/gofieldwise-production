"""
Usage:
    python .\\scripts\\diagnose_test_imports.py .\\tests\\test_auth_flow.py

What it does:
- Parses a test file for import statements
- Imports each discovered module in a separate subprocess
- Reports OK / FAIL / HANG for each module
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path


TIMEOUT_SECONDS = 15


def extract_modules(test_file: Path) -> list[str]:
    source = test_file.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(test_file))
    modules: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in modules:
                    modules.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level != 0:
                continue
            if node.module and node.module not in modules:
                modules.append(node.module)

    return modules


def try_import(module_name: str, cwd: Path, timeout: int) -> tuple[str, str]:
    code = (
        "import sys; "
        f"sys.path.insert(0, r'{cwd}'); "
        f"import {module_name}; "
        f"print('IMPORTED: {module_name}')"
    )

    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return "HANG", f"Timed out after {timeout}s"

    output = (result.stdout or "") + (result.stderr or "")
    output = output.strip()

    if result.returncode == 0:
        return "OK", output

    return "FAIL", output


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python .\\scripts\\diagnose_test_imports.py .\\tests\\test_auth_flow.py")
        return 2

    test_file = Path(sys.argv[1]).resolve()
    if not test_file.exists():
        print(f"Test file not found: {test_file}")
        return 2

    project_root = Path.cwd()
    modules = extract_modules(test_file)

    if not modules:
        print("No absolute imports found.")
        return 0

    print(f"Testing imports from: {test_file}")
    print(f"Working directory: {project_root}")
    print()

    for module_name in modules:
        status, details = try_import(module_name, project_root, TIMEOUT_SECONDS)
        print(f"[{status}] {module_name}")
        if details:
            print(details)
        print("-" * 80)

        if status in {"FAIL", "HANG"}:
            print(f"FIRST PROBLEM MODULE: {module_name}")
            return 1

    print("All discovered imports completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
