"""The generated demo year. Its numbers are taste; only these properties matter."""

from demo.generator import first_budget_date, generate_year, last_date

from engine import summarise

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
    assert generate_year() == generate_year()


def test_every_period_reconciles_and_chains():
    _, results = summaries()
    for s in results:
        assert s.closing_balance_cents == (
            s.free_to_spend_cents + s.income_cents - s.required_spend_cents - s.fun_spend_cents
        ), s.period.label
    for earlier, later in zip(results, results[1:]):
        assert earlier.closing_balance_cents == later.free_to_spend_cents


def test_salary_and_rent_land_in_the_period_they_pay_for():
    """The property the demo year exists to demonstrate."""
    transactions, results = summaries()
    for s in results[:-1]:
        in_period = [t for t in transactions if s.period.contains(t.date)]
        assert sum(1 for t in in_period if t.description == "Salary") == 1, s.period.label
        assert sum(1 for t in in_period if t.description == "Rent") == 1, s.period.label


def test_an_overspent_period_can_be_summoned():
    """docs/implementation.md section 8: awkward cases on demand, not by waiting."""
    _, default = summaries()
    _, splurged = summaries(splurge_cents=-480_000)
    assert not any(s.is_overspent for s in default)
    assert any(s.is_overspent for s in splurged)
