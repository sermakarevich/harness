"""`python -m harness.evals` → run the task suite and print one table."""

import sys

from rich.console import Console

from harness.config import ConfigError, load_settings
from harness.evals.report import all_passed, table
from harness.evals.run import run_suite
from harness.evals.tasks import load_tasks

FAILURE_EXIT = 1
MISSING_KEY_EXIT = 2


def main() -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        Console(stderr=True).print(f"[red]{exc}[/red]")
        return MISSING_KEY_EXIT
    results = run_suite(settings, load_tasks())
    print(table(results))
    return 0 if all_passed(results) else FAILURE_EXIT


if __name__ == "__main__":
    sys.exit(main())
