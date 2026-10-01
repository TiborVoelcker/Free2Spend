"""Shared helpers for building small, readable ledgers."""

from __future__ import annotations

import itertools
from datetime import date

from engine import BalanceAnchor, Classification, Ledger, Transaction

_counter = itertools.count(1)


def txn(
    day: str,
    euros: float,
    description: str = "test",
    classification: Classification = Classification.REQUIRED,
) -> Transaction:
    """A transaction from an ISO date and an amount in euros.

    Negative euros mean money leaving. Converted to integer cents here so the
    tests stay readable without floats reaching the engine.
    """
    return Transaction(
        id=f"t{next(_counter):04d}",
        booking_date=date.fromisoformat(day),
        amount_cents=round(euros * 100),
        description=description,
        classification=classification,
    )


def fun(day: str, euros: float, description: str = "fun") -> Transaction:
    return txn(day, euros, description, Classification.FUN)


def anchor(day: str, euros: float) -> BalanceAnchor:
    """The balance at the end of `day`, as the bank stated it."""
    return BalanceAnchor(date.fromisoformat(day), round(euros * 100), "test")


def ledger(*transactions: Transaction, anchors: tuple[BalanceAnchor, ...] = ()) -> Ledger:
    return Ledger(transactions, anchors)
