"""Shared helpers for building small, readable ledgers."""

from __future__ import annotations

from datetime import date

from engine import Classification, Transaction

_counter = iter(range(1, 10_000))


def txn(
    day: str,
    euros: float,
    description: str = "test",
    classification: Classification = Classification.REQUIRED,
) -> Transaction:
    """A transaction from an ISO date and an amount in euros.

    Negative euros mean money leaving. Amounts are converted to integer cents
    here so the tests stay readable without floats reaching the engine.
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
