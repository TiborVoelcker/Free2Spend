"""Print a period-by-period free-to-spend table for a generated demo year.

    python -m scripts.demo_year
    python -m scripts.demo_year --rollover-day 1    # calendar months, for contrast

This is milestone M1 (docs/build-plan.md): no database, no API, no UI. The point
is to look at a year of numbers and judge whether the strategy feels right.
"""

from __future__ import annotations

import argparse
import signal
from datetime import date, timedelta

from demo.generator import first_budget_date, generate_year, last_date
from engine import Classification, format_euros, period_containing, summarise

COLUMNS = [
    ("Period", 26, "<"),
    ("Free-to-spend", 14, ">"),
    ("Income", 11, ">"),
    ("Required", 11, ">"),
    ("Fun", 11, ">"),
    ("Remaining", 12, ">"),
    ("Closing", 11, ">"),
]


def _header() -> str:
    cells = [f"{name:{align}{width}}" for name, width, align in COLUMNS]
    return "  ".join(cells)


def _row(values: list[str]) -> str:
    cells = [f"{v:{align}{width}}" for v, (_, width, align) in zip(values, COLUMNS)]
    return "  ".join(cells)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rollover-day", type=int, default=27)
    parser.add_argument("--months", type=int, default=12)
    parser.add_argument("--seed", type=int, default=20260101)
    parser.add_argument(
        "--opening-balance",
        type=int,
        default=240_000,
        help="in cents (default 240000, i.e. EUR 2,400)",
    )
    parser.add_argument(
        "--splurge",
        type=int,
        default=290_000,
        help=(
            "cents spent on the holiday in period 11 (default 290000). Raise it "
            "past that period's free-to-spend to see an overspent period."
        ),
    )
    parser.add_argument(
        "--today",
        type=date.fromisoformat,
        default=None,
        help="ISO date; defaults to the end of the last complete period",
    )
    args = parser.parse_args()

    transactions = generate_year(
        rollover_day=args.rollover_day,
        months=args.months,
        seed=args.seed,
        opening_balance_cents=args.opening_balance,
        splurge_cents=-abs(args.splurge),
    )
    today = args.today or _end_of_last_complete_period(transactions, args.rollover_day)
    summaries = summarise(
        transactions,
        args.rollover_day,
        today,
        since=first_budget_date(transactions),
    )

    print()
    print(f"Demo year, rollover day {args.rollover_day}, {len(transactions)} transactions")
    print(f"Reporting as of {today.isoformat()}.")
    print()
    print(_header())
    print("-" * len(_header()))

    for summary in summaries:
        print(
            _row(
                [
                    summary.period.label,
                    format_euros(summary.free_to_spend_cents),
                    format_euros(summary.income_cents),
                    format_euros(summary.required_spend_cents),
                    format_euros(summary.fun_spend_cents),
                    format_euros(summary.remaining_free_to_spend_cents),
                    format_euros(summary.closing_balance_cents),
                ]
            )
            + ("   <-- overspent" if summary.is_overspent else "")
        )

    print()
    _print_checks(transactions, summaries, today)
    return 0


def _end_of_last_complete_period(transactions, rollover_day: int) -> date:
    """The last day of the most recent period that has fully elapsed.

    Without this the table ends on a stub row: a period holding only whichever
    transactions happened to spill past the final rollover.
    """
    last = last_date(transactions)
    current = period_containing(last, rollover_day)
    if last == current.last_day:
        return last
    return current.start - timedelta(days=1)


def _print_checks(transactions, summaries, today: date) -> None:
    """Assert the two things that would mean the engine is lying."""
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

    upto = [t for t in transactions if t.date <= today]
    total = sum(t.amount_cents for t in upto)
    fun = sum(t.amount_cents for t in upto if t.classification is Classification.FUN)
    print(f"Balance {format_euros(total)}, of which fun spending was {format_euros(-fun)}.")

    if problems:
        print("\nPROBLEMS:")
        for problem in problems:
            print(f"  - {problem}")
    else:
        print("Checks pass: every period reconciles, and each free-to-spend is the")
        print("previous period's closing balance.")


if __name__ == "__main__":
    if hasattr(signal, "SIGPIPE"):
        # Let `python -m scripts.demo_year | head` exit quietly, as a Unix tool
        # should, instead of raising BrokenPipeError.
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    raise SystemExit(main())
