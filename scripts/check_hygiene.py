#!/usr/bin/env python3
"""Repository hygiene checks.

Deliberately dependency-free so it can run in CI before anything is
installed, and so it does not pull external hook code into the developer's
machine the way a third-party pre-commit hook would.

Checks every text file tracked by git for:
  - trailing whitespace
  - a missing or duplicated final newline
  - leftover merge conflict markers
  - tabs used for indentation in Python files
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

CONFLICT_MARKERS = ("<<<<<<<", ">>>>>>>")
SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".pdf",
    ".zip",
    ".gz",
    ".whl",
    ".ico",
}


def tracked_files() -> list[Path]:
    """Return the text files git tracks."""
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        capture_output=True,
        text=True,
        check=True,
    )
    files = []
    for entry in result.stdout.split("\0"):
        if not entry:
            continue
        path = Path(entry)
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        files.append(path)
    return files


def check_file(path: Path) -> list[str]:
    """Return a list of problems found in a single file."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return [f"{path}: could not be read ({exc})"]

    if b"\0" in raw:
        return []  # binary file

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return []

    problems = []

    for number, line in enumerate(text.splitlines(), start=1):
        if line != line.rstrip():
            problems.append(f"{path}:{number}: trailing whitespace")

        for marker in CONFLICT_MARKERS:
            if line.startswith(marker):
                problems.append(f"{path}:{number}: merge conflict marker")

    if text and not text.endswith("\n"):
        problems.append(f"{path}: missing newline at end of file")
    elif text.endswith("\n\n"):
        problems.append(f"{path}: blank line at end of file")

    if path.suffix == ".py":
        for number, line in enumerate(text.splitlines(), start=1):
            if line.startswith("\t") or (line[: len(line) - len(line.lstrip())]).count(
                "\t"
            ):
                problems.append(f"{path}:{number}: tab used for indentation")

    return problems


def main() -> int:
    """Run every check and report all problems found."""
    files = tracked_files()
    problems: list[str] = []

    for path in files:
        problems.extend(check_file(path))

    for problem in problems:
        print(problem)

    if problems:
        print(f"\n{len(problems)} problem(s) found in {len(files)} file(s)")
        return 1

    print(f"hygiene checks passed ({len(files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
