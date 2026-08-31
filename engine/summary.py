"""One period's numbers, as the report scripts render them."""

from __future__ import annotations

from dataclasses import dataclass

from engine.period import Period


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

    @property
    def surplus_cents(self) -> int:
        """What this period hands to the next as free-to-spend."""
        return self.closing_balance_cents - self.free_to_spend_cents

    @property
    def is_overspent(self) -> bool:
        return self.remaining_free_to_spend_cents < 0
