"""One period's numbers, and a series of them."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from engine.ledger import Ledger
from engine.period import Period, periods_between


@dataclass(frozen=True)
class PeriodSummary:
    """Spend figures are positive: they are amounts of money that left."""

    period: Period
    free_to_spend_cents: int
    income_cents: int
    required_spend_cents: int
    fun_spend_cents: int
    remaining_free_to_spend_cents: int
    closing_balance_cents: int

    @classmethod
    def of(cls, ledger: Ledger, period: Period, as_of: date | None = None) -> PeriodSummary:
        opening = ledger.free_to_spend(period)
        fun = ledger.fun_spend(period, as_of)
        return cls(
            period=period,
            free_to_spend_cents=opening,
            income_cents=ledger.income(period),
            required_spend_cents=ledger.required_spend(period),
            fun_spend_cents=fun,
            remaining_free_to_spend_cents=opening - fun,
            closing_balance_cents=ledger.balance_before(period.end),
        )

    @property
    def surplus_cents(self) -> int:
        """What this period hands to the next as free-to-spend."""
        return self.closing_balance_cents - self.free_to_spend_cents

    @property
    def is_overspent(self) -> bool:
        return self.remaining_free_to_spend_cents < 0


def summarise(
    ledger: Ledger,
    rollover_day: int,
    today: date,
    since: date | None = None,
) -> list[PeriodSummary]:
    """One summary per period, from the earliest transaction through `today`.

    `since` starts the report later; earlier transactions still count toward the
    balance, they simply are not given a row.

    `today` is a parameter rather than read from a clock, so a whole simulated
    year runs through the engine reproducibly.
    """
    if not ledger:
        return []
    first = ledger.first_date
    if since is not None:
        first = max(first, since)
    if first > today:
        return []
    return [
        PeriodSummary.of(ledger, period, today)
        for period in periods_between(first, today, rollover_day)
    ]
