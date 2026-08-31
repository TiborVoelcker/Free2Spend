"""Print a free-to-spend table for a real bank export.

    python3 -m scripts.import_report tests/fixtures/ing_sample.csv
    python3 -m scripts.import_report statement.csv --rollover-day -3

This is milestone M2 (docs/build-plan.md), and it is the point of the whole
project: seeing what free-to-spend would actually have been, month by month, on
real money.

It needs **no classification and no pockets**. With no pockets configured,
free-to-spend is just the balance at each rollover, so an export and a rollover
day are enough. Everything therefore reads as required, the Fun column is zero,
and Remaining equals Free-to-spend.
"""

from __future__ import annotations

import argparse
import signal
import sys
from datetime import date, timedelta

from engine import format_euros, period_containing, summarise
from importers import ing_csv
from scripts import _report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="an ING Umsatzanzeige CSV export")
    parser.add_argument(
        "--rollover-day",
        type=int,
        default=27,
        help="1..31 counting forward, or -1..-28 counting back from the month end",
    )
    parser.add_argument(
        "--today",
        type=date.fromisoformat,
        default=None,
        help="ISO date; defaults to the end of the last complete period",
    )
    args = parser.parse_args()

    statement = ing_csv.read(args.path)
    _print_statement(statement)

    if statement.row_errors:
        print(f"\n{len(statement.row_errors)} rows could not be read:\n")
        for error in statement.row_errors[:20]:
            print(f"  {error}")
            print(f"    {error.raw[:160]}")
        if len(statement.row_errors) > 20:
            print(f"  ... and {len(statement.row_errors) - 20} more")
        print("\nNot reporting numbers: they would be wrong.")
        return 1

    if statement.balance_discrepancies:
        print("\nThe running balance does not add up:\n")
        for problem in statement.balance_discrepancies[:20]:
            print(f"  {problem}")
        print("\nThis means an amount was misread. Not reporting numbers.")
        return 1

    if not statement.booked:
        print("\nNo transactions in the export.")
        return 1

    print()
    _report.print_recurring_income(statement.booked)

    transactions = statement.transactions
    since = _first_complete_period_start(statement, args.rollover_day)
    today = args.today or _end_of_last_complete_period(transactions, args.rollover_day)
    summaries = summarise(transactions, args.rollover_day, today, since=since)

    print(f"\n\nRollover day {args.rollover_day}, reporting as of {today.isoformat()}.\n")
    if not summaries:
        print("Nothing to report: the export does not cover a complete period.")
        return 1
    _report.print_table(summaries)
    print()
    print("Nothing is classified yet, so every payment counts as required, Fun is zero")
    print("and Free-to-spend is simply the accumulating balance. The column that means")
    print("something here is Surplus: what each period would have handed to the next")
    print("once the free-to-spend budget is actually being spent down.")
    print()
    return 0 if _report.print_checks(summaries) else 1


def _print_statement(statement: ing_csv.ImportedStatement) -> None:
    window = ""
    if statement.period_start and statement.period_end:
        window = f", {statement.period_start.isoformat()} to {statement.period_end.isoformat()}"
    print()
    print(f"{statement.bank} · {statement.account_name} · {statement.iban}")
    print(f"Read as {statement.encoding}{window}")
    print(
        f"{len(statement.booked)} transactions, "
        f"opening balance {format_euros(statement.opening_balance_cents)}, "
        f"closing {format_euros(statement.statement_balance_cents or 0)}"
    )
    if statement.is_clean:
        print("The running balance verifies against every row.")


def _first_complete_period_start(
    statement: ing_csv.ImportedStatement,
    rollover_day: int,
) -> date:
    """The first period the export covers in full.

    A period that opens before the export's first transaction is missing part of
    its own window, so its numbers would be wrong. Its free-to-spend would also
    read as zero with the opening balance showing up as income, which is not
    what happened.
    """
    first = min(t.booking_date for t in statement.booked)
    period = period_containing(first, rollover_day)
    return period.start if period.start == first else period.end


def _end_of_last_complete_period(transactions, rollover_day: int) -> date:
    last = max(t.booking_date for t in transactions)
    current = period_containing(last, rollover_day)
    if last == current.last_day:
        return last
    return current.start - timedelta(days=1)


if __name__ == "__main__":
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    sys.exit(main())
