from datetime import date

from conftest import anchor, fun, ledger, txn

from engine import period_containing, summarise

PERIOD = period_containing(date(2026, 3, 5), 27)  # 2026-02-27 to 2026-03-26


def d(iso: str) -> date:
    return date.fromisoformat(iso)


def test_balance_before_excludes_the_day_itself():
    """The balance as a day begins, so a rollover does not count its own day."""
    book = ledger(txn("2026-03-01", 100), txn("2026-03-02", 50))
    assert book.balance_before(d("2026-03-02")) == 10_000
    assert book.balance_before(d("2026-03-03")) == 15_000


def test_an_empty_ledger_is_zero_everywhere():
    book = ledger()
    assert not book
    assert book.balance_before(d("2026-03-05")) == 0
    assert book.free_to_spend(PERIOD) == 0
    assert book.remaining_free_to_spend(PERIOD) == 0
    assert summarise(book, 27, today=d("2026-03-05")) == []


def test_required_spending_does_not_touch_this_period_free_to_spend():
    """Required spending only moves the balance; it shows up at the next rollover."""
    without = ledger(txn("2026-02-20", 500))
    with_rent = ledger(txn("2026-02-20", 500), txn("2026-03-01", -300, "rent"))
    assert with_rent.free_to_spend(PERIOD) == without.free_to_spend(PERIOD) == 50_000


def test_fun_spending_reduces_remaining_but_not_free_to_spend():
    book = ledger(txn("2026-02-20", 500), fun("2026-03-05", -120))
    assert book.free_to_spend(PERIOD) == 50_000
    assert book.remaining_free_to_spend(PERIOD) == 38_000


def test_only_fun_inside_the_period_counts():
    """Either side of the boundary, and a refund that gives some back."""
    book = ledger(
        fun("2026-02-26", -50),  # the day before the period opens
        fun("2026-03-05", -120),
        fun("2026-03-09", 45, "returned"),
        fun("2026-03-27", -50),  # the day the next period opens
    )
    assert book.fun_spend(PERIOD) == 7_500


def test_as_of_stops_the_count_part_way_through_a_period():
    book = ledger(txn("2026-02-20", 500), fun("2026-03-05", -120), fun("2026-03-20", -80))
    assert book.fun_spend(PERIOD, as_of=d("2026-03-10")) == 12_000
    assert book.fun_spend(PERIOD) == 20_000


def test_remaining_is_not_clamped_at_zero():
    """docs/strategy.md section 4.2: a negative number is the warning."""
    book = ledger(txn("2026-02-20", 100), fun("2026-03-05", -250))
    assert book.remaining_free_to_spend(PERIOD) == -15_000


# --- anchors ---


def test_an_anchor_is_the_balance_at_the_end_of_its_day():
    book = ledger(txn("2026-03-05", -30), anchors=(anchor("2026-02-28", 500),))
    assert book.balance_before(d("2026-03-05")) == 50_000
    assert book.balance_before(d("2026-03-06")) == 47_000


def test_transactions_before_an_anchor_are_not_counted_twice():
    """The anchor already includes them; it is the balance, not an addition."""
    book = ledger(
        txn("2026-01-10", 900),
        txn("2026-03-05", -30),
        anchors=(anchor("2026-02-28", 500),),
    )
    assert book.balance_before(d("2026-03-06")) == 47_000


def test_the_latest_anchor_before_the_moment_wins():
    """It keeps the span of transactions being trusted as short as possible."""
    book = ledger(
        txn("2026-03-05", -30),
        anchors=(anchor("2026-01-31", 100), anchor("2026-02-28", 500)),
    )
    assert book.balance_before(d("2026-03-06")) == 47_000


def test_two_anchors_on_one_day_resolve_the_same_way_whatever_the_order():
    """They contradict each other and cannot both be right.

    Which one wins is arbitrary, but it must not depend on the order they
    happened to be constructed in. `reconcile` is what reports the conflict.
    """
    one, two = anchor("2026-02-28", 500), anchor("2026-02-28", 900)
    forwards = ledger(txn("2026-03-05", -30), anchors=(one, two))
    backwards = ledger(txn("2026-03-05", -30), anchors=(two, one))

    assert forwards.balance_before(d("2026-03-06")) == backwards.balance_before(d("2026-03-06"))
    assert forwards.reconcile() == backwards.reconcile()
    assert len(forwards.reconcile()) == 1


def test_reconcile_is_quiet_when_the_transactions_explain_the_anchors():
    book = ledger(
        txn("2026-03-05", -30),
        txn("2026-03-20", 80),
        anchors=(anchor("2026-02-28", 500), anchor("2026-03-31", 550)),
    )
    assert book.reconcile() == []


def test_reconcile_finds_a_missing_transaction():
    """A discrepancy means transactions are missing, which is the whole point."""
    book = ledger(
        txn("2026-03-05", -30),
        anchors=(anchor("2026-02-28", 500), anchor("2026-03-31", 550)),
    )
    (problem,) = book.reconcile()
    assert "47000" in problem and "55000" in problem
