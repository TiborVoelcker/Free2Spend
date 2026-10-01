"""Rendering for the report scripts. Presentation only."""

from __future__ import annotations

import itertools
from collections.abc import Sequence

from engine import PeriodSummary, format_euros

COLUMNS = [
    ("Period", 26, "<"),
    ("Free-to-spend", 14, ">"),
    ("Remaining", 12, ">"),
    ("Income", 11, ">"),
    ("Required", 11, ">"),
    ("Fun", 10, ">"),
    ("Surplus", 11, ">"),
    ("Closing", 11, ">"),
]

INCOME_TOLERANCE_PERCENT = 50


def print_table(summaries: Sequence[PeriodSummary]) -> None:
    line = "  ".join(f"{name:{align}{width}}" for name, width, align in COLUMNS)
    print(line)
    print("-" * len(line))
    for summary in summaries:
        values = [
            summary.period.label,
            format_euros(summary.free_to_spend_cents),
            format_euros(summary.remaining_free_to_spend_cents),
            format_euros(summary.income_cents),
            format_euros(summary.required_spend_cents),
            format_euros(summary.fun_spend_cents),
            format_euros(summary.surplus_cents),
            format_euros(summary.closing_balance_cents),
        ]
        row = "  ".join(
            f"{value:{align}{width}}" for value, (_, width, align) in zip(values, COLUMNS)
        )
        print(row + ("   <-- overspent" if summary.is_overspent else ""))


def odd_income(summaries: Sequence[PeriodSummary]) -> list[tuple[PeriodSummary, int]]:
    """Periods whose income is far from the usual.

    A period with no income, or with two salaries in it, is the symptom of a
    rollover day on the wrong side of the salary — which is silent and
    permanent, since it happens every month.
    """
    incomes = sorted(summary.income_cents for summary in summaries)
    if len(incomes) < 3:
        return []
    median = incomes[len(incomes) // 2]
    if median <= 0:
        return []
    low = median * (100 - INCOME_TOLERANCE_PERCENT) // 100
    high = median * (100 + INCOME_TOLERANCE_PERCENT) // 100
    return [(s, median) for s in summaries if not low <= s.income_cents <= high]


def print_checks(summaries: Sequence[PeriodSummary]) -> bool:
    problems = []
    for summary in summaries:
        expected = (
            summary.free_to_spend_cents
            + summary.income_cents
            - summary.required_spend_cents
            - summary.fun_spend_cents
        )
        if expected != summary.closing_balance_cents:
            problems.append(f"{summary.period.label}: closing balance does not reconcile")
    for earlier, later in itertools.pairwise(summaries):
        if earlier.closing_balance_cents != later.free_to_spend_cents:
            problems.append(
                f"{later.period.label}: free-to-spend is not the previous closing balance"
            )

    for summary, median in odd_income(summaries):
        problems.append(
            f"{summary.period.label}: income is {format_euros(summary.income_cents)}, "
            f"usually {format_euros(median)}. Check the rollover day is not splitting "
            f"the salary from the month it pays for."
        )

    if problems:
        print("Check:")
        for problem in problems:
            print(f"  - {problem}")
        return False
    print("Checks pass: every period reconciles, each free-to-spend is the previous")
    print("period's closing balance, and no period has unusual income.")
    return True
