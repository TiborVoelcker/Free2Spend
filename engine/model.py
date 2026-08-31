"""The domain types the engine works over."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class Classification(Enum):
    """What a transaction is (docs/strategy.md section 2.4).

    REQUIRED is the default and does not touch free-to-spend; it only moves the
    balance, and so shows up at the next rollover. FUN is paid out of
    free-to-spend.

    POCKET_PAYMENT and TRANSFER arrive with their milestones (M3 and a second
    tracked account respectively).
    """

    REQUIRED = "required"
    FUN = "fun"


@dataclass(frozen=True)
class Transaction:
    """A real bank transaction. `amount_cents` is negative for money leaving."""

    id: str
    booking_date: date
    amount_cents: int
    description: str
    counterparty: str = ""
    classification: Classification = Classification.REQUIRED
    reviewed: bool = False
    value_date: date | None = None
    kind: str = ""

    @property
    def is_outflow(self) -> bool:
        return self.amount_cents < 0


@dataclass(frozen=True)
class BalanceAnchor:
    """What the bank said the balance was at the end of `as_of`.

    Ground truth. Transactions fill the gaps between anchors, and where the two
    disagree the anchor is right and transactions are missing.
    """

    as_of: date
    balance_cents: int
    source: str = ""
