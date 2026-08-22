from datetime import date

import pytest

from engine import Period, period_containing, periods_between
from engine.period import next_period


def d(iso: str) -> date:
    return date.fromisoformat(iso)


def test_period_runs_rollover_day_to_rollover_day():
    period = period_containing(d("2026-03-15"), rollover_day=27)
    assert period == Period(d("2026-02-27"), d("2026-03-27"))


def test_the_rollover_day_itself_starts_the_new_period():
    """The boundary is half-open: the 27th belongs to the period it opens."""
    assert period_containing(d("2026-03-27"), 27).start == d("2026-03-27")
    assert period_containing(d("2026-03-26"), 27).start == d("2026-02-27")


def test_a_period_contains_its_start_but_not_its_end():
    period = period_containing(d("2026-03-15"), 27)
    assert period.contains(period.start)
    assert not period.contains(period.end)
    assert period.last_day == d("2026-03-26")


def test_rollover_day_clamps_in_short_months():
    """A rollover day of 31 lands on the last day of February, not an error."""
    period = period_containing(d("2026-02-10"), rollover_day=31)
    assert period == Period(d("2026-01-31"), d("2026-02-28"))


def test_clamping_stays_contiguous():
    """Clamping must not open a gap or an overlap between periods."""
    current = period_containing(d("2026-01-15"), rollover_day=31)
    for _ in range(14):
        following = next_period(current, 31)
        assert following.start == current.end
        current = following


def test_periods_between_covers_the_range_without_gaps():
    periods = periods_between(d("2025-09-01"), d("2026-08-31"), 27)
    assert periods[0].contains(d("2025-09-01"))
    assert periods[-1].contains(d("2026-08-31"))
    for earlier, later in zip(periods, periods[1:]):
        assert earlier.end == later.start


def test_periods_between_is_empty_when_the_range_is_backwards():
    assert periods_between(d("2026-03-01"), d("2026-02-01"), 27) == []


def test_period_label_is_a_date_range_not_a_month_name():
    """docs/strategy.md section 7: a period is shown as its actual date range."""
    assert period_containing(d("2026-03-15"), 27).label == "2026-02-27 to 2026-03-26"


@pytest.mark.parametrize("bad", [0, 32, -1])
def test_invalid_rollover_day_is_rejected(bad):
    with pytest.raises(ValueError):
        period_containing(d("2026-03-15"), bad)
