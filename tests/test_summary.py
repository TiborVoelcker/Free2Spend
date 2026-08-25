"""Summaries, and the salary-timing case the rollover day exists for."""

from datetime import date

from conftest import fun, txn

from engine import free_to_spend, period_containing, summarise


def d(iso: str) -> date:
    return date.fromisoformat(iso)


# Salary and rent for September both land at the end of August, which is the
# situation docs/strategy.md section 4.1 is about.
LEDGER = [
    txn("2025-08-26", 2400, "opening balance"),
    txn("2025-08-29", 3200, "salary"),
    txn("2025-08-30", -1150, "rent"),
    txn("2025-09-10", -400, "groceries"),
    fun("2025-09-12", -200, "restaurant"),
]


def test_salary_arriving_early_counts_toward_the_month_it_pays_for():
    """With a rollover day of 27, the 29th of August belongs to September."""
    september = period_containing(d("2025-09-10"), 27)
    assert september.start == d("2025-08-27")
    assert free_to_spend(LEDGER, september) == 240_000  # the opening balance alone


def test_a_calendar_month_boundary_overstates_free_to_spend_by_a_salary():
    """The bug the rollover day prevents, stated as a test.

    With a rollover day of 1, August's balance still holds September's salary,
    so September's free-to-spend is inflated by the salary net of the rent that
    arrived with it. It happens every month, so the overstatement is permanent.
    """
    correct = free_to_spend(LEDGER, period_containing(d("2025-09-10"), 27))
    inflated = free_to_spend(LEDGER, period_containing(d("2025-09-10"), 1))
    assert inflated - correct == 320_000 - 115_000


def test_a_period_reconciles():
    september = period_containing(d("2025-09-10"), 27)
    (summary,) = [
        s for s in summarise(LEDGER, 27, today=d("2025-09-26")) if s.period == september
    ]
    assert summary.free_to_spend_cents == 240_000
    assert summary.income_cents == 320_000
    assert summary.required_spend_cents == 115_000 + 40_000
    assert summary.fun_spend_cents == 20_000
    assert summary.remaining_free_to_spend_cents == 220_000
    assert summary.closing_balance_cents == 385_000


def test_overspending_carries_into_the_next_period():
    """Each free-to-spend is the previous closing balance, even when it is bad."""
    ledger = [
        txn("2025-08-26", 2400, "opening balance"),
        txn("2025-08-29", 3200, "salary"),
        txn("2025-09-29", 3200, "salary"),
        fun("2025-09-12", -5000, "a very expensive holiday"),
    ]
    first, second = summarise(ledger, 27, today=d("2025-10-26"), since=d("2025-08-27"))
    assert first.remaining_free_to_spend_cents == 240_000 - 500_000
    assert first.is_overspent
    assert second.free_to_spend_cents == first.closing_balance_cents < 240_000


def test_transactions_after_today_are_not_reported_but_still_exist():
    """`today` bounds the report, not the ledger."""
    summaries = summarise(LEDGER, 27, today=d("2025-09-11"))
    assert summaries[-1].period.contains(d("2025-09-11"))
    assert summaries[-1].fun_spend_cents == 0  # the restaurant is on the 12th


def test_summarise_edges():
    assert summarise([], 27, today=d("2025-09-26")) == []
    assert summarise(LEDGER, 27, today=d("2025-09-26"), since=d("2026-01-01")) == []
    assert len(summarise(LEDGER, 27, today=d("2025-09-26"), since=d("2025-08-29"))) == 1
