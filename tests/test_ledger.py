from datetime import date

from conftest import fun, txn

from engine import (
    balance_before,
    free_to_spend,
    fun_spend,
    period_containing,
    remaining_free_to_spend,
)


def d(iso: str) -> date:
    return date.fromisoformat(iso)


def test_balance_before_excludes_the_day_itself():
    """The balance as a day begins, so a rollover does not count its own day."""
    ledger = [txn("2026-03-01", 100), txn("2026-03-02", 50)]
    assert balance_before(ledger, d("2026-03-02")) == 10_000
    assert balance_before(ledger, d("2026-03-03")) == 15_000


def test_free_to_spend_is_the_balance_at_the_rollover():
    ledger = [txn("2026-02-20", 500), txn("2026-03-05", -200)]
    period = period_containing(d("2026-03-05"), 27)
    assert free_to_spend(ledger, period) == 50_000


def test_required_spending_does_not_touch_this_period_free_to_spend():
    """Required spending only moves the balance; it shows up at the next rollover."""
    period = period_containing(d("2026-03-05"), 27)
    without = [txn("2026-02-20", 500)]
    with_rent = [*without, txn("2026-03-01", -300, "rent")]
    assert free_to_spend(with_rent, period) == free_to_spend(without, period)
    assert remaining_free_to_spend(with_rent, period) == remaining_free_to_spend(without, period)


def test_fun_spending_reduces_remaining_but_not_free_to_spend():
    period = period_containing(d("2026-03-05"), 27)
    ledger = [txn("2026-02-20", 500), fun("2026-03-05", -120)]
    assert free_to_spend(ledger, period) == 50_000
    assert remaining_free_to_spend(ledger, period) == 38_000


def test_as_of_stops_the_count_part_way_through_a_period():
    period = period_containing(d("2026-03-05"), 27)
    ledger = [txn("2026-02-20", 500), fun("2026-03-05", -120), fun("2026-03-20", -80)]
    assert fun_spend(ledger, period, as_of=d("2026-03-10")) == 12_000
    assert fun_spend(ledger, period, as_of=d("2026-03-25")) == 20_000
    assert fun_spend(ledger, period) == 20_000


def test_a_fun_refund_reduces_fun_spending():
    period = period_containing(d("2026-03-05"), 27)
    ledger = [txn("2026-02-20", 500), fun("2026-03-05", -120), fun("2026-03-09", 45, "returned")]
    assert fun_spend(ledger, period) == 7_500


def test_remaining_is_not_clamped_at_zero():
    """docs/strategy.md section 4.2: a negative number is the warning."""
    period = period_containing(d("2026-03-05"), 27)
    ledger = [txn("2026-02-20", 100), fun("2026-03-05", -250)]
    assert remaining_free_to_spend(ledger, period) == -15_000


def test_fun_spending_outside_the_period_is_ignored():
    period = period_containing(d("2026-03-05"), 27)
    ledger = [txn("2026-02-20", 500), fun("2026-02-26", -50), fun("2026-03-28", -50)]
    assert fun_spend(ledger, period) == 0
