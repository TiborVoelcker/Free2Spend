from datetime import date

import pytest

from engine import Period, period_containing, periods_between
from engine.period import next_period


def d(iso: str) -> date:
    return date.fromisoformat(iso)


def test_period_runs_rollover_day_to_rollover_day():
    assert period_containing(d("2026-03-15"), 27) == Period(d("2026-02-27"), d("2026-03-27"))


def test_the_rollover_day_itself_starts_the_new_period():
    """The boundary is half-open: the 27th belongs to the period it opens."""
    assert period_containing(d("2026-03-27"), 27).start == d("2026-03-27")
    assert period_containing(d("2026-03-26"), 27).start == d("2026-02-27")


def test_a_positive_rollover_day_clamps_in_short_months():
    assert period_containing(d("2026-02-10"), 31) == Period(d("2026-01-31"), d("2026-02-28"))


def test_a_negative_rollover_day_counts_back_from_the_month_end():
    """-1 is the last day of the month, -3 the third from last."""
    assert period_containing(d("2026-03-15"), -1) == Period(d("2026-02-28"), d("2026-03-31"))
    assert period_containing(d("2026-03-15"), -3) == Period(d("2026-02-26"), d("2026-03-29"))
    assert period_containing(d("2024-03-15"), -1).start == d("2024-02-29")  # leap year


@pytest.mark.parametrize("rollover_day", [1, 15, 27, 31, -1, -3, -28])
def test_periods_stay_contiguous_across_a_year(rollover_day):
    """Clamping at either end must not open a gap or an overlap."""
    current = period_containing(d("2026-01-15"), rollover_day)
    for _ in range(14):
        following = next_period(current, rollover_day)
        assert following.start == current.end
        assert period_containing(following.start, rollover_day) == following
        current = following


def test_periods_between_covers_the_range_without_gaps():
    periods = periods_between(d("2025-09-01"), d("2026-08-31"), 27)
    assert periods[0].contains(d("2025-09-01"))
    assert periods[-1].contains(d("2026-08-31"))
    assert all(a.end == b.start for a, b in zip(periods, periods[1:]))


@pytest.mark.parametrize(
    ("first", "last", "expected"),
    [
        ("2026-03-01", "2026-02-01", 0),  # backwards
        ("2026-03-15", "2026-03-15", 1),  # a single day
        ("2026-03-26", "2026-03-27", 2),  # straddling a rollover
    ],
)
def test_periods_between_edges(first, last, expected):
    assert len(periods_between(d(first), d(last), 27)) == expected


@pytest.mark.parametrize("bad", [0, 32, -29, 100])
def test_an_out_of_range_rollover_day_is_rejected(bad):
    with pytest.raises(ValueError):
        period_containing(d("2026-03-15"), bad)
