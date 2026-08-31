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
    """A real bank transaction.

    `amount_cents` is negative for money leaving the account and positive for
    money arriving.
    """

    id: str
    date: date
    amount_cents: int
    description: str
    counterparty: str = ""
    classification: Classification = Classification.REQUIRED

    @property
    def is_outflow(self) -> bool:
        return self.amount_cents < 0
