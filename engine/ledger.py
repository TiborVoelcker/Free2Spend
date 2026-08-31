"""The numbers, derived from the transaction log.

Nothing here is stored. `free-to-spend = balance - pockets` is a definition
recomputed from the balance at each rollover, not an accumulator
(docs/strategy.md section 2.1).
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from engine.model import Classification, Transaction
from engine.period import Period


def balance_before(transactions: Iterable[Transaction], moment: date) -> int:
    """The balance immediately before `moment`.

    Transactions dated `moment` itself are excluded, so this is the balance as
    the day begins.
    """
    return sum(t.amount_cents for t in transactions if t.booking_date < moment)


def free_to_spend(transactions: Iterable[Transaction], period: Period) -> int:
    """The period's free-to-spend, fixed at its start.

    This is `balance - pockets`. Pockets arrive in M3; until then there are
    none, so it is the balance at the rollover.
    """
    return balance_before(transactions, period.start)


def fun_spend(
    transactions: Iterable[Transaction],
    period: Period,
    as_of: date | None = None,
) -> int:
    """Fun spending within the period, as a positive number.

    `as_of` stops the count part-way through a period; passing a date beyond the
    period simply counts all of it. A refund classified as fun reduces the total,
    which is what makes it net spending rather than gross.
    """
    total = 0
    for transaction in transactions:
        if transaction.classification is not Classification.FUN:
            continue
        if not period.contains(transaction.booking_date):
            continue
        if as_of is not None and transaction.booking_date > as_of:
            continue
        total -= transaction.amount_cents
    return total


def remaining_free_to_spend(
    transactions: Iterable[Transaction],
    period: Period,
    as_of: date | None = None,
) -> int:
    """What is left of the period's free-to-spend. The number the user looks at.

    May be negative: that means the pockets claim more than the account holds,
    and it is deliberately not clamped to zero (docs/strategy.md section 4.2).
    """
    return free_to_spend(transactions, period) - fun_spend(transactions, period, as_of)
