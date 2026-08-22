"""Period-by-period summaries. The shape the report script renders."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date

from engine.ledger import balance_before, free_to_spend, fun_spend
from engine.model import Classification, Transaction
from engine.period import Period, periods_between


@dataclass(frozen=True)
class PeriodSummary:
    """One period's numbers.

    Spend figures are positive: they are amounts of money that left.
    """

    period: Period
    free_to_spend_cents: int
    income_cents: int
    required_spend_cents: int
    fun_spend_cents: int
    remaining_free_to_spend_cents: int
    closing_balance_cents: int

    @property
    def is_overspent(self) -> bool:
        return self.remaining_free_to_spend_cents < 0


def summarise_period(
    transactions: Sequence[Transaction],
    period: Period,
    as_of: date | None = None,
) -> PeriodSummary:
    income = 0
    required = 0
    for transaction in transactions:
        if not period.contains(transaction.date):
            continue
        if transaction.classification is not Classification.REQUIRED:
            continue
        if transaction.amount_cents > 0:
            income += transaction.amount_cents
        else:
            required -= transaction.amount_cents

    opening = free_to_spend(transactions, period)
    fun = fun_spend(transactions, period, as_of)
    return PeriodSummary(
        period=period,
        free_to_spend_cents=opening,
        income_cents=income,
        required_spend_cents=required,
        fun_spend_cents=fun,
        remaining_free_to_spend_cents=opening - fun,
        closing_balance_cents=balance_before(transactions, period.end),
    )


def summarise(
    transactions: Iterable[Transaction],
    rollover_day: int,
    today: date,
    since: date | None = None,
) -> list[PeriodSummary]:
    """One summary per period, from the earliest transaction through `today`.

    `since` starts the report from a later period instead; earlier transactions
    still count toward the balance, they simply are not given a row.

    `today` is a parameter rather than read from a clock, so a whole simulated
    year can be run through the engine and any result reproduced exactly.
    """
    transactions = list(transactions)
    if not transactions:
        return []
    first = min(t.date for t in transactions)
    if since is not None:
        first = max(first, since)
    if first > today:
        return []
    periods = periods_between(first, today, rollover_day)
    return [summarise_period(transactions, period, today) for period in periods]
