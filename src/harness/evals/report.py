"""Turns suite results into one table."""

from __future__ import annotations

from harness.evals.run import Result

HEADINGS = ("task", "pass", "in", "out", "cost", "seconds")
COST_DECIMALS = 4
SECONDS_DECIMALS = 1
PASS_TEMPLATE = "{passed}/{runs}"


def rows(results: list[Result]) -> list[tuple[str, ...]]:
    """One summary row per task, keeping first-seen order."""
    grouped: dict[str, list[Result]] = {}
    for result in results:
        grouped.setdefault(result.task, []).append(result)
    table: list[tuple[str, ...]] = []
    for name, group in grouped.items():
        passed = sum(1 for result in group if result.passed)
        table.append(
            (
                name,
                PASS_TEMPLATE.format(passed=passed, runs=len(group)),
                str(sum(result.usage.input_tokens for result in group)),
                str(sum(result.usage.output_tokens for result in group)),
                f"{sum(result.cost for result in group):.{COST_DECIMALS}f}",
                f"{sum(result.seconds for result in group) / len(group):.{SECONDS_DECIMALS}f}",
            )
        )
    return table


def table(results: list[Result]) -> str:
    """Heading row and data rows as text with lined-up columns."""
    grid = [HEADINGS, *rows(results)]
    widths = [max(len(row[column]) for row in grid) for column in range(len(HEADINGS))]
    return "\n".join(
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True))
        for row in grid
    )


def all_passed(results: list[Result]) -> bool:
    """True when every result passed."""
    return all(result.passed for result in results)
