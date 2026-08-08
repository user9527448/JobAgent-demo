"""Run the complete local and CI quality gate."""

from __future__ import annotations

import subprocess
import sys

CHECKS = (
    ("Ruff format", "-m", "ruff", "format", "--check", "."),
    ("Ruff lint", "-m", "ruff", "check", "."),
    ("Mypy", "-m", "mypy", "src", "tests", "scripts"),
    (
        "Pytest",
        "-m",
        "pytest",
        "--cov=jobagent",
        "--cov-report=term-missing",
        "--cov-report=xml",
    ),
)


def main() -> int:
    """Run checks sequentially and stop immediately when one fails."""
    for label, *arguments in CHECKS:
        print(f"\n==> {label}", flush=True)
        completed = subprocess.run((sys.executable, *arguments), check=False)
        if completed.returncode != 0:
            print(f"\nQuality gate failed at: {label}", file=sys.stderr)
            return completed.returncode

    print("\nAll quality checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
