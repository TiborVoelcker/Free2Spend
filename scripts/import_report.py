"""Print a free-to-spend table for a real bank export.

    python3 -m scripts.import_report tests/fixtures/ing_sample.csv
    python3 -m scripts.import_report statement.csv --rollover-day 27

Milestone M2 (docs/build-plan.md). It needs no classification and no pockets:
with none configured, free-to-spend is the balance at each rollover, so an
export and a rollover day are enough.
"""

from __future__ import annotations

import argparse
import signal
import sys
from datetime import date, timedelta

from engine import format_euros, period_containing
from importers import ing_csv
from importers.statement import ImportedStatement
from scripts import _report

DEFAULT_ROLLOVER_DAY = -5


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="an ING Umsatzanzeige CSV export")
    parser.add_argument(
        "--rollover-day",
        type=int,
        default=DEFAULT_ROLLOVER_DAY,
        help=(
            f"1..31 counting forward, or -1..-28 counting back from the month end "
            f"(default {DEFAULT_ROLLOVER_DAY})"
        ),
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
            print(f"  {error}\n    {error.raw[:160]}")
        if len(statement.row_errors) > 20:
            print(f"  ... and {len(statement.row_errors) - 20} more")
        print("\nNot reporting numbers: they would be wrong.")
        return 1

    for problem in statement.balance_discrepancies[:20]:
        print(f"  {problem}")
    if statement.balance_discrepancies:
        print("\nAn amount was misread. Not reporting numbers.")
        return 1

    ledger = statement.ledger
    if not ledger:
        print("\nNo transactions in the export.")
        return 1

    for discrepancy in ledger.reconcile():
        print(f"\nAnchors disagree with the transactions: {discrepancy}")
        return 1

    today = args.today or _end_of_last_complete_period(ledger.last_date, args.rollover_day)
    summaries = ledger.summarise(
        args.rollover_day,
        today,
        since=_first_complete_period_start(ledger.first_date, args.rollover_day),
    )

    print(f"\nRollover day {args.rollover_day}, reporting as of {today.isoformat()}.\n")
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


def _print_statement(statement: ImportedStatement) -> None:
    window = ""
    if statement.period_start and statement.period_end:
        window = f", {statement.period_start.isoformat()} to {statement.period_end.isoformat()}"
    print()
    print(f"{statement.bank} · {statement.account_name} · {statement.iban}")
    print(f"Read as {statement.encoding}{window}")
    print(
        f"{len(statement.transactions)} transactions, "
        f"opening balance {format_euros(statement.opening_balance_cents)}, "
        f"closing {format_euros(statement.closing_balance_cents)}"
    )
    if statement.is_clean:
        print("The running balance verifies against every row.")


def _first_complete_period_start(first: date, rollover_day: int) -> date:
    """The first period the export covers in full.

    A period opening before the export's first transaction is missing part of
    its own window, so its numbers would be wrong.
    """
    period = period_containing(first, rollover_day)
    return period.start if period.start == first else period.end


def _end_of_last_complete_period(last: date, rollover_day: int) -> date:
    period = period_containing(last, rollover_day)
    return last if last == period.last_day else period.start - timedelta(days=1)


if __name__ == "__main__":
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    sys.exit(main())
