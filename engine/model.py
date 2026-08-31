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

    **Two dates.** `booking_date` is when the bank posted the entry, and so when
    the balance changed; every calculation uses it. `value_date` (German
    *Wertstellung*) is an interest-calculation date the bank also supplies. It is
    stored for fidelity and deliberately touches nothing: assigning periods by
    value date would make our derived balance disagree with the bank's on the
    days the two differ, and the balance reconciliation in
    docs/implementation.md section 3.3 would then fire spuriously.

    There is no field for when the purchase actually happened. German exports do
    not supply one as a column; for card payments it appears inside the purpose
    text. That is the payment float question, deferred in docs/strategy.md
    section 5.
    """

    id: str
    booking_date: date
    amount_cents: int
    description: str
    counterparty: str = ""
    classification: Classification = Classification.REQUIRED
    reviewed: bool = False
    value_date: date | None = None
    kind: str = ""
    """The bank's own label for the entry, e.g. ING's Buchungstext. Free text,
    never an enum: the set of values a bank uses is not knowable in advance."""

    @property
    def is_outflow(self) -> bool:
        return self.amount_cents < 0
