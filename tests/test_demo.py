"""The generated demo year, and the invariants it must satisfy."""

from datetime import date

from demo.generator import (
    OPENING_BALANCE_ID,
    SPLURGE_OFFSET,
    first_budget_date,
    generate_year,
    last_date,
)

from engine import Classification, summarise

ROLLOVER_DAY = 27


def summaries(**kwargs):
    transactions = generate_year(rollover_day=ROLLOVER_DAY, **kwargs)
    return transactions, summarise(
        transactions,
        ROLLOVER_DAY,
        today=last_date(transactions),
        since=first_budget_date(transactions),
    )


def test_generation_is_deterministic():
    a = generate_year()
    b = generate_year()
    assert a == b


def test_a_different_seed_gives_different_data():
    assert generate_year(seed=1) != generate_year(seed=2)


def test_transactions_are_sorted_by_date():
    transactions = generate_year()
    assert transactions == sorted(transactions, key=lambda t: (t.date, t.id))


def test_the_opening_balance_precedes_every_budget_event():
    transactions = generate_year(rollover_day=ROLLOVER_DAY)
    (opening,) = [t for t in transactions if t.id == OPENING_BALANCE_ID]
    assert opening.date < first_budget_date(transactions)


def test_a_year_produces_twelve_full_periods_plus_the_running_one():
    _, results = summaries()
    assert len(results) == 13


def test_every_period_reconciles():
    """closing = free-to-spend + income - required - fun, for every period."""
    _, results = summaries()
    for s in results:
        expected = (
            s.free_to_spend_cents + s.income_cents - s.required_spend_cents - s.fun_spend_cents
        )
        assert expected == s.closing_balance_cents, s.period.label


def test_each_free_to_spend_is_the_previous_closing_balance():
    _, results = summaries()
    for earlier, later in zip(results, results[1:]):
        assert earlier.closing_balance_cents == later.free_to_spend_cents


def test_salary_and_rent_land_in_the_period_they_pay_for():
    """Each full period should hold exactly one salary and one rent."""
    transactions, results = summaries()
    for s in results[:-1]:
        in_period = [t for t in transactions if s.period.contains(t.date)]
        assert sum(1 for t in in_period if t.description == "Salary") == 1, s.period.label
        assert sum(1 for t in in_period if t.description == "Rent") == 1, s.period.label


def test_the_year_contains_the_events_worth_looking_at():
    transactions = generate_year()
    descriptions = {t.description for t in transactions}
    assert "Car insurance, annual premium" in descriptions  # a large non-monthly cost
    assert "Travel expenses reimbursed" in descriptions  # a windfall
    assert "Car repair" in descriptions  # a nasty surprise
    assert "Holiday, two weeks Mallorca" in descriptions  # saved up for, then spent


def test_the_default_year_never_overspends():
    _, results = summaries()
    assert not any(s.is_overspent for s in results)


def test_an_overspent_period_can_be_summoned():
    """docs/implementation.md section 8: awkward cases on demand, not by waiting."""
    _, results = summaries(splurge_cents=-480_000)
    overspent = [s for s in results if s.is_overspent]
    assert overspent
    assert overspent[0].period == results[SPLURGE_OFFSET].period


def test_fun_spending_is_a_realistic_share_of_income():
    transactions, _ = summaries()
    fun = -sum(t.amount_cents for t in transactions if t.classification is Classification.FUN)
    income = sum(
        t.amount_cents
        for t in transactions
        if t.classification is Classification.REQUIRED and t.amount_cents > 0
    )
    assert 0.20 < fun / income < 0.45


def test_the_demo_needs_no_clock():
    """Nothing in generation or summarising reads today's date."""
    transactions = generate_year()
    assert last_date(transactions) < date(2027, 1, 1)
