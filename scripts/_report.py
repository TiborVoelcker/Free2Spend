"""Rendering shared by the report scripts. Presentation only."""

from __future__ import annotations

import calendar
from collections import defaultdict
from collections.abc import Sequence
from datetime import date

from engine import Transaction, format_euros
from engine.summary import PeriodSummary

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


def header() -> str:
    return "  ".join(f"{name:{align}{width}}" for name, width, align in COLUMNS)


def print_table(summaries: Sequence[PeriodSummary]) -> None:
    line = header()
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


def check(summaries: Sequence[PeriodSummary]) -> list[str]:
    """The two things that would mean the engine is lying."""
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
    for earlier, later in zip(summaries, summaries[1:]):
        if earlier.closing_balance_cents != later.free_to_spend_cents:
            problems.append(
                f"{later.period.label}: free-to-spend is not the previous closing balance"
            )
    return problems


def print_checks(summaries: Sequence[PeriodSummary]) -> bool:
    problems = check(summaries)
    if problems:
        print("PROBLEMS:")
        for problem in problems:
            print(f"  - {problem}")
        return False
    print("Checks pass: every period reconciles, and each free-to-spend is the")
    print("previous period's closing balance.")
    return True


def days_from_month_end(moment: date) -> int:
    """-1 for the last day of the month, -2 for the day before it."""
    return moment.day - calendar.monthrange(moment.year, moment.month)[1] - 1


def _regular_payments(items: list[Transaction]) -> tuple[list[Transaction], list[Transaction]]:
    """Split a payer's credits into the recurring ones and the one-offs.

    A salary and an expense reimbursement often come from the same employer. If
    the reimbursement is treated as part of the pattern, the earliest observed
    payment date is wrong, and a rollover day chosen from it sits needlessly far
    back in the month.
    """
    amounts = sorted(t.amount_cents for t in items)
    typical = amounts[len(amounts) // 2]
    tolerance = abs(typical) * 15 // 100
    regular = [t for t in items if abs(t.amount_cents - typical) <= tolerance]
    others = [t for t in items if abs(t.amount_cents - typical) > tolerance]
    return regular, others


def print_recurring_income(transactions: Sequence[Transaction], minimum: int = 3) -> None:
    """Where the recurring income landed, so a rollover day can be chosen.

    Facts only. Which day to pick, and how much margin to leave, is a judgement
    the numbers inform rather than settle.
    """
    by_counterparty: dict[str, list[Transaction]] = defaultdict(list)
    for transaction in transactions:
        if transaction.amount_cents > 0:
            by_counterparty[transaction.counterparty].append(transaction)

    recurring = {}
    set_aside = {}
    for name, items in by_counterparty.items():
        regular, others = _regular_payments(items)
        months = {(t.booking_date.year, t.booking_date.month) for t in regular}
        if len(months) >= minimum:
            recurring[name] = sorted(regular, key=lambda t: t.booking_date)
            set_aside[name] = others
    if not recurring:
        print("No recurring income found, so there is nothing to place a rollover day against.")
        return

    print("Recurring income")
    for name, items in sorted(recurring.items(), key=lambda kv: -len(kv[1])):
        amounts = {t.amount_cents for t in items}
        amount = format_euros(next(iter(amounts))) if len(amounts) == 1 else "varying"
        print(f"\n  {name} — {len(items)} payments of {amount}")
        if set_aside[name]:
            dates = ", ".join(t.booking_date.strftime("%d.%m") for t in set_aside[name])
            print(f"    ignoring {len(set_aside[name])} one-off credit(s) from the same payer"
                  f" ({dates})")
        print(f"    booked           {'  '.join(t.booking_date.strftime('%d.%m') for t in items)}")

        absolute = [t.booking_date.day for t in items]
        relative = [days_from_month_end(t.booking_date) for t in items]
        print(f"    day of month     {'  '.join(f'{d:5d}' for d in absolute)}")
        print(f"    from month end   {'  '.join(f'{d:5d}' for d in relative)}")
        print(
            f"    earliest: day {min(absolute)} counting forward, "
            f"{min(relative)} counting back from the month end"
        )
