"""Compile the Streamlit app and project modules.

This script avoids shell-specific glob expansion issues on Windows PowerShell.
"""

from __future__ import annotations

from pathlib import Path
import py_compile


def iter_python_files() -> list[Path]:
    roots = [Path("app.py"), *Path("src").glob("*.py"), *Path("src/api").glob("*.py")]
    return [path for path in roots if path.exists()]


def main() -> None:
    files = iter_python_files()
    for path in files:
        py_compile.compile(str(path), doraise=True)
    print(f"compiled {len(files)} files")


if __name__ == "__main__":
    main()
