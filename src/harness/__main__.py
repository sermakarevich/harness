"""`python -m harness` → start the terminal chat."""

import sys

from rich.console import Console

from harness.config import ConfigError, load_settings
from harness.tui.app import App


def main() -> int:
    try:
        settings = load_settings()
    except ConfigError as exc:
        Console(stderr=True).print(f"[red]{exc}[/red]")
        return 2
    App(settings).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
