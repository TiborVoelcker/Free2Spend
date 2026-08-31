from datetime import date

from conftest import fun, txn

from engine import (
    balance_before,
    free_to_spend,
    fun_spend,
    period_containing,
    remaining_free_to_spend,
)

PERIOD = period_containing(date(2026, 3, 5), 27)  # 2026-02-27 to 2026-03-26


def d(iso: str) -> date:
    return date.fromisoformat(iso)


def test_balance_before_excludes_the_day_itself():
    """The balance as a day begins, so a rollover does not count its own day."""
    ledger = [txn("2026-03-01", 100), txn("2026-03-02", 50)]
    assert balance_before(ledger, d("2026-03-02")) == 10_000
    assert balance_before(ledger, d("2026-03-03")) == 15_000


def test_an_empty_ledger_is_zero_everywhere():
    assert balance_before([], d("2026-03-05")) == 0
    assert free_to_spend([], PERIOD) == 0
    assert fun_spend([], PERIOD) == 0
    assert remaining_free_to_spend([], PERIOD) == 0


def test_required_spending_does_not_touch_this_period_free_to_spend():
    """Required spending only moves the balance; it shows up at the next rollover."""
    without = [txn("2026-02-20", 500)]
    with_rent = [*without, txn("2026-03-01", -300, "rent")]
    assert free_to_spend(with_rent, PERIOD) == free_to_spend(without, PERIOD) == 50_000
    assert remaining_free_to_spend(with_rent, PERIOD) == remaining_free_to_spend(without, PERIOD)


def test_fun_spending_reduces_remaining_but_not_free_to_spend():
    ledger = [txn("2026-02-20", 500), fun("2026-03-05", -120)]
    assert free_to_spend(ledger, PERIOD) == 50_000
    assert remaining_free_to_spend(ledger, PERIOD) == 38_000


def test_only_fun_inside_the_period_counts():
    """Either side of the boundary, and a refund that gives some back."""
    ledger = [
        fun("2026-02-26", -50),  # the day before the period opens
        fun("2026-03-05", -120),
        fun("2026-03-09", 45, "returned"),
        fun("2026-03-27", -50),  # the day the next period opens
    ]
    assert fun_spend(ledger, PERIOD) == 7_500


def test_as_of_stops_the_count_part_way_through_a_period():
    ledger = [txn("2026-02-20", 500), fun("2026-03-05", -120), fun("2026-03-20", -80)]
    assert fun_spend(ledger, PERIOD, as_of=d("2026-03-10")) == 12_000
    assert fun_spend(ledger, PERIOD, as_of=d("2026-03-25")) == 20_000
    assert fun_spend(ledger, PERIOD) == 20_000


def test_remaining_is_not_clamped_at_zero():
    """docs/strategy.md section 4.2: a negative number is the warning."""
    ledger = [txn("2026-02-20", 100), fun("2026-03-05", -250)]
    assert remaining_free_to_spend(ledger, PERIOD) == -15_000
